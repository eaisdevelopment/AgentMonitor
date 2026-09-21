"""Thin versioned IAM HTTP mapping; M01 alone owns credential policy/state."""

import re
from datetime import UTC, datetime
from typing import Any

from agentmonitor.api.problem import ProblemError, SafeCommittedApiTokenV1
from agentmonitor.api.v1.dependencies import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    authorize_request,
    ports,
)
from agentmonitor.api.v1.pagination import cursor_codec, parse_list_query
from agentmonitor.api.v1.schemas.iam import (
    ApiTokenCredentialIssueV1,
    ApiTokenPageV1,
    BrowserSessionPageV1,
    ChangeAdministratorPasswordInputV1,
    CreateApiTokenInputV1,
    IamInitializationStateV1,
    IamSecurityEventPageV1,
    LoginInputV1,
    PageMetaV1,
    RotateApiTokenInputV1,
    SessionRevocationSummaryV1,
)
from agentmonitor.api.v1.schemas.iam import (
    ApiTokenSummaryV1 as WireApiTokenSummaryV1,
)
from agentmonitor.api.v1.schemas.iam import (
    CurrentSessionViewV1 as WireCurrentSessionViewV1,
)
from agentmonitor.api.v1.schemas.iam import (
    IamSecurityEventV1 as WireIamSecurityEventV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    ApiTokenMutationOutcomeV1,
    ApiTokenSummaryV1,
    AuthenticationFailureV1,
    IamSecurityEventViewV1,
    SecretInputV1,
    SessionCredentialIssueV1,
    SessionMutationOutcomeV1,
    SessionSummaryV1,
)
from agentmonitor.modules.identity_access.application.api_tokens import (
    TokenQueryErrorV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    SessionQueryErrorV1,
)
from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["iam"])
_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {
        "description": "SafeProblemV1",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/SafeProblemV1"}
            }
        },
    }
    for status in (
        400,
        401,
        403,
        404,
        405,
        409,
        412,
        413,
        415,
        422,
        428,
        429,
        500,
        503,
        504,
    )
}


def _operation(
    profile: str, permission: str, application_port: str, replay: str
) -> dict[str, object]:
    if profile == "preauth_loopback":
        security: list[dict[str, list[str]]] = []
    elif profile == "browser_cookie_only":
        security = [{"BrowserSessionCookieV1": []}]
    else:
        security = [{"BrowserSessionCookieV1": []}, {"BearerTokenV1": []}]
    return {
        "security": security,
        "x-agentmonitor-auth-profile": profile,
        "x-agentmonitor-required-permission": permission,
        "x-agentmonitor-application-port": application_port,
        "x-agentmonitor-replay-policy": replay,
        "x-agentmonitor-error-schema": "SafeProblemV1",
    }


def _list_operation(
    profile: str,
    permission: str,
    application_port: str,
    sort: str,
    *,
    events: bool = False,
) -> dict[str, object]:
    metadata = _operation(profile, permission, application_port, "safe_query_repeat")
    parameters: list[dict[str, object]] = [
        {
            "name": "limit",
            "in": "query",
            "required": False,
            "schema": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
        },
        {
            "name": "cursor",
            "in": "query",
            "required": False,
            "description": (
                "Versioned, query- and caller-bound cursor; expires in 15 minutes."
            ),
            "schema": {
                "type": "string",
                "maxLength": 1024,
                "pattern": r"^v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
            },
        },
        {
            "name": "sort",
            "in": "query",
            "required": False,
            "description": (
                "Fixed descending order with the resource ID as tie-breaker."
            ),
            "schema": {"type": "string", "enum": [sort], "default": sort},
        },
    ]
    if events:
        for name in ("event_type", "outcome"):
            parameters.append(
                {
                    "name": name,
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "pattern": "^[a-z_]{1,64}$"},
                }
            )
        for name in ("occurred_from", "occurred_before"):
            parameters.append(
                {
                    "name": name,
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "format": "date-time"},
                }
            )
    metadata["parameters"] = parameters
    return metadata


