"""M7 exact monetary policy; constructed values stay in these pure tests."""

from decimal import Decimal, localcontext

import pytest

from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.modules.capacity.domain import budget_money as policy


def _money(value: str, currency: str = "USD") -> ExactMoneyV1:
    return ExactMoneyV1(CanonicalDecimalV1.from_decimal(Decimal(value)), currency)


def test_required_money_operations_are_published() -> None:
    for name in (
        "sum_money",
        "subtract_money",
        "scale_decimal",
        "format_money",
        "budget_headroom",
        "remaining_percentage",
    ):
        assert callable(getattr(policy, name, None)), f"M05 missing {name} operation"


def test_exact_sum_and_signed_adjustment_do_not_use_binary_float() -> None:
    assert policy.sum_money((_money("0.10"), _money("0.20"))) == _money("0.30")
    assert policy.sum_money((_money("10"), _money("-2"))) == _money("8")
    assert policy.subtract_money(_money("100"), _money("110")) == _money("-10")
    assert policy.subtract_money(_money("1.01"), _money("0.009")) == _money("1.001")


def test_exact_78_digit_sum_cancellation_and_display_ignore_decimal_context() -> None:
    largest = "9" * 78
    with localcontext() as context:
        context.prec = 2
        assert policy.sum_money((_money(largest), _money("1"), _money("-1"))) == _money(
            largest
        )
        assert policy.sum_money((_money(largest), _money("-" + largest))) == _money("0")
        assert policy.subtract_money(_money(largest), _money("1")) == _money(
            "9" * 77 + "8"
        )
        assert policy.format_money(_money(largest)) == largest + ".00 USD"


@pytest.mark.parametrize("operation", ["sum", "subtract"])
def test_final_arithmetic_overflow_is_explicit(operation: str) -> None:
    with pytest.raises(policy.BudgetMoneyError, match="budget_money_overflow"):
        if operation == "sum":
            policy.sum_money((_money("9" * 78), _money("1")))
        else:
            policy.subtract_money(_money("-" + "9" * 78), _money("1"))


def test_scale_alignment_can_overflow_even_if_each_operand_fits() -> None:
    with pytest.raises(policy.BudgetMoneyError, match="budget_money_overflow"):
        policy.sum_money((_money("9" * 78), _money("0.1")))


def test_no_values_does_not_invent_a_zero_spend() -> None:
    with pytest.raises(policy.BudgetMoneyError, match="budget_money_inputs_absent"):
        policy.sum_money(())


@pytest.mark.parametrize("operation", ["sum", "subtract", "headroom", "percentage"])
def test_mixed_currencies_are_rejected(operation: str) -> None:
    dollars, pounds = _money("10"), _money("2", "GBP")
    with pytest.raises(policy.BudgetMoneyError, match="budget_money_currency_mismatch"):
        if operation == "sum":
            policy.sum_money((dollars, pounds))
        elif operation == "subtract":
            policy.subtract_money(dollars, pounds)
        elif operation == "headroom":
            policy.budget_headroom(dollars, pounds, kind="hard", compatible=True)
        else:
            policy.remaining_percentage(dollars, pounds, compatible=True)


def test_documented_cents_conversion_is_exact_and_context_independent() -> None:
    with localcontext() as context:
        context.prec = 2
        assert policy.scale_decimal(
            CanonicalDecimalV1("123456789", 6), exponent=-2
        ) == CanonicalDecimalV1("123456789", 8)
        assert policy.scale_decimal(CanonicalDecimalV1("1200", 0), exponent=-2) == (
            CanonicalDecimalV1("12", 0)
        )
        assert policy.scale_decimal(CanonicalDecimalV1("-123", 2), exponent=2) == (
            CanonicalDecimalV1("-123", 0)
        )
        assert policy.scale_decimal(CanonicalDecimalV1("0", 0), exponent=-18) == (
            CanonicalDecimalV1("0", 0)
        )


@pytest.mark.parametrize("exponent", [True, 1.0, -19, 19])
def test_scaling_rejects_unbounded_or_noninteger_exponents(exponent: object) -> None:
    with pytest.raises(policy.BudgetMoneyError, match="budget_money_exponent_invalid"):
        policy.scale_decimal(CanonicalDecimalV1("1", 0), exponent=exponent)


