"""Authenticated coverage CRUD using CTR-REG-013 only."""

import re
from datetime import UTC, datetime

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    policy,
    reject_unknown_query,
)
from agentmonitor.api.v1.routers.registry import _idempotency_key, _version_policy
from agentmonitor.api.v1.schemas.coverage import (
    OrganizationCoverageResourceV1,
    OrganizationCoverageSnapshotWireV1,
    OrganizationCoverageWireV1,
    SetOrganizationCoverageInputV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_coverage_v1 import (
    OrganizationProviderCoverageSelectionV1,
    OrganizationProviderCoverageV1,
    RevokeOrganizationProviderCoverageCommandV1,
    SetOrganizationProviderCoverageCommandV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from fastapi import APIRouter, Query, Request, Response

router = APIRouter(tags=["registry"])
_PATH = "/organizations/{organization_id}/provider-coverage/{provider_key}"


def _selection(
    organization_id: str, provider_key: str
) -> OrganizationProviderCoverageSelectionV1:
    try:
        if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", organization_id) is None:
            raise ValueError("invalid_identifier")
        return OrganizationProviderCoverageSelectionV1(
            (OpaqueIdV1(organization_id),), provider_key
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None


def _wire(item: OrganizationProviderCoverageV1) -> OrganizationCoverageWireV1:
    return OrganizationCoverageWireV1(
        coverage_id=item.coverage_id.value,
        organization_id=item.organization_id.value,
        provider_key=item.provider_key,
        outcome=item.outcome,
        account_id=item.account_id.value if item.account_id else None,
        account_organization_id=item.account_organization_id.value
        if item.account_organization_id
        else None,
        unavailable_reason=item.unavailable_reason,
        provenance=item.provenance,
        confirmed_at=item.confirmed_at,
        record_version=item.record_version,
        registry_revision=item.registry_revision,
        invalidated_at=item.invalidated_at,
        invalidation_reason=item.invalidation_reason,
    )


def _etag(
    response: Response, organization_id: str, provider_key: str, version: int
) -> None:
    response.headers["ETag"] = f'"{organization_id}.{provider_key}.{version}"'


def _expected(
    request: Request, organization_id: str, provider_key: str, *, creating: bool
) -> int:
    value = request.headers.get("if-match")
    if value is None:
        raise ProblemError(428, "precondition_required")
    prefix = re.escape(f"{organization_id}.{provider_key}.")
    match = re.fullmatch(r'"' + prefix + r'([0-9]{1,19})"', value)
    if match is None or int(match.group(1)) < (0 if creating else 1):
        raise ProblemError(400, "invalid_precondition")
    return int(match.group(1))


def _conflict(error: RegistryCommandConflictV1) -> ProblemError:
    code = str(error)
    if code == "registry_subject_not_found":
        return ProblemError(404, code)
    if code in {"registry_version_conflict", "registry_account_version_conflict"}:
        return ProblemError(412, code)
    if code not in {
        "registry_coverage_reference_invalid",
        "registry_idempotency_conflict",
        "registry_replay_stale",
    }:
        code = "registry_conflict"
    return ProblemError(409, code)


@router.get(
    "/provider-coverage/{provider_key}",
    operation_id="registry_list_organization_coverage_v1",
    response_model=OrganizationCoverageSnapshotWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "OrganizationProviderCoverageReadPortV1"),
)
def list_coverage(
    provider_key: str,
    request: Request,
    organization_ids: str = Query(
        min_length=1,
        max_length=12999,
        description=(
            "One to 200 distinct organization IDs, comma-separated in selection order."
        ),
    ),
) -> OrganizationCoverageSnapshotWireV1:
    authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset({"organization_ids"}))
    try:
        selected = tuple(
            _selection(item, provider_key).organization_ids[0]
            for item in organization_ids.split(",")
        )
        selection = OrganizationProviderCoverageSelectionV1(selected, provider_key)
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    reader = observation_ports(request).organization_coverage_read
    if reader is None:
        raise ProblemError(503, "registry_repository_unavailable")
    try:
        result = reader.read_coverage(selection)
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    if result.selection != selection:
        raise ProblemError(503, "registry_repository_unavailable")
    return OrganizationCoverageSnapshotWireV1(
        organization_ids=tuple(
            item.value for item in result.selection.organization_ids
        ),
        provider_key=provider_key,
        items=tuple(_wire(item) for item in result.items),
        completeness=result.completeness,
        registry_revision=result.registry_revision,
        as_of=result.as_of,
    )


@router.get(
    _PATH,
    operation_id="registry_get_organization_coverage_v1",
    response_model=OrganizationCoverageResourceV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "OrganizationProviderCoverageReadPortV1"),
)
def get_coverage(
    organization_id: str, provider_key: str, request: Request, response: Response
) -> OrganizationCoverageResourceV1:
    authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset())
    selection = _selection(organization_id, provider_key)
    ports = observation_ports(request)
    if ports.organization_coverage_read is None:
        raise ProblemError(503, "registry_repository_unavailable")
    try:
        organization = ports.get_organization(selection.organization_ids[0])
        if organization is None:
            raise ProblemError(404, "registry_subject_not_found")
        result = ports.organization_coverage_read.read_coverage(selection)
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    if result.completeness != "complete" or result.selection != selection:
        raise ProblemError(503, "registry_repository_unavailable")
    item = result.items[0] if result.items else None
    _etag(response, organization_id, provider_key, item.record_version if item else 0)
    return OrganizationCoverageResourceV1(
        organization_id=organization_id,
        provider_key=provider_key,
        coverage=_wire(item) if item else None,
        registry_revision=result.registry_revision,
        as_of=result.as_of,
    )


