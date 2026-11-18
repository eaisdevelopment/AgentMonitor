"""Assert a recent real owner-selected billing check, without reading secrets."""

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
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.live.billing.test_m7_native_cost_comparison import LIVE, _runtime
from backend.tests.live.ollama.test_budget_monetary_persistence import _require


def test_recent_real_billing_check_commits_provider_report() -> None:
    """Manual Check connection must produce a report before monitoring can start."""
    expected = os.environ.get("AGENTMONITOR_M7_EXPECTED_REVISION", "")
    run_id = os.environ.get("AGENTMONITOR_M7_CHECK_RUN_ID", "")
    _require(re.fullmatch("[a-f0-9]{40}", expected) is not None, "revision_required")
    _require(
        re.fullmatch("billing-check-run-[a-f0-9]{40}", run_id) is not None,
        "real_connection_check_required",
    )
    _runtime(expected)
    reference = DatabaseRefV1(LIVE / "agentmonitor.db", LIVE)
    run = SqliteCollectionRepositoryV1(reference).get_run(OpaqueIdV1(run_id))
    _require(isinstance(run, BudgetCollectionRunViewV1), "billing_check_required")
    assert isinstance(run, BudgetCollectionRunViewV1)
    now = datetime.now(UTC)
    _require(
        timedelta(0) <= now - run.requested_at <= timedelta(minutes=5),
        "fresh_connection_check_required",
    )
    _require(
        run.state == "succeeded",
        "recent_billing_check_did_not_succeed",
    )
    _require(
        run.report_id is not None and run.account_id is not None,
        "billing_check_report_missing",
    )
    assert run.report_id is not None and run.account_id is not None
    stored = SqliteBudgetReportRepositoryV1(reference).get_report(
        run.account_id, run.report_id
    )
    _require(stored is not None, "billing_check_committed_report_missing")
    assert stored is not None
    _require(
        stored.report.subject.account_id == run.account_id
        and stored.report.subject.resource_id == run.resource_id
        and stored.report.completeness == "complete",
        "billing_check_report_authority_mismatch",
    )
    print("M7 RECENT BILLING CHECK: complete real report committed")
