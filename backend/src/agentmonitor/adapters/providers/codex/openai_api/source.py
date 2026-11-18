"""Official organization report GETs in the supervised billing worker only.

The composition root owns a dedicated process and hard 120-second lifetime.
Each request additionally has a hard SIGALRM bound, including DNS/TLS/header
reads. Never call this source in the dashboard process or an async worker thread.
Raw bodies and credential bytes never leave this module.
"""

from __future__ import annotations

import http.client
import io
import json
import math
import signal
import ssl
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from types import FrameType
from typing import Literal, Protocol, cast

from agentmonitor.adapters.providers.codex.openai_api.policy import (
    COST_BASIS,
    HOST,
    MAX_NORMALIZED_BYTES,
    MAX_REQUESTS,
    MAX_RESPONSE_BYTES,
    MAX_ROWS,
    REPORT_SECONDS,
    REQUEST_SECONDS,
    SOURCE_ID,
    USAGE_SOURCE_ID,
    OpenAICostRequestV1,
    OpenAIUsageRequestV1,
    bounded_deadline,
    decimal_number,
    money_from_number,
    request_path,
)
from agentmonitor.adapters.providers.codex.openai_api.usage_mapping import (
    GROUP_FIELDS,
    OpenAIUsageMeasuresV1,
    bucket_key,
    dimensions_for_grouping,
    usage_buckets,
    usage_mapping,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    BudgetUsageBucketV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)

State = Literal[
    "success",
    "partial",
    "authorization_unavailable",
    "unauthorized",
    "access_denied",
    "rate_limited",
    "provider_unavailable",
    "unexpected_response",
    "invalid_provider_data",
    "deadline_exceeded",
    "worker_required",
    "internal_error",
]


@dataclass(frozen=True, slots=True)
class OpenAICostResultV1:
    """Only normalized facts and sanitized outcome codes cross the boundary."""

    state: State
    reason_code: str
    report: BudgetReportInputV1 | None
    requests_made: int
    http_status: int | None = None
    retry_after_seconds: int | None = None


class OpenAICostSourceV1(Protocol):
    """Typed A02 callable; composition adapts its result into M03/M04 outcomes."""

    def __call__(
        self,
        request: OpenAICostRequestV1,
        *,
        authorization: OpenAICostAuthorizationV1 | None,
        deadline_monotonic: float | None = None,
    ) -> OpenAICostResultV1: ...


@dataclass(frozen=True, slots=True)
class OpenAIUsageResultV1(OpenAICostResultV1):
    """Usage-only report result; no currency or balance inference."""


class OpenAIUsageSourceV1(Protocol):
    """One captured usage category through root's existing sealed grant."""

    def __call__(
        self,
        request: OpenAIUsageRequestV1,
        *,
        authorization: OpenAICostAuthorizationV1 | None,
        deadline_monotonic: float | None = None,
    ) -> OpenAIUsageResultV1: ...


class _WorkerRequired(ValueError):
    """Dedicated-worker admission refusal; never a provider response error."""


class OpenAICostAuthorizationSinkV1:
    """One header only; no URL, connection-control or logging capability."""

    __slots__ = ("__connection", "__active", "__applied")

    def __init__(self, connection: http.client.HTTPSConnection) -> None:
        self.__connection = connection
        self.__active = True
        self.__applied = False

    def put_api_key(self, token: bytearray) -> None:
        """Consume one visible-ASCII key and clear the supplied mutable buffer."""
        if type(token) is not bytearray:
            raise ValueError("openai_cost_authorization_invalid")
        try:
            if (
                not self.__active
                or self.__applied
                or not 1 <= len(token) <= 4096
                or any(value < 0x21 or value > 0x7E for value in token)
            ):
                raise ValueError("openai_cost_authorization_invalid")
            self.__connection.putheader("Authorization", b"Bearer " + bytes(token))
            self.__applied = True
        finally:
            token[:] = b"\0" * len(token)

    def finish(self) -> None:
        self.__active = False
        if not self.__applied:
            raise ValueError("openai_cost_authorization_missing")

    def cancel(self) -> None:
        self.__active = False


