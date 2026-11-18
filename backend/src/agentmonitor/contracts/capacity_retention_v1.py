"""Bounded M05 financial exports and the M7 subset of CTR-OPS-007.

No file paths, secret material or database handles cross these ports. The export
retains the original identities; import/restore is outside this M7 increment.
"""

from dataclasses import dataclass
from typing import ClassVar, Protocol

from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionReceiptV1
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1


@dataclass(frozen=True, slots=True)
class BudgetRetentionExportRecordV1(TechnicalValueV1):
    """An original report and ordered fact identities, never a re-collected copy.

    Fact order is the original receipt order: costs, then usage. Shared budget
    definitions and provenance rows are not deleted by financial retention.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-002"
    CONTRACT_VERSION: ClassVar[str] = "2.2.0"
    OWNER: ClassVar[str] = "PLAN-M05"
    report_sequence: int
    report: BudgetReportViewV1
    provenance: ObservationProvenanceV1
    receipt: BudgetCollectionReceiptV1
    receipt_id: OpaqueIdV1
    provenance_id: OpaqueIdV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.report_sequence) is not int
            or not 1 <= self.report_sequence <= 9223372036854775807
            or not isinstance(self.report, BudgetReportViewV1)
            or not isinstance(self.provenance, ObservationProvenanceV1)
            or not isinstance(self.receipt, BudgetCollectionReceiptV1)
            or not isinstance(self.receipt_id, OpaqueIdV1)
            or not isinstance(self.provenance_id, OpaqueIdV1)
        ):
            raise ValueError("budget_retention_export_invalid")
        payload = self.report.report
        if (
            self.report.report_id != self.receipt.report_id
            or self.report.stored_at != self.receipt.stored_at
            or len(self.receipt.fact_ids)
            != len(payload.cost_buckets) + len(payload.usage_buckets)
            or self.provenance.source_id != payload.source_id
            or self.provenance.provider_key != payload.subject.provider_key
            or self.provenance.collected_at != payload.collected_at
            or self.provenance.capability_id != self.receipt.capability_id
            or self.receipt.consumer_key != "capacity.budget"
        ):
            raise ValueError("budget_retention_export_invalid")


class BudgetRetentionRecordCodecV1(Protocol):
    """M05 owns the closed financial export schema consumed by M08 storage."""

    CONTRACT_ID: ClassVar[str] = "CTR-CAP-002"
    CONTRACT_VERSION: ClassVar[str] = "2.2.0"
    OWNER: ClassVar[str] = "PLAN-M05"

    def encode(self, record: BudgetRetentionExportRecordV1) -> bytes: ...

    def decode(self, payload: bytes) -> BudgetRetentionExportRecordV1: ...
