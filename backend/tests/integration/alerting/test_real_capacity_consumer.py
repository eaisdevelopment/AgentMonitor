"""A-LIVE01: genuine M05/M02 reads; M07 writes only isolated owned storage."""

import importlib.util
import json
import os
import secrets
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.alerting.sqlite.actions import (
    SqliteAlertActionRepositoryV1,
)
from agentmonitor.adapters.persistence.alerting.sqlite.capacity_consumer import (
    SqliteCapacityAlertRepositoryV1,
)
from agentmonitor.adapters.persistence.alerting.sqlite.repository import (
    SqliteAlertingRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.alerting_v1 import (
    AcknowledgeAlertCommandV1,
    AlertHistoryQueryV1,
    AlertListQueryV1,
    AlertScopeRefV1,
    CapacityRemainingRuleConfigurationV1,
    CreateAlertRuleCommandV1,
    MarkAlertReadCommandV1,
    SnoozeAlertCommandV1,
    UnsnoozeAlertCommandV1,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityAlertConditionQueryV1,
    CapacityCommittedNoticeV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.events_v1 import DurableEventV1
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.modules.alerting.application.commands import (
    AcknowledgeAlertV1,
    MarkAlertReadV1,
    SnoozeAlertV1,
    UnsnoozeAlertV1,
)
from agentmonitor.modules.alerting.application.consume import (
    ConsumeCapacityAlertEventV1,
)
from agentmonitor.modules.alerting.application.queries import (
    GetAlertV1,
    GetDashboardNotificationCountsV1,
    ListAlertHistoryV1,
    ListAlertsV1,
    ListDashboardNotificationsV1,
)
from agentmonitor.modules.alerting.application.rules import (
    CreateAlertRuleV1,
    ResolveEffectiveAlertRuleV1,
)
from agentmonitor.modules.capacity.application.events import ReadCapacityEventsV1
from agentmonitor.modules.capacity.application.queries import (
    ListCapacityAlertConditionsV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
    ListAccountResourcesV1,
    ListAccountsV1,
    ResolveAlertSubjectScopeV1,
)


def _selected_actual_trigger() -> tuple[
    DatabaseRefV1,
    DurableEventV1[CapacityCommittedNoticeV1],
    OpaqueIdV1,
    datetime,
]:
    selected = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if selected is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(selected)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    registry = SqliteRegistryRepositoryV1(reference)
    capacity = SqliteCapacityRepositoryV1(reference)
    as_of = datetime.now(UTC)
    eligible_resources: dict[OpaqueIdV1, OpaqueIdV1] = {}
    for account in ListAccountsV1(registry)("claude"):
        scope = ResolveAlertSubjectScopeV1(registry)(account.account_id)
        if scope is None or not scope.eligible:
            continue
        for resource in ListAccountResourcesV1(registry)(account.account_id):
            if resource.lifecycle == "active":
                assert resource.registry_revision == scope.registry_revision
                eligible_resources[resource.resource_id] = account.account_id
    assert eligible_resources, "BLOCKED: no eligible real resource"
    cursor = None
    for _ in range(10):
        batch = ReadCapacityEventsV1(capacity)(
            "m4-alert-readonly-observer", cursor, as_of
        )
        assert batch.availability.state == "available"
        for event in batch.events:
            account_id = eligible_resources.get(event.envelope.subject_id)
            if account_id is None:
                continue
            page = ListCapacityAlertConditionsV1(capacity)(
                CapacityAlertConditionQueryV1(
                    account_id, event.envelope.subject_id, None, as_of, 100
                )
            )
            if page.availability.state != "available" or page.has_more:
                continue
            facts = page.items
            if not facts or not any(item.availability == "current" for item in facts):
                continue
            assert all(
                item.account_id == account_id
                and item.resource_id == event.envelope.subject_id
                and item.provider_key == "claude"
                and item.generation > 0
                for item in facts
            )
            return reference, event, account_id, as_of
        if batch.next_cursor is None:
            break
        assert batch.next_cursor != cursor
        cursor = batch.next_cursor
    pytest.fail("BLOCKED: no genuine current capacity trigger")


def test_genuine_capacity_trigger_has_account_current_fact_and_consumer() -> None:
    _selected_actual_trigger()
    assert importlib.util.find_spec(
        "agentmonitor.modules.alerting.application.consume"
    ), "A-LIVE01: approved capacity-alert consumer is absent"


def _provision_actual_alerts(
    tmp_path: Path,
    credential: str | None = None,
) -> tuple[DatabaseRefV1, OpaqueIdV1, OpaqueIdV1]:
    source_reference, event, account_id, as_of = _selected_actual_trigger()
    source_registry = SqliteRegistryRepositoryV1(source_reference)
    source_capacity = SqliteCapacityRepositoryV1(source_reference)
    isolated = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(isolated)
    initialized = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(isolated), Argon2PasswordV1()
    )(
        SecretInputV1(credential or secrets.token_urlsafe(32)),
        correlation_id=secrets.token_hex(16),
    )
    assert initialized.code == "created" and initialized.administrator_id is not None
    rules = SqliteAlertingRepositoryV1(isolated)
    created = CreateAlertRuleV1(
        rules, AlertScopeAndSubjectQueryV1(SqliteRegistryRepositoryV1(isolated))
    )(
        CreateAlertRuleCommandV1(
            OpaqueIdV1(secrets.token_hex(16)),
            initialized.administrator_id,
            "capacity_remaining",
            AlertScopeRefV1("global", None),
            True,
            CapacityRemainingRuleConfigurationV1(1, 10000, 10000),
            as_of,
        )
    )
    assert created.rule.record_version == 1
    projection = SqliteCapacityAlertRepositoryV1(isolated)
    consume = ConsumeCapacityAlertEventV1(
        projection,
        ListCapacityAlertConditionsV1(source_capacity),
        ResolveAlertSubjectScopeV1(source_registry),
        ListAccountResourcesV1(source_registry),
        ResolveEffectiveAlertRuleV1(
            rules,
            ResolveAlertSubjectScopeV1(source_registry),
            AlertScopeAndSubjectQueryV1(source_registry),
        ),
    )
    receipt = consume(event, account_id, as_of=as_of)
    assert receipt.event_id == event.envelope.event_id
    assert receipt.disposition == "applied" and receipt.alert_ids
    assert consume(event, account_id, as_of=as_of) == receipt
    assert projection.lookup_capacity_event(event) == receipt
    for alert_id in receipt.alert_ids:
        alert = SqliteCapacityAlertRepositoryV1(isolated).get_alert(alert_id)
        assert alert is not None
        assert alert.subject.account_id == account_id
        assert alert.subject.subject_id == event.envelope.subject_id
        assert alert.decision.source.event_id == event.envelope.event_id
        assert alert.decision.source.observation_ids
        assert alert.lifecycle == "open"
    with open_sqlite_database(isolated, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_event_receipt"
                ).scalar_one()
                == 1
            )
            assert connection.exec_driver_sql(
                "SELECT count(*) FROM alert_event"
            ).scalar_one() == len(receipt.alert_ids)
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_event_outbox"
                ).scalar_one()
                == len(receipt.alert_ids) + 1
            )
            assert connection.exec_driver_sql(
                "SELECT count(*) FROM alert_event_outbox WHERE "
                "event_type='alert.opened.v1'"
            ).scalar_one() == len(receipt.alert_ids)
            published = connection.exec_driver_sql(
                "SELECT payload_json FROM alert_event_outbox WHERE "
                "event_type='alert.opened.v1' LIMIT 1"
            ).scalar_one()
            assert set(json.loads(published)) == {
                "envelope",
                "alert",
                "aggregate_sequence",
            }
            assert connection.exec_driver_sql(
                "SELECT count(*) FROM alert_stream_checkpoint"
            ).scalar_one() >= len(receipt.alert_ids)
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    return isolated, initialized.administrator_id, receipt.alert_ids[0]


