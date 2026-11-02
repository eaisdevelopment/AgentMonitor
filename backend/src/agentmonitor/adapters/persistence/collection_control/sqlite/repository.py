"""M04 repository over the production file-backed SQLite boundary."""

# ruff: noqa: E501 -- SQL text preserves auditable column and predicate ordering.

import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionFailedV1,
    CollectionFailurePolicyV1,
    CollectionRunAdmissionV1OrV2,
    CollectionRunAdmissionV2,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


class CollectionRepositoryErrorV1(ValueError):
    """A bounded repository error that never exposes SQL or stored values."""

    def __init__(self, code: str = "collection_repository_unavailable") -> None:
        self.code = code
        super().__init__(code)


def _storage_target(
    admission: CollectionRunAdmissionV1OrV2,
) -> tuple[str | None, str | None, str | None]:
    if isinstance(admission, CollectionRunAdmissionV2):
        if admission.provider_target.target_kind == "cloud_service":
            return (
                None,
                admission.provider_target.target_kind,
                admission.provider_target.target_id.value,
            )
        return admission.provider_target.target_id.value, None, None
    return admission.installation_id.value, None, None


def _require_cloud_run_target(
    connection: Connection,
    admission: CollectionRunAdmissionV1OrV2,
) -> None:
    expected = _storage_target(admission)
    row = connection.exec_driver_sql(
        "SELECT installation_id,provider_target_kind,provider_target_id "
        "FROM collection_run WHERE run_id=?",
        (admission.run_id.value,),
    ).one_or_none()
    if row is None or tuple(row) != expected:
        raise CollectionRepositoryErrorV1("collection_idempotency_conflict")


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise CollectionRepositoryErrorV1("collection_timestamp_invalid")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _utc_value(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _required_utc_value(value: object) -> datetime:
    if not isinstance(value, str):
        raise CollectionRepositoryErrorV1("collection_repository_unavailable")
    result = _utc_value(value)
    if result is None:
        raise CollectionRepositoryErrorV1("collection_repository_unavailable")
    return result


def _observation_ids(connection: Connection, run_id: str) -> tuple[OpaqueIdV1, ...]:
    values = connection.exec_driver_sql(
        "SELECT observation_id FROM collection_run_observation_ref "
        "WHERE run_id=? ORDER BY consumer_key, observation_id",
        (run_id,),
    ).scalars()
    return tuple(OpaqueIdV1(str(value)) for value in values)


def _run_view(connection: Connection, row: RowMapping) -> CollectionRunViewV1:
    return CollectionRunViewV1(
        run_id=OpaqueIdV1(str(row["run_id"])),
        schedule_id=OpaqueIdV1(str(row["schedule_id"])),
        provider_key=str(row["provider_key"]),
        account_id=(
            OpaqueIdV1(str(row["account_id"]))
            if row["account_id"] is not None
            else None
        ),
        resource_id=(
            OpaqueIdV1(str(row["resource_id"]))
            if row["resource_id"] is not None
            else None
        ),
        capability_id=str(row["capability_id"]),
        state=row["state"],
        source_id=str(row["source_id"]),
        adapter_version=str(row["adapter_version"]),
        provider_version=(
            str(row["provider_version"])
            if row["provider_version"] is not None
            else None
        ),
        target_generation=int(row["target_generation"]),
        fencing_token=int(row["fencing_token"]),
        requested_at=_required_utc_value(row["requested_at"]),
        started_at=_utc_value(row["started_at"]),
        completed_at=_utc_value(row["completed_at"]),
        deadline_at=_required_utc_value(row["deadline_at"]),
        duration_ms=(
            int(row["duration_ms"]) if row["duration_ms"] is not None else None
        ),
        payload_digest=(
            str(row["payload_digest"]) if row["payload_digest"] is not None else None
        ),
        outcome_code=(
            str(row["outcome_code"]) if row["outcome_code"] is not None else None
        ),
        error_code=(str(row["error_code"]) if row["error_code"] is not None else None),
        observation_ids=_observation_ids(connection, str(row["run_id"])),
    )


def _select_run(connection: Connection, run_id: str) -> RowMapping | None:
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_run WHERE run_id=?", (run_id,)
        )
        .mappings()
        .one_or_none()
    )
    return row


