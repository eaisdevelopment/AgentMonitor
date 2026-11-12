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
    due = due_billing_targets(
        ((target, "7d", now - timedelta(hours=1)), (other, "7d", None)), now
    )
    assert tuple(item.target.connection.resource_id for item in due) == (
        other.connection.resource_id,
        target.connection.resource_id,
    )
    assert (
        due_billing_targets(((target, "7d", now - timedelta(seconds=10)),), now) == ()
    )
    # A complete Check in this window delays the first scheduled read to next window.
    assert (
        len(due_billing_targets(((target, "7d", now),), now + timedelta(minutes=15)))
        == 1
    )


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
        ((anthropic, "7d", now - timedelta(hours=1)), (openai, "7d", None)), now
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


def test_thirty_day_schedule_is_independent_and_captures_completed_utc_days() -> None:
    from agentmonitor.composition.billing_schedule import billing_schedule_intent

    now = datetime(2026, 11, 11, 12, 1, tzinfo=UTC)
    target = _target(purpose="monitoring")
    week = billing_schedule_intent(target, now)
    month = billing_schedule_intent(target, now, range_key="30d")
    assert month.run_id != week.run_id
    assert month.schedule_id != week.schedule_id
    assert month.report_context.range_key == "30d"
    assert month.report_context.interval_end == week.report_context.interval_end
    assert month.report_context.interval_start == datetime(2026, 10, 12, tzinfo=UTC)
    assert month == billing_schedule_intent(
        target, now + timedelta(seconds=1), range_key="30d"
    )


def test_recent_week_does_not_suppress_uncollected_month() -> None:
    from agentmonitor.composition.billing_schedule import due_billing_targets

    now = datetime(2026, 11, 11, 12, 1, tzinfo=UTC)
    target = _target(purpose="monitoring")
    selected = due_billing_targets(((target, "7d", now), (target, "30d", None)), now)
    assert tuple(item.report_context.range_key for item in selected) == ("30d",)


def test_range_selection_prefers_oldest_attempt_not_range_name() -> None:
    from agentmonitor.composition.billing_schedule import due_billing_targets

    now = datetime(2026, 11, 11, 12, 1, tzinfo=UTC)
    target = _target(purpose="monitoring")
    candidates = (
        (target, "7d", now - timedelta(minutes=20)),
        (target, "30d", now - timedelta(hours=1)),
    )
    selected = due_billing_targets(candidates, now)
    assert tuple(item.report_context.range_key for item in selected) == ("30d", "7d")
    assert selected == due_billing_targets(tuple(reversed(candidates)), now)


def test_schedule_rejects_unadmitted_range() -> None:
    import pytest
    from agentmonitor.composition.billing_schedule import billing_schedule_intent

    with pytest.raises(ValueError, match="billing_schedule_range_invalid"):
        billing_schedule_intent(
            _target(purpose="monitoring"),
            datetime(2026, 11, 11, tzinfo=UTC),
            range_key="90d",
        )


def test_distinct_schedules_do_not_alias_the_unique_target_or_reset_budget() -> None:
    from agentmonitor.composition.billing_run import (
        anthropic_billing_request,
        build_anthropic_billing_run,
    )
    from agentmonitor.composition.openai_billing_run import (
        build_openai_billing_run,
        openai_billing_request,
    )

    from backend.tests.contracts import test_anthropic_billing_run as anthropic
    from backend.tests.contracts import test_openai_billing_run as openai

    for source, build, request in (
        (anthropic, build_anthropic_billing_run, anthropic_billing_request),
        (openai, build_openai_billing_run, openai_billing_request),
    ):
        target = source._target(purpose="monitoring")
        params = dict(
            target=target,
            access_target=source._access_target(),
            registry_revision=11,
            scheduler_instance_id=OpaqueIdV1("worker"),
            run_id=OpaqueIdV1("run"),
            request_id=OpaqueIdV1("request"),
            retry_chain_id=OpaqueIdV1("retry"),
            correlation_id=OpaqueIdV1("correlation"),
            causation_id=None,
            trigger="scheduled",
            request_principal_id=None,
            idempotency_key_digest=None,
            requested_at=source.NOW,
            deadline_at=source.NOW + timedelta(seconds=120),
        )
        first = build(**params, schedule_id=OpaqueIdV1("first"))
        second = build(**params, schedule_id=OpaqueIdV1("second"))
        assert first.target_key_digest != second.target_key_digest
        assert first.budget_scope_digest == second.budget_scope_digest
        assert request(first).period == request(second).period
