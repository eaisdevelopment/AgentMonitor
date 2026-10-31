"""M05 provider-neutral ingestion checks before persistence."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    CapacityCommitReceiptV1,
    CapacityCommitRequestV1,
    InvalidCapacityContractV1,
    ProviderQuotaInputV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunAdmissionV1,
)
from agentmonitor.contracts.common_v1 import TechnicalValueV1
from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1
from agentmonitor.modules.capacity.application.commit import (
    CommitCapacityCollectionOutcomeV1,
)
from agentmonitor.modules.capacity.domain.payload_digest import (
    capacity_payload_digest,
)


class PrepareCapacityCollectionOutcomeV1[SourceT: TechnicalValueV1]:
    """Translate one typed M03 outcome into the M04/M05 commit boundary."""

    def __init__(
        self,
        normalize: Callable[
            [SourceT, CollectionRunAdmissionV1],
            object,
        ],
    ) -> None:
        self._normalize = normalize

    def __call__(
        self,
        admission: CollectionRunAdmissionV1,
        outcome: CollectionOutcomeV1[SourceT],
        completed_at: datetime,
    ) -> CapacityCommitRequestV1 | CollectionFailedV1:
        if outcome.state not in {"success", "partial"}:
            assert outcome.error is not None
            terminal_state: Literal["failed", "blocked", "unsupported"] = (
                "unsupported"
                if outcome.state == "unsupported"
                else "blocked"
                if outcome.state
                in {
                    "unverified_provider_version",
                    "reauthentication_required",
                    "authorization_insufficient",
                    "blocked_user_action_required",
                }
                else "failed"
            )
            return CollectionFailedV1(
                run_id=admission.run_id,
                terminal_state=terminal_state,
                error_code=outcome.error.code,
                completed_at=completed_at,
            )
        assert outcome.value is not None and outcome.provenance is not None
        normalized = self._normalize(outcome.value, admission)
        if not isinstance(normalized, ProviderQuotaInputV1):
            raise InvalidCapacityContractV1("capacity_normalizer_result_invalid")
        if outcome.state == "partial":
            omission_codes = tuple(
                sorted(
                    {item.code for item in outcome.omissions}
                    | {item.code for item in outcome.warnings}
                )
            )
            normalized = replace(
                normalized,
                completeness="partial_scope",
                omission_codes=omission_codes,
            )
        return CapacityCommitRequestV1(
            run_id=admission.run_id,
            target_generation=admission.target_generation,
            capability_id=admission.capability_id,
            payload_schema=admission.payload_schema,
            payload_digest=capacity_payload_digest(normalized),
            terminal_state=("partial" if outcome.state == "partial" else "succeeded"),
            payload=normalized,
            provenance=outcome.provenance,
        )


class IngestCapacityCollectionV1:
    def __init__(self, commit: CommitCapacityCollectionOutcomeV1) -> None:
        self._commit = commit

    def __call__(self, request: CapacityCommitRequestV1) -> CapacityCommitReceiptV1:
        payload = request.payload
        provenance = request.provenance
        if (
            payload.subject.provider_key != provenance.provider_key
            or request.capability_id != provenance.capability_id
            or payload.capability_schema_version != provenance.capability_schema_version
        ):
            raise InvalidCapacityContractV1("capacity_provenance_mismatch")
        return self._commit(request)
