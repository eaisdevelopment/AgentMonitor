"""Pure checks for account ownership before a cloud capacity commit."""

import pytest

from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
    validate_cloud_target,
)


def test_cloud_target_rejects_cross_account_data() -> None:
    validate_cloud_target("account", "account", "account", "ollama")
    with pytest.raises(ValueError, match="ollama_cloud_target_mismatch"):
        validate_cloud_target("account", "other", "account", "ollama")
    with pytest.raises(ValueError, match="ollama_cloud_target_mismatch"):
        validate_cloud_target("account", "account", "account", "codex")


def test_source_status_maps_to_durable_rate_outcomes() -> None:
    from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
        admission_outcome_for_source,
    )

    assert admission_outcome_for_source("success") == "succeeded"
    assert admission_outcome_for_source("rate_limited") == "rate_limited"
    assert admission_outcome_for_source("unauthorized") == "failed"


def test_failure_policy_preserves_actionable_provider_states() -> None:
    from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
        cloud_failure_policy,
    )

    assert (
        cloud_failure_policy("authorization_unavailable", None).retry.disposition
        == "after_user_action"
    )
    assert (
        cloud_failure_policy("unauthorized", None).provider_outcome
        == "reauthentication_required"
    )
    assert cloud_failure_policy("rate_limited", 90).retry.delay_seconds == 90