def test_genuine_current_condition_commits_isolated_alerts_once(
    tmp_path: Path,
) -> None:
    _provision_actual_alerts(tmp_path)


def test_real_open_alert_exposes_versioned_user_actions(tmp_path: Path) -> None:
    """A-DB04: user actions require a genuine I03-created alert first."""
    reference, actor_id, alert_id = _provision_actual_alerts(tmp_path)
    assert SqliteCapacityAlertRepositoryV1(reference).get_alert(alert_id) is not None
    assert importlib.util.find_spec(
        "agentmonitor.modules.alerting.application.commands"
    ), "A-DB04: versioned user alert commands are absent"
    assert importlib.util.find_spec(
        "agentmonitor.adapters.persistence.alerting.sqlite.actions"
    ), "A-DB04: durable user alert action transaction is absent"
    repository = SqliteAlertActionRepositoryV1(reference)
    before = GetAlertV1(repository)(alert_id, as_of=datetime.now(UTC))
    assert before is not None and before.lifecycle == "open" and before.unread
    acknowledge = AcknowledgeAlertCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor_id,
        alert_id,
        before.record_version,
        datetime.now(UTC),
    )
    acknowledged = AcknowledgeAlertV1(repository)(acknowledge)
    assert acknowledged.alert.record_version == before.record_version + 1
    assert acknowledged.alert.acknowledged_by == actor_id
    assert not acknowledged.alert.unread
    assert (
        AcknowledgeAlertV1(repository)(replace(acknowledge, as_of=datetime.now(UTC)))
        == acknowledged
    )
    with pytest.raises(ValueError, match="alert_idempotency_conflict"):
        AcknowledgeAlertV1(repository)(
            replace(
                acknowledge,
                expected_record_version=acknowledge.expected_record_version + 1,
            )
        )
    with pytest.raises(ValueError, match="alert_version_conflict"):
        AcknowledgeAlertV1(repository)(
            replace(acknowledge, command_id=OpaqueIdV1(secrets.token_hex(16)))
        )
    snooze = SnoozeAlertCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor_id,
        alert_id,
        acknowledged.alert.record_version,
        datetime.now(UTC),
        60,
    )
    snoozed = SnoozeAlertV1(repository)(snooze)
    assert snoozed.alert.snoozed_until == snooze.as_of + timedelta(seconds=60)
    assert not snoozed.alert.unread
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT state FROM alert_deadline WHERE alert_id=?",
                    (alert_id.value,),
                ).scalar_one()
                == "pending"
            )
    assert (
        SnoozeAlertV1(SqliteAlertActionRepositoryV1(reference))(
            replace(snooze, as_of=datetime.now(UTC))
        )
        == snoozed
    )
    unsnooze = UnsnoozeAlertCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor_id,
        alert_id,
        snoozed.alert.record_version,
        datetime.now(UTC),
    )
    unsnoozed = UnsnoozeAlertV1(repository)(unsnooze)
    assert unsnoozed.alert.snoozed_until is None
    assert unsnoozed.alert.unread
    assert unsnoozed.alert.notification_revision == (
        snoozed.alert.notification_revision + 1
    )
    read = MarkAlertReadCommandV1(
        OpaqueIdV1(secrets.token_hex(16)),
        actor_id,
        alert_id,
        unsnoozed.alert.notification_revision,
        datetime.now(UTC),
    )
    marked = MarkAlertReadV1(repository)(read)
    assert not marked.alert.unread
    assert marked.alert.acknowledged_by == actor_id
    assert AcknowledgeAlertV1(repository)(acknowledge) == acknowledged
    assert GetAlertV1(repository)(alert_id, as_of=datetime.now(UTC)) == marked.alert
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_command_receipt"
                ).scalar_one()
                == 5
            )  # One rule command and four user commands.
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM alert_event WHERE alert_id=?",
                    (alert_id.value,),
                ).scalar_one()
                == 5
            )  # Genuine opened plus four user transitions.
            assert (
                connection.exec_driver_sql(
                    "SELECT state FROM alert_deadline WHERE alert_id=?",
                    (alert_id.value,),
                ).scalar_one()
                == "cancelled"
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    page = ListAlertsV1(repository)(AlertListQueryV1(datetime.now(UTC), limit=1))
    assert page.availability.state == "available" and len(page.items) == 1
    assert page.has_more and page.next_key is not None
    next_page = ListAlertsV1(repository)(
        AlertListQueryV1(datetime.now(UTC), limit=1, after_key=page.next_key)
    )
    assert len(next_page.items) == 1 and not next_page.has_more
    assert page.items[0].alert_id != next_page.items[0].alert_id
    assert marked.alert.subject.account_id is not None
    account_page = ListAlertsV1(repository)(
        AlertListQueryV1(
            datetime.now(UTC),
            scope=AlertScopeRefV1("account", marked.alert.subject.account_id.value),
            limit=10,
        )
    )
    assert len(account_page.items) == 2
    history = ListAlertHistoryV1(repository)(
        AlertHistoryQueryV1(alert_id, datetime.now(UTC), limit=10)
    )
    assert tuple(item.transition for item in history.items) == (
        "opened",
        "acknowledged",
        "snoozed",
        "unsnoozed",
        "marked_read",
    )
    first_event = ListAlertHistoryV1(repository)(
        AlertHistoryQueryV1(alert_id, datetime.now(UTC), limit=1)
    )
    assert first_event.has_more and first_event.next_key is not None
    second_event = ListAlertHistoryV1(repository)(
        AlertHistoryQueryV1(
            alert_id, datetime.now(UTC), limit=1, after_key=first_event.next_key
        )
    )
    assert tuple(item.transition for item in second_event.items) == ("acknowledged",)
    notifications = ListDashboardNotificationsV1(repository)(
        AlertListQueryV1(datetime.now(UTC), limit=10)
    )
    assert any(item.alert.alert_id == alert_id for item in notifications.items)
    first_notification = ListDashboardNotificationsV1(repository)(
        AlertListQueryV1(datetime.now(UTC), limit=1)
    )
    assert first_notification.has_more and first_notification.next_key is not None
    second_notification = ListDashboardNotificationsV1(repository)(
        AlertListQueryV1(
            datetime.now(UTC), limit=1, after_key=first_notification.next_key
        )
    )
    assert second_notification.items[0].alert.alert_id != (
        first_notification.items[0].alert.alert_id
    )
    counts = GetDashboardNotificationCountsV1(repository)(
        AlertListQueryV1(datetime.now(UTC), limit=1)
    )
    assert counts.active_critical == 2
    assert counts.acknowledged == 1 and counts.snoozed == 0
