"""Authenticated side-effect-free provider capability transport."""

from datetime import UTC, datetime

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    availability,
    policy,
    reject_unknown_query,
)
from agentmonitor.api.v1.schemas.providers import (
    CapabilitySourceViewV1,
    ObservedAccountIdentityViewV1,
    ProviderCapabilityDeclarationPageV1,
    ProviderCapabilityDeclarationViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.provider_system.application.queries import (
    ProviderCapabilitiesNotFoundV1,
)
from fastapi import APIRouter, Path, Request

router = APIRouter(tags=["providers"])


@router.get(
    "/accounts/{account_id}/observed-identity",
    operation_id="provider_get_observed_account_identity_v1",
    response_model=ObservedAccountIdentityViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "GetVerifiedQuotaIdentityV1"),
)
def get_observed_identity(
    request: Request,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> ObservedAccountIdentityViewV1:
    authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset())
    services = observation_ports(request)
    try:
        account = services.get_account(OpaqueIdV1(account_id))
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    if account is None:
        raise ProblemError(404, "registry_subject_not_found")
    receipt = (
        services.get_verified_quota_identity(OpaqueIdV1(account_id))
        if services.get_verified_quota_identity is not None
        else None
    )
    return ObservedAccountIdentityViewV1(
        account_id=account_id,
        state="verified" if receipt else "unresolved",
        email=receipt.identity.email if receipt else None,
        provider_organization=receipt.identity.provider_organization
        if receipt
        else None,
        collection_run_id=receipt.collection_run_id.value if receipt else None,
        verified_at=receipt.identity.observed_at if receipt else None,
        provider_version=receipt.identity.provider_version if receipt else None,
        source_id="claude.auth.status.v1",
        scope="default_profile_quota",
        running_agent_correlation="unresolved",
        profile_protection=receipt.profile_protection if receipt else "unknown",
    )


@router.get(
    "/providers/{provider_key}/capabilities",
    operation_id="provider_get_capabilities_v1",
    response_model=ProviderCapabilityDeclarationPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:status", "GetProviderCapabilitiesV1"),
)
def get_capabilities(
    request: Request,
    provider_key: str = Path(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_-]{0,63}$",
    ),
) -> ProviderCapabilityDeclarationPageV1:
    authorize_request(request, "read:status")
    reject_unknown_query(request, frozenset())
    try:
        result = observation_ports(request).get_provider_capabilities.view(
            provider_key, as_of=datetime.now(UTC)
        )
    except ProviderCapabilitiesNotFoundV1:
        raise ProblemError(404, "provider_capabilities_not_found") from None
    manifest = result.manifest
    return ProviderCapabilityDeclarationPageV1(
        provider_key=manifest.descriptor.provider_key,
        adapter_id=manifest.descriptor.adapter_id,
        adapter_version=manifest.descriptor.adapter_version,
        protocol_minimum=manifest.descriptor.protocol_versions.minimum,
        protocol_maximum=manifest.descriptor.protocol_versions.maximum,
        manifest_schema_version=manifest.manifest_schema_version,
        m0_mapping_id=manifest.m0_mapping_id,
        m0_mapping_version=manifest.m0_mapping_version,
        items=tuple(
            ProviderCapabilityDeclarationViewV1(
                capability_id=item.capability_id,
                support_state=item.decision,
                stability=item.stability,
                reason_code=item.reason_code,
                evidence_reference=item.evidence_reference,
                side_effect_class=item.side_effect_class,
                schema_minimum=f"{item.schema_versions.minimum.major}.{item.schema_versions.minimum.minor}",
                schema_maximum=f"{item.schema_versions.maximum.major}.{item.schema_versions.maximum.minor}",
                port_type=item.port_type,
                output_schema=item.output_schema,
                platforms=item.platforms,
                sources=tuple(
                    CapabilitySourceViewV1(
                        source_id=source.source_id,
                        source_class=source.source_class,
                        stability=source.stability,
                        mechanism_version=source.mechanism_version,
                        credential_role=source.credential_role,
                        side_effect_class=source.side_effect_class,
                        evidence_reference=source.evidence_reference,
                        is_experimental=source.is_experimental,
                    )
                    for source in item.sources
                ),
            )
            for item in manifest.declarations
        ),
        availability=availability(result.availability),
    )
