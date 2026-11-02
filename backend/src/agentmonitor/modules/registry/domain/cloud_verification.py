"""Pure M02 policy for owner-asserted Ollama cloud account enrollment."""

from typing import Literal


def decide_cloud_owner_assertion(
    *,
    account_provider: str,
    account_lifecycle: str,
    account_identity_state: str,
    account_monitoring_preference: str,
    account_record_version: int,
    expected_account_record_version: int,
    target_provider: str,
    target_lifecycle: str,
    binding_is_current: bool,
) -> tuple[Literal["active"], Literal["owner_confirmed"], Literal["enabled"], int]:
    """Return the one allowed pending-account transition or fail closed."""
    if account_provider != "ollama" or account_lifecycle != "pending":
        raise ValueError("registry_cloud_account_invalid")
    if (
        account_identity_state != "unresolved"
        or account_monitoring_preference != "disabled"
    ):
        raise ValueError("registry_cloud_identity_invalid")
    if (
        type(account_record_version) is not int
        or type(expected_account_record_version) is not int
        or account_record_version != expected_account_record_version
    ):
        raise ValueError("registry_account_version_conflict")
    if target_provider != "ollama" or target_lifecycle != "active":
        raise ValueError("registry_cloud_target_invalid")
    if binding_is_current is not True:
        raise ValueError("credential_binding_generation_conflict")
    return "active", "owner_confirmed", "enabled", account_record_version + 1
