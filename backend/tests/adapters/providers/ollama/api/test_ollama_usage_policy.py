"""Constructed request/math values only; no provider JSON fixtures or I/O."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from typing import Literal, cast

import pytest
from agentmonitor.adapters.providers.ollama.api.policy import (
    OllamaUsageRequestV1,
    bounded_deadline,
    completed_period,
    dollars_to_money,
    request_path,
    retry_after_seconds,
    validate_response_context,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, CapacitySubjectV2
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    ProviderTargetRefV1,
)

NOW = datetime(2026, 11, 11, 14, 17, tzinfo=UTC)


def _request() -> OllamaUsageRequestV1:
    account = OpaqueIdV1("pure-account")
    return OllamaUsageRequestV1(
        subject=CapacitySubjectV2(
            "ollama",
            ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32)),
            account,
            OpaqueIdV1("pure-resource"),
        ),
        binding=ActiveCredentialBindingRefV1(
            account, OpaqueIdV1("amcb_" + "b" * 32), 1
        ),
        scope_id=None,
        scope_evidence="unresolved",
        scope_generation=1,
        range_key="7d",
        period=completed_period(NOW, "7d"),
        requested_at=NOW,
    )


@pytest.mark.parametrize("days", [7, 30])
def test_native_range_selects_only_completed_utc_days(days: int) -> None:
    key: Literal["7d", "30d"] = "7d" if days == 7 else "30d"
    period = completed_period(NOW, key)
    assert period.end == NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    assert period.start == period.end - timedelta(days=days)
    request = replace(_request(), range_key=key, period=period)
    assert request_path(request) == f"/api/usage?range={key}&scope=self"


def test_team_is_explicit_and_owner_scope_is_never_promoted() -> None:
    request = replace(
        _request(),
        scope="team",
        scope_id=OpaqueIdV1("pure-owner-scope"),
        scope_evidence="owner_asserted",
    )
    assert request_path(request) == "/api/usage?range=7d&scope=team"
    assert request.scope_evidence == "owner_asserted"
    assert _request().scope_id is None and _request().scope_evidence == "unresolved"


@pytest.mark.parametrize(
    "case",
    [
        "provider",
        "account",
        "installation",
        "generation",
        "scope",
        "range",
        "period",
        "scope_identity",
        "scope_evidence",
    ],
)
def test_request_rejects_unadmitted_authority_and_range(case: str) -> None:
    request = _request()
    with pytest.raises(ValueError):
        if case == "provider":
            replace(request, subject=replace(request.subject, provider_key="claude"))
        elif case == "account":
            replace(
                request,
                binding=replace(request.binding, account_id=OpaqueIdV1("wrong")),
            )
        elif case == "installation":
            replace(
                request,
                subject=replace(
                    request.subject,
                    provider_target=ProviderTargetRefV1(
                        "provider_installation", OpaqueIdV1("local")
                    ),
                ),
            )
        elif case == "generation":
            replace(request, scope_generation=0)
        elif case == "scope":
            replace(request, scope=cast(Literal["self", "team"], "arbitrary"))
        elif case == "range":
            replace(request, range_key=cast(Literal["7d", "30d"], "24h"))
        elif case == "period":
            replace(request, period=BudgetPeriodV1(request.period.start, NOW))
        elif case == "scope_identity":
            replace(request, scope_id=OpaqueIdV1("unproven"))
        else:
            replace(
                request,
                scope_evidence=cast(
                    Literal["provider_verified", "owner_asserted", "unresolved"],
                    "unknown",
                ),
            )


@pytest.mark.parametrize(
    "instant",
    [
        NOW.replace(tzinfo=None),
        NOW.astimezone(timezone(timedelta(hours=1))),
    ],
)
def test_utc_cutoff_rejects_naive_or_local_time(instant: datetime) -> None:
    with pytest.raises(ValueError):
        completed_period(instant, "7d")


@pytest.mark.parametrize("field", ["range", "scope", "granularity", "start", "end"])
def test_response_context_must_match_selected_scope_and_fixed_cutoff(
    field: str,
) -> None:
    request = _request()
    with pytest.raises(ValueError):
        validate_response_context(
            request,
            range_key="30d" if field == "range" else "7d",
            scope="team" if field == "scope" else "self",
            granularity="hour" if field == "granularity" else "day",
            start=request.period.start
            + (timedelta(days=1) if field == "start" else timedelta()),
            end=request.period.end + timedelta(days=1) if field == "end" else NOW,
        )


def test_response_until_is_coverage_not_a_data_watermark() -> None:
    request = _request()
    validate_response_context(
        request,
        range_key="7d",
        scope="self",
        granularity="day",
        start=request.period.start,
        end=NOW,
    )


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-0.000000",
        "0.004",
        "-0.004",
        "12345678901234567890123456789012345678.123456",
    ],
)
def test_source_dollars_remain_exact_under_small_decimal_context(value: str) -> None:
    amount = Decimal(value)
    expected = CanonicalDecimalV1.from_decimal(amount)
    with localcontext() as context:
        context.prec = 2
        actual = dollars_to_money(amount)
    assert actual.currency == "USD" and actual.amount == expected


@pytest.mark.parametrize(
    "value", [Decimal("NaN"), Decimal("Infinity"), Decimal("1e-19")]
)
def test_nonfinite_or_unrepresentable_money_is_rejected(value: Decimal) -> None:
    with pytest.raises(ValueError):
        dollars_to_money(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 1.0])
def test_original_deadline_is_validated_before_clamping(value: float) -> None:
    with pytest.raises(TimeoutError):
        bounded_deadline(2.0, value)


def test_deadline_and_retry_bounds_are_finite_and_closed() -> None:
    assert bounded_deadline(2.0, None) == 12.0
    assert bounded_deadline(2.0, 8.0) == 8.0
    assert retry_after_seconds("60") == 60
    for value in (None, "-1", "١", "1.5", "9" * 30):
        assert retry_after_seconds(value) is None
