"""CTR-FND-002 lifecycle mechanism; no framework, adapter or import-time I/O.

Hooks are explicit approved composition callables, never plugin import strings.
They must cooperate with cancellation; external I/O implementations retain
their own bounded deadlines. Optional task failures are isolated and recorded
as safe codes. The foundation starts no collector or provider task itself.
"""

import asyncio
import math
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Literal, Protocol

from agentmonitor.foundation.observability import CorrelationContextV1


class ApplicationLifecycleError(ValueError):
    """Only code-owned sanitized classifications may cross the lifecycle seam."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class CloseableResource(Protocol):
    def close(self) -> None: ...


AsyncHook = Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class ComponentFactorySetV1:
    """No resource is acquired until lifespan. None permits schema generation only."""

    open_database: Callable[[], CloseableResource] | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class LifecycleHooksV1:
    startup: tuple[AsyncHook, ...] = field(default=(), repr=False)
    shutdown: tuple[AsyncHook, ...] = field(default=(), repr=False)
    tasks: tuple[AsyncHook, ...] = field(default=(), repr=False)
    startup_timeout_seconds: float = 5
    shutdown_timeout_seconds: float = 5
    foundation_contract_mode: bool = False

    def __post_init__(self) -> None:
        for timeout in (self.startup_timeout_seconds, self.shutdown_timeout_seconds):
            if not math.isfinite(timeout) or not 0.05 <= timeout <= 30:
                raise ApplicationLifecycleError("lifecycle_deadline_invalid")
        for hooks in (self.startup, self.shutdown, self.tasks):
            if not isinstance(hooks, tuple) or len(hooks) > 32:
                raise ApplicationLifecycleError("lifecycle_hooks_invalid")
            if not all(callable(hook) for hook in hooks):
                raise ApplicationLifecycleError("lifecycle_hooks_invalid")


@dataclass(slots=True)
class ApplicationLifecycleV1:
    components: ComponentFactorySetV1 = field(repr=False)
    hooks: LifecycleHooksV1 = field(repr=False)
    phase: Literal[
        "created", "starting", "running", "stopping", "stopped", "failed"
    ] = "created"
    failure_code: str | None = None
    task_failures: tuple[str, ...] = ()
    startup_context: CorrelationContextV1 | None = field(default=None, repr=False)

    async def _supervise(self, hook: AsyncHook) -> None:
        try:
            await hook()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Never retain exception objects, text, command, paths or tracebacks.
            self.task_failures += ("background_task_failed",)

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        if self.phase != "created":
            raise ApplicationLifecycleError("lifecycle_already_used")
        resource: CloseableResource | None = None
        tasks: list[asyncio.Task[None]] = []
        started = False
        self.phase = "starting"
        self.startup_context = CorrelationContextV1()
        try:
            try:
                if self.components.open_database is None:
                    raise ApplicationLifecycleError("runtime_components_missing")
                # The approved SQLite factory has a bounded driver timeout and
                # runs before traffic. It performs no implicit migration/DDL.
                resource = self.components.open_database()
                async with asyncio.timeout(self.hooks.startup_timeout_seconds):
                    for hook in self.hooks.startup:
                        await hook()
                tasks = [
                    asyncio.create_task(self._supervise(hook))
                    for hook in self.hooks.tasks
                ]
                started = True
                self.phase = "running"
            except TimeoutError:
                self.failure_code = "startup_timeout"
            except ApplicationLifecycleError as error:
                self.failure_code = error.code
            except Exception:
                self.failure_code = "startup_failed"
            if self.failure_code is None:
                yield
        finally:
            self.phase = "stopping"
            for task in tasks:
                task.cancel()
            try:
                async with asyncio.timeout(self.hooks.shutdown_timeout_seconds):
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                    if started:
                        for hook in reversed(self.hooks.shutdown):
                            await hook()
            except TimeoutError:
                self.failure_code = self.failure_code or "shutdown_timeout"
            except Exception:
                self.failure_code = self.failure_code or "shutdown_failed"
            finally:
                if resource is not None:
                    try:
                        resource.close()
                    except Exception:
                        self.failure_code = self.failure_code or "resource_close_failed"
                self.phase = "failed" if self.failure_code else "stopped"
        # Raise outside the handler so raw exceptions cannot leak in the chain.
        if self.failure_code is not None:
            raise ApplicationLifecycleError(self.failure_code) from None
