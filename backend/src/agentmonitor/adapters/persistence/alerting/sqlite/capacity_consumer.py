"""M07 atomic alert projection from admitted typed M05 current facts."""

import hashlib
import json
import secrets
from collections.abc import Callable
from datetime import datetime
from typing import Literal, cast

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.alerting.sqlite.codec import (
    canonical_json,
    integer,
    text,
    utc_text,
    utc_value,
)
from agentmonitor.adapters.persistence.alerting.sqlite.projection_codec import (
    alert_from_row,
    decision_snapshot,
    event_payload_snapshot,
    rule_snapshot,
)
from agentmonitor.contracts.alerting_v1 import (
    AlertHistoryEntryV1,
    AlertOpenedV1,
    AlertReasonCodeV1,
    AlertSignalReceiptV1,
    AlertStateChangedV1,
    AlertTransitionV1,
    AlertViewV1,
)
from agentmonitor.contracts.capacity_v1 import CapacityCommittedNoticeV1
from agentmonitor.contracts.common_v1 import EventEnvelopeV1, OpaqueIdV1
from agentmonitor.contracts.events_v1 import DurableEventV1
from agentmonitor.modules.alerting.application.ports import PreparedCapacityAlertV1
from agentmonitor.modules.alerting.domain.fingerprint import fingerprint_alert_condition
from agentmonitor.modules.alerting.domain.lifecycle import reduce_alert_signal
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError


class AlertCapacityRepositoryErrorV1(ValueError):
    """Closed failure, without stored row content or provider detail."""


def _id() -> OpaqueIdV1:
    return OpaqueIdV1(secrets.token_urlsafe(24))


