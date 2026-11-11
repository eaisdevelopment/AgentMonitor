"""Cookie administrator billing-check admission; no provider or secret I/O."""

import re
from datetime import UTC, datetime

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import ERROR_RESPONSES, policy
from agentmonitor.api.v1.schemas.billing_actions import (
    BillingCheckInputV1,
    BillingCheckRunV1,
    BudgetRunStatusV1,
)
from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
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