class OpenAICostAuthorizationV1(Protocol):
    """Root-issued grant revalidates inherited file/account lock on every call."""

    def authorize(self, sink: OpenAICostAuthorizationSinkV1) -> None: ...


def _alarm(_signum: int, _frame: FrameType | None) -> None:
    raise TimeoutError("openai_cost_deadline_exceeded")


@contextmanager
def request_deadline(report_deadline: float) -> Iterator[None]:
    """Refuse service/thread alarm ownership; bound a dedicated worker request."""
    if (
        threading.current_thread() is not threading.main_thread()
        or not hasattr(signal, "setitimer")
        or signal.getsignal(signal.SIGALRM) != signal.SIG_DFL
        or signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0)
    ):
        raise _WorkerRequired("openai_cost_dedicated_worker_required")
    now = time.monotonic()
    remaining = bounded_deadline(now, report_deadline, REQUEST_SECONDS) - now
    previous = signal.signal(signal.SIGALRM, _alarm)
    try:
        signal.setitimer(signal.ITIMER_REAL, remaining)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class _HeaderReader(io.BufferedIOBase):
    def __init__(self, source: io.BufferedIOBase) -> None:
        super().__init__()
        self._source = source
        self._bytes = 0
        self._lines = 0

    def readline(self, size: int | None = -1, /) -> bytes:
        bound = 16385 - self._bytes
        if size is not None and size >= 0:
            bound = min(bound, size)
        line = self._source.readline(bound)
        self._bytes += len(line)
        self._lines += 1
        if self._bytes > 16384 or self._lines > 66:
            raise ValueError("openai_cost_headers_too_large")
        return line


class _Response(http.client.HTTPResponse):
    def begin(self) -> None:
        if self.headers is not None:
            return
        original = self.fp
        if original is None:
            raise ValueError("openai_cost_headers_invalid")
        self.fp = _HeaderReader(original)
        try:
            super().begin()
        finally:
            self.fp = original


class _Connection(http.client.HTTPSConnection):
    response_class = _Response

    def __init__(self, host: str) -> None:
        if host != HOST:
            raise ValueError("openai_cost_destination_invalid")
        super().__init__(
            HOST, port=443, timeout=REQUEST_SECONDS, context=_secure_tls_context()
        )


class _SourceFailure(Exception):
    def __init__(
        self, state: State, status: int | None = None, retry: int | None = None
    ) -> None:
        self.state, self.status, self.retry = state, status, retry
        super().__init__("openai_cost_" + state)


def _retry_after(value: str | None) -> int | None:
    if value is None or len(value) > 128:
        return None
    try:
        if value.isascii() and value.isdigit():
            result = int(value)
        else:
            stamp = parsedate_to_datetime(value)
            if stamp.utcoffset() is None:
                return None
            result = max(0, math.ceil((stamp - datetime.now(UTC)).total_seconds()))
        return result if result <= 2**63 - 1 else None
    except (ValueError, TypeError, OverflowError):
        return None


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("openai_cost_duplicate_json_key")
        result[key] = value
    return result


def _reject_number(_value: str) -> object:
    raise ValueError("openai_cost_unexpected_json_number")


def _integer(value: str) -> int:
    if len(value) > 79:
        raise ValueError("openai_cost_json_integer_too_large")
    return int(value)