class SqliteCollectionRepositoryV1:
    """Durably admits and finalizes fenced runs without provider I/O."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def _finalize_budget(
        self, connection: Connection, run_id: OpaqueIdV1, instant_text: str
    ) -> None:
        """Apply the ordinary conservative budget rule inside finalization."""
        connection.exec_driver_sql(
            "UPDATE collection_budget_reservation SET state=CASE "
            "WHEN state='dispatched' THEN 'expired_conservative' "
            "ELSE 'released' END, updated_at=? WHERE run_id=?",
            (instant_text, run_id.value),
        )

    def _on_admitted(
        self, connection: Connection, admission: CollectionRunAdmissionV1OrV2
    ) -> None:
        """Internal adapter hook; ordinary M04 admissions need no extra write."""

    def admit_run(
        self, admission: CollectionRunAdmissionV1OrV2
    ) -> CollectionRunViewV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    existing = _select_run(connection, admission.run_id.value)
                    if existing is not None:
                        if existing["request_digest"] != admission.request_digest:
                            connection.rollback()
                            raise CollectionRepositoryErrorV1(
                                "collection_idempotency_conflict"
                            )
                        _require_cloud_run_target(connection, admission)
                        result = _run_view(connection, existing)
                        self._on_admitted(connection, admission)
                        connection.commit()
                        return result
                    if (
                        admission.trigger == "manual"
                        and admission.request_principal_id is not None
                        and admission.idempotency_key_digest is not None
                    ):
                        prior_request = (
                            connection.exec_driver_sql(
                                "SELECT request_fingerprint, linked_run_id FROM "
                                "collection_request WHERE principal_id=? AND "
                                "operation_family=? AND idempotency_key_digest=?",
                                (
                                    admission.request_principal_id.value,
                                    admission.operation_family,
                                    admission.idempotency_key_digest,
                                ),
                            )
                            .mappings()
                            .one_or_none()
                        )
                        if prior_request is not None:
                            if (
                                prior_request["request_fingerprint"]
                                != admission.request_digest
                            ):
                                connection.rollback()
                                raise CollectionRepositoryErrorV1(
                                    "collection_idempotency_conflict"
                                )
                            linked_run_id = prior_request["linked_run_id"]
                            linked = (
                                _select_run(connection, str(linked_run_id))
                                if linked_run_id is not None
                                else None
                            )
                            if linked is None:
                                raise CollectionRepositoryErrorV1(
                                    "collection_repository_unavailable"
                                )
                            result = _run_view(connection, linked)
                            connection.commit()
                            return result
                    schedule = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_schedule WHERE schedule_id=?",
                            (admission.schedule_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    installation_id, provider_target_kind, provider_target_id = (
                        _storage_target(admission)
                    )
                    if schedule is None:
                        instant = _utc_text(admission.requested_at)
                        connection.exec_driver_sql(
                            "INSERT INTO collection_schedule "
                            "(schedule_id, target_key_digest, provider_key, "
                            "installation_id, provider_target_kind, provider_target_id, "
                            "account_id, profile_id, resource_id, "
                            "capability_id, state, activity_class, "
                            "base_interval_seconds, effective_interval_seconds, "
                            "target_generation, next_due_at, not_before_at, "
                            "backoff_kind, backoff_generation, "
                            "consecutive_failure_count, last_attempted_run_id, "
                            "last_successful_run_id, last_terminal_outcome_code, "
                            "record_version, created_at, updated_at) VALUES "
                            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'enabled', 'unknown', 300, "
                            "300, ?, ?, NULL, NULL, 0, 0, ?, NULL, NULL, 1, ?, ?)",
                            (
                                admission.schedule_id.value,
                                admission.target_key_digest,
                                admission.provider_key,
                                installation_id,
                                provider_target_kind,
                                provider_target_id,
                                admission.account_id.value
                                if admission.account_id is not None
                                else None,
                                admission.profile_id.value
                                if admission.profile_id is not None
                                else None,
                                admission.resource_id.value
                                if admission.resource_id is not None
                                else None,
                                admission.capability_id,
                                admission.target_generation,
                                instant,
                                admission.run_id.value,
                                instant,
                                instant,
                            ),
                        )
                    elif (
                        schedule["target_key_digest"] != admission.target_key_digest
                        or schedule["provider_key"] != admission.provider_key
                        or schedule["installation_id"] != installation_id
                        or schedule["provider_target_kind"] != provider_target_kind
                        or schedule["provider_target_id"] != provider_target_id
                        or schedule["account_id"]
                        != (
                            admission.account_id.value
                            if admission.account_id is not None
                            else None
                        )
                        or schedule["profile_id"]
                        != (
                            admission.profile_id.value
                            if admission.profile_id is not None
                            else None
                        )
                        or schedule["resource_id"]
                        != (
                            admission.resource_id.value
                            if admission.resource_id is not None
                            else None
                        )
                        or schedule["capability_id"] != admission.capability_id
                        or schedule["target_generation"] > admission.target_generation
                    ):
                        connection.rollback()
                        raise CollectionRepositoryErrorV1(
                            "collection_schedule_conflict"
                        )
                    elif schedule["target_generation"] < admission.target_generation:
                        active_lease = connection.exec_driver_sql(
                            "SELECT 1 FROM collection_lease WHERE schedule_id=? "
                            "LIMIT 1",
                            (admission.schedule_id.value,),
                        ).scalar_one_or_none()
                        if active_lease is not None:
                            connection.rollback()
                            raise CollectionRepositoryErrorV1(
                                "collection_schedule_conflict"
                            )
                        connection.exec_driver_sql(
                            "UPDATE collection_schedule SET target_generation=?, "
                            "next_due_at=?, updated_at=?, record_version=record_version+1 "
                            "WHERE schedule_id=? AND target_generation<?",
                            (
                                admission.target_generation,
                                _utc_text(admission.requested_at),
                                _utc_text(admission.requested_at),
                                admission.schedule_id.value,
                                admission.target_generation,
                            ),
                        )
                    latest_policy = (
                        connection.exec_driver_sql(
                            "SELECT target_generation, registry_revision, source_id, "
                            "manifest_fingerprint, collection_policy_version FROM "
                            "collection_run WHERE schedule_id=? ORDER BY "
                            "target_generation DESC, attempt_ordinal DESC LIMIT 1",
                            (admission.schedule_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if latest_policy is not None and (
                        latest_policy["target_generation"] > admission.target_generation
                        or (
                            latest_policy["target_generation"]
                            == admission.target_generation
                            and (
                                latest_policy["registry_revision"]
                                != admission.registry_revision
                                or latest_policy["source_id"] != admission.source_id
                                or latest_policy["manifest_fingerprint"]
                                != admission.manifest_fingerprint
                                or latest_policy["collection_policy_version"]
                                != admission.collection_policy_version
                            )
                        )
                    ):
                        connection.rollback()
                        raise CollectionRepositoryErrorV1(
                            "collection_generation_conflict"
                        )
                    reserved_units = int(
                        connection.exec_driver_sql(
                            "SELECT coalesce(sum(units), 0) FROM "
                            "collection_budget_reservation WHERE "
                            "scope_key_digest=? AND dimension=? AND unit=? AND "
                            "state IN ('reserved','dispatched',"
                            "'expired_conservative') AND window_end>? AND "
                            "window_start<?",
                            (
                                admission.budget_scope_digest,
                                admission.budget_dimension,
                                admission.budget_unit,
                                _utc_text(admission.budget_window_start),
                                _utc_text(admission.budget_window_end),
                            ),
                        ).scalar_one()
                    )
                    if (
                        reserved_units + admission.budget_units
                        > admission.budget_limit_units
                    ):
                        connection.rollback()
                        raise CollectionRepositoryErrorV1("collection_budget_exhausted")
                    instant = _utc_text(admission.requested_at)
                    requested_capabilities = json.dumps(
                        admission.requested_capability_ids,
                        ensure_ascii=True,
                        separators=(",", ":"),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO collection_request "
                        "(request_id, schedule_id, trigger_kind, operation_family, "
                        "requested_capabilities_json, capability_set_version, "
                        "request_auth_method, principal_id, producer_key, "
                        "producer_event_id, idempotency_key_digest, "
                        "request_fingerprint, requested_at, expires_at, completed_at, "
                        "state, linked_run_id, correlation_id, causation_id, "
                        "safe_code) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, NULL, "
                        "'accepted', ?, ?, ?, NULL)",
                        (
                            admission.request_id.value,
                            admission.schedule_id.value,
                            admission.trigger,
                            admission.operation_family,
                            requested_capabilities,
                            admission.capability_set_version,
                            admission.request_auth_method,
                            admission.request_principal_id.value
                            if admission.request_principal_id is not None
                            else None,
                            admission.idempotency_key_digest,
                            admission.request_digest,
                            instant,
                            _utc_text(admission.deadline_at),
                            admission.run_id.value,
                            admission.correlation_id.value,
                            admission.causation_id.value
                            if admission.causation_id is not None
                            else None,
                        ),
                    )
                    fencing_token = int(
                        connection.exec_driver_sql(
                            "SELECT coalesce(max(fencing_token), 0) + 1 FROM "
                            "collection_run WHERE schedule_id=?",
                            (admission.schedule_id.value,),
                        ).scalar_one()
                    )
                    reservation_id = hashlib.sha256(
                        (
                            f"{admission.run_id.value}\x1f"
                            f"{admission.budget_policy_id}\x1f"
                            f"{admission.budget_dimension}"
                        ).encode()
                    ).hexdigest()
                    connection.exec_driver_sql(
                        "INSERT INTO collection_run "
                        "(run_id, schedule_id, request_digest, provider_key, "
                        "installation_id, provider_target_kind, provider_target_id, "
                        "account_id, profile_id, resource_id, "
                        "capability_id, source_id, adapter_version, "
                        "adapter_protocol_version, manifest_fingerprint, "
                        "collection_policy_version, registry_revision, "
                        "provider_version, trigger_kind, "
                        "primary_request_id, retry_chain_id, attempt_ordinal, "
                        "target_generation, fencing_token, budget_reservation_id, "
                        "payload_schema, "
                        "payload_digest, state, outcome_code, error_code, "
                        "requested_at, queued_at, started_at, completed_at, "
                        "deadline_at, duration_ms, retry_disposition, retry_eligible, "
                        "retry_after, correlation_id, causation_id, record_version) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                        "?, ?, ?, ?, ?, ?, NULL, 'queued', NULL, NULL, ?, ?, NULL, "
                        "NULL, ?, "
                        "NULL, NULL, NULL, NULL, ?, ?, 1)",
                        (
                            admission.run_id.value,
                            admission.schedule_id.value,
                            admission.request_digest,
                            admission.provider_key,
                            installation_id,
                            provider_target_kind,
                            provider_target_id,
                            admission.account_id.value
                            if admission.account_id is not None
                            else None,
                            admission.profile_id.value
                            if admission.profile_id is not None
                            else None,
                            admission.resource_id.value
                            if admission.resource_id is not None
                            else None,
                            admission.capability_id,
                            admission.source_id,
                            admission.adapter_version,
                            admission.adapter_protocol_version,
                            admission.manifest_fingerprint,
                            admission.collection_policy_version,
                            admission.registry_revision,
                            admission.provider_version,
                            admission.trigger,
                            admission.request_id.value,
                            admission.retry_chain_id.value,
                            admission.attempt_ordinal,
                            admission.target_generation,
                            fencing_token,
                            reservation_id,
                            admission.payload_schema,
                            instant,
                            instant,
                            _utc_text(admission.deadline_at),
                            admission.correlation_id.value,
                            admission.causation_id.value
                            if admission.causation_id is not None
                            else None,
                        ),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO collection_scheduler_instance "
                        "(instance_id, service_version, started_at, heartbeat_at, "
                        "stopping_at, completed_at, lifecycle_state, "
                        "last_health_code) VALUES (?, '1.0.0', ?, ?, NULL, NULL, "
                        "'running', NULL) ON CONFLICT(instance_id) DO UPDATE SET "
                        "heartbeat_at=excluded.heartbeat_at, lifecycle_state='running'",
                        (admission.scheduler_instance_id.value, instant, instant),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO collection_lease "
                        "(schedule_id, owner_instance_id, fencing_token, run_id, "
                        "acquired_at, heartbeat_at, expires_at, lease_policy_version) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            admission.schedule_id.value,
                            admission.scheduler_instance_id.value,
                            fencing_token,
                            admission.run_id.value,
                            instant,
                            instant,
                            _utc_text(admission.deadline_at),
                            admission.lease_policy_version,
                        ),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO collection_budget_reservation "
                        "(reservation_id, run_id, constraint_policy_id, "
                        "constraint_policy_version, scope_key_digest, dimension, "
                        "unit, window_start, window_end, units, state, created_at, "
                        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                        "'reserved', ?, ?)",
                        (
                            reservation_id,
                            admission.run_id.value,
                            admission.budget_policy_id,
                            admission.budget_policy_version,
                            admission.budget_scope_digest,
                            admission.budget_dimension,
                            admission.budget_unit,
                            _utc_text(admission.budget_window_start),
                            _utc_text(admission.budget_window_end),
                            admission.budget_units,
                            instant,
                            instant,
                        ),
                    )
                    row = _select_run(connection, admission.run_id.value)
                    if row is None:
                        raise CollectionRepositoryErrorV1(
                            "collection_repository_unavailable"
                        )
                    result = _run_view(connection, row)
                    self._on_admitted(connection, admission)
                    connection.commit()
                    return result
        except CollectionRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError):
            raise CollectionRepositoryErrorV1() from None

    def get_admission_state(self, run_id: OpaqueIdV1) -> tuple[str, str]:
        """Return bounded lease/reservation state without exposing storage rows."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    lease = connection.exec_driver_sql(
                        "SELECT 1 FROM collection_lease WHERE run_id=?",
                        (run_id.value,),
                    ).scalar_one_or_none()
                    budget = connection.exec_driver_sql(
                        "SELECT state FROM collection_budget_reservation "
                        "WHERE run_id=? ORDER BY reservation_id LIMIT 1",
                        (run_id.value,),
                    ).scalar_one_or_none()
                    if budget is None:
                        raise CollectionRepositoryErrorV1(
                            "collection_admission_not_found"
                        )
                    return ("active" if lease is not None else "released", str(budget))
        except CollectionRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError):
            raise CollectionRepositoryErrorV1() from None

    def get_run(self, run_id: OpaqueIdV1) -> CollectionRunViewV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = _select_run(connection, run_id.value)
                    if row is None:
                        raise CollectionRepositoryErrorV1("collection_run_not_found")
                    return _run_view(connection, row)
        except CollectionRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError):
            raise CollectionRepositoryErrorV1() from None

    def claim_expired_committing_runs(
        self,
        *,
        provider_key: str,
        capability_id: str,
        source_id: str,
        as_of: datetime,
        owner_stale_before: datetime,
        recovery_instance_id: OpaqueIdV1,
        recovery_lease_expires_at: datetime,
        limit: int,
    ) -> tuple[CollectionRunViewV1, ...]:
        """Atomically re-fence an oldest-first expired/stale recovery batch."""
        if (
            not provider_key
            or not capability_id
            or not source_id
            or as_of.utcoffset() != timedelta(0)
            or owner_stale_before.utcoffset() != timedelta(0)
            or recovery_lease_expires_at.utcoffset() != timedelta(0)
            or owner_stale_before > as_of
            or recovery_lease_expires_at <= as_of
            or recovery_lease_expires_at > as_of + timedelta(minutes=1)
            or type(limit) is not int
            or not 1 <= limit <= 64
        ):
            raise CollectionRepositoryErrorV1("collection_query_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    instant = _utc_text(as_of)
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT r.* FROM collection_run AS r "
                            "JOIN collection_lease AS l ON l.run_id=r.run_id "
                            "JOIN collection_scheduler_instance AS owner "
                            "ON owner.instance_id=l.owner_instance_id "
                            "WHERE r.state='committing' AND r.provider_key=? "
                            "AND r.capability_id=? AND r.source_id=? "
                            "AND l.expires_at<=? AND owner.heartbeat_at<=? "
                            "AND l.owner_instance_id<>? "
                            "ORDER BY r.requested_at, r.run_id LIMIT ?",
                            (
                                provider_key,
                                capability_id,
                                source_id,
                                _utc_text(as_of),
                                _utc_text(owner_stale_before),
                                recovery_instance_id.value,
                                limit,
                            ),
                        )
                        .mappings()
                        .all()
                    )
                    if rows:
                        connection.exec_driver_sql(
                            "INSERT INTO collection_scheduler_instance "
                            "(instance_id, service_version, started_at, heartbeat_at, "
                            "stopping_at, completed_at, lifecycle_state, "
                            "last_health_code) VALUES (?, '1.0.0', ?, ?, NULL, NULL, "
                            "'reconciling', NULL) ON CONFLICT(instance_id) DO UPDATE SET "
                            "heartbeat_at=excluded.heartbeat_at, stopping_at=NULL, "
                            "completed_at=NULL, lifecycle_state='reconciling', "
                            "last_health_code=NULL",
                            (recovery_instance_id.value, instant, instant),
                        )
                    claimed: list[CollectionRunViewV1] = []
                    for row in rows:
                        prior_fence = int(row["fencing_token"])
                        next_fence = int(
                            connection.exec_driver_sql(
                                "SELECT coalesce(max(fencing_token), 0) + 1 FROM "
                                "collection_run WHERE schedule_id=?",
                                (row["schedule_id"],),
                            ).scalar_one()
                        )
                        if next_fence <= prior_fence:
                            raise CollectionRepositoryErrorV1(
                                "collection_fencing_conflict"
                            )
                        lease_result = connection.exec_driver_sql(
                            "UPDATE collection_lease SET owner_instance_id=?, "
                            "fencing_token=?, acquired_at=?, heartbeat_at=?, "
                            "expires_at=? WHERE run_id=? AND fencing_token=? "
                            "AND expires_at<=?",
                            (
                                recovery_instance_id.value,
                                next_fence,
                                instant,
                                instant,
                                _utc_text(recovery_lease_expires_at),
                                row["run_id"],
                                prior_fence,
                                instant,
                            ),
                        )
                        if lease_result.rowcount != 1:
                            raise CollectionRepositoryErrorV1(
                                "collection_fencing_conflict"
                            )
                        run_result = connection.exec_driver_sql(
                            "UPDATE collection_run SET fencing_token=?, "
                            "record_version=record_version+1 WHERE run_id=? "
                            "AND state='committing' AND fencing_token=?",
                            (next_fence, row["run_id"], prior_fence),
                        )
                        if run_result.rowcount != 1:
                            raise CollectionRepositoryErrorV1(
                                "collection_fencing_conflict"
                            )
                        claimed_row = _select_run(connection, str(row["run_id"]))
                        if claimed_row is None:
                            raise CollectionRepositoryErrorV1(
                                "collection_repository_unavailable"
                            )
                        claimed.append(_run_view(connection, claimed_row))
                    connection.commit()
                    return tuple(claimed)
        except CollectionRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CollectionRepositoryErrorV1() from None

    def get_latest_source_run(
        self,
        provider_key: str,
        capability_id: str,
        source_id: str,
        as_of: datetime,
        *,
        account_id: OpaqueIdV1 | None = None,
    ) -> CollectionRunViewV1 | None:
        if as_of.utcoffset() != timedelta(0):
            raise CollectionRepositoryErrorV1("collection_query_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_run WHERE provider_key=? "
                            "AND capability_id=? AND source_id=? AND requested_at<=? "
                            "AND (? IS NULL OR account_id=?) "
                            "ORDER BY requested_at DESC, run_id LIMIT 1",
                            (
                                provider_key,
                                capability_id,
                                source_id,
                                _utc_text(as_of),
                                account_id.value if account_id else None,
                                account_id.value if account_id else None,
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return _run_view(connection, row) if row is not None else None
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CollectionRepositoryErrorV1() from None

    def list_runs(
        self,
        provider_key: str | None,
        account_id: OpaqueIdV1 | None,
        as_of: datetime,
        page_size: int,
        after_key: str | None = None,
    ) -> tuple[CollectionRunViewV1, ...]:
        if (
            as_of.utcoffset() != timedelta(0)
            or type(page_size) is not int
            or not 1 <= page_size <= 500
        ):
            raise CollectionRepositoryErrorV1("collection_query_invalid")
        clauses = ["requested_at<=?"]
        parameters: list[object] = [_utc_text(as_of)]
        if provider_key is not None:
            clauses.append("provider_key=?")
            parameters.append(provider_key)
        if account_id is not None:
            clauses.append("account_id=?")
            parameters.append(account_id.value)
        if after_key is not None:
            clauses.append(
                "(requested_at < (SELECT requested_at FROM collection_run WHERE run_id=?) "
                "OR (requested_at = (SELECT requested_at FROM collection_run WHERE run_id=?) AND run_id>?))"
            )
            parameters.extend((after_key, after_key, after_key))
        parameters.append(page_size)
        query = (
            "SELECT * FROM collection_run WHERE "
            + " AND ".join(clauses)
            + " ORDER BY requested_at DESC, run_id LIMIT ?"
        )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(query, tuple(parameters))
                        .mappings()
                        .all()
                    )
                    return tuple(_run_view(connection, row) for row in rows)
        except CollectionRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CollectionRepositoryErrorV1() from None

    def mark_running(
        self, run_id: OpaqueIdV1, started_at: datetime, *, fencing_token: int
    ) -> None:
        self._transition(
            run_id,
            expected="queued",
            state="running",
            instant=started_at,
            terminal_code=None,
            receipt=None,
            fencing_token=fencing_token,
        )

    def mark_committing(
        self,
        run_id: OpaqueIdV1,
        *,
        fencing_token: int,
        payload_digest: str,
        committing_at: datetime,
        terminal_state: str,
    ) -> None:
        if terminal_state not in {"succeeded", "partial"}:
            raise CollectionRepositoryErrorV1("collection_terminal_state_invalid")
        self._transition(
            run_id,
            expected="running",
            state="committing",
            instant=committing_at,
            terminal_code=terminal_state,
            receipt=None,
            fencing_token=fencing_token,
            payload_digest=payload_digest,
        )

    def finalize_committed(
        self,
        receipt: CollectionCommitReceiptV1,
        *,
        terminal_state: str,
        completed_at: datetime,
        fencing_token: int,
    ) -> None:
        if terminal_state not in {"succeeded", "partial"}:
            raise CollectionRepositoryErrorV1("collection_terminal_state_invalid")
        self._transition(
            receipt.run_id,
            expected="committing",
            state=terminal_state,
            instant=completed_at,
            terminal_code=terminal_state,
            receipt=receipt,
            fencing_token=fencing_token,
        )

    def finalize_before_dispatch(
        self, failure: CollectionFailedV1, *, fencing_token: int
    ) -> None:
        """Close a queued run proven not to have started provider dispatch."""
        self._transition(
            failure.run_id,
            expected="queued",
            state=failure.terminal_state,
            instant=failure.completed_at,
            terminal_code=failure.error_code,
            receipt=None,
            fencing_token=fencing_token,
        )

    def finalize_failed(
        self,
        failure: CollectionFailedV1,
        *,
        fencing_token: int,
        provider_policy: CollectionFailurePolicyV1 | None = None,
    ) -> None:
        self._transition(
            failure.run_id,
            expected="running",
            state=failure.terminal_state,
            instant=failure.completed_at,
            terminal_code=failure.error_code,
            receipt=None,
            fencing_token=fencing_token,
            provider_policy=provider_policy,
        )

    def finalize_interrupted(
        self, failure: CollectionFailedV1, *, fencing_token: int
    ) -> None:
        self._transition(
            failure.run_id,
            expected="committing",
            state=failure.terminal_state,
            instant=failure.completed_at,
            terminal_code=failure.error_code,
            receipt=None,
            fencing_token=fencing_token,
        )

    def _transition(
        self,
        run_id: OpaqueIdV1,
        *,
        expected: str,
        state: str,
        instant: datetime,
        terminal_code: str | None,
        receipt: CollectionCommitReceiptV1 | None,
        fencing_token: int,
        payload_digest: str | None = None,
        provider_policy: CollectionFailurePolicyV1 | None = None,
    ) -> None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = _select_run(connection, run_id.value)
                    if row is None:
                        raise CollectionRepositoryErrorV1("collection_run_not_found")
                    if row["state"] != expected:
                        raise CollectionRepositoryErrorV1(
                            "collection_transition_conflict"
                        )
                    fence = connection.exec_driver_sql(
                        "SELECT l.fencing_token FROM collection_lease AS l "
                        "JOIN collection_schedule AS s ON s.schedule_id=l.schedule_id "
                        "WHERE l.run_id=? AND l.schedule_id=? AND "
                        "s.target_generation=?",
                        (
                            run_id.value,
                            row["schedule_id"],
                            row["target_generation"],
                        ),
                    ).scalar_one_or_none()
                    if fence != fencing_token or row["fencing_token"] != fencing_token:
                        raise CollectionRepositoryErrorV1("collection_fencing_conflict")
                    instant_text = _utc_text(instant)
                    if receipt is None:
                        connection.exec_driver_sql(
                            "UPDATE collection_run SET state=?, "
                            "started_at=CASE WHEN ?='running' THEN ? ELSE "
                            "started_at END, "
                            "completed_at=CASE WHEN ? IN ('running','committing') "
                            "THEN NULL ELSE ? END, "
                            "payload_digest=CASE WHEN ?='committing' THEN ? ELSE "
                            "payload_digest END, "
                            "outcome_code=CASE WHEN ?='running' THEN NULL ELSE ? END, "
                            "error_code=CASE WHEN ? IN ('failed','blocked','cancelled',"
                            "'unsupported') THEN ? ELSE NULL END, "
                            "duration_ms=CASE WHEN ? IN ('failed','blocked',"
                            "'cancelled','unsupported') THEN CAST((julianday(?) - "
                            "julianday(started_at))*86400000 AS INTEGER) ELSE "
                            "duration_ms END, record_version=record_version+1 "
                            "WHERE run_id=?",
                            (
                                state,
                                state,
                                instant_text,
                                state,
                                instant_text,
                                state,
                                payload_digest,
                                state,
                                terminal_code,
                                state,
                                terminal_code,
                                state,
                                instant_text,
                                run_id.value,
                            ),
                        )
                        if provider_policy is not None:
                            retry = provider_policy.retry
                            advised_after = (
                                instant + timedelta(seconds=retry.delay_seconds)
                                if retry.delay_seconds is not None
                                else None
                            )
                            connection.exec_driver_sql(
                                "UPDATE collection_run SET provider_outcome_state=?, "
                                "retry_disposition=?,retry_eligible=?,retry_after=? "
                                "WHERE run_id=?",
                                (
                                    provider_policy.provider_outcome,
                                    retry.disposition,
                                    int(retry.disposition == "after_delay"),
                                    _utc_text(advised_after)
                                    if advised_after is not None
                                    else None,
                                    run_id.value,
                                ),
                            )
                        if state == "running":
                            connection.exec_driver_sql(
                                "UPDATE collection_budget_reservation SET "
                                "state='dispatched', updated_at=? WHERE run_id=? "
                                "AND state='reserved'",
                                (instant_text, run_id.value),
                            )
                    else:
                        if (
                            receipt.run_id != run_id
                            or receipt.target_generation != row["target_generation"]
                            or receipt.capability_id != row["capability_id"]
                            or receipt.payload_schema != row["payload_schema"]
                            or receipt.payload_digest != row["payload_digest"]
                        ):
                            raise CollectionRepositoryErrorV1(
                                "collection_receipt_mismatch"
                            )
                        connection.exec_driver_sql(
                            "UPDATE collection_run SET state=?, completed_at=?, "
                            "payload_digest=?, outcome_code=?, error_code=NULL, "
                            "duration_ms=CAST((julianday(?) - "
                            "julianday(started_at))*86400000 AS INTEGER), "
                            "record_version=record_version+1 WHERE run_id=?",
                            (
                                state,
                                instant_text,
                                receipt.payload_digest,
                                terminal_code,
                                instant_text,
                                run_id.value,
                            ),
                        )
                        for observation_id in receipt.observation_ids:
                            connection.exec_driver_sql(
                                "INSERT INTO collection_run_observation_ref "
                                "(run_id, consumer_key, consumer_version, "
                                "observation_id, receipt_version) VALUES "
                                "(?, ?, ?, ?, ?)",
                                (
                                    run_id.value,
                                    receipt.consumer_key,
                                    receipt.consumer_version,
                                    observation_id.value,
                                    receipt.receipt_version,
                                ),
                            )
                    if state in {
                        "succeeded",
                        "partial",
                        "failed",
                        "blocked",
                        "cancelled",
                        "unsupported",
                    }:
                        self._finalize_budget(connection, run_id, instant_text)
                        connection.exec_driver_sql(
                            "DELETE FROM collection_lease WHERE run_id=? AND "
                            "fencing_token=?",
                            (run_id.value, fencing_token),
                        )
                        connection.exec_driver_sql(
                            "UPDATE collection_schedule SET last_attempted_run_id=?, "
                            "last_successful_run_id=CASE WHEN ? IN "
                            "('succeeded','partial') THEN ? ELSE "
                            "last_successful_run_id END, "
                            "last_terminal_outcome_code=?, updated_at=?, "
                            "record_version=record_version+1 WHERE schedule_id=?",
                            (
                                run_id.value,
                                state,
                                run_id.value,
                                terminal_code,
                                instant_text,
                                row["schedule_id"],
                            ),
                        )
                        connection.exec_driver_sql(
                            "UPDATE collection_request SET state='completed', "
                            "completed_at=?, safe_code=? WHERE request_id=? AND "
                            "linked_run_id=?",
                            (
                                instant_text,
                                terminal_code,
                                row["primary_request_id"],
                                run_id.value,
                            ),
                        )
                        sequence = int(
                            connection.exec_driver_sql(
                                "SELECT coalesce(max(stream_sequence), 0) + 1 "
                                "FROM collection_event_outbox WHERE stream_id=?",
                                (row["schedule_id"],),
                            ).scalar_one()
                        )
                        event_id = hashlib.sha256(
                            f"{row['schedule_id']}\x1f{state}\x1f{sequence}".encode()
                        ).hexdigest()
                        event_payload = json.dumps(
                            {"run_id": run_id.value, "state": state},
                            ensure_ascii=True,
                            separators=(",", ":"),
                            sort_keys=True,
                        )
                        connection.exec_driver_sql(
                            "INSERT INTO collection_event_outbox "
                            "(event_id, event_type, event_schema, stream_id, "
                            "stream_sequence, subject_id, correlation_id, "
                            "causation_id, payload_json, occurred_at, recorded_at, "
                            "available_at) VALUES (?, 'collection.run_terminal.v1', "
                            "'collection.run_terminal.v1', ?, ?, ?, ?, ?, ?, ?, "
                            "?, ?)",
                            (
                                event_id,
                                row["schedule_id"],
                                sequence,
                                run_id.value,
                                row["correlation_id"],
                                row["causation_id"],
                                event_payload,
                                instant_text,
                                instant_text,
                                instant_text,
                            ),
                        )
                    connection.commit()
        except CollectionRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError):
            raise CollectionRepositoryErrorV1() from None
