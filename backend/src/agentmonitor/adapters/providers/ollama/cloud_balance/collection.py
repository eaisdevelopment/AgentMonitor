"""Pure account and capacity conversion for one Ollama cloud reading."""

from agentmonitor.contracts.capacity_v1 import CapacitySubjectV1, ProviderQuotaInputV1
from agentmonitor.contracts.providers.ollama.cloud_balance.v1.schema import (
    OllamaCloudBalanceV1,
    to_capacity_windows,
)


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


def cloud_balance_to_capacity(
    balance: OllamaCloudBalanceV1, subject: CapacitySubjectV1, registry_revision: int
) -> ProviderQuotaInputV1:
    """Retain unknown scope and never retire windows on an incomplete source."""
    if subject.provider_key != "ollama":
        raise ValueError("ollama_cloud_target_mismatch")
    projection = to_capacity_windows(balance)
    return ProviderQuotaInputV1(
        subject=subject,
        registry_revision=registry_revision,
        capability_schema_version="1.0.0",
        completeness="partial_scope",
        windows=projection.windows,
        omission_codes=("cloud_scope_unresolved",),
    )


def admission_outcome_for_source(state: str) -> str:
    if state == "success":
        return "succeeded"
    if state == "rate_limited":
        return "rate_limited"
    return "failed"


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
        delay = min(86400, max(1, retry_after if retry_after is not None else 60))
        return CollectionFailurePolicyV1(
            "rate_limited", RetryAdviceV1("after_delay", delay, "estimated")
        )
    if state in {"provider_unavailable", "deadline_exceeded"}:
        outcome = (
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