def _unsafe_operation(
    profile: str,
    permission: str,
    application_port: str,
    replay: str,
    *,
    precondition: bool = False,
    idempotency: bool = False,
) -> dict[str, object]:
    metadata = _operation(profile, permission, application_port, replay)
    if profile == "browser_cookie_only":
        metadata["security"] = [
            {"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []}
        ]
    elif profile == "cookie_or_bearer":
        metadata["security"] = [
            {"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []},
            {"BearerTokenV1": []},
        ]
    parameters: list[dict[str, object]] = []
    if precondition:
        parameters.append(
            {
                "name": "If-Match",
                "in": "header",
                "required": True,
                "description": "Current strong resource ETag.",
                "schema": {
                    "type": "string",
                    "pattern": r'"[A-Za-z0-9_-]{1,64}\.[1-9][0-9]*"',
                },
            }
        )
    if idempotency:
        parameters.append(
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "description": "One-time operation key; no credential data.",
                "schema": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9_-]{16,128}$",
                },
            }
        )
    if parameters:
        metadata["parameters"] = parameters
    return metadata


def _id(value: str) -> OpaqueIdV1:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}\Z", value) is None:
        raise ProblemError(404, "resource_not_found")
    return OpaqueIdV1(value)


def encode_strong_etag(subject_id: OpaqueIdV1, version: int) -> str:
    """The M2 opaque-subject/positive-version strong validator."""
    if type(version) is not int or not 1 <= version <= 2**63 - 1:
        raise ValueError("etag_version_invalid")
    return f'"{subject_id.value}.{version}"'


def decode_strong_etag(value: str) -> tuple[OpaqueIdV1, int] | None:
    """Reject weak, list, malformed, and oversized entity tags before M01."""
    match = re.fullmatch(r'"([A-Za-z0-9_-]{1,64})\.([1-9][0-9]{0,18})"\Z', value)
    if match is None:
        return None
    version = int(match.group(2))
    if version > 2**63 - 1:
        return None
    return OpaqueIdV1(match.group(1)), version


def _parsed_precondition(request: Request) -> tuple[OpaqueIdV1, int]:
    value = request.headers.get("if-match")
    if value is None:
        raise ProblemError(428, "precondition_required")
    parsed = decode_strong_etag(value)
    if parsed is None:
        raise ProblemError(412, "precondition_failed")
    return parsed


def _precondition(request: Request, subject_id: OpaqueIdV1) -> int:
    presented, version = _parsed_precondition(request)
    if presented != subject_id:
        raise ProblemError(412, "precondition_failed")
    return version


def _password_precondition(request: Request, session_id: OpaqueIdV1) -> int:
    presented, version = _parsed_precondition(request)
    # The M01 receipt must win over a stale subject on a one-time-secret retry.
    # A fresh request receives its normal published precondition failure: no
    # persisted session version can be negative.
    return version if presented == session_id else -1


def _idempotency_key(request: Request) -> str:
    key = request.headers.get("idempotency-key")
    if key is None or re.fullmatch(r"[A-Za-z0-9_-]{16,128}\Z", key) is None:
        raise ProblemError(400, "invalid_idempotency_key")
    return key


def _json(request: Request) -> None:
    if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
        raise ProblemError(415, "unsupported_media_type")


def _bounded_password_input(value: str) -> None:
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise ProblemError(422, "invalid_request_fields") from None
    if size > 1024:
        raise ProblemError(422, "invalid_request_fields")


def _session(item: SessionSummaryV1) -> WireCurrentSessionViewV1:
    return WireCurrentSessionViewV1(
        session_id=item.session_id.value,
        issued_at=item.issued_at,
        last_activity_at=item.last_activity_at,
        idle_expires_at=item.idle_expires_at,
        absolute_expires_at=item.absolute_expires_at,
        state=item.state,
        is_current=item.is_current,
        record_version=item.record_version,
    )


