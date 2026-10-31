"""Cookie-authorized explicit managed connection actions; safe status only."""

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import (
    authorize_request,
    correlation_id,
    observation_ports,
)
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
from agentmonitor.api.v1.schemas.providers import (
    CancelProviderConnectionInputV1,
    ProviderConnectionViewV1,
    StartProviderConnectionInputV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    ProviderConnectionErrorV1,
    ProviderConnectionPortV1,
    StartProviderConnectionCommandV1,
)
from agentmonitor.contracts.provider_system_v1 import (
    ProviderConnectionViewV1 as SourceViewV1,
)
from fastapi import APIRouter, Path, Request, Response

router = APIRouter(tags=["providers"])


def _services(request: Request) -> ProviderConnectionPortV1:
    service = observation_ports(request).provider_connections
    if service is None:
        raise ProblemError(503, "provider_connection_unavailable")
    return service


def _view(value: SourceViewV1) -> ProviderConnectionViewV1:
    return ProviderConnectionViewV1(
        account_id=value.account_id.value,
        flow_id=value.flow_id.value if value.flow_id else None,
        state=value.state,
        can_connect=value.can_connect,
        expected_email=value.expected_email,
        started_at=value.started_at,
        expires_at=value.expires_at,
        reason_code=value.reason_code,
    )


def _error(error: ProviderConnectionErrorV1) -> ProblemError:
    return ProblemError(
        {
            "registry_subject_not_found": 404,
            "precondition_failed": 412,
            "idempotency_key_reused": 409,
            "provider_connection_not_eligible": 409,
            "provider_connection_email_required": 422,
            "provider_connection_busy": 409,
            "provider_connection_not_found": 404,
        }.get(error.code, 503),
        error.code,
    )


def _start_policy() -> dict[str, object]:
    result = _version_policy("StartProviderConnectionCommandV1", idempotent=True)
    result.update(
        {
            "security": [{"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []}],
            "x-agentmonitor-auth-profile": "browser_cookie_only",
            "x-agentmonitor-required-permission": "write:reauth",
            "x-agentmonitor-replay-policy": "replay_safe_connection_receipt",
        }
    )
    return result


@router.get(
    "/accounts/{account_id}/connection",
    operation_id="provider_get_connection_v1",
    response_model=ProviderConnectionViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:accounts", "ProviderConnectionPortV1.read"),
)
def get_connection(
    request: Request,
    response: Response,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> ProviderConnectionViewV1:
    authorize_request(request, "read:accounts")
    reject_unknown_query(request, frozenset())
    response.headers["Cache-Control"] = "no-store, private"
    try:
        return _view(_services(request).read(OpaqueIdV1(account_id)))
    except ProviderConnectionErrorV1 as error:
        raise _error(error) from None
    except (OSError, ValueError, RuntimeError):
        raise ProblemError(503, "provider_connection_unavailable") from None


@router.post(
    "/accounts/{account_id}/connection",
    operation_id="provider_start_connection_v1",
    status_code=202,
    response_model=ProviderConnectionViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=_start_policy(),
)
def start_connection(
    request: Request,
    response: Response,
    input: StartProviderConnectionInputV1,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> ProviderConnectionViewV1:
    caller = authorize_request(
        request, "write:reauth", cookie_only=True, require_csrf=True
    )
    reject_unknown_query(request, frozenset())
    command = StartProviderConnectionCommandV1(
        OpaqueIdV1(account_id),
        _expected_version(request, account_id),
        input.expected_email,
        caller.principal.principal_id,
        _idempotency_key(request),
        OpaqueIdV1(correlation_id(request)),
    )
    try:
        value = _services(request).start(command)
        response.headers["Location"] = f"/api/v1/accounts/{account_id}/connection"
        response.headers["Cache-Control"] = "no-store, private"
        return _view(value)
    except ProviderConnectionErrorV1 as error:
        raise _error(error) from None
    except (OSError, ValueError, RuntimeError):
        raise ProblemError(503, "provider_connection_unavailable") from None


@router.delete(
    "/accounts/{account_id}/connection",
    operation_id="provider_cancel_connection_v1",
    response_model=ProviderConnectionViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra={
        "security": [{"BrowserSessionCookieV1": [], "BrowserCsrfHeaderV1": []}],
        "x-agentmonitor-auth-profile": "browser_cookie_only",
        "x-agentmonitor-required-permission": "write:reauth",
        "x-agentmonitor-application-port": "ProviderConnectionPortV1.cancel",
        "x-agentmonitor-replay-policy": "cancel_owned_connection",
        "x-agentmonitor-error-schema": "SafeProblemV1",
    },
)
def cancel_connection(
    request: Request,
    response: Response,
    input: CancelProviderConnectionInputV1,
    account_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
) -> ProviderConnectionViewV1:
    authorize_request(request, "write:reauth", cookie_only=True, require_csrf=True)
    reject_unknown_query(request, frozenset())
    response.headers["Cache-Control"] = "no-store, private"
    try:
        return _view(
            _services(request).cancel(OpaqueIdV1(account_id), OpaqueIdV1(input.flow_id))
        )
    except ProviderConnectionErrorV1 as error:
        raise _error(error) from None
    except (OSError, ValueError, RuntimeError):
        raise ProblemError(503, "provider_connection_unavailable") from None
