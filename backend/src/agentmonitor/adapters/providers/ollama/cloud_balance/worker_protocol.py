"""Bounded secret-free protocol from the isolated cloud worker to its parent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, cast

from agentmonitor.contracts.providers.ollama.cloud_balance.v1.schema import (
    IncludedCreditsV1,
    LegacyLimitsV1,
    LegacyWindowV1,
    OllamaCloudBalanceV1,
    SourcePeriodV1,
)

MAX_WORKER_RESULT_BYTES = 4096
_STATES = frozenset(
    {
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
    }
)
_RETRY_STATES = frozenset(
    {"not_applicable", "absent", "invalid", "available", "unrepresentable"}
)
_MAX_RETRY_AFTER_SECONDS = 2**63 - 1

WorkerRetryState = Literal[
    "not_applicable", "absent", "invalid", "available", "unrepresentable"
]


@dataclass(frozen=True, slots=True)
class WorkerResultV1:
    state: str
    observed_at: datetime
    http_status: int | None
    balance: OllamaCloudBalanceV1 | None
    retry_after_seconds: int | None
    retry_after_state: WorkerRetryState


def _time(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is not UTC:
        raise ValueError("ollama_cloud_worker_timestamp_invalid")
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _balance_fields(balance: OllamaCloudBalanceV1 | None) -> list[object] | None:
    if balance is None:
        return None
    included = balance.included
    if isinstance(included, IncludedCreditsV1):
        period = included.period
        fields: list[object] = [
            "credits",
            _decimal(included.balance_usd),
            _decimal(included.allowance_usd),
            _time(period.start) if period is not None else None,
            _time(period.end) if period is not None else None,
            _decimal(balance.purchased_usd),
        ]
    elif isinstance(included, LegacyLimitsV1):

        def window(value: LegacyWindowV1 | None) -> list[object] | None:
            if value is None:
                return None
            return [_decimal(value.remaining_percent), _time(value.resets_at)]

        fields = [
            "legacy",
            window(included.session),
            window(included.weekly),
            _decimal(balance.purchased_usd),
        ]
    elif included is None:
        fields = ["none", _decimal(balance.purchased_usd)]
    else:
        raise ValueError("ollama_cloud_worker_balance_invalid")
    return fields


def encode_worker_result_v1(
    *,
    state: str,
    observed_at: datetime,
    http_status: int | None,
    balance: OllamaCloudBalanceV1 | None,
    retry_after_seconds: int | None,
    retry_after_state: str,
) -> bytes:
    """Encode only validated typed fields, never raw provider or secret bytes."""
    if (
        state not in _STATES
        or retry_after_state not in _RETRY_STATES
        or (state == "success") != (balance is not None)
    ):
        raise ValueError("ollama_cloud_worker_result_invalid")
    payload = json.dumps(
        [
            state,
            _time(observed_at),
            http_status,
            retry_after_seconds,
            retry_after_state,
            _balance_fields(balance),
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    if not 0 < len(payload) <= MAX_WORKER_RESULT_BYTES:
        raise ValueError("ollama_cloud_worker_result_invalid")
    return payload


def _parsed_time(value: object) -> datetime | None:
    if value is None:
        return None
    if type(value) is not str or not 20 <= len(value) <= 27 or not value.endswith("Z"):
        raise ValueError("ollama_cloud_worker_timestamp_invalid")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is not UTC:
        raise ValueError("ollama_cloud_worker_timestamp_invalid")
    return parsed


def _parsed_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not str or not 1 <= len(value) <= 64 or not value.isascii():
        raise ValueError("ollama_cloud_worker_number_invalid")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("ollama_cloud_worker_number_invalid")
    return result


def _parsed_window(value: object) -> LegacyWindowV1 | None:
    if value is None:
        return None
    if type(value) is not list or len(value) != 2:
        raise ValueError("ollama_cloud_worker_balance_invalid")
    return LegacyWindowV1(_parsed_decimal(value[0]), _parsed_time(value[1]))


def _parsed_balance(value: object) -> OllamaCloudBalanceV1 | None:
    if value is None:
        return None
    if type(value) is not list or not value or type(value[0]) is not str:
        raise ValueError("ollama_cloud_worker_balance_invalid")
    if value[0] == "credits" and len(value) == 6:
        start = _parsed_time(value[3])
        end = _parsed_time(value[4])
        included: IncludedCreditsV1 | LegacyLimitsV1 | None = IncludedCreditsV1(
            _parsed_decimal(value[1]),
            _parsed_decimal(value[2]),
            SourcePeriodV1(start, end)
            if start is not None or end is not None
            else None,
        )
        purchased = _parsed_decimal(value[5])
    elif value[0] == "legacy" and len(value) == 4:
        included = LegacyLimitsV1(_parsed_window(value[1]), _parsed_window(value[2]))
        purchased = _parsed_decimal(value[3])
    elif value[0] == "none" and len(value) == 2:
        included = None
        purchased = _parsed_decimal(value[1])
    else:
        raise ValueError("ollama_cloud_worker_balance_invalid")
    return OllamaCloudBalanceV1(included, purchased)


def decode_worker_result_v1(payload: bytes) -> WorkerResultV1:
    """Revalidate the child record and discard every malformed shape."""
    try:
        if (
            type(payload) is not bytes
            or not 0 < len(payload) <= MAX_WORKER_RESULT_BYTES
        ):
            raise ValueError("ollama_cloud_worker_result_invalid")
        fields = json.loads(payload.decode("ascii", errors="strict"))
        if type(fields) is not list or len(fields) != 6:
            raise ValueError("ollama_cloud_worker_result_invalid")
        state, observed_at, status, retry_after, retry_state, balance = fields
        if (
            type(state) is not str
            or state not in _STATES
            or (
                status is not None
                and (type(status) is not int or not 100 <= status <= 599)
            )
            or (
                retry_after is not None
                and (
                    type(retry_after) is not int
                    or not 0 <= retry_after <= _MAX_RETRY_AFTER_SECONDS
                )
            )
            or type(retry_state) is not str
            or retry_state not in _RETRY_STATES
        ):
            raise ValueError("ollama_cloud_worker_result_invalid")
        parsed_balance = _parsed_balance(balance)
        if (state == "success") != (parsed_balance is not None):
            raise ValueError("ollama_cloud_worker_result_invalid")
        parsed_observed_at = _parsed_time(observed_at)
        if parsed_observed_at is None:
            raise ValueError("ollama_cloud_worker_timestamp_invalid")
        return WorkerResultV1(
            state=state,
            observed_at=parsed_observed_at,
            http_status=status,
            balance=parsed_balance,
            retry_after_seconds=retry_after,
            retry_after_state=cast(WorkerRetryState, retry_state),
        )
    except (
        InvalidOperation,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        raise ValueError("ollama_cloud_worker_result_invalid") from None
