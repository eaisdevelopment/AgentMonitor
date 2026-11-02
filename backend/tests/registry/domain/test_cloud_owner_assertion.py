"""Pure M02 owner-assertion policy; no database, provider, or secret I/O."""

import pytest

from agentmonitor.modules.registry.domain.cloud_verification import (
    cloud_verification_enqueue_account_version,
    decide_cloud_owner_assertion,
    require_cloud_verification_enqueue_authority,
)


def test_pending_ollama_account_becomes_owner_confirmed_and_enabled() -> None:
    decision = decide_cloud_owner_assertion(
        account_provider="ollama",
        account_lifecycle="pending",
        account_identity_state="unresolved",
        account_monitoring_preference="disabled",
        account_record_version=3,
        expected_account_record_version=3,
        target_provider="ollama",
        target_lifecycle="active",
        binding_is_current=True,
    )

    assert decision == ("active", "owner_confirmed", "enabled", 4)


@pytest.mark.parametrize(
    "overrides,code",
    (
        ({"account_provider": "claude"}, "registry_cloud_account_invalid"),
        ({"account_lifecycle": "archived"}, "registry_cloud_account_invalid"),
        ({"account_identity_state": "matched"}, "registry_cloud_identity_invalid"),
        ({"account_record_version": 4}, "registry_account_version_conflict"),
        ({"target_provider": "claude"}, "registry_cloud_target_invalid"),
        ({"target_lifecycle": "disabled"}, "registry_cloud_target_invalid"),
        ({"binding_is_current": False}, "credential_binding_generation_conflict"),
    ),
)
def test_owner_assertion_fails_closed(overrides: dict[str, object], code: str) -> None:
    values: dict[str, object] = {
        "account_provider": "ollama",
        "account_lifecycle": "pending",
        "account_identity_state": "unresolved",
        "account_monitoring_preference": "disabled",
        "account_record_version": 3,
        "expected_account_record_version": 3,
        "target_provider": "ollama",
        "target_lifecycle": "active",
        "binding_is_current": True,
    }
    values.update(overrides)
    with pytest.raises(ValueError, match=code):
        decide_cloud_owner_assertion(**values)  # type: ignore[arg-type]


def test_verification_enqueue_requires_exact_current_account_authority() -> None:
    require_cloud_verification_enqueue_authority(
        account_provider="ollama",
        account_lifecycle="active",
        account_identity_state="owner_confirmed",
        account_monitoring_preference="enabled",
        account_record_version=4,
        expected_account_record_version=4,
        target_provider="ollama",
        target_kind="cloud_service",
        target_authority="ollama.com",
        target_lifecycle="active",
        target_manifest_is_exact=True,
        graph_is_exact=True,
        binding_is_current=True,
    )


def test_enqueue_version_is_the_exact_owner_assertion_outcome() -> None:
    assert (
        cloud_verification_enqueue_account_version(
            command_expected_version=4,
            owner_assertion_required=False,
        )
        == 4
    )
    assert (
        cloud_verification_enqueue_account_version(
            command_expected_version=4,
            owner_assertion_required=True,
        )
        == 5
    )


@pytest.mark.parametrize(
    "overrides,code",
    (
        ({"account_record_version": 5}, "registry_account_version_conflict"),
        ({"account_lifecycle": "archived"}, "registry_cloud_account_invalid"),
        ({"account_identity_state": "unresolved"}, "registry_cloud_identity_invalid"),
        (
            {"account_monitoring_preference": "disabled"},
            "registry_cloud_monitoring_disabled",
        ),
        ({"target_authority": "other.example"}, "registry_cloud_target_invalid"),
        ({"target_manifest_is_exact": False}, "registry_cloud_target_invalid"),
        ({"graph_is_exact": False}, "registry_cloud_graph_invalid"),
        ({"binding_is_current": False}, "credential_binding_generation_conflict"),
    ),
)
def test_verification_enqueue_authority_fails_closed(
    overrides: dict[str, object], code: str
) -> None:
    values: dict[str, object] = {
        "account_provider": "ollama",
        "account_lifecycle": "active",
        "account_identity_state": "owner_confirmed",
        "account_monitoring_preference": "enabled",
        "account_record_version": 4,
        "expected_account_record_version": 4,
        "target_provider": "ollama",
        "target_kind": "cloud_service",
        "target_authority": "ollama.com",
        "target_lifecycle": "active",
        "target_manifest_is_exact": True,
        "graph_is_exact": True,
        "binding_is_current": True,
    }
    values.update(overrides)
    with pytest.raises(ValueError, match=code):
        require_cloud_verification_enqueue_authority(**values)  # type: ignore[arg-type]