def _receipt(
    connection: Connection, event: DurableEventV1[CapacityCommittedNoticeV1]
) -> AlertSignalReceiptV1 | None:
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM alert_event_receipt WHERE producer_key='capacity' "
            "AND event_id=?",
            (event.envelope.event_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    if text(row["payload_digest"]) != event.payload_digest:
        raise AlertCapacityRepositoryErrorV1("alert_capacity_event_digest_conflict")
    ids: object = json.loads(text(row["alert_ids_json"]))
    if (
        not isinstance(ids, list)
        or len(ids) > 200
        or any(type(item) is not str for item in ids)
    ):
        raise AlertCapacityRepositoryErrorV1("alert_capacity_receipt_invalid")
    return AlertSignalReceiptV1(
        OpaqueIdV1(text(row["receipt_id"])),
        OpaqueIdV1(text(row["event_id"])),
        cast(
            Literal[
                "applied", "duplicate", "stale_ignored", "not_evaluable", "rejected"
            ],
            text(row["disposition"]),
        ),
        tuple(OpaqueIdV1(item) for item in ids),
        integer(row["source_generation"]),
        utc_value(row["processed_at"]),
    )


def _alert_row(connection: Connection, fingerprint: str) -> RowMapping | None:
    return (
        connection.exec_driver_sql(
            "SELECT * FROM alert_alert WHERE fingerprint_version=1 AND "
            "fingerprint_digest=?",
            (fingerprint,),
        )
        .mappings()
        .one_or_none()
    )


_ALERT_COLUMNS = (
    "alert_id",
    "fingerprint_version",
    "fingerprint_digest",
    "fingerprint_material_json",
    "condition_type",
    "subject_kind",
    "subject_id",
    "dimension_kind",
    "dimension_id",
    "account_id",
    "provider_key",
    "organization_id",
    "registry_revision",
    "rule_snapshot_json",
    "severity",
    "lifecycle",
    "occurrence_generation",
    "occurrence_count",
    "record_version",
    "notification_revision",
    "aggregate_sequence",
    "opened_at",
    "last_seen_at",
    "recovered_at",
    "closed_at",
    "latest_notification_at",
    "unread",
    "acknowledged_at",
    "acknowledged_by",
    "snoozed_until",
    "deadline_generation",
    "decision_json",
)


def _save_alert(
    connection: Connection, alert: AlertViewV1, *, existing: RowMapping | None
) -> None:
    fingerprint = fingerprint_alert_condition(alert.condition_type, alert.subject, 1)
    subject = alert.subject
    deadline_generation = (
        0 if existing is None else integer(existing["deadline_generation"])
    )
    if existing is not None and (
        alert.snoozed_until
        != (
            utc_value(existing["snoozed_until"])
            if existing["snoozed_until"] is not None
            else None
        )
    ):
        deadline_generation += 1
        if existing["snoozed_until"] is not None:
            connection.exec_driver_sql(
                "UPDATE alert_deadline SET state='cancelled' WHERE alert_id=? "
                "AND state IN ('pending','claimed')",
                (alert.alert_id.value,),
            )
        if alert.snoozed_until is not None:
            connection.exec_driver_sql(
                "INSERT INTO alert_deadline (deadline_id,alert_id,kind,"
                "deadline_generation,due_at,state,lease_owner,fence,"
                "lease_until,completed_at,receipt_id) VALUES "
                "(?,?,'snooze_expiry',? ,?,'pending',NULL,0,NULL,NULL,NULL)",
                (
                    _id().value,
                    alert.alert_id.value,
                    deadline_generation,
                    utc_text(alert.snoozed_until),
                ),
            )
    values: tuple[object, ...] = (
        alert.alert_id.value,
        1,
        fingerprint.digest,
        fingerprint.canonical_material,
        alert.condition_type,
        subject.subject_kind,
        subject.subject_id.value,
        subject.dimension_kind,
        subject.dimension_id,
        subject.account_id.value if subject.account_id is not None else None,
        subject.provider_key,
        subject.organization_id.value if subject.organization_id is not None else None,
        subject.registry_revision,
        rule_snapshot(alert.rule),
        alert.severity,
        alert.lifecycle,
        alert.occurrence_generation,
        alert.occurrence_count,
        alert.record_version,
        alert.notification_revision,
        alert.aggregate_sequence,
        utc_text(alert.opened_at),
        utc_text(alert.last_seen_at),
        utc_text(alert.recovered_at) if alert.recovered_at is not None else None,
        utc_text(alert.closed_at) if alert.closed_at is not None else None,
        utc_text(alert.latest_notification_at),
        int(alert.unread),
        utc_text(alert.acknowledged_at) if alert.acknowledged_at is not None else None,
        alert.acknowledged_by.value if alert.acknowledged_by is not None else None,
        utc_text(alert.snoozed_until) if alert.snoozed_until is not None else None,
        deadline_generation,
        decision_snapshot(alert.decision),
    )
    if len(_ALERT_COLUMNS) != len(values):
        raise AlertCapacityRepositoryErrorV1("alert_projection_schema_invalid")
    if existing is None:
        connection.exec_driver_sql(
            "INSERT INTO alert_alert ("
            + ",".join(_ALERT_COLUMNS)
            + ") VALUES ("
            + ",".join("?" for _ in values)
            + ")",
            values,
        )
    else:
        changed = connection.exec_driver_sql(
            "UPDATE alert_alert SET "
            + ",".join(f"{name}=?" for name in _ALERT_COLUMNS[1:])
            + " WHERE alert_id=? AND record_version=?",
            values[1:] + (alert.alert_id.value, integer(existing["record_version"])),
        )
        if changed.rowcount != 1:
            raise AlertCapacityRepositoryErrorV1("alert_projection_version_conflict")


def _history(
    connection: Connection,
    alert: AlertViewV1,
    previous: AlertViewV1 | None,
    transition: AlertTransitionV1,
    source_event_id: OpaqueIdV1 | None,
    as_of: datetime,
    *,
    actor_id: OpaqueIdV1 | None = None,
    command_id: OpaqueIdV1 | None = None,
    reason_code: AlertReasonCodeV1 | None = None,
) -> None:
    history = AlertHistoryEntryV1(
        _id(),
        alert.alert_id,
        alert.aggregate_sequence,
        transition,
        as_of,
        previous.lifecycle if previous is not None else None,
        alert.lifecycle,
        previous.severity if previous is not None else None,
        alert.severity,
        actor_id,
        reason_code or alert.decision.reason_code,
        source_event_id,
        command_id,
    )
    connection.exec_driver_sql(
        "INSERT INTO alert_event (event_id,alert_id,aggregate_sequence,transition,"
        "previous_lifecycle,current_lifecycle,previous_severity,current_severity,"
        "actor_id,reason_code,source_event_id,command_id,occurred_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            history.event_id.value,
            history.alert_id.value,
            history.aggregate_sequence,
            history.transition,
            history.previous_lifecycle,
            history.current_lifecycle,
            history.previous_severity,
            history.current_severity,
            history.actor_id.value if history.actor_id is not None else None,
            history.reason_code,
            history.source_event_id.value if history.source_event_id else None,
            history.command_id.value if history.command_id else None,
            utc_text(as_of),
        ),
    )
    source = alert.decision.source
    references = (
        (
            ("event", source.event_id),
            *(("observation", item) for item in source.observation_ids),
            *(("evidence", item) for item in source.evidence_ids),
        )
        if source_event_id is not None
        else ()
    )
    for kind, reference in references:
        connection.exec_driver_sql(
            "INSERT INTO alert_evidence_reference (reference_id,alert_id,"
            "aggregate_sequence,producer_key,event_id,reference_kind,"
            "source_reference_id,condition_stream_key,source_generation,"
            "reason_code,recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                _id().value,
                alert.alert_id.value,
                alert.aggregate_sequence,
                source.producer_key,
                source.event_id.value,
                kind,
                reference.value,
                source.condition_stream_key,
                source.source_generation,
                source.reason_code,
                utc_text(as_of),
            ),
        )
    cause = source_event_id or command_id
    if cause is None:
        raise AlertCapacityRepositoryErrorV1("alert_event_cause_required")
    envelope = EventEnvelopeV1(
        history.event_id,
        "alert.opened.v1" if transition == "opened" else "alert.state_changed.v1",
        as_of,
        as_of,
        "alerting",
        "1.0.0",
        cause,
        cause,
        alert.alert_id,
    )
    envelope_json = canonical_json(
        {
            "event_id": envelope.event_id.value,
            "event_type": envelope.event_type,
            "occurred_at": utc_text(envelope.occurred_at),
            "recorded_at": utc_text(envelope.recorded_at),
            "producer": envelope.producer,
            "producer_version": envelope.producer_version,
            "correlation_id": envelope.correlation_id.value,
            "causation_id": envelope.causation_id.value
            if envelope.causation_id is not None
            else None,
            "subject_id": envelope.subject_id.value,
        }
    )
    published = (
        AlertOpenedV1(envelope, alert, alert.aggregate_sequence)
        if transition == "opened"
        else AlertStateChangedV1(envelope, history, alert)
    )
    payload_json = event_payload_snapshot(published)
    connection.exec_driver_sql(
        "INSERT INTO alert_event_outbox (event_id,event_type,event_schema_major,"
        "stream_key,stream_sequence,subject_id,envelope_json,payload_json,"
        "payload_digest,occurred_at,recorded_at,available_at,delivery_state,"
        "attempt_count,fence,lease_owner,lease_until,delivered_at) "
        "VALUES (?,?,1,?,?,?,?,?,?,?,?,?,'pending',0,0,NULL,NULL,NULL)",
        (
            history.event_id.value,
            envelope.event_type,
            alert.alert_id.value,
            alert.aggregate_sequence,
            alert.alert_id.value,
            envelope_json,
            payload_json,
            hashlib.sha256(payload_json.encode("ascii")).hexdigest(),
            utc_text(as_of),
            utc_text(as_of),
            utc_text(as_of),
        ),
    )