def _token(item: ApiTokenSummaryV1) -> WireApiTokenSummaryV1:
    return WireApiTokenSummaryV1(
        api_token_id=item.api_token_id.value,
        name=item.name,
        safe_prefix=item.safe_prefix,
        scopes=item.scopes,
        issued_at=item.issued_at,
        expires_at=item.expires_at,
        last_used_at=item.last_used_at,
        revoked_at=item.revoked_at,
        revocation_reason=item.revocation_reason,
        rotated_from_token_id=(
            item.rotated_from_token_id.value if item.rotated_from_token_id else None
        ),
        replacement_token_id=(
            item.replacement_token_id.value if item.replacement_token_id else None
        ),
        state=item.state,
        record_version=item.record_version,
    )


def _event(item: IamSecurityEventViewV1) -> WireIamSecurityEventV1:
    return WireIamSecurityEventV1(
        event_id=item.event_id.value,
        event_type=item.event_type,
        occurred_at=item.occurred_at,
        recorded_at=item.recorded_at,
        actor_principal_id=(
            item.actor_principal_id.value if item.actor_principal_id else None
        ),
        authentication_method=item.authentication_method,
        target_type=item.target_type,
        target_id=item.target_id.value if item.target_id else None,
        outcome_code=item.outcome_code,
        reason_code=item.reason_code,
        correlation_id=item.correlation_id.value,
        schema_version=item.schema_version,
        aggregate_count=item.aggregate_count,
    )


def _page(
    limit: int, items: tuple[object, ...], more: bool, cursor: str | None
) -> PageMetaV1:
    return PageMetaV1(limit=limit, has_more=more, next_cursor=cursor if more else None)


def _token_error(outcome: ApiTokenMutationOutcomeV1) -> ProblemError:
    code = outcome.code
    committed_resource = None
    if code == "one_time_secret_not_replayable":
        if (
            outcome.api_token_id is None
            or outcome.record_version is None
            or outcome.state is None
        ):
            return ProblemError(500, "internal_error")
        committed_resource = SafeCommittedApiTokenV1(
            api_token_id=outcome.api_token_id.value,
            record_version=outcome.record_version,
            state=outcome.state,
        )
    return ProblemError(
        {
            "dashboard_authentication_required": 401,
            "csrf_validation_failed": 403,
            "permission_denied": 403,
            "scope_escalation_denied": 403,
            "token_policy_violation": 422,
            "api_token_not_found": 404,
            "precondition_failed": 412,
            "credential_state_conflict": 409,
            "one_time_secret_not_replayable": 409,
            "idempotency_key_reused": 409,
            "active_token_limit_reached": 409,
        }.get(code, 500),
        code,
        committed_resource=committed_resource,
    )


def _session_error(outcome: SessionMutationOutcomeV1) -> ProblemError:
    code = outcome.code
    return ProblemError(
        {
            "dashboard_authentication_required": 401,
            "invalid_credentials": 401,
            "csrf_validation_failed": 403,
            "precondition_failed": 412,
            "credential_state_conflict": 409,
            "session_not_found": 404,
            "one_time_secret_not_replayable": 409,
            "idempotency_key_reused": 409,
            "login_throttled": 429,
            "password_policy_violation": 422,
        }.get(code, 500),
        "invalid_dashboard_credentials" if code == "invalid_credentials" else code,
        outcome.retry_after_seconds,
    )


@router.get(
    "/iam/initialization",
    operation_id="iam_get_initialization_v1",
    response_model=IamInitializationStateV1,
    responses=_ERROR_RESPONSES,
    openapi_extra={
        "security": [],
        "x-agentmonitor-auth-profile": "preauth_loopback",
        "x-agentmonitor-required-permission": "none",
        "x-agentmonitor-application-port": "GetIamInitializationStateV1",
        "x-agentmonitor-replay-policy": "safe_query_repeat",
        "x-agentmonitor-error-schema": "SafeProblemV1",
    },
)
def get_initialization(request: Request) -> IamInitializationStateV1:
    state = ports(request).initialization()
    return IamInitializationStateV1(
        state=state.state,
        policy_version=state.policy_version,
        schema_revision=state.schema_revision,
    )


