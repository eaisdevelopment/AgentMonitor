"""Test-only independent scalar comparison; no source parsing or I/O."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class NativeDay:
    start: datetime
    end: datetime
    usd: Decimal | None
    partial: bool


@dataclass(frozen=True)
class NormalizedCost:
    start: datetime
    end: datetime
    coefficient: int
    scale: int
    currency: str
    grouped: bool


def project_native_day(
    start: object,
    end: object,
    usd: object,
    partial: object = False,
) -> NativeDay:
    """Allowlisted pure fields; omitted partial is false, explicit flags stay strict."""
    if (
        type(start) is not str
        or type(end) is not str
        or type(partial) is not bool
        or usd is not None
        and type(usd) not in {Decimal, int}
    ):
        raise ValueError("native_comparison_context_invalid")
    assert isinstance(start, str) and isinstance(end, str) and isinstance(partial, bool)
    if usd is not None and not isinstance(usd, (Decimal, int)):
        raise ValueError("native_comparison_context_invalid")
    amount = None if usd is None else Decimal(usd)
    if amount is not None and not amount.is_finite():
        raise ValueError("native_comparison_context_invalid")
    try:
        return NativeDay(
            datetime.fromisoformat(start.replace("Z", "+00:00")),
            datetime.fromisoformat(end.replace("Z", "+00:00")),
            amount,
            partial,
        )
    except ValueError:
        raise ValueError("native_comparison_context_invalid") from None


def compare_completed_usd(
    native: tuple[NativeDay, ...],
    normalized: tuple[NormalizedCost, ...],
    start: datetime,
    end: datetime,
) -> int:
    """Compare exact ratios by day, never round, sum or infer absent costs."""
    days = (end - start).days
    if (
        days not in {7, 30}
        or end - start != timedelta(days=days)
        or start.tzinfo != UTC
        or start.hour
        or start.minute
        or start.second
        or start.microsecond
        or len(native) != days + 1
    ):
        raise ValueError("native_comparison_context_invalid")
    expected: dict[tuple[datetime, datetime], tuple[int, int]] = {}
    for index, day in enumerate(native):
        wanted_start = start + timedelta(days=index)
        if day.start != wanted_start or type(day.partial) is not bool:
            raise ValueError("native_comparison_context_invalid")
        if index == days:
            if not day.partial or not end <= day.end <= end + timedelta(days=1):
                raise ValueError("native_comparison_context_invalid")
            continue
        if day.partial or day.end != wanted_start + timedelta(days=1):
            raise ValueError("native_comparison_context_invalid")
        if day.usd is not None:
            if type(day.usd) is not Decimal or not day.usd.is_finite():
                raise ValueError("native_comparison_context_invalid")
            expected[day.start, day.end] = day.usd.as_integer_ratio()
    if len(normalized) != len(expected):
        raise ValueError("native_comparison_mismatch")
    seen: set[tuple[datetime, datetime]] = set()
    for cost in normalized:
        key = cost.start, cost.end
        if (
            key in seen
            or key not in expected
            or cost.currency != "USD"
            or cost.grouped
            or type(cost.coefficient) is not int
            or type(cost.scale) is not int
            or not 0 <= cost.scale <= 18
        ):
            raise ValueError("native_comparison_mismatch")
        numerator, denominator = expected[key]
        if cost.coefficient * denominator != numerator * 10**cost.scale:
            raise ValueError("native_comparison_mismatch")
        seen.add(key)
    if not expected:
        raise ValueError("native_comparison_money_not_reported")
    return len(expected)
