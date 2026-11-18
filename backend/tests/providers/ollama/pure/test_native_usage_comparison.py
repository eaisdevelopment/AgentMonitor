"""Independent exact arithmetic only; constructed scalars never perform I/O."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext

import pytest

from backend.tests.live.ollama.native_usage_comparison import (
    NativeDay,
    NormalizedCost,
    compare_completed_usd,
)

START = datetime(2026, 11, 1, tzinfo=UTC)
END = START + timedelta(days=7)


def _days(value: Decimal | None) -> tuple[NativeDay, ...]:
    return tuple(
        NativeDay(
            START + timedelta(days=i), START + timedelta(days=i + 1), value, False
        )
        for i in range(7)
    ) + (NativeDay(END, END + timedelta(hours=1), Decimal("999999"), True),)


def _costs(coefficient: int, scale: int) -> tuple[NormalizedCost, ...]:
    return tuple(
        NormalizedCost(
            START + timedelta(days=i),
            START + timedelta(days=i + 1),
            coefficient,
            scale,
            "USD",
            False,
        )
        for i in range(7)
    )


def test_exact_signed_ratio_is_independent_of_decimal_context() -> None:
    with localcontext() as context:
        context.prec = 2
        assert (
            compare_completed_usd(
                _days(Decimal("-12345.000000000000123")),
                _costs(-12345000000000000123, 15),
                START,
                END,
            )
            == 7
        )


def test_partial_today_is_not_compared_or_summed() -> None:
    assert compare_completed_usd(_days(Decimal("0")), _costs(0, 0), START, END) == 7


@pytest.mark.parametrize(
    "costs", [_costs(1001, 3), _costs(1, 0)[:-1], _costs(1, 0) + _costs(1, 0)[:1]]
)
def test_mismatch_missing_and_duplicate_normalized_costs_fail(
    costs: tuple[NormalizedCost, ...],
) -> None:
    with pytest.raises(ValueError, match="native_comparison_mismatch"):
        compare_completed_usd(_days(Decimal("1")), costs, START, END)


def test_absent_money_is_not_zero_or_monetary_success() -> None:
    with pytest.raises(ValueError, match="native_comparison_money_not_reported"):
        compare_completed_usd(_days(None), (), START, END)
    with pytest.raises(ValueError, match="native_comparison_mismatch"):
        compare_completed_usd(_days(None), _costs(0, 0), START, END)


@pytest.mark.parametrize("currency,grouped", [("EUR", False), ("USD", True)])
def test_currency_and_grouping_cannot_cross_context(
    currency: str, grouped: bool
) -> None:
    costs = tuple(
        NormalizedCost(
            item.start, item.end, item.coefficient, item.scale, currency, grouped
        )
        for item in _costs(1, 0)
    )
    with pytest.raises(ValueError, match="native_comparison_mismatch"):
        compare_completed_usd(_days(Decimal("1")), costs, START, END)


def test_partial_completed_day_and_drifted_interval_fail() -> None:
    days = _days(Decimal("1"))
    with pytest.raises(ValueError, match="native_comparison_context_invalid"):
        compare_completed_usd(
            (NativeDay(days[0].start, days[0].end, days[0].usd, True),) + days[1:],
            _costs(1, 0),
            START,
            END,
        )
    with pytest.raises(ValueError, match="native_comparison_context_invalid"):
        compare_completed_usd(days, _costs(1, 0), START + timedelta(hours=1), END)


def test_native_day_missing_partial_defaults_false() -> None:
    from backend.tests.live.ollama.native_usage_comparison import project_native_day

    day = project_native_day("2026-11-01T00:00:00Z", "2026-11-02T00:00:00Z", 0)
    assert day == NativeDay(START, START + timedelta(days=1), Decimal(0), False)


@pytest.mark.parametrize("partial", [False, True])
def test_native_day_explicit_partial_is_preserved(partial: bool) -> None:
    from backend.tests.live.ollama.native_usage_comparison import project_native_day

    day = project_native_day(
        "2026-11-01T00:00:00Z", "2026-11-02T00:00:00Z", Decimal("1.25"), partial
    )
    assert day.partial is partial
    assert day.usd == Decimal("1.25")


@pytest.mark.parametrize("partial", [None, 0, 1, "", "false", [], {}])
def test_native_day_malformed_partial_is_not_coerced(partial: object) -> None:
    from backend.tests.live.ollama.native_usage_comparison import project_native_day

    with pytest.raises(ValueError, match="native_comparison_context_invalid"):
        project_native_day(
            "2026-11-01T00:00:00Z", "2026-11-02T00:00:00Z", None, partial
        )