@router.put(
    _PATH,
    operation_id="registry_set_organization_coverage_v1",
    response_model=OrganizationCoverageWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy(
        "OrganizationProviderCoverageWritePortV1", idempotent=True
    ),
)
def set_coverage(
    organization_id: str,
    provider_key: str,
    input: SetOrganizationCoverageInputV1,
    request: Request,
    response: Response,
) -> OrganizationCoverageWireV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    selection = _selection(organization_id, provider_key)
    version = _expected(request, organization_id, provider_key, creating=True)
    command_id = _idempotency_key(request)
    try:
        command = SetOrganizationProviderCoverageCommandV1(
            organization_id=selection.organization_ids[0],
            provider_key=provider_key,
            outcome=input.outcome,
            account_id=OpaqueIdV1(input.account_id) if input.account_id else None,
            expected_account_record_version=input.expected_account_record_version,
            unavailable_reason=input.unavailable_reason,
            expected_version=version,
            command_id=command_id,
            principal_id=caller.principal.principal_id,
            requested_at=datetime.now(UTC),
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    writer = observation_ports(request).organization_coverage_write
    if writer is None:
        raise ProblemError(503, "registry_repository_unavailable")
    try:
        item = writer.set_coverage(command)
    except RegistryCommandConflictV1 as error:
        raise _conflict(error) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    _etag(response, organization_id, provider_key, item.record_version)
    return _wire(item)


@router.delete(
    _PATH,
    operation_id="registry_revoke_organization_coverage_v1",
    response_model=OrganizationCoverageWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_version_policy(
        "OrganizationProviderCoverageWritePortV1", idempotent=True
    ),
)
def revoke_coverage(
    organization_id: str, provider_key: str, request: Request, response: Response
) -> OrganizationCoverageWireV1:
    caller = authorize_request(request, "write:accounts", require_csrf=True)
    reject_unknown_query(request, frozenset())
    selection = _selection(organization_id, provider_key)
    version = _expected(request, organization_id, provider_key, creating=False)
    command_id = _idempotency_key(request)
    command = RevokeOrganizationProviderCoverageCommandV1(
        organization_id=selection.organization_ids[0],
        provider_key=provider_key,
        expected_version=version,
        command_id=command_id,
        principal_id=caller.principal.principal_id,
        requested_at=datetime.now(UTC),
    )
    writer = observation_ports(request).organization_coverage_write
    if writer is None:
        raise ProblemError(503, "registry_repository_unavailable")
    try:
        item = writer.revoke_coverage(command)
    except RegistryCommandConflictV1 as error:
        raise _conflict(error) from None
    except ValueError:
        raise ProblemError(503, "registry_repository_unavailable") from None
    _etag(response, organization_id, provider_key, item.record_version)
    return _wire(item)
