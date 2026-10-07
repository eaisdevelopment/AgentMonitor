"""Exact Codex CLI capabilities admitted by the bounded M5 evidence."""

from typing import Literal

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.provider_system_v1 import (
    AdapterDescriptorV1,
    CapabilityDecisionStateV1,
    CapabilityDeclarationV1,
    CapabilityManifestV1,
    CapabilitySchemaRangeV1,
    CapabilitySchemaVersionV1,
    CollectionConstraintV1,
    ProtocolVersionRangeV1,
    ProviderSourceV1,
    ProviderVersionRuleV1,
    SideEffectClassV1,
    StabilityV1,
)

SourceClassV1 = Literal[
    "documented_api",
    "supported_cli",
    "approved_local_metadata",
    "experimental_private_or_browser",
]

CODEX_ADAPTER_ID = "agentmonitor.codex"
CODEX_ADAPTER_VERSION = "1.0.1"
CODEX_PARSER_VERSION = "1.0.0"
CODEX_PROVIDER_VERSION = "0.160.0"
CODEX_INSTALLATION_SOURCE_ID = "codex.version.banner.v1"
CODEX_ACCOUNT_SOURCE_ID = "codex.app-server.account-read.v2"
CODEX_RATE_LIMITS_SOURCE_ID = "codex.app-server.account-rate-limits-read.v2"
CODEX_LOGIN_SOURCE_ID = "codex.login.browser.v1"
CODEX_SCHEMA_BUNDLE_DIGEST = (
    "36bd8e1d76b12b89b06446a85c45e957945eb8cb63b05061264c3dec97f625da"
)
CODEX_APP_SERVER_MECHANISM_VERSION = (
    f"codex-app-server-v2@0.160.0+schema.{CODEX_SCHEMA_BUNDLE_DIGEST}"
)
M0_MAPPING_ID = "M5-CDX-0-160-0-002"
# SHA-256 of the corrected exact-version source decision in
# docs/evidence/m5-codex-read-side-effect-blocker.md.
M0_MAPPING_DIGEST = "2ac086063dbfdae1c673f7cd899ac60d6d559bc72dbb598c6e5196c43567a204"


def _schema_v1() -> CapabilitySchemaRangeV1:
    return CapabilitySchemaRangeV1(
        CapabilitySchemaVersionV1(1, 0), CapabilitySchemaVersionV1(1, 0)
    )


def _constraints(
    *, deadline_ms: int, minimum_interval_ms: int
) -> CollectionConstraintV1:
    return CollectionConstraintV1(
        deadline_ms=deadline_ms,
        minimum_interval_ms=minimum_interval_ms,
        maximum_concurrency=1,
        automatic_retry_count=0,
        provider_request_count=None,
        provider_request_count_availability=FieldAvailabilityV1("unknown"),
    )


def _source(
    *,
    source_id: str,
    capability_id: str,
    source_class: SourceClassV1,
    stability: StabilityV1,
    credential_role: str,
    side_effect_class: SideEffectClassV1,
    mechanism_version: str,
) -> ProviderSourceV1:
    return ProviderSourceV1(
        source_id=source_id,
        provider_key="codex",
        capability_id=capability_id,
        source_class=source_class,
        stability=stability,
        mechanism_version=mechanism_version,
        credential_role=credential_role,
        side_effect_class=side_effect_class,
        evidence_reference=M0_MAPPING_ID,
        is_experimental=source_class == "experimental_private_or_browser",
    )


def _declaration(
    *,
    capability_id: str,
    source_id: str,
    source_class: SourceClassV1,
    decision: CapabilityDecisionStateV1,
    stability: StabilityV1,
    credential_role: str,
    side_effect_class: SideEffectClassV1,
    port_type: str,
    output_schema: str,
    rule_suffix: str,
    deadline_ms: int,
    minimum_interval_ms: int,
    mechanism_version: str,
) -> CapabilityDeclarationV1:
    source = _source(
        source_id=source_id,
        capability_id=capability_id,
        source_class=source_class,
        stability=stability,
        credential_role=credential_role,
        side_effect_class=side_effect_class,
        mechanism_version=mechanism_version,
    )
    return CapabilityDeclarationV1(
        capability_id=capability_id,
        schema_versions=_schema_v1(),
        decision=decision,
        stability=stability,
        reason_code=(
            "accepted_exact_installed_tuple"
            if decision == "supported"
            else "approved_experimental_exact_tuple"
        ),
        evidence_reference=M0_MAPPING_ID,
        port_type=port_type,
        output_schema=output_schema,
        sources=(source,),
        provider_version_rule=ProviderVersionRuleV1(
            rule_id=f"codex-cli-0-160-0-{rule_suffix}-exact",
            scheme="opaque_exact",
            verified_versions=(CODEX_PROVIDER_VERSION,),
        ),
        constraints=_constraints(
            deadline_ms=deadline_ms,
            minimum_interval_ms=minimum_interval_ms,
        ),
        side_effect_class=side_effect_class,
        platforms=("linux-x86_64",),
    )


