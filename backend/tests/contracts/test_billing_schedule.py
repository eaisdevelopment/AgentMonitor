"""Pure scheduling intent and fairness; constructed targets never enter storage."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.contracts.test_anthropic_billing_run import _target


def test_window_identity_replays_and_rolls_over_at_utc_midnight() -> None:
    from agentmonitor.composition.billing_schedule import billing_schedule_intent

    target = _target(purpose="monitoring")
    now = datetime(2026, 11, 11, 23, 59, tzinfo=UTC)
    first = billing_schedule_intent(target, now)
    assert first == billing_schedule_intent(target, now + timedelta(seconds=30))
    later = billing_schedule_intent(target, now + timedelta(minutes=1))
    assert later.run_id != first.run_id
    assert later.schedule_id == first.schedule_id
    assert first.window_start == now.replace(minute=45)
    assert (
        first.window_start <= first.due_at < first.window_start + timedelta(minutes=1)
    )
    assert later.window_start == datetime(2026, 11, 12, tzinfo=UTC)


def test_binding_scope_and_connection_changes_create_distinct_intent() -> None:
    from agentmonitor.composition.billing_schedule import billing_schedule_intent

    target = _target(purpose="monitoring")
    now = datetime(2026, 11, 11, 12, 1, tzinfo=UTC)
    original = billing_schedule_intent(target, now)
    for changed in (
        replace(target, binding=replace(target.binding, generation=9)),
        replace(target, connection=replace(target.connection, scope_generation=4)),
        replace(target, connection=replace(target.connection, record_version=8)),
    ):
        actual = billing_schedule_intent(changed, now)
        assert actual.run_id != original.run_id
        assert actual.schedule_id != original.schedule_id


def test_due_selection_is_oldest_first_and_current_window_is_not_repeated() -> None:
    from agentmonitor.composition.billing_schedule import due_billing_targets

    target = _target(purpose="monitoring")
    other = replace(
        target,
        connection=replace(target.connection, resource_id=OpaqueIdV1("resource-2")),
    )
    now = datetime(2026, 11, 11, 12, 1, tzinfo=UTC)
    due = due_billing_targets(((target, now - timedelta(hours=1)), (other, None)), now)
    assert tuple(item.target.connection.resource_id for item in due) == (
        other.connection.resource_id,
        target.connection.resource_id,
    )
    assert due_billing_targets(((target, now - timedelta(seconds=10)),), now) == ()
    # A complete Check in this window delays the first scheduled read to next window.
    assert len(due_billing_targets(((target, now),), now + timedelta(minutes=15))) == 1


def test_openai_has_independent_identity_and_shares_oldest_due_order() -> None:
    from agentmonitor.composition.billing_schedule import (
        billing_schedule_intent,
        due_billing_targets,
    )

    anthropic = _target(purpose="monitoring")
    openai = replace(
        anthropic, connection=replace(anthropic.connection, provider_key="codex")
    )
    now = datetime(2026, 11, 11, 12, 1, tzinfo=UTC)
    first = billing_schedule_intent(openai, now)
    assert first == billing_schedule_intent(openai, now + timedelta(seconds=30))
    assert first.schedule_id != billing_schedule_intent(anthropic, now).schedule_id
    assert first.run_id != billing_schedule_intent(anthropic, now).run_id
    selected = due_billing_targets(
        ((anthropic, now - timedelta(hours=1)), (openai, None)), now
    )
    assert tuple(item.target.connection.provider_key for item in selected) == (
        "codex",
        "claude",
    )


def test_scheduled_intent_captures_the_reporting_window() -> None:
    from agentmonitor.composition.billing_schedule import billing_schedule_intent

    before = datetime(2026, 11, 11, 23, 59, tzinfo=UTC)
    intent = billing_schedule_intent(_target(purpose="monitoring"), before)
    assert intent.report_context.range_key == "7d"
    assert intent.report_context.interval_end == datetime(2026, 11, 11, tzinfo=UTC)
    assert intent.report_context.interval_start == datetime(2026, 11, 4, tzinfo=UTC)
