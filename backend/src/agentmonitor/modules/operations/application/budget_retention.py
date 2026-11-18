"""One bounded export-before-purge financial retention batch through public ports."""

from dataclasses import replace
from datetime import UTC, datetime

from agentmonitor.contracts.operations_v1 import (
    BudgetRetentionCheckpointPortV1,
    BudgetRetentionParticipantV1,
    OperationsParticipantReceiptV1,
    OperationsParticipantRequestV1,
)


def run_budget_retention_batch(
    request: OperationsParticipantRequestV1,
    participant: BudgetRetentionParticipantV1,
    checkpoints: BudgetRetentionCheckpointPortV1,
) -> OperationsParticipantReceiptV1:
    """No deletion is dispatched until the exact preview has a verified export."""
    if (
        request.limit != 1
        or request.cutoff is None
        or request.prepared_database_ref is not None
        or request.checkpoint_id is not None
        or request.preview_digest is not None
        or request.deadline <= datetime.now(UTC)
    ):
        raise ValueError("budget_retention_request_invalid")
    recovered = checkpoints.find_prepared(request)
    if recovered is not None:
        if (
            replace(recovered, preview_digest=None, checkpoint_id=None) != request
            or recovered.preview_digest is None
            or recovered.checkpoint_id is None
            or request.deadline <= datetime.now(UTC)
        ):
            raise ValueError("budget_retention_recovery_invalid")
        result = participant.purge_expired(recovered)
        if (
            result.operation_id != request.operation_id
            or result.outcome in {"complete", "partial"}
            and (result.count != 1 or result.digest != recovered.preview_digest)
        ):
            raise ValueError("budget_retention_result_invalid")
        return result
    preview = participant.preview_expired(request)
    if preview.operation_id != request.operation_id:
        raise ValueError("budget_retention_preview_invalid")
    if preview.outcome not in {"complete", "partial"}:
        return preview
    if preview.count is None or not 0 <= preview.count <= 1 or preview.digest is None:
        raise ValueError("budget_retention_preview_invalid")
    prepared = replace(request, preview_digest=preview.digest)
    if preview.count:
        records = participant.query_export_records(prepared)
        if len(records) != preview.count:
            raise ValueError("budget_retention_export_changed")
        checkpoint_id = checkpoints.store(prepared, records)
        prepared = replace(prepared, checkpoint_id=checkpoint_id)
        if not checkpoints.verify(prepared, records):
            raise ValueError("budget_retention_checkpoint_unverified")
    if request.deadline <= datetime.now(UTC):
        raise ValueError("budget_retention_deadline_exceeded")
    result = participant.purge_expired(prepared)
    if (
        result.operation_id != request.operation_id
        or result.participant_key != preview.participant_key
        or result.outcome in {"complete", "partial"}
        and (result.count != preview.count or result.digest != preview.digest)
    ):
        raise ValueError("budget_retention_result_invalid")
    return result
