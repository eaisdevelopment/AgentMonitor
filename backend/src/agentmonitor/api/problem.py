"""CTR-COMMON-005: bounded RFC 9457 problem representation for P01."""

from dataclasses import dataclass
from typing import Any, Literal

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema
from starlette.exceptions import HTTPException as StarletteHTTPException


class SafeFieldErrorV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(max_length=128)
    code: str = Field(max_length=64)


class SafeCommittedApiTokenV1(BaseModel):
    """Only committed token replay metadata, never a credential or scope grant."""

    model_config = ConfigDict(extra="forbid")

    api_token_id: str = Field(min_length=1, max_length=128)
    record_version: int = Field(ge=1)
    state: Literal["active", "expired", "revoked", "rotated"]


def _omit_schema_default(schema: dict[str, Any]) -> None:
    """Absent optional metadata must not advertise a null wire default."""
    schema.pop("default", None)


class SafeProblemV1(BaseModel):
    """Public failure: neither exception text nor rejected input is serialized."""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    detail: str = Field(default_factory=str)
    code: str
    correlation_id: str
    errors: tuple[SafeFieldErrorV1, ...] = ()
    committed_resource: SafeCommittedApiTokenV1 | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=_omit_schema_default
    )


_TITLES = {
    400: "Invalid request",
    401: "Dashboard authentication required",
    403: "Request forbidden",
    404: "Resource not found",
    405: "Method not allowed",
    409: "Request conflict",
    412: "Precondition failed",
    413: "Request too large",
    415: "Unsupported media type",
    422: "Invalid request fields",
    428: "Precondition required",
    429: "Too many requests",
    500: "Internal service error",
    503: "Service unavailable",
    504: "Request timed out",
}

