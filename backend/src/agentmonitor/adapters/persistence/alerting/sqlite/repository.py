"""M07-only SQLite rule UoW. No hidden DDL, foreign SQL or provider access."""

import hashlib
import secrets
from datetime import timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.alerting.sqlite.codec import (
    canonical_json,
    config_document,
    rule_from_row,
    text,
    utc_text,
)
from agentmonitor.contracts.alerting_v1 import (
    AlertConditionTypeV1,
    AlertRuleCommandResultV1,
    AlertRuleListQueryV1,
    AlertRuleViewV1,
    AlertScopeRefV1,
    AlertSubjectV1,
    ArchiveAlertRuleCommandV1,
    CreateAlertRuleCommandV1,
    UpdateAlertRuleCommandV1,
)
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.contracts.registry_v1 import RegistryScopeSnapshotV1
from agentmonitor.modules.alerting.application.ports import RuleCommandV1
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class AlertRepositoryErrorV1(ValueError):
    """Sanitized expected mutation/infrastructure result, never driver messages."""


def _id() -> str:
    return secrets.token_urlsafe(24)


def _request(command: RuleCommandV1) -> tuple[str, str]:
    if isinstance(command, ArchiveAlertRuleCommandV1):
        kind = "archive_rule"
        data: dict[str, object] = {
            "kind": kind,
            "rule_id": command.rule_id.value,
            "expected_record_version": command.expected_record_version,
        }
    else:
        kind = (
            "update_rule"
            if isinstance(command, UpdateAlertRuleCommandV1)
            else "create_rule"
        )
        data = {
            "kind": kind,
            "condition_type": command.condition_type,
            "scope_kind": command.scope.scope_kind,
            "scope_id": command.scope.scope_id,
            "enabled": command.enabled,
            "configuration": config_document(command.configuration),
        }
        if isinstance(command, UpdateAlertRuleCommandV1):
            data.update(
                rule_id=command.rule_id.value,
                expected_record_version=command.expected_record_version,
            )
    # Server admission time changes on replay; it is not user command identity.
    return kind, hashlib.sha256(canonical_json(data).encode("ascii")).hexdigest()


