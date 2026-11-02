"""Durable single-instance Ollama cloud request admission over real SQLite."""

# ruff: noqa: E501 -- SQL identity and fence predicates stay explicit.

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast

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
    CollectionRunAdmissionV1OrV2,
    CollectionRunAdmissionV2,
    CollectionRunStateV1,
    OllamaCloudAdmissionDecisionV1,
    OllamaCloudLatestSourceSignalQueryV1,
    OllamaCloudLatestSourceSignalV1,
    OllamaCloudNoResponseCompletionV2,
    OllamaCloudRateGateViewV1,
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
    OllamaCloudRequestLeaseV1,
    OllamaCloudVerificationAcquireV1,
    OllamaCloudVerificationClaimRequestV1,
    OllamaCloudVerificationClaimTerminalV1,
    OllamaCloudVerificationDispatchCertaintyV1,
    OllamaCloudVerificationEnqueueV2,
    OllamaCloudVerificationGateStateV1,
    OllamaCloudVerificationInterruptionProofV1,
    OllamaCloudVerificationJobClaimV1,
    OllamaCloudVerificationJobViewV1,
    OllamaCloudVerificationReplayQueryV1,
    OllamaCloudVerificationStatusV1,
    OllamaCloudVerificationTargetV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CredentialBindingVerificationReceiptV1,
    ProviderTargetRefV1,
)
from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
    after_ollama_attempt,
    cloud_schedule_generation_action,
    next_cloud_work_lane,
    reserve_after_lease,
)
from agentmonitor.modules.collection_control.domain.ollama_verification import (
    RECONCILABLE_VERIFICATION_RUN_STATES_V1,
    VERIFICATION_RESPONSE_OUTCOME_V1,
    classify_latest_ollama_cloud_source_signal_v1,
    decide_cloud_verification_replay,
    verification_completion_decision,
    verification_lineage_matches,
)

_GATE_ID = "ollama-cloud-balance-v1"
_PROVIDER_KEY = "ollama"
_CAPABILITY_ID = "subscription.quota"


def cloud_schedule_storage_target(
    target: ProviderTargetRefV1,
) -> tuple[str | None, str | None, str | None]:
    """Preserve the cloud/installation distinction in schedule storage."""
    if target.target_kind == "provider_installation":
        return target.target_id.value, None, None
    if target.target_kind == "cloud_service":
        return None, target.target_kind, target.target_id.value
    raise ValueError("ollama_cloud_schedule_invalid")


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


def _gate_status(
    connection: Connection, queried_at: datetime
) -> tuple[str, datetime | None]:
    """Read the provider-global gate without guessing an expired active lease."""
    _assert_terminal_gate_consistency(connection)
    gate = _gate_row(connection)
    if gate is None:
        return "ready", None
    if gate["active_admission_id"] is not None:
        active = _admission_row(connection, str(gate["active_admission_id"]))
        if active is None or active["state"] != "active":
            raise OllamaCloudAdmissionRepositoryErrorV1("ollama_cloud_fencing_conflict")
        expiry = _utc_value(active["lease_expires_at"])
        if expiry <= queried_at:
            return "unresolved", None
        return "busy", max(expiry, _utc_value(gate["next_allowed_at"]))
    next_allowed = _utc_value(gate["next_allowed_at"])
    if next_allowed > queried_at:
        return "not_due", next_allowed
    return "ready", None


def _idempotency_digest(principal_id: str, idempotency_key: str) -> str:
    return hashlib.sha256(
        (
            "agentmonitor.ollama-verification.v1\0"
            + principal_id
            + "\0"
            + idempotency_key
        ).encode("utf-8")
    ).hexdigest()


def _verification_claim(row: RowMapping) -> OllamaCloudVerificationJobClaimV1:
    return OllamaCloudVerificationJobClaimV1(
        job_id=OpaqueIdV1(str(row["job_id"])),
        worker_instance_id=OpaqueIdV1(str(row["claim_owner_id"])),
        request_principal_id=OpaqueIdV1(str(row["principal_id"])),
        idempotency_key_digest=str(row["idempotency_digest"]),
        schedule_id=OpaqueIdV1(str(row["schedule_id"])),
        account_id=OpaqueIdV1(str(row["account_id"])),
        access_target_id=OpaqueIdV1(str(row["access_target_id"])),
        binding_generation=int(row["binding_generation"]),
        fencing_token=int(row["claim_fencing_token"]),
        claimed_at=_utc_value(row["claimed_at"]),
        claim_expires_at=_utc_value(row["claim_expires_at"]),
        record_version=int(row["record_version"]),
    )


