"""Durable single-instance Ollama cloud request admission over real SQLite."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunAdmissionV1,
    OllamaCloudAdmissionDecisionV1,
    OllamaCloudRateGateViewV1,
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
    OllamaCloudRequestLeaseV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
    after_ollama_attempt,
    reserve_after_lease,
)

_GATE_ID = "ollama-cloud-balance-v1"
_PROVIDER_KEY = "ollama"
_CAPABILITY_ID = "subscription.quota"


class OllamaCloudAdmissionRepositoryErrorV1(ValueError):
    """A bounded failure that never includes SQL, paths, or provider data."""

    def __init__(self, code: str = "ollama_cloud_admission_unavailable") -> None:
        self.code = code
        super().__init__(code)


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise OllamaCloudAdmissionRepositoryErrorV1(
            "ollama_cloud_admission_time_invalid"
        )
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _utc_value(value: object) -> datetime:
    if not isinstance(value, str):
        raise OllamaCloudAdmissionRepositoryErrorV1()
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise OllamaCloudAdmissionRepositoryErrorV1() from None
    if result.utcoffset() != timedelta(0):
        raise OllamaCloudAdmissionRepositoryErrorV1()
    return result.astimezone(UTC)


def _gate_row(connection: Connection) -> RowMapping | None:
    return (
        connection.exec_driver_sql(
            "SELECT * FROM collection_ollama_cloud_gate WHERE gate_id=?",
            (_GATE_ID,),
        )
        .mappings()
        .one_or_none()
    )


def _admission_row(connection: Connection, admission_id: str) -> RowMapping | None:
    return (
        connection.exec_driver_sql(
            "SELECT * FROM collection_ollama_cloud_admission WHERE admission_id=?",
            (admission_id,),
        )
        .mappings()
        .one_or_none()
    )


def _lease(row: RowMapping, gate_record_version: int) -> OllamaCloudRequestLeaseV1:
    return OllamaCloudRequestLeaseV1(
        admission_id=OpaqueIdV1(str(row["admission_id"])),
        scheduler_instance_id=OpaqueIdV1(str(row["scheduler_instance_id"])),
        schedule_id=OpaqueIdV1(str(row["schedule_id"])),
        account_id=OpaqueIdV1(str(row["account_id"])),
        fencing_token=int(row["fencing_token"]),
        started_at=_utc_value(row["started_at"]),
        lease_expires_at=_utc_value(row["lease_expires_at"]),
        next_allowed_at=_utc_value(row["next_allowed_at"]),
        gate_record_version=gate_record_version,
    )


def _gate_view(row: RowMapping) -> OllamaCloudRateGateViewV1:
    return OllamaCloudRateGateViewV1(
        next_allowed_at=_utc_value(row["next_allowed_at"]),
        fair_cursor_schedule_id=(
            OpaqueIdV1(str(row["fair_cursor_schedule_id"]))
            if row["fair_cursor_schedule_id"] is not None
            else None
        ),
        active_admission_id=(
            OpaqueIdV1(str(row["active_admission_id"]))
            if row["active_admission_id"] is not None
            else None
        ),
        consecutive_rate_limits=int(row["consecutive_rate_limits"]),
        fencing_token=int(row["fencing_token"]),
        record_version=int(row["record_version"]),
        updated_at=_utc_value(row["updated_at"]),
    )


def _same_acquire(row: RowMapping, request: OllamaCloudRequestAcquireV1) -> bool:
    return (
        row["scheduler_instance_id"] == request.scheduler_instance_id.value
        and _utc_value(row["started_at"]) == request.requested_at
        and _utc_value(row["lease_expires_at"]) == request.lease_expires_at
        and int(row["admission_jitter_seconds"]) == request.jitter_seconds
    )


def ensure_ollama_lease_in_transaction(
    connection: Connection, lease: OllamaCloudRequestLeaseV1, now: datetime
) -> None:
    """Fence a capacity commit against the same active durable cloud lease."""
    if not connection.in_transaction():
        raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_transaction_required")
    row = _admission_row(connection, lease.admission_id.value)
    gate = _gate_row(connection)
    if (
        row is None
        or gate is None
        or row["state"] != "active"
        or gate["active_admission_id"] != lease.admission_id.value
        or row["scheduler_instance_id"] != lease.scheduler_instance_id.value
        or row["schedule_id"] != lease.schedule_id.value
        or row["account_id"] != lease.account_id.value
        or int(row["fencing_token"]) != lease.fencing_token
        or int(gate["fencing_token"]) != lease.fencing_token
        or _utc_value(row["started_at"]) != lease.started_at
        or _utc_value(row["lease_expires_at"]) != lease.lease_expires_at
        or now < lease.started_at
        or now > lease.lease_expires_at
    ):
        raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")


def ensure_ollama_run_in_transaction(
    connection: Connection,
    lease: OllamaCloudRequestLeaseV1,
    run: CollectionRunAdmissionV1,
    payload_digest: str,
    now: datetime,
) -> None:
    """Require the actual M04 run in committing state, bound to the rate lease."""
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_run WHERE run_id=?", (run.run_id.value,)
        )
        .mappings()
        .one_or_none()
    )
    run_lease = (
        connection.exec_driver_sql(
            "SELECT * FROM collection_lease WHERE schedule_id=?",
            (lease.schedule_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if (
        not connection.in_transaction()
        or row is None
        or run_lease is None
        or run_lease["run_id"] != run.run_id.value
        or run_lease["owner_instance_id"] != run.scheduler_instance_id.value
        or run_lease["fencing_token"] != row["fencing_token"]
        or _utc_value(run_lease["expires_at"]) < now
        or row["state"] != "committing"
        or row["schedule_id"] != lease.schedule_id.value
        or row["account_id"] != lease.account_id.value
        or row["provider_key"] != "ollama"
        or row["capability_id"] != "subscription.quota"
        or row["source_id"] != "ollama.cloud.balance.v1"
        or row["installation_id"] != run.installation_id.value
        or row["resource_id"] != (run.resource_id.value if run.resource_id else None)
        or row["correlation_id"] != run.correlation_id.value
        or row["target_generation"] != run.target_generation
        or row["registry_revision"] != run.registry_revision
        or row["payload_schema"] != run.payload_schema
        or row["payload_digest"] != payload_digest
    ):
        raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_run_fencing_conflict")


class SqliteOllamaCloudAdmissionRepositoryV1:
    """Atomically rotate due accounts through one durable request gate."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def assert_active(self, lease: OllamaCloudRequestLeaseV1, now: datetime) -> None:
        """Check the acquired gate before starting the one provider request."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    ensure_ollama_lease_in_transaction(connection, lease, now)
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def register_schedule(self, admission: CollectionRunAdmissionV1) -> None:
        """Register one genuine target for fair selection without creating a run."""
        if (
            admission.provider_key != _PROVIDER_KEY
            or admission.capability_id != _CAPABILITY_ID
            or admission.source_id != "ollama.cloud.balance.v1"
            or admission.trigger != "scheduled"
            or admission.account_id is None
            or admission.profile_id is None
            or admission.resource_id is None
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_schedule_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_schedule WHERE schedule_id=?",
                            (admission.schedule_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    target = (
                        admission.target_key_digest,
                        admission.provider_key,
                        admission.installation_id.value,
                        admission.account_id.value,
                        admission.profile_id.value,
                        admission.resource_id.value,
                        admission.capability_id,
                    )
                    if row is None:
                        instant = _utc_text(admission.requested_at)
                        connection.exec_driver_sql(
                            "INSERT INTO collection_schedule "
                            "(schedule_id,target_key_digest,provider_key,installation_id,"
                            "account_id,profile_id,resource_id,capability_id,state,activity_class,"
                            "base_interval_seconds,effective_interval_seconds,target_generation,"
                            "next_due_at,not_before_at,backoff_kind,backoff_generation,"
                            "consecutive_failure_count,last_attempted_run_id,last_successful_run_id,"
                            "last_terminal_outcome_code,record_version,created_at,"
                            "updated_at) "
                            "VALUES (?,?,?,?,?,?,?,?,'enabled','unknown',300,300,?,?"
                            ",NULL,NULL,"
                            "0,0,NULL,NULL,NULL,1,?,?)",
                            (
                                admission.schedule_id.value,
                                *target,
                                admission.target_generation,
                                instant,
                                instant,
                                instant,
                            ),
                        )
                    else:
                        actual = tuple(
                            row[key]
                            for key in (
                                "target_key_digest",
                                "provider_key",
                                "installation_id",
                                "account_id",
                                "profile_id",
                                "resource_id",
                                "capability_id",
                            )
                        )
                        if (
                            actual != target
                            or row["target_generation"] != admission.target_generation
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_schedule_conflict"
                            )
                    connection.commit()
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def acquire(
        self, request: OllamaCloudRequestAcquireV1
    ) -> OllamaCloudAdmissionDecisionV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    result = self._acquire(connection, request)
                    connection.commit()
                    return result
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def _acquire(
        self, connection: Connection, request: OllamaCloudRequestAcquireV1
    ) -> OllamaCloudAdmissionDecisionV1:
        requested_text = _utc_text(request.requested_at)
        existing = _admission_row(connection, request.admission_id.value)
        gate = _gate_row(connection)
        if existing is not None:
            if gate is None or not _same_acquire(existing, request):
                raise OllamaCloudAdmissionRepositoryErrorV1(
                    "ollama_cloud_admission_conflict"
                )
            next_allowed = _utc_value(existing["next_allowed_at"])
            if existing["state"] == "active":
                if gate["active_admission_id"] != request.admission_id.value:
                    raise OllamaCloudAdmissionRepositoryErrorV1()
                return OllamaCloudAdmissionDecisionV1(
                    "replayed_active",
                    None,
                    max(
                        _utc_value(existing["lease_expires_at"]),
                        next_allowed,
                    ),
                )
            if existing["state"] in {"completed", "expired"}:
                return OllamaCloudAdmissionDecisionV1(
                    "replayed_terminal", None, next_allowed
                )
            raise OllamaCloudAdmissionRepositoryErrorV1()

        if gate is None:
            connection.exec_driver_sql(
                "INSERT INTO collection_ollama_cloud_gate "
                "(gate_id,provider_key,capability_id,next_allowed_at,"
                "fair_cursor_schedule_id,active_admission_id,"
                "consecutive_rate_limits,fencing_token,record_version,updated_at) "
                "VALUES (?, ?, ?, ?, NULL, NULL, 0, 0, 1, ?)",
                (
                    _GATE_ID,
                    _PROVIDER_KEY,
                    _CAPABILITY_ID,
                    requested_text,
                    requested_text,
                ),
            )
            gate = _gate_row(connection)
            if gate is None:
                raise OllamaCloudAdmissionRepositoryErrorV1()
        elif request.requested_at < _utc_value(gate["updated_at"]):
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_clock_rollback")

        active_id = gate["active_admission_id"]
        if active_id is not None:
            active = _admission_row(connection, str(active_id))
            if active is None or active["state"] != "active":
                raise OllamaCloudAdmissionRepositoryErrorV1()
            active_expiry = _utc_value(active["lease_expires_at"])
            next_allowed = _utc_value(gate["next_allowed_at"])
            if request.requested_at < active_expiry:
                return OllamaCloudAdmissionDecisionV1(
                    "busy", None, max(active_expiry, next_allowed)
                )
            # Fencing protects commits, not an HTTP request still in flight.
            # Never re-admit solely because a clock-based lease expired: an
            # unobserved late 429 could otherwise lose its retry deadline.
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_expired_request_unresolved"
            )

        next_allowed = _utc_value(gate["next_allowed_at"])
        if request.requested_at < next_allowed:
            return OllamaCloudAdmissionDecisionV1("not_due", None, next_allowed)

        cursor = gate["fair_cursor_schedule_id"]
        candidate = (
            connection.exec_driver_sql(
                "SELECT s.schedule_id,s.account_id,s.effective_interval_seconds "
                "FROM collection_schedule AS s LEFT JOIN collection_lease AS l "
                "ON l.schedule_id=s.schedule_id WHERE s.provider_key=? AND "
                "s.capability_id=? AND s.account_id IS NOT NULL AND "
                "s.state='enabled' AND s.next_due_at<=? AND "
                "(s.not_before_at IS NULL OR s.not_before_at<=?) AND "
                "l.schedule_id IS NULL ORDER BY CASE WHEN ? IS NULL THEN 0 "
                "WHEN s.schedule_id>? THEN 0 ELSE 1 END,s.schedule_id LIMIT 1",
                (
                    _PROVIDER_KEY,
                    _CAPABILITY_ID,
                    requested_text,
                    requested_text,
                    cursor,
                    cursor,
                ),
            )
            .mappings()
            .one_or_none()
        )
        if candidate is None:
            return OllamaCloudAdmissionDecisionV1("no_candidate", None, None)

        try:
            reserved_until = reserve_after_lease(
                request.lease_expires_at, request.jitter_seconds
            )
        except ValueError as error:
            code = str(error)
            if not code.startswith("ollama_"):
                code = "ollama_cloud_admission_unavailable"
            raise OllamaCloudAdmissionRepositoryErrorV1(code) from None
        fencing_token = int(gate["fencing_token"]) + 1
        gate_version = int(gate["record_version"]) + 1
        reserved_text = _utc_text(reserved_until)
        connection.exec_driver_sql(
            "INSERT INTO collection_ollama_cloud_admission "
            "(admission_id,gate_id,scheduler_instance_id,schedule_id,account_id,"
            "fencing_token,state,started_at,lease_expires_at,"
            "admission_jitter_seconds,response_received_at,outcome,"
            "retry_after_seconds,completion_jitter_seconds,next_allowed_at) "
            "VALUES (?,?,?,?,?,?,'active',?,?,?,NULL,NULL,NULL,NULL,?)",
            (
                request.admission_id.value,
                _GATE_ID,
                request.scheduler_instance_id.value,
                candidate["schedule_id"],
                candidate["account_id"],
                fencing_token,
                requested_text,
                _utc_text(request.lease_expires_at),
                request.jitter_seconds,
                reserved_text,
            ),
        )
        updated = connection.exec_driver_sql(
            "UPDATE collection_ollama_cloud_gate SET next_allowed_at=?,"
            "fair_cursor_schedule_id=?,active_admission_id=?,fencing_token=?,"
            "record_version=?,updated_at=? WHERE gate_id=? AND record_version=? "
            "AND active_admission_id IS NULL",
            (
                reserved_text,
                candidate["schedule_id"],
                request.admission_id.value,
                fencing_token,
                gate_version,
                requested_text,
                _GATE_ID,
                gate["record_version"],
            ),
        )
        if updated.rowcount != 1:
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_admission_conflict"
            )
        schedule_due = request.requested_at + timedelta(
            seconds=int(candidate["effective_interval_seconds"])
        )
        connection.exec_driver_sql(
            "UPDATE collection_schedule SET next_due_at=?,updated_at=?,"
            "record_version=record_version+1 WHERE schedule_id=?",
            (_utc_text(schedule_due), requested_text, candidate["schedule_id"]),
        )
        row = _admission_row(connection, request.admission_id.value)
        if row is None:
            raise OllamaCloudAdmissionRepositoryErrorV1()
        return OllamaCloudAdmissionDecisionV1(
            "acquired", _lease(row, gate_version), None
        )

    def complete(
        self, completion: OllamaCloudRequestCompletionV1
    ) -> OllamaCloudRateGateViewV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    result = self._complete(connection, completion)
                    connection.commit()
                    return result
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def _complete(
        self, connection: Connection, completion: OllamaCloudRequestCompletionV1
    ) -> OllamaCloudRateGateViewV1:
        row = _admission_row(connection, completion.admission_id.value)
        gate = _gate_row(connection)
        if row is None or gate is None:
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_admission_not_found"
            )
        if row["state"] == "completed":
            if not self._same_completion(row, completion):
                raise OllamaCloudAdmissionRepositoryErrorV1(
                    "ollama_cloud_completion_conflict"
                )
            return _gate_view(gate)
        if (
            row["state"] != "active"
            or gate["active_admission_id"] != completion.admission_id.value
            or row["scheduler_instance_id"] != completion.scheduler_instance_id.value
            or row["schedule_id"] != completion.schedule_id.value
            or int(row["fencing_token"]) != completion.fencing_token
            or _utc_value(row["started_at"]) != completion.started_at
            or completion.response_received_at > _utc_value(row["lease_expires_at"])
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
        consecutive = (
            min(100, int(gate["consecutive_rate_limits"]) + 1)
            if completion.outcome == "rate_limited"
            else 0
        )
        try:
            policy_next = after_ollama_attempt(
                completion.started_at,
                consecutive,
                completion.retry_after_seconds,
                completion.jitter_seconds,
                response_received_at=completion.response_received_at,
            )
        except ValueError as error:
            code = str(error)
            if code == "ollama_rate_wait_unrepresentable":
                policy_next = datetime.max.replace(tzinfo=UTC)
            else:
                if not code.startswith("ollama_"):
                    code = "ollama_cloud_admission_unavailable"
                raise OllamaCloudAdmissionRepositoryErrorV1(code) from None
        next_allowed = max(_utc_value(gate["next_allowed_at"]), policy_next)
        completed_text = _utc_text(completion.response_received_at)
        next_text = _utc_text(next_allowed)
        connection.exec_driver_sql(
            "UPDATE collection_ollama_cloud_admission SET state='completed',"
            "response_received_at=?,outcome=?,retry_after_seconds=?,"
            "completion_jitter_seconds=?,next_allowed_at=? WHERE admission_id=? "
            "AND state='active'",
            (
                completed_text,
                completion.outcome,
                completion.retry_after_seconds,
                completion.jitter_seconds,
                next_text,
                completion.admission_id.value,
            ),
        )
        updated = connection.exec_driver_sql(
            "UPDATE collection_ollama_cloud_gate SET next_allowed_at=?,"
            "active_admission_id=NULL,consecutive_rate_limits=?,"
            "record_version=record_version+1,updated_at=? WHERE gate_id=? "
            "AND active_admission_id=? AND fencing_token=?",
            (
                next_text,
                consecutive,
                completed_text,
                _GATE_ID,
                completion.admission_id.value,
                completion.fencing_token,
            ),
        )
        if updated.rowcount != 1:
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
        gate = _gate_row(connection)
        if gate is None:
            raise OllamaCloudAdmissionRepositoryErrorV1()
        return _gate_view(gate)

    @staticmethod
    def _same_completion(
        row: RowMapping, completion: OllamaCloudRequestCompletionV1
    ) -> bool:
        return (
            row["scheduler_instance_id"] == completion.scheduler_instance_id.value
            and row["schedule_id"] == completion.schedule_id.value
            and int(row["fencing_token"]) == completion.fencing_token
            and _utc_value(row["started_at"]) == completion.started_at
            and _utc_value(row["response_received_at"])
            == completion.response_received_at
            and row["outcome"] == completion.outcome
            and row["retry_after_seconds"] == completion.retry_after_seconds
            and int(row["completion_jitter_seconds"]) == completion.jitter_seconds
        )
