"""Pure M05 V2 cloud-target contracts; no provider or persistence I/O."""

from dataclasses import replace

import pytest
from agentmonitor.contracts.capacity_v1 import (
    CapacityHistoryPointV2,
    CapacitySubjectV2,
    ExactMetricFieldV1,
    InvalidCapacityContractV1,
    ProviderQuotaInputV2,
    ProviderQuotaWindowInputV1,
    QuotaWindowViewV2,
)
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1
from agentmonitor.modules.capacity.domain.payload_digest import capacity_payload_digest


def _unknown(reason: str) -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        availability=FieldAvailabilityV1("unknown"),
        value=None,
        precision="unknown",
        confidence="unknown",
        value_kind="unknown",
        reason_code=reason,
    )


def test_cloud_capacity_subject_is_not_a_provider_installation() -> None:
    subject = CapacitySubjectV2(
        provider_key="ollama",
        provider_target=ProviderTargetRefV1(
            target_kind="cloud_service",
            target_id=OpaqueIdV1("amat_" + "a" * 32),
        ),
        account_id=OpaqueIdV1("account-1"),
        resource_id=OpaqueIdV1("resource-1"),
    )
    payload = ProviderQuotaInputV2(
        subject=subject,
        registry_revision=1,
        capability_schema_version="2.0.0",
        completeness="partial_scope",
        windows=(
            ProviderQuotaWindowInputV1(
                window_key="purchased_credits",
                safe_label="Purchased credits",
                semantic_role="purchased_credits",
                is_constraining=False,
                used=_unknown("not_reported"),
                remaining=_unknown("not_reported"),
                limit=_unknown("not_applicable"),
                remaining_ratio=_unknown("not_applicable"),
                reset_at=None,
                reset_precision="unknown",
            ),
        ),
        omission_codes=("cloud_scope_unresolved",),
    )

    assert payload.subject.provider_target.target_kind == "cloud_service"
    assert QuotaWindowViewV2.CONTRACT_VERSION == "2.0.0"
    assert CapacityHistoryPointV2.CONTRACT_VERSION == "2.0.0"
    assert len(capacity_payload_digest(payload)) == 64
    with pytest.raises(InvalidCapacityContractV1, match="capacity_subject_invalid"):
        replace(subject, account_id=None)  # type: ignore[arg-type]
    with pytest.raises(InvalidCapacityContractV1, match="capacity_subject_invalid"):
        replace(subject, provider_target="cloud_service")  # type: ignore[arg-type]