class SqliteAlertingRepositoryV1:
    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    @staticmethod
    def _receipt(
        connection: Connection, command: RuleCommandV1
    ) -> AlertRuleCommandResultV1 | None:
        kind, digest = _request(command)
        receipt = (
            connection.exec_driver_sql(
                "SELECT * FROM alert_command_receipt WHERE principal_id=? AND "
                "command_id=?",
                (command.actor_id.value, command.command_id.value),
            )
            .mappings()
            .one_or_none()
        )
        if receipt is None:
            return None
        if receipt["command_kind"] != kind or receipt["request_digest"] != digest:
            raise AlertRepositoryErrorV1("alert_idempotency_conflict")
        revision = (
            connection.exec_driver_sql(
                "SELECT * FROM alert_rule_revision WHERE rule_id=? AND "
                "record_version=?",
                (receipt["subject_id"], receipt["result_record_version"]),
            )
            .mappings()
            .one_or_none()
        )
        if revision is None:
            raise AlertRepositoryErrorV1("alert_receipt_integrity_failed")
        return AlertRuleCommandResultV1(
            OpaqueIdV1(text(receipt["receipt_id"])), rule_from_row(revision)
        )

    def lookup_rule_command(
        self, command: RuleCommandV1
    ) -> AlertRuleCommandResultV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    return self._receipt(connection, command)
        except AlertRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise AlertRepositoryErrorV1("alert_repository_unavailable") from None

    def create_rule(
        self, command: CreateAlertRuleCommandV1, snapshot: RegistryScopeSnapshotV1
    ) -> AlertRuleCommandResultV1:
        return self._write_rule(command, snapshot)

    def update_rule(
        self, command: UpdateAlertRuleCommandV1, snapshot: RegistryScopeSnapshotV1
    ) -> AlertRuleCommandResultV1:
        return self._write_rule(command, snapshot)

    def archive_rule(
        self, command: ArchiveAlertRuleCommandV1, snapshot: RegistryScopeSnapshotV1
    ) -> AlertRuleCommandResultV1:
        return self._write_rule(command, snapshot)

    @staticmethod
    def _require_scope_available(
        connection: Connection,
        command: CreateAlertRuleCommandV1,
        excluded_rule_id: str | None,
    ) -> None:
        occupied = connection.exec_driver_sql(
            "SELECT rule_id FROM alert_rule WHERE archived_at IS NULL AND "
            "condition_type=? AND scope_kind=? AND scope_key=? AND (? IS NULL OR "
            "rule_id<>?) LIMIT 1",
            (
                command.condition_type,
                command.scope.scope_kind,
                command.scope.scope_id or "global",
                excluded_rule_id,
                excluded_rule_id,
            ),
        ).scalar_one_or_none()
        if occupied is not None:
            raise AlertRepositoryErrorV1("alert_rule_scope_conflict")

    def _write_rule(
        self, command: RuleCommandV1, snapshot: RegistryScopeSnapshotV1
    ) -> AlertRuleCommandResultV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    replay = self._receipt(connection, command)
                    if replay is not None:
                        connection.commit()
                        return replay
                    kind, digest = _request(command)
                    previous_scope: AlertScopeRefV1 | None = None
                    instant = utc_text(command.as_of)
                    if isinstance(
                        command, (UpdateAlertRuleCommandV1, ArchiveAlertRuleCommandV1)
                    ):
                        existing = self._get(connection, command.rule_id)
                        if existing is None:
                            raise AlertRepositoryErrorV1("alert_rule_not_found")
                        if existing.record_version != command.expected_record_version:
                            raise AlertRepositoryErrorV1("alert_version_conflict")
                        if existing.archived_at is not None:
                            raise AlertRepositoryErrorV1("alert_rule_archived")
                        if (
                            existing.updated_at is not None
                            and command.as_of < existing.updated_at
                        ):
                            raise AlertRepositoryErrorV1("alert_rule_time_conflict")
                        previous_scope = existing.scope
                        rule_id = command.rule_id.value
                        version = existing.record_version + 1
                        if isinstance(command, ArchiveAlertRuleCommandV1):
                            connection.exec_driver_sql(
                                "UPDATE alert_rule SET archived_at=?, updated_at=?, "
                                "actor_id=?, record_version=? WHERE rule_id=? AND "
                                "record_version=?",
                                (
                                    instant,
                                    instant,
                                    command.actor_id.value,
                                    version,
                                    rule_id,
                                    command.expected_record_version,
                                ),
                            )
                        else:
                            self._require_scope_available(connection, command, rule_id)
                            connection.exec_driver_sql(
                                "UPDATE alert_rule SET condition_type=?, "
                                "scope_kind=?, scope_key=?, enabled=?, config_json=?,"
                                " updated_at=?, actor_id=?, record_version=? WHERE "
                                "rule_id=? AND record_version=?",
                                (
                                    command.condition_type,
                                    command.scope.scope_kind,
                                    command.scope.scope_id or "global",
                                    int(command.enabled),
                                    canonical_json(
                                        config_document(command.configuration)
                                    ),
                                    instant,
                                    command.actor_id.value,
                                    version,
                                    rule_id,
                                    command.expected_record_version,
                                ),
                            )
                    else:
                        rule_id = _id()
                        version = 1
                        self._require_scope_available(connection, command, None)
                        connection.exec_driver_sql(
                            "INSERT INTO alert_rule (rule_id, condition_type, "
                            "scope_kind, scope_key, enabled, config_schema, "
                            "config_json, record_version, actor_id, created_at, "
                            "updated_at, archived_at) VALUES (?, ?, ?, ?, ?, 1, ?, 1,"
                            " ?, ?, ?, NULL)",
                            (
                                rule_id,
                                command.condition_type,
                                command.scope.scope_kind,
                                command.scope.scope_id or "global",
                                int(command.enabled),
                                canonical_json(config_document(command.configuration)),
                                command.actor_id.value,
                                instant,
                                instant,
                            ),
                        )
                    connection.exec_driver_sql(
                        "INSERT INTO alert_rule_revision (rule_id, record_version, "
                        "condition_type, scope_kind, scope_key, enabled, "
                        "config_schema, config_json, actor_id, command_id, "
                        "created_at, updated_at, archived_at) SELECT rule_id, "
                        "record_version, condition_type, scope_kind, scope_key, "
                        "enabled, config_schema, config_json, actor_id, ?, "
                        "created_at, updated_at, archived_at FROM alert_rule WHERE "
                        "rule_id=?",
                        (command.command_id.value, rule_id),
                    )
                    rule = self._get(connection, OpaqueIdV1(rule_id))
                    if rule is None:
                        raise AlertRepositoryErrorV1("alert_rule_integrity_failed")
                    receipt_id = _id()
                    connection.exec_driver_sql(
                        "INSERT INTO alert_command_receipt (receipt_id, principal_id,"
                        " command_id, request_digest, command_kind, subject_id, "
                        "result_record_version, result_json, created_at, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            receipt_id,
                            command.actor_id.value,
                            command.command_id.value,
                            digest,
                            kind,
                            rule_id,
                            version,
                            canonical_json(
                                {"rule_id": rule_id, "record_version": version}
                            ),
                            instant,
                            utc_text(command.as_of + timedelta(days=365)),
                        ),
                    )
                    affected_scopes: tuple[AlertScopeRefV1, ...] = (rule.scope,)
                    if previous_scope is not None and previous_scope != rule.scope:
                        affected_scopes += (previous_scope,)
                    for affected_scope in affected_scopes:
                        connection.exec_driver_sql(
                            "INSERT INTO alert_reevaluation_job (job_id, cause_kind, "
                            "cause_id, cause_revision, scope_kind, scope_key, cursor,"
                            " checkpoint_json, state, lease_owner, fence, "
                            "attempt_count, lease_until, next_due_at, safe_code, "
                            "created_at, completed_at) VALUES (?, 'rule', ?, ?, ?, ?,"
                            " NULL, ?, 'pending', NULL, 0, 0, NULL, ?, NULL, ?, NULL)",
                            (
                                _id(),
                                rule_id,
                                version,
                                affected_scope.scope_kind,
                                affected_scope.scope_id or "global",
                                canonical_json(
                                    {"registry_revision": snapshot.registry_revision}
                                ),
                                instant,
                                instant,
                            ),
                        )
                    self._append_rule_outbox(connection, command, rule)
                    connection.commit()
                    return AlertRuleCommandResultV1(OpaqueIdV1(receipt_id), rule)
        except AlertRepositoryErrorV1:
            raise
        except IntegrityError:
            raise AlertRepositoryErrorV1("alert_rule_scope_conflict") from None
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise AlertRepositoryErrorV1("alert_repository_unavailable") from None

    @staticmethod
    def _append_rule_outbox(
        connection: Connection, command: RuleCommandV1, rule: AlertRuleViewV1
    ) -> None:
        assert rule.rule_id is not None
        event_id = _id()
        instant = utc_text(command.as_of)
        payload = canonical_json(
            {
                "rule_id": rule.rule_id.value,
                "record_version": rule.record_version,
                "condition_type": rule.condition_type,
                "scope_kind": rule.scope.scope_kind,
                "scope_id": rule.scope.scope_id,
                "archived": rule.archived_at is not None,
            }
        )
        envelope = canonical_json(
            {
                "event_id": event_id,
                "event_type": "alert.rule.changed.v1",
                "occurred_at": instant,
                "recorded_at": instant,
                "producer": "alerting",
                "producer_version": "1.0.0",
                "correlation_id": command.command_id.value,
                "causation_id": command.command_id.value,
                "subject_id": rule.rule_id.value,
            }
        )
        connection.exec_driver_sql(
            "INSERT INTO alert_event_outbox (event_id, event_type, "
            "event_schema_major, stream_key, stream_sequence, subject_id, "
            "envelope_json, payload_json, payload_digest, occurred_at, recorded_at, "
            "available_at, delivery_state, attempt_count, fence, lease_owner, "
            "lease_until, delivered_at) VALUES (?, 'alert.rule.changed.v1', 1, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, 'pending', 0, 0, NULL, NULL, NULL)",
            (
                event_id,
                rule.rule_id.value,
                rule.record_version,
                rule.rule_id.value,
                envelope,
                payload,
                hashlib.sha256(payload.encode("ascii")).hexdigest(),
                instant,
                instant,
                instant,
            ),
        )

    @staticmethod
    def _get(connection: Connection, rule_id: OpaqueIdV1) -> AlertRuleViewV1 | None:
        row = (
            connection.exec_driver_sql(
                "SELECT * FROM alert_rule WHERE rule_id=?", (rule_id.value,)
            )
            .mappings()
            .one_or_none()
        )
        return rule_from_row(row) if row is not None else None

    def get_rule(self, rule_id: OpaqueIdV1) -> AlertRuleViewV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    return self._get(connection, rule_id)
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise AlertRepositoryErrorV1("alert_repository_unavailable") from None

    def list_rules(self, query: AlertRuleListQueryV1) -> QueryPageV1[AlertRuleViewV1]:
        clauses: list[str] = []
        parameters: list[object] = []
        if not query.include_archived:
            clauses.append("archived_at IS NULL")
        if query.condition_type is not None:
            clauses.append("condition_type=?")
            parameters.append(query.condition_type)
        if query.scope is not None:
            clauses.extend(("scope_kind=?", "scope_key=?"))
            parameters.extend(
                (query.scope.scope_kind, query.scope.scope_id or "global")
            )
        if query.after_key is not None:
            clauses.append("rule_id>?")
            parameters.append(query.after_key)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        parameters.append(query.limit + 1)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT * FROM alert_rule"
                            + where
                            + " ORDER BY rule_id LIMIT ?",
                            tuple(parameters),
                        )
                        .mappings()
                        .all()
                    )
            has_more = len(rows) > query.limit
            items = tuple(rule_from_row(row) for row in rows[: query.limit])
            key = (
                items[-1].rule_id.value
                if has_more and items[-1].rule_id is not None
                else None
            )
            return QueryPageV1(
                items,
                query.limit,
                has_more,
                key,
                QueryAvailabilityV1(
                    "available", "alert_rule_query_complete", query.as_of
                ),
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise AlertRepositoryErrorV1("alert_repository_unavailable") from None

    def list_rule_candidates(
        self, subject: AlertSubjectV1, condition_type: AlertConditionTypeV1
    ) -> tuple[AlertRuleViewV1, ...]:
        selections = [("global", "global")]
        if subject.provider_key is not None:
            selections.append(("provider", subject.provider_key))
        if subject.account_id is not None:
            selections.append(("account", subject.account_id.value))
            if subject.organization_id is not None:
                selections.append(("organization", subject.organization_id.value))
        parameters: list[object] = [condition_type]
        for kind, key in selections:
            parameters.extend((kind, key))
        clauses = " OR ".join("(scope_kind=? AND scope_key=?)" for _ in selections)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    rows: list[RowMapping] = list(
                        connection.exec_driver_sql(
                            "SELECT * FROM alert_rule WHERE archived_at IS NULL AND "
                            "condition_type=? AND (" + clauses + ")",
                            tuple(parameters),
                        ).mappings()
                    )
                    return tuple(rule_from_row(row) for row in rows)
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise AlertRepositoryErrorV1("alert_repository_unavailable") from None
