"""Pure M02 policy for owner-asserted Ollama cloud account enrollment."""

from typing import Literal

from agentmonitor.contracts.registry_v1 import (
    CredentialBindingVerificationReceiptV1,
)

VerificationReceiptTransitionV1 = Literal["install", "replay", "supersede"]


def verification_receipt_transition(
    current: CredentialBindingVerificationReceiptV1 | None,
    proposed: CredentialBindingVerificationReceiptV1,
) -> VerificationReceiptTransitionV1:
    """Preserve exact replay and replace only a newer receipt for one binding."""
    if not isinstance(proposed, CredentialBindingVerificationReceiptV1) or (
        current is not None
        and not isinstance(current, CredentialBindingVerificationReceiptV1)
    ):
        raise ValueError("credential_binding_verification_conflict")
    if current is None:
        return "install"
    if current == proposed:
        return "replay"
    if (
        current.binding != proposed.binding
        or current.access_target_id != proposed.access_target_id
        or current.source_id != proposed.source_id
        or current.adapter_version != proposed.adapter_version
        or current.manifest_fingerprint != proposed.manifest_fingerprint
        or current.verification_id == proposed.verification_id
        or current.run_id == proposed.run_id
        or current.admission_id == proposed.admission_id
        or proposed.verified_at <= current.verified_at
    ):
        raise ValueError("credential_binding_verification_conflict")
    return "supersede"


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


def decide_cloud_binding_reassertion(
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
    graph_lifecycle: str,
    graph_identity_state: str,
    binding_is_current: bool,
) -> int:
    """Fence a fresh owner check after rotation without weakening enrollment."""
    if (
        type(account_record_version) is not int
        or type(expected_account_record_version) is not int
        or account_record_version < 1
        or account_record_version != expected_account_record_version
    ):
        raise ValueError("registry_account_version_conflict")
    if (
        account_provider != "ollama"
        or account_lifecycle != "active"
        or account_identity_state != "owner_confirmed"
        or account_monitoring_preference != "enabled"
        or target_provider != "ollama"
        or target_kind != "cloud_service"
        or target_authority != "ollama.com"
        or target_lifecycle != "active"
        or graph_lifecycle != "active"
        or graph_identity_state != "owner_confirmed"
        or binding_is_current is not True
    ):
        raise ValueError("registry_cloud_reassertion_invalid")
    return account_record_version + 1
