"""Authenticated M02 registry transports over published application ports."""

import re
from datetime import UTC, datetime
from typing import Literal, cast

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import (
    authorize_request,
    correlation_id,
    observation_ports,
)
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    availability,
    decode_cursor,
    page_meta,
    policy,
    reject_unknown_query,
)
from agentmonitor.api.v1.schemas.registry import (
    AccountBillingConnectionsV1,
    AccountPageV1,
    AccountViewV1,
    ArchiveAccountInputV1,
    ArchiveOrganizationInputV1,
    AssignAccountOrganizationInputV1,
    BillingConnectionViewV1,
    BillingCredentialStatusV1,
    BillingLocalMaintenanceV1,
    BillingLocalSetupV1,
    ChangeBillingScopeInputV1,
    CreateBillingConnectionInputV1,
    CreateOrganizationInputV1,
    MaskedRegistryFieldWireV1,
    OrganizationOrderingViewV1,
    OrganizationPageV1,
    OrganizationViewV1,
    ProviderInstallationPageV1,
    ProviderInstallationViewV1,
    ReconnectBillingConnectionInputV1,
    RegisterAccountInputV1,
    RenameAccountInputV1,
    RenameOrganizationInputV1,
    ReorderOrganizationsInputV1,
    SetAccountMonitoringInputV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingConnectionViewV1 as SourceBillingConnectionV1,
)
from agentmonitor.contracts.registry_billing_v1 import (
    ChangeBillingScopeCommandV1,
    CreateBillingConnectionCommandV1,
    ReconnectBillingConnectionCommandV1,
)
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1 as SourceAccountViewV1,
)
from agentmonitor.contracts.registry_v1 import MaskedRegistryFieldV1
from agentmonitor.contracts.registry_v1 import (
    OrganizationViewV1 as SourceOrganizationViewV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.provider_system.application.queries import (
    ProviderCapabilitiesNotFoundV1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    RegistryQueryUnavailableV1,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationCommandV1,
    EditOrganizationCommandV1,
    RegistryCommandConflictV1,
    ReorderOrganizationsCommandV1,
)
from fastapi import APIRouter, Query, Request, Response

router = APIRouter(tags=["registry"])


def _organization(item: SourceOrganizationViewV1) -> OrganizationViewV1:
    return OrganizationViewV1(
        organization_id=item.organization_id.value,
        name=item.name,
        description=item.description,
        display_order=item.display_order,
        lifecycle=item.lifecycle,
        active_account_count=item.active_account_count,
        archived_account_count=item.archived_account_count,
        record_version=item.record_version,
        registry_revision=item.registry_revision,
        created_at=item.created_at,
        updated_at=item.updated_at,
        archived_at=item.archived_at,
    )


def _account(item: SourceAccountViewV1) -> AccountViewV1:
    return AccountViewV1(
        account_id=item.account_id.value,
        provider_key=item.provider_key,
        friendly_name=item.friendly_name,
        organization_id=item.organization_id.value if item.organization_id else None,
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
        initial_connection_purpose=item.initial_connection_purpose,
        has_active_subscription_resource=item.has_active_subscription_resource,
    )


def _mutation_policy(port: str) -> dict[str, object]:
    return {
        "security": [
            {"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []},
            {"BearerTokenV1": []},
        ],
        "x-agentmonitor-auth-profile": "cookie_or_bearer",
        "x-agentmonitor-required-permission": "write:accounts",
        "x-agentmonitor-application-port": port,
        "x-agentmonitor-replay-policy": "replay_safe_representation",
        "x-agentmonitor-error-schema": "SafeProblemV1",
        "parameters": [
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "description": "Stable operation key for safe retries.",
                "schema": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9_-]{16,128}$",
                },
            }
        ],
    }


def _idempotency_key(request: Request) -> OpaqueIdV1:
    value = request.headers.get("idempotency-key")
    if value is None or re.fullmatch(r"[A-Za-z0-9_-]{16,128}\Z", value) is None:
        raise ProblemError(400, "invalid_idempotency_key")
    return OpaqueIdV1(value)


