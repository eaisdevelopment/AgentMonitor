"""Claude adapter declarations for the exact accepted live tuple."""

from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_VERSION,
    CLAUDE_PROVIDER_VERSION,
    CLAUDE_USAGE_SOURCE_ID,
    build_claude_manifest,
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
