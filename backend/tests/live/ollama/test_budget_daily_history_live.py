"""Page genuine stored facts in disposable copies; no provider calls or seeding."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryQueryV1,
    BudgetHistoryRowV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, BudgetReportViewV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.budget_selected import (
    GetSelectedBudgetReportV1,
)
from agentmonitor.modules.registry.application.accounts import GetAccountV1

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def _reports(
    reference: DatabaseRefV1, as_of: datetime
) -> tuple[BudgetReportViewV1, ...]:
    runs = SqliteCollectionRepositoryV1(reference).list_runs("ollama", None, as_of, 500)
    repository = SqliteBudgetReportRepositoryV1(reference)
    found = []
    for run in runs:
        if (
            isinstance(run, BudgetCollectionRunViewV1)
            and run.source_id == "ollama.cloud.usage.v1"
            and run.state == "succeeded"
            and run.report_id is not None
            and run.account_id is not None
        ):
            stored = repository.get_report(run.account_id, run.report_id)
            if stored is not None and stored.report.usage_buckets:
                found.append(stored)
    assert found, "genuine_stored_usage_report_required"
    return tuple(found)


def _query(stored: BudgetReportViewV1, as_of: datetime) -> BudgetHistoryQueryV1:
    return BudgetHistoryQueryV1(
        stored.report.subject.account_id,
        stored.report.subject.resource_id,
        stored.report_id,
        stored.report.requested_period,
        as_of,
        limit=1,
    )


def test_genuine_history_pages_exact_retained_usage_without_changing_selection(
    tmp_path: Path,
) -> None:
    from agentmonitor.modules.capacity.application.budget_history import (
        ListBudgetHistoryV1,
    )

    reference = _private_real_copy(tmp_path)
    now = datetime.now(UTC)
    stored = _reports(reference, now)[0]
    selected = GetSelectedBudgetReportV1(
        GetAccountV1(SqliteRegistryRepositoryV1(reference)),
        SqliteBudgetReportRepositoryV1(reference),
    )
    history = ListBudgetHistoryV1(selected)
    query = _query(stored, now)
    rows: list[BudgetHistoryRowV1] = []
    while True:
        result = history(query)
        assert result is not None, "genuine_history_selection_missing"
        assert result.report == stored
        assert result.as_of == now
        assert len(result.page.items) == 1
        rows.extend(result.page.items)
        assert len(rows) <= len(stored.report.cost_buckets) + len(
            stored.report.usage_buckets
        )
        if not result.page.has_more:
            assert result.page.next_key is None
            break
        assert result.page.next_key is not None
        query = replace(query, after_key=result.page.next_key)
    assert tuple(row.usage for row in rows if row.usage is not None) == tuple(
        sorted(
            stored.report.usage_buckets,
            key=lambda bucket: (
                bucket.period.start,
                bucket.period.end,
                bucket.bucket_key,
            ),
        )
    )
    assert tuple(row.cost for row in rows if row.cost is not None) == tuple(
        sorted(
            stored.report.cost_buckets,
            key=lambda bucket: (
                bucket.period.start,
                bucket.period.end,
                bucket.bucket_key,
            ),
        )
    )
    assert (
        SqliteBudgetReportRepositoryV1(reference).get_report(
            query.account_id, query.report_id
        )
        == stored
    )


def test_removed_selected_report_does_not_fall_back_to_another_real_report(
    tmp_path: Path,
) -> None:
    from agentmonitor.modules.capacity.application.budget_history import (
        ListBudgetHistoryV1,
    )

    reference = _private_real_copy(tmp_path)
    now = datetime.now(UTC)
    reports = _reports(reference, now)
    pairs = [
        (first, other)
        for first in reports
        for other in reports
        if first.report_id != other.report_id
        and first.report.subject == other.report.subject
        and first.report.requested_period == other.report.requested_period
    ]
    assert pairs, "genuine_alternative_report_required"
    stored, alternative = pairs[0]
    repository = SqliteBudgetReportRepositoryV1(reference)
    history = ListBudgetHistoryV1(
        GetSelectedBudgetReportV1(
            GetAccountV1(SqliteRegistryRepositoryV1(reference)), repository
        )
    )
    query = _query(stored, now)
    first = history(query)
    assert first is not None and first.page.next_key is not None
    next_query = replace(query, after_key=first.page.next_key)
    assert history(replace(query, resource_id=OpaqueIdV1("unrelated-resource"))) is None
    assert history(replace(query, account_id=OpaqueIdV1("unrelated-account"))) is None
    assert (
        history(replace(query, as_of=stored.stored_at - timedelta(microseconds=1)))
        is None
    )
    assert (
        history(
            replace(
                query,
                period=BudgetPeriodV1(
                    query.period.start - timedelta(days=7),
                    query.period.end - timedelta(days=7),
                ),
            )
        )
        is None
    )
    with pytest.raises(ValueError, match="budget_history_cursor_invalid"):
        history(replace(next_query, as_of=now + timedelta(seconds=1)))
    # M05-owned SQLite test boundary in a disposable genuine snapshot only.
    # This proves disappearance between pages, not the future retention policy.
    with open_sqlite_database(reference, "runtime_read_write") as database:
        with database.connect() as connection:
            with connection.begin():
                removed = connection.exec_driver_sql(
                    "DELETE FROM capacity_budget_report "
                    "WHERE account_id=? AND report_id=?",
                    (query.account_id.value, query.report_id.value),
                )
                assert removed.rowcount == 1
    assert repository.get_report(query.account_id, query.report_id) is None
    assert (
        repository.get_report(
            alternative.report.subject.account_id, alternative.report_id
        )
        == alternative
    )
    assert history(next_query) is None
    assert history(query) is None
