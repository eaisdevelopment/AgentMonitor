"""Pure checks for account ownership before a cloud capacity commit."""

import pytest
from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
    validate_cloud_target,
)
from agentmonitor.modules.collection_control.application.ollama_cloud_admission import (
    admission_outcome_for_source,
    cloud_failure_policy,
    no_response_reason_for_source,
)


def test_cloud_target_rejects_cross_account_data() -> None:
    validate_cloud_target("account", "account", "account", "ollama")
    with pytest.raises(ValueError, match="ollama_cloud_target_mismatch"):
        validate_cloud_target("account", "other", "account", "ollama")
    with pytest.raises(ValueError, match="ollama_cloud_target_mismatch"):
        validate_cloud_target("account", "account", "account", "codex")


def test_source_status_maps_to_durable_rate_outcomes() -> None:
    assert admission_outcome_for_source("success") == "succeeded"
    assert admission_outcome_for_source("rate_limited") == "rate_limited"
    assert admission_outcome_for_source("unauthorized") == "failed"


def test_credential_update_contention_keeps_a_distinct_no_response_reason() -> None:
    assert (
        no_response_reason_for_source(
            "authorization_unavailable", "ollama_cloud_store_locked"
        )
        == "credential_update_in_progress"
    )
    assert (
        no_response_reason_for_source(
            "authorization_unavailable", "ollama_cloud_store_unavailable"
        )
        == "store_unavailable"
    )
    assert (
        no_response_reason_for_source(
            "provider_unavailable", "ollama_cloud_provider_unavailable"
        )
        == "source_not_started"
    )


def test_failure_policy_preserves_actionable_provider_states() -> None:
    assert (
        cloud_failure_policy("authorization_unavailable", None).retry.disposition
        == "after_user_action"
    )
    assert (
        cloud_failure_policy("unauthorized", None).provider_outcome
        == "reauthentication_required"
    )
    assert cloud_failure_policy("rate_limited", 90).retry.delay_seconds == 90


def test_failure_policy_never_shortens_provider_retry() -> None:
    assert cloud_failure_policy("rate_limited", 172800).retry.delay_seconds == 172800


def test_cloud_target_projects_into_v2_capacity_contract() -> None:
    from decimal import Decimal

    from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
        cloud_balance_to_capacity,
    )
    from agentmonitor.contracts.capacity_v1 import (
        CapacitySubjectV2,
        ProviderQuotaInputV2,
    )
    from agentmonitor.contracts.common_v1 import OpaqueIdV1
    from agentmonitor.contracts.providers.ollama.cloud_balance.v1.schema import (
        OllamaCloudBalanceV1,
    )
    from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

    subject = CapacitySubjectV2(
        "ollama",
        ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32)),
        OpaqueIdV1("account"),
        OpaqueIdV1("resource"),
    )
    payload = cloud_balance_to_capacity(
        OllamaCloudBalanceV1(None, Decimal("5")), subject, 1
    )
    assert isinstance(payload, ProviderQuotaInputV2)
    assert payload.subject == subject


def test_cloud_v2_requires_same_provider_target() -> None:
    from agentmonitor.composition.ollama_capacity_commit import (
        validate_cloud_provider_target,
    )
    from agentmonitor.contracts.common_v1 import OpaqueIdV1
    from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

    left = ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32))
    other = ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "b" * 32))
    validate_cloud_provider_target(left, left)
    with pytest.raises(ValueError, match="ollama_cloud_target_mismatch"):
        validate_cloud_provider_target(left, other)
