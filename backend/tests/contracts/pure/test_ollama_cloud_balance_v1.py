"""Pure Ollama balance contract examples; no provider I/O or payloads."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from agentmonitor.contracts.providers.ollama.cloud_balance.v1.schema import (
    IncludedCreditsV1,
    LegacyLimitsV1,
    LegacyWindowV1,
    OllamaCloudBalanceV1,
    SourcePeriodV1,
    to_capacity_windows,
)


def test_included_and_purchased_remain_separate_with_period() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    balance = OllamaCloudBalanceV1(
        included=IncludedCreditsV1(
            Decimal("12.50"), Decimal("25"), SourcePeriodV1(start, end)
        ),
        purchased_usd=Decimal("3.125"),
    )
    result = to_capacity_windows(balance)
    assert result.period == SourcePeriodV1(start, end)
    included, purchased = result.windows
    assert included.window_key == "ollama_included_credits"
    assert included.remaining.value is not None
    assert included.remaining_ratio.value is not None
    assert included.remaining.value.as_decimal() == Decimal("12.50")
    assert included.remaining.value.unit == "usd"
    assert included.remaining_ratio.value.as_decimal() == Decimal("0.5")
    assert included.remaining_ratio.value_kind == "derived"
    assert included.reset_at == end
    assert purchased.window_key == "ollama_purchased_credits"
    assert purchased.remaining.value is not None
    assert purchased.remaining.value.as_decimal() == Decimal("3.125")
    assert purchased.limit.value is None and purchased.remaining_ratio.value is None
    assert purchased.reset_at is None


def test_legacy_windows_keep_unknowns_and_distinguish_zero() -> None:
    reset = datetime(2026, 2, 1, tzinfo=UTC)
    balance = OllamaCloudBalanceV1(
        included=LegacyLimitsV1(
            LegacyWindowV1(Decimal("0"), reset), LegacyWindowV1(None, None)
        ),
        purchased_usd=None,
    )
    result = to_capacity_windows(balance)
    session, weekly, purchased = result.windows
    assert result.period is None
    assert session.remaining_ratio.value is not None
    assert session.remaining_ratio.value.as_decimal() == Decimal("0")
    assert session.remaining_ratio.value_kind == "provider_reported"
    assert session.reset_at == reset
    assert weekly.remaining_ratio.availability.state == "unknown"
    assert weekly.reset_at is None
    assert purchased.remaining.availability.state == "unknown"


def test_missing_and_zero_allowance_do_not_create_ratio() -> None:
    for allowance in (None, Decimal("0")):
        result = to_capacity_windows(
            OllamaCloudBalanceV1(
                included=IncludedCreditsV1(Decimal("0"), allowance, None),
                purchased_usd=None,
            )
        )
        assert result.windows[0].remaining.value is not None
        assert result.windows[0].remaining.value.as_decimal() == Decimal("0")
        assert result.windows[0].remaining_ratio.value is None


def test_reject_bad_values_and_inconsistent_period() -> None:
    with pytest.raises(ValueError):
        LegacyWindowV1(Decimal("101"), None)
    with pytest.raises(ValueError):
        IncludedCreditsV1(Decimal("-1"), None, None)
    with pytest.raises((TypeError, ValueError)):
        LegacyWindowV1(0.1, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        SourcePeriodV1(
            datetime(2026, 2, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)
        )
    with pytest.raises(ValueError):
        SourcePeriodV1(datetime(2026, 1, 1), None)


def test_nonterminating_derived_ratio_is_not_misrepresented_as_exact() -> None:
    result = to_capacity_windows(
        OllamaCloudBalanceV1(
            included=IncludedCreditsV1(Decimal("1"), Decimal("3"), None),
            purchased_usd=None,
        )
    )
    assert result.windows[0].remaining_ratio.value is None
    assert result.windows[0].remaining.value is not None
    assert result.windows[0].remaining.value.as_decimal() == Decimal("1")


def test_reset_and_period_fields_require_timestamps() -> None:
    with pytest.raises(ValueError):
        SourcePeriodV1("not a timestamp", None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        LegacyWindowV1(Decimal("50"), "not a timestamp")  # type: ignore[arg-type]


def test_credit_pools_do_not_individually_trigger_exhaustion() -> None:
    """Separate balances do not establish each is an independent limit."""
    for included, purchased in (
        (Decimal("20"), Decimal("0")),
        (Decimal("0"), Decimal("20")),
    ):
        result = to_capacity_windows(
            OllamaCloudBalanceV1(
                included=IncludedCreditsV1(included, Decimal("25"), None),
                purchased_usd=purchased,
            )
        )
        assert all(not window.is_constraining for window in result.windows)


def test_legacy_limits_remain_constraining() -> None:
    result = to_capacity_windows(
        OllamaCloudBalanceV1(
            included=LegacyLimitsV1(LegacyWindowV1(Decimal("10"), None), None),
            purchased_usd=Decimal("0"),
        )
    )
    assert result.windows[0].is_constraining
    assert not result.windows[1].is_constraining


def test_period_and_reset_reject_non_utc_timestamps() -> None:
    from datetime import timedelta, timezone

    non_utc = datetime(2026, 2, 1, tzinfo=timezone(timedelta(hours=1)))
    with pytest.raises(ValueError, match="timestamp-must-be-aware-utc"):
        SourcePeriodV1(None, non_utc)
    with pytest.raises(ValueError, match="timestamp-must-be-aware-utc"):
        LegacyWindowV1(Decimal("5"), non_utc)
    with pytest.raises(ValueError, match="timestamp-must-be-aware-utc"):
        LegacyWindowV1(Decimal("5"), datetime(2026, 2, 1))
