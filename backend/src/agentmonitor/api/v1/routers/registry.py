"""Authenticated, read-only M02 registry transports."""

from datetime import UTC, datetime

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    availability,
    decode_cursor,
    page_meta,
    policy,
    reject_unknown_query,
)
from agentmonitor.api.v1.schemas.registry import (
    AccountPageV1,
    AccountViewV1,
    MaskedRegistryFieldWireV1,
    ProviderInstallationPageV1,
    ProviderInstallationViewV1,
)
from agentmonitor.contracts.registry_v1 import MaskedRegistryFieldV1
from agentmonitor.modules.registry.application.accounts import (
    RegistryQueryUnavailableV1,
)
from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["registry"])


def _masked(item: MaskedRegistryFieldV1) -> MaskedRegistryFieldWireV1:
    return MaskedRegistryFieldWireV1(
        state=item.state,
        masked_value=item.masked_value,
        reason_code=item.reason_code,
    )


@router.get(
    "/accounts",
    operation_id="registry_list_accounts_v1",
    response_model=AccountPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "ListAccountsV1"),
)
def list_accounts(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
    provider_key: str | None = Query(None, min_length=1, max_length=64),
) -> AccountPageV1:
    caller = authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset({"limit", "cursor", "provider_key"}))
    as_of = datetime.now(UTC)
    filters = {"provider_key": provider_key}
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="registry_list_accounts_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = observation_ports(request).list_accounts.page(
            provider_key, as_of=as_of, limit=limit, after_key=after_key
        )
    except RegistryQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return AccountPageV1(
        items=tuple(
            AccountViewV1(
                account_id=item.account_id.value,
                provider_key=item.provider_key,
                friendly_name=item.friendly_name,
                organization_id=item.organization_id.value
                if item.organization_id
                else None,
                lifecycle=item.lifecycle,
                monitoring_preference=item.monitoring_preference,
                is_effective_monitoring_enabled=item.is_effective_monitoring_enabled,
                effective_monitoring_reason=item.effective_monitoring_reason,
                identity_state=item.identity_state,
                masked_identity=_masked(item.masked_identity),
                record_version=item.record_version,
                registry_revision=item.registry_revision,
                created_at=item.created_at,
                updated_at=item.updated_at,
                archived_at=item.archived_at,
            )
            for item in result.items
        ),
        page=page_meta(
            request,
            caller,
            operation_id="registry_list_accounts_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.get(
    "/provider-installations",
    operation_id="registry_list_provider_installations_v1",
    response_model=ProviderInstallationPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "ListProviderInstallationsV1"),
)
def list_provider_installations(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
    provider_key: str | None = Query(None, min_length=1, max_length=64),
) -> ProviderInstallationPageV1:
    caller = authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset({"limit", "cursor", "provider_key"}))
    as_of = datetime.now(UTC)
    filters = {"provider_key": provider_key}
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="registry_list_provider_installations_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = observation_ports(request).list_provider_installations.page(
            provider_key, as_of=as_of, limit=limit, after_key=after_key
        )
    except RegistryQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return ProviderInstallationPageV1(
        items=tuple(
            ProviderInstallationViewV1(
                provider_installation_id=item.provider_installation_id.value,
                provider_key=item.provider_key,
                platform_key=item.platform_key,
                version=_masked(item.version),
                presence_state=item.presence_state,
                first_seen_at=item.first_seen_at,
                last_seen_at=item.last_seen_at,
                record_version=item.record_version,
                registry_revision=item.registry_revision,
            )
            for item in result.items
        ),
        page=page_meta(
            request,
            caller,
            operation_id="registry_list_provider_installations_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )
