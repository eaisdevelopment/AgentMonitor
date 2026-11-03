"""Optional service-owned Ollama process collection with bounded backoff."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.state.runtime_backoff import (
    OllamaRuntimeBackoffStoreErrorV1,
    OllamaRuntimeBackoffStoreV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.manifest import OLLAMA_PROVIDER_VERSION
from agentmonitor.composition.linux_runtime_monitoring import (
    LinuxRuntimeMonitoringCancelledV1,
    recover_pending_ollama_runtime_commits,
    run_scheduled_ollama_runtime_collection,
)
from agentmonitor.composition.ollama_installation_reconciliation import (
    reconcile_ollama_installation_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.queries import (
    GetLatestSourceRunV1,
    source_poll_is_due_v1,
)
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)

_CAPABILITY_ID = "local.process.observation"
_SOURCE_ID = "linux.proc.process.v1"
_MINIMUM_INTERVAL_MS = 300_000
_FAILURE_BACKOFF = timedelta(minutes=5)
_TICK_BUDGET_SECONDS = 20.0
_MAXIMUM_RECOVERY_RUNS_PER_TICK = 2
_TRANSIENT_READ_FAILURES = frozenset(
    {
        "linux_boot_scope_unavailable",
        "linux_deadline_exceeded",
        "linux_ollama_process_not_observed",
        "linux_procfs_unavailable",
    }
)


class OllamaRuntimeCollectorV1:
    """Collect exact local process facts without publishing an M03 capability."""

    def __init__(self, reference: DatabaseRefV1, *, data_root: Path) -> None:
        expected = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
        if reference != expected:
            raise ValueError("ollama_runtime_database_reference_invalid")
        self._reference = reference
        self._data_root = data_root
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._collection = SqliteCollectionRepositoryV1(reference)
        self._backoff = OllamaRuntimeBackoffStoreV1(data_root)
        self._instance = OpaqueIdV1("ollama-runtime-" + uuid.uuid4().hex)
        self._next_attempt_at: datetime | None = None
        self._recovery_complete = False
        self._stop_requested = Event()

    def _checkpoint(self, deadline_monotonic: float) -> None:
        if self._stop_requested.is_set():
            raise LinuxRuntimeMonitoringCancelledV1(
                "linux_runtime_collection_cancelled"
            )
        if time.monotonic() >= deadline_monotonic:
            raise RuntimeError("ollama_runtime_tick_deadline")

    def _record_failure(self, now: datetime) -> None:
        self._recovery_complete = False
        self._next_attempt_at = now + _FAILURE_BACKOFF
        try:
            self._backoff.write(self._next_attempt_at)
        except OllamaRuntimeBackoffStoreErrorV1:
            # The in-process deadline still prevents a hot loop. An unsafe or
            # unavailable state file is never replaced or treated as durable.
            pass

    def _backoff_deadline(self) -> datetime | None:
        persisted = self._backoff.not_before_at()
        candidates = tuple(
            value for value in (self._next_attempt_at, persisted) if value is not None
        )
        return max(candidates) if candidates else None

    def _clear_backoff(self, prior: datetime | None) -> None:
        self._next_attempt_at = None
        if prior is not None:
            self._backoff.write(None)

    def _reject_ambiguous_installation(self) -> None:
        matches = tuple(
            item
            for item in ListProviderInstallationsV1(self._registry)("ollama")
            if item.provider_key == "ollama"
            and item.platform_key == "linux-x86_64"
            and item.presence_state == "present"
            and item.version.state == "known_masked"
            and item.version.masked_value == OLLAMA_PROVIDER_VERSION
        )
        if len(matches) > 1:
            raise ValueError("ollama_runtime_installation_ambiguous")

    def _tick(self, now: datetime, *, deadline_monotonic: float) -> str:
        self._checkpoint(deadline_monotonic)
        if not self._recovery_complete:
            recover_pending_ollama_runtime_commits(
                self._reference,
                as_of=now,
                maximum_runs=_MAXIMUM_RECOVERY_RUNS_PER_TICK,
            )
            self._recovery_complete = True
        self._checkpoint(deadline_monotonic)

        latest = GetLatestSourceRunV1(self._collection)(
            "ollama", _CAPABILITY_ID, _SOURCE_ID, now
        )
        self._checkpoint(deadline_monotonic)
        transient = bool(
            latest is not None and latest.error_code in _TRANSIENT_READ_FAILURES
        )
        if not source_poll_is_due_v1(
            now,
            latest,
            _MINIMUM_INTERVAL_MS,
            transient_read_failure=transient,
        ):
            return (
                "ollama_runtime_backoff"
                if latest is not None and latest.state not in {"succeeded", "partial"}
                else "ollama_runtime_waiting"
            )

        self._reject_ambiguous_installation()
        self._checkpoint(deadline_monotonic)
        # An existing registry row is not a fresh installation observation.
        # Refresh from the real CLI only when this collection is due.
        reconcile_ollama_installation_v1(self._reference)
        self._checkpoint(deadline_monotonic)

        remaining_seconds = deadline_monotonic - time.monotonic()
        if remaining_seconds <= 0:
            raise RuntimeError("ollama_runtime_tick_deadline")
        result = run_scheduled_ollama_runtime_collection(
            self._data_root,
            scheduler_instance_id=self._instance,
            cancellation_requested=self._stop_requested.is_set,
            operation_deadline_at=datetime.now(UTC)
            + timedelta(seconds=remaining_seconds),
            recover_pending=False,
        )
        return (
            "ollama_runtime_partial"
            if result.completed_run.state == "partial"
            else "ollama_runtime_collected"
        )

    def tick(self) -> str:
        """Run at most one due collection and classify expected optional failure."""

        now = datetime.now(UTC)
        deadline_monotonic = time.monotonic() + _TICK_BUDGET_SECONDS
        try:
            backoff = self._backoff_deadline()
            if backoff is not None and now < backoff:
                return "ollama_runtime_backoff"
            result = self._tick(now, deadline_monotonic=deadline_monotonic)
            self._clear_backoff(backoff)
            return result
        except LinuxRuntimeMonitoringCancelledV1:
            return "ollama_runtime_stopping"
        except Exception:  # noqa: BLE001 - optional task boundary emits only safe state.
            self._record_failure(now)
            return "ollama_runtime_unavailable"

    async def run(self) -> None:
        """Keep the optional collector isolated and cancellation-cooperative."""

        previous = None
        output_available = True
        while True:
            work = asyncio.create_task(asyncio.to_thread(self.tick))
            try:
                status = await asyncio.shield(work)
            except asyncio.CancelledError:
                self._stop_requested.set()
                await work
                raise
            except Exception:  # noqa: BLE001 - keep the optional supervised lane alive.
                self._record_failure(datetime.now(UTC))
                status = "ollama_runtime_unavailable"
            if output_available and status != previous:
                try:
                    print(json.dumps({"event": status}), flush=True)
                except (OSError, ValueError):
                    output_available = False
                previous = status
            await asyncio.sleep(1)
