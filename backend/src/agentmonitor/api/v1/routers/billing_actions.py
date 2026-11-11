"""Cookie administrator billing-check admission; no provider or secret I/O."""

import re
from datetime import UTC, datetime

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import ERROR_RESPONSES, policy
from agentmonitor.api.v1.schemas.billing_actions import (
    BillingCheckInputV1,
    BillingCheckRunV1,
    BillingMonitoringResultV1,
    BillingMonitoringStatusV1,
    BudgetRunStatusV1,
    SetBillingMonitoringInputV1,
)
from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import SetBillingMonitoringCommandV1
from fastapi import APIRouter, Path, Request, Response

router = APIRouter(tags=["billing"])

_ERRORS = {
    "billing_check_target_unavailable": 404,
    "billing_check_version_conflict": 412,
    "billing_check_authority_unavailable": 409,
    "billing_check_target_changed": 409,
    "billing_check_idempotency_conflict": 409,
    "billing_check_provider_unsupported": 409,
    "billing_check_rate_limited": 429,
    "billing_check_unavailable": 503,
    "billing_check_service_unavailable": 503,
}


def _account_version(request: Request, account_id: str) -> int:
    value = request.headers.get("if-match")
    if value is None:
        raise ProblemError(428, "precondition_required")
    match = re.fullmatch(r'"' + re.escape(account_id) + r'\.([0-9]{1,18})"', value)
    if match is None or int(match.group(1)) < 1:
        raise ProblemError(400, "invalid_precondition")
    return int(match.group(1))


