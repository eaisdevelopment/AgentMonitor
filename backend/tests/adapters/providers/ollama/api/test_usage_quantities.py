"""Pure typed quantity policy, not provider-response compatibility evidence."""

from decimal import Decimal, localcontext

import pytest


def test_optional_token_measures_remain_separate_and_exact() -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import usage_quantities

    with localcontext() as context:
        context.prec = 2
        actual = usage_quantities(
            request_count=3,
            input_tokens=123456789012345678901234567890,
            cached_input_tokens=5,
            output_tokens=7,
        )
    assert tuple((q.unit, q.amount.coefficient, q.amount.scale) for q in actual) == (
        ("requests", "3", 0),
        ("input_tokens", "123456789012345678901234567890", 0),
        ("cached_input_tokens", "5", 0),
        ("output_tokens", "7", 0),
    )


def test_missing_tokens_stay_absent_but_reported_zero_is_preserved() -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import usage_quantities

    assert tuple(q.unit for q in usage_quantities(request_count=0)) == ("requests",)
    actual = usage_quantities(request_count=1, cached_input_tokens=0)
    assert tuple((q.unit, q.amount.coefficient) for q in actual) == (
        ("requests", "1"),
        ("cached_input_tokens", "0"),
    )


@pytest.mark.parametrize(
    "field", ["request_count", "input_tokens", "cached_input_tokens", "output_tokens"]
)
@pytest.mark.parametrize("invalid", [-1, True, 1.5, "1", Decimal("1"), 10**78])
def test_invalid_or_unrepresentable_count_is_not_coerced(
    field: str, invalid: object
) -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import usage_quantities

    values = {"request_count": 1, field: invalid}
    with pytest.raises(ValueError):
        usage_quantities(**values)


def test_request_count_is_required_even_when_tokens_are_reported() -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import usage_quantities

    with pytest.raises(ValueError):
        usage_quantities(request_count=None, input_tokens=3)
