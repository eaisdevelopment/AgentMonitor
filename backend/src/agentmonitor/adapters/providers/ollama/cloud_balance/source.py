"""One bounded read of Ollama's documented cloud balance endpoint.

The destination, method, path, TLS policy, request count, and response bounds
are fixed here.  Provider response bytes are parsed into
``OLLAMA-CLOUD-BALANCE-V1`` and are never returned, logged, or retained.
"""

from __future__ import annotations

import http.client
import json
import math
import re
import ssl
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol

from agentmonitor.adapters.providers.ollama.cloud_balance.status import (
    CloudStatus,
    classify_status,
)
from agentmonitor.contracts.providers.ollama.cloud_balance.v1.schema import (
    IncludedCreditsV1,
    LegacyLimitsV1,
    LegacyWindowV1,
    OllamaCloudBalanceV1,
    SourcePeriodV1,
)

SOURCE_ID: Literal["ollama.cloud.balance.v1"] = "ollama.cloud.balance.v1"
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z\Z"
)
_HEADER_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_READ_CHUNK_BYTES = 16 * 1024
_MAX_JSON_DEPTH = 5
_MAX_JSON_NODES = 24
_MAX_JSON_STRING_BYTES = 64
_MAX_RETRY_AFTER_SECONDS = 365 * 24 * 60 * 60
_RETAINED_HEADERS = frozenset(
    {
        "content-encoding",
        "content-length",
        "content-type",
        "retry-after",
        "transfer-encoding",
    }
)


@dataclass(frozen=True, slots=True)
class CloudBalancePolicyV1:
    """Immutable allowlist and resource bounds for one provider request."""

    scheme: Literal["https"]
    host: Literal["ollama.com"]
    port: Literal[443]
    method: Literal["GET"]
    path: Literal["/api/balance"]
    request_count: Literal[1]
    automatic_retry_count: Literal[0]
    follow_redirects: Literal[False]
    use_environment_proxy: Literal[False]
    connect_timeout_seconds: float
    read_timeout_seconds: float
    operation_timeout_seconds: float
    maximum_header_count: int
    maximum_header_bytes: int
    maximum_body_bytes: int


CLOUD_BALANCE_POLICY_V1 = CloudBalancePolicyV1(
    scheme="https",
    host="ollama.com",
    port=443,
    method="GET",
    path="/api/balance",
    request_count=1,
    automatic_retry_count=0,
    follow_redirects=False,
    use_environment_proxy=False,
    connect_timeout_seconds=3.0,
    read_timeout_seconds=3.0,
    operation_timeout_seconds=8.0,
    maximum_header_count=64,
    maximum_header_bytes=16 * 1024,
    maximum_body_bytes=64 * 1024,
)


class CloudBalanceAuthorizationV1(Protocol):
    """Private grant that writes only the header for an already-bound request.

    The provider key never appears in this method signature or return value.
    The future credential boundary owns transient retrieval and header
    application.  The adapter has already fixed the TLS peer, request line and
    ordinary headers before calling this method.
    """

    def apply_authorization_header_v1(
        self, connection: http.client.HTTPSConnection
    ) -> None: ...


AuthorizationFailureCode = Literal[
    "ollama_cloud_store_locked",
    "ollama_cloud_store_unavailable",
]


class CloudBalanceAuthorizationUnavailable(RuntimeError):
    """Sanitized private-boundary failure with no provider or secret detail."""

    def __init__(self, code: AuthorizationFailureCode) -> None:
        self.code = code
        super().__init__(code)


SourceState = Literal[
    "success",
    "unauthorized",
    "access_denied",
    "rate_limited",
    "provider_unavailable",
    "unexpected_response",
    "invalid_provider_data",
    "deadline_exceeded",
    "authorization_unavailable",
    "internal_adapter_error",
]


@dataclass(frozen=True, slots=True)
class CloudBalanceSourceResultV1:
    """Sanitized source outcome; it can never carry response or secret data."""

    state: SourceState
    reason_code: str
    source_id: Literal["ollama.cloud.balance.v1"]
    observed_at: datetime
    http_status: int | None
    balance: OllamaCloudBalanceV1 | None
    retry_after_seconds: int | None


