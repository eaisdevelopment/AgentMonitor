"""Pure dashboard-owned freshness policy; no provider or registry I/O."""

from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.providers.ollama.cloud_balance.freshness import (
    cloud_freshness_deadline_v1,
)


def test_freshness_scales_with_observed_monitored_account_count() -> None:
    observed = datetime(2026, 1, 1, tzinfo=UTC)
    assert cloud_freshness_deadline_v1(observed, 1) == observed + timedelta(minutes=15)
    assert cloud_freshness_deadline_v1(observed, 10) == observed + timedelta(
        seconds=1400
    )


def test_unknown_or_invalid_account_count_has_no_invented_deadline() -> None:
    observed = datetime(2026, 1, 1, tzinfo=UTC)
    assert cloud_freshness_deadline_v1(observed, None) is None
    assert cloud_freshness_deadline_v1(observed, 0) is None
    assert cloud_freshness_deadline_v1(observed, 1001) is None
