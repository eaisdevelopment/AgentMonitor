"""Expanded source identity preserves legacy cost admission and shared authority."""

from agentmonitor.adapters.providers.claude.anthropic_api.manifest import (
    build_anthropic_analytics_manifest,
    build_anthropic_cost_manifest,
)


def test_expanded_analytics_manifest_admits_separate_cost_and_usage_sources() -> None:
    legacy = build_anthropic_cost_manifest()
    manifest = build_anthropic_analytics_manifest()
    assert legacy.descriptor.adapter_version == "1.0.1"
    assert manifest.descriptor.adapter_version == "1.1.1"
    assert manifest.descriptor.adapter_id == legacy.descriptor.adapter_id
    assert manifest.m0_mapping_digest != legacy.m0_mapping_digest
    assert {item.capability_id for item in manifest.declarations} == {
        "api.cost",
        "api.usage",
    }
    assert {item.sources[0].source_id for item in manifest.declarations} == {
        "anthropic.analytics.cost.v1",
        "anthropic.analytics.usage.v1",
    }
    assert all(
        item.is_experimental
        for declaration in manifest.declarations
        for item in declaration.sources
    )
    assert {
        item.constraints.provider_request_count for item in manifest.declarations
    } == {20}
