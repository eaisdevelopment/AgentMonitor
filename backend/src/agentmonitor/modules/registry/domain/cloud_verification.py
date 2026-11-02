"""Pure M02 policy for owner-asserted Ollama cloud account enrollment."""

from typing import Literal


def cloud_verification_enqueue_account_version(
    *, command_expected_version: int, owner_assertion_required: bool
) -> int:
    """Return the only account version a new verification job may fence."""
    if (
        type(command_expected_version) is not int
        or command_expected_version < 1
        or type(owner_assertion_required) is not bool
    ):
        raise ValueError("registry_account_version_conflict")
    return command_expected_version + int(owner_assertion_required)


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
    if (
        type(account_record_version) is not int
        or type(expected_account_record_version) is not int
        or account_record_version != expected_account_record_version
    ):
        raise ValueError("registry_account_version_conflict")
    if account_provider != "ollama" or account_lifecycle != "pending":
        raise ValueError("registry_cloud_account_invalid")
    if (
        account_identity_state != "unresolved"
        or account_monitoring_preference != "disabled"
    ):
        raise ValueError("registry_cloud_identity_invalid")
    if target_provider != "ollama" or target_lifecycle != "active":
        raise ValueError("registry_cloud_target_invalid")
    if binding_is_current is not True:
        raise ValueError("credential_binding_generation_conflict")
    return "active", "owner_confirmed", "enabled", account_record_version + 1


def require_cloud_verification_enqueue_authority(
    *,
    account_provider: str,
    account_lifecycle: str,
    account_identity_state: str,
    account_monitoring_preference: str,
    account_record_version: int,
    expected_account_record_version: int,
    target_provider: str,
    target_kind: str,
    target_authority: str,
    target_lifecycle: str,
    target_manifest_is_exact: bool,
    graph_is_exact: bool,
    binding_is_current: bool,
) -> None:
    """Require current M02 authority before M04 creates verification work."""
    if (
        type(account_record_version) is not int
        or type(expected_account_record_version) is not int
        or account_record_version != expected_account_record_version
    ):
        raise ValueError("registry_account_version_conflict")
    if account_provider != "ollama" or account_lifecycle != "active":
        raise ValueError("registry_cloud_account_invalid")
    if account_identity_state != "owner_confirmed":
        raise ValueError("registry_cloud_identity_invalid")
    if account_monitoring_preference != "enabled":
        raise ValueError("registry_cloud_monitoring_disabled")
    if (
        target_provider != "ollama"
        or target_kind != "cloud_service"
        or target_authority != "ollama.com"
        or target_lifecycle != "active"
        or target_manifest_is_exact is not True
    ):
        raise ValueError("registry_cloud_target_invalid")
    if graph_is_exact is not True:
        raise ValueError("registry_cloud_graph_invalid")
    if binding_is_current is not True:
        raise ValueError("credential_binding_generation_conflict")
