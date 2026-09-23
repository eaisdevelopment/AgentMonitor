"""Claude adapter declarations for the exact accepted live tuple."""

from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_VERSION,
    CLAUDE_OTEL_SOURCE_ID,
    CLAUDE_PARSER_VERSION,
    CLAUDE_PROVIDER_VERSION,
    CLAUDE_USAGE_SOURCE_ID,
    build_claude_manifest,
    build_claude_otel_manifest,
)


def test_manifest_exposes_only_the_evidenced_subscription_source() -> None:
    """CLA-PURE-001/CLA-SEC-001: the live lane is closed and read-only."""
    manifest = build_claude_manifest()
    quota = next(
        item
        for item in manifest.declarations
        if item.capability_id == "subscription.quota"
    )

    assert manifest.descriptor.adapter_version == CLAUDE_ADAPTER_VERSION
    assert quota.decision == "supported"
    assert quota.provider_version_rule.verified_versions == (CLAUDE_PROVIDER_VERSION,)
    assert quota.constraints.automatic_retry_count == 0
    assert quota.constraints.maximum_concurrency == 1
    assert quota.constraints.deadline_ms == 30_000
    assert tuple(source.source_id for source in quota.sources) == (
        CLAUDE_USAGE_SOURCE_ID,
    )
    assert all(source.side_effect_class == "read_only" for source in quota.sources)


def test_corrected_live_parser_has_distinct_patch_provenance() -> None:
    """CLA-PROV-001: corrected parser semantics never reuse the old identity."""
    assert CLAUDE_ADAPTER_VERSION == "1.0.2"
    assert CLAUDE_PARSER_VERSION == "1.0.2"


def test_manifest_declares_official_otel_session_lane_separately() -> None:
    """CLA-PURE-OTEL-001: session telemetry cannot broaden the quota lane."""
    quota_manifest = build_claude_manifest()
    otel_manifest = build_claude_otel_manifest()
    quota = quota_manifest.declarations[0]
    session = otel_manifest.declarations[0]

    assert quota.provider_version_rule.verified_versions == (CLAUDE_PROVIDER_VERSION,)
    assert tuple(source.source_id for source in quota.sources) == (
        CLAUDE_USAGE_SOURCE_ID,
    )
    assert session.provider_version_rule.verified_versions == (CLAUDE_PROVIDER_VERSION,)
    assert tuple(source.source_id for source in session.sources) == (
        CLAUDE_OTEL_SOURCE_ID,
    )
    assert session.sources[0].source_class == "documented_api"
    assert quota_manifest.m0_mapping_digest != otel_manifest.m0_mapping_digest
    assert quota_manifest.descriptor.adapter_id != otel_manifest.descriptor.adapter_id
