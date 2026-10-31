"""M04 real file-backed SQLite admission and idempotency evidence."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
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
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    CollectionRepositoryErrorV1,
    SqliteCollectionRepositoryV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunAdmissionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.runner import (
    RequestManualCollectionV1,
)

NOW = datetime(2026, 9, 22, 14, 0, tzinfo=UTC)


def _repository(tmp_path: Path) -> SqliteCollectionRepositoryV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return SqliteCollectionRepositoryV1(reference)


def _admission(
    *,
    digest: str = "a" * 64,
    idempotency_digest: str = "f" * 64,
    run_id: str = "collection-run-one",
    request_id: str = "collection-request-one",
    schedule_id: str = "collection-schedule-one",
    correlation_id: str = "correlation-one",
    budget_units: int = 1,
    target_key_digest: str = "b" * 64,
    resource_id: str = "resource-one",
    registry_revision: int = 1,
    target_generation: int = 1,
    manifest_fingerprint: str = "e" * 64,
    collection_policy_version: str = "1.0.0",
) -> CollectionRunAdmissionV1:
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1(run_id),
        schedule_id=OpaqueIdV1(schedule_id),
        request_id=OpaqueIdV1(request_id),
        trigger="manual",
        operation_family="collect.subscription.quota",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="owner_session",
        request_principal_id=OpaqueIdV1("owner-one"),
        correlation_id=OpaqueIdV1(correlation_id),
        causation_id=None,
        target_key_digest=target_key_digest,
        provider_key="claude",
        installation_id=OpaqueIdV1("installation-one"),
        account_id=OpaqueIdV1("account-one"),
        profile_id=OpaqueIdV1("profile-one"),
        resource_id=OpaqueIdV1(resource_id),
        capability_id="subscription.quota",
        source_id="claude.subscription.usage.screen_reader",
        adapter_version="1.0.0",
        provider_version="2.1.278",
        adapter_protocol_version="1.0.0",
        manifest_fingerprint=manifest_fingerprint,
        collection_policy_version=collection_policy_version,
        registry_revision=registry_revision,
        retry_chain_id=OpaqueIdV1("retry-chain-one"),
        attempt_ordinal=1,
        target_generation=target_generation,
        scheduler_instance_id=OpaqueIdV1("scheduler-instance-one"),
        lease_policy_version="1.0.0",
        budget_policy_id="provider-request-budget-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest="d" * 64,
        budget_dimension="provider_requests",
        budget_unit="request",
        budget_units=budget_units,
        budget_limit_units=1,
        budget_window_start=NOW,
        budget_window_end=datetime(2026, 9, 22, 14, 1, tzinfo=UTC),
        payload_schema="ProviderQuotaInputV1@1",
        idempotency_key_digest=idempotency_digest,
        request_digest=digest,
        requested_at=NOW,
        deadline_at=datetime(2026, 9, 22, 14, 0, 30, tzinfo=UTC),
    )


def test_admission_is_durable_and_same_request_is_idempotent(tmp_path: Path) -> None:
    """M04-DB-007: identical manual admission returns the same durable run."""
    repository = _repository(tmp_path)

    request_manual = RequestManualCollectionV1(repository)
    first = request_manual(_admission())
    replay = request_manual(_admission())

    assert first == replay
    assert first.state == "queued"
    assert repository.get_run(first.run_id) == first
    assert repository.get_admission_state(first.run_id) == ("active", "reserved")


def test_same_run_with_different_digest_conflicts_without_overwrite(
    tmp_path: Path,
) -> None:
    """M04 admission mechanism: a run identity cannot change fingerprint."""
    repository = _repository(tmp_path)
    first = repository.admit_run(_admission())

    try:
        repository.admit_run(_admission(digest="c" * 64))
    except CollectionRepositoryErrorV1 as error:
        assert error.code == "collection_idempotency_conflict"
    else:
        raise AssertionError("conflicting admission was accepted")

    assert repository.get_run(first.run_id) == first


def test_same_manual_idempotency_key_coalesces_a_new_request_identity(
    tmp_path: Path,
) -> None:
    """M04-DB-007: a manual retry links to the first admitted run."""
    repository = _repository(tmp_path)
    first = repository.admit_run(_admission())

    replay = repository.admit_run(
        _admission(
            run_id="collection-run-retry",
            request_id="collection-request-retry",
        )
    )

    assert replay == first
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM collection_request"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM collection_run"
                ).scalar_one()
                == 1
            )


def test_same_manual_idempotency_key_rejects_a_different_fingerprint(
    tmp_path: Path,
) -> None:
    """M04-DB-008: a reused key cannot change the admitted target/fingerprint."""
    repository = _repository(tmp_path)
    first = repository.admit_run(_admission())

    try:
        repository.admit_run(
            _admission(
                digest="c" * 64,
                run_id="collection-run-retry",
                request_id="collection-request-retry",
                target_key_digest="2" * 64,
                resource_id="resource-two",
            )
        )
    except CollectionRepositoryErrorV1 as error:
        assert error.code == "collection_idempotency_conflict"
    else:
        raise AssertionError("reused idempotency key changed the request")

    assert repository.get_run(first.run_id) == first


def test_transition_requires_the_current_durable_fencing_token(
    tmp_path: Path,
) -> None:
    """M04 fencing mechanism: a wrong token cannot advance an admitted run."""
    repository = _repository(tmp_path)
    run = repository.admit_run(_admission())

    try:
        repository.mark_running(run.run_id, NOW, fencing_token=2)
    except CollectionRepositoryErrorV1 as error:
        assert error.code == "collection_fencing_conflict"
    else:
        raise AssertionError("stale fencing token advanced the run")

    assert repository.get_run(run.run_id).state == "queued"
    assert repository.get_admission_state(run.run_id) == ("active", "reserved")


def test_failed_terminal_transition_keeps_dispatched_budget_conservative(
    tmp_path: Path,
) -> None:
    """M04-DB-006/011: dispatched work remains counted after failure."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    run = repository.admit_run(_admission())
    repository.mark_running(run.run_id, NOW, fencing_token=run.fencing_token)

    repository.finalize_failed(
        CollectionFailedV1(
            run_id=run.run_id,
            terminal_state="failed",
            error_code="provider_unavailable",
            completed_at=NOW,
        ),
        fencing_token=run.fencing_token,
    )

    assert repository.get_run(run.run_id).state == "failed"
    assert repository.get_admission_state(run.run_id) == (
        "released",
        "expired_conservative",
    )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            request = connection.exec_driver_sql(
                "SELECT state FROM collection_request WHERE request_id=?",
                ("collection-request-one",),
            ).scalar_one()
            event_count = connection.exec_driver_sql(
                "SELECT count(*) FROM collection_event_outbox WHERE subject_id=?",
                (run.run_id.value,),
            ).scalar_one()
    assert request == "completed"
    assert event_count == 1


