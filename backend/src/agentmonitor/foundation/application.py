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

from agentmonitor.contracts.foundation_v1 import LifecycleStateV1
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
    """Cleanup runs once in reverse order after every attempted lifespan.

    Shutdown hooks must be idempotent and tolerate incomplete or absent startup
    acquisition. Each receives a share of the shutdown deadline, so one failed,
    cancelled or timed-out hook cannot prevent the remaining cleanup attempts.
    All hooks must cooperate with cancellation, including their own I/O cleanup.
    """

    startup: tuple[AsyncHook, ...] = field(default=(), repr=False)
    shutdown: tuple[AsyncHook, ...] = field(default=(), repr=False)
    tasks: tuple[AsyncHook, ...] = field(default=(), repr=False)
    startup_timeout_seconds: float = 5
    shutdown_timeout_seconds: float = 5
    foundation_contract_mode: bool = False

    def __post_init__(self) -> None:
        for timeout in (self.startup_timeout_seconds, self.shutdown_timeout_seconds):
            if not math.isfinite(timeout) or not 0.05 <= timeout <= 60:
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

    def get_lifecycle_state(self) -> LifecycleStateV1:
        """Publish only current safe state; never acquire or probe a resource."""
        return LifecycleStateV1(self.phase, self.failure_code)

    async def _supervise(self, hook: AsyncHook) -> None:
        try:
            await hook()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Never retain exception objects, text, command, paths or tracebacks.
            self.task_failures += ("background_task_failed",)

    async def _cleanup(
        self, resource: CloseableResource | None, tasks: list[asyncio.Task[None]]
    ) -> None:
        self.phase = "stopping"
        for task in tasks:
            task.cancel()
        stages = len(self.hooks.shutdown) + bool(tasks)
        deadline = self.hooks.shutdown_timeout_seconds / max(stages, 1)
        try:
            if tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True), deadline
                    )
                except TimeoutError:
                    self.failure_code = self.failure_code or "shutdown_timeout"
            for hook in reversed(self.hooks.shutdown):
                try:
                    # Separate tasks contain a hook's self-cancellation; cleanup
                    # of the other resources must still execute and be awaited.
                    await asyncio.wait_for(hook(), deadline)
                except TimeoutError:
                    self.failure_code = self.failure_code or "shutdown_timeout"
                except asyncio.CancelledError:
                    self.failure_code = self.failure_code or "shutdown_cancelled"
                except Exception:
                    self.failure_code = self.failure_code or "shutdown_failed"
        finally:
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    self.failure_code = self.failure_code or "resource_close_failed"
            self.phase = "failed" if self.failure_code else "stopped"

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        if self.phase != "created":
            raise ApplicationLifecycleError("lifecycle_already_used")
        resource: CloseableResource | None = None
        tasks: list[asyncio.Task[None]] = []
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
                self.phase = "running"
            except asyncio.CancelledError:
                self.failure_code = "startup_cancelled"
                raise
            except TimeoutError:
                self.failure_code = "startup_timeout"
            except ApplicationLifecycleError as error:
                self.failure_code = error.code
            except Exception:
                self.failure_code = "startup_failed"
            if self.failure_code is None:
                yield
        finally:
            cleanup = asyncio.create_task(self._cleanup(resource, tasks))
            cancelled = False
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    # Repeated caller cancellation cannot abandon owned cleanup.
                    cancelled = True
            cleanup.result()
            if cancelled:
                raise asyncio.CancelledError
        # Raise outside the handler so raw exceptions cannot leak in the chain.
        if self.failure_code is not None:
            raise ApplicationLifecycleError(self.failure_code) from None
