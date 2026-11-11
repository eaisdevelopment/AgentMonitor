"""Pure AgentMonitor request/admission policy; no provider response fixtures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext

import pytest

from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    AnthropicCostRequestV1,
    bounded_deadline,
    cents_to_usd,
    completed_week,
    request_path,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, CapacitySubjectV2
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    ProviderTargetRefV1,
)


def request() -> AnthropicCostRequestV1:
    instant = datetime(2026, 11, 11, 16, 38, tzinfo=UTC)
    return AnthropicCostRequestV1(
        subject=CapacitySubjectV2(
            "claude",
            ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32)),
            OpaqueIdV1("pure-account"),
            OpaqueIdV1("pure-resource"),
        ),
        binding=ActiveCredentialBindingRefV1(
            OpaqueIdV1("pure-account"), OpaqueIdV1("amcb_" + "b" * 32), 1
        ),
        scope_id=None,
        scope_evidence="unresolved",
        scope_generation=1,
        period=completed_week(instant),
        requested_at=instant,
    )


def test_reporting_range_excludes_today_and_crosses_month_boundary() -> None:
    instant = datetime(2026, 11, 2, 23, 45, tzinfo=UTC)
    assert completed_week(instant) == BudgetPeriodV1(
        datetime(2026, 10, 26, tzinfo=UTC), datetime(2026, 11, 2, tzinfo=UTC)
    )


@pytest.mark.parametrize(
    "change",
    ["provider", "binding_account", "scope", "generation", "range", "current_day"],
)
def test_request_rejects_wrong_authority_or_unadmitted_coverage(change: str) -> None:
    value = request()
    with pytest.raises(ValueError):
        if change == "provider":
            replace(value, subject=replace(value.subject, provider_key="ollama"))
        elif change == "binding_account":
            replace(
                value, binding=replace(value.binding, account_id=OpaqueIdV1("other"))
            )
        elif change == "scope":
            replace(value, scope_evidence="provider_verified")
        elif change == "generation":
            replace(value, scope_generation=0)
        elif change == "range":
            replace(
                value,
                period=BudgetPeriodV1(
                    value.period.start - timedelta(days=1), value.period.end
                ),
            )
        else:
            replace(
                value, period=BudgetPeriodV1(value.period.start, value.requested_at)
            )


@pytest.mark.parametrize(
    "instant", [datetime(2026, 11, 11), datetime(2026, 1, 5, tzinfo=UTC)]
)
def test_range_rejects_naive_clock_or_undocumented_history(instant: datetime) -> None:
    with pytest.raises(ValueError):
        completed_week(instant)


def test_query_keeps_opaque_cursor_inside_one_fixed_path() -> None:
    path = request_path(request(), "opaque/+?=&cursor")
    assert path.startswith("/v1/organizations/analytics/cost?")
    assert "time_bucket_width=1d" in path
    assert "page=opaque%2F%2B%3F%3D%26cursor" in path
    assert "group_by" not in path


@pytest.mark.parametrize("cursor", ["", "a\r\nb", "x" * 1025])
def test_query_rejects_invalid_cursor(cursor: str) -> None:
    with pytest.raises(ValueError):
        request_path(request(), cursor)


@pytest.mark.parametrize(
    ("cents", "dollars"),
    [
        ("123.450000", "1.2345"),
        ("0.000001", "0.00000001"),
        ("-1.000000", "-0.01"),
        ("0.000000", "0"),
    ],
)
def test_money_unit_conversion_is_exact(cents: str, dollars: str) -> None:
    assert cents_to_usd(cents).amount.as_decimal() == Decimal(dollars)


def test_money_conversion_preserves_digits_under_low_decimal_precision() -> None:
    with localcontext() as context:
        context.prec = 6
        assert cents_to_usd(
            "123456789012345678901234567890.123456"
        ).amount.as_decimal() == Decimal("1234567890123456789012345678.90123456")


@pytest.mark.parametrize(
    "value", ["NaN", "1e2", "1", "1.0000000", " 1.000000", "9" * 80 + ".000000"]
)
def test_unadmitted_money_shape_is_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        cents_to_usd(value)


@pytest.mark.parametrize("supplied", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_deadline_is_not_replaced_with_a_fresh_budget(
    supplied: float,
) -> None:
    with pytest.raises(TimeoutError):
        bounded_deadline(1000.0, supplied, 120)


def test_deadline_preserves_earlier_caller_bound_and_caps_later_bound() -> None:
    assert bounded_deadline(1000.0, 1003.0, 120) == 1003.0
    assert bounded_deadline(1000.0, 9000.0, 120) == 1120.0
    assert bounded_deadline(1000.0, None, 120) == 1120.0
    assert bounded_deadline(1000.0, 1003.0, 10) == 1003.0
    with pytest.raises(TimeoutError):
        bounded_deadline(1000.0, 1000.0, 10)
