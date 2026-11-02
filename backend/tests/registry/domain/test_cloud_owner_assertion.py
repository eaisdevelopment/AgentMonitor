"""Pure M02 owner-assertion policy; no database, provider, or secret I/O."""

import pytest

from agentmonitor.modules.registry.domain.cloud_verification import (
    decide_cloud_owner_assertion,
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
