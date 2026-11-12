"""Authenticated owner cloud usage action and read-only context/status queries."""

import re
from datetime import UTC, datetime
from typing import Literal

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    policy,
    reject_unknown_query,
)
from agentmonitor.api.v1.routers.billing_actions import _account_version
from agentmonitor.api.v1.schemas.cloud_usage_actions import (
    CloudUsageCollectInputV1,
    CloudUsageContextV1,
    CloudUsageEligibilityWireV1,
    CloudUsageRunStatusV1,
)
from agentmonitor.api.v1.serialization import technical_wire
from agentmonitor.contracts.cloud_usage_actions_v1 import CloudUsageCollectCommandV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunViewV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from fastapi import APIRouter, Path, Request, Response

router = APIRouter(tags=["cloud-usage"])
_ERRORS = {
    "cloud_usage_target_unavailable": 404,
    "cloud_usage_version_conflict": 412,
    "cloud_usage_target_changed": 409,
    "cloud_usage_idempotency_conflict": 409,
    "cloud_usage_interval_unavailable": 422,
    "cloud_usage_monitoring_disabled": 409,
    "cloud_usage_credential_required": 409,
    "cloud_usage_authority_unavailable": 409,
    "cloud_usage_rate_limited": 429,
    "cloud_usage_request_unresolved": 409,
    "cloud_usage_service_unavailable": 503,
    "cloud_usage_unavailable": 503,
}


def _problem(error: ValueError) -> ProblemError:
    code = str(error)
    if code not in _ERRORS:
        code = "cloud_usage_unavailable"
    return ProblemError(_ERRORS[code], code)


def _wire(
    run: BudgetCollectionRunViewV1, context: CloudBudgetReportContextV1
) -> CloudUsageRunStatusV1:
    if run.account_id is None or run.resource_id is None:
        raise ProblemError(503, "cloud_usage_unavailable")
    return CloudUsageRunStatusV1(
        run_id=run.run_id.value,
        account_id=run.account_id.value,
        resource_id=run.resource_id.value,
        report_id=None if run.report_id is None else run.report_id.value,
        report_context=CloudUsageContextV1.model_validate(technical_wire(context)),
        state=run.state,
        outcome_code=run.outcome_code,
        error_code=run.error_code,
        requested_at=run.requested_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        deadline_at=run.deadline_at,
    )


@router.post(
    "/accounts/{account_id}/cloud-usage/{resource_id}/collections",
    response_model=CloudUsageRunStatusV1,
    status_code=202,
    operation_id="cloud_usage_collect_v1",
    responses=ERROR_RESPONSES,
    openapi_extra={
        "security": [{"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []}],
        "x-agentmonitor-auth-profile": "browser_cookie_only",
        "x-agentmonitor-required-permission": "write:accounts",
        "x-agentmonitor-application-port": "CloudUsageActionsPortV1.collect",
        "x-agentmonitor-replay-policy": "replay_safe_representation",
        "x-agentmonitor-error-schema": "SafeProblemV1",
        "parameters": [
            {
                "name": "If-Match",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "maxLength": 160},
            },
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "pattern": "^[A-Za-z0-9_-]{16,128}$"},
            },
        ],
    },
)
def collect_usage(
    body: CloudUsageCollectInputV1,
    request: Request,
    response: Response,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    resource_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> CloudUsageRunStatusV1:
    caller = authorize_request(
        request, "write:accounts", cookie_only=True, require_csrf=True
    )
    if request.query_params:
        raise ProblemError(400, "invalid_filter")
    version = _account_version(request, account_id)
    key = request.headers.get("idempotency-key")
    if key is None or re.fullmatch(r"[A-Za-z0-9_-]{16,128}", key) is None:
        raise ProblemError(400, "invalid_idempotency_key")
    try:
        c = body.report_context
        context = CloudBudgetReportContextV1(
            c.scope, c.range_key, c.interval_start, c.interval_end
        )
        command = CloudUsageCollectCommandV1(
            OpaqueIdV1(account_id),
            OpaqueIdV1(resource_id),
            version,
            body.expected_target_version,
            caller.principal.principal_id,
            OpaqueIdV1(key),
            datetime.now(UTC),
            context,
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    port = observation_ports(request).cloud_usage
    if port is None:
        raise ProblemError(503, "cloud_usage_unavailable")
    try:
        run = port.collect(command)
    except ValueError as error:
        raise _problem(error) from None
    response.headers["Cache-Control"] = "no-store, private"
    return _wire(run, context)


@router.get(
    "/accounts/{account_id}/cloud-usage/{resource_id}/collection-eligibility",
    response_model=CloudUsageEligibilityWireV1,
    operation_id="cloud_usage_eligibility_v1",
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "CloudUsageActionsPortV1.eligibility"),
)
def usage_eligibility(
    request: Request,
    response: Response,
    scope: Literal["self", "team"],
    range_key: Literal["7d", "30d"],
    interval_start: datetime,
    interval_end: datetime,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    resource_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> CloudUsageEligibilityWireV1:
    authorize_request(request, "read:telemetry")
    reject_unknown_query(
        request, frozenset({"scope", "range_key", "interval_start", "interval_end"})
    )
    try:
        context = CloudBudgetReportContextV1(
            scope, range_key, interval_start, interval_end
        )
    except ValueError:
        raise ProblemError(422, "invalid_request_fields") from None
    port = observation_ports(request).cloud_usage
    if port is None:
        raise ProblemError(503, "cloud_usage_unavailable")
    try:
        result = port.eligibility(
            OpaqueIdV1(account_id), OpaqueIdV1(resource_id), context, datetime.now(UTC)
        )
    except ValueError as error:
        raise _problem(error) from None
    if result is None:
        raise ProblemError(404, "cloud_usage_target_unavailable")
    response.headers["Cache-Control"] = "no-store, private"
    return CloudUsageEligibilityWireV1.model_validate(technical_wire(result))


@router.get(
    "/accounts/{account_id}/cloud-usage/{resource_id}/runs/{run_id}",
    response_model=CloudUsageRunStatusV1,
    operation_id="cloud_usage_status_v1",
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "CloudUsageActionsPortV1.get_status"),
)
def usage_status(
    request: Request,
    response: Response,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    resource_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    run_id: str = Path(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$"),
) -> CloudUsageRunStatusV1:
    authorize_request(request, "read:telemetry")
    if request.query_params:
        raise ProblemError(400, "invalid_filter")
    port = observation_ports(request).cloud_usage
    if port is None:
        raise ProblemError(503, "cloud_usage_unavailable")
    try:
        result = port.get_status(
            OpaqueIdV1(account_id), OpaqueIdV1(resource_id), OpaqueIdV1(run_id)
        )
    except ValueError as error:
        raise _problem(error) from None
    if result is None:
        raise ProblemError(404, "cloud_usage_target_unavailable")
    response.headers["Cache-Control"] = "no-store, private"
    return _wire(*result)