@router.post(
    "/session",
    operation_id="iam_login_v1",
    status_code=204,
    response_class=Response,
    responses=_ERROR_RESPONSES,
    openapi_extra={
        "security": [],
        "x-agentmonitor-auth-profile": "preauth_loopback",
        "x-agentmonitor-required-permission": "none",
        "x-agentmonitor-application-port": "AuthenticateAdministratorV1",
        "x-agentmonitor-replay-policy": "fresh_credential_issue",
        "x-agentmonitor-error-schema": "SafeProblemV1",
    },
)
def login(input: LoginInputV1, request: Request, response: Response) -> Response:
    _json(request)
    if request.headers.get("authorization") is not None:
        raise ProblemError(400, "unsupported_authentication_method")
    _bounded_password_input(input.password)
    result = ports(request).login(
        SecretInputV1(input.password), correlation_id=request.state.correlation_id
    )
    if isinstance(result, AuthenticationFailureV1):
        mapping = {
            "invalid_credentials": (401, "invalid_dashboard_credentials"),
            "login_throttled": (429, "login_throttled"),
            "iam_setup_required": (503, "iam_setup_required"),
            "iam_repository_unavailable": (503, "iam_repository_unavailable"),
        }
        status, code = mapping[result.code]
        raise ProblemError(status, code, result.retry_after_seconds)
    if not isinstance(result, SessionCredentialIssueV1):
        raise ProblemError(500, "internal_error")
    response.status_code = 204
    max_age = max(
        0, int((result.session.absolute_expires_at - datetime.now(UTC)).total_seconds())
    )
    response.set_cookie(
        SESSION_COOKIE,
        result.session_credential,
        httponly=True,
        secure=False,
        samesite="strict",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        CSRF_COOKIE,
        result.csrf_credential,
        httponly=False,
        secure=False,
        samesite="strict",
        path="/",
        max_age=max_age,
    )
    return response


@router.get(
    "/session",
    operation_id="iam_get_current_session_v1",
    response_model=WireCurrentSessionViewV1,
    responses=_ERROR_RESPONSES,
    openapi_extra=_operation(
        "browser_cookie_only",
        "read:self",
        "ResolveBrowserSessionV1",
        "safe_query_repeat",
    ),
)
def get_current_session(
    request: Request, response: Response
) -> WireCurrentSessionViewV1:
    caller = authorize_request(request, "read:self", cookie_only=True)
    session = caller.session
    if session is None:
        raise ProblemError(401, "dashboard_authentication_required")
    response.headers["ETag"] = encode_strong_etag(
        session.session_id, session.record_version
    )
    return _session(session)


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=False, httponly=True, samesite="strict"
    )
    response.delete_cookie(
        CSRF_COOKIE, path="/", secure=False, httponly=False, samesite="strict"
    )


@router.delete(
    "/session",
    operation_id="iam_logout_v1",
    status_code=204,
    response_class=Response,
    responses=_ERROR_RESPONSES,
    openapi_extra=_unsafe_operation(
        "browser_cookie_only",
        "write:self",
        "LogoutSessionV1",
        "terminal_idempotent_transition",
        precondition=True,
    ),
)
def logout(request: Request, response: Response) -> Response:
    caller = authorize_request(
        request, "write:self", cookie_only=True, require_csrf=True
    )
    session = caller.session
    if session is None:
        raise ProblemError(401, "dashboard_authentication_required")
    version = _precondition(request, session.session_id)
    outcome = ports(request).logout(
        session.session_id,
        version,
        caller.proof.csrf_cookie,
        caller.proof.csrf_header,
        correlation_id=request.state.correlation_id,
    )
    if outcome.code != "revoked":
        raise _session_error(outcome)
    response.status_code = 204
    _clear_cookies(response)
    return response


