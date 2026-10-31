"""M07 local administrator alert commands with durable CAS receipts."""

import hashlib
import secrets
from datetime import timedelta
from typing import Literal, cast

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.alerting.sqlite.capacity_consumer import (
    SqliteCapacityAlertRepositoryV1,
    _history,
    _save_alert,
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
    alert_from_snapshot,
    alert_snapshot,
)
from agentmonitor.contracts.alerting_v1 import (
    AlertCommandResultV1,
    AlertHistoryEntryV1,
    AlertHistoryQueryV1,
    AlertLifecycleV1,
    AlertListQueryV1,
    AlertReasonCodeV1,
    AlertSeverityV1,
    AlertTransitionV1,
    AlertViewV1,
    DashboardNotificationCountsV1,
    DashboardNotificationViewV1,
    MarkAlertReadCommandV1,
    SnoozeAlertCommandV1,
    UnsnoozeAlertCommandV1,
)
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.modules.alerting.application.ports import AlertUserCommandV1
from agentmonitor.modules.alerting.domain.lifecycle import (
    acknowledge_alert,
    mark_alert_read,
    snooze_alert,
    unsnooze_alert,
)
from agentmonitor.modules.alerting.domain.notifications import ordered_notifications
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError


class AlertActionRepositoryErrorV1(ValueError):
    """Closed failure; never exposes stored values or input payloads."""


def _kind(
    command: AlertUserCommandV1,
) -> Literal["acknowledge_alert", "snooze_alert", "unsnooze_alert", "mark_alert_read"]:
    if isinstance(command, MarkAlertReadCommandV1):
        return "mark_alert_read"
    if isinstance(command, SnoozeAlertCommandV1):
        return "snooze_alert"
    if isinstance(command, UnsnoozeAlertCommandV1):
        return "unsnooze_alert"
    return "acknowledge_alert"


def _digest(command: AlertUserCommandV1) -> str:
    document: dict[str, str | int] = {
        "kind": _kind(command),
        "alert_id": command.alert_id.value,
    }
    if isinstance(command, MarkAlertReadCommandV1):
        document["expected_notification_revision"] = (
            command.expected_notification_revision
        )
    else:
        document["expected_record_version"] = command.expected_record_version
    if isinstance(command, SnoozeAlertCommandV1):
        document["duration_seconds"] = command.duration_seconds
    # Server admission time is not command identity on a network retry.
    return hashlib.sha256(canonical_json(document).encode("ascii")).hexdigest()


def _receipt(
    connection: Connection, command: AlertUserCommandV1
) -> AlertCommandResultV1 | None:
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM alert_command_receipt WHERE principal_id=? AND command_id=?",
            (command.actor_id.value, command.command_id.value),
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    if text(row["command_kind"]) != _kind(command) or text(
        row["request_digest"]
    ) != _digest(command):
        raise AlertActionRepositoryErrorV1("alert_idempotency_conflict")
    result = alert_from_snapshot(row["result_json"])
    if result.alert_id != command.alert_id or result.record_version != integer(
        row["result_record_version"]
    ):
        raise AlertActionRepositoryErrorV1("alert_receipt_integrity_failed")
    return AlertCommandResultV1(OpaqueIdV1(text(row["receipt_id"])), result)


_EXPECTED = frozenset(
    {
        "alert_command_subject_conflict",
        "alert_version_conflict",
        "alert_notification_conflict",
        "alert_not_open",
        "alert_transition_time_invalid",
    }
)


def _alert_filter(query: AlertListQueryV1) -> tuple[str, list[object]]:
    """Only fixed SQL fragments; every owner-supplied value is bound."""
    clauses = ["last_seen_at<=?"]
    parameters: list[object] = [utc_text(query.as_of)]
    if query.condition_type is not None:
        clauses.append("condition_type=?")
        parameters.append(query.condition_type)
    if query.scope is not None:
        kind = query.scope.scope_kind
        if kind == "account":
            clauses.append("account_id=?")
        elif kind == "provider":
            clauses.append("provider_key=?")
        elif kind == "organization":
            clauses.append("organization_id=?")
        else:
            kind = "global"
        if kind != "global":
            parameters.append(query.scope.scope_id)
    if query.lifecycle is not None:
        clauses.append("lifecycle=?")
        parameters.append(query.lifecycle)
    if query.severity is not None:
        clauses.append("severity=?")
        parameters.append(query.severity)
    if query.unread is not None:
        clauses.append("unread=?")
        parameters.append(int(query.unread))
    if query.snoozed is not None:
        clauses.append(
            "(lifecycle='open' AND snoozed_until>?)"
            if query.snoozed
            else "NOT (lifecycle='open' AND snoozed_until>?)"
        )
        parameters.append(utc_text(query.as_of))
    if query.range_start is not None and query.range_before is not None:
        clauses.extend(("latest_notification_at>=?", "latest_notification_at<?"))
        parameters.extend((utc_text(query.range_start), utc_text(query.range_before)))
    return " AND ".join(clauses), parameters