def _secure_tls_context() -> ssl.SSLContext:
    """Verified system roots without environment-requested TLS key logging."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs(ssl.Purpose.SERVER_AUTH)
    context.keylog_filename = None  # type: ignore[assignment]
    return context


def _read_page(
    request: OpenAICostRequestV1,
    cursor: str | None,
    authorization: OpenAICostAuthorizationV1,
    deadline: float,
) -> dict[str, object]:
    connection = _Connection(HOST)
    response: http.client.HTTPResponse | None = None
    sink: OpenAICostAuthorizationSinkV1 | None = None
    try:
        with request_deadline(deadline):
            connection.set_debuglevel(0)
            connection.putrequest(
                "GET", request_path(request, cursor), skip_accept_encoding=True
            )
            connection.putheader("Accept", "application/json")
            sink = OpenAICostAuthorizationSinkV1(connection)
            try:
                authorization.authorize(sink)
                sink.finish()
            except TimeoutError:
                raise
            except Exception:
                raise _SourceFailure("authorization_unavailable") from None
            finally:
                sink.cancel()
            connection.endheaders()
            response = connection.getresponse()
            if response.status != 200:
                state: State = (
                    "unauthorized"
                    if response.status == 401
                    else "access_denied"
                    if response.status == 403
                    else "rate_limited"
                    if response.status == 429
                    else "provider_unavailable"
                    if response.status >= 500
                    else "unexpected_response"
                )
                raise _SourceFailure(
                    state,
                    response.status,
                    _retry_after(response.getheader("Retry-After"))
                    if state == "rate_limited"
                    else None,
                )
            if (
                response.getheader("Content-Encoding", "identity").lower() != "identity"
                or response.getheader("Content-Type", "")
                .split(";", 1)[0]
                .strip()
                .lower()
                != "application/json"
            ):
                raise ValueError("openai_cost_response_encoding_invalid")
            length = response.getheader("Content-Length")
            if length is not None and (
                not length.isascii()
                or not length.isdigit()
                or len(length) > 10
                or int(length) > MAX_RESPONSE_BYTES
            ):
                raise ValueError("openai_cost_response_too_large")
            body = bytearray()
            while True:
                chunk = response.read(min(16384, MAX_RESPONSE_BYTES + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError("openai_cost_response_too_large")
            try:
                parsed: object = json.loads(
                    body,
                    object_pairs_hook=_object,
                    parse_float=decimal_number,
                    parse_int=_integer,
                    parse_constant=_reject_number,
                )
            finally:
                body[:] = b"\0" * len(body)
            if not isinstance(parsed, dict):
                raise ValueError("openai_cost_response_invalid")
            return cast(dict[str, object], parsed)
    finally:
        if sink is not None:
            sink.cancel()
        if response is not None:
            response.close()
        # http.client buffers header bytes until endheaders; clear on every exit.
        buffer = getattr(connection, "_buffer", None)
        if type(buffer) is list:
            buffer.clear()
        connection.set_debuglevel(0)
        connection.close()


def _timestamp(value: object) -> datetime:
    if type(value) is not int or not 0 <= value <= 253402300799:
        raise ValueError("openai_cost_timestamp_invalid")
    return datetime.fromtimestamp(value, UTC)


_NULL_FIELDS = frozenset(
    {
        "api_key_id",
        "api_source",
        "line_item",
        "project_id",
        "user_id",
        "quantity",
        "quantity_unit",
    }
)


def _bucket_header(
    value: object, request: OpenAICostRequestV1
) -> tuple[BudgetPeriodV1, list[object]]:
    if (
        not isinstance(value, dict)
        # OpenAI documents added JSON properties as backward compatible.
        # Consume only the required bucket fields; extra metadata never enters
        # the financial report or changes its period/dimension validation.
        or not {"object", "start_time", "end_time", "results"} <= set(value)
        or value["object"] != "bucket"
    ):
        raise ValueError("openai_cost_bucket_invalid")
    period = BudgetPeriodV1(
        _timestamp(value["start_time"]), _timestamp(value["end_time"])
    )
    if (
        period.start < request.period.start
        or period.end > request.period.end
        or period.start.time() != datetime.min.time()
        or period.end - period.start != timedelta(days=1)
    ):
        raise ValueError("openai_cost_bucket_period_invalid")
    results = value["results"]
    if not isinstance(results, list) or len(results) > MAX_ROWS:
        raise ValueError("openai_report_results_invalid")
    if request.grouping in ((), ("token_category",)) and len(results) > 1:
        raise ValueError("openai_report_ungrouped_result_invalid")
    return period, results


def _dimensions(
    result: dict[str, object],
    request: OpenAICostRequestV1,
    fields: tuple[str, ...],
) -> tuple[BudgetDimensionV1, ...]:
    grouping = () if request.grouping == ("token_category",) else request.grouping
    selected = GROUP_FIELDS[grouping[0]] if grouping else None
    if any(result.get(key) is not None for key in fields if key != selected):
        raise ValueError("openai_report_unrequested_dimension")
    value = result.get(selected) if selected else None
    if value is not None and type(value) is not str:
        raise ValueError("openai_report_dimension_invalid")
    return dimensions_for_grouping(grouping, value)


def _cost_result(
    result: object,
    period: BudgetPeriodV1,
    request: OpenAICostRequestV1,
) -> BudgetCostBucketV1 | None:
    if (
        not isinstance(result, dict)
        # Additional response properties are backward compatible in OpenAI's
        # API. Only admitted money and dimension fields are consumed below;
        # extra metadata is neither attributed nor retained.
        or result.get("object") != "organization.costs.result"
    ):
        raise ValueError("openai_cost_result_invalid")
    dimensions = _dimensions(result, request, tuple(_NULL_FIELDS))
    if "amount" not in result:
        return None
    amount = result["amount"]
    if not isinstance(amount, dict) or set(amount) - {"value", "currency"}:
        raise ValueError("openai_cost_amount_invalid")
    if set(amount) != {"value", "currency"}:
        return None
    money = money_from_number(amount["value"], amount["currency"])
    return BudgetCostBucketV1(
        bucket_key=bucket_key(period, dimensions),
        period=period,
        amount=money,
        dimensions=dimensions,
        kind="adjustment" if int(money.amount.coefficient) < 0 else "charge",
    )


def _usage_result(
    result: object,
    period: BudgetPeriodV1,
    request: OpenAIUsageRequestV1,
) -> tuple[BudgetUsageBucketV1, ...]:
    mapping = usage_mapping(request.category)
    fields = mapping.required + mapping.optional
    if (
        not isinstance(result, dict)
        or result.get("object") != mapping.result_object
        or set(result) - {"object", *fields, *mapping.dimension_fields}
        or not set(mapping.required) <= set(result)
    ):
        raise ValueError("openai_usage_result_invalid")
    dimensions = _dimensions(result, request, mapping.dimension_fields)
    quantities = []
    for field in sorted(fields):
        if field not in result:
            continue
        value = result[field]
        if value is None and field in mapping.nullable:
            continue
        if type(value) is not int:
            raise ValueError("openai_usage_quantity_invalid")
        quantities.append(ExactQuantityV1(CanonicalDecimalV1(str(value), 0), field))
    measures = OpenAIUsageMeasuresV1(request.category, tuple(quantities))
    return usage_buckets(
        period,
        measures,
        dimensions,
        token_categories=request.grouping == ("token_category",),
    )


def _bucket(
    value: object,
    request: OpenAICostRequestV1,
    remaining_rows: int,
) -> tuple[BudgetPeriodV1, tuple[BudgetCostBucketV1 | BudgetUsageBucketV1, ...], bool]:
    period, results = _bucket_header(value, request)
    rows: list[BudgetCostBucketV1 | BudgetUsageBucketV1] = []
    unavailable = False
    for result in results:
        if isinstance(request, OpenAIUsageRequestV1):
            rows.extend(_usage_result(result, period, request))
        else:
            cost = _cost_result(result, period, request)
            if cost is None:
                unavailable = True
            else:
                rows.append(cost)
        if len(rows) > remaining_rows:
            raise ValueError("openai_report_rows_exceeded")
    return period, tuple(rows), unavailable


def _report(
    request: OpenAICostRequestV1,
    rows: Sequence[BudgetCostBucketV1 | BudgetUsageBucketV1],
    periods: set[datetime],
    omissions: set[str],
    *,
    collected_at: datetime,
) -> BudgetReportInputV1:
    omissions = set(omissions)
    # An explicit exhausted empty report carries coverage, not assumed currency
    # or monetary zero. Missing days in a nonempty report are not interpolated.
    if periods and len(periods) != (request.period.end - request.period.start).days:
        omissions.add("daily_coverage_incomplete")
    usage = isinstance(request, OpenAIUsageRequestV1)
    expected_type = BudgetUsageBucketV1 if usage else BudgetCostBucketV1
    if any(not isinstance(row, expected_type) for row in rows):
        raise ValueError("openai_report_row_category_invalid")
    currencies = {
        row.amount.currency for row in rows if isinstance(row, BudgetCostBucketV1)
    }
    if len(currencies) > 1:
        raise ValueError("openai_cost_currency_mixed")
    complete = not omissions
    return BudgetReportInputV1(
        subject=request.subject,
        binding_id=request.binding.binding_id,
        binding_generation=request.binding.generation,
        scope_generation=request.scope_generation,
        scope_id=request.scope_id,
        scope_evidence=request.scope_evidence,
        source_id=USAGE_SOURCE_ID if usage else SOURCE_ID,
        source_category=(
            "usage_"
            + request.category
            + ("_tokens" if request.grouping == ("token_category",) else "")
        )
        if isinstance(request, OpenAIUsageRequestV1)
        else "cost",
        cost_basis="not_applicable" if usage else COST_BASIS,
        grouping=request.grouping,
        requested_period=request.period,
        covered_period=request.period if complete else None,
        source_data_through=None,
        collected_at=collected_at,
        completeness="complete" if complete else "partial",
        omission_codes=tuple(sorted(omissions)),
        currency=next(iter(currencies)) if currencies else None,
        empty_means_zero=False,
        cost_buckets=tuple(row for row in rows if isinstance(row, BudgetCostBucketV1)),
        usage_buckets=tuple(
            row for row in rows if isinstance(row, BudgetUsageBucketV1)
        ),
    )


def _collect_report(
    request: OpenAICostRequestV1,
    *,
    authorization: OpenAICostAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
) -> OpenAICostResultV1:
    """Collect one report; root must fence binding/scope again before commit.

    Only root's dedicated supervised worker may call this candidate. It does not
    self-admit scheduling or claim that any credential has been live verified.
    No automatic retries, redirects, provider writes or environment lookups.
    """
    prefix = (
        "openai_usage_" if isinstance(request, OpenAIUsageRequestV1) else "openai_cost_"
    )
    if authorization is None:
        return OpenAICostResultV1(
            "authorization_unavailable",
            prefix + "authorization_unavailable",
            None,
            0,
        )
    started = time.monotonic()
    rows: list[BudgetCostBucketV1 | BudgetUsageBucketV1] = []
    row_keys: set[str] = set()
    seen: set[datetime] = set()
    omissions: set[str] = set()
    cursors: set[str] = set()
    cursor: str | None = None
    normalized_bytes = 0
    requests = 0
    try:
        deadline = bounded_deadline(started, deadline_monotonic, REPORT_SECONDS)
        # Validate worker ownership before any authorization callback or dispatch.
        with request_deadline(deadline):
            pass
        for _page_index in range(MAX_REQUESTS):
            requests += 1
            page = _read_page(request, cursor, authorization, deadline)
            if (
                set(page) != {"object", "data", "has_more", "next_page"}
                or page["object"] != "page"
            ):
                raise ValueError("openai_cost_page_invalid")
            data = page["data"]
            if (
                not isinstance(data, list)
                or len(seen) + len(data) > MAX_ROWS
                or type(page["has_more"]) is not bool
            ):
                raise ValueError("openai_cost_page_limits_invalid")
            for value in data:
                period, batch, unavailable = _bucket(
                    value, request, MAX_ROWS - len(rows)
                )
                if period.start in seen:
                    raise ValueError("openai_cost_duplicate_bucket")
                normalized_bytes += 512
                if normalized_bytes > MAX_NORMALIZED_BYTES:
                    raise ValueError("openai_cost_normalized_too_large")
                seen.add(period.start)
                for row in batch:
                    if row.bucket_key in row_keys:
                        raise ValueError("openai_report_duplicate_row")
                    normalized_bytes += 1024
                    if len(rows) >= MAX_ROWS or normalized_bytes > MAX_NORMALIZED_BYTES:
                        raise ValueError("openai_report_normalized_too_large")
                    row_keys.add(row.bucket_key)
                    rows.append(row)
                if unavailable:
                    omissions.add("monetary_fields_unavailable")
            next_page = page["next_page"]
            if page["has_more"]:
                if type(next_page) is not str or next_page in cursors:
                    raise ValueError("openai_cost_pagination_invalid")
                request_path(request, next_page)
                cursors.add(next_page)
                cursor = next_page
            else:
                if next_page is not None:
                    raise ValueError("openai_cost_pagination_invalid")
                bounded_deadline(time.monotonic(), deadline, REPORT_SECONDS)
                report = _report(
                    request, rows, seen, omissions, collected_at=datetime.now(UTC)
                )
                bounded_deadline(time.monotonic(), deadline, REPORT_SECONDS)
                state: State = (
                    "success" if report.completeness == "complete" else "partial"
                )
                return OpenAICostResultV1(
                    state,
                    "openai_cost_monetary_unavailable"
                    if not rows and not isinstance(request, OpenAIUsageRequestV1)
                    else prefix + state,
                    report,
                    requests,
                    200,
                )
            if time.monotonic() >= deadline:
                raise TimeoutError
        bounded_deadline(time.monotonic(), deadline, REPORT_SECONDS)
        omissions.add("page_budget_exceeded")
        report = _report(request, rows, seen, omissions, collected_at=datetime.now(UTC))
        bounded_deadline(time.monotonic(), deadline, REPORT_SECONDS)
        return OpenAICostResultV1(
            "partial", prefix + "page_budget_exceeded", report, requests, 200
        )
    except _SourceFailure as failure:
        return OpenAICostResultV1(
            failure.state,
            prefix + failure.state,
            None,
            requests,
            failure.status,
            failure.retry,
        )
    except TimeoutError:
        return OpenAICostResultV1(
            "deadline_exceeded", prefix + "deadline_exceeded", None, requests
        )
    except (ssl.SSLError, OSError, http.client.HTTPException):
        return OpenAICostResultV1(
            "provider_unavailable",
            prefix + "transport_unavailable",
            None,
            requests,
        )
    except _WorkerRequired:
        return OpenAICostResultV1(
            "worker_required",
            prefix + "dedicated_worker_required",
            None,
            requests,
        )
    except (ValueError, RecursionError):
        return OpenAICostResultV1(
            "invalid_provider_data", prefix + "data_invalid", None, requests
        )
    except Exception:
        return OpenAICostResultV1(
            "internal_error", prefix + "internal_error", None, requests
        )


def collect_cost_report_in_worker_v1(
    request: OpenAICostRequestV1,
    *,
    authorization: OpenAICostAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
) -> OpenAICostResultV1:
    """Existing cost port; defaults preserve ungrouped report identity."""
    if type(request) is not OpenAICostRequestV1:
        raise ValueError("openai_cost_request_required")
    return _collect_report(
        request, authorization=authorization, deadline_monotonic=deadline_monotonic
    )


def collect_usage_report_in_worker_v1(
    request: OpenAIUsageRequestV1,
    *,
    authorization: OpenAICostAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
) -> OpenAIUsageResultV1:
    """One finite native usage category; never invokes inference or pricing."""
    if type(request) is not OpenAIUsageRequestV1:
        raise ValueError("openai_usage_request_required")
    result = _collect_report(
        request, authorization=authorization, deadline_monotonic=deadline_monotonic
    )
    return OpenAIUsageResultV1(
        result.state,
        result.reason_code,
        result.report,
        result.requests_made,
        result.http_status,
        result.retry_after_seconds,
    )