@router.patch(
    "/session/password",
    operation_id="iam_change_password_v1",
    status_code=204,
    response_class=Response,
    responses=_ERROR_RESPONSES,
    openapi_extra=_unsafe_operation(
        "browser_cookie_only",
        "write:self",
        "ChangeAdministratorPasswordV1",
        "one_time_secret_non_replayable",
        precondition=True,
        idempotency=True,
    ),
)
def change_password(
    input: ChangeAdministratorPasswordInputV1, request: Request, response: Response
) -> Response:
    _json(request)
    _bounded_password_input(input.current_password)
    _bounded_password_input(input.new_password)
    caller = authorize_request(
        request, "write:self", cookie_only=True, require_csrf=True
    )
    session = caller.session
    if session is None:
        raise ProblemError(401, "dashboard_authentication_required")
    version = _password_precondition(request, session.session_id)
    key = _idempotency_key(request)
    outcome = ports(request).change_password(
        session.session_id,
        version,
        caller.proof.csrf_cookie,
        caller.proof.csrf_header,
        SecretInputV1(input.current_password),
        SecretInputV1(input.new_password),
        idempotency_key=key,
        correlation_id=request.state.correlation_id,
    )
    if isinstance(outcome, SessionMutationOutcomeV1):
        raise _session_error(outcome)
    response.status_code = 204
    max_age = max(
        0,
        int((outcome.session.absolute_expires_at - datetime.now(UTC)).total_seconds()),
    )
    response.set_cookie(
        SESSION_COOKIE,
        outcome.session_credential,
        httponly=True,
        secure=False,
        samesite="strict",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        CSRF_COOKIE,
        outcome.csrf_credential,
        httponly=False,
        secure=False,
        samesite="strict",
        path="/",
        max_age=max_age,
    )
    return response


@router.get(
    "/iam/sessions",
    operation_id="iam_list_sessions_v1",
    response_model=BrowserSessionPageV1,
    responses=_ERROR_RESPONSES,
    openapi_extra=_list_operation(
        "browser_cookie_only", "write:sessions", "ListSessionsV1", "-issued_at"
    ),
)
def list_sessions(request: Request) -> BrowserSessionPageV1:
    caller = authorize_request(request, "write:sessions", cookie_only=True)
    query = parse_list_query(request, sort="-issued_at", id_field="session_id")
    codec = cursor_codec(request)
    binding = query.binding("iam_list_sessions_v1", caller.principal)
    keyset = codec.decode(query.cursor, binding) if query.cursor is not None else None
    try:
        items = ports(request).list_sessions(
            caller.principal,
            limit=query.limit,
            cursor=keyset,
            correlation_id=request.state.correlation_id,
        )
        next_keyset = items[-1].session_id.value if len(items) == query.limit else None
        more = bool(
            next_keyset
            and ports(request).list_sessions(
                caller.principal,
                limit=1,
                cursor=next_keyset,
                correlation_id=request.state.correlation_id,
            )
        )
    except SessionQueryErrorV1 as error:
        raise ProblemError(
            401 if error.code == "dashboard_authentication_required" else 400,
            "invalid_cursor" if error.code == "session_cursor_invalid" else error.code,
        ) from None
    return BrowserSessionPageV1(
        items=tuple(_session(item) for item in items),
        page=_page(
            query.limit,
            items,
            more,
            codec.encode(next_keyset, binding) if more and next_keyset else None,
        ),
    )


@router.delete(
    "/iam/sessions/{session_id}",
    operation_id="iam_revoke_session_v1",
    status_code=204,
    response_class=Response,
    responses=_ERROR_RESPONSES,
    openapi_extra=_unsafe_operation(
        "browser_cookie_only",
        "write:sessions",
        "RevokeSessionV1",
        "terminal_idempotent_transition",
        precondition=True,
    ),
)
def revoke_session(session_id: str, request: Request, response: Response) -> Response:
    caller = authorize_request(
        request, "write:sessions", cookie_only=True, require_csrf=True
    )
    target = _id(session_id)
    version = _precondition(request, target)
    actor = caller.session
    if actor is None:
        raise ProblemError(401, "dashboard_authentication_required")
    outcome = ports(request).revoke_session(
        actor.session_id,
        target,
        version,
        caller.proof.csrf_cookie,
        caller.proof.csrf_header,
        correlation_id=request.state.correlation_id,
    )
    if outcome.code != "revoked":
        raise _session_error(outcome)
    response.status_code = 204
    if target == actor.session_id:
        _clear_cookies(response)
    return response


