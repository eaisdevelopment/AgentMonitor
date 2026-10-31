"""Shared declaration helpers for read-only observation transports."""

import json
import re
from typing import Any

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import AuthorizedCallerV1
from agentmonitor.api.v1.pagination import cursor_codec
from agentmonitor.api.v1.schemas.registry import AvailabilityV1, PageMetaV1
from agentmonitor.contracts.common_v1 import QueryAvailabilityV1
from fastapi import Request

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
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

SECURITY: list[dict[str, list[str]]] = [
    {"BrowserSessionCookieV1": []},
    {"BearerTokenV1": []},
]
_OPAQUE_SELECTOR = re.compile(r"[A-Za-z0-9._:-]{1,256}\Z")


def reject_unknown_query(request: Request, allowed: frozenset[str]) -> None:
    keys = tuple(key for key, _value in request.query_params.multi_items())
    if len(keys) != len(set(keys)) or any(key not in allowed for key in keys):
        raise ProblemError(400, "invalid_filter")


def require_opaque_selector(value: str) -> str:
    if _OPAQUE_SELECTOR.fullmatch(value) is None:
        raise ProblemError(400, "invalid_filter")
    return value


def availability(source: QueryAvailabilityV1) -> AvailabilityV1:
    return AvailabilityV1(
        state=source.state,
        reason_code=source.reason_code,
        as_of=source.as_of,
    )


def policy(permission: str, port: str) -> dict[str, object]:
    return {
        "security": SECURITY,
        "x-agentmonitor-auth-profile": "cookie_or_bearer",
        "x-agentmonitor-required-permission": permission,
        "x-agentmonitor-application-port": port,
        "x-agentmonitor-replay-policy": "safe_query_repeat",
        "x-agentmonitor-error-schema": "SafeProblemV1",
    }


def _binding(
    operation_id: str,
    caller: AuthorizedCallerV1,
    limit: int,
    filters: dict[str, str | None],
) -> bytes:
    return json.dumps(
        {
            "operation": operation_id,
            "principal_id": caller.principal.principal_id.value,
            "credential_id": (
                caller.principal.credential_id.value
                if caller.principal.credential_id is not None
                else None
            ),
            "limit": limit,
            "filters": filters,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def decode_cursor(
    request: Request,
    caller: AuthorizedCallerV1,
    cursor: str | None,
    *,
    operation_id: str,
    limit: int,
    filters: dict[str, str | None],
) -> str | None:
    if cursor is None:
        return None
    return cursor_codec(request).decode(
        cursor, _binding(operation_id, caller, limit, filters)
    )


def page_meta(
    request: Request,
    caller: AuthorizedCallerV1,
    *,
    operation_id: str,
    limit: int,
    has_more: bool,
    next_key: str | None,
    filters: dict[str, str | None],
) -> PageMetaV1:
    next_cursor = None
    if has_more:
        if next_key is None:
            raise ValueError("query_page_next_key_missing")
        next_cursor = cursor_codec(request).encode(
            next_key, _binding(operation_id, caller, limit, filters)
        )
    return PageMetaV1(limit=limit, next_cursor=next_cursor, has_more=has_more)
