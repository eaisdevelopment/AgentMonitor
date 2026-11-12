"""Pure billing action intent validation, no credentials or provider fixtures."""

from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_check_connection_requires_current_owner_versions() -> None:
    from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1

    for version in (0, -1, True):
        with pytest.raises(ValueError, match="billing_check_command_invalid"):
            BillingCheckCommandV1(
                OpaqueIdV1("account"),
                OpaqueIdV1("resource"),
                version,
                1,
                OpaqueIdV1("principal"),
                OpaqueIdV1("request"),
                datetime(2026, 11, 11, tzinfo=UTC),
            )


def test_collect_captures_completed_period_and_rejects_future() -> None:
    from dataclasses import replace
    from datetime import timedelta

    from agentmonitor.contracts.billing_actions_v1 import BillingCollectCommandV1
    from agentmonitor.contracts.collection_control_v1 import (
        BillingBudgetReportContextV1,
    )

    now = datetime(2026, 11, 12, tzinfo=UTC)
    context = BillingBudgetReportContextV1("7d", now - timedelta(days=7), now, "cost")
    command = BillingCollectCommandV1(
        OpaqueIdV1("account"),
        OpaqueIdV1("resource"),
        1,
        1,
        OpaqueIdV1("principal"),
        OpaqueIdV1("request"),
        now,
        context,
    )
    assert command.report_context == context
    with pytest.raises(ValueError, match="billing_collect_command_invalid"):
        replace(command, requested_at=now - timedelta(seconds=1))
    with pytest.raises(ValueError, match="billing_collect_command_invalid"):
        replace(command, report_context=None)  # type: ignore[arg-type]


def test_collect_identity_binds_period_and_is_distinct_from_check() -> None:
    from dataclasses import replace
    from datetime import timedelta

    from agentmonitor.composition.billing_actions import billing_check_identifiers
    from agentmonitor.contracts.billing_actions_v1 import (
        BillingCheckCommandV1,
        BillingCollectCommandV1,
    )
    from agentmonitor.contracts.collection_control_v1 import (
        BillingBudgetReportContextV1,
    )

    now = datetime(2026, 11, 12, tzinfo=UTC)
    args = (
        OpaqueIdV1("account"),
        OpaqueIdV1("resource"),
        1,
        1,
        OpaqueIdV1("principal"),
        OpaqueIdV1("request"),
        now,
    )
    context = BillingBudgetReportContextV1("7d", now - timedelta(days=7), now, "cost")
    command = BillingCollectCommandV1(*args, context)
    first = billing_check_identifiers(command)
    assert first == billing_check_identifiers(
        replace(command, requested_at=now + timedelta(days=1))
    )
    other = billing_check_identifiers(
        replace(
            command,
            report_context=replace(
                context,
                interval_start=context.interval_start - timedelta(days=7),
                interval_end=now - timedelta(days=7),
            ),
        )
    )
    assert other.run_id == first.run_id  # same key with changed intent must conflict
    assert other.schedule_id != first.schedule_id
    assert other.idempotency_key_digest != first.idempotency_key_digest
    assert (
        billing_check_identifiers(BillingCheckCommandV1(*args)).run_id != first.run_id
    )


def test_default_check_context_captures_utc_window_before_midnight() -> None:
    from datetime import timedelta

    from agentmonitor.composition.billing_context import completed_billing_cost_context

    before = datetime(2026, 11, 12, 23, 59, tzinfo=UTC)
    captured = completed_billing_cost_context(before)
    assert captured.interval_end == datetime(2026, 11, 12, tzinfo=UTC)
    assert captured.interval_start == datetime(2026, 11, 5, tzinfo=UTC)
    assert captured.range_key == "7d" and captured.source_category == "cost"
    assert captured != completed_billing_cost_context(before + timedelta(minutes=1))


def test_unsupported_collection_context_remains_actionable_problem() -> None:
    import json

    from agentmonitor.api.problem import problem_response

    response = problem_response(
        422, "billing_collect_context_unsupported", "collection-test"
    )
    assert response.status_code == 422
    assert (
        json.loads(bytes(response.body))["code"]
        == "billing_collect_context_unsupported"
    )


def test_policy_upgrade_changes_schedule_but_preserves_owner_replay_identity() -> None:
    from agentmonitor.composition.billing_actions import billing_check_identifiers
    from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1

    command = BillingCheckCommandV1(
        OpaqueIdV1("account"),
        OpaqueIdV1("resource"),
        1,
        1,
        OpaqueIdV1("owner"),
        OpaqueIdV1("command"),
        datetime(2026, 11, 12, tzinfo=UTC),
    )
    legacy = billing_check_identifiers(command, collection_policy_version="1.0.0")
    current = billing_check_identifiers(command)
    assert current.schedule_id != legacy.schedule_id
    assert current.run_id == legacy.run_id
    assert current.request_id == legacy.request_id
    assert current.idempotency_key_digest == legacy.idempotency_key_digest


def test_legacy_schedule_replay_is_readable_but_other_intent_still_conflicts() -> None:
    from dataclasses import replace

    from agentmonitor.composition.billing_actions import (
        _require_replay,
        billing_check_identifiers,
    )
    from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1

    from backend.tests.contracts.test_billing_monitoring_proof import _evidence

    target, stored, _, _ = _evidence()
    command = BillingCheckCommandV1(
        target.connection.account_id,
        target.connection.resource_id,
        1,
        target.connection.record_version,
        OpaqueIdV1("owner"),
        OpaqueIdV1("command"),
        stored.requested_at,
    )
    legacy = billing_check_identifiers(command, collection_policy_version="1.0.0")
    current = billing_check_identifiers(command)
    stored = replace(stored, run_id=legacy.run_id, schedule_id=legacy.schedule_id)
    assert _require_replay(command, current, stored, target) == stored
    with pytest.raises(ValueError, match="billing_check_idempotency_conflict"):
        _require_replay(
            command,
            current,
            replace(stored, schedule_id=OpaqueIdV1("unrelated")),
            target,
        )
