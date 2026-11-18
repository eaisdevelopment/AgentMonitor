"""Recover unchanged genuine pre-finalization storage, without provider replay."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.composition.billing_collection import BillingCollectionV1
from agentmonitor.composition.billing_worker_supervisor import BillingWorkerSupervisorV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1

from backend.tests.live.ollama.test_budget_monetary_persistence import (
    _check_normalized_storage,
    _counts,
    _receipt,
    _require,
)

LIVE = Path("/home/dev/.local/share/agentmonitor")


def _intent(
    reference: DatabaseRefV1, run: BudgetCollectionRunViewV1
) -> tuple[tuple[object, ...] | None, tuple[int, ...]]:
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as db:
            row = db.exec_driver_sql(
                "SELECT primary_request_id,request_digest,requested_at,deadline_at,"
                "target_generation,payload_digest FROM collection_run WHERE run_id=?",
                (run.run_id.value,),
            ).one_or_none()
            counts = tuple(
                int(db.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar_one())
                for table in (
                    "collection_run",
                    "collection_request",
                    "collection_ollama_cloud_admission",
                )
            )
    return None if row is None else tuple(row), counts


def _release_lock(supervisor: BillingWorkerSupervisorV1) -> None:
    for descriptor in (supervisor._lock_fd, supervisor._root_fd):
        if descriptor is not None:
            os.close(descriptor)
    supervisor._lock_fd = supervisor._root_fd = None


def test_genuine_prefinalization_snapshot_recovers_original_receipt(
    tmp_path: Path,
) -> None:
    """One real worker read; subsequent recovery is isolated and credential-free."""
    tmp_path.chmod(0o700)
    destination = tmp_path / "agentmonitor.db"
    os.close(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    live = DatabaseRefV1(LIVE / "agentmonitor.db", LIVE)
    live_runs = SqliteCollectionRepositoryV1(live)
    before = {
        run.run_id for run in live_runs.list_runs(None, None, datetime.now(UTC), 500)
    }
    selected = subprocess.run(
        [
            "systemctl",
            "--user",
            "show",
            "agentmonitor-dashboard.service",
            "--property=WorkingDirectory",
            "--value",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    runtime = Path(selected.stdout.strip())
    _require(
        selected.returncode == 0
        and runtime.parent == LIVE / "releases"
        and re.fullmatch(r"m6-candidate-[a-f0-9]{40}-[a-f0-9]{64}", runtime.name)
        is not None,
        "installed_runtime_source_unavailable",
    )
    source = runtime / "backend/src"
    _require(
        (source / "agentmonitor/composition/billing_worker.py").is_file(),
        "installed_worker_source_unavailable",
    )
    supervisor = BillingWorkerSupervisorV1(LIVE)
    # The normal dispatcher chooses among all admitted financial sources.
    # A provider-specific gate does not establish that any report is due.
    # Keep the same bounded window as the existing native cost readiness check.
    wait_deadline = time.monotonic() + 1000
    snapshot_errors = {
        "M7 SNAPSHOT: capture_failed\n": "genuine_commit_snapshot_copy_failed",
        "M7 SNAPSHOT: not_observed\n": "no_eligible_report_commit_observed",
    }
    try:
        while True:
            while True:
                _require(
                    time.monotonic() < wait_deadline,
                    "installed_collection_slot_unavailable",
                )
                try:
                    lock = supervisor._acquire_lock()
                except BlockingIOError:
                    pass
                else:
                    if supervisor._read_marker() == "":
                        break
                    _release_lock(supervisor)
                time.sleep(0.25)
            authority = uuid.uuid4().hex
            child = Path(__file__).with_name("capture_budget_commit_snapshot.py")
            with subprocess.Popen(
                [sys.executable, str(child), str(LIVE), str(destination), authority],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                pass_fds=(lock,),
                env={
                    "PATH": "/usr/bin:/bin",
                    "HOME": "/home/dev",
                    "LANG": "C.UTF-8",
                    "PYTHONPATH": str(source),
                },
            ) as process:
                try:
                    output, _diagnostic = process.communicate(
                        "START " + authority + "\n", timeout=125
                    )
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=5)
                    pytest.fail("owned_snapshot_worker_timeout", pytrace=False)
            _require(process.returncode == 0, "owned_snapshot_worker_did_not_complete")
            if output == "M7 SNAPSHOT: not_started\n":
                # Only the owned worker's no-collection witness permits another
                # admission attempt. Never retry a started provider collection.
                _release_lock(supervisor)
                print("M7 RECEIPT RECOVERY: no collection started; waiting", flush=True)
                time.sleep(5)
                continue
            _require(
                output == "M7 SNAPSHOT: captured\n",
                snapshot_errors.get(output, "genuine_commit_snapshot_output_invalid"),
            )
            break
    finally:
        _release_lock(supervisor)

    reference = DatabaseRefV1(destination, tmp_path)
    runs = SqliteCollectionRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    pending = [
        run
        for run in runs.list_runs(None, None, datetime.now(UTC), 500)
        if isinstance(run, BudgetCollectionRunViewV1)
        and run.run_id not in before
        and run.state == "committing"
    ]
    _require(len(pending) == 1, "one_genuine_committing_snapshot_required")
    run = pending[0]
    receipt = _receipt(reference, run)
    _require(run.account_id is not None, "genuine_report_account_required")
    assert run.account_id is not None
    stored = reports.get_report(run.account_id, receipt.report_id)
    _require(stored is not None, "genuine_committed_report_required")
    assert stored is not None
    _check_normalized_storage(reference, stored, receipt)
    _require(
        live_runs.get_run(run.run_id).state == run.outcome_code,
        "original_live_worker_not_finalized",
    )
    original_intent, original_counts = _intent(reference, run), _counts(reference)
    print(
        "M7 RECEIPT RECOVERY: captured; live finalized; aging private snapshot",
        flush=True,
    )
    # The live run already finished. Only the unchanged private snapshot ages.
    recover_at = max(run.deadline_at, datetime.now(UTC) + timedelta(seconds=121))
    while datetime.now(UTC) < recover_at:
        time.sleep(min(20, max(0.01, (recover_at - datetime.now(UTC)).total_seconds())))
    first_recovered: BudgetCollectionRunViewV1 | None = None
    for _ in range(2):
        collector = BillingCollectionV1(
            tmp_path, credential_env_file=None, deadline_monotonic=time.monotonic() + 30
        )
        _require(
            collector.run(recovery_only=True) == 0, "isolated_receipt_recovery_failed"
        )
        recovered = runs.get_run(run.run_id)
        _require(
            isinstance(recovered, BudgetCollectionRunViewV1), "recovered_type_changed"
        )
        assert isinstance(recovered, BudgetCollectionRunViewV1)
        _require(
            recovered.state == run.outcome_code
            and recovered.report_id == receipt.report_id,
            "original_receipt_not_reconciled",
        )
        if first_recovered is None:
            first_recovered = recovered
        else:
            _require(recovered == first_recovered, "repeat_recovery_changed_run")
        _require(_receipt(reference, recovered) == receipt, "recovery_changed_receipt")
        _require(
            reports.get_report(run.account_id, receipt.report_id) == stored,
            "recovery_changed_report",
        )
        _require(
            _counts(reference) == original_counts, "recovery_added_financial_facts"
        )
        _require(
            _intent(reference, recovered) == original_intent,
            "recovery_changed_intent_or_created_request",
        )
    print(
        "M7 RECEIPT RECOVERY: PASSED genuine_prefinalization_snapshot "
        + ("monetary" if stored.report.cost_buckets else "nonmonetary")
        + " no_recollection no_duplicate_facts"
    )
