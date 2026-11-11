"""M05-owned exact V1 quantity primitives with no binary floating point."""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from agentmonitor.contracts.common_v1 import TechnicalValueV1

_COEFFICIENT = re.compile(r"-?(?:0|[1-9][0-9]{0,77})\Z")
_UNIT = re.compile(r"[a-z][a-z0-9_.-]{0,63}\Z")


class InvalidExactQuantityV1(ValueError):
    """An exact quantity violates the closed CTR-COMMON-003 representation."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class CanonicalDecimalV1(TechnicalValueV1):
    """Canonical base-10 coefficient and nonnegative scale.

    The represented value is ``coefficient * 10 ** -scale``.  Trailing zeroes
    are removed while scale is positive, and negative zero is forbidden.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-003"
    OWNER: ClassVar[str] = "PLAN-FND"

    coefficient: str
    scale: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.coefficient) is not str
            or _COEFFICIENT.fullmatch(self.coefficient) is None
            or self.coefficient == "-0"
            or type(self.scale) is not int
            or not 0 <= self.scale <= 18
        ):
            raise InvalidExactQuantityV1("exact_decimal_noncanonical")
        if self.scale > 0 and self.coefficient.endswith("0"):
            raise InvalidExactQuantityV1("exact_decimal_noncanonical")

    @classmethod
    def from_decimal(cls, value: Decimal) -> "CanonicalDecimalV1":
        if type(value) is not Decimal:
            raise InvalidExactQuantityV1("exact_decimal_required")
        if not value.is_finite():
            raise InvalidExactQuantityV1("exact_decimal_finite_required")
        sign, digits, exponent = value.as_tuple()
        if not isinstance(exponent, int):
            raise InvalidExactQuantityV1("exact_decimal_finite_required")
        if exponent > 0 and exponent > 78 - len(digits):
            raise InvalidExactQuantityV1("exact_decimal_coefficient_too_large")
        coefficient = "".join(str(digit) for digit in digits) or "0"
        if exponent > 0:
            coefficient += "0" * exponent
            scale = 0
        else:
            scale = -exponent
            while scale > 0 and coefficient.endswith("0"):
                coefficient = coefficient[:-1]
                scale -= 1
            coefficient = coefficient.lstrip("0") or "0"
        if sign and coefficient != "0":
            coefficient = f"-{coefficient}"
        return cls(coefficient=coefficient, scale=scale)

    def as_decimal(self) -> Decimal:
        # String construction preserves every admitted digit regardless of the
        # caller's Decimal context; scaleb is arithmetic and may round.
        return Decimal(f"{self.coefficient}e-{self.scale}")


@dataclass(frozen=True, slots=True)
class ExactQuantityV1(TechnicalValueV1):
    """One canonical exact amount and explicit native unit."""

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-003"
    OWNER: ClassVar[str] = "PLAN-FND"

    amount: CanonicalDecimalV1
    unit: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if type(self.unit) is not str or _UNIT.fullmatch(self.unit) is None:
            raise InvalidExactQuantityV1("exact_quantity_unit_invalid")

    @classmethod
    def from_decimal(cls, value: Decimal, *, unit: str) -> "ExactQuantityV1":
        return cls(amount=CanonicalDecimalV1.from_decimal(value), unit=unit)

    def as_decimal(self) -> Decimal:
        return self.amount.as_decimal()


@dataclass(frozen=True, slots=True)
class ExactMoneyV1(TechnicalValueV1):
    """Exact money without assuming an unverified currency exponent."""

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-003"
    OWNER: ClassVar[str] = "PLAN-FND"

    amount: CanonicalDecimalV1
    currency: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.currency) is not str
            or len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isupper()
            or not self.currency.isalpha()
        ):
            raise InvalidExactQuantityV1("exact_money_currency_invalid")


@dataclass(frozen=True, slots=True)
class ExactRatioV1(TechnicalValueV1):
    """Exact closed ratio in the inclusive interval zero through one."""

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-003"
    OWNER: ClassVar[str] = "PLAN-FND"

    value: CanonicalDecimalV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not Decimal("0") <= self.value.as_decimal() <= Decimal("1"):
            raise InvalidExactQuantityV1("exact_ratio_out_of_range")
