"""Real inert financial-worker isolation and pure observation-bound policy."""

import json
import sqlite3
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.automation.implementations import m6_controlled_recovery_interval as recovery

ROOT = Path(__file__).resolve().parents[3]


def test_financial_mode_rejects_invalid_revision_before_service_access() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.automation.implementations.m6_controlled_recovery_interval",
            "--financial",
            "--revision",
            "invalid",
            "--attempt-id",
            uuid.uuid4().hex,
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 3
    assert not result.stdout


def test_real_financial_child_is_inert_until_both_parent_grants(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    (tmp_path / ".ollama-env.lock").touch(mode=0o600)
    worker = recovery._start_worker(root, env_file, uuid.uuid4().hex, financial=True)
    try:
        assert worker.namespace_inode != recovery._namespace("self")
        assert worker.process.stdin is not None
        worker.process.stdin.close()
        assert worker.process.wait(timeout=5) == 3
    finally:
        worker.close()
    assert list(root.iterdir()) == []
    assert env_file.stat().st_size == 0


def test_real_financial_namespace_keeps_only_billing_supervisor_lock(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    (tmp_path / ".ollama-env.lock").touch(mode=0o600)
    worker = None
    try:
        with recovery._supervisor_lock(root, financial=True) as descriptor:
            worker = recovery._start_worker(
                root, env_file, uuid.uuid4().hex, descriptor, financial=True
            )
        with (
            pytest.raises(BlockingIOError),
            recovery._supervisor_lock(root, financial=True),
        ):
            pass
        with recovery._supervisor_lock(root):
            assert not (root / "agentmonitor.db").exists()
    finally:
        if worker is not None:
            worker.close()
    with recovery._supervisor_lock(root, financial=True):
        assert not (root / "agentmonitor.db").exists()


def test_financial_observation_respects_actual_retry_time_without_rewriting_it() -> (
    None
):
    now = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
    retry = now + timedelta(minutes=14)
    assert recovery.financial_observation_end(now, retry) == retry + timedelta(
        seconds=600
    )
    assert recovery.financial_observation_end(now, None) == now + timedelta(seconds=600)
    with pytest.raises(ValueError, match="m7_financial_retry_unbounded"):
        recovery.financial_observation_end(now, now + timedelta(hours=1))


def test_financial_observation_waits_for_scheduled_context_after_unknown_cooldown() -> (
    None
):
    now = datetime(2026, 11, 17, 19, 31, tzinfo=UTC)
    cooldown = now + timedelta(minutes=5)
    scheduled = now + timedelta(minutes=13)
    assert recovery.financial_observation_end(
        now, cooldown, schedule_due=scheduled
    ) == scheduled + timedelta(seconds=600)
    with pytest.raises(ValueError, match="m7_financial_retry_unbounded"):
        recovery.financial_observation_end(
            now, cooldown, schedule_due=now + timedelta(minutes=16)
        )


def test_financial_slot_waits_for_both_actual_allowance_and_schedule() -> None:
    now = datetime(2026, 11, 18, 5, 0, tzinfo=UTC)
    due = now + timedelta(seconds=30)
    allowance = now + timedelta(seconds=90)
    assert (
        recovery.financial_slot_ready_at(now, ("not_due", allowance), due) == allowance
    )
    assert recovery.financial_slot_ready_at(now, ("ready", None), due) == due
    assert (
        recovery.financial_slot_ready_at(allowance, ("ready", None), due) == allowance
    )


@pytest.mark.parametrize("state", ["busy", "unresolved", "unknown"])
def test_financial_slot_does_not_infer_release_from_a_lease_time(state: str) -> None:
    now = datetime(2026, 11, 18, 5, 0, tzinfo=UTC)
    assert recovery.financial_slot_ready_at(now, (state, now), now) is None


def test_financial_slot_requires_a_reported_cooldown_boundary() -> None:
    now = datetime(2026, 11, 18, 5, 0, tzinfo=UTC)
    assert recovery.financial_slot_ready_at(now, ("not_due", None), now) is None


def test_financial_recovery_waits_when_another_cloud_context_has_first_turn() -> None:
    from agentmonitor.composition.budget_dispatch import BudgetWorkV1

    now = datetime(2026, 11, 18, 6, 9, tzinfo=UTC)
    monetary_key = ("ollama", "monetary-scope", "self-7d")
    other = BudgetWorkV1(("ollama", "other-scope", "self-30d"), None, now, None, True)
    monetary = BudgetWorkV1(monetary_key, now, now, None, True)
    assert not recovery.financial_has_next_turn(
        (other, monetary), frozenset({monetary_key})
    )
    assert recovery.financial_has_next_turn(
        (monetary, other), frozenset({monetary_key})
    )


def test_financial_recovery_does_not_isolate_owner_queued_or_absent_work() -> None:
    from agentmonitor.composition.budget_dispatch import BudgetWorkV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    now = datetime(2026, 11, 18, 6, 9, tzinfo=UTC)
    key = ("ollama", "monetary-scope", "self-7d")
    queued = BudgetWorkV1(key, now, now, OpaqueIdV1("owner-request"), True)
    not_due = BudgetWorkV1(key, now, now, None, False)
    assert not recovery.financial_has_next_turn((queued,), frozenset({key}))
    assert not recovery.financial_has_next_turn((not_due,), frozenset({key}))
    assert not recovery.financial_has_next_turn((), frozenset({key}))


def test_real_financial_go_without_start_cannot_open_storage(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    (tmp_path / ".ollama-env.lock").touch(mode=0o600)
    attempt = uuid.uuid4().hex
    worker = recovery._start_worker(root, env_file, attempt, financial=True)
    try:
        assert worker.process.stdin is not None
        worker.process.stdin.write(f"GO {attempt}\n".encode())
        worker.process.stdin.close()
        assert worker.process.wait(timeout=5) == 3
        assert worker.process.stdout is not None
        assert json.loads(worker.process.stdout.read()) == {"worker_exit_code": 5}
    finally:
        worker.close()
    assert list(root.iterdir()) == []
    assert env_file.stat().st_size == 0


def test_real_financial_storage_failure_retains_closed_diagnostic(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    database = root / "agentmonitor.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version=0")
    database.chmod(0o600)
    env_file = tmp_path / ".env"
    env_file.touch(mode=0o600)
    (tmp_path / ".ollama-env.lock").touch(mode=0o600)
    attempt = uuid.uuid4().hex
    worker = recovery._start_worker(root, env_file, attempt, financial=True)
    try:
        assert worker.process.stdin is not None
        worker.process.stdin.write(f"GO {attempt}\nSTART {attempt}\n".encode())
        worker.process.stdin.flush()
        assert worker.process.wait(timeout=15) == 3
        assert worker.process.stdout is not None
        assert json.loads(worker.process.stdout.read()) == {"worker_exit_code": 4}
        assert worker.process.stderr is not None
        diagnostic = recovery.financial_worker_diagnostic(
            worker.process.stderr.read(4096)
        )
        assert diagnostic is not None
        assert diagnostic.startswith("BILLING_WORKER_FAILURE phase=")
        assert " source=" in diagnostic
        assert str(tmp_path) not in diagnostic
    finally:
        worker.close()


@pytest.mark.parametrize(
    "output",
    (
        b"arbitrary worker text",
        b"BILLING_WORKER_FAILURE phase=collect type=PrivateError source=unknown:0",
        b"BILLING_WORKER_FAILURE phase=collect type=ValueError source=/private/value:1",
        b"BILLING_WORKER_FAILURE phase=collect type=ValueError "
        b"source=unknown:0 extra=value",
        b"x" * 4097,
    ),
)
def test_financial_diagnostic_rejects_unapproved_worker_output(output: bytes) -> None:
    assert recovery.financial_worker_diagnostic(output) is None


def test_genuine_isolated_dispatch_keeps_unknown_outcome(tmp_path: Path) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
        _private_real_copy,
    )

    reference = _private_real_copy(tmp_path)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            actual = connection.exec_driver_sql(
                "SELECT r.run_id FROM collection_run r "
                "JOIN collection_cloud_attempt_journal j ON j.run_id=r.run_id "
                "WHERE r.source_id='ollama.cloud.usage.v1' "
                "AND j.phase='dispatched' AND j.response_received_at IS NULL "
                "AND (r.state='running' OR (r.state='failed' "
                "AND r.error_code='collection_worker_interrupted')) "
                "ORDER BY r.requested_at DESC LIMIT 1"
            ).scalar_one_or_none()
    assert actual is not None, "genuine_unknown_financial_dispatch_required"
    run = SqliteCollectionRepositoryV1(reference).get_run(OpaqueIdV1(actual))
    assert isinstance(run, BudgetCollectionRunViewV1)
    assert recovery.financial_attempt_kind(reference, run) == "outcome_unknown"


def test_financial_recovery_result_requires_exact_actual_witness() -> None:
    from tools.automation.implementations import auto_m7

    payload: dict[str, object] = {
        "record_type": "agentmonitor.m7_financial_recovery.v1",
        "isolation_scope": "owned_billing_worker_network",
        "status": "passed",
        "reason_code": "m7_financial_source_recovered",
        "source_revision": "a" * 40,
        "attempt_id": "b" * 32,
        "service_invocation_id": "c" * 32,
        "failure_run_id": "failure",
        "old_report_id": "old",
        "recovery_run_id": "recovery",
        "recovery_report_id": "new",
        "old_payload_digest": "d" * 64,
        "recovery_payload_digest": "e" * 64,
        "namespace_cleanup_confirmed": True,
        "namespace_pid": 100,
        "namespace_start_ticks": 1,
        "parent_namespace_inode": 1,
        "isolated_namespace_inode": 2,
        "continuity_run_ids": ["other"],
        "dashboard_observed_at": [
            "2026-11-12T10:00:00+00:00",
            "2026-11-12T10:05:00+00:00",
        ],
        "started_at": "2026-11-12T10:00:00+00:00",
        "isolation_started_at": "2026-11-12T10:00:01+00:00",
        "isolation_ended_at": "2026-11-12T10:00:05+00:00",
        "completed_at": "2026-11-12T10:05:00+00:00",
    }
    assert (
        auto_m7.financial_recovery_result(0, payload, "a" * 40, "b" * 32).status
        == "passed"
    )
    uncertain = payload | {
        "reason_code": "m7_financial_uncertain_source_recovered",
        "failure_kind": "outcome_unknown",
        "uncertainty_released_at": "2026-11-12T10:03:00+00:00",
        "uncertainty_next_allowed_at": "2026-11-12T10:08:00+00:00",
        "completed_at": "2026-11-12T10:10:00+00:00",
    }
    proof = auto_m7.financial_recovery_result(0, uncertain, "a" * 40, "b" * 32)
    assert proof.status == "passed"
    assert proof.reason_code == "m7_financial_uncertain_source_recovered"
    for change in (
        {"failure_kind": "provider_response"},
        {"uncertainty_released_at": None},
        {"uncertainty_next_allowed_at": "2026-11-12T10:03:00+00:00"},
    ):
        assert (
            auto_m7.financial_recovery_result(
                0, uncertain | change, "a" * 40, "b" * 32
            ).status
            == "failed"
        )
    for key, value in (
        ("namespace_cleanup_confirmed", False),
        ("source_revision", "c" * 40),
        ("continuity_run_ids", []),
        ("recovery_run_id", "failure"),
        ("isolated_namespace_inode", 1),
        ("attempt_id", "c" * 32),
    ):
        assert (
            auto_m7.financial_recovery_result(
                0, payload | {key: value}, "a" * 40, "b" * 32
            ).status
            == "failed"
        )
    blocked = payload | {
        "status": "blocked",
        "reason_code": "m7_financial_prior_monetary_report_required",
    }
    assert (
        auto_m7.financial_recovery_result(3, blocked, "a" * 40, "b" * 32).status
        == "blocked"
    )
    assert (
        auto_m7.financial_recovery_result(1, payload, "a" * 40, "b" * 32).status
        == "failed"
    )


def test_existing_recovery_and_continuity_accept_exact_installed_revision() -> None:
    from tools.automation.implementations import auto_m7

    for lane, check in (("live", "recovery"), ("live", None), ("deploy", "continuity")):
        auto_m7.validate_selection(lane, check, "a" * 40)
        with pytest.raises(ValueError, match="m7_selection_invalid"):
            auto_m7.validate_selection(lane, check, "invalid")
    assert auto_m7.BROWSER_CLOSED_TARGETS == (
        "backend/tests/live/ollama/test_m7_browser_closed_collection.py"
        "::test_new_scheduled_financial_receipt_after_controlled_window_closes",
    )