class _InvalidCloudBalance(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> _InvalidCloudBalance:
    return _InvalidCloudBalance(code)


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("ollama_cloud_json_duplicate_key")
        result[key] = value
    return result


def _constant(_value: str) -> Decimal:
    raise _fail("ollama_cloud_number_invalid")


def _bounded_tree(value: object, *, depth: int = 0) -> int:
    if depth > _MAX_JSON_DEPTH:
        raise _fail("ollama_cloud_json_depth_exceeded")
    if type(value) is dict:
        result = 1
        for key, item in value.items():
            if (
                type(key) is not str
                or len(key.encode("utf-8")) > _MAX_JSON_STRING_BYTES
            ):
                raise _fail("ollama_cloud_json_string_invalid")
            result += _bounded_tree(item, depth=depth + 1)
        if result > _MAX_JSON_NODES:
            raise _fail("ollama_cloud_json_nodes_exceeded")
        return result
    if type(value) is list:
        result = 1 + sum(_bounded_tree(item, depth=depth + 1) for item in value)
        if result > _MAX_JSON_NODES:
            raise _fail("ollama_cloud_json_nodes_exceeded")
        return result
    if type(value) is str and len(value.encode("utf-8")) > _MAX_JSON_STRING_BYTES:
        raise _fail("ollama_cloud_json_string_invalid")
    return 1


def _exact_object(value: object, keys: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict or frozenset(value) != keys:
        raise _fail("ollama_cloud_schema_invalid")
    return value


def _number(value: object, *, percent: bool = False) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or value < 0:
        raise _fail("ollama_cloud_number_invalid")
    if percent and value > 100:
        raise _fail("ollama_cloud_number_invalid")
    try:
        # The contract validates the exact coefficient and scale bounds.
        if percent:
            LegacyWindowV1(value, None)
        else:
            IncludedCreditsV1(value, None, None)
    except (InvalidOperation, ValueError) as error:
        raise _fail("ollama_cloud_number_invalid") from error
    return value


def _utc_timestamp(value: object) -> datetime:
    if type(value) is not str or _TIMESTAMP.fullmatch(value) is None:
        raise _fail("ollama_cloud_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise _fail("ollama_cloud_timestamp_invalid") from error
    if parsed.tzinfo is not UTC:
        raise _fail("ollama_cloud_timestamp_invalid")
    return parsed


def parse_cloud_balance_v1(payload: bytes) -> OllamaCloudBalanceV1:
    """Parse the documented closed response without retaining its raw form.

    Provider compatibility still requires a real authenticated response.  This
    function defines the approved schema and fail-closed safety behavior; it
    does not make an authenticated evidence claim by itself.
    """
    if (
        type(payload) is not bytes
        or not 0 < len(payload) <= CLOUD_BALANCE_POLICY_V1.maximum_body_bytes
    ):
        raise _fail("ollama_cloud_body_size_invalid")
    try:
        document = json.loads(
            payload.decode("utf-8", errors="strict"),
            parse_float=Decimal,
            parse_int=Decimal,
            parse_constant=_constant,
            object_pairs_hook=_object,
        )
    except _InvalidCloudBalance:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise _fail("ollama_cloud_json_invalid") from error
    if _bounded_tree(document) > _MAX_JSON_NODES:
        raise _fail("ollama_cloud_json_nodes_exceeded")

    root = _exact_object(document, frozenset({"included", "purchased"}))
    included_value = root["included"]
    if type(included_value) is not dict:
        raise _fail("ollama_cloud_schema_invalid")
    included_keys = frozenset(included_value)
    if included_keys == frozenset({"balance_usd", "allowance_usd", "period"}):
        period_value = _exact_object(
            included_value["period"], frozenset({"from", "until"})
        )
        try:
            included: IncludedCreditsV1 | LegacyLimitsV1 = IncludedCreditsV1(
                balance_usd=_number(included_value["balance_usd"]),
                allowance_usd=_number(included_value["allowance_usd"]),
                period=SourcePeriodV1(
                    start=_utc_timestamp(period_value["from"]),
                    end=_utc_timestamp(period_value["until"]),
                ),
            )
        except _InvalidCloudBalance:
            raise
        except ValueError as error:
            raise _fail("ollama_cloud_schema_invalid") from error
    elif included_keys == frozenset({"session", "weekly"}):

        def legacy_window(value: object) -> LegacyWindowV1:
            item = _exact_object(value, frozenset({"remaining_percent", "resets_at"}))
            return LegacyWindowV1(
                remaining_percent=_number(item["remaining_percent"], percent=True),
                resets_at=_utc_timestamp(item["resets_at"]),
            )

        try:
            included = LegacyLimitsV1(
                session=legacy_window(included_value["session"]),
                weekly=legacy_window(included_value["weekly"]),
            )
        except _InvalidCloudBalance:
            raise
        except ValueError as error:
            raise _fail("ollama_cloud_schema_invalid") from error
    else:
        raise _fail("ollama_cloud_schema_invalid")

    purchased = _exact_object(root["purchased"], frozenset({"balance_usd"}))
    try:
        return OllamaCloudBalanceV1(
            included=included,
            purchased_usd=_number(purchased["balance_usd"]),
        )
    except ValueError as error:
        raise _fail("ollama_cloud_schema_invalid") from error


def _remaining(deadline: float, maximum: float) -> float:
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError("ollama_cloud_deadline_exceeded")
    return min(value, maximum)


def _set_socket_timeout(
    connection: http.client.HTTPSConnection,
    response: http.client.HTTPResponse | None,
    timeout: float,
) -> None:
    transport = connection.sock
    if transport is None and response is not None and response.fp is not None:
        raw = getattr(response.fp, "raw", None)
        transport = getattr(raw, "_sock", None)
    if transport is None:
        raise OSError("ollama_cloud_transport_unavailable")
    transport.settimeout(timeout)


def _headers(response: http.client.HTTPResponse) -> dict[str, tuple[str, ...]]:
    pairs = response.getheaders()
    if len(pairs) > CLOUD_BALANCE_POLICY_V1.maximum_header_count:
        raise _fail("ollama_cloud_headers_too_large")
    size = 0
    result: dict[str, list[str]] = {}
    for raw_name, raw_value in pairs:
        if (
            type(raw_name) is not str
            or type(raw_value) is not str
            or _HEADER_TOKEN.fullmatch(raw_name) is None
        ):
            raise _fail("ollama_cloud_headers_invalid")
        try:
            size += len(raw_name.encode("ascii")) + len(raw_value.encode("latin-1")) + 4
        except UnicodeEncodeError as error:
            raise _fail("ollama_cloud_headers_invalid") from error
        if size > CLOUD_BALANCE_POLICY_V1.maximum_header_bytes:
            raise _fail("ollama_cloud_headers_too_large")
        name = raw_name.lower()
        if name in _RETAINED_HEADERS:
            result.setdefault(name, []).append(raw_value.strip())
    for name in _RETAINED_HEADERS:
        if len(result.get(name, ())) > 1:
            raise _fail("ollama_cloud_headers_invalid")
    return {name: tuple(values) for name, values in result.items()}


def _retry_after(headers: dict[str, tuple[str, ...]]) -> int | None:
    values = headers.get("retry-after")
    if values is None:
        return None
    value = values[0]
    if not value.isascii() or not value.isdigit() or len(value) > 10:
        return None
    seconds = int(value)
    if not 0 <= seconds <= _MAX_RETRY_AFTER_SECONDS:
        return None
    return seconds


def _content_length(headers: dict[str, tuple[str, ...]]) -> int | None:
    values = headers.get("content-length")
    if values is None:
        return None
    value = values[0]
    if not value.isascii() or not value.isdigit() or len(value) > 6:
        raise _fail("ollama_cloud_content_length_invalid")
    length = int(value)
    if length > CLOUD_BALANCE_POLICY_V1.maximum_body_bytes:
        raise _fail("ollama_cloud_body_too_large")
    return length


def _read_body(
    connection: http.client.HTTPSConnection,
    response: http.client.HTTPResponse,
    headers: dict[str, tuple[str, ...]],
    deadline: float,
) -> bytes:
    content_types = headers.get("content-type")
    if content_types is None:
        raise _fail("ollama_cloud_content_type_invalid")
    media_type, separator, parameter = content_types[0].lower().partition(";")
    if media_type.strip() != "application/json" or (
        separator and parameter.strip() != "charset=utf-8"
    ):
        raise _fail("ollama_cloud_content_type_invalid")
    encoding = headers.get("content-encoding")
    if encoding is not None and encoding[0].lower() != "identity":
        raise _fail("ollama_cloud_content_encoding_invalid")
    transfer = headers.get("transfer-encoding")
    if transfer is not None and transfer[0].lower() != "chunked":
        raise _fail("ollama_cloud_transfer_encoding_invalid")
    expected = _content_length(headers)
    if transfer is not None and expected is not None:
        raise _fail("ollama_cloud_framing_invalid")

    result = bytearray()
    maximum = CLOUD_BALANCE_POLICY_V1.maximum_body_bytes
    while True:
        _set_socket_timeout(
            connection,
            response,
            _remaining(deadline, CLOUD_BALANCE_POLICY_V1.read_timeout_seconds),
        )
        chunk = response.read1(min(_READ_CHUNK_BYTES, maximum + 1 - len(result)))
        if not chunk:
            break
        result.extend(chunk)
        if len(result) > maximum:
            raise _fail("ollama_cloud_body_too_large")
    if expected is not None and len(result) != expected:
        raise _fail("ollama_cloud_body_incomplete")
    return bytes(result)


_STATUS_REASON: dict[CloudStatus, str] = {
    "success": "ollama_cloud_success",
    "unauthorized": "ollama_cloud_unauthorized",
    "access_denied": "ollama_cloud_access_denied",
    "rate_limited": "ollama_cloud_rate_limited",
    "provider_unavailable": "ollama_cloud_provider_unavailable",
    "unexpected_response": "ollama_cloud_unexpected_response",
}


def _result(
    state: SourceState,
    reason_code: str,
    *,
    http_status: int | None = None,
    balance: OllamaCloudBalanceV1 | None = None,
    retry_after_seconds: int | None = None,
) -> CloudBalanceSourceResultV1:
    return CloudBalanceSourceResultV1(
        state=state,
        reason_code=reason_code,
        source_id=SOURCE_ID,
        observed_at=datetime.now(UTC),
        http_status=http_status,
        balance=balance,
        retry_after_seconds=retry_after_seconds,
    )


def read_cloud_balance_once_v1(
    *,
    authorization: CloudBalanceAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
) -> CloudBalanceSourceResultV1:
    """Perform exactly one fixed HTTPS GET and return only sanitized data.

    ``None`` authorization is supported only for the real anonymous boundary
    check; it cannot yield a successful balance under the documented API.
    """
    policy = CLOUD_BALANCE_POLICY_V1
    started = time.monotonic()
    if deadline_monotonic is not None and (
        type(deadline_monotonic) is not float
        or not math.isfinite(deadline_monotonic)
        or deadline_monotonic <= started
    ):
        return _result("deadline_exceeded", "ollama_cloud_deadline_exceeded")
    deadline = min(
        started + policy.operation_timeout_seconds,
        deadline_monotonic
        if deadline_monotonic is not None
        else started + policy.operation_timeout_seconds,
    )
    connection: http.client.HTTPSConnection | None = None
    response: http.client.HTTPResponse | None = None
    try:
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        connection = http.client.HTTPSConnection(
            policy.host,
            port=policy.port,
            timeout=_remaining(deadline, policy.connect_timeout_seconds),
            context=context,
        )
        connection.connect()
        _set_socket_timeout(
            connection,
            None,
            _remaining(deadline, policy.read_timeout_seconds),
        )
        connection.putrequest(
            policy.method,
            policy.path,
            skip_host=True,
            skip_accept_encoding=True,
        )
        connection.putheader("Host", policy.host)
        connection.putheader("Accept", "application/json")
        connection.putheader("Accept-Encoding", "identity")
        connection.putheader("Connection", "close")
        if authorization is not None:
            authorization.apply_authorization_header_v1(connection)
        _set_socket_timeout(
            connection,
            None,
            _remaining(deadline, policy.read_timeout_seconds),
        )
        connection.endheaders()
        _set_socket_timeout(
            connection,
            None,
            _remaining(deadline, policy.read_timeout_seconds),
        )
        response = connection.getresponse()
        headers = _headers(response)
        status = classify_status(response.status)
        if status != "success":
            return _result(
                status,
                _STATUS_REASON[status],
                http_status=response.status,
                retry_after_seconds=(
                    _retry_after(headers) if status == "rate_limited" else None
                ),
            )
        body = _read_body(connection, response, headers, deadline)
        _remaining(deadline, policy.operation_timeout_seconds)
        balance = parse_cloud_balance_v1(body)
        body = b""
        _remaining(deadline, policy.operation_timeout_seconds)
        return _result(
            "success",
            _STATUS_REASON["success"],
            http_status=response.status,
            balance=balance,
        )
    except CloudBalanceAuthorizationUnavailable as error:
        return _result("authorization_unavailable", error.code)
    except TimeoutError:
        return _result("deadline_exceeded", "ollama_cloud_deadline_exceeded")
    except _InvalidCloudBalance as error:
        return _result("invalid_provider_data", error.code)
    except (http.client.HTTPException, OSError, ssl.SSLError):
        return _result("provider_unavailable", "ollama_cloud_network_unavailable")
    except Exception:
        # Never propagate or stringify a credential-boundary/provider exception.
        return _result("internal_adapter_error", "ollama_cloud_internal_error")
    finally:
        if response is not None:
            response.close()
        if connection is not None:
            connection.close()
