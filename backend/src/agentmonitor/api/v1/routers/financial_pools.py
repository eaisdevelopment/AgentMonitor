"""Financial-pool metadata via M02's published port; no secret/provider access."""

from datetime import UTC, datetime
from typing import Literal

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    policy,
    reject_unknown_query,
)
from agentmonitor.api.v1.routers.registry import (
    _expected_version,
    _idempotency_key,
    _version_policy,
)
from agentmonitor.api.v1.schemas.financial_pools import (
    AssignFinancialPoolInputV1,
    EditFinancialPoolInputV1,
    FinancialPoolConfigurationV1,
    FinancialPoolPageV1,
    FinancialPoolViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    AssignFinancialPoolCommandV1,
    EditFinancialPoolCommandV1,
    FinancialPoolRegistryPortV1,
)
from agentmonitor.contracts.registry_billing_v1 import (
    FinancialPoolConfigurationV1 as Configuration,
)
from agentmonitor.contracts.registry_billing_v1 import (
    FinancialPoolViewV1 as Pool,
)
from fastapi import APIRouter, Path, Query, Request, Response

router = APIRouter(tags=["registry"])
_ERRORS = {
    "financial_pool_scope_changed": 409,
    "financial_pool_incompatible": 409,
    "financial_pool_organization_unavailable": 409,
    "financial_pool_unavailable": 409,
    "financial_pool_time_conflict": 409,
    "registry_revision_conflict": 412,
    "registry_version_conflict": 412,
    "registry_idempotency_conflict": 409,
    "registry_replay_stale": 409,
    "registry_subject_not_found": 404,
}


def _port(request: Request) -> FinancialPoolRegistryPortV1:
    result = observation_ports(request).financial_pools
    if result is None:
        raise ProblemError(503, "financial_pool_query_unavailable")
    return result


def _error(error: ValueError) -> ProblemError:
    code = str(error)
    return (
        ProblemError(_ERRORS[code], code)
        if code in _ERRORS
        else ProblemError(503, "financial_pool_query_unavailable")
    )


def _pool(value: Pool) -> FinancialPoolViewV1:
    return FinancialPoolViewV1(
        pool_id=value.pool_id.value,
        provider_key=value.provider_key,
        selector=value.selector,
        display_name=value.display_name,
        primary_organization_id=value.primary_organization_id.value
        if value.primary_organization_id
        else None,
        record_version=value.record_version,
        registry_revision=value.registry_revision,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def _configuration(value: Configuration) -> FinancialPoolConfigurationV1:
    scope = value.scope
    return FinancialPoolConfigurationV1(
        account_id=value.account_id.value,
        resource_id=value.resource_id.value,
        selector=value.selector,
        provider_scope_id=scope.provider_scope_id if scope else None,
        scope_evidence=scope.scope_evidence if scope else None,
        scope_generation=scope.scope_generation if scope else None,
        pool=_pool(value.pool) if value.pool else None,
        association_evidence=value.membership.association_evidence
        if value.membership
        else None,
        can_assign=scope is not None,
        registry_revision=value.registry_revision,
        reason_code=value.reason_code,
    )


def _headers(response: Response, revision: int) -> None:
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["ETag"] = f'"registry.{revision}"'


@router.get(
    "/financial-pools",
    response_model=FinancialPoolPageV1,
    operation_id="registry_list_financial_pools_v1",
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "FinancialPoolRegistryPortV1.list_pools"),
)
def list_pools(
    request: Request,
    response: Response,
    provider_key: Literal["claude", "codex", "ollama"] = Query(),
    limit: int = Query(default=50, ge=1, le=200),
    after_pool_id: str | None = Query(
        default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    ),
    expected_registry_revision: int | None = Query(default=None, ge=0),
) -> FinancialPoolPageV1:
    authorize_request(request, "read:accounts")
    reject_unknown_query(
        request,
        frozenset(
            {"provider_key", "limit", "after_pool_id", "expected_registry_revision"}
        ),
    )
    try:
        page = _port(request).list_pools(
            provider_key,
            limit=limit,
            after=OpaqueIdV1(after_pool_id) if after_pool_id else None,
            expected_registry_revision=expected_registry_revision,
        )
    except ValueError as error:
        raise _error(error) from None
    _headers(response, page.registry_revision)
    return FinancialPoolPageV1(
        items=tuple(_pool(p) for p in page.pools),
        next_pool_id=page.next_pool_id.value if page.next_pool_id else None,
        registry_revision=page.registry_revision,
    )


