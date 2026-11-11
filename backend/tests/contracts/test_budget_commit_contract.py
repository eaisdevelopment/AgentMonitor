"""Pure M7 receipt policy: constructed values never cross I/O boundaries."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from agentmonitor.contracts import collection_control_v1 as contracts
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportHistoryQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def _receipt() -> contracts.BudgetCollectionReceiptV1:
    assert hasattr(contracts, "BudgetCollectionReceiptV1"), (
        "budget coverage cannot be acknowledged without fictitious observations"
    )
    return contracts.BudgetCollectionReceiptV1(
        run_id=OpaqueIdV1("pure-run"),
        target_generation=1,
        capability_id="api.billing",
        payload_schema="budget.report.v1",
        payload_digest="a" * 64,
        consumer_key="capacity.budget",
        consumer_version="1.0.0",
        report_id=OpaqueIdV1("pure-report"),
        fact_ids=(),
        stored_at=datetime(2026, 11, 11, tzinfo=UTC),
        receipt_version=1,
    )


def test_empty_report_receipt_requires_real_report_not_fabricated_facts() -> None:
    receipt = _receipt()
    assert receipt.fact_ids == ()
    assert receipt.report_id == OpaqueIdV1("pure-report")
    with pytest.raises(ValueError, match="budget_receipt_invalid"):
        replace(receipt, report_id=None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"target_generation": 0},
        {"receipt_version": True},
        {"payload_digest": "invalid"},
        {"consumer_key": ""},
        {"fact_ids": (OpaqueIdV1("duplicate"), OpaqueIdV1("duplicate"))},
        {"fact_ids": ("untyped",)},
        {"stored_at": "not-a-timestamp"},
    ],
)
def test_budget_receipt_rejects_ambiguous_commit_identity(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="budget_receipt_invalid"):
        replace(_receipt(), **changes)


def test_budget_commit_status_cannot_claim_success_without_receipt() -> None:
    receipt = _receipt()
    status_type = contracts.BudgetCollectionCommitStatusV1
    assert status_type("committed", receipt).receipt == receipt
    assert status_type("not_committed", None).receipt is None
    with pytest.raises(ValueError, match="budget_commit_status_invalid"):
        status_type("committed", None)
    with pytest.raises(ValueError, match="budget_commit_status_invalid"):
        status_type("conflict", receipt)


@pytest.mark.parametrize("limit", [0, 201, True])
def test_report_query_cannot_exceed_real_page_bounds(limit: int) -> None:
    with pytest.raises(ValueError, match="budget_history_query_invalid"):
        BudgetReportHistoryQueryV1(
            OpaqueIdV1("pure-account"),
            OpaqueIdV1("pure-resource"),
            BudgetPeriodV1(
                datetime(2026, 11, 1, tzinfo=UTC),
                datetime(2026, 11, 8, tzinfo=UTC),
            ),
            limit=limit,
        )
