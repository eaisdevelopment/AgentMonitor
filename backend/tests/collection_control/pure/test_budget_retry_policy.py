"""Pure time policy; constructed timestamps do not represent provider evidence."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.adapters.persistence.collection_control.sqlite import repository

from backend.tests.contracts.test_anthropic_billing_run import _admission


@pytest.mark.parametrize("delay,expected", [(1, True), (0, False), (-1, False)])
def test_only_future_retry_time_defers_dispatch(delay: int, expected: bool) -> None:
    now = datetime(2026, 11, 11, 12, tzinfo=UTC)
    assert (
        repository._budget_retry_deferred(now + timedelta(microseconds=delay), now)
        is expected
    )


def test_absent_retry_time_does_not_defer_dispatch() -> None:
    assert not repository._budget_retry_deferred(None, datetime.now(UTC))


def test_naive_retry_time_is_not_treated_as_elapsed() -> None:
    with pytest.raises(
        repository.CollectionRepositoryErrorV1, match="collection_timestamp_invalid"
    ):
        repository._budget_retry_deferred(datetime(2026, 11, 11), datetime.now(UTC))


def test_budget_schedule_metadata_matches_fifteen_minute_policy() -> None:
    assert (
        repository._schedule_interval_seconds(_admission(purpose="monitoring")) == 900
    )


def test_non_budget_schedule_preserves_five_minute_interval() -> None:
    from dataclasses import fields

    from agentmonitor.contracts.collection_control_v1 import CollectionRunAdmissionV2

    budget = _admission()
    ordinary = CollectionRunAdmissionV2(
        **{
            **{
                field.name: getattr(budget, field.name)
                for field in fields(CollectionRunAdmissionV2)
            },
            "profile_id": budget.account_id,
            "payload_schema": "quota.snapshot.v1",
        }
    )
    assert repository._schedule_interval_seconds(ordinary) == 300
