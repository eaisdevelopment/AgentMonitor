"""M7-T008/T015: one actual selected grouped collection and its stored receipt."""

import os
import re
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetAuthorityV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)

from backend.tests.live.billing.test_m7_native_cost_comparison import LIVE, _runtime
from backend.tests.live.ollama.test_budget_monetary_persistence import _require


def test_recent_real_openai_key_grouped_collection_commits_matching_report() -> None:
    """Read one real manual action; never collect, configure or replay its source."""
    expected = os.environ.get("AGENTMONITOR_M7_EXPECTED_REVISION", "")
    run_id = os.environ.get("AGENTMONITOR_M7_COLLECT_RUN_ID", "")
    _require(re.fullmatch("[a-f0-9]{40}", expected) is not None, "revision_required")
    _require(
        re.fullmatch("billing-collect-run-[a-f0-9]{40}", run_id) is not None,
        "real_grouped_collection_required",
    )
    _runtime(expected)
    reference = DatabaseRefV1(LIVE / "agentmonitor.db", LIVE)
    runs = SqliteCollectionRepositoryV1(reference)
    run = runs.get_run(OpaqueIdV1(run_id))
    _require(isinstance(run, BudgetCollectionRunViewV1), "billing_collection_required")
    assert isinstance(run, BudgetCollectionRunViewV1)
    target = runs.get_budget_target(run.run_id)
    _require(isinstance(target, BillingBudgetAuthorityV1), "billing_authority_required")
    assert isinstance(target, BillingBudgetAuthorityV1)
    _require(
        run.provider_key == "codex"
        and target.report_context.source_category == "cost"
        and target.report_context.grouping == ("api_key_id",),
        "selected_grouped_context_required",
    )
    _require(
        timedelta(0) <= datetime.now(UTC) - run.requested_at <= timedelta(hours=1),
        "recent_collection_required",
    )
    _require(run.state == "succeeded", "grouped_collection_did_not_succeed")
    _require(
        run.report_id is not None and run.account_id is not None,
        "grouped_collection_report_missing",
    )
    assert run.report_id is not None and run.account_id is not None
    reports = SqliteBudgetReportRepositoryV1(reference)
    stored = reports.get_report(run.account_id, run.report_id)
    _require(stored is not None, "grouped_collection_storage_missing")
    assert stored is not None
    report = stored.report
    _require(
        report.subject.account_id == run.account_id
        and report.subject.resource_id == run.resource_id
        and report.source_category == target.report_context.source_category
        and report.grouping == target.report_context.grouping
        and report.requested_period.start == target.report_context.interval_start
        and report.requested_period.end == target.report_context.interval_end
        and report.completeness == "complete"
        and budget_report_payload_digest(report) == run.payload_digest,
        "grouped_collection_report_mismatch",
    )
    status = reports.get_commit_status(run.run_id, run.capability_id)
    _require(
        status.state == "committed"
        and status.receipt is not None
        and status.receipt.report_id == run.report_id
        and status.receipt.payload_digest == run.payload_digest,
        "grouped_collection_receipt_mismatch",
    )