def _alert_cursor(raw: str) -> tuple[str, str]:
    try:
        time_value, alert_id = raw.rsplit(":", 1)
        if utc_text(utc_value(time_value)) != time_value:
            raise ValueError
        identity = OpaqueIdV1(alert_id)
        if identity.value != alert_id:
            raise ValueError
        return time_value, alert_id
    except (ValueError, TypeError):
        raise AlertActionRepositoryErrorV1("alert_page_key_invalid") from None


def _history_cursor(raw: str) -> int:
    if not raw.isdecimal() or raw.startswith("0") or len(raw) > 12:
        raise AlertActionRepositoryErrorV1("alert_page_key_invalid")
    return int(raw)


def _history_row(row: object) -> AlertHistoryEntryV1:
    if not hasattr(row, "__getitem__"):
        raise ValueError("alert_history_invalid")
    return AlertHistoryEntryV1(
        OpaqueIdV1(text(row["event_id"])),
        OpaqueIdV1(text(row["alert_id"])),
        integer(row["aggregate_sequence"]),
        cast(AlertTransitionV1, text(row["transition"])),
        utc_value(row["occurred_at"]),
        cast(AlertLifecycleV1 | None, row["previous_lifecycle"]),
        cast(AlertLifecycleV1, text(row["current_lifecycle"])),
        cast(AlertSeverityV1 | None, row["previous_severity"]),
        cast(AlertSeverityV1, text(row["current_severity"])),
        OpaqueIdV1(text(row["actor_id"])) if row["actor_id"] is not None else None,
        cast(AlertReasonCodeV1, text(row["reason_code"])),
        OpaqueIdV1(text(row["source_event_id"]))
        if row["source_event_id"] is not None
        else None,
        OpaqueIdV1(text(row["command_id"])) if row["command_id"] is not None else None,
    )


