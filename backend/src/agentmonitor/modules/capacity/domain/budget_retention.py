"""Pure fixed-cutoff and scan identity for bounded financial retention."""

import base64
import hashlib
import json
from datetime import datetime

from agentmonitor.contracts.capacity_retention_v1 import BudgetRetentionExportRecordV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import OperationsParticipantRequestV1
from agentmonitor.modules.capacity.domain.budget_codec import utc_text

POLICY_ID = "budget_reports_365_days"
POLICY_VERSION = "1.0.0"


def referenced_report(
    fact_ids: tuple[OpaqueIdV1, ...], references: tuple[OpaqueIdV1, ...]
) -> bool:
    """A reference protects the entire immutable report, not only one fact."""
    return not set(fact_ids).isdisjoint(references)


def original_fact_values(
    record: BudgetRetentionExportRecordV1, index: int
) -> dict[str, object]:
    """Exact parent shape produced by the original budget report writer."""
    report, receipt, provenance = (
        record.report.report,
        record.receipt,
        record.provenance,
    )
    values: dict[str, object] = dict(
        account_id=report.subject.account_id.value,
        resource_id=report.subject.resource_id.value,
        project_id=None,
        workspace_id=None,
        collected_at=utc_text(report.collected_at),
        stored_at=utc_text(record.report.stored_at),
        completeness=report.completeness,
        provenance_id=record.provenance_id.value,
        collection_run_id=receipt.run_id.value,
        payload_digest=receipt.payload_digest,
        capability_schema_version=provenance.capability_schema_version,
        observed_at=utc_text(provenance.observed_at)
        if provenance.observed_at
        else None,
        data_through_end=utc_text(report.source_data_through)
        if report.source_data_through
        else None,
    )
    if index < len(report.cost_buckets):
        bucket = report.cost_buckets[index]
        identity = json.dumps(
            [
                report.subject.provider_key,
                report.subject.account_id.value,
                report.subject.resource_id.value,
                report.scope_id.value if report.scope_id else None,
                report.scope_generation,
                report.source_id,
                report.source_category,
                report.cost_basis,
                report.currency,
                report.grouping,
            ],
            separators=(",", ":"),
        )
        values.update(
            observation_id=receipt.fact_ids[index].value,
            budget_definition_id=hashlib.sha256(identity.encode()).hexdigest(),
            definition_version=1,
            observation_kind="cost_bucket",
            billing_start=utc_text(bucket.period.start),
            billing_end=utc_text(bucket.period.end),
            enforcement_state="not_applicable",
            enforcement_code=None,
            current_candidate=0,
            invalidation_reason=None,
        )
    else:
        usage = report.usage_buckets[index - len(report.cost_buckets)]
        values.update(
            bucket_id=receipt.fact_ids[index].value,
            bucket_start=utc_text(usage.period.start),
            bucket_end=utc_text(usage.period.end),
        )
    return values


def expired_report(stored_at: datetime, period_end: datetime, cutoff: datetime) -> bool:
    return stored_at < cutoff and period_end < cutoff


def request_identity(request: OperationsParticipantRequestV1) -> str:
    if request.cutoff is None:
        raise ValueError("budget_retention_cutoff_required")
    return json.dumps(
        [
            POLICY_ID,
            POLICY_VERSION,
            request.operation_id.value,
            utc_text(request.cutoff),
            request.limit,
        ],
        separators=(",", ":"),
    )


def retention_cursor(
    request: OperationsParticipantRequestV1, snapshot: int, last: int
) -> str:
    if not 0 <= last <= snapshot <= 9223372036854775807:
        raise ValueError("budget_retention_cursor_invalid")
    raw = hashlib.sha256(request_identity(request).encode()).digest()[:16]
    raw += snapshot.to_bytes(8) + last.to_bytes(8)
    return "br1_" + base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def retention_position(
    request: OperationsParticipantRequestV1,
) -> tuple[int, int] | None:
    request_identity(request)
    if request.cursor is None:
        return None
    try:
        if not request.cursor.startswith("br1_") or len(request.cursor) != 47:
            raise ValueError
        raw = base64.b64decode(request.cursor[4:] + "=", altchars=b"-_", validate=True)
        snapshot, last = int.from_bytes(raw[16:24]), int.from_bytes(raw[24:])
        if (
            len(raw) != 32
            or retention_cursor(request, snapshot, last) != request.cursor
        ):
            raise ValueError
        return snapshot, last
    except (ValueError, TypeError):
        raise ValueError("budget_retention_cursor_invalid") from None
