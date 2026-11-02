"""Live production-lifespan polling; use only an explicitly selected owner DB."""

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application, serve_loopback
from agentmonitor.contracts.capacity_v1 import QuotaWindowViewV1
from agentmonitor.foundation.application import LifecycleHooksV1


def test_production_service_collects_enabled_claude_and_preserves_registry() -> None:
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    if selected is None:
        pytest.skip("NOT RUN: explicit owner data root required for live polling")
    root = Path(selected)
    assert root.is_absolute() and (root / "agentmonitor.db").is_file()
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    registry = SqliteRegistryRepositoryV1(reference)
    accounts = registry.list_accounts("claude")
    enabled = tuple(
        row
        for row in accounts
        if row.is_effective_monitoring_enabled
        and any(
            profile.is_protected_default and profile.lifecycle == "active"
            for profile in registry.list_monitoring_profiles(row.account_id)
        )
    )
    assert len(enabled) == 1, "one eligible owner-confirmed real Claude required"
    account = enabled[0]
    before = (
        account.account_id,
        account.friendly_name,
        account.organization_id,
        account.record_version,
        account.monitoring_preference,
    )
    capacity = SqliteCapacityRepositoryV1(reference)
    collection = SqliteCollectionRepositoryV1(reference)
    port = int(os.environ.get("AGENTMONITOR_TEST_DASHBOARD_PORT", "0"))

    async def run() -> None:
        config = root / "service.env"
        stop = asyncio.Event()
        ready = asyncio.get_running_loop().create_future()
        app = create_iam_application(config, root, lifecycle=LifecycleHooksV1())
        started = datetime.now(UTC)
        server = asyncio.create_task(
            serve_loopback(
                app,
                host="127.0.0.1",
                port=port,
                ready=ready.set_result,
                stop=stop,
            )
        )
        try:
            await asyncio.wait_for(ready, 8)
            # Respect the real source cadence on repeat executions; never move
            # the machine clock or shorten the live source interval for a test.
            deadline = asyncio.get_running_loop().time() + 345
            fresh: tuple[QuotaWindowViewV1, ...] = ()
            while asyncio.get_running_loop().time() < deadline:
                quota_rows = capacity.list_account_quota_windows(
                    account.account_id, datetime.now(UTC)
                )
                current_rows: list[QuotaWindowViewV1] = []
                for row in quota_rows:
                    assert isinstance(row, QuotaWindowViewV1)
                    current_rows.append(row)
                fresh = tuple(current_rows)
                if fresh and all(row.collected_at >= started for row in fresh):
                    break
                await asyncio.sleep(0.5)
            observed_new_quota = bool(fresh) and all(
                row.collected_at >= started for row in fresh
            )
            assert observed_new_quota, (
                "enabled account received no new quota from service"
            )
            assert all(row.freshness == "fresh" for row in fresh)
            runs = collection.list_runs(
                "claude", account.account_id, datetime.now(UTC), 100
            )
            committed = tuple(
                row for row in runs if row.run_id == fresh[0].collection_run_id
            )
            assert len(committed) == 1
            assert committed[0].state in {"succeeded", "partial"}
            assert committed[0].observation_ids
        finally:
            stop.set()
            await asyncio.wait_for(server, 35)

        current = registry.get_account(account.account_id)
        assert current is not None
        assert (
            current.account_id,
            current.friendly_name,
            current.organization_id,
            current.record_version,
            current.monitoring_preference,
        ) == before
        original_runs = collection.list_runs(
            "claude", account.account_id, datetime.now(UTC), 100
        )
        stop = asyncio.Event()
        ready = asyncio.get_running_loop().create_future()
        app = create_iam_application(config, root, lifecycle=LifecycleHooksV1())
        server = asyncio.create_task(
            serve_loopback(
                app,
                host="127.0.0.1",
                port=port,
                ready=ready.set_result,
                stop=stop,
            )
        )
        try:
            await asyncio.wait_for(ready, 8)
            await asyncio.sleep(6)
            assert (
                collection.list_runs(
                    "claude", account.account_id, datetime.now(UTC), 100
                )
                == original_runs
            )
        finally:
            stop.set()
            await asyncio.wait_for(server, 35)

    asyncio.run(run())


def test_service_restart_does_not_duplicate_optional_runtime_collection(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    config = tmp_path / "service.env"
    config.write_text("")
    config.chmod(0o600)

    async def run() -> None:
        first_runs = None
        for attempt in range(2):
            app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
            stop = asyncio.Event()
            ready = asyncio.get_running_loop().create_future()
            server = asyncio.create_task(
                serve_loopback(
                    app,
                    host="127.0.0.1",
                    port=0,
                    ready=ready.set_result,
                    stop=stop,
                )
            )
            try:
                await asyncio.wait_for(ready, 8)
                await asyncio.sleep(1)
            finally:
                stop.set()
                await asyncio.wait_for(server, 35)
            # SQLite's read-only runtime opens may retain journal sidecars.
            runs = SqliteCollectionRepositoryV1(reference).list_runs(
                None, None, datetime.now(UTC), 100
            )
            if attempt == 0:
                first_runs = runs
            else:
                assert runs == first_runs

    asyncio.run(run())
