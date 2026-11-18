"""One official usage GET inside a root-supervised dedicated worker only.

Candidate mapping is documentation-derived; authenticated compatibility remains
live verification work. No balance-only grant, file reader, profile or database
is imported here. Root owns outer process lifetime and generation/scope fences.
"""

from __future__ import annotations

import http.client
import io
import json
import signal
import ssl
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import FrameType
from typing import Literal, Protocol, cast

from agentmonitor.adapters.providers.ollama.api.grouping import (
    ModelPartition,
    ModelUsage,
    UsageMetrics,
    reconcile_model_usage,
    report_money_availability,
    validate_model_selection,
)
from agentmonitor.adapters.providers.ollama.api.policy import (
    COST_BASIS,
    HOST,
    MAX_RESPONSE_BYTES,
    REQUEST_SECONDS,
    SOURCE_ID,
    OllamaUsageRequestV1,
    bounded_deadline,
    dollars_to_money,
    request_path,
    retry_after_seconds,
    usage_quantities,
    validate_response_context,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    BudgetUsageBucketV1,
)
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1

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
MoneyAvailability = Literal["available", "not_reported", "partial"]


@dataclass(frozen=True, slots=True)
class OllamaUsageResultV1:
    state: State
    reason_code: str
    report: BudgetReportInputV1 | None
    requests_made: int
    money_availability: MoneyAvailability | None = None
    http_status: int | None = None
    retry_after_seconds: int | None = None


class OllamaUsageAuthorizationSinkV1:
    """A usage-specific, single-use bearer header sink; no URL or response access."""

    __slots__ = ("__connection", "__active", "__applied")

    def __init__(self, connection: http.client.HTTPSConnection) -> None:
        self.__connection = connection
        self.__active = True
        self.__applied = False

    def put_bearer_token(self, token: bytearray) -> None:
        if type(token) is not bytearray:
            raise ValueError("ollama_usage_authorization_invalid")
        try:
            if (
                not self.__active
                or self.__applied
                or not 1 <= len(token) <= 4096
                or any(value < 0x21 or value > 0x7E for value in token)
            ):
                raise ValueError("ollama_usage_authorization_invalid")
            self.__connection.putheader("Authorization", b"Bearer " + bytes(token))
            self.__applied = True
        finally:
            token[:] = b"\0" * len(token)

    def finish(self) -> None:
        self.__active = False
        if not self.__applied:
            raise ValueError("ollama_usage_authorization_missing")

    def cancel(self) -> None:
        self.__active = False


class OllamaUsageAuthorizationV1(Protocol):
    """Separate root-issued usage purpose; existing balance grants do not satisfy it."""

    def authorize(self, sink: OllamaUsageAuthorizationSinkV1) -> None: ...


class OllamaUsageSourceV1(Protocol):
    def __call__(
        self,
        request: OllamaUsageRequestV1,
        *,
        authorization: OllamaUsageAuthorizationV1 | None,
        deadline_monotonic: float | None = None,
    ) -> OllamaUsageResultV1: ...


class _WorkerRequired(ValueError):
    pass


def _alarm(_signum: int, _frame: FrameType | None) -> None:
    raise TimeoutError("ollama_usage_deadline_exceeded")


@contextmanager
def request_deadline(deadline: float) -> Iterator[None]:
    if (
        threading.current_thread() is not threading.main_thread()
        or not hasattr(signal, "setitimer")
        or signal.getsignal(signal.SIGALRM) != signal.SIG_DFL
        or signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0)
    ):
        raise _WorkerRequired("ollama_usage_dedicated_worker_required")
    now = time.monotonic()
    remaining = bounded_deadline(now, deadline) - now
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
            raise ValueError("ollama_usage_headers_too_large")
        return line


class _Response(http.client.HTTPResponse):
    def begin(self) -> None:
        if self.headers is not None:
            return
        original = self.fp
        if original is None:
            raise ValueError("ollama_usage_headers_invalid")
        self.fp = _HeaderReader(original)
        try:
            super().begin()
        finally:
            self.fp = original


