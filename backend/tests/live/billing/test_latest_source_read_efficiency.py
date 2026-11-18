"""M7 continuity: real retained scheduling reads avoid full run-history scans."""

import sqlite3
from datetime import UTC, datetime

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
    _run_view,
    _utc_text,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from sqlalchemy import event
from sqlalchemy.engine import Engine

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


@pytest.fixture(scope="module")
def retained(tmp_path_factory: pytest.TempPathFactory) -> DatabaseRefV1:
    return _private_real_copy(tmp_path_factory.mktemp("scheduler-read-efficiency"))


@pytest.mark.parametrize("provider", ["claude", "codex", "ollama"])
@pytest.mark.parametrize("scoped", [False, True])
@pytest.mark.parametrize("historical", [False, True])
def test_latest_source_matches_real_history_with_bounded_query_work(
    retained: DatabaseRefV1, provider: str, scoped: bool, historical: bool
) -> None:
    with open_sqlite_database(retained, "runtime_read_only") as handle:
        with handle.connect() as connection:
            source = connection.exec_driver_sql(
                "SELECT capability_id,source_id,account_id,requested_at "
                "FROM collection_run "
                "WHERE provider_key=? AND account_id IS NOT NULL "
                "ORDER BY requested_at DESC,run_id LIMIT 1 OFFSET 10",
                (provider,),
            ).one_or_none()
            assert source is not None, "genuine_provider_history_required"
            capability, source_id, account, instant = source
    account_id = OpaqueIdV1(account) if scoped else None
    as_of = datetime.fromisoformat(instant) if historical else datetime.now(UTC)
    steps = 0

    def progress() -> int:
        nonlocal steps
        steps += 1000
        return 0

    def connected(driver: object, record: object) -> None:
        assert isinstance(driver, sqlite3.Connection)
        driver.set_progress_handler(progress, 1000)

    event.listen(Engine, "connect", connected)
    try:
        with open_sqlite_database(retained, "runtime_read_only") as handle:
            with handle.connect() as connection:
                row = (
                    connection.exec_driver_sql(
                        "SELECT * FROM collection_run WHERE provider_key=? "
                        "AND capability_id=? AND source_id=? AND requested_at<=? "
                        "AND (? IS NULL OR account_id=?) "
                        "ORDER BY requested_at DESC,run_id LIMIT 1",
                        (
                            provider,
                            capability,
                            source_id,
                            _utc_text(as_of),
                            account if scoped else None,
                            account if scoped else None,
                        ),
                    )
                    .mappings()
                    .one_or_none()
                )
                expected = _run_view(connection, row) if row is not None else None
        original_steps = steps
        assert original_steps > 10000, "genuine_nontrivial_history_required"
        steps = 0
        actual = SqliteCollectionRepositoryV1(retained).get_latest_source_run(
            provider, capability, source_id, as_of, account_id=account_id
        )
        if actual != expected:
            raise AssertionError("latest_source_history_result_changed")
        assert steps < original_steps // 4, "latest_source_scans_full_history"
    finally:
        event.remove(Engine, "connect", connected)