@router.post(
    "/accounts/{account_id}/billing-connections/{resource_id}/checks",
    response_model=BillingCheckRunV1,
    status_code=202,
    operation_id="billing_check_connection_v1",
    responses=ERROR_RESPONSES,
    openapi_extra={
        "security": [{"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []}],
        "x-agentmonitor-auth-profile": "browser_cookie_only",
        "x-agentmonitor-required-permission": "write:accounts",
        "x-agentmonitor-application-port": "BillingCheckPortV1.check",
        "x-agentmonitor-replay-policy": "replay_safe_representation",
        "x-agentmonitor-error-schema": "SafeProblemV1",
        "parameters": [
            {
                "name": "If-Match",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "maxLength": 160},
                "description": "Current account ETag.",
            },
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "pattern": "^[A-Za-z0-9_-]{16,128}$"},
                "description": "Stable key for retrying this billing check.",
            },
        ],
    },
)
def check_billing(
    body: BillingCheckInputV1,
    request: Request,
    response: Response,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    resource_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> BillingCheckRunV1:
    caller = authorize_request(
        request, "write:accounts", cookie_only=True, require_csrf=True
    )
    if request.query_params:
        raise ProblemError(400, "invalid_filter")
    account_version = _account_version(request, account_id)
    command_id = request.headers.get("idempotency-key")
    if command_id is None or re.fullmatch(r"[A-Za-z0-9_-]{16,128}", command_id) is None:
        raise ProblemError(400, "invalid_idempotency_key")
    service = observation_ports(request).billing_checks
    if service is None:
        raise ProblemError(503, "billing_check_unavailable")
    try:
        command = BillingCheckCommandV1(
            OpaqueIdV1(account_id),
            OpaqueIdV1(resource_id),
            account_version,
            body.expected_connection_version,
            caller.principal.principal_id,
            OpaqueIdV1(command_id),
            datetime.now(UTC),
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    try:
        run = service.check(command)
    except ValueError as error:
        code = str(error)
        if code not in _ERRORS:
            raise ProblemError(503, "billing_check_unavailable") from None
        raise ProblemError(_ERRORS[code], code) from None
    response.headers["Cache-Control"] = "no-store, private"
    return BillingCheckRunV1(
        run_id=run.run_id.value,
        state=run.state,
        outcome_code=run.outcome_code,
        error_code=run.error_code,
        requested_at=run.requested_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        deadline_at=run.deadline_at,
    )


@router.get(
    "/collection-runs/{run_id}/budget",
    response_model=BudgetRunStatusV1,
    operation_id="billing_get_run_status_v1",
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "BillingCheckPortV1.get_status"),
)
def get_billing_run_status(
    request: Request,
    response: Response,
    run_id: str = Path(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$"),
) -> BudgetRunStatusV1:
    authorize_request(request, "read:telemetry")
    if request.query_params:
        raise ProblemError(400, "invalid_filter")
    service = observation_ports(request).billing_checks
    if service is None:
        raise ProblemError(503, "billing_check_unavailable")
    try:
        run = service.get_status(OpaqueIdV1(run_id))
    except ValueError:
        raise ProblemError(503, "billing_check_unavailable") from None
    if run is None:
        raise ProblemError(404, "billing_check_target_unavailable")
    if run.account_id is None or run.resource_id is None:
        raise ProblemError(503, "billing_check_unavailable")
    response.headers["Cache-Control"] = "no-store, private"
    return BudgetRunStatusV1(
        run_id=run.run_id.value,
        account_id=run.account_id.value,
        resource_id=run.resource_id.value,
        report_id=run.report_id.value if run.report_id is not None else None,
        state=run.state,
        outcome_code=run.outcome_code,
        error_code=run.error_code,
        requested_at=run.requested_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        deadline_at=run.deadline_at,
    )


_MONITORING_ERRORS = {
    "billing_monitoring_target_unavailable": 404,
    "registry_subject_not_found": 404,
    "registry_version_conflict": 412,
    "billing_monitoring_version_conflict": 412,
    "billing_monitoring_target_changed": 409,
    "billing_monitoring_verification_required": 409,
    "billing_monitoring_credential_required": 409,
    "billing_monitoring_account_unavailable": 409,
    "registry_idempotency_conflict": 409,
    "registry_replay_stale": 409,
    "billing_monitoring_unavailable": 503,
    "billing_monitoring_runtime_unavailable": 503,
}


def _monitoring_error(error: Exception) -> ProblemError:
    code = str(error)
    code = {
        "billing_monitoring_proof_required": "billing_monitoring_verification_required",
        "billing_monitoring_proof_conflict": "billing_monitoring_target_changed",
        "registry_timestamp_conflict": "billing_monitoring_target_changed",
    }.get(code, code)
    if code not in _MONITORING_ERRORS:
        return ProblemError(503, "billing_monitoring_unavailable")
    return ProblemError(_MONITORING_ERRORS[code], code)


@router.get(
    "/accounts/{account_id}/billing-connections/{resource_id}/monitoring",
    response_model=BillingMonitoringStatusV1,
    operation_id="billing_get_monitoring_v1",
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "BillingMonitoringPortV1.get_status"),
)
def get_billing_monitoring(
    request: Request,
    response: Response,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    resource_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> BillingMonitoringStatusV1:
    authorize_request(request, "read:telemetry")
    if request.query_params:
        raise ProblemError(400, "invalid_filter")
    service = observation_ports(request).billing_monitoring
    if service is None:
        raise ProblemError(503, "billing_monitoring_unavailable")
    try:
        status = service.get_status(OpaqueIdV1(account_id), OpaqueIdV1(resource_id))
    except (ValueError, RuntimeError, OSError) as error:
        raise _monitoring_error(error) from None
    if status is None:
        raise ProblemError(404, "billing_monitoring_target_unavailable")
    item = status.connection
    response.headers["Cache-Control"] = "no-store, private"
    return BillingMonitoringStatusV1(
        account_id=item.account_id.value,
        resource_id=item.resource_id.value,
        account_record_version=status.account_record_version,
        connection_record_version=item.record_version,
        scope_generation=item.scope_generation,
        binding_generation=status.binding_generation,
        monitoring_preference=item.monitoring_preference,
        lifecycle=item.lifecycle,
        can_enable=status.can_enable,
        can_disable=status.can_disable,
        reason_code=status.reason_code,
        verified_run_id=(
            status.verified_run_id.value if status.verified_run_id else None
        ),
        verified_at=status.verified_at,
    )


@router.put(
    "/accounts/{account_id}/billing-connections/{resource_id}/monitoring",
    response_model=BillingMonitoringResultV1,
    operation_id="billing_set_monitoring_v1",
    responses=ERROR_RESPONSES,
    openapi_extra={
        "security": [{"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []}],
        "x-agentmonitor-auth-profile": "browser_cookie_only",
        "x-agentmonitor-required-permission": "write:accounts",
        "x-agentmonitor-application-port": "BillingMonitoringPortV1.set_monitoring",
        "x-agentmonitor-replay-policy": "replay_safe_representation",
        "x-agentmonitor-error-schema": "SafeProblemV1",
        "parameters": [
            {
                "name": "If-Match",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "maxLength": 160},
                "description": "Current account ETag.",
            },
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "pattern": "^[A-Za-z0-9_-]{16,128}$"},
                "description": "Stable key for retrying this monitoring preference.",
            },
        ],
    },
)
def set_billing_monitoring(
    body: SetBillingMonitoringInputV1,
    request: Request,
    response: Response,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    resource_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> BillingMonitoringResultV1:
    caller = authorize_request(
        request, "write:accounts", cookie_only=True, require_csrf=True
    )
    if request.query_params:
        raise ProblemError(400, "invalid_filter")
    version = _account_version(request, account_id)
    command_id = request.headers.get("idempotency-key")
    if command_id is None or re.fullmatch(r"[A-Za-z0-9_-]{16,128}", command_id) is None:
        raise ProblemError(400, "invalid_idempotency_key")
    if body.monitoring_preference == "enabled" and (
        body.verified_run_id is None or body.expected_binding_generation is None
    ):
        raise ProblemError(409, "billing_monitoring_verification_required")
    try:
        command = SetBillingMonitoringCommandV1(
            account_id=OpaqueIdV1(account_id),
            resource_id=OpaqueIdV1(resource_id),
            expected_account_version=version,
            expected_connection_version=body.expected_connection_version,
            expected_scope_generation=body.expected_scope_generation,
            expected_binding_generation=body.expected_binding_generation,
            monitoring_preference=body.monitoring_preference,
            verified_run_id=OpaqueIdV1(body.verified_run_id)
            if body.verified_run_id
            else None,
            principal_id=caller.principal.principal_id,
            command_id=OpaqueIdV1(command_id),
            requested_at=datetime.now(UTC),
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    service = observation_ports(request).billing_monitoring
    if service is None:
        raise ProblemError(503, "billing_monitoring_unavailable")
    try:
        item = service.set_monitoring(command)
    except (ValueError, RuntimeError, OSError) as error:
        raise _monitoring_error(error) from None
    response.headers["Cache-Control"] = "no-store, private"
    return BillingMonitoringResultV1(
        account_id=item.account_id.value,
        resource_id=item.resource_id.value,
        connection_record_version=item.record_version,
        scope_generation=item.scope_generation,
        monitoring_preference=item.monitoring_preference,
        lifecycle=item.lifecycle,
        registry_revision=item.registry_revision,
        updated_at=item.updated_at,
    )
