"""One bounded read of Ollama's documented cloud balance endpoint.

The destination, method, path, TLS policy, request count, and response bounds
are fixed here.  Provider response bytes are parsed into
``OLLAMA-CLOUD-BALANCE-V1`` and are never returned, logged, or retained.
"""

from __future__ import annotations

import http.client
import io
import json
import math
import os
import re
import signal
import ssl
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from agentmonitor.contracts.provider_system_v1 import (
        ScheduledSourceAdmissionProofV1,
    )

from agentmonitor.adapters.providers.ollama.cloud_balance.credential_lock import (
    validated_credential_lock_descriptor,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    EnvCredentialFileAuthorityV1,
    EnvCredentialFileError,
    InheritedEnvCredentialFileV1,
    env_credential_file_lease_v1,
    validated_inherited_env_file_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.status import (
    CloudStatus,
    classify_status,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.transport_policy import (
    CLOUD_BALANCE_POLICY_V1 as CLOUD_BALANCE_POLICY_V1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.transport_policy import (
    CloudBalancePolicyV1 as CloudBalancePolicyV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.worker_protocol import (
    MAX_WORKER_RESULT_BYTES,
    WorkerResultV2,
    decode_worker_result_v2,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.providers.ollama.cloud_balance.v1.schema import (
    IncludedCreditsV1,
    LegacyLimitsV1,
    LegacyWindowV1,
    OllamaCloudBalanceV1,
    SourcePeriodV1,
)
from agentmonitor.contracts.registry_v1 import (
    AccountCredentialLockLeaseV1,
    ActiveCredentialBindingRefV1,
    InheritedAccountCredentialLockV1,
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
_MAX_RETRY_AFTER_SECONDS = 2**63 - 1
_MAX_RETRY_AFTER_TEXT = str(_MAX_RETRY_AFTER_SECONDS)
_MAX_BEARER_BYTES = ENV_AUTHORIZATION_POLICY_V1.maximum_token_bytes
_RETAINED_HEADERS = frozenset(
    {
        "content-encoding",
        "content-length",
        "content-type",
        "retry-after",
        "transfer-encoding",
    }
)


class _AuthorizationContractInvalid(RuntimeError):
    pass


class CloudBalanceAuthorizationSinkV1:
    """Single-use bearer sink with no transport or debug-control authority."""

    __slots__ = ("__active", "__applied", "__connection")

    def __init__(self, connection: http.client.HTTPSConnection) -> None:
        self.__connection = connection
        self.__active = True
        self.__applied = False

    def put_bearer_token_v1(self, token: bytearray) -> None:
        """Consume one bounded visible-ASCII token and clear the caller buffer."""
        if not self.__active or self.__applied:
            raise _AuthorizationContractInvalid(
                "ollama_cloud_authorization_contract_invalid"
            )
        if type(token) is not bytearray:
            raise _AuthorizationContractInvalid(
                "ollama_cloud_authorization_contract_invalid"
            )
        try:
            if not 1 <= len(token) <= _MAX_BEARER_BYTES or any(
                value < 0x21 or value > 0x7E for value in token
            ):
                raise _AuthorizationContractInvalid(
                    "ollama_cloud_authorization_contract_invalid"
                )
            self.__connection.putheader("Authorization", b"Bearer " + bytes(token))
            self.__applied = True
        finally:
            token[:] = b"\x00" * len(token)

    def _finish_v1(self) -> None:
        self.__active = False
        if not self.__applied:
            raise _AuthorizationContractInvalid(
                "ollama_cloud_authorization_contract_invalid"
            )

    def _cancel_v1(self) -> None:
        self.__active = False


class CloudBalanceAuthorizationV1(Protocol):
    """Resolved private grant limited to a single-use bearer sink.

    The provider key never appears in this method signature or return value.
    The private credential boundary owns transient retrieval and header
    application. The grant receives no connection, destination, request,
    logging, debug, redirect, or response authority.
    """

    def apply_authorization_v1(self, sink: CloudBalanceAuthorizationSinkV1) -> None: ...


AuthorizationFailureCode = Literal[
    "ollama_cloud_store_locked",
    "ollama_cloud_store_unavailable",
]


class CloudBalanceAuthorizationUnavailable(RuntimeError):
    """Sanitized private-boundary failure with no provider or secret detail."""

    def __init__(self, code: AuthorizationFailureCode) -> None:
        if type(code) is not str or code not in {
            "ollama_cloud_store_locked",
            "ollama_cloud_store_unavailable",
        }:
            raise ValueError(
                "ollama_cloud_authorization_failure_code_invalid"
            ) from None
        self.code: AuthorizationFailureCode = code
        super().__init__(code)


SourceState = Literal[
    "source_not_admitted",
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
RetryAfterState = Literal[
    "not_applicable",
    "absent",
    "invalid",
    "available",
    "unrepresentable",
]
DispatchCertainty = Literal["not_started", "may_have_started", "response_received"]


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
    retry_after_state: RetryAfterState
    dispatch_certainty: DispatchCertainty

    def __post_init__(self) -> None:
        if self.dispatch_certainty not in {
            "not_started",
            "may_have_started",
            "response_received",
        } or (self.http_status is not None) != (
            self.dispatch_certainty == "response_received"
        ):
            raise ValueError("ollama_cloud_dispatch_certainty_invalid")


@dataclass(frozen=True, slots=True)
class CloudBalanceParseResultV1:
    """A parsed typed value or one stable code, never a payload exception."""

    balance: OllamaCloudBalanceV1 | None
    reason_code: str | None

    def __post_init__(self) -> None:
        if (self.balance is None) == (self.reason_code is None):
            raise ValueError("ollama_cloud_parse_result_invalid")


class _InvalidCloudBalance(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> _InvalidCloudBalance:
    return _InvalidCloudBalance(code)


class _BoundedHeaderReader(io.BufferedIOBase):
    """Enforce the policy byte/line budget before stdlib header parsing."""

    def __init__(
        self, source: io.BufferedIOBase, *, maximum_bytes: int, maximum_lines: int
    ) -> None:
        super().__init__()
        self._source = source
        self._maximum_bytes = maximum_bytes
        self._maximum_lines = maximum_lines
        self._bytes_read = 0
        self._lines_read = 0

    def readline(self, size: int | None = -1, /) -> bytes:
        remaining = self._maximum_bytes - self._bytes_read
        # Read one byte beyond the remaining budget so an oversized line cannot
        # be mistaken for a complete bounded line by ``http.client``.
        bounded_size = remaining + 1
        if size is not None and size >= 0:
            bounded_size = min(size, bounded_size)
        line = self._source.readline(bounded_size)
        self._bytes_read += len(line)
        if self._bytes_read > self._maximum_bytes:
            raise _fail("ollama_cloud_headers_too_large")
        if line not in {b"", b"\n", b"\r\n"}:
            self._lines_read += 1
            if self._lines_read > self._maximum_lines:
                raise _fail("ollama_cloud_headers_too_large")
        return line


class _BoundedHeaderHTTPResponse(http.client.HTTPResponse):
    """Apply the cumulative ingress limit around ``HTTPResponse.begin``."""

    def begin(self) -> None:
        if self.headers is not None:
            return
        source = self.fp
        if source is None:
            raise _fail("ollama_cloud_headers_invalid")
        bounded = _BoundedHeaderReader(
            source,
            maximum_bytes=CLOUD_BALANCE_POLICY_V1.maximum_header_bytes,
            # ``HTTPResponse.begin`` reads the status line through this same
            # object.  The published count applies to response-header lines.
            maximum_lines=CLOUD_BALANCE_POLICY_V1.maximum_header_count + 1,
        )
        self.fp = bounded
        try:
            super().begin()
        finally:
            self.fp = source


class _BoundedHeaderHTTPSConnection(http.client.HTTPSConnection):
    response_class = _BoundedHeaderHTTPResponse


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


def _parse_cloud_balance_v1(payload: bytes) -> OllamaCloudBalanceV1:
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


def parse_cloud_balance_v1(payload: bytes) -> CloudBalanceParseResultV1:
    """Return only a typed value or stable code after all raw frames unwind."""
    try:
        balance = _parse_cloud_balance_v1(payload)
    except _InvalidCloudBalance as error:
        code = error.code
    except InvalidOperation:
        code = "ollama_cloud_number_invalid"
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        code = "ollama_cloud_json_invalid"
    except (TypeError, ValueError):
        code = "ollama_cloud_schema_invalid"
    else:
        payload = b""
        return CloudBalanceParseResultV1(balance=balance, reason_code=None)
    payload = b""
    return CloudBalanceParseResultV1(balance=None, reason_code=code)


def _remaining(deadline: float, maximum: float) -> float:
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError("ollama_cloud_deadline_exceeded")
    return min(value, maximum)


def _secure_tls_context() -> ssl.SSLContext:
    """Build verified TLS without honoring environment-requested key logging."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs(ssl.Purpose.SERVER_AUTH)
    context.keylog_filename = None  # type: ignore[assignment]
    return context


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
    if not value.isascii() or not value.isdigit():
        return None
    normalized = value.lstrip("0") or "0"
    if len(normalized) > len(_MAX_RETRY_AFTER_TEXT) or (
        len(normalized) == len(_MAX_RETRY_AFTER_TEXT)
        and normalized > _MAX_RETRY_AFTER_TEXT
    ):
        raise _fail("ollama_cloud_retry_after_unrepresentable")
    return int(normalized)


def _retry_after_state(
    headers: dict[str, tuple[str, ...]],
) -> tuple[int | None, RetryAfterState]:
    values = headers.get("retry-after")
    if values is None:
        return None, "absent"
    value = values[0]
    if not value.isascii() or not value.isdigit():
        return None, "invalid"
    return _retry_after(headers), "available"


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
    dispatch_certainty: DispatchCertainty,
    http_status: int | None = None,
    balance: OllamaCloudBalanceV1 | None = None,
    retry_after_seconds: int | None = None,
    retry_after_state: RetryAfterState = "not_applicable",
    observed_at: datetime | None = None,
) -> CloudBalanceSourceResultV1:
    return CloudBalanceSourceResultV1(
        state=state,
        reason_code=reason_code,
        source_id=SOURCE_ID,
        observed_at=datetime.now(UTC) if observed_at is None else observed_at,
        http_status=http_status,
        balance=balance,
        retry_after_seconds=retry_after_seconds,
        retry_after_state=retry_after_state,
        dispatch_certainty=dispatch_certainty,
    )


def _read_cloud_balance_once_v1(
    *,
    authorization: CloudBalanceAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
) -> CloudBalanceSourceResultV1:
    """Perform one fixed request; ``None`` is private to the admission probe."""
    policy = CLOUD_BALANCE_POLICY_V1
    started = time.monotonic()
    if deadline_monotonic is not None and (
        type(deadline_monotonic) is not float
        or not math.isfinite(deadline_monotonic)
        or deadline_monotonic <= started
    ):
        return _result(
            "deadline_exceeded",
            "ollama_cloud_deadline_exceeded",
            dispatch_certainty="not_started",
        )
    deadline = min(
        started + policy.operation_timeout_seconds,
        deadline_monotonic
        if deadline_monotonic is not None
        else started + policy.operation_timeout_seconds,
    )
    connection: http.client.HTTPSConnection | None = None
    response: http.client.HTTPResponse | None = None
    dispatch_certainty: DispatchCertainty = "not_started"
    try:
        connection = _BoundedHeaderHTTPSConnection(
            policy.host,
            port=policy.port,
            timeout=_remaining(deadline, policy.connect_timeout_seconds),
            context=_secure_tls_context(),
        )
        connection.set_debuglevel(0)
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
            sink = CloudBalanceAuthorizationSinkV1(connection)
            try:
                authorization.apply_authorization_v1(sink)
            except Exception:
                sink._cancel_v1()
                raise
            sink._finish_v1()
        # The resolved grant never receives the connection, and debug output is
        # disabled again immediately before the buffered secret header is sent.
        connection.set_debuglevel(0)
        connection.connect()
        _set_socket_timeout(
            connection,
            None,
            _remaining(deadline, policy.read_timeout_seconds),
        )
        # ``endheaders`` may partially send before raising. From immediately
        # before that call until a status arrives, no caller may infer that the
        # provider did not receive the request.
        dispatch_certainty = "may_have_started"
        connection.endheaders()
        _set_socket_timeout(
            connection,
            None,
            _remaining(deadline, policy.read_timeout_seconds),
        )
        response = connection.getresponse()
        dispatch_certainty = "response_received"
        _remaining(deadline, policy.operation_timeout_seconds)
        headers = _headers(response)
        status = classify_status(response.status)
        if status != "success":
            if status == "rate_limited":
                try:
                    retry_after_seconds, retry_after_state = _retry_after_state(headers)
                except _InvalidCloudBalance as error:
                    return _result(
                        "invalid_provider_data",
                        error.code,
                        dispatch_certainty=dispatch_certainty,
                        http_status=response.status,
                        retry_after_state="unrepresentable",
                    )
            else:
                retry_after_seconds = None
                retry_after_state = "not_applicable"
            return _result(
                status,
                _STATUS_REASON[status],
                dispatch_certainty=dispatch_certainty,
                http_status=response.status,
                retry_after_seconds=retry_after_seconds,
                retry_after_state=retry_after_state,
            )
        body = _read_body(connection, response, headers, deadline)
        _remaining(deadline, policy.operation_timeout_seconds)
        parsed = parse_cloud_balance_v1(body)
        body = b""
        _remaining(deadline, policy.operation_timeout_seconds)
        if parsed.balance is None:
            return _result(
                "invalid_provider_data",
                parsed.reason_code or "ollama_cloud_schema_invalid",
                dispatch_certainty=dispatch_certainty,
                http_status=response.status,
            )
        return _result(
            "success",
            _STATUS_REASON["success"],
            dispatch_certainty=dispatch_certainty,
            http_status=response.status,
            balance=parsed.balance,
        )
    except CloudBalanceAuthorizationUnavailable as error:
        return _result(
            "authorization_unavailable",
            error.code,
            dispatch_certainty=dispatch_certainty,
            http_status=response.status if response is not None else None,
        )
    except TimeoutError:
        return _result(
            "deadline_exceeded",
            "ollama_cloud_deadline_exceeded",
            dispatch_certainty=dispatch_certainty,
            http_status=response.status if response is not None else None,
        )
    except _InvalidCloudBalance as error:
        return _result(
            "invalid_provider_data",
            error.code,
            dispatch_certainty=dispatch_certainty,
            http_status=response.status if response is not None else None,
        )
    except (http.client.HTTPException, OSError, ssl.SSLError):
        return _result(
            "provider_unavailable",
            "ollama_cloud_network_unavailable",
            dispatch_certainty=dispatch_certainty,
            http_status=response.status if response is not None else None,
        )
    except Exception:
        # Never propagate or stringify a credential-boundary/provider exception.
        return _result(
            "internal_adapter_error",
            "ollama_cloud_internal_error",
            dispatch_certainty=dispatch_certainty,
            http_status=response.status if response is not None else None,
        )
    finally:
        if response is not None:
            response.close()
        if connection is not None:
            buffer = getattr(connection, "_buffer", None)
            if type(buffer) is list:
                buffer.clear()
            connection.set_debuglevel(0)
            connection.close()


def read_cloud_balance_once_v1(
    *,
    authorization: CloudBalanceAuthorizationV1,
    deadline_monotonic: float | None = None,
) -> CloudBalanceSourceResultV1:
    """Use one pre-resolved private grant; authenticated admission is pending."""
    if not CLOUD_BALANCE_POLICY_V1.authenticated_collection_admitted:
        return _result(
            "source_not_admitted",
            "ollama_cloud_authenticated_source_not_admitted",
            dispatch_certainty="not_started",
        )
    return _read_cloud_balance_once_v1(
        authorization=authorization,
        deadline_monotonic=deadline_monotonic,
    )


def _stop_worker_process(process: subprocess.Popen[bytes]) -> bool:
    """Kill the pinned live session leader and reap it within one second."""
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            return False
    try:
        process.wait(timeout=1.0)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass
        return False
    return True


def _map_worker_result(
    worker: WorkerResultV2, *, authenticated: bool
) -> CloudBalanceSourceResultV1:
    state = worker.state
    status = worker.http_status
    retry_after = worker.retry_after_seconds
    retry_state = worker.retry_after_state
    observed_at = worker.observed_at
    dispatch_certainty = worker.dispatch_certainty

    def worker_failed() -> CloudBalanceSourceResultV1:
        return _result(
            "internal_adapter_error",
            "ollama_cloud_worker_failed",
            dispatch_certainty=dispatch_certainty,
            http_status=status,
            observed_at=observed_at,
        )

    if state == "success":
        if not authenticated:
            return _result(
                "unexpected_response",
                "ollama_cloud_anonymous_success_unexpected",
                dispatch_certainty=dispatch_certainty,
                http_status=status,
                observed_at=observed_at,
            )
        if (
            status is None
            or classify_status(status) != "success"
            or worker.balance is None
            or retry_after is not None
            or retry_state != "not_applicable"
        ):
            return worker_failed()
        return _result(
            "success",
            "ollama_cloud_success",
            dispatch_certainty=dispatch_certainty,
            http_status=status,
            balance=worker.balance,
            observed_at=observed_at,
        )
    ordinary_states = {
        "unauthorized",
        "access_denied",
        "rate_limited",
        "provider_unavailable",
        "unexpected_response",
    }
    if state in ordinary_states:
        if state == "provider_unavailable":
            if status is not None and classify_status(status) not in {
                "success",
                "provider_unavailable",
            }:
                return worker_failed()
        elif status is None or classify_status(status) != state:
            return worker_failed()
        if state == "rate_limited":
            if retry_state not in {"absent", "invalid", "available"} or (
                (retry_state == "available") != (retry_after is not None)
            ):
                return worker_failed()
        elif retry_after is not None or retry_state != "not_applicable":
            return worker_failed()
        reason = (
            "ollama_cloud_network_unavailable"
            if state == "provider_unavailable" and status is None
            else _STATUS_REASON[state]  # type: ignore[index]
        )
        return _result(
            state,  # type: ignore[arg-type]
            reason,
            dispatch_certainty=dispatch_certainty,
            http_status=status,
            retry_after_seconds=retry_after,
            retry_after_state=retry_state,
            observed_at=observed_at,
        )
    if (
        state == "deadline_exceeded"
        and (status is None or classify_status(status) == "success")
        and retry_after is None
        and retry_state == "not_applicable"
    ):
        return _result(
            "deadline_exceeded",
            "ollama_cloud_deadline_exceeded",
            dispatch_certainty=dispatch_certainty,
            http_status=status,
            observed_at=observed_at,
        )
    if (
        state == "authorization_unavailable"
        and authenticated
        and status is None
        and dispatch_certainty == "not_started"
        and retry_after is None
        and retry_state == "not_applicable"
    ):
        return _result(
            "authorization_unavailable",
            "ollama_cloud_store_unavailable",
            dispatch_certainty=dispatch_certainty,
            observed_at=observed_at,
        )
    if (
        state == "invalid_provider_data"
        and status in {200, 429}
        and retry_after is None
        and (
            (status == 200 and retry_state == "not_applicable")
            or (status == 429 and retry_state == "unrepresentable")
        )
    ):
        return _result(
            "invalid_provider_data",
            "ollama_cloud_probe_invalid_provider_data",
            dispatch_certainty=dispatch_certainty,
            http_status=status,
            retry_after_state=(
                "unrepresentable"
                if retry_state == "unrepresentable"
                else "not_applicable"
            ),
            observed_at=observed_at,
        )
    if (
        state == "internal_adapter_error"
        and retry_after is None
        and retry_state == "not_applicable"
    ):
        return worker_failed()
    return worker_failed()


def _worker_result(
    payload: bytes,
    returncode: int,
    *,
    authenticated: bool,
    fallback_certainty: DispatchCertainty,
) -> CloudBalanceSourceResultV1:
    if returncode != 0 or not 0 < len(payload) <= MAX_WORKER_RESULT_BYTES:
        return _result(
            "internal_adapter_error",
            "ollama_cloud_worker_failed",
            dispatch_certainty=fallback_certainty,
        )
    try:
        worker = decode_worker_result_v2(payload)
    except ValueError:
        return _result(
            "internal_adapter_error",
            "ollama_cloud_worker_failed",
            dispatch_certainty=fallback_certainty,
        )
    return _map_worker_result(worker, authenticated=authenticated)


def _run_isolated_worker(
    deadline: float,
    *,
    binding_id: str | None = None,
    account_id: OpaqueIdV1 | None = None,
    credential_lock: InheritedAccountCredentialLockV1 | None = None,
    credential_file: InheritedEnvCredentialFileV1 | None = None,
) -> CloudBalanceSourceResultV1:
    helper = Path(__file__).with_name("deadline_helper.py")
    executable = Path(sys.executable)
    if (
        not helper.is_file()
        or helper.is_symlink()
        or not executable.is_absolute()
        or not executable.is_file()
    ):
        return _result(
            "internal_adapter_error",
            "ollama_cloud_worker_unavailable",
            dispatch_certainty="not_started",
        )
    process: subprocess.Popen[bytes] | None = None
    fallback_certainty: DispatchCertainty = "not_started"
    try:
        command = [str(executable), "-I", "-B", str(helper), format(deadline, ".17g")]
        environment = {"LC_ALL": "C.UTF-8"}
        pass_fds: tuple[int, ...] = ()
        if binding_id is not None:
            if (
                type(credential_lock) is not InheritedAccountCredentialLockV1
                or not isinstance(account_id, OpaqueIdV1)
                or type(credential_file) is not InheritedEnvCredentialFileV1
            ):
                return _result(
                    "internal_adapter_error",
                    "ollama_cloud_credential_lock_invalid",
                    dispatch_certainty="not_started",
                )
            try:
                lock_arguments = credential_lock.subprocess_arguments(account_id)
                lock_descriptor, directory_descriptor = (
                    validated_credential_lock_descriptor(credential_lock, account_id)
                )
                validated_inherited_env_file_v1(credential_file)
                credential_file_arguments = credential_file.subprocess_arguments()
                credential_file_descriptors = credential_file.subprocess_descriptors()
            except (OSError, ValueError):
                return _result(
                    "internal_adapter_error",
                    "ollama_cloud_credential_lock_invalid",
                    dispatch_certainty="not_started",
                )
            command.append(binding_id)
            command.extend(lock_arguments)
            command.extend(credential_file_arguments)
            pass_fds = (
                lock_descriptor,
                directory_descriptor,
                *credential_file_descriptors,
            )
        elif (
            credential_lock is not None
            or account_id is not None
            or credential_file is not None
        ):
            return _result(
                "internal_adapter_error",
                "ollama_cloud_worker_unavailable",
                dispatch_certainty="not_started",
            )
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=helper.parent,
            env=environment,
            close_fds=True,
            pass_fds=pass_fds,
            start_new_session=True,
        )
        fallback_certainty = "may_have_started"
        stdout, _ = process.communicate(
            timeout=_remaining(
                deadline, CLOUD_BALANCE_POLICY_V1.operation_timeout_seconds
            )
        )
        if not _stop_worker_process(process):
            return _result(
                "internal_adapter_error",
                "ollama_cloud_worker_cleanup_failed",
                dispatch_certainty=fallback_certainty,
            )
        if time.monotonic() >= deadline:
            return _result(
                "deadline_exceeded",
                "ollama_cloud_deadline_exceeded",
                dispatch_certainty=fallback_certainty,
            )
        if credential_lock is not None and account_id is not None:
            try:
                validated_credential_lock_descriptor(credential_lock, account_id)
                if credential_file is None:
                    raise ValueError("ollama_env_lease_invalid")
                validated_inherited_env_file_v1(credential_file)
            except (OSError, ValueError):
                return _result(
                    "internal_adapter_error",
                    "ollama_cloud_credential_lock_invalid",
                    dispatch_certainty=fallback_certainty,
                )
        return _worker_result(
            stdout,
            process.returncode,
            authenticated=binding_id is not None,
            fallback_certainty=fallback_certainty,
        )
    except (TimeoutError, subprocess.TimeoutExpired):
        if process is not None and not _stop_worker_process(process):
            return _result(
                "internal_adapter_error",
                "ollama_cloud_worker_cleanup_failed",
                dispatch_certainty=fallback_certainty,
            )
        return _result(
            "deadline_exceeded",
            "ollama_cloud_deadline_exceeded",
            dispatch_certainty=fallback_certainty,
        )
    except (OSError, subprocess.SubprocessError):
        if process is not None and not _stop_worker_process(process):
            return _result(
                "internal_adapter_error",
                "ollama_cloud_worker_cleanup_failed",
                dispatch_certainty=fallback_certainty,
            )
        return _result(
            "internal_adapter_error",
            "ollama_cloud_worker_unavailable",
            dispatch_certainty=fallback_certainty,
        )
    finally:
        if process is not None:
            _stop_worker_process(process)


def probe_cloud_balance_endpoint_v1(
    *, deadline_monotonic: float | None = None
) -> CloudBalanceSourceResultV1:
    """Bound DNS, TLS and headers in a killable credential-free process."""
    started = time.monotonic()
    if deadline_monotonic is not None and (
        type(deadline_monotonic) is not float
        or not math.isfinite(deadline_monotonic)
        or deadline_monotonic <= started
    ):
        return _result(
            "deadline_exceeded",
            "ollama_cloud_deadline_exceeded",
            dispatch_certainty="not_started",
        )
    deadline = min(
        started + CLOUD_BALANCE_POLICY_V1.operation_timeout_seconds,
        deadline_monotonic
        if deadline_monotonic is not None
        else started + CLOUD_BALANCE_POLICY_V1.operation_timeout_seconds,
    )
    return _run_isolated_worker(deadline)


def probe_cloud_balance_for_binding_v1(
    *,
    binding: ActiveCredentialBindingRefV1,
    credential_lock: AccountCredentialLockLeaseV1 | None = None,
    credential_authority: EnvCredentialFileAuthorityV1 | None = None,
    deadline_monotonic: float | None = None,
) -> CloudBalanceSourceResultV1:
    """Run the explicit admission probe in one isolated child.

    The reference is owner asserted and proves no provider identity. Its exact
    generation must be rechecked transactionally before any observation commit.
    This source candidate is not scheduled until authenticated live validation.
    """
    if not isinstance(binding, ActiveCredentialBindingRefV1):
        return _result(
            "internal_adapter_error",
            "ollama_cloud_binding_invalid",
            dispatch_certainty="not_started",
        )
    if type(credential_lock) is not AccountCredentialLockLeaseV1:
        return _result(
            "internal_adapter_error",
            "ollama_cloud_credential_lock_invalid",
            dispatch_certainty="not_started",
        )
    if type(credential_authority) is not EnvCredentialFileAuthorityV1:
        return _result(
            "authorization_unavailable",
            "ollama_cloud_store_unavailable",
            dispatch_certainty="not_started",
        )
    try:
        inherited_lock = credential_lock.inherited_lock(binding.account_id)
    except (OSError, ValueError):
        return _result(
            "internal_adapter_error",
            "ollama_cloud_credential_lock_invalid",
            dispatch_certainty="not_started",
        )
    started = time.monotonic()
    if deadline_monotonic is not None and (
        type(deadline_monotonic) is not float
        or not math.isfinite(deadline_monotonic)
        or deadline_monotonic <= started
    ):
        return _result(
            "deadline_exceeded",
            "ollama_cloud_deadline_exceeded",
            dispatch_certainty="not_started",
        )
    deadline = min(
        started + CLOUD_BALANCE_POLICY_V1.operation_timeout_seconds,
        deadline_monotonic
        if deadline_monotonic is not None
        else started + CLOUD_BALANCE_POLICY_V1.operation_timeout_seconds,
    )
    try:
        with env_credential_file_lease_v1(credential_authority) as credential_file:
            inherited_file = credential_file.inherited_file()
            result = _run_isolated_worker(
                deadline,
                binding_id=binding.binding_id.value,
                account_id=binding.account_id,
                credential_lock=inherited_lock,
                credential_file=inherited_file,
            )
            try:
                # Reinvoke both issuers: inherited children can prove pinned FDs,
                # while these live leases additionally prove the approved paths.
                credential_lock.inherited_lock(binding.account_id)
                credential_file.inherited_file()
            except (OSError, ValueError):
                return _result(
                    "internal_adapter_error",
                    "ollama_cloud_credential_lock_invalid",
                    dispatch_certainty=result.dispatch_certainty,
                )
            return result
    except EnvCredentialFileError as error:
        return _result(
            "authorization_unavailable",
            error.code,
            dispatch_certainty="not_started",
        )


def read_cloud_balance_for_binding_v1(
    *,
    binding: ActiveCredentialBindingRefV1,
    credential_lock: AccountCredentialLockLeaseV1 | None = None,
    credential_authority: EnvCredentialFileAuthorityV1 | None = None,
    deadline_monotonic: float | None = None,
) -> CloudBalanceSourceResultV1:
    """Fail closed until the isolated authenticated source is live-validated."""
    if (
        not CLOUD_BALANCE_POLICY_V1.authenticated_collection_admitted
        or not CLOUD_BALANCE_POLICY_V1.binding_worker_authenticated_validated
    ):
        return _result(
            "source_not_admitted",
            "ollama_cloud_authenticated_source_not_admitted",
            dispatch_certainty="not_started",
        )
    return probe_cloud_balance_for_binding_v1(
        binding=binding,
        credential_lock=credential_lock,
        credential_authority=credential_authority,
        deadline_monotonic=deadline_monotonic,
    )


def read_scheduled_cloud_balance_v1(
    *,
    binding: ActiveCredentialBindingRefV1,
    proof: ScheduledSourceAdmissionProofV1,
    credential_lock: AccountCredentialLockLeaseV1 | None = None,
    credential_authority: EnvCredentialFileAuthorityV1 | None = None,
    deadline_monotonic: float | None = None,
) -> CloudBalanceSourceResultV1:
    """Read only with an exact, freshly rederived per-binding M03 proof."""
    from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
        require_matching_scheduled_proof,
    )

    try:
        require_matching_scheduled_proof(binding, proof)
    except (TypeError, ValueError):
        return _result(
            "source_not_admitted",
            "ollama_cloud_scheduled_proof_invalid",
            dispatch_certainty="not_started",
        )
    return probe_cloud_balance_for_binding_v1(
        binding=binding,
        credential_lock=credential_lock,
        credential_authority=credential_authority,
        deadline_monotonic=deadline_monotonic,
    )