@router.post(
    "/iam/session-revocations",
    operation_id="iam_revoke_other_sessions_v1",
    response_model=SessionRevocationSummaryV1,
    responses=_ERROR_RESPONSES,
    openapi_extra=_unsafe_operation(
        "browser_cookie_only",
        "write:sessions",
        "RevokeAllSessionsV1",
        "replay_safe_representation",
        idempotency=True,
    ),
)
def revoke_other_sessions(request: Request) -> SessionRevocationSummaryV1:
    caller = authorize_request(
        request, "write:sessions", cookie_only=True, require_csrf=True
    )
    actor = caller.session
    if actor is None:
        raise ProblemError(401, "dashboard_authentication_required")
    outcome = ports(request).revoke_other_sessions(
        actor.session_id,
        caller.proof.csrf_cookie,
        caller.proof.csrf_header,
        idempotency_key=_idempotency_key(request),
        correlation_id=request.state.correlation_id,
    )
    if outcome.code != "revoked":
        raise _session_error(outcome)
    return SessionRevocationSummaryV1(affected_count=outcome.affected_count)


@router.get(
    "/api-tokens",
    operation_id="iam_list_api_tokens_v1",
    response_model=ApiTokenPageV1,
    responses=_ERROR_RESPONSES,
    openapi_extra=_list_operation(
        "cookie_or_bearer", "write:tokens", "ListApiTokensV1", "-issued_at"
    ),
)
def list_api_tokens(request: Request) -> ApiTokenPageV1:
    caller = authorize_request(request, "write:tokens")
    query = parse_list_query(request, sort="-issued_at", id_field="api_token_id")
    codec = cursor_codec(request)
    binding = query.binding("iam_list_api_tokens_v1", caller.principal)
    keyset = codec.decode(query.cursor, binding) if query.cursor is not None else None
    try:
        items = ports(request).list_tokens(
            caller.proof,
            limit=query.limit,
            cursor=keyset,
            correlation_id=request.state.correlation_id,
        )
        next_keyset = (
            items[-1].api_token_id.value if len(items) == query.limit else None
        )
        more = bool(
            next_keyset
            and ports(request).list_tokens(
                caller.proof,
                limit=1,
                cursor=next_keyset,
                correlation_id=request.state.correlation_id,
            )
        )
    except TokenQueryErrorV1 as error:
        raise ProblemError(
            401 if error.code == "dashboard_authentication_required" else 400,
            "invalid_cursor" if error.code == "token_cursor_invalid" else error.code,
        ) from None
    return ApiTokenPageV1(
        items=tuple(_token(item) for item in items),
        page=_page(
            query.limit,
            items,
            more,
            codec.encode(next_keyset, binding) if more and next_keyset else None,
        ),
    )


@router.post(
    "/api-tokens",
    operation_id="iam_create_api_token_v1",
    status_code=201,
    response_model=ApiTokenCredentialIssueV1,
    responses=_ERROR_RESPONSES,
    openapi_extra=_unsafe_operation(
        "cookie_or_bearer",
        "write:tokens",
        "CreateApiTokenV1",
        "one_time_secret_non_replayable",
        idempotency=True,
    ),
)
def create_api_token(
    input: CreateApiTokenInputV1, request: Request, response: Response
) -> ApiTokenCredentialIssueV1:
    _json(request)
    caller = authorize_request(request, "write:tokens", require_csrf=True)
    outcome = ports(request).create_token(
        caller.proof,
        name=input.name,
        scopes=input.scopes,
        lifetime_seconds=input.lifetime_seconds,
        idempotency_key=_idempotency_key(request),
        correlation_id=request.state.correlation_id,
    )
    if isinstance(outcome, ApiTokenMutationOutcomeV1):
        raise _token_error(outcome)
    response.headers["ETag"] = encode_strong_etag(
        outcome.token.api_token_id, outcome.token.record_version
    )
    return ApiTokenCredentialIssueV1(
        token=_token(outcome.token), bearer_credential=outcome.bearer_credential
    )


