"""Durable single-instance Ollama cloud request admission over real SQLite."""

# ruff: noqa: E501 -- SQL identity and fence predicates stay explicit.

from datetime import UTC, datetime, timedelta

from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunAdmissionV1,
    CollectionRunAdmissionV1OrV2,
    CollectionRunAdmissionV2,
    OllamaCloudAdmissionDecisionV1,
    OllamaCloudNoResponseCompletionV2,
    OllamaCloudRateGateViewV1,
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
    OllamaCloudRequestLeaseV1,
    OllamaCloudVerificationAcquireV1,
    OllamaCloudVerificationTargetV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
    after_ollama_attempt,
    cloud_schedule_generation_action,
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
    row = (
        connection.exec_driver_sql(
            "SELECT a.*, t.admission_id AS no_response_id, t.terminal_at AS v2_terminal_at, "
            "t.next_allowed_at AS v2_next_allowed_at, t.reason_code AS v2_reason_code, "
            "t.source_state AS v2_source_state, t.dispatch_certainty AS v2_certainty, "
            "t.gate_record_version AS v2_gate_record_version FROM collection_ollama_cloud_admission a "
            "LEFT JOIN collection_cloud_no_response_terminal t ON t.admission_id=a.admission_id "
            "WHERE a.admission_id=?",
            (admission_id,),
        )
        .mappings()
        .one_or_none()
    )
    if row is not None and row["no_response_id"] is not None:
        gate = _gate_row(connection)
        if gate is not None and gate["active_admission_id"] == admission_id:
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
    return row


def _assert_terminal_gate_consistency(connection: Connection) -> None:
    """A V2 terminal must never simultaneously own the active rate gate."""
    conflict = connection.exec_driver_sql(
        "SELECT 1 FROM collection_cloud_no_response_terminal t "
        "JOIN collection_ollama_cloud_gate g ON g.active_admission_id=t.admission_id LIMIT 1"
    ).first()
    if conflict is not None:
        raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")


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
        or _utc_value(row["next_allowed_at"]) != lease.next_allowed_at
        or _utc_value(gate["next_allowed_at"]) != lease.next_allowed_at
        or int(gate["record_version"]) != lease.gate_record_version
        or now < lease.started_at
        or now > lease.lease_expires_at
    ):
        raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")


