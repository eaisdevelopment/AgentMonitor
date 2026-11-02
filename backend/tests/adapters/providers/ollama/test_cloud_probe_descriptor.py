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
    assert source.side_effect_class == "read_only"
    assert not source.is_experimental
    assert len(ollama_cloud_probe_fingerprint()) == 64
    assert ollama_cloud_probe_fingerprint() == ollama_cloud_probe_fingerprint()
