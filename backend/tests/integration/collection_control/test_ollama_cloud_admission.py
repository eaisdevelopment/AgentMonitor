"""M6 real SQLite evidence for durable Ollama cloud request admission."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
    OllamaCloudAdmissionRepositoryErrorV1,
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.ollama_cloud_admission import (
    AcquireOllamaCloudRequestV1,
    CompleteOllamaCloudRequestV1,
)

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def _insert_schedule(
    reference: DatabaseRefV1,
    suffix: str,
    *,
    state: str = "enabled",
    due_at: datetime = NOW,
) -> None:
    """Create only M04 control state; no provider observation is invented."""
    instant = due_at.isoformat(timespec="microseconds").replace("+00:00", "Z")
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "INSERT INTO collection_schedule (schedule_id,target_key_digest,"
                "provider_key,installation_id,account_id,profile_id,resource_id,"
                "capability_id,state,activity_class,base_interval_seconds,"
                "effective_interval_seconds,target_generation,next_due_at,"
                "not_before_at,backoff_kind,backoff_generation,"
                "consecutive_failure_count,last_attempted_run_id,"
                "last_successful_run_id,last_terminal_outcome_code,record_version,"
                "created_at,updated_at) VALUES (?,?, 'ollama',?,?,NULL,?,"
                "'subscription.quota',?,'unknown',300,300,1,?,NULL,NULL,0,0,"
                "NULL,NULL,NULL,1,?,?)",
                (
                    f"ollama-cloud-{suffix}",
                    suffix * 64,
                    "ollama-installation",
                    f"ollama-account-{suffix}",
                    f"ollama-resource-{suffix}",
                    state,
                    instant,
                    instant,
                    instant,
                ),
            )
            connection.commit()


def _acquire(
    suffix: str,
    started_at: datetime,
    *,
    jitter_seconds: int = 0,
) -> OllamaCloudRequestAcquireV1:
    return OllamaCloudRequestAcquireV1(
        admission_id=OpaqueIdV1(f"ollama-admission-{suffix}"),
        scheduler_instance_id=OpaqueIdV1("ollama-scheduler-one"),
        requested_at=started_at,
        lease_expires_at=started_at + timedelta(seconds=30),
        jitter_seconds=jitter_seconds,
    )


def _complete(
    decision,
    completed_at: datetime,
    *,
    outcome: str = "succeeded",
    retry_after_seconds: int | None = None,
    jitter_seconds: int = 0,
) -> OllamaCloudRequestCompletionV1:
    assert decision.lease is not None
    return OllamaCloudRequestCompletionV1(
        admission_id=decision.lease.admission_id,
        scheduler_instance_id=decision.lease.scheduler_instance_id,
        schedule_id=decision.lease.schedule_id,
        fencing_token=decision.lease.fencing_token,
        started_at=decision.lease.started_at,
        response_received_at=completed_at,
        outcome=outcome,
        retry_after_seconds=retry_after_seconds,
        jitter_seconds=jitter_seconds,
    )


def test_round_robin_cursor_and_spacing_survive_repository_reconstruction(
    tmp_path: Path,
) -> None:
    """M6-A09: enabled due accounts rotate fairly under one durable gate."""
    reference = _database(tmp_path)
    for suffix in ("a", "b", "c"):
        _insert_schedule(reference, suffix)
    repository = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    acquire = AcquireOllamaCloudRequestV1(repository)
    complete = CompleteOllamaCloudRequestV1(repository)

    first = acquire(_acquire("one", NOW))
    assert first.state == "acquired"
    assert first.lease is not None
    assert first.lease.schedule_id == OpaqueIdV1("ollama-cloud-a")
    complete(_complete(first, NOW + timedelta(seconds=1)))

    restarted = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    too_soon = restarted.acquire(_acquire("too-soon", NOW + timedelta(seconds=59)))
    assert too_soon.state == "not_due"
    assert too_soon.retry_at == NOW + timedelta(seconds=60)

    second = restarted.acquire(_acquire("two", NOW + timedelta(seconds=60)))
    assert second.lease is not None
    assert second.lease.schedule_id == OpaqueIdV1("ollama-cloud-b")
    restarted.complete(_complete(second, NOW + timedelta(seconds=61)))
    third = restarted.acquire(_acquire("three", NOW + timedelta(seconds=120)))
    assert third.lease is not None
    assert third.lease.schedule_id == OpaqueIdV1("ollama-cloud-c")
    restarted.complete(_complete(third, NOW + timedelta(seconds=121)))

    no_due_account = restarted.acquire(
        _acquire("none-due", NOW + timedelta(seconds=180))
    )
    assert no_due_account.state == "no_candidate"
    wrapped = restarted.acquire(_acquire("four", NOW + timedelta(seconds=300)))
    assert wrapped.lease is not None
    assert wrapped.lease.schedule_id == OpaqueIdV1("ollama-cloud-a")


def test_one_transaction_wins_concurrent_global_admission(tmp_path: Path) -> None:
    """M6-A09: real SQLite serializes one cloud request across accounts."""
    reference = _database(tmp_path)
    _insert_schedule(reference, "a")
    _insert_schedule(reference, "b")
    barrier = Barrier(2)

    def acquire(suffix: str):
        repository = SqliteOllamaCloudAdmissionRepositoryV1(reference)
        barrier.wait(timeout=2)
        return repository.acquire(_acquire(suffix, NOW))

    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions = tuple(pool.map(acquire, ("one", "two")))

    assert sorted(item.state for item in decisions) == ["acquired", "busy"]
    acquired = next(item for item in decisions if item.state == "acquired")
    busy = next(item for item in decisions if item.state == "busy")
    assert acquired.lease is not None
    assert busy.lease is None
    assert busy.retry_at == NOW + timedelta(seconds=60)


def test_admission_replay_never_authorizes_a_second_dispatch(tmp_path: Path) -> None:
    """M6-A09: durable admission identity is create-once and fenced."""
    reference = _database(tmp_path)
    _insert_schedule(reference, "a")
    repository = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    request = _acquire("one", NOW)

    acquired = repository.acquire(request)
    replay = repository.acquire(request)
    assert acquired.state == "acquired"
    assert replay.state == "replayed_active"
    assert replay.lease is None
    assert replay.retry_at == NOW + timedelta(seconds=60)

    with pytest.raises(OllamaCloudAdmissionRepositoryErrorV1) as conflict:
        repository.acquire(
            replace(request, lease_expires_at=NOW + timedelta(seconds=29))
        )
    assert conflict.value.code == "ollama_cloud_admission_conflict"

    repository.complete(_complete(acquired, NOW + timedelta(seconds=1)))
    terminal_replay = repository.acquire(request)
    assert terminal_replay.state == "replayed_terminal"
    assert terminal_replay.lease is None


def test_retry_after_is_global_and_durable_from_response_time(tmp_path: Path) -> None:
    """M6-A07/A09: a 429 delay survives restart and cannot be shortened."""
    reference = _database(tmp_path)
    _insert_schedule(reference, "a")
    _insert_schedule(reference, "b")
    repository = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    first = repository.acquire(_acquire("one", NOW))

    gate = repository.complete(
        _complete(
            first,
            NOW + timedelta(seconds=10),
            outcome="rate_limited",
            retry_after_seconds=120,
            jitter_seconds=5,
        )
    )
    assert gate.next_allowed_at == NOW + timedelta(seconds=135)
    assert gate.consecutive_rate_limits == 1

    restarted = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    early = restarted.acquire(_acquire("early", NOW + timedelta(seconds=134)))
    assert early.state == "not_due"
    assert early.retry_at == NOW + timedelta(seconds=135)
    next_account = restarted.acquire(_acquire("two", NOW + timedelta(seconds=135)))
    assert next_account.lease is not None
    assert next_account.lease.schedule_id == OpaqueIdV1("ollama-cloud-b")


def test_missing_retry_after_uses_durable_safe_fallback(tmp_path: Path) -> None:
    """M6-A07: a 429 without a usable header remains globally rate limited."""
    reference = _database(tmp_path)
    _insert_schedule(reference, "a")
    repository = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    acquired = repository.acquire(_acquire("one", NOW))

    gate = repository.complete(
        _complete(
            acquired,
            NOW + timedelta(seconds=10),
            outcome="rate_limited",
            retry_after_seconds=None,
            jitter_seconds=2,
        )
    )

    assert gate.next_allowed_at == NOW + timedelta(seconds=62)
    assert gate.consecutive_rate_limits == 1
    restarted = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    assert (
        restarted.acquire(_acquire("early", NOW + timedelta(seconds=61))).state
        == "not_due"
    )


def test_unrepresentable_retry_after_fails_closed_durably(tmp_path: Path) -> None:
    """M6-A07: excessive provider waits never degrade to a shorter delay."""
    reference = _database(tmp_path)
    _insert_schedule(reference, "a")
    repository = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    acquired = repository.acquire(_acquire("one", NOW))

    gate = repository.complete(
        _complete(
            acquired,
            NOW + timedelta(seconds=10),
            outcome="rate_limited",
            retry_after_seconds=2**63 - 1,
        )
    )

    assert gate.next_allowed_at == datetime.max.replace(tzinfo=UTC)
    restarted = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    blocked = restarted.acquire(_acquire("later", NOW + timedelta(days=365)))
    assert blocked.state == "not_due"
    assert blocked.retry_at == datetime.max.replace(tzinfo=UTC)


def test_expired_inflight_admission_retains_spacing_and_advances_fairly(
    tmp_path: Path,
) -> None:
    """M6-A07/A09: crash recovery never starts early or repeats one account."""
    reference = _database(tmp_path)
    _insert_schedule(reference, "a")
    _insert_schedule(reference, "b")
    repository = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    first = repository.acquire(_acquire("one", NOW))
    assert first.lease is not None

    busy = repository.acquire(_acquire("busy", NOW + timedelta(seconds=20)))
    assert busy.state == "busy"
    after_expiry = repository.acquire(_acquire("expired", NOW + timedelta(seconds=30)))
    assert after_expiry.state == "not_due"
    recovered = SqliteOllamaCloudAdmissionRepositoryV1(reference).acquire(
        _acquire("recovered", NOW + timedelta(seconds=60))
    )
    assert recovered.lease is not None
    assert recovered.lease.schedule_id == OpaqueIdV1("ollama-cloud-b")

    replay = repository.acquire(_acquire("one", NOW))
    assert replay.state == "replayed_terminal"
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
            )
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )


def test_disabled_and_future_accounts_are_not_admitted(tmp_path: Path) -> None:
    """M6-A09: rotation selects only enabled accounts whose schedule is due."""
    reference = _database(tmp_path)
    _insert_schedule(reference, "a", state="paused_monitoring_disabled")
    _insert_schedule(reference, "b", due_at=NOW + timedelta(minutes=1))
    _insert_schedule(reference, "c")

    decision = SqliteOllamaCloudAdmissionRepositoryV1(reference).acquire(
        _acquire("one", NOW)
    )

    assert decision.state == "acquired"
    assert decision.lease is not None
    assert decision.lease.schedule_id == OpaqueIdV1("ollama-cloud-c")


def test_wall_clock_rollback_refuses_new_admission(tmp_path: Path) -> None:
    """M6-A07: a clock moving behind durable state never starts early."""
    reference = _database(tmp_path)
    _insert_schedule(reference, "a")
    repository = SqliteOllamaCloudAdmissionRepositoryV1(reference)
    first = repository.acquire(_acquire("one", NOW))
    repository.complete(_complete(first, NOW + timedelta(seconds=1)))

    with pytest.raises(OllamaCloudAdmissionRepositoryErrorV1) as caught:
        repository.acquire(_acquire("rollback", NOW))

    assert caught.value.code == "ollama_cloud_clock_rollback"