class SqliteCapacityAlertRepositoryV1:
    """BEGIN IMMEDIATE owns receipt, per-condition checkpoints and transitions."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def lookup_capacity_event(
        self, event: DurableEventV1[CapacityCommittedNoticeV1]
    ) -> AlertSignalReceiptV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    return _receipt(connection, event)
        except AlertCapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertCapacityRepositoryErrorV1(
                "alert_capacity_repository_unavailable"
            ) from None

    def commit_capacity_event(
        self,
        event: DurableEventV1[CapacityCommittedNoticeV1],
        prepared: tuple[PreparedCapacityAlertV1, ...],
        *,
        as_of: datetime,
        recheck_current: Callable[[], None],
    ) -> AlertSignalReceiptV1:
        if not prepared or len(prepared) > 200:
            raise AlertCapacityRepositoryErrorV1("alert_capacity_input_unavailable")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    replay = _receipt(connection, event)
                    if replay is not None:
                        connection.commit()
                        return replay
                    try:
                        recheck_current()
                    except ValueError:
                        raise AlertCapacityRepositoryErrorV1(
                            "alert_capacity_admission_changed"
                        ) from None
                    changed_alerts: list[OpaqueIdV1] = []
                    any_advanced = False
                    max_generation = 0
                    seen_streams: set[str] = set()
                    for item in prepared:
                        signal = item.signal
                        source = signal.decision.source
                        max_generation = max(max_generation, source.source_generation)
                        if (
                            source.producer_key != "capacity"
                            or source.event_id != event.envelope.event_id
                            or signal.condition_type
                            not in ("capacity_remaining", "capacity_exhausted")
                            or item.effective_rule.selected.condition_type
                            != signal.condition_type
                        ):
                            raise AlertCapacityRepositoryErrorV1(
                                "alert_capacity_input_conflict"
                            )
                        checkpoint_key = (
                            source.condition_stream_key + ":" + signal.condition_type
                        )
                        if len(checkpoint_key) > 128 or checkpoint_key in seen_streams:
                            raise AlertCapacityRepositoryErrorV1(
                                "alert_capacity_stream_conflict"
                            )
                        seen_streams.add(checkpoint_key)
                        checkpoint = (
                            connection.exec_driver_sql(
                                "SELECT * FROM alert_stream_checkpoint WHERE "
                                "producer_key='capacity' AND condition_stream_key=?",
                                (checkpoint_key,),
                            )
                            .mappings()
                            .one_or_none()
                        )
                        previous_generation = (
                            integer(checkpoint["source_generation"])
                            if checkpoint is not None
                            else 0
                        )
                        if source.source_generation <= previous_generation:
                            continue
                        any_advanced = True
                        fingerprint = fingerprint_alert_condition(
                            signal.condition_type,
                            signal.subject,
                            signal.condition_semantic_major,
                        )
                        prior_row = _alert_row(connection, fingerprint.digest)
                        if (
                            prior_row is not None
                            and text(prior_row["fingerprint_material_json"])
                            != fingerprint.canonical_material
                        ):
                            raise AlertCapacityRepositoryErrorV1(
                                "alert_capacity_fingerprint_collision"
                            )
                        prior = (
                            alert_from_row(prior_row) if prior_row is not None else None
                        )
                        alert_id = prior.alert_id if prior is not None else _id()
                        transition = reduce_alert_signal(
                            prior,
                            signal,
                            item.effective_rule.selected,
                            alert_id,
                            as_of,
                            greatest_source_generation=previous_generation,
                        )
                        if transition.alert is not None and transition.transition:
                            alert = transition.alert
                            _save_alert(connection, alert, existing=prior_row)
                            _history(
                                connection,
                                alert,
                                prior,
                                transition.transition,
                                event.envelope.event_id,
                                as_of,
                            )
                            changed_alerts.append(alert.alert_id)
                        rule = item.effective_rule.selected
                        evaluation = canonical_json(
                            {
                                "condition_type": signal.condition_type,
                                "rule_id": rule.rule_id.value
                                if rule.rule_id is not None
                                else None,
                                "rule_version": rule.record_version,
                                "registry_revision": signal.subject.registry_revision,
                            }
                        )
                        current_event_id = (
                            source.event_id.value
                            if signal.decision.truth_state == "current"
                            else checkpoint["current_event_id"]
                            if checkpoint is not None
                            else None
                        )
                        evaluable_generation = (
                            source.source_generation
                            if signal.decision.truth_state == "current"
                            else checkpoint["evaluable_generation"]
                            if checkpoint is not None
                            else None
                        )
                        connection.exec_driver_sql(
                            "INSERT INTO alert_stream_checkpoint "
                            "(producer_key,condition_stream_key,source_generation,"
                            "evaluable_generation,current_event_id,last_event_id,"
                            "last_payload_digest,registry_revision,rule_evaluation_json,"
                            "updated_at) VALUES ('capacity',?,?,?,?,?,?,?,?,?) "
                            "ON CONFLICT(producer_key,condition_stream_key) "
                            "DO UPDATE SET "
                            "source_generation=excluded.source_generation,"
                            "evaluable_generation=excluded.evaluable_generation,"
                            "current_event_id=excluded.current_event_id,"
                            "last_event_id=excluded.last_event_id,"
                            "last_payload_digest=excluded.last_payload_digest,"
                            "registry_revision=excluded.registry_revision,"
                            "rule_evaluation_json=excluded.rule_evaluation_json,"
                            "updated_at=excluded.updated_at",
                            (
                                checkpoint_key,
                                source.source_generation,
                                evaluable_generation,
                                current_event_id,
                                event.envelope.event_id.value,
                                event.payload_digest,
                                signal.subject.registry_revision,
                                evaluation,
                                utc_text(as_of),
                            ),
                        )
                    receipt = AlertSignalReceiptV1(
                        _id(),
                        event.envelope.event_id,
                        "applied"
                        if changed_alerts
                        else "not_evaluable"
                        if any_advanced
                        else "stale_ignored",
                        tuple(dict.fromkeys(changed_alerts)),
                        max_generation,
                        as_of,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO alert_event_receipt (receipt_id,producer_key,"
                        "event_id,payload_digest,condition_stream_key,"
                        "source_generation,disposition,alert_ids_json,processed_at) "
                        "VALUES (?,'capacity',?,?,?,?,?,?,?)",
                        (
                            receipt.receipt_id.value,
                            receipt.event_id.value,
                            event.payload_digest,
                            event.stream_key,
                            receipt.source_generation,
                            receipt.disposition,
                            canonical_json([item.value for item in receipt.alert_ids]),
                            utc_text(as_of),
                        ),
                    )
                    connection.commit()
                    return receipt
        except AlertCapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertCapacityRepositoryErrorV1(
                "alert_capacity_repository_unavailable"
            ) from None

    def get_alert(self, alert_id: OpaqueIdV1) -> AlertViewV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM alert_alert WHERE alert_id=?",
                            (alert_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return alert_from_row(row) if row is not None else None
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertCapacityRepositoryErrorV1(
                "alert_capacity_repository_unavailable"
            ) from None
