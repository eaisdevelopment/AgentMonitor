"""Pure account and capacity conversion for one Ollama cloud reading."""

from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    CapacitySubjectV1,
    CapacitySubjectV2,
    ProviderQuotaInputV1,
    ProviderQuotaInputV2,
)
from agentmonitor.contracts.providers.ollama.cloud_balance.v1.schema import (
    OllamaCloudBalanceV1,
    to_capacity_windows,
)
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1


def validate_cloud_target(
    lease_account: str, binding_account: str, subject_account: str, provider: str
) -> None:
    if (
        not lease_account
        or lease_account != binding_account
        or lease_account != subject_account
        or provider != "ollama"
    ):
        raise ValueError("ollama_cloud_target_mismatch")


def validate_cloud_provider_target(
    run_target: ProviderTargetRefV1, subject_target: ProviderTargetRefV1
) -> None:
    """Never relabel one cloud service target as another."""
    if run_target.target_kind != "cloud_service" or run_target != subject_target:
        raise ValueError("ollama_cloud_target_mismatch")


def cloud_balance_to_capacity(
    balance: OllamaCloudBalanceV1,
    subject: CapacitySubjectV1 | CapacitySubjectV2,
    registry_revision: int,
) -> ProviderQuotaInputV1 | ProviderQuotaInputV2:
    """Retain unknown scope and never retire windows on an incomplete source."""
    if subject.provider_key != "ollama":
        raise ValueError("ollama_cloud_target_mismatch")
    projection = to_capacity_windows(balance)
    if isinstance(subject, CapacitySubjectV2):
        return ProviderQuotaInputV2(
            subject,
            registry_revision,
            "1.0.0",
            "partial_scope",
            projection.windows,
            ("cloud_scope_unresolved",),
        )
    return ProviderQuotaInputV1(
        subject,
        registry_revision,
        "1.0.0",
        "partial_scope",
        projection.windows,
        ("cloud_scope_unresolved",),
    )


def admission_outcome_for_source(
    state: str,
) -> Literal["succeeded", "rate_limited", "failed"]:
    if state == "success":
        return "succeeded"
    if state == "rate_limited":
        return "rate_limited"
    return "failed"


def no_response_reason_for_source(
    state: str, reason_code: str
) -> Literal[
    "credential_update_in_progress", "store_unavailable", "source_not_started"
]:
    """Preserve temporary local contention without exposing store internals."""
    if (
        state == "authorization_unavailable"
        and reason_code == "ollama_cloud_store_locked"
    ):
        return "credential_update_in_progress"
    if state == "authorization_unavailable":
        return "store_unavailable"
    return "source_not_started"


def eligible_cloud_account(
    provider: str, lifecycle: str, effective_monitoring: bool, identity_state: str
) -> bool:
    """Do not schedule archived, disabled or unassociated accounts."""
    return (
        provider == "ollama"
        and lifecycle == "active"
        and effective_monitoring is True
        and identity_state in {"owner_confirmed", "matched"}
    )


def cloud_failure_policy(state: str, retry_after: int | None):
    """Map closed source failure categories to actionable M04 retry policy."""
    from agentmonitor.contracts.collection_control_v1 import CollectionFailurePolicyV1
    from agentmonitor.contracts.provider_system_v1 import RetryAdviceV1

    if state == "authorization_unavailable":
        return CollectionFailurePolicyV1(
            "blocked_user_action_required", RetryAdviceV1("after_user_action")
        )
    if state == "unauthorized":
        return CollectionFailurePolicyV1(
            "reauthentication_required", RetryAdviceV1("after_reauthentication")
        )
    if state == "access_denied":
        return CollectionFailurePolicyV1(
            "authorization_insufficient", RetryAdviceV1("after_user_action")
        )
    if state == "rate_limited":
        delay = max(1, retry_after if retry_after is not None else 60)
        precision: Literal["exact", "estimated"] = (
            "exact" if retry_after is not None and retry_after >= 1 else "estimated"
        )
        return CollectionFailurePolicyV1(
            "rate_limited", RetryAdviceV1("after_delay", delay, precision)
        )
    if state in {"provider_unavailable", "deadline_exceeded"}:
        outcome: Literal["deadline_exceeded", "provider_unavailable"] = (
            "deadline_exceeded"
            if state == "deadline_exceeded"
            else "provider_unavailable"
        )
        return CollectionFailurePolicyV1(
            outcome, RetryAdviceV1("after_delay", 60, "estimated")
        )
    if state in {"invalid_provider_data", "unexpected_response"}:
        return CollectionFailurePolicyV1(
            "invalid_provider_data", RetryAdviceV1("after_version_review")
        )
    return CollectionFailurePolicyV1(
        "internal_adapter_error", RetryAdviceV1("after_user_action")
    )
