"""Pure request, money and resource-admission policy; no provider payloads."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from urllib.parse import parse_qs, urlsplit

import pytest
from agentmonitor.adapters.providers.codex.openai_api import policy as policy_module
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, CapacitySubjectV2
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    ProviderTargetRefV1,
)


def request(days: int = 7) -> policy_module.OpenAICostRequestV1:
    instant = datetime(2026, 11, 11, 16, 38, tzinfo=UTC)
    return policy_module.OpenAICostRequestV1(
        subject=CapacitySubjectV2(
            "codex",
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
        period=policy_module.completed_period(instant, days),
        requested_at=instant,
    )


@pytest.mark.parametrize("days", [7, 30])
def test_completed_utc_period_excludes_today_across_month_boundary(days: int) -> None:
    instant = datetime(2026, 11, 2, 23, 45, tzinfo=UTC)
    end = datetime(2026, 11, 2, tzinfo=UTC)
    assert policy_module.completed_period(instant, days) == BudgetPeriodV1(
        end - timedelta(days=days), end
    )


@pytest.mark.parametrize("days", [True, 0, 1, 31, 365])
def test_unadmitted_range_refused(days: int) -> None:
    with pytest.raises(ValueError):
        policy_module.completed_period(datetime(2026, 11, 11, tzinfo=UTC), days)


def test_naive_time_refused() -> None:
    with pytest.raises(ValueError):
        policy_module.completed_period(datetime(2026, 11, 11), 7)


@pytest.mark.parametrize(
    "change", ["provider", "binding", "scope", "generation", "range", "current_day"]
)
def test_wrong_authority_or_period_refused(change: str) -> None:
    value = request()
    with pytest.raises(ValueError):
        if change == "provider":
            replace(value, subject=replace(value.subject, provider_key="claude"))
        elif change == "binding":
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


def test_fixed_get_query_contains_only_admitted_fields_and_encoded_cursor() -> None:
    value = request(30)
    path = policy_module.request_path(value, "opaque/+?=&cursor")
    parsed = urlsplit(path)
    assert parsed.path == "/v1/organization/costs"
    assert not parsed.scheme and not parsed.netloc
    query = parse_qs(parsed.query)
    assert set(query) == {"start_time", "end_time", "bucket_width", "limit", "page"}
    assert query["bucket_width"] == ["1d"]
    assert query["limit"] == ["30"]
    assert query["page"] == ["opaque/+?=&cursor"]
    assert query["start_time"] == [str(int(value.period.start.timestamp()))]
    assert query["end_time"] == [str(int(value.period.end.timestamp()))]


@pytest.mark.parametrize("cursor", ["", "x\r\ny", "x" * 1025])
def test_cursor_is_a_bounded_query_value(cursor: str) -> None:
    with pytest.raises(ValueError):
        policy_module.request_path(request(), cursor)


@pytest.mark.parametrize(
    "value",
    [
        "0.1",
        "0.2",
        "-0.003",
        "1e-18",
        "0.000000",
        "123456789012345678901234567890.123456",
    ],
)
def test_numeric_lexeme_is_exact_without_scaling_or_float(value: str) -> None:
    with localcontext() as context:
        context.prec = 6
        number = policy_module.decimal_number(value)
        money = policy_module.money_from_number(number, "gbp")
        assert money.amount.as_decimal() == Decimal(value)
        assert money.currency == "GBP"


@pytest.mark.parametrize(
    "value", ["NaN", "Infinity", " 1.0", "+1", "01", "1e999999", "9" * 129]
)
def test_unadmitted_numeric_lexeme_refused(value: str) -> None:
    with pytest.raises(ValueError):
        policy_module.decimal_number(value)


@pytest.mark.parametrize(
    "number,currency",
    [
        (True, "usd"),
        (1.2, "usd"),
        ("1.2", "usd"),
        (Decimal("NaN"), "usd"),
        (Decimal("1e-19"), "usd"),
        (Decimal("1e78"), "usd"),
        (1, "USD"),
        (1, "unknown"),
    ],
)
def test_missing_precision_or_currency_is_not_invented(
    number: object, currency: object
) -> None:
    with pytest.raises(ValueError):
        policy_module.money_from_number(number, currency)


@pytest.mark.parametrize("supplied", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_deadline_refused_before_clamp(supplied: float) -> None:
    with pytest.raises(TimeoutError):
        policy_module.bounded_deadline(1000.0, supplied, 120)


def test_earlier_deadline_wins_and_later_deadline_is_capped() -> None:
    assert policy_module.bounded_deadline(1000.0, 1003.0, 120) == 1003.0
    assert policy_module.bounded_deadline(1000.0, 9999.0, 120) == 1120.0
    with pytest.raises(TimeoutError):
        policy_module.bounded_deadline(1000.0, 1000.0, 10)


def test_absent_runtime_grant_refuses_without_provider_dispatch() -> None:
    from agentmonitor.adapters.providers.codex.openai_api.source import (
        collect_cost_report_in_worker_v1,
    )

    result = collect_cost_report_in_worker_v1(request(), authorization=None)
    assert result.state == "authorization_unavailable"
    assert result.requests_made == 0
    assert result.report is None