@router.get(
    "/accounts/{account_id}/financial-pools/{resource_id}/{selector}",
    response_model=FinancialPoolConfigurationV1,
    operation_id="registry_get_financial_pool_configuration_v1",
    responses=ERROR_RESPONSES,
    openapi_extra=policy(
        "read:accounts", "FinancialPoolRegistryPortV1.get_configuration"
    ),
)
def get_configuration(
    request: Request,
    response: Response,
    selector: Literal["billing", "self", "team"],
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    resource_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> FinancialPoolConfigurationV1:
    authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset())
    try:
        value = _port(request).get_configuration(
            OpaqueIdV1(account_id), OpaqueIdV1(resource_id), selector
        )
    except ValueError as error:
        raise _error(error) from None
    if value is None:
        raise ProblemError(404, "registry_subject_not_found")
    _headers(response, value.registry_revision)
    return _configuration(value)


@router.post(
    "/accounts/{account_id}/financial-pools/{resource_id}/{selector}",
    response_model=FinancialPoolConfigurationV1,
    operation_id="registry_assign_financial_pool_v1",
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy(
        "FinancialPoolRegistryPortV1.assign", idempotent=True
    ),
)
def assign_pool(
    body: AssignFinancialPoolInputV1,
    request: Request,
    response: Response,
    selector: Literal["billing", "self", "team"],
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    resource_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> FinancialPoolConfigurationV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    revision = _expected_version(request, "registry")
    command_id = _idempotency_key(request)
    port = _port(request)
    try:
        current = port.get_configuration(
            OpaqueIdV1(account_id), OpaqueIdV1(resource_id), selector
        )
    except ValueError as error:
        raise _error(error) from None
    if current is None:
        raise ProblemError(404, "registry_subject_not_found")
    if current.scope is None:
        raise ProblemError(409, "financial_pool_scope_changed")
    try:
        command = AssignFinancialPoolCommandV1(
            current.scope,
            revision,
            body.action,
            OpaqueIdV1(body.pool_id) if body.pool_id else None,
            OpaqueIdV1(body.primary_organization_id)
            if body.primary_organization_id
            else None,
            caller.principal.principal_id,
            command_id,
            datetime.now(UTC),
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    try:
        result = port.assign(command)
    except ValueError as error:
        raise _error(error) from None
    _headers(response, result.registry_revision)
    return _configuration(result)


@router.put(
    "/financial-pools/{pool_id}/attribution",
    response_model=FinancialPoolViewV1,
    operation_id="registry_edit_financial_pool_attribution_v1",
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy("FinancialPoolRegistryPortV1.edit", idempotent=True),
)
def edit_attribution(
    body: EditFinancialPoolInputV1,
    request: Request,
    response: Response,
    pool_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> FinancialPoolViewV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    revision = _expected_version(request, "registry")
    command_id = _idempotency_key(request)
    command = EditFinancialPoolCommandV1(
        OpaqueIdV1(pool_id),
        body.expected_record_version,
        revision,
        OpaqueIdV1(body.primary_organization_id)
        if body.primary_organization_id
        else None,
        caller.principal.principal_id,
        command_id,
        datetime.now(UTC),
    )
    try:
        result = _port(request).edit(command)
    except ValueError as error:
        raise _error(error) from None
    _headers(response, result.registry_revision)
    return _pool(result)
