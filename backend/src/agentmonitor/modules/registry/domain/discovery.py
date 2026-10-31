"""Pure provider-neutral registry discovery reconciliation policies."""

from typing import Literal

from agentmonitor.modules.registry.domain.account import RegistryPolicyErrorV1

InstallationReconciliationDecisionV1 = Literal["not_applicable", "insert", "update"]


def decide_installation_only_reconciliation(
    *,
    capability_id: str,
    account_count: int,
    installation_count: int,
    outcome_provider_key: str,
    incoming_provider_key: str,
    incoming_identity_fingerprint: str,
    incoming_platform_key: str,
    existing_installations: tuple[tuple[str, str], ...],
) -> InstallationReconciliationDecisionV1:
    """Keep an installation-only observation on one stable persisted identity."""
    if capability_id != "installation.discovery":
        return "not_applicable"
    if (
        account_count != 0
        or installation_count != 1
        or not outcome_provider_key
        or incoming_provider_key != outcome_provider_key
        or len(incoming_identity_fingerprint) != 64
        or any(
            character not in "0123456789abcdef"
            for character in incoming_identity_fingerprint
        )
        or not incoming_platform_key
    ):
        raise RegistryPolicyErrorV1("registry_installation_scope_invalid")
    if not existing_installations:
        return "insert"
    if existing_installations == (
        (incoming_identity_fingerprint, incoming_platform_key),
    ):
        return "update"
    raise RegistryPolicyErrorV1("registry_installation_identity_conflict")