def _verification_job(row: RowMapping) -> OllamaCloudVerificationJobViewV1:
    state = str(row["state"])
    certainty = row["dispatch_certainty"]
    outcome = row["outcome"]
    reason = row["reason_code"]
    retry_after = row["retry_after_seconds"]
    if state == "admitted":
        phase = row.get("journal_phase")
        if phase == "dispatched":
            certainty = "may_have_started"
            reason = "request_outcome_unknown"
        elif phase == "outcome":
            certainty = "response_received"
            outcome = row.get("journal_outcome")
            reason = row.get("journal_failure_code") or reason
            retry_after = row.get("journal_retry_after_seconds")
        elif phase == "reserved":
            certainty = "not_started"
    return OllamaCloudVerificationJobViewV1(
        job_id=OpaqueIdV1(str(row["job_id"])),
        account_id=OpaqueIdV1(str(row["account_id"])),
        access_target_id=OpaqueIdV1(str(row["access_target_id"])),
        schedule_id=OpaqueIdV1(str(row["schedule_id"])),
        binding_generation=int(row["binding_generation"]),
        state=state,  # type: ignore[arg-type]
        requested_at=_utc_value(row["requested_at"]),
        not_before_at=_utc_value(row["not_before_at"]),
        admission_id=(
            OpaqueIdV1(str(row["admission_id"]))
            if row["admission_id"] is not None
            else None
        ),
        run_id=(OpaqueIdV1(str(row["run_id"])) if row["run_id"] is not None else None),
        dispatch_certainty=certainty,
        terminal_at=(
            _utc_value(row["terminal_at"]) if row["terminal_at"] is not None else None
        ),
        outcome=outcome,
        reason_code=str(reason) if reason is not None else None,
        retry_after_seconds=(int(retry_after) if retry_after is not None else None),
        record_version=int(row["record_version"]),
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
    job = connection.exec_driver_sql(
        "SELECT job_id,run_id FROM collection_cloud_verification_job "
        "WHERE admission_id=?",
        (lease.admission_id.value,),
    ).first()
    if job is not None:
        if job[1] is not None and job[1] != run.run_id.value:
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_run_fencing_conflict"
            )
        bound = connection.exec_driver_sql(
            "UPDATE collection_cloud_verification_job SET run_id=?,"
            "record_version=record_version+1 WHERE job_id=? AND state='admitted' "
            "AND admission_id=? AND (run_id IS NULL OR run_id=?)",
            (
                run.run_id.value,
                job[0],
                lease.admission_id.value,
                run.run_id.value,
            ),
        )
        if bound.rowcount != 1:
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_run_fencing_conflict"
            )


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

    def _fence_new_verification_job(
        self,
        connection: Connection,
        request: OllamaCloudVerificationEnqueueV2,
        *,
        profile_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
    ) -> None:
        """Require a composition-owned authority fence before a new job."""
        raise OllamaCloudAdmissionRepositoryErrorV1(
            "ollama_cloud_verification_authority_unavailable"
        )

    def preferred_work_lane(self) -> str:
        """Choose fairly from the latest durable global admission."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT EXISTS (SELECT 1 FROM collection_cloud_verification_job j "
                            "WHERE j.admission_id=a.admission_id) AS was_verification "
                            "FROM collection_ollama_cloud_admission a WHERE a.gate_id=? "
                            "ORDER BY a.fencing_token DESC LIMIT 1",
                            (_GATE_ID,),
                        )
                        .mappings()
                        .one_or_none()
                    )
            return next_cloud_work_lane(
                None if row is None else bool(row["was_verification"])
            )
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

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
                    job = connection.exec_driver_sql(
                        "SELECT job_id FROM collection_cloud_verification_job "
                        "WHERE admission_id=?",
                        (lease.admission_id.value,),
                    ).scalar_one_or_none()
                    if job is not None:
                        job_changed = connection.exec_driver_sql(
                            "UPDATE collection_cloud_verification_job SET "
                            "dispatch_certainty='may_have_started',"
                            "reason_code='request_outcome_unknown',"
                            "record_version=record_version+1 WHERE job_id=? "
                            "AND state='admitted' AND dispatch_certainty='not_started'",
                            (job,),
                        )
                        if job_changed.rowcount != 1:
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
                    job = connection.exec_driver_sql(
                        "SELECT job_id FROM collection_cloud_verification_job "
                        "WHERE admission_id=?",
                        (lease.admission_id.value,),
                    ).scalar_one_or_none()
                    if job is not None:
                        job_changed = connection.exec_driver_sql(
                            "UPDATE collection_cloud_verification_job SET "
                            "dispatch_certainty='not_started',reason_code=NULL,"
                            "record_version=record_version+1 WHERE job_id=? "
                            "AND state='admitted' "
                            "AND dispatch_certainty='may_have_started'",
                            (job,),
                        )
                        if job_changed.rowcount != 1:
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
        job = connection.exec_driver_sql(
            "SELECT job_id FROM collection_cloud_verification_job WHERE admission_id=?",
            (lease.admission_id.value,),
        ).scalar_one_or_none()
        if job is not None:
            finished = connection.exec_driver_sql(
                "UPDATE collection_cloud_verification_job SET state='terminal',"
                "dispatch_certainty='not_started',terminal_at=?,outcome=NULL,"
                "reason_code=?,retry_after_seconds=NULL,record_version=record_version+1 "
                "WHERE job_id=? AND state='admitted' AND admission_id=?",
                (
                    _utc_text(terminal.terminal_at),
                    terminal.source_state or terminal.reason_code,
                    job,
                    lease.admission_id.value,
                ),
            )
            if finished.rowcount != 1:
                raise OllamaCloudAdmissionRepositoryErrorV1(
                    "ollama_cloud_completion_conflict"
                )

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

    def register_schedule(self, admission: CollectionRunAdmissionV1OrV2) -> None:
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
                        *cloud_schedule_storage_target(
                            admission.provider_target
                            if isinstance(admission, CollectionRunAdmissionV2)
                            else ProviderTargetRefV1(
                                "provider_installation", admission.installation_id
                            )
                        ),
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
                            "provider_target_kind,provider_target_id,"
                            "account_id,profile_id,resource_id,capability_id,state,activity_class,"
                            "base_interval_seconds,effective_interval_seconds,target_generation,"
                            "next_due_at,not_before_at,backoff_kind,backoff_generation,"
                            "consecutive_failure_count,last_attempted_run_id,last_successful_run_id,"
                            "last_terminal_outcome_code,record_version,created_at,"
                            "updated_at) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,'enabled','unknown',300,300,?,?"
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
                                "provider_target_kind",
                                "provider_target_id",
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

    def replay_verification(
        self, query: OllamaCloudVerificationReplayQueryV1
    ) -> OllamaCloudVerificationJobViewV1 | None:
        """Return only the exact original initiation request, before new-work fencing."""
        digest = _idempotency_digest(
            query.principal_id.value, query.idempotency_key.value
        )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job "
                            "WHERE principal_id=? AND idempotency_digest=?",
                            (query.principal_id.value, digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        return None
                    decide_cloud_verification_replay(
                        existing_account_id=str(row["account_id"]),
                        existing_expected_account_record_version=(
                            int(row["expected_account_record_version"])
                            if row["expected_account_record_version"] is not None
                            else None
                        ),
                        request_account_id=query.account_id.value,
                        request_expected_account_record_version=(
                            query.expected_account_record_version
                        ),
                    )
                    return _verification_job(row)
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except ValueError as error:
            if str(error) == "ollama_cloud_verification_idempotency_conflict":
                raise OllamaCloudAdmissionRepositoryErrorV1(str(error)) from None
            raise OllamaCloudAdmissionRepositoryErrorV1() from None
        except (SQLAlchemyError, SqlitePolicyError, OSError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def enqueue_verification(
        self, request: OllamaCloudVerificationEnqueueV2
    ) -> OllamaCloudVerificationJobViewV1:
        """Create one private-idempotent job after rechecking the exact target."""
        digest = _idempotency_digest(
            request.principal_id.value, request.idempotency_key.value
        )
        instant = _utc_text(request.requested_at)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    existing = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job "
                            "WHERE principal_id=? AND idempotency_digest=?",
                            (request.principal_id.value, digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if existing is not None:
                        if (
                            existing["schedule_id"] != request.schedule_id.value
                            or existing["account_id"] != request.account_id.value
                            or existing["access_target_id"]
                            != request.access_target_id.value
                            or int(existing["binding_generation"])
                            != request.binding_generation
                            or existing["expected_account_record_version"]
                            != request.expected_account_record_version
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_verification_idempotency_conflict"
                            )
                        connection.rollback()
                        return _verification_job(existing)
                    target = (
                        connection.exec_driver_sql(
                            "SELECT profile_id,resource_id FROM collection_schedule WHERE schedule_id=? "
                            "AND account_id=? AND provider_key=? AND capability_id=? "
                            "AND provider_target_kind='cloud_service' "
                            "AND provider_target_id=? AND target_generation=? "
                            "AND state='enabled'",
                            (
                                request.schedule_id.value,
                                request.account_id.value,
                                _PROVIDER_KEY,
                                _CAPABILITY_ID,
                                request.access_target_id.value,
                                request.binding_generation,
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if target is None:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_target_unavailable"
                        )
                    self._fence_new_verification_job(
                        connection,
                        request,
                        profile_id=OpaqueIdV1(str(target["profile_id"])),
                        resource_id=OpaqueIdV1(str(target["resource_id"])),
                    )
                    active = connection.exec_driver_sql(
                        "SELECT 1 FROM collection_cloud_verification_job "
                        "WHERE account_id=? AND binding_generation=? "
                        "AND state IN ('queued','claimed','admitted')",
                        (request.account_id.value, request.binding_generation),
                    ).first()
                    if active is not None:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_already_pending"
                        )
                    job_id = "amvj_" + secrets.token_hex(16)
                    connection.exec_driver_sql(
                        "INSERT INTO collection_cloud_verification_job "
                        "(job_id,principal_id,idempotency_digest,schedule_id,account_id,"
                        "access_target_id,binding_generation,expected_account_record_version,"
                        "state,requested_at,not_before_at,"
                        "claim_owner_id,claim_fencing_token,claimed_at,claim_expires_at,"
                        "admission_id,run_id,dispatch_certainty,terminal_at,outcome,"
                        "reason_code,retry_after_seconds,record_version) "
                        "VALUES (?,?,?,?,?,?,?,?,'queued',?,?,NULL,0,NULL,NULL,NULL,NULL,"
                        "NULL,NULL,NULL,NULL,NULL,1)",
                        (
                            job_id,
                            request.principal_id.value,
                            digest,
                            request.schedule_id.value,
                            request.account_id.value,
                            request.access_target_id.value,
                            request.binding_generation,
                            request.expected_account_record_version,
                            instant,
                            instant,
                        ),
                    )
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job WHERE job_id=?",
                            (job_id,),
                        )
                        .mappings()
                        .one()
                    )
                    connection.commit()
                    return _verification_job(row)
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def claim_verification(
        self, request: OllamaCloudVerificationClaimRequestV1
    ) -> OllamaCloudVerificationJobClaimV1 | None:
        """Claim due work; only a never-admitted expired claim is reusable."""
        claimed = _utc_text(request.claimed_at)
        expires = _utc_text(request.claim_expires_at)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    connection.exec_driver_sql(
                        "UPDATE collection_cloud_verification_job AS j SET "
                        "state='terminal',dispatch_certainty='not_started',terminal_at=?,"
                        "reason_code='target_unavailable',record_version=record_version+1 "
                        "WHERE state IN ('queued','claimed') AND admission_id IS NULL "
                        "AND NOT EXISTS (SELECT 1 FROM collection_schedule s "
                        "WHERE s.schedule_id=j.schedule_id AND s.account_id=j.account_id "
                        "AND s.provider_target_kind='cloud_service' "
                        "AND s.provider_target_id=j.access_target_id "
                        "AND s.target_generation=j.binding_generation "
                        "AND s.provider_key=? AND s.capability_id=? AND s.state='enabled')",
                        (claimed, _PROVIDER_KEY, _CAPABILITY_ID),
                    )
                    candidate = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job "
                            "WHERE not_before_at<=? AND ((state='queued') OR "
                            "(state='claimed' AND admission_id IS NULL "
                            "AND claim_expires_at<=?)) "
                            "ORDER BY requested_at,job_id LIMIT 1",
                            (claimed, claimed),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if candidate is None:
                        connection.commit()
                        return None
                    token = int(candidate["claim_fencing_token"]) + 1
                    version = int(candidate["record_version"]) + 1
                    updated = connection.exec_driver_sql(
                        "UPDATE collection_cloud_verification_job SET state='claimed',"
                        "claim_owner_id=?,claim_fencing_token=?,claimed_at=?,"
                        "claim_expires_at=?,record_version=? WHERE job_id=? "
                        "AND record_version=? AND admission_id IS NULL "
                        "AND ((state='queued') OR (state='claimed' AND claim_expires_at<=?))",
                        (
                            request.worker_instance_id.value,
                            token,
                            claimed,
                            expires,
                            version,
                            candidate["job_id"],
                            candidate["record_version"],
                            claimed,
                        ),
                    )
                    if updated.rowcount != 1:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_claim_conflict"
                        )
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job WHERE job_id=?",
                            (candidate["job_id"],),
                        )
                        .mappings()
                        .one()
                    )
                    connection.commit()
                    return _verification_claim(row)
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def finish_verification_claim(
        self, terminal: OllamaCloudVerificationClaimTerminalV1
    ) -> OllamaCloudVerificationJobViewV1:
        """Record only a fenced, pre-admission no-request terminal."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    existing = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job WHERE job_id=?",
                            (terminal.job_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if existing is not None and existing["state"] == "terminal":
                        if (
                            existing["claim_owner_id"]
                            != terminal.worker_instance_id.value
                            or int(existing["claim_fencing_token"])
                            != terminal.fencing_token
                            or existing["claimed_at"] != _utc_text(terminal.claimed_at)
                            or existing["claim_expires_at"]
                            != _utc_text(terminal.claim_expires_at)
                            or existing["terminal_at"]
                            != _utc_text(terminal.terminal_at)
                            or existing["dispatch_certainty"] != "not_started"
                            or existing["reason_code"] != terminal.reason_code
                            or existing["admission_id"] is not None
                            or existing["run_id"] is not None
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_verification_claim_conflict"
                            )
                        connection.rollback()
                        return _verification_job(existing)
                    updated = connection.exec_driver_sql(
                        "UPDATE collection_cloud_verification_job SET state='terminal',"
                        "dispatch_certainty='not_started',terminal_at=?,reason_code=?,"
                        "record_version=record_version+1 WHERE job_id=? AND state='claimed' "
                        "AND admission_id IS NULL AND run_id IS NULL AND claim_owner_id=? "
                        "AND claim_fencing_token=? AND claimed_at=? AND claim_expires_at=?",
                        (
                            _utc_text(terminal.terminal_at),
                            terminal.reason_code,
                            terminal.job_id.value,
                            terminal.worker_instance_id.value,
                            terminal.fencing_token,
                            _utc_text(terminal.claimed_at),
                            _utc_text(terminal.claim_expires_at),
                        ),
                    )
                    if updated.rowcount != 1:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_claim_conflict"
                        )
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job WHERE job_id=?",
                            (terminal.job_id.value,),
                        )
                        .mappings()
                        .one()
                    )
                    connection.commit()
                    return _verification_job(row)
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def acquire_claimed_verification(
        self,
        claim: OllamaCloudVerificationJobClaimV1,
        request: OllamaCloudVerificationAcquireV1,
    ) -> OllamaCloudAdmissionDecisionV1:
        """Acknowledge a live claim and associate rate admission atomically."""
        if (
            claim.schedule_id != request.schedule_id
            or claim.account_id != request.account_id
            or claim.binding_generation != request.target_generation
            or claim.worker_instance_id != request.scheduler_instance_id
            or not claim.claimed_at <= request.requested_at <= claim.claim_expires_at
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_claim_conflict"
            )
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
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job WHERE job_id=?",
                            (claim.job_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None or (
                        row["claim_owner_id"] != claim.worker_instance_id.value
                        or row["principal_id"] != claim.request_principal_id.value
                        or row["idempotency_digest"] != claim.idempotency_key_digest
                        or int(row["claim_fencing_token"]) != claim.fencing_token
                        or _utc_value(row["claimed_at"]) != claim.claimed_at
                        or _utc_value(row["claim_expires_at"]) != claim.claim_expires_at
                        or row["schedule_id"] != claim.schedule_id.value
                        or row["account_id"] != claim.account_id.value
                        or row["access_target_id"] != claim.access_target_id.value
                        or int(row["binding_generation"]) != claim.binding_generation
                    ):
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_claim_conflict"
                        )
                    exact_target = connection.exec_driver_sql(
                        "SELECT 1 FROM collection_schedule WHERE schedule_id=? "
                        "AND account_id=? AND provider_key=? AND capability_id=? "
                        "AND provider_target_kind='cloud_service' "
                        "AND provider_target_id=? AND target_generation=? "
                        "AND state='enabled'",
                        (
                            claim.schedule_id.value,
                            claim.account_id.value,
                            _PROVIDER_KEY,
                            _CAPABILITY_ID,
                            claim.access_target_id.value,
                            claim.binding_generation,
                        ),
                    ).first()
                    if row["state"] == "admitted":
                        if (
                            row["admission_id"] != request.admission_id.value
                            or exact_target is None
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_verification_claim_conflict"
                            )
                        result = self._acquire(connection, base, verification=request)
                        connection.commit()
                        return result
                    if (
                        row["state"] != "claimed"
                        or row["admission_id"] is not None
                        or row["run_id"] is not None
                        or int(row["record_version"]) != claim.record_version
                        or datetime.now(UTC) >= claim.claim_expires_at
                    ):
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_claim_conflict"
                        )
                    result = (
                        self._acquire(connection, base, verification=request)
                        if exact_target is not None
                        else OllamaCloudAdmissionDecisionV1("no_candidate", None, None)
                    )
                    if result.state == "acquired":
                        changed = connection.exec_driver_sql(
                            "UPDATE collection_cloud_verification_job SET state='admitted',"
                            "admission_id=?,dispatch_certainty='not_started',"
                            "record_version=record_version+1 WHERE job_id=? "
                            "AND state='claimed' AND record_version=?",
                            (
                                request.admission_id.value,
                                claim.job_id.value,
                                claim.record_version,
                            ),
                        )
                    elif result.state in {"busy", "not_due"}:
                        if result.retry_at is None:
                            raise OllamaCloudAdmissionRepositoryErrorV1()
                        changed = connection.exec_driver_sql(
                            "UPDATE collection_cloud_verification_job SET state='queued',"
                            "not_before_at=?,claim_owner_id=NULL,claimed_at=NULL,"
                            "claim_expires_at=NULL,record_version=record_version+1 "
                            "WHERE job_id=? AND state='claimed' AND record_version=?",
                            (
                                _utc_text(result.retry_at),
                                claim.job_id.value,
                                claim.record_version,
                            ),
                        )
                    elif result.state == "no_candidate":
                        target = connection.exec_driver_sql(
                            "SELECT 1 FROM collection_schedule WHERE schedule_id=? "
                            "AND account_id=? AND provider_key=? AND capability_id=? "
                            "AND provider_target_kind='cloud_service' "
                            "AND provider_target_id=? AND target_generation=? "
                            "AND state='enabled'",
                            (
                                claim.schedule_id.value,
                                claim.account_id.value,
                                _PROVIDER_KEY,
                                _CAPABILITY_ID,
                                claim.access_target_id.value,
                                claim.binding_generation,
                            ),
                        ).first()
                        lease_expiry = connection.exec_driver_sql(
                            "SELECT expires_at FROM collection_lease WHERE schedule_id=?",
                            (claim.schedule_id.value,),
                        ).scalar_one_or_none()
                        if (
                            target is not None
                            and lease_expiry is not None
                            and _utc_value(lease_expiry) > request.requested_at
                        ):
                            changed = connection.exec_driver_sql(
                                "UPDATE collection_cloud_verification_job SET state='queued',"
                                "not_before_at=?,claim_owner_id=NULL,claimed_at=NULL,"
                                "claim_expires_at=NULL,record_version=record_version+1 "
                                "WHERE job_id=? AND state='claimed' AND record_version=?",
                                (
                                    _utc_text(_utc_value(lease_expiry)),
                                    claim.job_id.value,
                                    claim.record_version,
                                ),
                            )
                        else:
                            reason = (
                                "collection_lease_unresolved"
                                if target is not None and lease_expiry is not None
                                else "target_unavailable"
                            )
                            changed = connection.exec_driver_sql(
                                "UPDATE collection_cloud_verification_job SET state='terminal',"
                                "dispatch_certainty='not_started',terminal_at=?,"
                                "reason_code=?,record_version=record_version+1 "
                                "WHERE job_id=? AND state='claimed' AND record_version=?",
                                (
                                    _utc_text(request.requested_at),
                                    reason,
                                    claim.job_id.value,
                                    claim.record_version,
                                ),
                            )
                    else:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_claim_conflict"
                        )
                    if changed.rowcount != 1:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_claim_conflict"
                        )
                    connection.commit()
                    return result
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def read_verification_status(
        self,
        account_id: OpaqueIdV1,
        binding_generation: int,
        queried_at: datetime,
    ) -> OllamaCloudVerificationStatusV1:
        """Read the latest safe job projection and the authoritative global gate."""
        if (
            type(binding_generation) is not int
            or binding_generation < 1
            or queried_at.utcoffset() != timedelta(0)
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_query_invalid"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT j.*,a.state AS admission_state,"
                            "a.lease_expires_at AS admission_lease_expires_at,"
                            "x.phase AS journal_phase,x.outcome AS journal_outcome,"
                            "x.failure_code AS journal_failure_code,"
                            "x.retry_after_seconds AS journal_retry_after_seconds "
                            "FROM collection_cloud_verification_job j "
                            "LEFT JOIN collection_ollama_cloud_admission a "
                            "ON a.admission_id=j.admission_id "
                            "LEFT JOIN collection_cloud_attempt_journal x "
                            "ON x.admission_id=j.admission_id "
                            "WHERE j.account_id=? AND j.binding_generation=? "
                            "ORDER BY j.requested_at DESC,j.job_id DESC LIMIT 1",
                            (account_id.value, binding_generation),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    job = _verification_job(row) if row is not None else None
                    gate = _gate_row(connection)
                    gate_state = "ready"
                    retry_at = None
                    if gate is not None and gate["active_admission_id"] is not None:
                        active = _admission_row(
                            connection, str(gate["active_admission_id"])
                        )
                        if active is None or active["state"] != "active":
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_fencing_conflict"
                            )
                        expiry = _utc_value(active["lease_expires_at"])
                        if expiry <= queried_at:
                            gate_state = "unresolved"
                        else:
                            gate_state = "busy"
                            retry_at = max(expiry, _utc_value(gate["next_allowed_at"]))
                    elif (
                        gate is not None
                        and _utc_value(gate["next_allowed_at"]) > queried_at
                    ):
                        gate_state = "not_due"
                        retry_at = _utc_value(gate["next_allowed_at"])
                    if (
                        job is not None
                        and job.state == "admitted"
                        and job.dispatch_certainty == "may_have_started"
                    ):
                        gate_state = "unresolved"
                        retry_at = None
                    elif job is not None and gate_state != "unresolved":
                        job_retry = None
                        if job.state == "queued" and job.not_before_at > queried_at:
                            job_retry = job.not_before_at
                        elif (
                            job.state == "claimed"
                            and row is not None
                            and row["claim_expires_at"] is not None
                            and _utc_value(row["claim_expires_at"]) > queried_at
                        ):
                            job_retry = _utc_value(row["claim_expires_at"])
                        if job_retry is not None:
                            if retry_at is not None:
                                job_retry = max(job_retry, retry_at)
                            gate_state = "busy" if job.state == "claimed" else "not_due"
                            retry_at = job_retry
                    return OllamaCloudVerificationStatusV1(
                        account_id=account_id,
                        binding_generation=binding_generation,
                        job=job,
                        gate_state=gate_state,  # type: ignore[arg-type]
                        retry_at=retry_at,
                        queried_at=queried_at,
                    )
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def read_latest_source_signal(
        self, query: OllamaCloudLatestSourceSignalQueryV1
    ) -> OllamaCloudLatestSourceSignalV1:
        """Read one exact target/source's latest sanitized M04 outcome."""
        if not isinstance(query, OllamaCloudLatestSourceSignalQueryV1):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_source_signal_query_invalid"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    excluded_admission_id = None
                    if query.exclude_active_lease is not None:
                        lease = query.exclude_active_lease
                        ensure_ollama_lease_in_transaction(
                            connection, lease, query.queried_at
                        )
                        current = (
                            connection.exec_driver_sql(
                                "SELECT j.phase,r.state,r.schedule_id,r.account_id,"
                                "r.provider_key,r.provider_target_kind,"
                                "r.provider_target_id,r.target_generation,"
                                "r.capability_id,r.source_id,r.adapter_version,"
                                "r.manifest_fingerprint,r.payload_schema,"
                                "r.fencing_token,l.owner_instance_id "
                                "FROM collection_cloud_attempt_journal j "
                                "JOIN collection_run r ON r.run_id=j.run_id "
                                "JOIN collection_lease l ON l.run_id=r.run_id "
                                "WHERE j.admission_id=?",
                                (lease.admission_id.value,),
                            )
                            .mappings()
                            .one_or_none()
                        )
                        if (
                            current is None
                            or current["phase"] != "reserved"
                            or current["state"] not in {"queued", "running"}
                            or current["schedule_id"] != lease.schedule_id.value
                            or current["account_id"] != query.account_id.value
                            or current["account_id"] != lease.account_id.value
                            or current["provider_key"] != "ollama"
                            or current["provider_target_kind"] != "cloud_service"
                            or current["provider_target_id"]
                            != query.access_target_id.value
                            or int(current["target_generation"])
                            != query.binding_generation
                            or current["capability_id"] != query.capability_id
                            or current["source_id"] != query.source_id
                            or current["adapter_version"] != query.adapter_version
                            or current["manifest_fingerprint"]
                            != query.source_fingerprint
                            or current["payload_schema"] != query.payload_schema
                            or int(current["fencing_token"]) != lease.fencing_token
                            or current["owner_instance_id"]
                            != lease.scheduler_instance_id.value
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_source_signal_exclusion_invalid"
                            )
                        excluded_admission_id = lease.admission_id.value
                    exclusion_sql = (
                        "AND (j.admission_id IS NULL OR j.admission_id<>?) "
                        if excluded_admission_id is not None
                        else ""
                    )
                    parameters: tuple[object, ...] = (
                        query.account_id.value,
                        query.access_target_id.value,
                        query.binding_generation,
                        query.capability_id,
                        query.source_id,
                        query.adapter_version,
                        query.source_fingerprint,
                        query.payload_schema,
                    )
                    if excluded_admission_id is not None:
                        parameters += (excluded_admission_id,)
                    statement = (
                        "SELECT r.run_id,r.schedule_id,r.state,r.requested_at,"
                        "j.admission_id,j.phase,j.outcome,j.response_received_at,"
                        "j.failure_code,a.state AS admission_state,"
                        "a.account_id AS admission_account_id,"
                        "a.schedule_id AS admission_schedule_id,"
                        "t.terminal_at AS no_response_terminal_at,"
                        "t.source_state AS no_response_source_state,"
                        "t.dispatch_certainty AS no_response_certainty "
                        "FROM collection_run r "
                        "LEFT JOIN collection_cloud_attempt_journal j "
                        "ON j.run_id=r.run_id "
                        "LEFT JOIN collection_ollama_cloud_admission a "
                        "ON a.admission_id=j.admission_id "
                        "LEFT JOIN collection_cloud_no_response_terminal t "
                        "ON t.admission_id=j.admission_id "
                        "WHERE r.provider_key='ollama' AND r.account_id=? "
                        "AND r.provider_target_kind='cloud_service' "
                        "AND r.provider_target_id=? AND r.target_generation=? "
                        "AND r.capability_id=? AND r.source_id=? "
                        "AND r.adapter_version=? AND r.manifest_fingerprint=? "
                        "AND r.payload_schema=? "
                        + exclusion_sql
                        + "ORDER BY r.requested_at DESC,r.run_id DESC LIMIT 1"
                    )
                    row = (
                        connection.exec_driver_sql(
                            statement,
                            parameters,
                        )
                        .mappings()
                        .one_or_none()
                    )
                    gate_state, retry_at = _gate_status(connection, query.queried_at)
                    if row is None:
                        return OllamaCloudLatestSourceSignalV1(
                            account_id=query.account_id,
                            binding_generation=query.binding_generation,
                            access_target_id=query.access_target_id,
                            capability_id=query.capability_id,
                            source_id=query.source_id,
                            adapter_version=query.adapter_version,
                            source_fingerprint=query.source_fingerprint,
                            payload_schema=query.payload_schema,
                            signal="outcome_unresolved",
                            run_id=None,
                            admission_id=None,
                            run_state=None,
                            dispatch_certainty=None,
                            run_requested_at=None,
                            signal_observed_at=None,
                            gate_state=cast(
                                OllamaCloudVerificationGateStateV1, gate_state
                            ),
                            retry_at=retry_at,
                            queried_at=query.queried_at,
                        )
                    if (
                        row["admission_id"] is None
                        or row["admission_state"] is None
                        or row["admission_account_id"] != query.account_id.value
                        or row["admission_schedule_id"] != row["schedule_id"]
                    ):
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_fencing_conflict"
                        )
                    phase = str(row["phase"])
                    if row["no_response_terminal_at"] is not None:
                        certainty = str(row["no_response_certainty"])
                        outcome = None
                        failure = (
                            str(row["no_response_source_state"])
                            if row["no_response_source_state"] is not None
                            else None
                        )
                        observed_at = _utc_value(row["no_response_terminal_at"])
                    elif phase == "outcome":
                        certainty = "response_received"
                        outcome = str(row["outcome"])
                        failure = (
                            str(row["failure_code"])
                            if row["failure_code"] is not None
                            else None
                        )
                        observed_at = _utc_value(row["response_received_at"])
                    elif phase == "reserved":
                        certainty = "not_started"
                        outcome = None
                        failure = None
                        observed_at = None
                    elif phase in {"dispatched", "legacy_unresolved"}:
                        certainty = "may_have_started"
                        outcome = None
                        failure = None
                        observed_at = None
                    else:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_fencing_conflict"
                        )
                    run_state = str(row["state"])
                    signal = classify_latest_ollama_cloud_source_signal_v1(
                        run_state=run_state,
                        dispatch_certainty=certainty,
                        outcome=outcome,
                        failure_code=failure,
                    )
                    return OllamaCloudLatestSourceSignalV1(
                        account_id=query.account_id,
                        binding_generation=query.binding_generation,
                        access_target_id=query.access_target_id,
                        capability_id=query.capability_id,
                        source_id=query.source_id,
                        adapter_version=query.adapter_version,
                        source_fingerprint=query.source_fingerprint,
                        payload_schema=query.payload_schema,
                        signal=signal,
                        run_id=OpaqueIdV1(str(row["run_id"])),
                        admission_id=OpaqueIdV1(str(row["admission_id"])),
                        run_state=cast(CollectionRunStateV1, run_state),
                        dispatch_certainty=cast(
                            OllamaCloudVerificationDispatchCertaintyV1, certainty
                        ),
                        run_requested_at=_utc_value(row["requested_at"]),
                        signal_observed_at=observed_at,
                        gate_state=cast(OllamaCloudVerificationGateStateV1, gate_state),
                        retry_at=retry_at,
                        queried_at=query.queried_at,
                    )
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def read_verification_job(
        self, run_id: OpaqueIdV1, admission_id: OpaqueIdV1
    ) -> OllamaCloudVerificationJobViewV1 | None:
        """Read one exact sanitized M04 verification job without provider I/O."""
        if not isinstance(run_id, OpaqueIdV1) or not isinstance(
            admission_id, OpaqueIdV1
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_query_invalid"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job "
                            "WHERE run_id=? AND admission_id=?",
                            (run_id.value, admission_id.value),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return _verification_job(row) if row is not None else None
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def pending_verification_finalizations(
        self,
        limit: int = 32,
        *,
        after_job_id: OpaqueIdV1 | None = None,
    ) -> tuple[OllamaCloudVerificationJobViewV1, ...]:
        """Page terminal HTTP-success jobs still awaiting receipt reconciliation."""
        if (
            type(limit) is not int
            or not 1 <= limit <= 64
            or (after_job_id is not None and not isinstance(after_job_id, OpaqueIdV1))
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_query_invalid"
            )
        after = None if after_job_id is None else after_job_id.value
        if after is not None and (
            len(after) != 37
            or not after.startswith("amvj_")
            or any(character not in "0123456789abcdef" for character in after[5:])
        ):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_query_invalid"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT j.*,x.phase AS journal_phase,"
                            "x.outcome AS journal_outcome,"
                            "x.failure_code AS journal_failure_code,"
                            "x.retry_after_seconds AS journal_retry_after_seconds "
                            "FROM collection_cloud_verification_job j "
                            "JOIN collection_ollama_cloud_admission a "
                            "ON a.admission_id=j.admission_id "
                            "JOIN collection_cloud_attempt_journal x "
                            "ON x.admission_id=j.admission_id "
                            "JOIN collection_run r ON r.run_id=j.run_id "
                            "WHERE j.state='admitted' "
                            "AND j.dispatch_certainty='response_received' "
                            "AND j.reason_code='verification_commit_pending' "
                            "AND j.run_id IS NOT NULL AND a.state='completed' "
                            "AND a.outcome='succeeded' AND x.phase='outcome' "
                            "AND x.outcome='succeeded' "
                            "AND r.state IN (?,?,?,?,?,?) "
                            "AND (? IS NULL OR j.job_id>?) "
                            "ORDER BY j.job_id LIMIT ?",
                            (
                                *RECONCILABLE_VERIFICATION_RUN_STATES_V1,
                                after,
                                after,
                                limit,
                            ),
                        )
                        .mappings()
                        .all()
                    )
                    return tuple(_verification_job(row) for row in rows)
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def finalize_verification_success(
        self, receipt: CredentialBindingVerificationReceiptV1
    ) -> OllamaCloudVerificationJobViewV1:
        """Terminalize only after the exact M02 receipt and M04 run committed."""
        if not isinstance(receipt, CredentialBindingVerificationReceiptV1):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_proof_invalid"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = (
                        connection.exec_driver_sql(
                            "SELECT j.*,a.state AS admission_state,"
                            "a.outcome AS admission_outcome,"
                            "a.account_id AS admission_account_id,"
                            "a.schedule_id AS admission_schedule_id,"
                            "x.run_id AS journal_run_id,x.phase AS journal_phase,"
                            "x.outcome AS journal_outcome,"
                            "x.failure_code AS journal_failure_code,"
                            "r.state AS run_state,r.account_id AS run_account_id,"
                            "r.schedule_id AS run_schedule_id,"
                            "r.provider_key AS run_provider_key,"
                            "r.provider_target_kind AS run_target_kind,"
                            "r.provider_target_id AS run_target_id,"
                            "r.capability_id AS run_capability_id,"
                            "r.source_id AS run_source_id,"
                            "r.adapter_version AS run_adapter_version,"
                            "r.manifest_fingerprint AS run_manifest_fingerprint,"
                            "r.target_generation AS run_target_generation,"
                            "r.payload_digest AS run_payload_digest,"
                            "r.completed_at AS run_completed_at "
                            "FROM collection_cloud_verification_job j "
                            "JOIN collection_ollama_cloud_admission a "
                            "ON a.admission_id=j.admission_id "
                            "JOIN collection_cloud_attempt_journal x "
                            "ON x.admission_id=j.admission_id "
                            "JOIN collection_run r ON r.run_id=j.run_id "
                            "WHERE j.run_id=? AND j.admission_id=?",
                            (receipt.run_id.value, receipt.admission_id.value),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_proof_invalid"
                        )
                    decision = verification_completion_decision(
                        "succeeded",
                        cast(CollectionRunStateV1, str(row["run_state"])),
                        True,
                    )
                    completed_at = _utc_value(row["run_completed_at"])
                    observation = connection.exec_driver_sql(
                        "SELECT 1 FROM collection_run_observation_ref "
                        "WHERE run_id=? AND consumer_key='capacity' LIMIT 1",
                        (receipt.run_id.value,),
                    ).first()
                    if (
                        decision != "verification_succeeded"
                        or not verification_lineage_matches(
                            expected_run_id=receipt.run_id.value,
                            job_run_id=row["run_id"],
                            journal_run_id=row["journal_run_id"],
                            job_account_id=row["account_id"],
                            admission_account_id=row["admission_account_id"],
                            run_account_id=row["run_account_id"],
                            job_schedule_id=row["schedule_id"],
                            admission_schedule_id=row["admission_schedule_id"],
                            run_schedule_id=row["run_schedule_id"],
                        )
                        or row["admission_state"] != "completed"
                        or row["admission_outcome"] != "succeeded"
                        or row["journal_phase"] != "outcome"
                        or row["journal_outcome"] != "succeeded"
                        or row["journal_failure_code"] is not None
                        or row["account_id"] != receipt.binding.account_id.value
                        or row["access_target_id"] != receipt.access_target_id.value
                        or int(row["binding_generation"]) != receipt.binding.generation
                        or row["run_account_id"] != receipt.binding.account_id.value
                        or row["run_provider_key"] != _PROVIDER_KEY
                        or row["run_target_kind"] != "cloud_service"
                        or row["run_target_id"] != receipt.access_target_id.value
                        or row["run_capability_id"] != _CAPABILITY_ID
                        or row["run_source_id"] != receipt.source_id
                        or row["run_adapter_version"] != receipt.adapter_version
                        or row["run_manifest_fingerprint"]
                        != receipt.manifest_fingerprint
                        or int(row["run_target_generation"])
                        != receipt.binding.generation
                        or row["run_payload_digest"] != receipt.payload_digest
                        or receipt.verified_at > completed_at
                        or observation is None
                    ):
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_proof_invalid"
                        )
                    if row["state"] == "terminal":
                        if (
                            row["dispatch_certainty"] != "response_received"
                            or row["outcome"] != "succeeded"
                            or row["reason_code"] != "verification_succeeded"
                            or row["terminal_at"] != _utc_text(completed_at)
                            or row["retry_after_seconds"] is not None
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_verification_proof_invalid"
                            )
                        connection.rollback()
                        return _verification_job(row)
                    changed = connection.exec_driver_sql(
                        "UPDATE collection_cloud_verification_job SET "
                        "state='terminal',terminal_at=?,outcome='succeeded',"
                        "reason_code='verification_succeeded',"
                        "retry_after_seconds=NULL,record_version=record_version+1 "
                        "WHERE job_id=? AND state='admitted' "
                        "AND dispatch_certainty='response_received' "
                        "AND reason_code='verification_commit_pending' "
                        "AND outcome IS NULL AND terminal_at IS NULL",
                        (_utc_text(completed_at), row["job_id"]),
                    )
                    if changed.rowcount != 1:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_proof_invalid"
                        )
                    final = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job "
                            "WHERE job_id=?",
                            (row["job_id"],),
                        )
                        .mappings()
                        .one()
                    )
                    connection.commit()
                    return _verification_job(final)
        except OllamaCloudAdmissionRepositoryErrorV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, OSError, ValueError, TypeError):
            raise OllamaCloudAdmissionRepositoryErrorV1() from None

    def finalize_verification_interrupted(
        self, proof: OllamaCloudVerificationInterruptionProofV1
    ) -> OllamaCloudVerificationJobViewV1:
        """Terminalize a failed run only after trusted absence checks completed."""
        if not isinstance(proof, OllamaCloudVerificationInterruptionProofV1):
            raise OllamaCloudAdmissionRepositoryErrorV1(
                "ollama_cloud_verification_proof_invalid"
            )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = (
                        connection.exec_driver_sql(
                            "SELECT j.*,a.state AS admission_state,"
                            "a.outcome AS admission_outcome,"
                            "a.account_id AS admission_account_id,"
                            "a.schedule_id AS admission_schedule_id,"
                            "x.run_id AS journal_run_id,x.phase AS journal_phase,"
                            "x.outcome AS journal_outcome,"
                            "x.failure_code AS journal_failure_code,"
                            "r.state AS run_state,r.account_id AS run_account_id,"
                            "r.schedule_id AS run_schedule_id,"
                            "r.provider_key AS run_provider_key,"
                            "r.provider_target_kind AS run_target_kind,"
                            "r.provider_target_id AS run_target_id,"
                            "r.capability_id AS run_capability_id,"
                            "r.source_id AS run_source_id,"
                            "r.target_generation AS run_target_generation,"
                            "r.completed_at AS run_completed_at "
                            "FROM collection_cloud_verification_job j "
                            "JOIN collection_ollama_cloud_admission a "
                            "ON a.admission_id=j.admission_id "
                            "JOIN collection_cloud_attempt_journal x "
                            "ON x.admission_id=j.admission_id "
                            "JOIN collection_run r ON r.run_id=j.run_id "
                            "WHERE j.job_id=? AND j.run_id=? AND j.admission_id=?",
                            (
                                proof.job_id.value,
                                proof.run_id.value,
                                proof.admission_id.value,
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_proof_invalid"
                        )
                    decision = verification_completion_decision(
                        "succeeded",
                        cast(CollectionRunStateV1, str(row["run_state"])),
                        False,
                    )
                    completed_at = _utc_value(row["run_completed_at"])
                    if (
                        decision != "verification_commit_interrupted"
                        or not verification_lineage_matches(
                            expected_run_id=proof.run_id.value,
                            job_run_id=row["run_id"],
                            journal_run_id=row["journal_run_id"],
                            job_account_id=row["account_id"],
                            admission_account_id=row["admission_account_id"],
                            run_account_id=row["run_account_id"],
                            job_schedule_id=row["schedule_id"],
                            admission_schedule_id=row["admission_schedule_id"],
                            run_schedule_id=row["run_schedule_id"],
                        )
                        or proof.checked_at < completed_at
                        or row["admission_state"] != "completed"
                        or row["admission_outcome"] != "succeeded"
                        or row["journal_phase"] != "outcome"
                        or row["journal_outcome"] != "succeeded"
                        or row["journal_failure_code"] is not None
                        or row["run_account_id"] != row["account_id"]
                        or row["run_provider_key"] != _PROVIDER_KEY
                        or row["run_target_kind"] != "cloud_service"
                        or row["run_target_id"] != row["access_target_id"]
                        or row["run_capability_id"] != _CAPABILITY_ID
                        or row["run_source_id"] != "ollama.cloud.balance.v1"
                        or int(row["run_target_generation"])
                        != int(row["binding_generation"])
                    ):
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_proof_invalid"
                        )
                    if row["state"] == "terminal":
                        if (
                            row["dispatch_certainty"] != "response_received"
                            or row["outcome"] != VERIFICATION_RESPONSE_OUTCOME_V1
                            or row["reason_code"] != "verification_commit_interrupted"
                            or row["terminal_at"] != _utc_text(completed_at)
                            or row["retry_after_seconds"] is not None
                        ):
                            raise OllamaCloudAdmissionRepositoryErrorV1(
                                "ollama_cloud_verification_proof_invalid"
                            )
                        connection.rollback()
                        return _verification_job(row)
                    changed = connection.exec_driver_sql(
                        "UPDATE collection_cloud_verification_job SET "
                        "state='terminal',terminal_at=?,outcome=?,"
                        "reason_code='verification_commit_interrupted',"
                        "retry_after_seconds=NULL,record_version=record_version+1 "
                        "WHERE job_id=? AND state='admitted' "
                        "AND dispatch_certainty='response_received' "
                        "AND reason_code='verification_commit_pending' "
                        "AND outcome IS NULL AND terminal_at IS NULL",
                        (
                            _utc_text(completed_at),
                            VERIFICATION_RESPONSE_OUTCOME_V1,
                            row["job_id"],
                        ),
                    )
                    if changed.rowcount != 1:
                        raise OllamaCloudAdmissionRepositoryErrorV1(
                            "ollama_cloud_verification_proof_invalid"
                        )
                    final = (
                        connection.exec_driver_sql(
                            "SELECT * FROM collection_cloud_verification_job "
                            "WHERE job_id=?",
                            (row["job_id"],),
                        )
                        .mappings()
                        .one()
                    )
                    connection.commit()
                    return _verification_job(final)
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
            "SELECT outcome,response_received_at,retry_after_seconds,completion_jitter_seconds,failure_code "
            "FROM collection_cloud_attempt_journal WHERE admission_id=? AND phase='outcome'",
            (completion.admission_id.value,),
        ).first()
        if intent is None or tuple(intent[:4]) != (
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
        job = connection.exec_driver_sql(
            "SELECT job_id FROM collection_cloud_verification_job WHERE admission_id=?",
            (completion.admission_id.value,),
        ).scalar_one_or_none()
        if job is not None:
            if completion.outcome == "succeeded":
                decision = verification_completion_decision(
                    completion.outcome, "running", False
                )
                if decision != "pending":
                    raise OllamaCloudAdmissionRepositoryErrorV1(
                        "ollama_cloud_completion_conflict"
                    )
                finished = connection.exec_driver_sql(
                    "UPDATE collection_cloud_verification_job SET "
                    "dispatch_certainty='response_received',"
                    "reason_code='verification_commit_pending',"
                    "record_version=record_version+1 WHERE job_id=? "
                    "AND state='admitted' AND admission_id=? "
                    "AND outcome IS NULL AND terminal_at IS NULL",
                    (job, completion.admission_id.value),
                )
            else:
                finished = connection.exec_driver_sql(
                    "UPDATE collection_cloud_verification_job SET state='terminal',"
                    "dispatch_certainty='response_received',terminal_at=?,outcome=?,"
                    "reason_code=?,retry_after_seconds=?,record_version=record_version+1 "
                    "WHERE job_id=? AND state='admitted' AND admission_id=?",
                    (
                        completed_text,
                        completion.outcome,
                        intent[4],
                        completion.retry_after_seconds,
                        job,
                        completion.admission_id.value,
                    ),
                )
            if finished.rowcount != 1:
                raise OllamaCloudAdmissionRepositoryErrorV1(
                    "ollama_cloud_completion_conflict"
                )
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
