"""The real local task records an empty cycle without provider/browser activity."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_inspection,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)

from backend.tests.integration.api.test_iam_http import _installation


def test_dashboard_owns_the_retention_background_task(tmp_path: Path) -> None:
    from agentmonitor.composition.budget_retention import BudgetRetentionTaskV1

    app, _ = _installation(tmp_path)
    owners = [
        getattr(task, "__self__", None) for task in app.state.lifecycle.hooks.tasks
    ]
    assert sum(isinstance(owner, BudgetRetentionTaskV1) for owner in owners) == 1


def test_unsafe_retention_directory_does_not_prevent_dashboard_creation(
    tmp_path: Path,
) -> None:
    from agentmonitor.composition.budget_retention import BudgetRetentionTaskV1

    directory = tmp_path / "budget-retention"
    directory.mkdir(mode=0o755)
    directory.chmod(0o755)
    app, _ = _installation(tmp_path)
    task = next(
        owner
        for callback in app.state.lifecycle.hooks.tasks
        if isinstance(
            owner := getattr(callback, "__self__", None), BudgetRetentionTaskV1
        )
    )
    with pytest.raises(ValueError, match="budget_checkpoint_directory_unsafe"):
        task.run_once()
    assert task.last_error == "budget_retention_batch_failed"
    assert not tuple(directory.iterdir())


def test_background_task_records_real_empty_retention_cycle(tmp_path: Path) -> None:
    from agentmonitor.composition.budget_retention import BudgetRetentionTaskV1

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    task = BudgetRetentionTaskV1(reference, tmp_path / "retention")
    before = datetime.now(UTC)

    async def exercise() -> None:
        running = asyncio.create_task(task.run())
        try:
            async with asyncio.timeout(15):
                while task.last_receipt is None:
                    await asyncio.sleep(0.05)
            assert task.last_receipt.outcome == "complete"
            assert task.last_receipt.count == 0
            assert task.last_error is None
        finally:
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)

    asyncio.run(exercise())
    after = datetime.now(UTC)
    with open_sqlite_inspection(reference) as connection:
        rows = connection.exec_driver_sql(
            "SELECT cutoff_at,batch_count,export_checkpoint_ref,state,completed_at "
            "FROM capacity_retention_run"
        ).all()
        assert len(rows) == 1
        cutoff = datetime.fromisoformat(rows[0][0])
        assert before - timedelta(days=365) <= cutoff <= after - timedelta(days=365)
        assert rows[0][1:4] == (0, None, "completed")
        assert before <= datetime.fromisoformat(rows[0][4]) <= after
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM collection_run"
            ).scalar_one()
            == 0
        )
    assert list((tmp_path / "retention").glob("*.zip")) == []