# Closed local documentation catalog. Neither the route nor the problem type
# accepts a code copied from submitted input or an unrecognized port outcome.
PROBLEM_DESCRIPTIONS: dict[str, str] = {
    "budget_report_not_found": (
        "The selected financial report is unavailable. "
        "Refresh the view to select retained data."
    ),
    "billing_monitoring_target_unavailable": "The billing connection is unavailable.",
    "billing_monitoring_version_conflict": (
        "The billing connection changed. Refresh its status."
    ),
    "billing_monitoring_target_changed": "Billing access changed. Refresh its status.",
    "billing_monitoring_verification_required": (
        "Complete a successful billing check before enabling monitoring."
    ),
    "billing_monitoring_credential_required": (
        "A stored credential is required for billing monitoring."
    ),
    "billing_monitoring_account_unavailable": (
        "This account cannot enable billing monitoring."
    ),
    "billing_monitoring_unavailable": "Billing monitoring is temporarily unavailable.",
    "billing_monitoring_runtime_unavailable": "The billing collector is unavailable.",
    "billing_check_target_unavailable": "The billing connection is unavailable.",
    "billing_check_version_conflict": "The account changed. Refresh before retrying.",
    "billing_check_authority_unavailable": (
        "Store a billing credential before checking access."
    ),
    "billing_check_target_changed": (
        "The billing connection changed. Refresh its status."
    ),
    "billing_check_idempotency_conflict": (
        "This request key belongs to a different billing check."
    ),
    "billing_check_provider_unsupported": (
        "Billing checks for this provider are not yet available."
    ),
    "billing_check_rate_limited": (
        "The billing read budget is currently exhausted. Try later."
    ),
    "billing_check_unavailable": (
        "The billing check could not be admitted. Refresh its status."
    ),
    "billing_check_service_unavailable": (
        "The billing worker is unavailable. Check service status."
    ),
    "capacity_v2_required": "This capacity reading requires the V2 endpoint.",
    "credential_update_in_progress": "Another account update is in progress.",
    "ollama_cloud_connection_unavailable": "Ollama cloud connection is unavailable.",
    "request_body_not_allowed": "This request does not accept a body.",
    "alert_not_found": "The alert is unavailable.",
    "alert_notification_conflict": "The notification changed before this command.",
    "alert_command_subject_conflict": "The alert command targets a different subject.",
    "alert_not_open": "This alert is no longer open.",
    "alert_transition_time_invalid": "The alert changed after this command time.",
    "alert_rule_not_found": "The alert rule is unavailable.",
    "alert_version_conflict": "The alert rule changed before this command.",
    "alert_idempotency_conflict": (
        "The operation key was used for another alert command."
    ),
    "alert_rule_scope_conflict": (
        "An active rule already covers this scope and condition."
    ),
    "alert_rule_archived": "The alert rule is archived.",
    "alert_rule_time_conflict": "The rule clock is behind its last update.",
    "alert_repository_unavailable": "Alert storage is unavailable.",
    "active_token_limit_reached": "The active API-token limit has been reached.",
    "ambiguous_credentials": "Use a session cookie or a bearer token, not both.",
    "api_token_not_found": "The requested API token is unavailable.",
    "audit_cursor_invalid": "The security-event cursor is invalid.",
    "audit_filter_invalid": "The security-event filter is invalid.",
    "audit_limit_invalid": "The security-event page limit is invalid.",
    "credential_state_conflict": "The credential is no longer in the required state.",
    "csrf_validation_failed": "The browser CSRF proof was rejected.",
    "cursor_query_mismatch": "The page cursor belongs to another query or caller.",
    "dashboard_authentication_required": "Sign in to the dashboard and retry.",
    "host_not_allowed": "The request authority is not the bound local service.",
    "http_request_rejected": "The HTTP request was rejected.",
    "iam_repository_unavailable": "The local identity store is unavailable.",
    "iam_setup_required": "The local administrator has not been initialized.",
    "idempotency_key_reused": "This operation key was used for another request.",
    "internal_error": "The service could not complete the request.",
    "invalid_authorization_header": "The authorization header is invalid.",
    "invalid_content_length": "The request length header is invalid.",
    "invalid_correlation_id": "The correlation header is invalid.",
    "invalid_cursor": "The page cursor is invalid or expired.",
    "invalid_dashboard_credentials": "The dashboard credential was rejected.",
    "invalid_filter": "The request filter is invalid.",
    "invalid_idempotency_key": "The operation key is invalid.",
    "invalid_request_fields": "One or more request fields are invalid.",
    "invalid_precondition": "The supplied resource version is invalid.",
    "invalid_sort": "The requested ordering is unavailable.",
    "login_throttled": "Too many login attempts were made; retry later.",
    "method_not_allowed": "This HTTP method is not available here.",
    "observation_data_unavailable": "The observation query service is unavailable.",
    "observation_repository_unavailable": "The local observation store is unavailable.",
    "one_time_secret_not_replayable": (
        "A one-time issued secret cannot be retrieved again."
    ),
    "origin_not_allowed": "The browser origin is not the local service.",
    "password_policy_violation": "The proposed password did not meet policy.",
    "permission_denied": "The caller lacks the required permission.",
    "precondition_failed": "The resource version no longer matches.",
    "precondition_required": "A current resource version is required.",
    "provider_capabilities_not_found": (
        "The provider capability declaration is unavailable."
    ),
    "provider_connection_unavailable": "The account connection service is unavailable.",
    "provider_connection_not_eligible": (
        "Only an unconnected managed account can start sign-in."
    ),
    "provider_connection_email_required": "Enter the intended provider account email.",
    "provider_connection_busy": "Finish or cancel the current account sign-in first.",
    "provider_connection_not_found": "The selected sign-in attempt is unavailable.",
    "provider_identity_legacy_unavailable": (
        "Use the provider-neutral identity resource for this provider."
    ),
    "request_capacity_exceeded": "The local request-capacity limit was reached.",
    "request_timeout": "The request exceeded its execution deadline.",
    "request_too_large": "The request exceeded a transport size limit.",
    "registry_alias_conflict": "An active account already uses that provider name.",
    "registry_conflict": "The registry operation conflicts with current state.",
    "registry_idempotency_conflict": "The operation key belongs to another request.",
    "registry_name_conflict": "An active organization already uses that name.",
    "registry_monitoring_not_eligible": "Confirm identity and profile first.",
    "registry_organization_unavailable": "The destination organization is unavailable.",
    "registry_organization_not_empty": "Move or archive its accounts first.",
    "registry_order_set_invalid": "The order must contain each active group once.",
    "registry_provider_unavailable": "The requested provider is not admitted.",
    "registry_replay_stale": "The replayed registry result has since changed.",
    "registry_revision_conflict": "The registry changed since the order was read.",
    "registry_repository_unavailable": "The local registry store is unavailable.",
    "registry_subject_archived": "The registry record is archived.",
    "registry_subject_not_archived": "The registry record is not archived.",
    "registry_subject_not_found": "The registry record is unavailable.",
    "registry_account_version_conflict": (
        "The selected account changed. Refresh before saving."
    ),
    "registry_coverage_reference_invalid": (
        "The selected account or organization cannot provide this coverage."
    ),
    "registry_version_conflict": "The registry record version no longer matches.",
    "resource_not_found": "The requested local resource is unavailable.",
    "scope_escalation_denied": "The requested token scopes exceed caller authority.",
    "session_cursor_invalid": "The session cursor is invalid.",
    "session_not_found": "The requested session is unavailable.",
    "token_cursor_invalid": "The API-token cursor is invalid.",
    "token_list_limit_invalid": "The API-token page limit is invalid.",
    "token_policy_violation": "The proposed API token did not meet policy.",
    "unsupported_authentication_method": "This authentication method is unavailable.",
    "unsupported_media_type": "Use the required request media type.",
}


