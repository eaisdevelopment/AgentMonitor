"""Independent pure native-cost oracle; no provider parser/converter or I/O.

Admitted source units: Anthropic cost.amount is decimal USD cents; OpenAI
amount.value is decimal units of amount.currency. Neither is a cash balance.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

Dimensions = tuple[tuple[str, str | None], ...]


@dataclass(frozen=True)
class CostScalar:
    start: datetime
    end: datetime
    amount: Decimal
    currency: str
    dimensions: Dimensions


@dataclass(frozen=True)
class NormalizedCost:
    start: datetime
    end: datetime
    coefficient: int
    scale: int
    currency: str
    dimensions: Dimensions


def native_amount(provider: str, value: object) -> Decimal:
    """Validate allowlisted scalar types without a production money converter."""
    if provider == "anthropic":
        if (
            type(value) is not str
            or re.fullmatch(r"-?(?:0|[1-9][0-9]{0,69})\.[0-9]{6}", value) is None
        ):
            raise ValueError("native_cost_comparison_fields_invalid")
        amount = Decimal(value)
    elif provider == "openai" and type(value) in {Decimal, int}:
        assert isinstance(value, (Decimal, int))
        amount = Decimal(value)
    else:
        raise ValueError("native_cost_comparison_fields_invalid")
    if (
        not amount.is_finite()
        or len(amount.as_tuple().digits) > 78
        or abs(int(amount.as_tuple().exponent)) > 1000
    ):
        raise ValueError("native_cost_comparison_fields_invalid")
    return amount


def compare_cost_scalars(
    provider: str,
    native: tuple[CostScalar, ...],
    normalized: tuple[NormalizedCost, ...],
    start: datetime,
    end: datetime,
    grouping: tuple[str, ...],
) -> int:
    """Exact one-to-one row comparison; missing/empty never manufactures zero."""
    if (
        provider not in {"anthropic", "openai"}
        or end - start not in {timedelta(days=7), timedelta(days=30)}
        or any(
            stamp.utcoffset() != timedelta(0) or stamp.time() != datetime.min.time()
            for stamp in (start, end)
        )
        or len(native) > 10000
    ):
        raise ValueError("native_cost_comparison_context_invalid")
    expected: dict[tuple[datetime, datetime, Dimensions], tuple[int, int, str]] = {}
    for item in native:
        if (
            item.start < start
            or item.end > end
            or item.start.utcoffset() != timedelta(0)
            or item.start.time() != datetime.min.time()
            or item.end - item.start != timedelta(days=1)
        ):
            raise ValueError("native_cost_comparison_context_invalid")
        key = item.start, item.end, item.dimensions
        if key in expected or tuple(kind for kind, _ in item.dimensions) != grouping:
            raise ValueError("native_cost_comparison_mismatch")
        if (
            re.fullmatch("[A-Za-z]{3}", item.currency) is None
            or provider == "anthropic"
            and item.currency != "USD"
            or not item.amount.is_finite()
        ):
            raise ValueError("native_cost_comparison_fields_invalid")
        numerator, denominator = item.amount.as_integer_ratio()
        expected[key] = (
            numerator,
            denominator * (100 if provider == "anthropic" else 1),
            item.currency.upper(),
        )
    if len(normalized) != len(expected):
        raise ValueError("native_cost_comparison_mismatch")
    seen = set()
    for mapped in normalized:
        key = mapped.start, mapped.end, mapped.dimensions
        if (
            key in seen
            or key not in expected
            or type(mapped.coefficient) is not int
            or type(mapped.scale) is not int
            or not 0 <= mapped.scale <= 18
        ):
            raise ValueError("native_cost_comparison_mismatch")
        numerator, denominator, currency = expected[key]
        if (
            mapped.currency != currency
            or mapped.coefficient * denominator != numerator * 10**mapped.scale
        ):
            raise ValueError("native_cost_comparison_mismatch")
        seen.add(key)
    return len(expected)


def comparison_disposition(
    provider: str,
    compared_rows: int,
    *,
    complete: bool,
    exhausted: bool,
    currency: str | None,
    cost_basis: str,
    empty_means_zero: bool,
) -> tuple[str, str | None, bool]:
    """An exhausted empty response is not automatically monetary zero."""
    if not complete or not exhausted:
        return "partial", "native_cost_incomplete_coverage", False
    if compared_rows:
        return "matched", None, False
    qualified = (
        provider == "anthropic"
        and currency == "USD"
        and cost_basis == "discounted_before_credits"
        and empty_means_zero
    )
    if qualified:
        return "empty_complete", None, True
    return "money_not_reported", "native_cost_money_not_reported", False
