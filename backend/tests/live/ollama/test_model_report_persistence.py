"""Genuine grouped reports and context isolation; no provider calls or replay."""

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetCostBucketV1, BudgetUsageBucketV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunViewV1,
    CollectionRunViewV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)

from backend.tests.live.ollama.test_budget_monetary_persistence import _require
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def _retained_runs(
    runs: SqliteCollectionRepositoryV1, as_of: datetime
) -> Iterator[CollectionRunViewV1]:
    """Page genuine history; a busy balance poller must not hide older models."""
    cursor = None
    seen: set[str] = set()
    for _ in range(30):
        page = runs.list_runs("ollama", None, as_of, 500, cursor)
        yield from page
        if len(page) < 500:
            return
        next_cursor = page[-1].run_id.value
        _require(next_cursor not in seen, "model_run_cursor_repeated")
        seen.add(next_cursor)
        cursor = next_cursor
    _require(False, "model_run_scan_limit")


def test_genuine_model_report_context_receipt_and_latest_run_survive_reopen(
    tmp_path: Path,
) -> None:
    reference = _private_real_copy(tmp_path)
    runs = SqliteCollectionRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    now = datetime.now(UTC)
    selected = None
    for run in _retained_runs(runs, now):
        if (
            not isinstance(run, BudgetCollectionRunViewV1)
            or run.source_id != "ollama.cloud.usage.v1"
            or run.report_id is None
            or run.account_id is None
        ):
            continue
        target = runs.get_budget_target(run.run_id)
        if isinstance(target, tuple) and target[2].grouping == ("model",):
            selected = (run, target)
            break
    _require(selected is not None, "genuine_grouped_model_report_required")
    assert selected is not None
    run, target = selected
    graph, _, context = target
    assert run.account_id is not None and run.report_id is not None
    stored = reports.get_report(run.account_id, run.report_id)
    status = reports.get_commit_status(run.run_id, run.capability_id)
    _require(stored is not None, "model_report_missing")
    _require(status.state == "committed", "model_commit_receipt_missing")
    assert stored is not None and status.receipt is not None
    report, receipt = stored.report, status.receipt
    _require(
        report.grouping == context.grouping
        and report.source_category == f"{context.scope}_requests_and_cost"
        and report.requested_period.start == context.interval_start
        and report.requested_period.end == context.interval_end
        and report.subject.account_id == graph.account_id
        and report.subject.resource_id == graph.resource_id
        and report.binding_generation == graph.binding.generation
        and receipt.report_id == run.report_id
        and receipt.payload_digest
        == run.payload_digest
        == budget_report_payload_digest(report),
        "model_captured_context_or_receipt_changed",
    )
    facts: tuple[BudgetCostBucketV1 | BudgetUsageBucketV1, ...] = (
        *report.cost_buckets,
        *report.usage_buckets,
    )
    _require(bool(facts), "genuine_populated_model_report_required")
    for fact in facts:
        _require(
            len(fact.dimensions) == 1
            and fact.dimensions[0].kind == "model"
            and (
                fact.dimensions[0].value is None
                if fact.dimensions[0].is_remainder
                else fact.dimensions[0].value is not None
            ),
            "model_dimension_or_remainder_changed",
        )
    reopened_runs = SqliteCollectionRepositoryV1(reference)
    reopened_reports = SqliteBudgetReportRepositoryV1(reference)
    _require(
        reopened_runs.get_budget_target(run.run_id) == target
        and reopened_reports.get_report(run.account_id, run.report_id) == stored
        and reopened_reports.get_commit_status(run.run_id, run.capability_id) == status,
        "model_context_or_report_changed_after_reopen",
    )
    grouped = reopened_runs.get_latest_budget_run(
        graph.account_id, graph.resource_id, 1, now, report_context=context
    )
    _require(grouped is not None, "model_latest_run_missing")
    assert grouped is not None
    grouped_target = reopened_runs.get_budget_target(grouped.run_id)
    _require(
        isinstance(grouped_target, tuple) and grouped_target[2] == context,
        "model_latest_run_selected_aggregate",
    )
    aggregate_context = replace(context, grouping=())
    aggregate = reopened_runs.get_latest_budget_run(
        graph.account_id, graph.resource_id, 1, now, report_context=aggregate_context
    )
    _require(aggregate is not None, "genuine_matching_aggregate_run_required")
    assert aggregate is not None
    aggregate_target = reopened_runs.get_budget_target(aggregate.run_id)
    _require(
        aggregate.run_id != grouped.run_id
        and isinstance(aggregate_target, tuple)
        and aggregate_target[2] == aggregate_context,
        "aggregate_latest_run_selected_model",
    )