def test_scaling_never_rounds_out_of_contract_precision() -> None:
    with pytest.raises(policy.BudgetMoneyError, match="budget_money_overflow"):
        policy.scale_decimal(CanonicalDecimalV1("1", 18), exponent=-1)
    with pytest.raises(policy.BudgetMoneyError, match="budget_money_overflow"):
        policy.scale_decimal(CanonicalDecimalV1("9" * 78, 0), exponent=1)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("0", "0.00 USD"),
        ("0.004", "<0.01 USD"),
        ("0.009", "<0.01 USD"),
        ("-0.004", "Negative <0.01 USD"),
        ("0.01", "0.01 USD"),
        ("1.225", "1.22 USD"),
        ("1.235", "1.24 USD"),
        ("-1.225", "-1.22 USD"),
        ("-1.235", "-1.24 USD"),
        ("9.999", "10.00 USD"),
    ],
)
def test_usd_display_rounds_half_even_without_hiding_nonzero(
    amount: str, expected: str
) -> None:
    assert policy.format_money(_money(amount)) == expected


def test_other_currencies_keep_exact_decimal_without_guessing_exponent() -> None:
    assert policy.format_money(_money("0.000000000000000001", "JPY")) == (
        "0.000000000000000001 JPY"
    )
    assert policy.format_money(_money("-12.345", "GBP")) == "-12.345 GBP"


@pytest.mark.parametrize("kind", ["soft", "hard"])
def test_headroom_retains_limit_kind_and_exceeded_amount(kind: str) -> None:
    headroom = policy.budget_headroom(
        _money("100"), _money("110"), kind=kind, compatible=True
    )
    assert headroom.kind == kind
    assert headroom.amount == _money("-10")
    assert headroom.state == "exceeded"
    assert headroom.method_id == "matching-limit-minus-spend-v1"
    assert not hasattr(headroom, "cash_balance")
    assert (
        policy.budget_headroom(
            _money("100"), _money("20"), kind=kind, compatible=True
        ).state
        == "remaining"
    )
    assert (
        policy.budget_headroom(
            _money("100"), _money("100"), kind=kind, compatible=True
        ).state
        == "at_limit"
    )


def test_soft_headroom_never_implies_cash_and_missing_inputs_stay_absent() -> None:
    result = policy.budget_headroom(
        _money("100"), _money("20"), kind="soft", compatible=True
    )
    assert result.amount == _money("80")
    assert result.kind == "soft"
    for limit, spend, compatible in (
        (None, _money("20"), True),
        (_money("100"), None, True),
        (_money("100"), _money("20"), False),
    ):
        assert (
            policy.budget_headroom(limit, spend, kind="hard", compatible=compatible)
            is None
        )


def test_negative_limit_or_unknown_limit_kind_cannot_create_headroom() -> None:
    with pytest.raises(policy.BudgetMoneyError, match="budget_money_limit_invalid"):
        policy.budget_headroom(_money("-1"), _money("0"), kind="hard", compatible=True)
    with pytest.raises(
        policy.BudgetMoneyError, match="budget_money_limit_kind_invalid"
    ):
        policy.budget_headroom(_money("1"), _money("0"), kind="cash", compatible=True)


def test_ratio_preserves_exact_inputs_and_declares_rounding() -> None:
    with localcontext() as context:
        context.prec = 2
        result = policy.remaining_percentage(_money("1"), _money("3"), compatible=True)
    assert result.numerator == _money("1")
    assert result.denominator == _money("3")
    assert result.percentage_text == "33.33"
    assert result.decimal_places == 2
    assert result.rounding == "half_even"
    assert result.method_id == "remaining-over-limit-percent-v1"


@pytest.mark.parametrize(
    ("remaining", "limit", "expected"),
    [
        ("120", "100", "120.00"),
        ("-10", "100", "-10.00"),
        ("0", "100", "0.00"),
        ("1", "32", "3.12"),
        ("3", "32", "9.38"),
    ],
)
def test_percentages_are_not_clipped_and_ties_are_half_even(
    remaining: str, limit: str, expected: str
) -> None:
    result = policy.remaining_percentage(
        _money(remaining), _money(limit), compatible=True
    )
    assert result.percentage_text == expected


@pytest.mark.parametrize("limit", [None, "0", "-1"])
def test_missing_or_nonpositive_denominator_has_no_percentage(
    limit: str | None,
) -> None:
    assert (
        policy.remaining_percentage(
            _money("1"), _money(limit) if limit is not None else None, compatible=True
        )
        is None
    )


def test_unknown_remaining_and_incompatible_basis_have_no_percentage() -> None:
    assert policy.remaining_percentage(None, _money("100"), compatible=True) is None
    assert (
        policy.remaining_percentage(_money("20"), _money("100"), compatible=False)
        is None
    )


@pytest.mark.parametrize("operation", ["headroom", "percentage"])
def test_compatibility_requires_an_actual_boolean(operation: str) -> None:
    with pytest.raises(
        policy.BudgetMoneyError, match="budget_money_compatibility_invalid"
    ):
        if operation == "headroom":
            policy.budget_headroom(_money("10"), _money("2"), kind="hard", compatible=1)
        else:
            policy.remaining_percentage(_money("2"), _money("10"), compatible=1)