class SqliteAlertActionRepositoryV1(SqliteCapacityAlertRepositoryV1):
    """One writer lock for projection, history, deadline, outbox and receipt."""

    def list_alerts(self, query: AlertListQueryV1) -> QueryPageV1[AlertViewV1]:
        where, parameters = _alert_filter(query)
        if query.after_key is not None:
            time_key, id_key = _alert_cursor(query.after_key)
            where += " AND (latest_notification_at,alert_id)<(?,?)"
            parameters.extend((time_key, id_key))
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT * FROM alert_alert WHERE "
                            + where
                            + " ORDER BY latest_notification_at DESC, alert_id DESC"
                            + " LIMIT ?",
                            tuple([*parameters, query.limit + 1]),
                        )
                        .mappings()
                        .all()
                    )
            has_more = len(rows) > query.limit
            items = tuple(alert_from_row(row) for row in rows[: query.limit])
            next_key = (
                utc_text(items[-1].latest_notification_at)
                + ":"
                + items[-1].alert_id.value
                if has_more
                else None
            )
            return QueryPageV1(
                items,
                query.limit,
                has_more,
                next_key,
                QueryAvailabilityV1("available", "alert_query_complete", query.as_of),
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertActionRepositoryErrorV1("alert_repository_unavailable") from None

    def list_history(
        self, query: AlertHistoryQueryV1
    ) -> QueryPageV1[AlertHistoryEntryV1]:
        parameters: list[object] = [query.alert_id.value, utc_text(query.as_of)]
        where = "alert_id=? AND occurred_at<=?"
        if query.after_key is not None:
            where += " AND aggregate_sequence>?"
            parameters.append(_history_cursor(query.after_key))
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT * FROM alert_event WHERE "
                            + where
                            + " ORDER BY aggregate_sequence ASC LIMIT ?",
                            tuple([*parameters, query.limit + 1]),
                        )
                        .mappings()
                        .all()
                    )
            has_more = len(rows) > query.limit
            items = tuple(_history_row(row) for row in rows[: query.limit])
            next_key = str(items[-1].aggregate_sequence) if has_more else None
            return QueryPageV1(
                items,
                query.limit,
                has_more,
                next_key,
                QueryAvailabilityV1("available", "alert_history_complete", query.as_of),
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertActionRepositoryErrorV1("alert_repository_unavailable") from None

    def list_notifications(
        self, query: AlertListQueryV1
    ) -> QueryPageV1[DashboardNotificationViewV1]:
        where, parameters = _alert_filter(query)
        rank = (
            "CASE WHEN lifecycle='open' AND "
            "(snoozed_until IS NULL OR snoozed_until<=?) "
            "THEN CASE WHEN severity='critical' THEN 0 ELSE 1 END "
            "WHEN lifecycle='recovered' AND unread=1 THEN 2 ELSE 3 END"
        )
        rank_time = utc_text(query.as_of)
        outer_where = ""
        if query.after_key is not None:
            parts = query.after_key.split(":", 1)
            if len(parts) != 2 or parts[0] not in ("0", "1", "2", "3"):
                raise AlertActionRepositoryErrorV1("alert_page_key_invalid")
            time_key, id_key = _alert_cursor(parts[1])
            outer_where = (
                " WHERE (notification_rank>? OR "
                "(notification_rank=? AND "
                "(latest_notification_at,alert_id)<(?,?)))"
            )
            cursor_parameters: list[object] = [
                int(parts[0]),
                int(parts[0]),
                time_key,
                id_key,
            ]
        else:
            cursor_parameters = []
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT * FROM (SELECT alert_alert.*, "
                            + rank
                            + " AS notification_rank FROM alert_alert WHERE "
                            + where
                            + ")"
                            + outer_where
                            + " ORDER BY notification_rank ASC, "
                            "latest_notification_at DESC, alert_id DESC LIMIT ?",
                            tuple(
                                [
                                    rank_time,
                                    *parameters,
                                    *cursor_parameters,
                                    query.limit + 1,
                                ]
                            ),
                        )
                        .mappings()
                        .all()
                    )
            has_more = len(rows) > query.limit
            alerts = tuple(alert_from_row(row) for row in rows[: query.limit])
            items = ordered_notifications(alerts, query.as_of)
            next_key = (
                str(items[-1].rank)
                + ":"
                + utc_text(items[-1].alert.latest_notification_at)
                + ":"
                + items[-1].alert.alert_id.value
                if has_more
                else None
            )
            return QueryPageV1(
                items,
                query.limit,
                has_more,
                next_key,
                QueryAvailabilityV1(
                    "available", "alert_notification_query_complete", query.as_of
                ),
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertActionRepositoryErrorV1("alert_repository_unavailable") from None

    def notification_counts(
        self, query: AlertListQueryV1
    ) -> DashboardNotificationCountsV1:
        where, parameters = _alert_filter(query)
        # Aggregate the full matching set, independent of the caller's page limit.
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = connection.exec_driver_sql(
                        "SELECT "
                        "coalesce(sum(lifecycle='open' AND severity='critical' "
                        "AND (snoozed_until IS NULL OR snoozed_until>?)),0), "
                        "coalesce(sum(lifecycle='open' AND severity='warning' "
                        "AND (snoozed_until IS NULL OR snoozed_until>?)),0), "
                        "coalesce(sum(unread=1 AND NOT (lifecycle='open' "
                        "AND snoozed_until>?)),0), "
                        "coalesce(sum(unread=1),0), "
                        "coalesce(sum(acknowledged_at IS NOT NULL),0), "
                        "coalesce(sum(lifecycle='open' AND snoozed_until>?),0), "
                        "coalesce(sum(lifecycle='recovered'),0) "
                        "FROM alert_alert WHERE " + where,
                        tuple(
                            [
                                utc_text(query.as_of),
                                utc_text(query.as_of),
                                utc_text(query.as_of),
                                utc_text(query.as_of),
                                *parameters,
                            ]
                        ),
                    ).one()
            result = DashboardNotificationCountsV1(*(integer(value) for value in row))
            return result
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertActionRepositoryErrorV1("alert_repository_unavailable") from None

    def lookup_alert_command(
        self, command: AlertUserCommandV1
    ) -> AlertCommandResultV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    return _receipt(connection, command)
        except AlertActionRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertActionRepositoryErrorV1("alert_repository_unavailable") from None

    def apply_alert_command(self, command: AlertUserCommandV1) -> AlertCommandResultV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    replay = _receipt(connection, command)
                    if replay is not None:
                        connection.commit()
                        return replay
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM alert_alert WHERE alert_id=?",
                            (command.alert_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        raise AlertActionRepositoryErrorV1("alert_not_found")
                    prior = alert_from_row(row)
                    try:
                        if isinstance(command, MarkAlertReadCommandV1):
                            transition = mark_alert_read(prior, command)
                        elif isinstance(command, SnoozeAlertCommandV1):
                            transition = snooze_alert(prior, command)
                        elif isinstance(command, UnsnoozeAlertCommandV1):
                            transition = unsnooze_alert(prior, command)
                        else:
                            transition = acknowledge_alert(prior, command)
                    except ValueError as error:
                        if str(error) in _EXPECTED:
                            raise AlertActionRepositoryErrorV1(str(error)) from None
                        raise AlertActionRepositoryErrorV1(
                            "alert_command_invalid"
                        ) from None
                    changed = transition.alert or prior
                    if transition.transition is not None:
                        _save_alert(connection, changed, existing=row)
                        _history(
                            connection,
                            changed,
                            prior,
                            transition.transition,
                            None,
                            command.as_of,
                            actor_id=command.actor_id,
                            command_id=command.command_id,
                            reason_code=cast(AlertReasonCodeV1, transition.transition),
                        )
                    receipt = AlertCommandResultV1(
                        OpaqueIdV1(secrets.token_urlsafe(24)), changed
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO alert_command_receipt (receipt_id,principal_id,"
                        "command_id,request_digest,command_kind,subject_id,"
                        "result_record_version,result_json,created_at,expires_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (
                            receipt.receipt_id.value,
                            command.actor_id.value,
                            command.command_id.value,
                            _digest(command),
                            _kind(command),
                            command.alert_id.value,
                            changed.record_version,
                            alert_snapshot(changed),
                            utc_text(command.as_of),
                            utc_text(command.as_of + timedelta(days=365)),
                        ),
                    )
                    connection.commit()
                    return receipt
        except AlertActionRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise AlertActionRepositoryErrorV1("alert_repository_unavailable") from None
