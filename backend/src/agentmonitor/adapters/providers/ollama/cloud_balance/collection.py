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
