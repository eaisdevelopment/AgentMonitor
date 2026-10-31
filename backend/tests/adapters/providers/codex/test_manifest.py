"""Pure Codex manifest policy for the exact M5 admission tuple."""

from agentmonitor.adapters.providers.codex.manifest import (
    CODEX_ACCOUNT_SOURCE_ID,
    CODEX_ADAPTER_ID,
    CODEX_ADAPTER_VERSION,
    CODEX_INSTALLATION_SOURCE_ID,
    CODEX_LOGIN_SOURCE_ID,
    CODEX_PARSER_VERSION,
    CODEX_PROVIDER_VERSION,
    CODEX_RATE_LIMITS_SOURCE_ID,
    CODEX_SCHEMA_BUNDLE_DIGEST,
    M0_MAPPING_DIGEST,
    M0_MAPPING_ID,
    build_codex_manifest,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CapabilityDeclarationV1,
    CapabilitySchemaVersionV1,
    SourcePolicyV1,
)
from agentmonitor.modules.provider_system.domain.protocol import (
    CapabilityResolutionV1,
    resolve_capability,
)


def _declaration(capability_id: str) -> CapabilityDeclarationV1:
    return next(
        item
        for item in build_codex_manifest().declarations
        if item.capability_id == capability_id
    )


def _policy(capability_id: str, *, experimental: bool) -> SourcePolicyV1:
    source_id = _declaration(capability_id).sources[0].source_id
    return SourcePolicyV1(
        policy_ref=OpaqueIdV1(f"codex-{capability_id}-policy"),
        source_ids=(source_id,),
        approved_fallbacks=(),
        experimental_grant_ref=(
            OpaqueIdV1(f"codex-{capability_id}-experimental-grant")
            if experimental
            else None
        ),
    )


def _resolve_quota(*, experimental: bool) -> CapabilityResolutionV1:
    return resolve_capability(
        build_codex_manifest(),
        approved_mapping_digest=M0_MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version=CODEX_PROVIDER_VERSION,
        platform_id="linux-x86_64",
        source_policy=_policy("subscription.quota", experimental=experimental),
    )


def test_manifest_binds_the_exact_accepted_codex_tuple() -> None:
    """M5-CDX-PURE-001..004: manifest identity and compatibility stay closed."""
    manifest = build_codex_manifest()

    assert manifest.descriptor.adapter_id == CODEX_ADAPTER_ID
    assert manifest.descriptor.adapter_version == CODEX_ADAPTER_VERSION
    assert CODEX_ADAPTER_VERSION == "1.0.2"
    assert CODEX_PARSER_VERSION == "1.0.1"
    assert manifest.descriptor.provider_key == "codex"
    assert manifest.descriptor.protocol_versions.includes("1.0.0")
    assert manifest.m0_mapping_id == M0_MAPPING_ID
    assert manifest.m0_mapping_digest == M0_MAPPING_DIGEST
    assert M0_MAPPING_ID == "M5-CDX-0-160-0-002"
    assert M0_MAPPING_DIGEST == (
        "417c46ba301f9c4217c606beed52be93c9bf497da9ca5b99ca4b1993167688d3"
    )
    assert len(M0_MAPPING_DIGEST) == 64

    assert tuple(item.capability_id for item in manifest.declarations) == (
        "installation.discovery",
        "identity.verification",
        "authentication.health",
        "subscription.quota",
        "authentication.reauthenticate",
    )
    assert all(
        item.provider_version_rule.verified_versions == (CODEX_PROVIDER_VERSION,)
        and item.provider_version_rule.scheme == "opaque_exact"
        and item.platforms == ("linux-x86_64",)
        and item.evidence_reference == M0_MAPPING_ID
        and item.constraints.maximum_concurrency == 1
        and item.constraints.automatic_retry_count == 0
        for item in manifest.declarations
    )


def test_manifest_keeps_installation_and_app_server_sources_distinct() -> None:
    """M5-CDX-PURE-005..008: source, effect and polling rules do not widen."""
    installation = _declaration("installation.discovery")
    identity = _declaration("identity.verification")
    auth_health = _declaration("authentication.health")
    quota = _declaration("subscription.quota")
    reauthentication = _declaration("authentication.reauthenticate")

    assert installation.decision == "supported"
    assert installation.side_effect_class == "read_only"
    assert installation.constraints.deadline_ms == 3_000
    assert installation.constraints.minimum_interval_ms == 0
    assert tuple(source.source_id for source in installation.sources) == (
        CODEX_INSTALLATION_SOURCE_ID,
    )
    assert installation.sources[0].source_class == "supported_cli"
    assert installation.sources[0].is_experimental is False

    assert identity.sources[0].source_id == CODEX_ACCOUNT_SOURCE_ID
    assert auth_health.sources[0].source_id == CODEX_ACCOUNT_SOURCE_ID
    assert quota.sources[0].source_id == CODEX_RATE_LIMITS_SOURCE_ID
    assert quota.constraints.minimum_interval_ms == 300_000
    assert quota.constraints.deadline_ms == 30_000
    assert all(
        CODEX_SCHEMA_BUNDLE_DIGEST in item.sources[0].mechanism_version
        for item in (identity, auth_health, quota)
    )
    assert all(
        item.decision == "experimental"
        and item.stability == "experimental"
        and item.side_effect_class == "managed_profile_write"
        and len(item.sources) == 1
        and item.sources[0].source_class == "experimental_private_or_browser"
        and item.sources[0].is_experimental is True
        for item in (identity, auth_health, quota)
    )
    assert reauthentication.decision == "experimental"
    assert reauthentication.stability == "experimental"
    assert reauthentication.side_effect_class == "managed_profile_write"
    assert reauthentication.constraints.deadline_ms == 600_000
    assert reauthentication.constraints.minimum_interval_ms == 0
    assert tuple(source.source_id for source in reauthentication.sources) == (
        CODEX_LOGIN_SOURCE_ID,
    )
    assert reauthentication.sources[0].credential_role == (
        "agentmonitor_managed_profile"
    )
    assert reauthentication.sources[0].source_class == (
        "experimental_private_or_browser"
    )
    assert reauthentication.sources[0].is_experimental is True


def test_unknown_codex_version_fails_closed_before_source_selection() -> None:
    """M5-CDX-PURE-009/010: another CLI version is unverified, not unsupported."""
    manifest = build_codex_manifest()
    resolution = resolve_capability(
        manifest,
        approved_mapping_digest=M0_MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="installation.discovery",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="0.160.1",
        platform_id="linux-x86_64",
        source_policy=_policy("installation.discovery", experimental=False),
    )

    assert resolution.code == "provider_version_unverified"
    assert resolution.declaration is None
    assert resolution.selected_source is None
    assert resolution.source_policy is None


def test_experimental_app_server_requires_an_explicit_scoped_grant() -> None:
    """M5-CDX-PURE-011/012: app-server cannot run by default or by fallback."""
    disabled = _resolve_quota(experimental=False)
    admitted = _resolve_quota(experimental=True)

    assert disabled.code == "capability_disabled"
    assert disabled.selected_source is None
    assert admitted.code == "resolved"
    assert admitted.selected_source is not None
    assert admitted.selected_source.source_id == CODEX_RATE_LIMITS_SOURCE_ID