def bind_ollama_run_in_transaction(
    connection: Connection,
    lease: OllamaCloudRequestLeaseV1,
    run: CollectionRunAdmissionV1OrV2,
    now: datetime,
) -> None:
    """Attach the actual queued M04 run to the reserved rate attempt atomically."""
    ensure_ollama_lease_in_transaction(connection, lease, now)
    row = (
        connection.exec_driver_sql(
            "SELECT r.state,r.account_id,r.schedule_id,l.owner_instance_id "
            "FROM collection_run r JOIN collection_lease l ON l.run_id=r.run_id "
            "WHERE r.run_id=?",
            (run.run_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if (
        row is None
        or row["state"] != "queued"
        or row["account_id"] != lease.account_id.value
        or row["schedule_id"] != lease.schedule_id.value
        or row["owner_instance_id"] != lease.scheduler_instance_id.value
        or run.scheduler_instance_id != lease.scheduler_instance_id
    ):
        raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_run_fencing_conflict")
    changed = connection.exec_driver_sql(
        "UPDATE collection_cloud_attempt_journal SET run_id=? "
        "WHERE admission_id=? AND phase='reserved' AND (run_id IS NULL OR run_id=?)",
        (run.run_id.value, lease.admission_id.value, run.run_id.value),
    )
    if changed.rowcount != 1:
        raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_run_fencing_conflict")


def ensure_ollama_run_in_transaction(
    connection: Connection,
    lease: OllamaCloudRequestLeaseV1,
    run: CollectionRunAdmissionV1OrV2,
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
    cloud_target = (
        (run.provider_target.target_kind, run.provider_target.target_id.value)
        if isinstance(run, CollectionRunAdmissionV2)
        and run.provider_target.target_kind == "cloud_service"
        else None
    )
    storage_installation_id = (
        None
        if cloud_target is not None
        else run.provider_target.target_id.value
        if isinstance(run, CollectionRunAdmissionV2)
        else run.installation_id.value
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
        or run.scheduler_instance_id != lease.scheduler_instance_id
        or run.schedule_id != lease.schedule_id
        or run.account_id != lease.account_id
        or run.provider_key != "ollama"
        or run.capability_id != "subscription.quota"
        or run.source_id != "ollama.cloud.balance.v1"
        or row["schedule_id"] != lease.schedule_id.value
        or row["profile_id"] != (run.profile_id.value if run.profile_id else None)
        or row["request_digest"] != run.request_digest
        or row["manifest_fingerprint"] != run.manifest_fingerprint
        or row["adapter_version"] != run.adapter_version
        or row["adapter_protocol_version"] != run.adapter_protocol_version
        or row["collection_policy_version"] != run.collection_policy_version
        or row["deadline_at"] != _utc_text(run.deadline_at)
        or row["account_id"] != lease.account_id.value
        or row["provider_key"] != "ollama"
        or row["capability_id"] != "subscription.quota"
        or row["source_id"] != "ollama.cloud.balance.v1"
        or row["installation_id"] != storage_installation_id
        or row["provider_target_kind"]
        != (cloud_target[0] if cloud_target is not None else None)
        or row["provider_target_id"]
        != (cloud_target[1] if cloud_target is not None else None)
        or row["resource_id"] != (run.resource_id.value if run.resource_id else None)
        or row["correlation_id"] != run.correlation_id.value
        or row["target_generation"] != run.target_generation
        or row["registry_revision"] != run.registry_revision
        or row["payload_schema"] != run.payload_schema
        or row["payload_digest"] != payload_digest
    ):
        raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_run_fencing_conflict")


class SqliteOllamaCloudRunRepositoryV1(SqliteCollectionRepositoryV1):
    """Narrow M04 port that binds its rate attempt during the admission transaction."""

    def __init__(
        self, reference: DatabaseRefV1, lease: OllamaCloudRequestLeaseV1
    ) -> None:
        super().__init__(reference)
        self._cloud_lease = lease

    def _on_admitted(
        self, connection: Connection, admission: CollectionRunAdmissionV1OrV2
    ) -> None:
        bind_ollama_run_in_transaction(
            connection, self._cloud_lease, admission, datetime.now(UTC)
        )


class SqliteOllamaNoResponseRunRepositoryV1(SqliteCollectionRepositoryV1):
    """M04 finalizer whose budget release is fenced by exact V2 no-request proof."""

    def __init__(self, reference: DatabaseRefV1, admission_id: OpaqueIdV1) -> None:
        super().__init__(reference)
        self._admission_id = admission_id

    def _finalize_budget(
        self, connection: Connection, run_id: OpaqueIdV1, instant_text: str
    ) -> None:
        _assert_terminal_gate_consistency(connection)
        proof = connection.exec_driver_sql(
            "SELECT 1 FROM collection_cloud_no_response_terminal t "
            "JOIN collection_cloud_attempt_journal j ON j.admission_id=t.admission_id "
            "WHERE t.admission_id=? AND t.dispatch_certainty='not_started' AND j.run_id=?",
            (self._admission_id.value, run_id.value),
        ).first()
        if proof is None:
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_no_request_proof_missing"
            )
        connection.exec_driver_sql(
            "UPDATE collection_budget_reservation SET state='released',updated_at=? WHERE run_id=?",
            (instant_text, run_id.value),
        )


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

    def mark_dispatched(self, lease: OllamaCloudRequestLeaseV1, now: datetime) -> None:
        """Persist dispatch before a source worker can start."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    ensure_ollama_lease_in_transaction(connection, lease, now)
                    updated = connection.exec_driver_sql(
                        "UPDATE collection_cloud_attempt_journal SET phase='dispatched' "
                        "WHERE admission_id=? AND phase='reserved' AND run_id IS NOT NULL",
                        (lease.admission_id.value,),
                    )
                    if updated.rowcount != 1:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_dispatch_conflict"
                        )
                    connection.commit()
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def revert_undispatched(self, lease: OllamaCloudRequestLeaseV1) -> None:
        """Undo dispatch marker only from the owner's proven pre-worker path."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = _admission_row(connection, lease.admission_id.value)
                    gate = _gate_row(connection)
                    if (
                        row is None
                        or gate is None
                        or row["state"] != "active"
                        or gate["active_admission_id"] != lease.admission_id.value
                        or int(gate["fencing_token"]) != lease.fencing_token
                        or row["scheduler_instance_id"]
                        != lease.scheduler_instance_id.value
                        or row["schedule_id"] != lease.schedule_id.value
                        or row["account_id"] != lease.account_id.value
                        or int(row["fencing_token"]) != lease.fencing_token
                        or _utc_value(row["started_at"]) != lease.started_at
                        or _utc_value(row["lease_expires_at"]) != lease.lease_expires_at
                        or _utc_value(row["next_allowed_at"]) != lease.next_allowed_at
                        or _utc_value(gate["next_allowed_at"]) != lease.next_allowed_at
                        or int(gate["record_version"]) != lease.gate_record_version
                    ):
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_fencing_conflict"
                        )
                    changed = connection.exec_driver_sql(
                        "UPDATE collection_cloud_attempt_journal SET phase='reserved' "
                        "WHERE admission_id=? AND phase='dispatched'",
                        (lease.admission_id.value,),
                    )
                    if changed.rowcount != 1:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_dispatch_conflict"
                        )
                    connection.commit()
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def record_completion(
        self,
        lease: OllamaCloudRequestLeaseV1,
        completion: OllamaCloudRequestCompletionV1,
        *,
        failure_code: str | None = None,
    ) -> None:
        """Durably record one exact sanitized result before either journal finalizes."""
        permitted = {
            "authorization_unavailable",
            "unauthorized",
            "access_denied",
            "rate_limited",
            "provider_unavailable",
            "unexpected_response",
            "invalid_provider_data",
            "deadline_exceeded",
            "internal_adapter_error",
            "source_not_admitted",
        }
        if (
            (completion.outcome == "succeeded" and failure_code is not None)
            or (completion.outcome != "succeeded" and failure_code not in permitted)
            or (
                (completion.outcome == "rate_limited")
                != (failure_code == "rate_limited")
            )
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_completion_conflict"
            )
        if (
            completion.admission_id != lease.admission_id
            or completion.scheduler_instance_id != lease.scheduler_instance_id
            or completion.schedule_id != lease.schedule_id
            or completion.fencing_token != lease.fencing_token
            or completion.started_at != lease.started_at
            or completion.response_received_at > lease.lease_expires_at
            or datetime.now(UTC) > lease.lease_expires_at
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_completion_conflict"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    if datetime.now(UTC) > lease.lease_expires_at:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_fencing_conflict"
                        )
                    row = _admission_row(connection, lease.admission_id.value)
                    gate = _gate_row(connection)
                    if (
                        row is None
                        or gate is None
                        or row["state"] != "active"
                        or gate["active_admission_id"] != lease.admission_id.value
                        or int(gate["fencing_token"]) != lease.fencing_token
                        or int(row["fencing_token"]) != lease.fencing_token
                        or row["scheduler_instance_id"]
                        != lease.scheduler_instance_id.value
                        or row["schedule_id"] != lease.schedule_id.value
                        or row["account_id"] != lease.account_id.value
                        or _utc_value(row["started_at"]) != lease.started_at
                        or _utc_value(row["lease_expires_at"]) != lease.lease_expires_at
                        or _utc_value(row["next_allowed_at"]) != lease.next_allowed_at
                        or _utc_value(gate["next_allowed_at"]) != lease.next_allowed_at
                        or int(gate["record_version"]) != lease.gate_record_version
                    ):
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_fencing_conflict"
                        )
                    values = (
                        completion.outcome,
                        _utc_text(completion.response_received_at),
                        completion.retry_after_seconds,
                        completion.jitter_seconds,
                        failure_code,
                        completion.admission_id.value,
                    )
                    updated = connection.exec_driver_sql(
                        "UPDATE collection_cloud_attempt_journal SET phase='outcome', outcome=?, "
                        "response_received_at=?, retry_after_seconds=?, completion_jitter_seconds=?, failure_code=? "
                        "WHERE admission_id=? AND phase='dispatched'",
                        values,
                    )
                    if updated.rowcount != 1:
                        existing = connection.exec_driver_sql(
                            "SELECT outcome,response_received_at,retry_after_seconds,completion_jitter_seconds,failure_code "
                            "FROM collection_cloud_attempt_journal WHERE admission_id=? AND phase='outcome'",
                            (completion.admission_id.value,),
                        ).first()
                        if existing is None or tuple(existing) != values[:5]:
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_completion_conflict"
                            )
                    connection.commit()
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def finish_no_response(
        self,
        lease: OllamaCloudRequestLeaseV1,
        terminal: OllamaCloudNoResponseCompletionV2,
    ) -> None:
        """Close a proven no-request attempt without recording a response time."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    self._finish_no_response(connection, lease, terminal)
                    connection.commit()
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def _finish_no_response(
        self,
        connection: Connection,
        lease: OllamaCloudRequestLeaseV1,
        terminal: OllamaCloudNoResponseCompletionV2,
        *,
        allow_expired: bool = False,
    ) -> None:
        if (
            terminal.admission_id != lease.admission_id
            or terminal.scheduler_instance_id != lease.scheduler_instance_id
            or terminal.schedule_id != lease.schedule_id
            or terminal.fencing_token != lease.fencing_token
            or terminal.started_at != lease.started_at
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
        row = _admission_row(connection, lease.admission_id.value)
        gate = _gate_row(connection)
        if row is None or gate is None:
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
        if row["no_response_id"] is not None:
            if (
                row["v2_terminal_at"] != _utc_text(terminal.terminal_at)
                or row["v2_reason_code"] != terminal.reason_code
                or row["v2_source_state"] != terminal.source_state
                or row["v2_certainty"] != terminal.dispatch_certainty
                or int(row["v2_gate_record_version"]) != lease.gate_record_version
                or _utc_value(row["v2_next_allowed_at"])
                != max(lease.next_allowed_at, terminal.terminal_at)
                or row["scheduler_instance_id"] != lease.scheduler_instance_id.value
                or row["schedule_id"] != lease.schedule_id.value
                or row["account_id"] != lease.account_id.value
                or int(row["fencing_token"]) != lease.fencing_token
                or _utc_value(row["started_at"]) != lease.started_at
                or _utc_value(row["lease_expires_at"]) != lease.lease_expires_at
                or _utc_value(row["next_allowed_at"]) != lease.next_allowed_at
            ):
                raise OllamaCloudAdmissionRepositoryErrorV1(
                    "ollama_cloud_completion_conflict"
                )
            return
        if not allow_expired and (
            terminal.terminal_at > lease.lease_expires_at
            or datetime.now(UTC) > lease.lease_expires_at
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
        if allow_expired and terminal.reason_code != "pre_dispatch_failed":
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
        journal = connection.exec_driver_sql(
            "SELECT phase FROM collection_cloud_attempt_journal WHERE admission_id=?",
            (lease.admission_id.value,),
        ).scalar_one_or_none()
        expected_phase = (
            "reserved"
            if terminal.reason_code == "pre_dispatch_failed"
            else "dispatched"
        )
        if (
            journal != expected_phase
            or row["state"] != "active"
            or gate["active_admission_id"] != lease.admission_id.value
            or row["scheduler_instance_id"] != lease.scheduler_instance_id.value
            or row["schedule_id"] != lease.schedule_id.value
            or row["account_id"] != lease.account_id.value
            or int(row["fencing_token"]) != lease.fencing_token
            or int(gate["fencing_token"]) != lease.fencing_token
            or int(gate["record_version"]) != lease.gate_record_version
            or _utc_value(row["started_at"]) != lease.started_at
            or _utc_value(row["lease_expires_at"]) != lease.lease_expires_at
            or _utc_value(row["next_allowed_at"]) != lease.next_allowed_at
            or _utc_value(gate["next_allowed_at"]) != lease.next_allowed_at
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
        next_allowed = max(_utc_value(gate["next_allowed_at"]), terminal.terminal_at)
        connection.exec_driver_sql(
            "INSERT INTO collection_cloud_no_response_terminal "
            "(admission_id,terminal_at,gate_record_version,next_allowed_at,reason_code,source_state,dispatch_certainty) "
            "VALUES (?,?,?,?,?,?,'not_started')",
            (
                lease.admission_id.value,
                _utc_text(terminal.terminal_at),
                lease.gate_record_version,
                _utc_text(next_allowed),
                terminal.reason_code,
                terminal.source_state,
            ),
        )
        changed = connection.exec_driver_sql(
            "UPDATE collection_ollama_cloud_gate SET active_admission_id=NULL,next_allowed_at=?, "
            "record_version=record_version+1,updated_at=? "
            "WHERE gate_id=? AND active_admission_id=? AND fencing_token=? AND record_version=?",
            (
                _utc_text(next_allowed),
                _utc_text(terminal.terminal_at),
                _GATE_ID,
                lease.admission_id.value,
                lease.fencing_token,
                lease.gate_record_version,
            ),
        )
        if changed.rowcount != 1:
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")

    def recover_rate_gate(
        self,
        now: datetime,
        *,
        expected: OllamaCloudRequestLeaseV1 | None = None,
        reserved_only: bool = False,
        owner_stale_before: datetime | None = None,
    ) -> str:
        """Resolve reserved or journaled work; never guess a dispatched outcome."""
        if now.utcoffset() != timedelta(0) or (
            owner_stale_before is not None
            and (
                owner_stale_before.utcoffset() != timedelta(0)
                or owner_stale_before > now
            )
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_recovery_time_invalid"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    gate = _gate_row(connection)
                    if gate is None or gate["active_admission_id"] is None:
                        connection.commit()
                        return "idle"
                    admission_id = str(gate["active_admission_id"])
                    if (
                        expected is not None
                        and expected.admission_id.value != admission_id
                    ):
                        connection.commit()
                        return "changed"
                    row = _admission_row(connection, admission_id)
                    journal = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_attempt_journal WHERE admission_id=?",
                            (admission_id,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None or journal is None or row["state"] != "active":
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_fencing_conflict"
                        )
                    if reserved_only:
                        if expected is None or (
                            row["scheduler_instance_id"]
                            != expected.scheduler_instance_id.value
                            or row["schedule_id"] != expected.schedule_id.value
                            or row["account_id"] != expected.account_id.value
                            or int(row["fencing_token"]) != expected.fencing_token
                            or _utc_value(row["started_at"]) != expected.started_at
                            or _utc_value(row["lease_expires_at"])
                            != expected.lease_expires_at
                            or _utc_value(row["next_allowed_at"])
                            != expected.next_allowed_at
                            or _utc_value(gate["next_allowed_at"])
                            != expected.next_allowed_at
                            or int(gate["record_version"])
                            != expected.gate_record_version
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_fencing_conflict"
                            )
                    elif journal["phase"] in {"reserved", "outcome"}:
                        if (
                            owner_stale_before is None
                            or _utc_value(row["lease_expires_at"]) > now
                        ):
                            connection.commit()
                            return "owner_active_or_unverified"
                        owner = connection.exec_driver_sql(
                            "SELECT heartbeat_at FROM collection_scheduler_instance WHERE instance_id=?",
                            (row["scheduler_instance_id"],),
                        ).scalar_one_or_none()
                        if owner is None or _utc_value(owner) > owner_stale_before:
                            connection.commit()
                            return "owner_active_or_unverified"
                    if reserved_only and journal["phase"] != "reserved":
                        connection.commit()
                        return "not_reserved"
                    if journal["phase"] == "legacy_unresolved":
                        connection.commit()
                        return "legacy_unresolved"
                    if journal["phase"] == "dispatched":
                        connection.commit()
                        return "outcome_unknown"
                    if journal["phase"] == "reserved":
                        lease = _lease(row, int(gate["record_version"]))
                        terminal = OllamaCloudNoResponseCompletionV2(
                            admission_id=lease.admission_id,
                            scheduler_instance_id=lease.scheduler_instance_id,
                            schedule_id=lease.schedule_id,
                            fencing_token=lease.fencing_token,
                            started_at=lease.started_at,
                            terminal_at=now,
                            reason_code="pre_dispatch_failed",
                        )
                        self._finish_no_response(
                            connection, lease, terminal, allow_expired=not reserved_only
                        )
                        connection.commit()
                        return "recovered"
                    elif journal["phase"] == "outcome":
                        outcome = journal["outcome"]
                        received = _utc_value(journal["response_received_at"])
                        retry_after = journal["retry_after_seconds"]
                        jitter = journal["completion_jitter_seconds"]
                    else:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_fencing_conflict"
                        )
                    completion = OllamaCloudRequestCompletionV1(
                        admission_id=OpaqueIdV1(admission_id),
                        scheduler_instance_id=OpaqueIdV1(
                            str(row["scheduler_instance_id"])
                        ),
                        schedule_id=OpaqueIdV1(str(row["schedule_id"])),
                        fencing_token=int(row["fencing_token"]),
                        started_at=_utc_value(row["started_at"]),
                        response_received_at=received,
                        outcome=outcome,
                        retry_after_seconds=retry_after,
                        jitter_seconds=jitter,
                    )
                    self._complete(connection, completion)
                    connection.commit()
                    return "recovered"
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def recoverable_orphaned_runs(
        self, *, now: datetime, owner_stale_before: datetime, limit: int = 32
    ) -> tuple[
        tuple[
            OpaqueIdV1, str, int, str | None, int | None, OpaqueIdV1 | None, str | None
        ],
        ...,
    ]:
        """Return expired queued/running M04 runs with a terminal rate journal."""
        if (
            now.utcoffset() != timedelta(0)
            or owner_stale_before.utcoffset() != timedelta(0)
            or owner_stale_before > now
            or type(limit) is not int
            or not 1 <= limit <= 64
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_recovery_time_invalid"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    _assert_terminal_gate_consistency(connection)
                    rows = connection.exec_driver_sql(
                        "SELECT r.run_id,r.state,r.fencing_token,COALESCE(t.source_state,j.failure_code),j.retry_after_seconds,t.admission_id,t.reason_code "
                        "FROM collection_cloud_attempt_journal j "
                        "JOIN collection_ollama_cloud_admission a ON a.admission_id=j.admission_id "
                        "LEFT JOIN collection_cloud_no_response_terminal t ON t.admission_id=a.admission_id "
                        "JOIN collection_run r ON r.run_id=j.run_id "
                        "JOIN collection_lease l ON l.run_id=r.run_id "
                        "JOIN collection_scheduler_instance owner ON owner.instance_id=l.owner_instance_id "
                        "WHERE ((j.phase='outcome' AND a.state='completed') OR t.admission_id IS NOT NULL) "
                        "AND r.provider_key='ollama' AND r.capability_id='subscription.quota' "
                        "AND r.source_id='ollama.cloud.balance.v1' AND r.state IN ('queued','running') "
                        "AND r.schedule_id=a.schedule_id AND r.account_id=a.account_id "
                        "AND l.owner_instance_id=a.scheduler_instance_id AND l.fencing_token=r.fencing_token "
                        "AND l.expires_at<=? AND owner.heartbeat_at<=? "
                        "ORDER BY r.requested_at,r.run_id LIMIT ?",
                        (_utc_text(now), _utc_text(owner_stale_before), limit),
                    ).all()
                    return tuple(
                        (
                            OpaqueIdV1(str(row[0])),
                            str(row[1]),
                            int(row[2]),
                            str(row[3]) if row[3] is not None else None,
                            int(row[4]) if row[4] is not None else None,
                            OpaqueIdV1(str(row[5])) if row[5] is not None else None,
                            str(row[6]) if row[6] is not None else None,
                        )
                        for row in rows
                    )
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def reconcile_source_lane(self, eligible: tuple[OpaqueIdV1, ...]) -> None:
        """Remove stale source registrations while preserving schedule history."""
        if len(eligible) > 1000 or len(set(eligible)) != len(eligible):
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_schedule_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    parameters: tuple[object, ...] = ("ollama.cloud.balance.v1",)
                    predicate = ""
                    if eligible:
                        predicate = (
                            " AND schedule_id NOT IN ("
                            + ",".join("?" for _ in eligible)
                            + ")"
                        )
                        parameters += tuple(item.value for item in eligible)
                    connection.exec_driver_sql(
                        "DELETE FROM collection_cloud_schedule_lane WHERE source_id=?"
                        + predicate,
                        parameters,
                    )
                    connection.commit()
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def register_verification_target(
        self, target: OllamaCloudVerificationTargetV1
    ) -> None:
        """Register a cloud-only target without putting it in the scheduled lane."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    _assert_terminal_gate_consistency(connection)
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_schedule WHERE schedule_id=?",
                            (target.schedule_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    expected = (
                        target.target_key_digest,
                        _PROVIDER_KEY,
                        None,
                        target.provider_target.target_kind,
                        target.provider_target.target_id.value,
                        target.account_id.value,
                        target.profile_id.value,
                        target.resource_id.value,
                        _CAPABILITY_ID,
                        target.target_generation,
                    )
                    instant = _utc_text(target.requested_at)
                    if row is None:
                        connection.exec_driver_sql(
                            "INSERT INTO collection_schedule "
                            "(schedule_id,target_key_digest,provider_key,installation_id,"
                            "provider_target_kind,provider_target_id,account_id,profile_id,"
                            "resource_id,capability_id,state,activity_class,"
                            "base_interval_seconds,effective_interval_seconds,target_generation,"
                            "next_due_at,not_before_at,backoff_kind,backoff_generation,"
                            "consecutive_failure_count,last_attempted_run_id,last_successful_run_id,"
                            "last_terminal_outcome_code,record_version,created_at,updated_at) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,'enabled','unknown',300,300,?,?,"
                            "NULL,NULL,0,0,NULL,NULL,NULL,1,?,?)",
                            (
                                target.schedule_id.value,
                                *expected,
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
                                "provider_target_kind",
                                "provider_target_id",
                                "account_id",
                                "profile_id",
                                "resource_id",
                                "capability_id",
                                "target_generation",
                            )
                        )
                        if actual != expected:
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_schedule_conflict"
                            )
                    connection.commit()
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
                    _assert_terminal_gate_consistency(connection)
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
                        if actual != target:
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_schedule_conflict"
                            )
                        active_work = (
                            connection.exec_driver_sql(
                                "SELECT 1 FROM collection_lease WHERE schedule_id=? "
                                "UNION ALL SELECT 1 FROM "
                                "collection_ollama_cloud_admission "
                                "WHERE schedule_id=? AND state='active' "
                                "AND NOT EXISTS (SELECT 1 FROM collection_cloud_no_response_terminal t "
                                "WHERE t.admission_id=collection_ollama_cloud_admission.admission_id) LIMIT 1",
                                (
                                    admission.schedule_id.value,
                                    admission.schedule_id.value,
                                ),
                            ).first()
                            is not None
                        )
                        try:
                            action = cloud_schedule_generation_action(
                                row["target_generation"],
                                admission.target_generation,
                                active_work,
                            )
                        except ValueError as error:
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                str(error)
                            ) from None
                        if action == "advance":
                            updated = connection.exec_driver_sql(
                                "UPDATE collection_schedule SET target_generation=?,"
                                "record_version=record_version+1,updated_at=? "
                                "WHERE schedule_id=? AND target_generation=? "
                                "AND record_version=?",
                                (
                                    admission.target_generation,
                                    _utc_text(admission.requested_at),
                                    admission.schedule_id.value,
                                    row["target_generation"],
                                    row["record_version"],
                                ),
                            )
                            if updated.rowcount != 1:
                                raise OllamaCloudAdmissionRepositoryErrorV1(
                                    "ollama_cloud_schedule_conflict"
                                )
                    connection.exec_driver_sql(
                        "INSERT INTO collection_cloud_schedule_lane (schedule_id,source_id) "
                        "VALUES (?,?) ON CONFLICT(schedule_id) DO NOTHING",
                        (admission.schedule_id.value, admission.source_id),
                    )
                    registered = connection.exec_driver_sql(
                        "SELECT source_id FROM collection_cloud_schedule_lane WHERE schedule_id=?",
                        (admission.schedule_id.value,),
                    ).scalar_one_or_none()
                    if registered != admission.source_id:
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

    def acquire_verification(
        self, request: OllamaCloudVerificationAcquireV1
    ) -> OllamaCloudAdmissionDecisionV1:
        """Admit one exact owner-selected target through the same global gate."""
        base = OllamaCloudRequestAcquireV1(
            admission_id=request.admission_id,
            scheduler_instance_id=request.scheduler_instance_id,
            requested_at=request.requested_at,
            lease_expires_at=request.lease_expires_at,
            jitter_seconds=request.jitter_seconds,
        )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    result = self._acquire(connection, base, verification=request)
                    connection.commit()
                    return result
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def _acquire(
        self,
        connection: Connection,
        request: OllamaCloudRequestAcquireV1,
        *,
        verification: OllamaCloudVerificationAcquireV1 | None = None,
    ) -> OllamaCloudAdmissionDecisionV1:
        requested_text = _utc_text(request.requested_at)
        existing = _admission_row(connection, request.admission_id.value)
        gate = _gate_row(connection)
        if existing is not None:
            if (
                gate is None
                or not _same_acquire(existing, request)
                or (
                    verification is not None
                    and (
                        existing["schedule_id"] != verification.schedule_id.value
                        or existing["account_id"] != verification.account_id.value
                        or connection.exec_driver_sql(
                            "SELECT target_generation FROM collection_schedule "
                            "WHERE schedule_id=? AND provider_target_kind='cloud_service'",
                            (verification.schedule_id.value,),
                        ).scalar_one_or_none()
                        != verification.target_generation
                    )
                )
            ):
                raise OllamaCloudAdmissionRepositoryErrorV1(
                    "ollama_cloud_admission_conflict"
                )
            next_allowed = _utc_value(existing["next_allowed_at"])
            if existing["no_response_id"] is not None:
                return OllamaCloudAdmissionDecisionV1(
                    "replayed_terminal",
                    None,
                    _utc_value(existing["v2_next_allowed_at"]),
                )
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
        if verification is None:
            candidate = (
                connection.exec_driver_sql(
                    "SELECT s.schedule_id,s.account_id,s.effective_interval_seconds "
                    "FROM collection_schedule AS s JOIN collection_cloud_schedule_lane AS lane "
                    "ON lane.schedule_id=s.schedule_id AND lane.source_id='ollama.cloud.balance.v1' "
                    "LEFT JOIN collection_lease AS l "
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
        else:
            candidate = (
                connection.exec_driver_sql(
                    "SELECT s.schedule_id,s.account_id,s.effective_interval_seconds "
                    "FROM collection_schedule AS s "
                    "LEFT JOIN collection_lease AS l ON l.schedule_id=s.schedule_id "
                    "WHERE s.schedule_id=? AND s.account_id=? AND s.provider_key=? "
                    "AND s.capability_id=? AND s.target_generation=? "
                    "AND s.provider_target_kind='cloud_service' "
                    "AND s.provider_target_id IS NOT NULL AND s.state='enabled' "
                    "AND l.schedule_id IS NULL",
                    (
                        verification.schedule_id.value,
                        verification.account_id.value,
                        _PROVIDER_KEY,
                        _CAPABILITY_ID,
                        verification.target_generation,
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
            "INSERT INTO collection_scheduler_instance "
            "(instance_id,service_version,started_at,heartbeat_at,stopping_at,completed_at,lifecycle_state,last_health_code) "
            "VALUES (?,'1.0.0',?,?,NULL,NULL,'running',NULL) "
            "ON CONFLICT(instance_id) DO UPDATE SET heartbeat_at=excluded.heartbeat_at, "
            "lifecycle_state='running',stopping_at=NULL,completed_at=NULL",
            (request.scheduler_instance_id.value, requested_text, requested_text),
        )
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
        connection.exec_driver_sql(
            "INSERT INTO collection_cloud_attempt_journal (admission_id,phase) VALUES (?,'reserved')",
            (request.admission_id.value,),
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
        intent = connection.exec_driver_sql(
            "SELECT outcome,response_received_at,retry_after_seconds,completion_jitter_seconds "
            "FROM collection_cloud_attempt_journal WHERE admission_id=? AND phase='outcome'",
            (completion.admission_id.value,),
        ).first()
        if intent is None or tuple(intent) != (
            completion.outcome,
            _utc_text(completion.response_received_at),
            completion.retry_after_seconds,
            completion.jitter_seconds,
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_completion_conflict"
            )
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
