"""P01's bounded M2 IAM list envelope; M01 still owns ordered keyset reads."""

import base64
import binascii
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from agentmonitor.api.problem import ProblemError
from agentmonitor.contracts.identity_access_v1 import PrincipalV1
from fastapi import Request

_CURSOR_LIFETIME_SECONDS = 900
_MAX_CURSOR_BYTES = 1024
_SAFE_KEYSET_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_SAFE_FILTER_CODE = re.compile(r"[a-z_]{1,64}\Z")
_DECIMAL_LIMIT = re.compile(r"[1-9][0-9]{0,2}\Z")
_BASE64URL = re.compile(r"[A-Za-z0-9_-]+\Z")
_ORDERS = {
    ("-issued_at", "session_id"): ("-issued_at", "-session_id"),
    ("-issued_at", "api_token_id"): ("-issued_at", "-api_token_id"),
    ("-occurred_at", "event_id"): ("-occurred_at", "-event_id"),
}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    if _BASE64URL.fullmatch(text) is None:
        raise ValueError("cursor_segment_invalid")
    decoded = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    if _b64(decoded) != text:
        raise ValueError("cursor_segment_noncanonical")
    return decoded


@dataclass(frozen=True, slots=True)
class ListQueryV1:
    limit: int
    cursor: str | None
    sort: str
    order: tuple[str, str]
    event_type: str | None = None
    outcome: str | None = None
    occurred_from: datetime | None = None
    occurred_before: datetime | None = None

    def binding(self, operation_id: str, principal: PrincipalV1) -> bytes:
        """Canonical safe metadata only; no cookie, bearer, or raw query string."""
        document = {
            "operation": operation_id,
            "limit": self.limit,
            "sort": self.sort,
            "order": self.order,
            "event_type": self.event_type,
            "outcome": self.outcome,
            "occurred_from": _utc(self.occurred_from),
            "occurred_before": _utc(self.occurred_before),
            "principal_id": principal.principal_id.value,
            "credential_id": (
                principal.credential_id.value if principal.credential_id else None
            ),
            "authentication_method": principal.authentication_method,
            "effective_permissions": sorted(principal.effective_permissions),
        }
        return json.dumps(document, sort_keys=True, separators=(",", ":")).encode(
            "ascii"
        )


def _utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _time_filter(raw: str) -> datetime:
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise ProblemError(400, "invalid_filter") from None
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ProblemError(400, "invalid_filter")
    return value.astimezone(UTC)


def parse_list_query_values(
    pairs: tuple[tuple[str, str], ...],
    *,
    sort: str,
    id_field: str,
    events: bool = False,
) -> ListQueryV1:
    """Pure parser for the URL-decoded key/value sequence, preserving repeats."""
    try:
        order = _ORDERS[(sort, id_field)]
    except KeyError:
        raise ValueError("list_order_configuration_invalid") from None
    allowed = {"limit", "cursor", "sort"}
    if events:
        allowed.update({"event_type", "outcome", "occurred_from", "occurred_before"})
    if len(pairs) > len(allowed) or len({key for key, _ in pairs}) != len(pairs):
        raise ProblemError(400, "invalid_filter")
    values = dict(pairs)
    if values.keys() - allowed:
        raise ProblemError(400, "invalid_filter")
    raw_limit = values.get("limit")
    if raw_limit is None:
        limit = 50
    elif _DECIMAL_LIMIT.fullmatch(raw_limit) is None:
        raise ProblemError(400, "invalid_filter")
    else:
        limit = int(raw_limit)
        if limit > 200:
            raise ProblemError(400, "invalid_filter")
    selected_sort = values.get("sort", sort)
    if selected_sort != sort:
        raise ProblemError(400, "invalid_sort")
    cursor = values.get("cursor")
    if cursor is not None and (not cursor or len(cursor) > _MAX_CURSOR_BYTES):
        raise ProblemError(400, "invalid_cursor")
    event_type = values.get("event_type")
    outcome = values.get("outcome")
    if any(
        item is not None and _SAFE_FILTER_CODE.fullmatch(item) is None
        for item in (event_type, outcome)
    ):
        raise ProblemError(400, "invalid_filter")
    from_raw = values.get("occurred_from")
    before_raw = values.get("occurred_before")
    occurred_from = _time_filter(from_raw) if from_raw is not None else None
    occurred_before = _time_filter(before_raw) if before_raw is not None else None
    if (
        occurred_from is not None
        and occurred_before is not None
        and occurred_from >= occurred_before
    ):
        raise ProblemError(400, "invalid_filter")
    return ListQueryV1(
        limit,
        cursor,
        selected_sort,
        order,
        event_type,
        outcome,
        occurred_from,
        occurred_before,
    )


