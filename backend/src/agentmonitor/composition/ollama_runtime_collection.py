"""Optional service-owned Ollama process collection with bounded backoff."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.manifest import OLLAMA_PROVIDER_VERSION
from agentmonitor.composition.linux_runtime_monitoring import (
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
        self._instance = OpaqueIdV1("ollama-runtime-" + uuid.uuid4().hex)
        self._next_attempt_at: datetime | None = None
        self._installation_ready = False
        self._recovery_complete = False

    def _registered_installation_is_current(self) -> bool:
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
        return len(matches) == 1

    def _tick(self, now: datetime) -> str:
        if self._next_attempt_at is not None and now < self._next_attempt_at:
            return "ollama_runtime_backoff"
        if not self._recovery_complete:
            recover_pending_ollama_runtime_commits(self._reference, as_of=now)
            self._recovery_complete = True

        latest = GetLatestSourceRunV1(self._collection)(
            "ollama", _CAPABILITY_ID, _SOURCE_ID, now
        )
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

        if not self._installation_ready:
            self._installation_ready = self._registered_installation_is_current()
            if not self._installation_ready:
                reconcile_ollama_installation_v1(self._reference)
                self._installation_ready = True

        result = run_scheduled_ollama_runtime_collection(
            self._data_root, scheduler_instance_id=self._instance
        )
        self._next_attempt_at = None
        return (
            "ollama_runtime_partial"
            if result.completed_run.state == "partial"
            else "ollama_runtime_collected"
        )

    def tick(self) -> str:
        """Run at most one due collection and classify expected optional failure."""

        now = datetime.now(UTC)
        try:
            return self._tick(now)
        except (OSError, RuntimeError, ValueError):
            self._installation_ready = False
            self._recovery_complete = False
            self._next_attempt_at = now + _FAILURE_BACKOFF
            return "ollama_runtime_unavailable"

    async def run(self) -> None:
        """Keep the optional collector isolated and cancellation-cooperative."""

        previous = None
        while True:
            work = asyncio.create_task(asyncio.to_thread(self.tick))
            try:
                status = await asyncio.shield(work)
            except asyncio.CancelledError:
                await work
                raise
            if status != previous:
                print(json.dumps({"event": status}), flush=True)
                previous = status
            await asyncio.sleep(1)
