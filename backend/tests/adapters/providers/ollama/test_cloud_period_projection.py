"""Provider period start survives the pure capacity projection."""

from datetime import UTC, datetime
from decimal import Decimal

from agentmonitor.contracts.providers.ollama.cloud_balance.v1.schema import (
    IncludedCreditsV1,
    OllamaCloudBalanceV1,
    SourcePeriodV1,
    to_capacity_windows,
)


def test_included_credit_window_keeps_source_period_start() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    balance = OllamaCloudBalanceV1(
        IncludedCreditsV1(Decimal("1"), Decimal("2"), SourcePeriodV1(start, end)),
        None,
    )
    projection = to_capacity_windows(balance)
    assert projection.windows[0].source_period_start == start
    assert projection.windows[0].reset_at == end
