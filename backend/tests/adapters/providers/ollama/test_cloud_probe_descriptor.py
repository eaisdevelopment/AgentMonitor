"""Pure provenance contract for an owner-initiated first cloud check."""

from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
    ollama_cloud_probe_source,
)


def test_probe_identifies_documented_api_without_claiming_supported_capability() -> (
    None
):
    source = ollama_cloud_probe_source()
    assert source.source_id == "ollama.cloud.balance.v1"
    assert source.source_class == "documented_api"
    assert source.capability_id == "subscription.quota"
    assert source.mechanism_version == "1.0.2"
    assert source.side_effect_class == "read_only"
    assert not source.is_experimental
    assert (
        ollama_cloud_probe_fingerprint()
        == "1754266efc774ce201bb803e8223d4adfb71fedeb71f5dc99b57825d0b95d7f7"
    )


def test_scheduled_policy_is_documented_rate_bounded_and_digest_bound() -> None:
    from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
        ollama_cloud_scheduled_policy,
    )

    policy = ollama_cloud_scheduled_policy()
    assert policy.source_fingerprint == ollama_cloud_probe_fingerprint()
    assert policy.minimum_interval_seconds == 60
    assert policy.maximum_concurrency == 1
    assert policy.automatic_retry_count == 0


def test_scheduled_proof_is_bound_to_current_account_and_policy() -> None:
    from dataclasses import replace
    from datetime import timedelta

    import pytest
    from backend.tests.provider_system.test_scheduled_source_admission import (
        NOW,
        lineage,
    )

    from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
        ollama_cloud_scheduled_policy,
        require_matching_scheduled_proof,
    )
    from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
    from agentmonitor.modules.provider_system.domain.protocol import (
        derive_scheduled_source_admission_v1,
    )

    policy = ollama_cloud_scheduled_policy()
    origin = replace(
        lineage(),
        adapter_version=policy.adapter_version,
        run_adapter_version=policy.adapter_version,
        source_fingerprint=policy.source_fingerprint,
        authorization_signal_adapter_version=policy.adapter_version,
        authorization_signal_source_fingerprint=policy.source_fingerprint,
    )
    proof = derive_scheduled_source_admission_v1(
        policy, origin, evaluated_at=NOW + timedelta(seconds=2)
    )
    binding = ActiveCredentialBindingRefV1(
        proof.account_id, proof.binding_id, proof.binding_generation
    )
    require_matching_scheduled_proof(binding, proof)
    with pytest.raises(ValueError):
        require_matching_scheduled_proof(
            replace(binding, generation=binding.generation + 1), proof
        )
