"""Pure account and capacity conversion for one Ollama cloud reading."""

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
