"""Pure export identity rules; constructed values never cross an I/O boundary."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Literal

import pytest
from agentmonitor.contracts.capacity_retention_v1 import BudgetRetentionExportRecordV1
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionReceiptV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.capacity.pure.test_budget_commit_policy import pure_request


def _record() -> BudgetRetentionExportRecordV1:
    request = pure_request()
    view = BudgetReportViewV1(
        OpaqueIdV1("pure-report"), request.payload, request.payload.collected_at
    )
    receipt = BudgetCollectionReceiptV1(
        request.run_id,
        request.target_generation,
        request.capability_id,
        request.payload_schema,
        request.payload_digest,
        "capacity.budget",
        "1.0.0",
        view.report_id,
        (OpaqueIdV1("pure-cost"), OpaqueIdV1("pure-usage")),
        view.stored_at,
        1,
    )
    return BudgetRetentionExportRecordV1(
        1,
        view,
        request.provenance,
        receipt,
        OpaqueIdV1("pure-receipt"),
        OpaqueIdV1("pure-provenance"),
    )


def test_export_preserves_original_report_receipt_and_ordered_fact_ids() -> None:
    record = _record()
    assert record.report.report_id == record.receipt.report_id
    assert record.receipt.fact_ids == (
        OpaqueIdV1("pure-cost"),
        OpaqueIdV1("pure-usage"),
    )


@pytest.mark.parametrize("sequence", [0, -1, True])
def test_export_requires_original_positive_storage_sequence(sequence: int) -> None:
    with pytest.raises(ValueError, match="budget_retention_export_invalid"):
        replace(_record(), report_sequence=sequence)


def test_export_rejects_different_report_or_missing_fact_identity() -> None:
    record = _record()
    for receipt in (
        replace(record.receipt, report_id=OpaqueIdV1("different-report")),
        replace(record.receipt, fact_ids=()),
    ):
        with pytest.raises(ValueError, match="budget_retention_export_invalid"):
            replace(record, receipt=receipt)


def test_export_rejects_provenance_from_another_collection() -> None:
    record = _record()
    with pytest.raises(ValueError, match="budget_retention_export_invalid"):
        replace(record, provenance=replace(record.provenance, source_id="other"))


@pytest.mark.parametrize("outcome", ["complete", "partial"])
def test_successful_retention_receipt_has_a_truthful_reason(
    outcome: Literal["complete", "partial"],
) -> None:
    from agentmonitor.contracts.operations_v1 import OperationsParticipantReceiptV1

    receipt = OperationsParticipantReceiptV1(
        "capacity",
        OpaqueIdV1("pure-retention"),
        outcome,
        1,
        "a" * 64,
        1,
        None,
        datetime(2026, 11, 12, tzinfo=UTC),
        "operations_retention_batch_" + outcome,
    )
    assert receipt.outcome == outcome