@router.post(
    "/api-tokens/{token_id}/rotations",
    operation_id="iam_rotate_api_token_v1",
    status_code=201,
    response_model=ApiTokenCredentialIssueV1,
    responses=_ERROR_RESPONSES,
    openapi_extra=_unsafe_operation(
        "cookie_or_bearer",
        "write:tokens",
        "RotateApiTokenV1",
        "one_time_secret_non_replayable",
        precondition=True,
        idempotency=True,
    ),
)
def rotate_api_token(
    token_id: str,
    input: RotateApiTokenInputV1,
    request: Request,
    response: Response,
) -> ApiTokenCredentialIssueV1:
    _json(request)
    caller = authorize_request(request, "write:tokens", require_csrf=True)
    target = _id(token_id)
    presented_target, version = _parsed_precondition(request)
    outcome = ports(request).rotate_token(
        caller.proof,
        target,
        version,
        name=input.name,
        scopes=input.scopes,
        lifetime_seconds=input.lifetime_seconds,
        idempotency_key=_idempotency_key(request),
        correlation_id=request.state.correlation_id,
        presented_target_id=presented_target,
    )
    if isinstance(outcome, ApiTokenMutationOutcomeV1):
        raise _token_error(outcome)
    response.headers["ETag"] = encode_strong_etag(
        outcome.token.api_token_id, outcome.token.record_version
    )
    return ApiTokenCredentialIssueV1(
        token=_token(outcome.token), bearer_credential=outcome.bearer_credential
    )


@router.delete(
    "/api-tokens/{token_id}",
    operation_id="iam_revoke_api_token_v1",
    status_code=204,
    response_class=Response,
    responses=_ERROR_RESPONSES,
    openapi_extra=_unsafe_operation(
        "cookie_or_bearer",
        "write:tokens",
        "RevokeApiTokenV1",
        "terminal_idempotent_transition",
        precondition=True,
    ),
)
def revoke_api_token(token_id: str, request: Request, response: Response) -> Response:
    caller = authorize_request(request, "write:tokens", require_csrf=True)
    target = _id(token_id)
    outcome = ports(request).revoke_token(
        caller.proof,
        target,
        _precondition(request, target),
        correlation_id=request.state.correlation_id,
    )
    if outcome.code != "revoked":
        raise _token_error(outcome)
    response.status_code = 204
    return response


@router.get(
    "/iam/security-events",
    operation_id="iam_list_security_events_v1",
    response_model=IamSecurityEventPageV1,
    responses=_ERROR_RESPONSES,
    openapi_extra=_list_operation(
        "cookie_or_bearer",
        "read:diagnostics",
        "ListIamSecurityEventsV1",
        "-occurred_at",
        events=True,
    ),
)
def list_security_events(request: Request) -> IamSecurityEventPageV1:
    caller = authorize_request(request, "read:diagnostics")
    query = parse_list_query(
        request, sort="-occurred_at", id_field="event_id", events=True
    )
    codec = cursor_codec(request)
    binding = query.binding("iam_list_security_events_v1", caller.principal)
    keyset = codec.decode(query.cursor, binding) if query.cursor is not None else None
    try:
        items = ports(request).list_events(
            caller.proof,
            limit=query.limit,
            cursor=keyset,
            event_type=query.event_type,
            outcome=query.outcome,
            occurred_from=query.occurred_from,
            occurred_before=query.occurred_before,
            correlation_id=request.state.correlation_id,
        )
        next_keyset = items[-1].event_id.value if len(items) == query.limit else None
        more = bool(
            next_keyset
            and ports(request).list_events(
                caller.proof,
                limit=1,
                cursor=next_keyset,
                event_type=query.event_type,
                outcome=query.outcome,
                occurred_from=query.occurred_from,
                occurred_before=query.occurred_before,
                correlation_id=request.state.correlation_id,
            )
        )
    except TokenQueryErrorV1 as error:
        raise ProblemError(
            401 if error.code == "dashboard_authentication_required" else 400,
            "invalid_cursor" if error.code == "audit_cursor_invalid" else error.code,
        ) from None
    return IamSecurityEventPageV1(
        items=tuple(_event(item) for item in items),
        page=_page(
            query.limit,
            items,
            more,
            codec.encode(next_keyset, binding) if more and next_keyset else None,
        ),
    )
