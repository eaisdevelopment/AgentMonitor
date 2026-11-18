"""Pure scalar arithmetic and context checks; no provider payloads or I/O."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext

import pytest

from backend.tests.live.billing.native_cost_comparison import (
    CostScalar,
    NormalizedCost,
    compare_cost_scalars,
    native_amount,
)

START = datetime(2026, 11, 1, tzinfo=UTC)
END = START + timedelta(days=7)
DAY = START + timedelta(days=1)


def test_anthropic_cents_are_exact_usd_not_list_cost_or_dollars() -> None:
    native = CostScalar(
        START, DAY, native_amount("anthropic", "-12345.000001"), "USD", ()
    )
    mapped = NormalizedCost(START, DAY, -12345000001, 8, "USD", ())
    with localcontext() as context:
        context.prec = 2
        assert (
            compare_cost_scalars("anthropic", (native,), (mapped,), START, END, ()) == 1
        )
    with pytest.raises(ValueError, match="native_cost_comparison_mismatch"):
        compare_cost_scalars(
            "anthropic",
            (native,),
            (NormalizedCost(START, DAY, -12345000001, 6, "USD", ()),),
            START,
            END,
            (),
        )


def test_openai_uses_declared_currency_units_without_cent_conversion() -> None:
    native = CostScalar(
        START, DAY, native_amount("openai", Decimal("1.000000000000000001")), "eur", ()
    )
    mapped = NormalizedCost(START, DAY, 1000000000000000001, 18, "EUR", ())
    with localcontext() as context:
        context.prec = 2
        assert compare_cost_scalars("openai", (native,), (mapped,), START, END, ()) == 1


@pytest.mark.parametrize(
    "provider,value",
    [
        ("anthropic", "1"),
        ("anthropic", Decimal("1.000000")),
        ("openai", 1.2),
        ("openai", True),
        ("openai", "1.2"),
        ("openai", Decimal("NaN")),
    ],
)
def test_native_numbers_reject_unadmitted_shapes(provider: str, value: object) -> None:
    with pytest.raises(ValueError, match="native_cost_comparison_fields_invalid"):
        native_amount(provider, value)


def test_null_group_identity_is_preserved_without_inventing_a_name() -> None:
    dimensions = (("project", None),)
    native = CostScalar(START, DAY, Decimal("0"), "usd", dimensions)
    mapped = NormalizedCost(START, DAY, 0, 0, "USD", dimensions)
    assert (
        compare_cost_scalars("openai", (native,), (mapped,), START, END, ("project",))
        == 1
    )
    with pytest.raises(ValueError, match="native_cost_comparison_mismatch"):
        compare_cost_scalars(
            "openai",
            (native,),
            (NormalizedCost(START, DAY, 0, 0, "USD", (("project", "unknown"),)),),
            START,
            END,
            ("project",),
        )


@pytest.mark.parametrize(
    "variant", ["missing", "duplicate", "currency", "period", "grouping"]
)
def test_cost_identity_mismatch_is_not_hidden_by_equal_total(variant: str) -> None:
    native = CostScalar(START, DAY, Decimal("1"), "usd", ())
    mapped = NormalizedCost(START, DAY, 1, 0, "USD", ())
    rows = (
        ()
        if variant == "missing"
        else (mapped, mapped)
        if variant == "duplicate"
        else (
            NormalizedCost(START, DAY, 1, 0, "EUR", ())
            if variant == "currency"
            else NormalizedCost(DAY, DAY + timedelta(days=1), 1, 0, "USD", ())
            if variant == "period"
            else NormalizedCost(START, DAY, 1, 0, "USD", (("project", None),)),
        )
    )
    with pytest.raises(ValueError, match="native_cost_comparison_mismatch"):
        compare_cost_scalars("openai", (native,), rows, START, END, ())


def test_empty_contains_no_fabricated_zero_and_duplicate_native_is_rejected() -> None:
    assert compare_cost_scalars("openai", (), (), START, END, ()) == 0
    row = CostScalar(START, DAY, Decimal("1"), "usd", ())
    mapped = NormalizedCost(START, DAY, 1, 0, "USD", ())
    with pytest.raises(ValueError, match="native_cost_comparison_mismatch"):
        compare_cost_scalars("openai", (row, row), (mapped, mapped), START, END, ())


def test_native_day_outside_captured_interval_is_rejected() -> None:
    row = CostScalar(END, END + timedelta(days=1), Decimal("1"), "usd", ())
    mapped = NormalizedCost(END, END + timedelta(days=1), 1, 0, "USD", ())
    with pytest.raises(ValueError, match="native_cost_comparison_context_invalid"):
        compare_cost_scalars("openai", (row,), (mapped,), START, END, ())


@pytest.mark.parametrize(
    "provider,currency,basis,empty_zero,complete,exhausted,state",
    [
        (
            "anthropic",
            "USD",
            "discounted_before_credits",
            True,
            True,
            True,
            "empty_complete",
        ),
        ("anthropic", "USD", "discounted_before_credits", True, False, True, "partial"),
        ("anthropic", "USD", "discounted_before_credits", True, True, False, "partial"),
        (
            "anthropic",
            None,
            "discounted_before_credits",
            True,
            True,
            True,
            "money_not_reported",
        ),
        ("anthropic", "USD", "list_price", True, True, True, "money_not_reported"),
        (
            "openai",
            None,
            "openai_reported_cost",
            False,
            True,
            True,
            "money_not_reported",
        ),
        (
            "openai",
            "USD",
            "openai_reported_cost",
            True,
            True,
            True,
            "money_not_reported",
        ),
    ],
)
def test_only_source_qualified_complete_empty_is_monetary_zero(
    provider: str,
    currency: str | None,
    basis: str,
    empty_zero: bool,
    complete: bool,
    exhausted: bool,
    state: str,
) -> None:
    from backend.tests.live.billing.native_cost_comparison import comparison_disposition

    result = comparison_disposition(
        provider,
        0,
        complete=complete,
        exhausted=exhausted,
        currency=currency,
        cost_basis=basis,
        empty_means_zero=empty_zero,
    )
    assert result[0] == state
    assert result[2] is (state == "empty_complete")


def test_partial_page_collection_cannot_be_a_numeric_comparison_pass() -> None:
    from backend.tests.live.billing.native_cost_comparison import comparison_disposition

    assert (
        comparison_disposition(
            "openai",
            3,
            complete=True,
            exhausted=False,
            currency="USD",
            cost_basis="openai_reported_cost",
            empty_means_zero=False,
        )[0]
        == "partial"
    )