def _version_policy(port: str, *, idempotent: bool = False) -> dict[str, object]:
    result = _mutation_policy(port)
    parameters = [
        {
            "name": "If-Match",
            "in": "header",
            "required": True,
            "description": "Current resource ETag.",
            "schema": {"type": "string", "maxLength": 160},
        }
    ]
    if idempotent:
        parameters.extend(cast(list[dict[str, object]], result["parameters"]))
    result["parameters"] = parameters
    return result


def _expected_version(request: Request, subject_id: str) -> int:
    value = request.headers.get("if-match")
    if value is None:
        raise ProblemError(428, "precondition_required")
    match = re.fullmatch(r'"' + re.escape(subject_id) + r'\.(\d+)"\Z', value)
    if match is None or int(match.group(1)) < 1:
        raise ProblemError(400, "invalid_precondition")
    return int(match.group(1))


def _edit_account(
    request: Request,
    response: Response,
    account_id: str,
    action: Literal["rename", "assign", "monitoring", "archive", "restore"],
    *,
    friendly_name: str | None = None,
    organization_id: str | None = None,
    monitoring_preference: Literal["enabled", "disabled"] | None = None,
) -> AccountViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    expected_version = _expected_version(request, account_id)
    command_id = (
        _idempotency_key(request)
        if action == "archive"
        else OpaqueIdV1(correlation_id(request))
    )
    try:
        command = EditAccountCommandV1(
            account_id=OpaqueIdV1(account_id),
            expected_version=expected_version,
            principal_id=caller.principal.principal_id,
            command_id=command_id,
            action=action,
            requested_at=datetime.now(UTC),
            friendly_name=friendly_name,
            monitoring_preference=monitoring_preference,
            organization_id=(
                OpaqueIdV1(organization_id) if organization_id is not None else None
            ),
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    try:
        item = observation_ports(request).edit_account(command)
    except RegistryCommandConflictV1 as error:
        code = str(error)
        if code == "registry_subject_not_found":
            raise ProblemError(404, code) from None
        if code == "registry_version_conflict":
            raise ProblemError(412, code) from None
        if code not in {
            "registry_alias_conflict",
            "registry_monitoring_not_eligible",
            "registry_organization_unavailable",
            "registry_subject_archived",
            "registry_subject_not_archived",
            "registry_idempotency_conflict",
            "registry_replay_stale",
        }:
            code = "registry_conflict"
        raise ProblemError(409, code) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    response.headers["ETag"] = f'"{item.account_id.value}.{item.record_version}"'
    return _account(item)


def _masked(item: MaskedRegistryFieldV1) -> MaskedRegistryFieldWireV1:
    return MaskedRegistryFieldWireV1(
        state=item.state,
        masked_value=item.masked_value,
        reason_code=item.reason_code,
    )


def _assert_account_matches(item: SourceAccountViewV1, account_id: OpaqueIdV1) -> None:
    if item.account_id != account_id:
        raise ProblemError(503, "registry_repository_unavailable")


@router.get(
    "/organizations",
    operation_id="registry_list_organizations_v1",
    response_model=OrganizationPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "ListOrganizationsV1"),
)
def list_organizations(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
) -> OrganizationPageV1:
    caller = authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset({"limit", "cursor"}))
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="registry_list_organizations_v1",
        limit=limit,
        filters={},
    )
    try:
        result = observation_ports(request).list_organizations.page(
            as_of=datetime.now(UTC), limit=limit, after_key=after_key
        )
    except RegistryQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return OrganizationPageV1(
        items=tuple(_organization(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="registry_list_organizations_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters={},
        ),
        availability=availability(result.availability),
    )


@router.post(
    "/organizations",
    operation_id="registry_create_organization_v1",
    status_code=201,
    response_model=OrganizationViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("CreateOrganizationV1"),
)
def create_organization(
    input: CreateOrganizationInputV1, request: Request, response: Response
) -> OrganizationViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    command_id = _idempotency_key(request)
    try:
        command = CreateOrganizationCommandV1(
            command_id=command_id,
            principal_id=caller.principal.principal_id,
            name=input.name,
            description=input.description,
            requested_at=datetime.now(UTC),
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    try:
        item = observation_ports(request).create_organization(command)
    except RegistryCommandConflictV1 as error:
        code = str(error)
        if code not in {"registry_idempotency_conflict", "registry_name_conflict"}:
            code = "registry_conflict"
        raise ProblemError(409, code) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    response.headers["ETag"] = f'"{item.organization_id.value}.{item.record_version}"'
    response.headers["Location"] = f"/api/v1/organizations/{item.organization_id.value}"
    return _organization(item)


@router.post(
    "/organization-orderings",
    operation_id="registry_reorder_organizations_v1",
    response_model=OrganizationOrderingViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("ReorderOrganizationsV1"),
)
def reorder_organizations(
    input: ReorderOrganizationsInputV1,
    request: Request,
    response: Response,
) -> OrganizationOrderingViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    command_id = _idempotency_key(request)
    try:
        command = ReorderOrganizationsCommandV1(
            ordered_organization_ids=tuple(
                OpaqueIdV1(item) for item in input.ordered_organization_ids
            ),
            expected_registry_revision=input.expected_registry_revision,
            principal_id=caller.principal.principal_id,
            command_id=command_id,
            requested_at=datetime.now(UTC),
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    try:
        item = observation_ports(request).reorder_organizations(command)
    except RegistryCommandConflictV1 as error:
        code = str(error)
        if code == "registry_revision_conflict":
            raise ProblemError(412, code) from None
        if code not in {
            "registry_order_set_invalid",
            "registry_idempotency_conflict",
            "registry_replay_stale",
        }:
            code = "registry_conflict"
        raise ProblemError(409, code) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    response.headers["ETag"] = f'"registry.{item.registry_revision}"'
    return OrganizationOrderingViewV1(
        organization_ids=tuple(value.value for value in item.organization_ids),
        registry_revision=item.registry_revision,
    )


@router.get(
    "/organizations/{organization_id}",
    operation_id="registry_get_organization_v1",
    response_model=OrganizationViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "GetOrganizationV1"),
)
def get_organization(
    organization_id: str,
    request: Request,
    response: Response,
) -> OrganizationViewV1:
    authorize_request(request, "read:accounts")
    try:
        item = observation_ports(request).get_organization(OpaqueIdV1(organization_id))
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    if item is None:
        raise ProblemError(404, "registry_subject_not_found")
    response.headers["ETag"] = f'"{item.organization_id.value}.{item.record_version}"'
    return _organization(item)


def _edit_organization(
    request: Request,
    response: Response,
    organization_id: str,
    action: Literal["rename", "archive", "restore"],
    *,
    name: str | None = None,
) -> OrganizationViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    expected_version = _expected_version(request, organization_id)
    command_id = (
        _idempotency_key(request)
        if action == "archive"
        else OpaqueIdV1(correlation_id(request))
    )
    try:
        command = EditOrganizationCommandV1(
            organization_id=OpaqueIdV1(organization_id),
            expected_version=expected_version,
            principal_id=caller.principal.principal_id,
            command_id=command_id,
            action=action,
            requested_at=datetime.now(UTC),
            name=name,
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    try:
        item = observation_ports(request).edit_organization(command)
    except RegistryCommandConflictV1 as error:
        code = str(error)
        if code == "registry_subject_not_found":
            raise ProblemError(404, code) from None
        if code == "registry_version_conflict":
            raise ProblemError(412, code) from None
        if code not in {
            "registry_name_conflict",
            "registry_organization_not_empty",
            "registry_subject_archived",
            "registry_subject_not_archived",
            "registry_idempotency_conflict",
            "registry_replay_stale",
        }:
            code = "registry_conflict"
        raise ProblemError(409, code) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    response.headers["ETag"] = f'"{item.organization_id.value}.{item.record_version}"'
    return _organization(item)


@router.patch(
    "/organizations/{organization_id}",
    operation_id="registry_rename_organization_v1",
    response_model=OrganizationViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("RenameOrganizationV1"),
)
def rename_organization(
    organization_id: str,
    input: RenameOrganizationInputV1,
    request: Request,
    response: Response,
) -> OrganizationViewV1:
    return _edit_organization(
        request, response, organization_id, "rename", name=input.name
    )


@router.post(
    "/organizations/{organization_id}/archivals",
    operation_id="registry_archive_organization_v1",
    response_model=OrganizationViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("ArchiveOrganizationV1", idempotent=True),
)
def archive_organization(
    organization_id: str,
    input: ArchiveOrganizationInputV1,
    request: Request,
    response: Response,
) -> OrganizationViewV1:
    return _edit_organization(request, response, organization_id, "archive")


@router.delete(
    "/organizations/{organization_id}/archival",
    operation_id="registry_restore_organization_v1",
    response_model=OrganizationViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("RestoreOrganizationV1"),
)
def restore_organization(
    organization_id: str,
    request: Request,
    response: Response,
) -> OrganizationViewV1:
    return _edit_organization(request, response, organization_id, "restore")


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
        items=tuple(_account(item) for item in result.items),
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


@router.post(
    "/accounts",
    operation_id="registry_register_account_v1",
    status_code=201,
    response_model=AccountViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_mutation_policy("RegisterAccountV1"),
)
def register_account(
    input: RegisterAccountInputV1, request: Request, response: Response
) -> AccountViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    command_id = _idempotency_key(request)
    try:
        manifest = observation_ports(request).get_provider_capabilities(
            input.provider_key
        )
    except ProviderCapabilitiesNotFoundV1:
        raise ProblemError(422, "registry_provider_unavailable") from None
    try:
        command = CreatePendingAccountCommandV1(
            command_id=command_id,
            principal_id=caller.principal.principal_id,
            provider_key=input.provider_key,
            manifest_reference=get_manifest_fingerprint_v1(manifest),
            initial_connection_purpose=input.initial_connection_purpose,
            friendly_name=input.friendly_name,
            organization_id=(
                OpaqueIdV1(input.organization_id)
                if input.organization_id is not None
                else None
            ),
            requested_at=datetime.now(UTC),
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    try:
        item = observation_ports(request).register_account.pending(command)
    except RegistryCommandConflictV1 as error:
        code = str(error)
        if code not in {
            "registry_idempotency_conflict",
            "registry_alias_conflict",
            "registry_organization_unavailable",
            "registry_provider_unavailable",
        }:
            code = "registry_conflict"
        raise ProblemError(409, code) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    response.headers["ETag"] = f'"{item.account_id.value}.{item.record_version}"'
    response.headers["Location"] = f"/api/v1/accounts/{item.account_id.value}"
    return _account(item)


@router.get(
    "/accounts/{account_id}",
    operation_id="registry_get_account_v1",
    response_model=AccountViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "GetAccountV1"),
)
def get_account(account_id: str, request: Request, response: Response) -> AccountViewV1:
    authorize_request(request, "read:accounts")
    try:
        item = observation_ports(request).get_account(OpaqueIdV1(account_id))
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    if item is None:
        raise ProblemError(404, "registry_subject_not_found")
    _assert_account_matches(item, OpaqueIdV1(account_id))
    response.headers["ETag"] = f'"{item.account_id.value}.{item.record_version}"'
    return _account(item)


@router.patch(
    "/accounts/{account_id}",
    operation_id="registry_rename_account_v1",
    response_model=AccountViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("RenameAccountV1"),
)
def rename_account(
    account_id: str,
    input: RenameAccountInputV1,
    request: Request,
    response: Response,
) -> AccountViewV1:
    return _edit_account(
        request, response, account_id, "rename", friendly_name=input.friendly_name
    )


@router.put(
    "/accounts/{account_id}/organization",
    operation_id="registry_assign_account_organization_v1",
    response_model=AccountViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("AssignAccountOrganizationV1"),
)
def assign_account_organization(
    account_id: str,
    input: AssignAccountOrganizationInputV1,
    request: Request,
    response: Response,
) -> AccountViewV1:
    return _edit_account(
        request,
        response,
        account_id,
        "assign",
        organization_id=input.organization_id,
    )


@router.put(
    "/accounts/{account_id}/monitoring",
    operation_id="registry_set_account_monitoring_v1",
    response_model=AccountViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("SetAccountMonitoringV1"),
)
def set_account_monitoring(
    account_id: str,
    input: SetAccountMonitoringInputV1,
    request: Request,
    response: Response,
) -> AccountViewV1:
    return _edit_account(
        request,
        response,
        account_id,
        "monitoring",
        monitoring_preference=input.monitoring_preference,
    )


@router.post(
    "/accounts/{account_id}/archivals",
    operation_id="registry_archive_account_v1",
    response_model=AccountViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("ArchiveAccountV1", idempotent=True),
)
def archive_account(
    account_id: str,
    input: ArchiveAccountInputV1,
    request: Request,
    response: Response,
) -> AccountViewV1:
    return _edit_account(request, response, account_id, "archive")


@router.delete(
    "/accounts/{account_id}/archival",
    operation_id="registry_restore_account_v1",
    response_model=AccountViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("RestoreAccountV1"),
)
def restore_account(
    account_id: str,
    request: Request,
    response: Response,
) -> AccountViewV1:
    return _edit_account(request, response, account_id, "restore")


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


def _billing_connection(item: SourceBillingConnectionV1) -> BillingConnectionViewV1:
    return BillingConnectionViewV1(
        account_id=item.account_id.value,
        resource_id=item.resource_id.value,
        provider_key=item.provider_key,
        scope_id=item.scope_id,
        scope_evidence=item.scope_evidence,
        scope_generation=item.scope_generation,
        monitoring_preference=item.monitoring_preference,
        lifecycle=item.lifecycle,
        record_version=item.record_version,
        registry_revision=item.registry_revision,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get(
    "/accounts/{account_id}/billing-connections",
    operation_id="registry_get_billing_connections_v1",
    response_model=AccountBillingConnectionsV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "BillingConnectionPortV1.get"),
)
def get_billing_connections(
    account_id: str,
    request: Request,
    response: Response,
) -> AccountBillingConnectionsV1:
    authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset())
    port = observation_ports(request).billing_connections
    if port is None:
        raise ProblemError(503, "registry_repository_unavailable")
    try:
        status = port.get(OpaqueIdV1(account_id))
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    if status is None:
        raise ProblemError(404, "registry_subject_not_found")
    response.headers["Cache-Control"] = "no-store"
    # Account record_version fences metadata mutations, but does not version
    # credential lifecycle changes in this composite view. Do not advertise it
    # as a strong representation validator.
    setup_port = observation_ports(request).billing_local_setup
    setup = None if setup_port is None else setup_port.describe(status)
    maintenance = None if setup_port is None else setup_port.maintenance(status)
    return AccountBillingConnectionsV1(
        account_id=status.account_id.value,
        provider_key=status.provider_key,
        account_lifecycle=status.account_lifecycle,
        account_record_version=status.account_record_version,
        can_add_connection=status.can_add_connection,
        reason_code=status.reason_code,
        connections=tuple(_billing_connection(item) for item in status.connections),
        local_setup=(
            None
            if setup is None
            else BillingLocalSetupV1(
                host_label=setup.host_label,
                command=setup.command,
            )
        ),
        local_maintenance=(
            None
            if maintenance is None
            else BillingLocalMaintenanceV1(
                host_label=maintenance.host_label,
                disconnect_command=maintenance.disconnect_command,
                cleanup_command=maintenance.cleanup_command,
            )
        ),
        credential_status=(
            None
            if status.credential_status is None
            else BillingCredentialStatusV1(
                state=status.credential_status.state,
                active_generation=status.credential_status.active_generation,
                pending_generation=status.credential_status.pending_generation,
                cleanup_required=status.credential_status.cleanup_required,
            )
        ),
    )


@router.post(
    "/accounts/{account_id}/billing-connections",
    operation_id="registry_create_billing_connection_v1",
    status_code=201,
    response_model=BillingConnectionViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("BillingConnectionPortV1.create", idempotent=True),
)
def create_billing_connection(
    account_id: str,
    input: CreateBillingConnectionInputV1,
    request: Request,
    response: Response,
) -> BillingConnectionViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    command = CreateBillingConnectionCommandV1(
        account_id=OpaqueIdV1(account_id),
        expected_account_version=_expected_version(request, account_id),
        principal_id=caller.principal.principal_id,
        command_id=_idempotency_key(request),
        scope_id=input.scope_id,
        requested_at=datetime.now(UTC),
    )
    port = observation_ports(request).billing_connections
    if port is None:
        raise ProblemError(503, "registry_repository_unavailable")
    try:
        item = port.create(command)
    except RegistryCommandConflictV1 as error:
        code = str(error)
        if code == "registry_subject_not_found":
            raise ProblemError(404, code) from None
        if code == "registry_version_conflict":
            raise ProblemError(412, code) from None
        if code not in {"registry_idempotency_conflict", "registry_replay_stale"}:
            code = "registry_conflict"
        raise ProblemError(409, code) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    response.headers["Cache-Control"] = "no-store"
    response.headers["ETag"] = f'"{item.resource_id.value}.{item.record_version}"'
    return _billing_connection(item)


@router.put(
    "/accounts/{account_id}/billing-connections/{resource_id}/scope",
    operation_id="registry_change_billing_scope_v1",
    response_model=BillingConnectionViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy(
        "BillingConnectionPortV1.change_scope", idempotent=True
    ),
)
def change_billing_scope(
    account_id: str,
    resource_id: str,
    input: ChangeBillingScopeInputV1,
    request: Request,
    response: Response,
) -> BillingConnectionViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    command = ChangeBillingScopeCommandV1(
        account_id=OpaqueIdV1(account_id),
        resource_id=OpaqueIdV1(resource_id),
        expected_account_version=input.expected_account_version,
        expected_connection_version=_expected_version(request, resource_id),
        expected_scope_generation=input.expected_scope_generation,
        scope_id=input.scope_id,
        principal_id=caller.principal.principal_id,
        command_id=_idempotency_key(request),
        requested_at=datetime.now(UTC),
    )
    port = observation_ports(request).billing_connections
    if port is None:
        raise ProblemError(503, "registry_repository_unavailable")
    try:
        item = port.change_scope(command)
    except RegistryCommandConflictV1 as error:
        code = str(error)
        if code == "registry_subject_not_found":
            raise ProblemError(404, code) from None
        if code == "registry_version_conflict":
            raise ProblemError(412, code) from None
        if code not in {"registry_idempotency_conflict", "registry_replay_stale"}:
            code = "registry_conflict"
        raise ProblemError(409, code) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    response.headers["Cache-Control"] = "no-store"
    response.headers["ETag"] = f'"{item.resource_id.value}.{item.record_version}"'
    return _billing_connection(item)


@router.post(
    "/accounts/{account_id}/billing-connections/{resource_id}/reconnect",
    operation_id="registry_reconnect_billing_connection_v1",
    response_model=BillingConnectionViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("BillingConnectionPortV1.reconnect", idempotent=True),
)
def reconnect_billing_connection(
    account_id: str,
    resource_id: str,
    input: ReconnectBillingConnectionInputV1,
    request: Request,
    response: Response,
) -> BillingConnectionViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    command = ReconnectBillingConnectionCommandV1(
        account_id=OpaqueIdV1(account_id),
        resource_id=OpaqueIdV1(resource_id),
        expected_account_version=input.expected_account_version,
        expected_connection_version=_expected_version(request, resource_id),
        expected_scope_generation=input.expected_scope_generation,
        principal_id=caller.principal.principal_id,
        command_id=_idempotency_key(request),
        requested_at=datetime.now(UTC),
    )
    port = observation_ports(request).billing_connections
    if port is None:
        raise ProblemError(503, "registry_repository_unavailable")
    try:
        item = port.reconnect(command)
    except RegistryCommandConflictV1 as error:
        code = str(error)
        if code == "registry_subject_not_found":
            raise ProblemError(404, code) from None
        if code == "registry_version_conflict":
            raise ProblemError(412, code) from None
        if code not in {"registry_idempotency_conflict", "registry_replay_stale"}:
            code = "registry_conflict"
        raise ProblemError(409, code) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    response.headers["Cache-Control"] = "no-store"
    response.headers["ETag"] = f'"{item.resource_id.value}.{item.record_version}"'
    return _billing_connection(item)
