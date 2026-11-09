"""Claude adapter declarations for the exact accepted live tuple."""

import hashlib
import json
from pathlib import Path

import agentmonitor.adapters.providers.claude.manifest as claude_manifest
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_VERSION,
    CLAUDE_OTEL_MAPPING_DIGEST,
    CLAUDE_OTEL_PROVIDER_VERSION,
    CLAUDE_OTEL_SOURCE_ID,
    CLAUDE_PARSER_VERSION,
    CLAUDE_PROVIDER_VERSION,
    CLAUDE_USAGE_SOURCE_ID,
    build_claude_manifest,
    build_claude_otel_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
CLAUDE_OTEL_MAPPING_PATH = (
    REPOSITORY_ROOT / "docs/discovery/m0/m0-to-m03-claude-otel-v1.json"
)
CLAUDE_QUOTA_ADMISSION_PATH = (
    REPOSITORY_ROOT / "docs/discovery/m0/m0-to-m03-claude-2.1.289-v2.json"
)
CLAUDE_VERSION_EVIDENCE_PATH = (
    REPOSITORY_ROOT / "docs/evidence/claude-weekly-only-admission-2026-11-09.md"
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


def test_manifest_declares_every_capability_in_the_current_admission() -> None:
    """CLA-ARCH-004: the published A01 manifest matches its exact admission."""
    admission = json.loads(CLAUDE_QUOTA_ADMISSION_PATH.read_text(encoding="utf-8"))
    admitted = {row["capability_id"]: row for row in admission["scope"]["capabilities"]}
    declared = {
        declaration.capability_id: declaration
        for declaration in build_claude_manifest().declarations
    }

    assert set(declared) == set(admitted)
    expected_ports = {
        "installation.discovery": "InstallationDiscoveryPortV1",
        "subscription.quota": "SubscriptionQuotaPortV1",
        "authentication.health": "AuthenticationHealthPortV1",
        "identity.verification": "ProviderCapabilityPortV1",
        "authentication.reauthenticate": "ProviderConnectionPortV1",
    }
    for capability_id, admitted_row in admitted.items():
        declaration = declared[capability_id]
        output_schema, admitted_version = admitted_row["output_contract"].split("@")
        version_parts = tuple(int(part) for part in admitted_version.split("."))
        expected_version = (
            version_parts[0],
            version_parts[1] if len(version_parts) > 1 else 0,
        )

        assert declaration.decision == "supported"
        assert declaration.port_type == expected_ports[capability_id]
        assert declaration.output_schema == output_schema
        assert (
            declaration.schema_versions.minimum.major,
            declaration.schema_versions.minimum.minor,
        ) == expected_version
        assert (
            declaration.schema_versions.minimum == declaration.schema_versions.maximum
        )
        assert declaration.provider_version_rule.verified_versions == (
            CLAUDE_PROVIDER_VERSION,
        )
        assert declaration.side_effect_class == admitted_row["side_effect_class"]
        assert tuple(source.source_id for source in declaration.sources) == (
            admitted_row["source_id"],
        )
        assert all(
            source.side_effect_class == admitted_row["side_effect_class"]
            for source in declaration.sources
        )


def test_quota_version_admission_preserves_parser_provenance() -> None:
    """CLA-PROV-001: changed parsing has a distinct provenance version."""
    assert CLAUDE_ADAPTER_VERSION == "1.0.4"
    assert CLAUDE_PARSER_VERSION == "1.0.4"


def test_quota_manifest_binds_exact_current_admission_without_widening_otel() -> None:
    """CLA-CLI-003/004: active quota admission has exact hash-bound evidence."""
    admission = json.loads(CLAUDE_QUOTA_ADMISSION_PATH.read_text(encoding="utf-8"))
    digest = hashlib.sha256(CLAUDE_QUOTA_ADMISSION_PATH.read_bytes()).hexdigest()
    quota = build_claude_manifest().declarations[0]
    otel = build_claude_otel_manifest().declarations[0]

    assert set(admission) == {
        "record_type",
        "schema_version",
        "admission_id",
        "status",
        "approved_at",
        "authority",
        "scope",
        "compatibility_policy",
        "managed_authentication_policy",
        "quota_parser_policy",
        "evidence",
        "historical_predecessor",
        "excluded",
    }
    assert admission["record_type"] == "M0ToM03ClaudeVersionAdmissionV1"
    assert admission["schema_version"] == "1.0.0"
    assert admission["status"] == "approved"
    assert admission["scope"]["provider_version"] == "2.1.289"
    assert claude_manifest.CLAUDE_PROVIDER_VERSION == "2.1.289"
    assert claude_manifest.CLAUDE_ADAPTER_VERSION == "1.0.4"
    assert claude_manifest.CLAUDE_PARSER_VERSION == "1.0.4"
    assert claude_manifest.CLAUDE_OTEL_PROVIDER_VERSION == "2.1.282"
    assert admission["scope"]["capabilities"] == [
        {
            "capability_id": "installation.discovery",
            "source_id": "claude.version.banner.v1",
            "side_effect_class": "read_only",
            "output_contract": "DiscoveryOutcomeV1@1.0",
        },
        {
            "capability_id": "subscription.quota",
            "source_id": "claude.usage.ax-screen-reader.v1",
            "side_effect_class": "read_only",
            "output_contract": "ClaudeSubscriptionQuotaV1@1.0",
        },
        {
            "capability_id": "authentication.health",
            "source_id": "claude.usage.ax-screen-reader.v1",
            "side_effect_class": "read_only",
            "output_contract": "AuthHealthObservationV1@1.0",
        },
        {
            "capability_id": "identity.verification",
            "source_id": "claude.auth.status",
            "side_effect_class": "read_only",
            "output_contract": "ObservedProfileIdentityV1@1",
        },
        {
            "capability_id": "authentication.reauthenticate",
            "source_id": "claude.auth.login",
            "side_effect_class": "managed_profile_write",
            "output_contract": "ProviderConnectionViewV1@1",
        },
    ]
    assert admission["compatibility_policy"] == {
        "version_scheme": "opaque_exact",
        "verified_versions": ["2.1.289"],
        "unknown_version_outcome": "unverified_provider_version",
        "maximum_quota_concurrency": 1,
        "minimum_quota_interval_ms": 300_000,
        "automatic_quota_retry_count": 0,
        "quota_deadline_ms": 30_000,
    }
    assert admission["managed_authentication_policy"] == {
        "owner_browser_interaction_required": True,
        "target_profile": "agentmonitor_managed_only",
        "protected_default_profile_write": False,
        "credential_read_or_persistence": False,
        "identity_match_required": True,
        "protected_default_identity_recheck_required": True,
    }
    assert admission["quota_parser_policy"] == {
        "required_windows": ["current_session", "current_week_all_models"],
        "required_reported_windows": ["current_week_all_models"],
        "missing_session": "unknown_after_settled_fresh_deadline_capture",
        "missing_session_omission_code": "claude_current_session_not_reported",
        "minimum_quiet_seconds": 1,
        "post_command_values_must_match_current_surface": True,
        "session_label_anywhere_in_capture": "fail_closed",
        "fixed_optional_windows": ["current_week_sonnet_only"],
        "missing_reset_display": "field_unknown",
        "model_specific_window": "bounded_omission",
        "model_specific_omission_code": ("claude_model_specific_window_unsupported"),
        "multiple_or_unallowlisted_model_windows": "fail_closed",
    }
    evidence = admission["evidence"]
    assert evidence["status"] == "passed"
    assert evidence["path"] == str(
        CLAUDE_VERSION_EVIDENCE_PATH.relative_to(REPOSITORY_ROOT)
    )
    assert (
        hashlib.sha256(CLAUDE_VERSION_EVIDENCE_PATH.read_bytes()).hexdigest()
        == (evidence["sha256"])
    )
    assert "claude.otel.metrics.http-json.v1 on 2.1.289" in admission["excluded"]
    assert "generic Linux process observation owned by A04/M06" in admission["excluded"]
    assert "protected default profile writes" in admission["excluded"]
    assert claude_manifest.M0_MAPPING_ID == admission["admission_id"]
    assert claude_manifest.M0_MAPPING_DIGEST == digest
    assert quota.provider_version_rule.verified_versions == ("2.1.289",)
    assert otel.provider_version_rule.verified_versions == ("2.1.282",)


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
    assert session.provider_version_rule.verified_versions == (
        CLAUDE_OTEL_PROVIDER_VERSION,
    )
    assert tuple(source.source_id for source in session.sources) == (
        CLAUDE_OTEL_SOURCE_ID,
    )
    assert session.sources[0].source_class == "documented_api"
    assert quota_manifest.m0_mapping_digest != otel_manifest.m0_mapping_digest
    assert otel_manifest.m0_mapping_digest == CLAUDE_OTEL_MAPPING_DIGEST
    assert CLAUDE_OTEL_MAPPING_PATH.is_file()
    assert (
        hashlib.sha256(CLAUDE_OTEL_MAPPING_PATH.read_bytes()).hexdigest()
        == CLAUDE_OTEL_MAPPING_DIGEST
    )
    assert quota_manifest.descriptor.adapter_id != otel_manifest.descriptor.adapter_id
