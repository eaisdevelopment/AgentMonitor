"""Pure finite selection/admission policies and the actual reviewed mapping."""

import hashlib
import json
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.codex.openai_api import manifest, policy
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilitySchemaVersionV1,
    SourcePolicyV1,
)
from agentmonitor.modules.provider_system.domain.protocol import resolve_capability


def _expected_selections() -> set[tuple[str, tuple[str, ...]]]:
    ordinary = {
        "cost": ("project", "api_key_id"),
        "usage_completions": ("project", "api_key_id", "model"),
        "usage_embeddings": ("project", "api_key_id", "model"),
        "usage_moderations": ("project", "api_key_id", "model"),
        "usage_images": ("project", "api_key_id", "model"),
        "usage_audio_speeches": ("project", "api_key_id", "model"),
        "usage_audio_transcriptions": ("project", "api_key_id", "model"),
        "usage_code_interpreter_sessions": ("project",),
        "usage_vector_stores": ("project",),
        "usage_file_search_calls": ("project", "api_key_id"),
        "usage_web_search_calls": ("project", "api_key_id", "model"),
        "usage_decisions": ("project", "api_key_id", "model"),
    }
    return {
        (category, grouping)
        for category, dimensions in ordinary.items()
        for grouping in ((), *((dimension,) for dimension in dimensions))
    } | {
        ("usage_" + category + "_tokens", ("token_category",))
        for category in ("completions", "embeddings", "moderations", "decisions")
    }


def test_openai_analytics_inventory_is_exact_and_classifies_all_46_views() -> None:
    selections = policy.ANALYTICS_REPORT_SELECTIONS
    assert isinstance(selections, tuple)
    assert len(selections) == len(set(selections)) == 46
    assert set(selections) == _expected_selections()
    for category, grouping in selections:
        assert policy.analytics_selection_is_usage(category, grouping) is (
            category != "cost"
        )


@pytest.mark.parametrize(
    ("category", "grouping"),
    (
        ("cost", ("model",)),
        ("cost_tokens", ("token_category",)),
        ("usage", ()),
        ("usage_completions", ("token_category",)),
        ("usage_completions_tokens", ()),
        ("usage_images_tokens", ("token_category",)),
        ("usage_file_search_calls", ("model",)),
        ("usage_vector_stores", ("api_key_id",)),
        ("usage_code_interpreter_sessions", ("model",)),
        ("usage_decisions", ("project", "model")),
        ("usage_completions", ("user_id",)),
    ),
)
def test_openai_analytics_rejects_unreviewed_views(
    category: str, grouping: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError, match="openai_analytics_selection_invalid"):
        policy.analytics_selection_is_usage(category, grouping)


def test_openai_analytics_manifest_preserves_legacy_and_distinct_source_versions() -> (
    None
):
    legacy = manifest.build_openai_cost_manifest()
    combined = manifest.build_openai_analytics_manifest()
    assert legacy == manifest.build_openai_cost_manifest()
    assert legacy.descriptor.adapter_version == "1.0.3"
    assert combined.descriptor.adapter_id == legacy.descriptor.adapter_id
    assert combined.descriptor.adapter_version == "1.1.3"
    assert combined.descriptor.build_identity == "agentmonitor-openai-analytics-v1.1.3"
    assert combined.m0_mapping_id == "OPENAI-ANALYTICS-1.1"
    assert combined.m0_mapping_version == "1.1.0"
    assert combined.m0_mapping_digest != legacy.m0_mapping_digest
    assert tuple(item.capability_id for item in combined.declarations) == (
        "api.cost",
        "api.usage",
    )
    for declaration, source_id, version in zip(
        combined.declarations,
        (policy.SOURCE_ID, policy.USAGE_SOURCE_ID),
        (manifest.PROVIDER_VERSION, manifest.USAGE_PROVIDER_VERSION),
        strict=True,
    ):
        source = declaration.sources[0]
        assert source.source_id == source_id
        assert source.mechanism_version == version
        assert declaration.provider_version_rule.verified_versions == (version,)
        assert source.evidence_reference == combined.m0_mapping_id
        assert declaration.evidence_reference == combined.m0_mapping_id
        assert declaration.constraints == legacy.declarations[0].constraints
        assert source.side_effect_class == "read_only"
        assert source.credential_role == "owner_entered_admin_api_key"
        assert declaration.decision == "experimental"
        assert declaration.reason_code == "documented_source_live_verification_pending"


def test_openai_analytics_admission_requires_grant_and_source_specific_version() -> (
    None
):
    combined = manifest.build_openai_analytics_manifest()
    for declaration in combined.declarations:
        source = declaration.sources[0]
        other_version = (
            manifest.USAGE_PROVIDER_VERSION
            if source.capability_id == "api.cost"
            else manifest.PROVIDER_VERSION
        )
        for grant, version, expected in (
            (None, source.mechanism_version, "capability_disabled"),
            (OpaqueIdV1("pure-grant"), source.mechanism_version, "resolved"),
            (OpaqueIdV1("pure-grant"), other_version, "provider_version_unverified"),
        ):
            result = resolve_capability(
                combined,
                approved_mapping_digest=combined.m0_mapping_digest,
                host_protocol_version="1.0.0",
                capability_id=declaration.capability_id,
                capability_schema_version=CapabilitySchemaVersionV1(2, 0),
                provider_version=version,
                platform_id="linux-x86_64",
                source_policy=SourcePolicyV1(
                    OpaqueIdV1("pure-policy"), (source.source_id,), (), grant
                ),
            )
            assert result.code == expected


def test_openai_analytics_mapping_bytes_and_inventory_match_manifest() -> None:
    root = next(
        path for path in Path(__file__).parents if (path / "AGENTS.md").is_file()
    )
    raw = (root / "contracts/provider-system/openai-analytics-v1.1.json").read_bytes()
    mapping = json.loads(raw)
    combined = manifest.build_openai_analytics_manifest()
    assert hashlib.sha256(raw).hexdigest() == combined.m0_mapping_digest
    assert mapping["mapping_id"] == combined.m0_mapping_id
    assert mapping["mapping_version"] == combined.m0_mapping_version
    assert mapping["authority"] == "openai.organization"
    assert mapping["live_verification"] == "not_established_by_this_mapping"
    assert {
        (report["category"], tuple(grouping))
        for report in mapping["reports"]
        for grouping in report["groupings"]
    } == _expected_selections()
