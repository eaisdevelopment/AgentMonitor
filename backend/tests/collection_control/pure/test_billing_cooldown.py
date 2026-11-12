"""Pure billing cooldown selection; timestamps are not provider observations."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.adapters.persistence.collection_control.sqlite import repository

NOW = datetime(2026, 11, 12, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    "retry_delta,reservation_delta,expected_delta",
    [
        (None, None, None),
        (0, None, None),
        (-1, 0, None),
        (1, None, 1),
        (None, 1, 1),
        (1, 2, 2),
        (3, 2, 3),
    ],
)
def test_cooldown_uses_latest_future_boundary(
    retry_delta: int | None, reservation_delta: int | None, expected_delta: int | None
) -> None:
    def instant(delta: int | None) -> datetime | None:
        return None if delta is None else NOW + timedelta(microseconds=delta)

    assert repository._billing_cooldown_boundary(
        NOW, instant(retry_delta), instant(reservation_delta)
    ) == instant(expected_delta)


def test_invalid_stored_cooldown_does_not_become_ready() -> None:
    with pytest.raises(
        repository.CollectionRepositoryErrorV1, match="collection_timestamp_invalid"
    ):
        repository._billing_cooldown_boundary(NOW, datetime(2026, 11, 12), None)
