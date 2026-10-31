"""Constructed inputs exercise only the pure polling decision."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.collection_control_v1 import CollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.queries import (
    source_poll_is_due_v1,
)
from agentmonitor.modules.collection_control.domain.polling import poll_is_due


def test_first_poll_and_minimum_interval() -> None:
    now = datetime(2026, 9, 28, tzinfo=UTC)
    assert poll_is_due(now, None, None, 300)
    assert not poll_is_due(now + timedelta(seconds=299), now, "succeeded", 300)
    assert poll_is_due(now + timedelta(seconds=300), now, "succeeded", 300)
    assert poll_is_due(now + timedelta(seconds=300), now, "partial", 300)


@pytest.mark.parametrize(
    "state",
    [
        "queued",
        "running",
        "committing",
        "failed",
        "blocked",
        "cancelled",
        "unsupported",
    ],
)
def test_no_repeat_without_a_successful_source_attempt(state: str) -> None:
    then = datetime(2026, 9, 28, tzinfo=UTC)
    assert not poll_is_due(then + timedelta(days=1), then, state, 300)


def test_invalid_pair_is_rejected() -> None:
    with pytest.raises(ValueError, match="collection_poll_input_invalid"):
        poll_is_due(datetime.now(UTC), None, "succeeded", 300)


def test_explicit_transient_failure_can_start_a_new_scheduled_observation() -> None:
    """M04-MANAGED-003: distinct scheduled reading, preserved minimum cadence."""
    then = datetime(2026, 9, 28, tzinfo=UTC)
    assert not poll_is_due(
        then + timedelta(seconds=299), then, "failed", 300, transient_read_failure=True
    )
    assert poll_is_due(
        then + timedelta(seconds=300), then, "failed", 300, transient_read_failure=True
    )
    assert not poll_is_due(
        then + timedelta(days=1), then, "blocked", 300, transient_read_failure=True
    )


def test_source_minimum_interval_is_measured_between_actual_attempt_starts() -> None:
    """M04-PURE-001: run cleanup time does not create a stale cadence gap."""
    requested = datetime(2026, 9, 29, tzinfo=UTC)
    started = requested + timedelta(seconds=1)
    latest = CollectionRunViewV1(
        run_id=OpaqueIdV1("run-one"),
        schedule_id=OpaqueIdV1("schedule-one"),
        provider_key="claude",
        account_id=OpaqueIdV1("account-one"),
        resource_id=OpaqueIdV1("resource-one"),
        capability_id="subscription.quota",
        state="succeeded",
        source_id="claude.subscription.usage.screen_reader",
        adapter_version="1.0.2",
        provider_version="2.1.283",
        target_generation=1,
        fencing_token=1,
        requested_at=requested,
        started_at=started,
        completed_at=started + timedelta(seconds=14),
        deadline_at=requested + timedelta(seconds=30),
        duration_ms=14_000,
        payload_digest="a" * 64,
        outcome_code="succeeded",
        error_code=None,
        observation_ids=(OpaqueIdV1("observation-one"),),
    )

    assert not source_poll_is_due_v1(started + timedelta(seconds=299), latest, 300_000)
    assert source_poll_is_due_v1(started + timedelta(seconds=300), latest, 300_000)
