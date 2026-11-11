"""Exact M05 money arithmetic; callers establish source and report compatibility.

These pure operations never select reports, infer funds, convert currencies, or
claim provider precision. Applications retain source/input IDs when publishing
derived results. A true compatibility argument must come from checked typed
scope, period, currency, cost-basis and (for hard limits) enforcement context.
"""

from dataclasses import dataclass
from typing import ClassVar, Literal

from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactMoneyV1,
    InvalidExactQuantityV1,
)


class BudgetMoneyError(ValueError):
    """A closed arithmetic failure without monetary values in its message."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _canonical(coefficient: int, scale: int) -> CanonicalDecimalV1:
    if coefficient == 0:
        return CanonicalDecimalV1("0", 0)
    if scale < 0:
        coefficient *= 10**-scale
        scale = 0
    while scale > 0 and coefficient % 10 == 0:
        coefficient //= 10
        scale -= 1
    try:
        return CanonicalDecimalV1(str(coefficient), scale)
    except InvalidExactQuantityV1 as error:
        raise BudgetMoneyError("budget_money_overflow") from error


def _same_currency(left: ExactMoneyV1, right: ExactMoneyV1) -> None:
    if left.currency != right.currency:
        raise BudgetMoneyError("budget_money_currency_mismatch")


def _aligned(value: CanonicalDecimalV1, scale: int) -> int:
    # Every caller selects the largest input scale, so this power is integral.
    factor = int(10 ** (scale - value.scale))
    return int(value.coefficient) * factor


def sum_money(values: tuple[ExactMoneyV1, ...]) -> ExactMoneyV1:
    """Sum already selected compatible cost facts, rejecting an empty selection.

    Only the final exact result must fit CTR-COMMON-003; cancellation must not
    depend on the iteration order or the process Decimal precision.
    """
    if not values:
        raise BudgetMoneyError("budget_money_inputs_absent")
    first = values[0]
    for value in values:
        _same_currency(first, value)
    scale = max(value.amount.scale for value in values)
    total = sum(_aligned(value.amount, scale) for value in values)
    return ExactMoneyV1(_canonical(total, scale), first.currency)


def subtract_money(left: ExactMoneyV1, right: ExactMoneyV1) -> ExactMoneyV1:
    """Subtract matching currency amounts without clamping signed differences."""
    _same_currency(left, right)
    scale = max(left.amount.scale, right.amount.scale)
    difference = _aligned(left.amount, scale) - _aligned(right.amount, scale)
    return ExactMoneyV1(_canonical(difference, scale), left.currency)


def scale_decimal(value: CanonicalDecimalV1, *, exponent: int) -> CanonicalDecimalV1:
    """Multiply exactly by 10**exponent within the existing representation.

    Provider adapters may use exponent=-2 for a documented cents source; this
    function never chooses a currency exponent or changes a currency itself.
    """
    if type(exponent) is not int or not -18 <= exponent <= 18:
        raise BudgetMoneyError("budget_money_exponent_invalid")
    return _canonical(int(value.coefficient), value.scale - exponent)


def _round_half_even(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(abs(numerator), denominator)
    if remainder * 2 > denominator or (
        remainder * 2 == denominator and quotient % 2 == 1
    ):
        quotient += 1
    return -quotient if numerator < 0 else quotient


def _fixed(coefficient: int, scale: int) -> str:
    digits = str(abs(coefficient))
    sign = "-" if coefficient < 0 else ""
    if scale == 0:
        return sign + digits
    digits = digits.zfill(scale + 1)
    return sign + digits[:-scale] + "." + digits[-scale:]


def format_money(value: ExactMoneyV1) -> str:
    """Format USD half-even; other currencies retain their full exact amount.

    Nonzero sub-cent USD is explicitly marked rather than rounded to zero.
    The caller exposes the unchanged exact input alongside this display text.
    """
    coefficient, scale = int(value.amount.coefficient), value.amount.scale
    if value.currency != "USD":
        return f"{_fixed(coefficient, scale)} {value.currency}"
    if coefficient != 0 and abs(coefficient) * 100 < 10**scale:
        return "Negative <0.01 USD" if coefficient < 0 else "<0.01 USD"
    cents = _round_half_even(coefficient * 100, 10**scale)
    return f"{_fixed(cents, 2)} USD"


@dataclass(frozen=True, slots=True)
class BudgetHeadroom:
    """A signed difference to a named limit; it is never a cash balance."""

    kind: Literal["soft", "hard"]
    amount: ExactMoneyV1
    method_id: ClassVar[str] = "matching-limit-minus-spend-v1"

    def __post_init__(self) -> None:
        if self.kind not in {"soft", "hard"}:
            raise BudgetMoneyError("budget_money_limit_kind_invalid")

    @property
    def state(self) -> Literal["remaining", "at_limit", "exceeded"]:
        coefficient = int(self.amount.amount.coefficient)
        return (
            "remaining"
            if coefficient > 0
            else "exceeded"
            if coefficient < 0
            else "at_limit"
        )


def _require_boolean_compatibility(compatible: bool) -> None:
    if type(compatible) is not bool:
        raise BudgetMoneyError("budget_money_compatibility_invalid")


def budget_headroom(
    limit: ExactMoneyV1 | None,
    spend: ExactMoneyV1 | None,
    *,
    kind: Literal["soft", "hard"],
    compatible: bool,
) -> BudgetHeadroom | None:
    """Derive only matching limit headroom; missing context remains unavailable."""
    _require_boolean_compatibility(compatible)
    if kind not in {"soft", "hard"}:
        raise BudgetMoneyError("budget_money_limit_kind_invalid")
    if not compatible or limit is None or spend is None:
        return None
    if int(limit.amount.coefficient) < 0:
        raise BudgetMoneyError("budget_money_limit_invalid")
    return BudgetHeadroom(kind, subtract_money(limit, spend))


@dataclass(frozen=True, slots=True)
class MoneyPercentage:
    """Exact ratio inputs plus a declared derived percentage presentation."""

    numerator: ExactMoneyV1
    denominator: ExactMoneyV1
    method_id: ClassVar[str] = "remaining-over-limit-percent-v1"
    decimal_places: ClassVar[int] = 2
    rounding: ClassVar[str] = "half_even"

    def __post_init__(self) -> None:
        _same_currency(self.numerator, self.denominator)
        if int(self.denominator.amount.coefficient) <= 0:
            raise BudgetMoneyError("budget_money_denominator_invalid")

    @property
    def percentage_text(self) -> str:
        scale = max(self.numerator.amount.scale, self.denominator.amount.scale)
        numerator = _aligned(self.numerator.amount, scale)
        denominator = _aligned(self.denominator.amount, scale)
        # A factor of 100 converts a ratio to percent; another 100 retains
        # exactly two display places. Integer rounding avoids Decimal context.
        hundredths = _round_half_even(numerator * 10000, denominator)
        return _fixed(hundredths, self.decimal_places)

    @property
    def is_low_remaining(self) -> bool:
        """Classify the exact ratio at or below 20%, before display rounding.

        The positive denominator is validated on construction. Signed and
        over-limit inputs remain unchanged; this does not infer a provider stop.
        """
        scale = max(self.numerator.amount.scale, self.denominator.amount.scale)
        numerator = _aligned(self.numerator.amount, scale)
        denominator = _aligned(self.denominator.amount, scale)
        return numerator * 100 <= denominator * 20


def remaining_percentage(
    remaining: ExactMoneyV1 | None,
    limit: ExactMoneyV1 | None,
    *,
    compatible: bool,
) -> MoneyPercentage | None:
    """Return an unclipped percentage only with known matching positive limit."""
    _require_boolean_compatibility(compatible)
    if not compatible or remaining is None or limit is None:
        return None
    _same_currency(remaining, limit)
    if int(limit.amount.coefficient) <= 0:
        return None
    return MoneyPercentage(remaining, limit)