def test_concurrent_scoped_budget_admission_has_one_winner(tmp_path: Path) -> None:
    """M04-DB-006: concurrent reservations cannot exceed the scoped ceiling."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    barrier = Barrier(2)
    admissions = (
        _admission(),
        _admission(
            run_id="collection-run-two",
            request_id="collection-request-two",
            schedule_id="collection-schedule-two",
            idempotency_digest="1" * 64,
            target_key_digest="2" * 64,
            resource_id="resource-two",
        ),
    )

    def admit(index: int) -> str:
        repository = SqliteCollectionRepositoryV1(reference)
        barrier.wait()
        try:
            repository.admit_run(admissions[index])
        except CollectionRepositoryErrorV1 as error:
            return error.code
        return "admitted"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(admit, range(2)))

    assert sorted(results) == ["admitted", "collection_budget_exhausted"]


@pytest.mark.parametrize(
    "changed",
    (
        replace(
            _admission(
                run_id="collection-run-two",
                request_id="collection-request-two",
                idempotency_digest="1" * 64,
                budget_units=0,
            ),
            registry_revision=2,
        ),
        replace(
            _admission(
                run_id="collection-run-two",
                request_id="collection-request-two",
                idempotency_digest="1" * 64,
                budget_units=0,
            ),
            source_id="source-two",
        ),
        replace(
            _admission(
                run_id="collection-run-two",
                request_id="collection-request-two",
                idempotency_digest="1" * 64,
                budget_units=0,
            ),
            manifest_fingerprint="2" * 64,
        ),
        replace(
            _admission(
                run_id="collection-run-two",
                request_id="collection-request-two",
                idempotency_digest="1" * 64,
                budget_units=0,
            ),
            collection_policy_version="1.0.1",
        ),
    ),
    ids=("registry-revision", "source", "manifest", "collection-policy"),
)
def test_same_schedule_generation_rejects_changed_policy_snapshot(
    tmp_path: Path,
    changed: CollectionRunAdmissionV1,
) -> None:
    """M4-GEN-003: one generation cannot change any policy input."""
    repository = _repository(tmp_path)
    first = repository.admit_run(_admission(budget_units=0))
    repository.mark_running(first.run_id, NOW, fencing_token=first.fencing_token)
    repository.finalize_failed(
        CollectionFailedV1(
            run_id=first.run_id,
            terminal_state="failed",
            error_code="provider_unavailable",
            completed_at=NOW,
        ),
        fencing_token=first.fencing_token,
    )

    try:
        repository.admit_run(changed)
    except CollectionRepositoryErrorV1 as error:
        assert error.code == "collection_generation_conflict"
    else:
        raise AssertionError("same generation accepted changed policy snapshot")


def test_active_lease_blocks_generation_advance_without_schedule_mutation(
    tmp_path: Path,
) -> None:
    """M04-DB-004/012: a newer policy cannot refence active work."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    first = repository.admit_run(
        _admission(registry_revision=48, target_generation=48, budget_units=0)
    )

    try:
        repository.admit_run(
            _admission(
                run_id="collection-run-two",
                request_id="collection-request-two",
                idempotency_digest="1" * 64,
                registry_revision=48,
                target_generation=49,
                manifest_fingerprint="2" * 64,
                budget_units=0,
            )
        )
    except CollectionRepositoryErrorV1 as error:
        assert error.code == "collection_schedule_conflict"
    else:
        raise AssertionError("active lease was replaced by a newer generation")

    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            generation = connection.exec_driver_sql(
                "SELECT target_generation FROM collection_schedule "
                "WHERE schedule_id='collection-schedule-one'"
            ).scalar_one()
            second_run_count = connection.exec_driver_sql(
                "SELECT count(*) FROM collection_run WHERE run_id='collection-run-two'"
            ).scalar_one()
            second_request_count = connection.exec_driver_sql(
                "SELECT count(*) FROM collection_request "
                "WHERE request_id='collection-request-two'"
            ).scalar_one()
            lease = connection.exec_driver_sql(
                "SELECT run_id, fencing_token FROM collection_lease "
                "WHERE schedule_id='collection-schedule-one'"
            ).one()
    assert generation == 48
    assert second_run_count == 0
    assert second_request_count == 0
    assert lease == (first.run_id.value, first.fencing_token)