def build_codex_manifest() -> CapabilityManifestV1:
    """Build the closed exact-version manifest without provider I/O."""
    installation = _declaration(
        capability_id="installation.discovery",
        source_id=CODEX_INSTALLATION_SOURCE_ID,
        source_class="supported_cli",
        decision="supported",
        stability="documented",
        credential_role="none",
        side_effect_class="read_only",
        port_type="InstallationDiscoveryPortV1",
        output_schema="DiscoveryOutcomeV1",
        rule_suffix="installation",
        deadline_ms=3_000,
        minimum_interval_ms=0,
        mechanism_version="codex-cli@0.160.0",
    )
    identity = _declaration(
        capability_id="identity.verification",
        source_id=CODEX_ACCOUNT_SOURCE_ID,
        source_class="experimental_private_or_browser",
        decision="experimental",
        stability="experimental",
        credential_role="agentmonitor_managed_profile",
        side_effect_class="managed_profile_write",
        port_type="ProviderCapabilityPortV1",
        output_schema="ObservedProfileIdentityV1",
        rule_suffix="identity",
        deadline_ms=30_000,
        minimum_interval_ms=0,
        mechanism_version=CODEX_APP_SERVER_MECHANISM_VERSION,
    )
    authentication_health = _declaration(
        capability_id="authentication.health",
        source_id=CODEX_ACCOUNT_SOURCE_ID,
        source_class="experimental_private_or_browser",
        decision="experimental",
        stability="experimental",
        credential_role="agentmonitor_managed_profile",
        side_effect_class="managed_profile_write",
        port_type="AuthenticationHealthPortV1",
        output_schema="AuthHealthObservationV1",
        rule_suffix="auth-health",
        deadline_ms=30_000,
        minimum_interval_ms=0,
        mechanism_version=CODEX_APP_SERVER_MECHANISM_VERSION,
    )
    quota = _declaration(
        capability_id="subscription.quota",
        source_id=CODEX_RATE_LIMITS_SOURCE_ID,
        source_class="experimental_private_or_browser",
        decision="experimental",
        stability="experimental",
        credential_role="agentmonitor_managed_profile",
        side_effect_class="managed_profile_write",
        port_type="SubscriptionQuotaPortV1",
        output_schema="CodexSubscriptionQuotaV1",
        rule_suffix="quota",
        deadline_ms=30_000,
        minimum_interval_ms=300_000,
        mechanism_version=CODEX_APP_SERVER_MECHANISM_VERSION,
    )
    reauthentication = _declaration(
        capability_id="authentication.reauthenticate",
        source_id=CODEX_LOGIN_SOURCE_ID,
        source_class="experimental_private_or_browser",
        decision="experimental",
        stability="experimental",
        credential_role="agentmonitor_managed_profile",
        side_effect_class="managed_profile_write",
        port_type="ProviderConnectionPortV1",
        output_schema="ProviderConnectionViewV1",
        rule_suffix="managed-reauth",
        deadline_ms=600_000,
        minimum_interval_ms=0,
        mechanism_version="codex-cli@0.160.0",
    )
    return CapabilityManifestV1(
        descriptor=AdapterDescriptorV1(
            adapter_id=CODEX_ADAPTER_ID,
            adapter_version=CODEX_ADAPTER_VERSION,
            provider_key="codex",
            protocol_versions=ProtocolVersionRangeV1("1.0.0", "1.0.0"),
            build_identity="agentmonitor-codex-v1",
        ),
        manifest_schema_version="1.0.0",
        declarations=(
            installation,
            identity,
            authentication_health,
            quota,
            reauthentication,
        ),
        m0_mapping_id=M0_MAPPING_ID,
        m0_mapping_version="1.0.0",
        m0_mapping_digest=M0_MAPPING_DIGEST,
    )
