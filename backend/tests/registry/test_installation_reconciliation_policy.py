"""Pure M02 policy for atomic installation-only reconciliation."""

import pytest
from agentmonitor.modules.registry.domain.account import RegistryPolicyErrorV1
from agentmonitor.modules.registry.domain.discovery import (
    decide_installation_only_reconciliation,
)


def test_installation_only_reconciliation_requires_one_stable_identity() -> None:
    """CTR-REG-004/006: current-installation refresh cannot add a second row."""
    assert (
        decide_installation_only_reconciliation(
            capability_id="installation.discovery",
            account_count=0,
            installation_count=1,
            outcome_provider_key="claude",
            incoming_provider_key="claude",
            incoming_identity_fingerprint="a" * 64,
            incoming_platform_key="linux-x86_64",
            existing_installations=(),
        )
        == "insert"
    )
    assert (
        decide_installation_only_reconciliation(
            capability_id="installation.discovery",
            account_count=0,
            installation_count=1,
            outcome_provider_key="claude",
            incoming_provider_key="claude",
            incoming_identity_fingerprint="a" * 64,
            incoming_platform_key="linux-x86_64",
            existing_installations=(("a" * 64, "linux-x86_64"),),
        )
        == "update"
    )
    for existing in (
        (("b" * 64, "linux-x86_64"),),
        (("a" * 64, "darwin-arm64"),),
        (("a" * 64, "linux-x86_64"), ("b" * 64, "linux-x86_64")),
    ):
        with pytest.raises(
            RegistryPolicyErrorV1,
            match="^registry_installation_identity_conflict$",
        ):
            decide_installation_only_reconciliation(
                capability_id="installation.discovery",
                account_count=0,
                installation_count=1,
                outcome_provider_key="claude",
                incoming_provider_key="claude",
                incoming_identity_fingerprint="a" * 64,
                incoming_platform_key="linux-x86_64",
                existing_installations=existing,
            )


def test_installation_only_reconciliation_rejects_candidate_or_shape_drift() -> None:
    """CTR-REG-006: the strict path accepts one installation and no accounts."""
    for account_count, installation_count in ((1, 1), (0, 0), (0, 2)):
        with pytest.raises(
            RegistryPolicyErrorV1,
            match="^registry_installation_scope_invalid$",
        ):
            decide_installation_only_reconciliation(
                capability_id="installation.discovery",
                account_count=account_count,
                installation_count=installation_count,
                outcome_provider_key="claude",
                incoming_provider_key="claude",
                incoming_identity_fingerprint="a" * 64,
                incoming_platform_key="linux-x86_64",
                existing_installations=(),
            )


def test_other_discovery_capabilities_keep_existing_generic_policy() -> None:
    """CTR-REG-006: the additive guard does not narrow account discovery."""
    assert (
        decide_installation_only_reconciliation(
            capability_id="subscription.quota",
            account_count=1,
            installation_count=1,
            outcome_provider_key="claude",
            incoming_provider_key="other-provider",
            incoming_identity_fingerprint="a" * 64,
            incoming_platform_key="linux-x86_64",
            existing_installations=(("b" * 64, "linux-x86_64"),),
        )
        == "not_applicable"
    )


def test_installation_only_reconciliation_rejects_provider_scope_drift() -> None:
    """CTR-REG-004/006: nested installation scope must match the outcome."""
    with pytest.raises(
        RegistryPolicyErrorV1,
        match="^registry_installation_scope_invalid$",
    ):
        decide_installation_only_reconciliation(
            capability_id="installation.discovery",
            account_count=0,
            installation_count=1,
            outcome_provider_key="claude",
            incoming_provider_key="other-provider",
            incoming_identity_fingerprint="a" * 64,
            incoming_platform_key="linux-x86_64",
            existing_installations=(),
        )
