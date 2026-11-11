"""M7-MATH-14: pure exact-money regressions; no provider or I/O fixtures."""

from decimal import Decimal, Inexact, localcontext

import pytest
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1


@pytest.mark.parametrize(
    ("coefficient", "scale"),
    [
        ("12345678901234567890123456789012345678", 0),
        ("9" * 78, 18),
        ("-" + "9" * 78, 18),
        ("1", 18),
        ("0", 0),
    ],
)
def test_canonical_decimal_round_trip_preserves_all_admitted_digits(
    coefficient: str, scale: int
) -> None:
    value = CanonicalDecimalV1(coefficient=coefficient, scale=scale)
    expected = Decimal(f"{coefficient}e-{scale}")

    assert value.as_decimal() == expected
    assert CanonicalDecimalV1.from_decimal(value.as_decimal()) == value


def test_exact_conversion_does_not_depend_on_callers_decimal_context() -> None:
    value = CanonicalDecimalV1(coefficient="123456789", scale=5)
    with localcontext() as context:
        context.prec = 2
        context.traps[Inexact] = True
        assert value.as_decimal() == Decimal("1234.56789")
        assert not context.flags[Inexact]


@pytest.mark.parametrize("source", ["0.00000000", "-0.00", "0E-999999", "0E+999999"])
def test_exact_zero_canonicalizes_without_precision_or_exponent_artifacts(
    source: str,
) -> None:
    """A reported numeric zero remains zero independently of source formatting."""
    assert CanonicalDecimalV1.from_decimal(Decimal(source)) == CanonicalDecimalV1(
        "0", 0
    )