@dataclass(frozen=True, slots=True)
class ProblemError(Exception):
    status: int
    code: str
    retry_after_seconds: int | None = None
    committed_resource: SafeCommittedApiTokenV1 | None = None


def problem_response(
    status: int,
    code: str,
    correlation_id: str,
    *,
    errors: tuple[SafeFieldErrorV1, ...] = (),
    retry_after_seconds: int | None = None,
    committed_resource: SafeCommittedApiTokenV1 | None = None,
) -> JSONResponse:
    if code not in PROBLEM_DESCRIPTIONS:
        status, code = 500, "internal_error"
    if committed_resource is not None and code != "one_time_secret_not_replayable":
        status, code, committed_resource = 500, "internal_error", None
    title = _TITLES.get(status, "Request failed")
    body = SafeProblemV1(
        type=f"/problems/{code}",
        title=title,
        status=status,
        detail=title + ".",
        code=code,
        correlation_id=correlation_id,
        errors=errors,
        committed_resource=committed_resource,
    )
    headers = {"Cache-Control": "no-store, private"}
    if retry_after_seconds is not None:
        headers["Retry-After"] = str(retry_after_seconds)
    omitted = set()
    if not errors:
        omitted.add("errors")
    if committed_resource is None:
        omitted.add("committed_resource")
    return JSONResponse(
        body.model_dump(exclude=omitted),
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
    )


async def handle_problem(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, ProblemError):
        return await handle_unexpected(request, error)
    response = problem_response(
        error.status,
        error.code,
        request.state.correlation_id,
        retry_after_seconds=error.retry_after_seconds,
        committed_resource=error.committed_resource,
    )
    if (
        error.code == "dashboard_authentication_required"
        and request.url.path == "/api/v1/session"
        and request.method == "DELETE"
    ):
        if "agentmonitor_session" in request.cookies:
            response.delete_cookie(
                "agentmonitor_session",
                path="/",
                secure=False,
                httponly=True,
                samesite="strict",
            )
        if "agentmonitor_csrf" in request.cookies:
            response.delete_cookie(
                "agentmonitor_csrf",
                path="/",
                secure=False,
                httponly=False,
                samesite="strict",
            )
    return response


async def handle_validation(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, RequestValidationError):
        return await handle_unexpected(request, error)
    # Pydantic's error objects may include submitted secrets in `input`/`ctx`.
    # Only bounded locations and a constant code cross this boundary.
    paths: list[SafeFieldErrorV1] = []
    approved_fields = {
        "password",
        "current_password",
        "new_password",
        "name",
        "scopes",
        "lifetime_seconds",
        "limit",
        "cursor",
        "event_type",
        "outcome",
        "occurred_from",
        "occurred_before",
    }
    for issue in error.errors()[:8]:
        location = issue.get("loc", ())
        safe_parts = [
            part
            for part in location
            if isinstance(part, str) and part in approved_fields
        ]
        safe = "/" + "/".join(safe_parts or ["request"])
        paths.append(SafeFieldErrorV1(path=safe[:128], code="invalid_field"))
    return problem_response(
        422,
        "invalid_request_fields",
        request.state.correlation_id,
        errors=tuple(paths),
    )


async def handle_http(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, StarletteHTTPException):
        return await handle_unexpected(request, error)
    status = error.status_code
    return problem_response(
        status,
        {404: "resource_not_found", 405: "method_not_allowed"}.get(
            status, "http_request_rejected"
        ),
        request.state.correlation_id,
    )


async def handle_unexpected(request: Request, error: Exception) -> JSONResponse:
    # Never retain or emit the exception object: it could carry a credential.
    status, code = map_unexpected_error(error)
    return problem_response(status, code, request.state.correlation_id)


def map_unexpected_error(_error: Exception) -> tuple[int, str]:
    """Closed pure mapping: exception text and attributes never cross P01."""
    return 500, "internal_error"


async def handle_repository_unavailable(
    request: Request, error: Exception
) -> JSONResponse:
    return problem_response(
        503, "iam_repository_unavailable", request.state.correlation_id
    )