class _Connection(http.client.HTTPSConnection):
    response_class = _Response

    def __init__(self, host: str) -> None:
        if host != HOST:
            raise ValueError("ollama_usage_destination_invalid")
        # create_default_context honors SSLKEYLOGFILE. Construct verified TLS
        # directly, as the existing balance source does, without that hook.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_default_certs(ssl.Purpose.SERVER_AUTH)
        super().__init__(HOST, port=443, timeout=REQUEST_SECONDS, context=context)


class _SourceFailure(Exception):
    def __init__(
        self, state: State, status: int | None = None, retry: int | None = None
    ) -> None:
        self.state, self.status, self.retry = state, status, retry
        super().__init__("ollama_usage_" + state)


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("ollama_usage_duplicate_json_key")
        result[key] = value
    return result


def _decimal(value: str) -> Decimal:
    if len(value) > 128:
        raise ValueError("ollama_usage_number_too_large")
    return Decimal(value)


def _integer(value: str) -> int:
    if len(value) > 78:
        raise ValueError("ollama_usage_number_too_large")
    return int(value)


def _reject_constant(_value: str) -> object:
    raise ValueError("ollama_usage_nonfinite_number")


def _fetch(
    request: OllamaUsageRequestV1,
    authorization: OllamaUsageAuthorizationV1,
    deadline: float,
) -> dict[str, object]:
    connection = _Connection(HOST)
    response: http.client.HTTPResponse | None = None
    sink: OllamaUsageAuthorizationSinkV1 | None = None
    body = bytearray()
    try:
        with request_deadline(deadline):
            connection.set_debuglevel(0)
            connection.putrequest(
                "GET", request_path(request), skip_accept_encoding=True
            )
            connection.putheader("Accept", "application/json")
            sink = OllamaUsageAuthorizationSinkV1(connection)
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
                    retry_after_seconds(response.getheader("Retry-After"))
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
                raise ValueError("ollama_usage_response_encoding_invalid")
            length = response.getheader("Content-Length")
            if length is not None and (
                not length.isascii()
                or not length.isdigit()
                or len(length) > 10
                or int(length) > MAX_RESPONSE_BYTES
            ):
                raise ValueError("ollama_usage_response_too_large")
            while True:
                chunk = response.read(min(16384, MAX_RESPONSE_BYTES + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError("ollama_usage_response_too_large")
            parsed: object = json.loads(
                body,
                object_pairs_hook=_object,
                parse_float=_decimal,
                parse_int=_integer,
                parse_constant=_reject_constant,
            )
            if not isinstance(parsed, dict):
                raise ValueError("ollama_usage_response_invalid")
            return cast(dict[str, object], parsed)
    finally:
        body[:] = b"\0" * len(body)
        if sink is not None:
            sink.cancel()
        if response is not None:
            response.close()
        buffered = getattr(connection, "_buffer", None)
        if type(buffered) is list:
            buffered.clear()
        connection.set_debuglevel(0)
        connection.close()


def _timestamp(value: object) -> datetime:
    if type(value) is not str or len(value) > 40:
        raise ValueError("ollama_usage_timestamp_invalid")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.utcoffset() != timedelta(0):
        raise ValueError("ollama_usage_timestamp_invalid")
    return stamp


_METRICS = frozenset(
    {
        "request_count",
        "usage_usd",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
    }
)


def _metrics(
    value: object, *, bucket: bool
) -> tuple[tuple[ExactQuantityV1, ...], Decimal | None]:
    if not isinstance(value, dict) or not set(value) <= (
        _METRICS | {"from", "until", "partial"} if bucket else _METRICS
    ):
        raise ValueError("ollama_usage_metrics_invalid")
    quantities = usage_quantities(
        request_count=value.get("request_count"),
        input_tokens=value.get("input_tokens"),
        cached_input_tokens=value.get("cached_input_tokens"),
        output_tokens=value.get("output_tokens"),
    )
    money = value.get("usage_usd")
    if money is not None and type(money) not in {Decimal, int}:
        raise ValueError("ollama_usage_money_invalid")
    return quantities, Decimal(money) if money is not None else None


def _model_summary(value: object, *, bucket: bool) -> ModelPartition:
    allowed = (
        _METRICS
        | {"groups", "remainder"}
        | ({"from", "until", "partial"} if bucket else set())
    )
    if not isinstance(value, dict) or not set(value) <= allowed:
        raise ValueError("ollama_usage_metrics_invalid")
    rows = value.get("groups")
    if not isinstance(rows, list) or len(rows) > 10:
        raise ValueError("ollama_usage_groups_invalid")

    def metrics(raw: object) -> UsageMetrics:
        quantities, money = _metrics(raw, bucket=False)
        return UsageMetrics(
            quantities, None if money is None else dollars_to_money(money)
        )

    parent = metrics({key: item for key, item in value.items() if key in _METRICS})
    groups = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or not set(row) <= _METRICS | {"model"}
            or type(row.get("model")) is not str
        ):
            raise ValueError("ollama_usage_groups_invalid")
        groups.append(
            ModelUsage(
                BudgetDimensionV1("model", row["model"]),
                metrics({key: item for key, item in row.items() if key != "model"}),
            )
        )
    remainder = (
        None
        if "remainder" not in value
        else ModelUsage(
            BudgetDimensionV1("model", None, is_remainder=True),
            metrics(value["remainder"]),
        )
    )
    return reconcile_model_usage(parent, tuple(groups), remainder)


def _report(
    request: OllamaUsageRequestV1, payload: dict[str, object], collected_at: datetime
) -> tuple[BudgetReportInputV1, MoneyAvailability]:
    expected = {
        "range",
        "scope",
        "granularity",
        "from",
        "until",
        "totals",
        "buckets",
    }
    if request.grouping:
        expected.add("group_by")
    if set(payload) != expected:
        raise ValueError("ollama_usage_shape_invalid")
    native_end = _timestamp(payload["until"])
    validate_response_context(
        request,
        range_key=payload["range"],
        scope=payload["scope"],
        granularity=payload["granularity"],
        start=_timestamp(payload["from"]),
        end=native_end,
        grouping=payload.get("group_by"),
    )
    # Native totals include today: validate, never emit them as selected spend.
    selection: tuple[str, ...] = ()
    if request.grouping:
        total = _model_summary(payload["totals"], bucket=False)
        selection = tuple(
            component.dimension.value
            for component in total.components
            if component.dimension.value is not None
        )
    else:
        _metrics(payload["totals"], bucket=False)
    buckets = payload["buckets"]
    days = (request.period.end - request.period.start).days
    if not isinstance(buckets, list) or len(buckets) != days + 1:
        raise ValueError("ollama_usage_bucket_coverage_invalid")
    costs: list[BudgetCostBucketV1] = []
    usage: list[BudgetUsageBucketV1] = []
    money_states: list[MoneyAvailability] = []
    for index, bucket in enumerate(buckets):
        components: tuple[tuple[str, tuple[BudgetDimensionV1, ...], UsageMetrics], ...]
        if request.grouping:
            partition = _model_summary(bucket, bucket=True)
            names = tuple(
                component.dimension.value
                for component in partition.components
                if component.dimension.value is not None
            )
            validate_model_selection(selection, names)
            components = tuple(
                (
                    "remainder"
                    if component.dimension.is_remainder
                    else "model-" + str(selection.index(component.dimension.value)),
                    (component.dimension,),
                    component.metrics,
                )
                for component in partition.components
            )
            bucket_money = partition.money_availability
        else:
            quantities, money = _metrics(bucket, bucket=True)
            components = (
                (
                    "",
                    (),
                    UsageMetrics(
                        quantities, None if money is None else dollars_to_money(money)
                    ),
                ),
            )
            bucket_money = "not_reported" if money is None else "available"
        assert isinstance(bucket, dict)
        start, end = _timestamp(bucket.get("from")), _timestamp(bucket.get("until"))
        expected_start = request.period.start + timedelta(days=index)
        partial = bucket.get("partial", False)
        if type(partial) is not bool or start != expected_start:
            raise ValueError("ollama_usage_bucket_coverage_invalid")
        if index == days:
            if not partial or end != native_end or end < start:
                raise ValueError("ollama_usage_partial_bucket_invalid")
            continue
        if partial or end != start + timedelta(days=1):
            raise ValueError("ollama_usage_bucket_coverage_invalid")
        period = BudgetPeriodV1(start, end)
        key = start.date().isoformat()
        money_states.append(bucket_money)
        for component_key, dimensions, measures in components:
            suffix = key if not component_key else key + "-" + component_key
            usage.extend(
                BudgetUsageBucketV1(
                    quantity.unit + "-" + suffix, period, quantity, dimensions
                )
                for quantity in measures.quantities
            )
            if measures.money is not None:
                amount = measures.money
                costs.append(
                    BudgetCostBucketV1(
                        "cost-" + suffix,
                        period,
                        amount,
                        dimensions,
                        "adjustment"
                        if int(amount.amount.coefficient) < 0
                        else "charge",
                    )
                )
    money_state = report_money_availability(tuple(money_states), has_costs=bool(costs))
    partial_costs = money_state == "partial"
    report = BudgetReportInputV1(
        subject=request.subject,
        binding_id=request.binding.binding_id,
        binding_generation=request.binding.generation,
        scope_generation=request.scope_generation,
        scope_id=request.scope_id,
        scope_evidence=request.scope_evidence,
        source_id=SOURCE_ID,
        source_category=request.scope + "_requests_and_cost",
        cost_basis=COST_BASIS,
        grouping=request.grouping,
        requested_period=request.period,
        covered_period=request.period,
        source_data_through=None,
        collected_at=collected_at,
        completeness="partial" if partial_costs else "complete",
        omission_codes=("cost_not_reported_for_all_buckets",) if partial_costs else (),
        currency="USD" if costs else None,
        empty_means_zero=False,
        cost_buckets=tuple(costs),
        usage_buckets=tuple(usage),
    )
    return report, money_state


def collect_usage_report_in_worker_v1(
    request: OllamaUsageRequestV1,
    *,
    authorization: OllamaUsageAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
) -> OllamaUsageResultV1:
    """No retries or balance fallback; root must re-fence before report commit."""
    if authorization is None:
        return OllamaUsageResultV1(
            "authorization_unavailable",
            "ollama_usage_authorization_unavailable",
            None,
            0,
        )
    attempted = 0
    try:
        deadline = bounded_deadline(time.monotonic(), deadline_monotonic)
        with request_deadline(deadline):
            pass
        attempted = 1
        payload = _fetch(request, authorization, deadline)
        bounded_deadline(time.monotonic(), deadline)
        report, money_state = _report(request, payload, datetime.now(UTC))
        bounded_deadline(time.monotonic(), deadline)
        state: State = "partial" if report.completeness == "partial" else "success"
        return OllamaUsageResultV1(
            state,
            "ollama_usage_cost_not_reported"
            if money_state == "not_reported"
            else "ollama_usage_" + state,
            report,
            attempted,
            money_state,
            200,
        )
    except _WorkerRequired:
        state = "worker_required"
    except TimeoutError:
        state = "deadline_exceeded"
    except _SourceFailure as error:
        return OllamaUsageResultV1(
            error.state,
            "ollama_usage_" + error.state,
            None,
            attempted,
            http_status=error.status,
            retry_after_seconds=error.retry,
        )
    except (ValueError, TypeError, KeyError, RecursionError):
        state = "invalid_provider_data"
    except (OSError, http.client.HTTPException):
        state = "provider_unavailable"
    except Exception:
        state = "internal_error"
    return OllamaUsageResultV1(state, "ollama_usage_" + state, None, attempted)