def test_interrupted_committing_run_resolves_without_reinvoking_provider(
    tmp_path: Path,
) -> None:
    """M04-DB-019: definitive absent receipt closes interrupted commit safely."""
    repository = _repository(tmp_path)
    run = repository.admit_run(_admission())
    repository.mark_running(run.run_id, NOW, fencing_token=run.fencing_token)
    repository.mark_committing(
        run.run_id,
        fencing_token=run.fencing_token,
        payload_digest="9" * 64,
        committing_at=NOW,
        terminal_state="succeeded",
    )

    repository.finalize_interrupted(
        CollectionFailedV1(
            run_id=run.run_id,
            terminal_state="failed",
            error_code="collection_commit_interrupted",
            completed_at=NOW,
        ),
        fencing_token=run.fencing_token,
    )

    resolved = repository.get_run(run.run_id)
    assert resolved.state == "failed"
    assert resolved.error_code == "collection_commit_interrupted"
    assert repository.get_admission_state(run.run_id) == (
        "released",
        "expired_conservative",
    )


def test_terminal_outbox_orders_per_schedule_and_preserves_correlation(
    tmp_path: Path,
) -> None:
    """M04 outbox mechanism: schedule order and request correlation persist."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteCollectionRepositoryV1(reference)
    first = repository.admit_run(_admission(budget_units=0))
    repository.mark_running(first.run_id, NOW, fencing_token=first.fencing_token)
    repository.finalize_failed(
        CollectionFailedV1(
            run_id=first.run_id,
            terminal_state="failed",
            error_code="provider_unavailable",
            completed_at=NOW,
        ),
        fencing_token=first.fencing_token,
    )
    second = repository.admit_run(
        _admission(
            run_id="collection-run-two",
            request_id="collection-request-two",
            idempotency_digest="1" * 64,
            correlation_id="correlation-two",
            budget_units=0,
        )
    )
    repository.mark_running(second.run_id, NOW, fencing_token=second.fencing_token)
    repository.finalize_failed(
        CollectionFailedV1(
            run_id=second.run_id,
            terminal_state="failed",
            error_code="provider_unavailable",
            completed_at=NOW,
        ),
        fencing_token=second.fencing_token,
    )

    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            events = connection.exec_driver_sql(
                "SELECT stream_id, stream_sequence, correlation_id FROM "
                "collection_event_outbox ORDER BY stream_sequence"
            ).fetchall()
    assert [tuple(row) for row in events] == [
        ("collection-schedule-one", 1, "correlation-one"),
        ("collection-schedule-one", 2, "correlation-two"),
    ]