def parse_list_query(
    request: Request, *, sort: str, id_field: str, events: bool = False
) -> ListQueryV1:
    """HTTP adapter; never discard repeated query keys before pure validation."""
    return parse_list_query_values(
        tuple(request.query_params.multi_items()),
        sort=sort,
        id_field=id_field,
        events=events,
    )


class CursorCodecV1:
    """Service-lifetime HMAC envelope; raw keyset ID is safe but untrusted."""

    __slots__ = ("_key",)

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("cursor_key_invalid")
        self._key = key

    def __repr__(self) -> str:
        return "<CursorCodecV1 redacted>"

    def _mac(self, purpose: bytes, material: bytes) -> bytes:
        return hmac.new(self._key, purpose + material, hashlib.sha256).digest()

    def encode(self, keyset_id: str, binding: bytes) -> str:
        if _SAFE_KEYSET_ID.fullmatch(keyset_id) is None:
            raise ValueError("cursor_keyset_invalid")
        payload = {
            "b": _b64(self._mac(b"binding-v1\0", binding)),
            "e": int(time.time()) + _CURSOR_LIFETIME_SECONDS,
            "i": keyset_id,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        return "v1." + _b64(raw) + "." + _b64(self._mac(b"cursor-v1\0", raw))

    def decode(self, cursor: str, binding: bytes) -> str:
        if len(cursor) > _MAX_CURSOR_BYTES or not cursor.isascii():
            raise ProblemError(400, "invalid_cursor")
        parts = cursor.split(".")
        if len(parts) != 3 or parts[0] != "v1":
            raise ProblemError(400, "invalid_cursor")
        try:
            raw = _unb64(parts[1])
            tag = _unb64(parts[2])
            if not hmac.compare_digest(tag, self._mac(b"cursor-v1\0", raw)):
                raise ValueError("cursor_mac_invalid")
            payload = json.loads(raw)
            if not isinstance(payload, dict) or set(payload) != {"b", "e", "i"}:
                raise ValueError("cursor_payload_invalid")
            keyset_id, expires_at, recorded_binding = (
                payload["i"],
                payload["e"],
                payload["b"],
            )
            now = int(time.time())
            if (
                not isinstance(keyset_id, str)
                or _SAFE_KEYSET_ID.fullmatch(keyset_id) is None
                or type(expires_at) is not int
                or expires_at <= now
                or expires_at > now + _CURSOR_LIFETIME_SECONDS
                or not isinstance(recorded_binding, str)
                or len(recorded_binding) != 43
                or _BASE64URL.fullmatch(recorded_binding) is None
            ):
                raise ValueError("cursor_payload_invalid")
        except (ValueError, UnicodeDecodeError, TypeError, KeyError, binascii.Error):
            raise ProblemError(400, "invalid_cursor") from None
        expected = _b64(self._mac(b"binding-v1\0", binding))
        if not hmac.compare_digest(recorded_binding, expected):
            raise ProblemError(400, "cursor_query_mismatch")
        return keyset_id


def cursor_codec(request: Request) -> CursorCodecV1:
    value = getattr(request.app.state, "cursor_codec", None)
    if not isinstance(value, CursorCodecV1):
        raise ProblemError(500, "internal_error")
    return value
