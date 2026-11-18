"""Missing retention authority must fail before any database is created."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1


def test_missing_retention_dependencies_do_not_open_database(tmp_path: Path) -> None:
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_retention import (
        SqliteBudgetRetentionV1,
    )

    path = tmp_path / "agentmonitor.db"
    with pytest.raises(ValueError, match="budget_retention_dependencies_required"):
        SqliteBudgetRetentionV1(
            DatabaseRefV1(path, tmp_path),
            transaction_guard=None,
            live_context=None,
            checkpoints=None,
        )
    assert not path.exists()


def test_real_empty_retention_is_audited_without_export(tmp_path: Path) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )
    from agentmonitor.composition.budget_retention import build_budget_retention
    from agentmonitor.contracts.common_v1 import OpaqueIdV1
    from agentmonitor.contracts.operations_v1 import OperationsParticipantRequestV1

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    participant = build_budget_retention(ref, tmp_path / "checkpoints")
    now = datetime.now(UTC)
    request = OperationsParticipantRequestV1(
        OpaqueIdV1("empty-retention"),
        OpaqueIdV1("empty-correlation"),
        now + timedelta(minutes=1),
        1,
        now - timedelta(days=365),
        1,
        None,
        None,
        None,
        None,
    )
    preview = participant.preview_expired(request)
    assert preview.count == 0 and preview.next_cursor is None
    prepared = replace(request, preview_digest=preview.digest)
    result = participant.purge_expired(prepared)
    assert result.count == 0 and result.outcome == "complete"
    assert participant.purge_expired(prepared) == result
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT batch_count,export_checkpoint_ref,state "
                "FROM capacity_retention_run"
            ).one()
            assert tuple(row) == (0, None, "completed")
    assert tuple((tmp_path / "checkpoints").glob("*.zip")) == ()
