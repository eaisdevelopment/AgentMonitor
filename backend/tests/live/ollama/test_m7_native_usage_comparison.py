"""One explicitly authorized real comparison, and an inert START refusal check.

T009/T015; CTR-COL-006/CTR-CAP-002 2.0.0 unchanged. Alternate real
composition, not proof of the stock worker entrypoint. No payload fixtures.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    ollama_cloud_admission,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.billing_worker_supervisor import BillingWorkerSupervisorV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)

from backend.tests.live.ollama.native_usage_readiness import (
    monetary_schedule_candidates,
    monetary_schedule_ready_at,
)
from backend.tests.live.ollama.test_budget_interrupted_receipt import _release_lock
from backend.tests.live.ollama.test_budget_monetary_persistence import _require
from tools.automation.implementations.m6_cutover import _verify_retained_baseline
from tools.automation.implementations.m6_recovery_interval import _identity

LIVE = Path("/home/dev/.local/share/agentmonitor")
WORKER = Path(__file__).with_name("native_usage_comparison_worker.py")
CHECKOUT = Path(__file__).resolve().parents[4]
CHECKOUT_SOURCE = CHECKOUT / "backend/src"


def test_native_comparison_worker_refuses_before_start_without_state_access(
    tmp_path: Path,
) -> None:
    absent_root = tmp_path / "must-not-be-opened"
    result = subprocess.run(
        [sys.executable, str(WORKER), str(absent_root), uuid.uuid4().hex, "0" * 40],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "PYTHONPATH": str(CHECKOUT_SOURCE) + os.pathsep + str(CHECKOUT),
        },
    )
    _require(result.returncode == 5, "native_comparison_start_refusal_failed")
    _require(
        result.stdout == "" and result.stderr == "", "native_comparison_refusal_output"
    )
    _require(not absent_root.exists(), "native_comparison_prestart_state_created")


def test_native_comparison_namespace_runtime_uses_real_module_paths() -> None:
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
        check=True,
    )
    runtime = Path(selected.stdout.strip())
    revision = _verify_retained_baseline(runtime)[0]
    code = (
        "import sys, agentmonitor; from pathlib import Path; "
        "from backend.tests.live.ollama.native_usage_comparison_worker "
        "import _sealed_runtime; "
        "assert agentmonitor.__file__ is None; "
        "assert _sealed_runtime(Path(sys.argv[1]), sys.argv[2]); "
        "print('sealed')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(LIVE), revision],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "PYTHONPATH": str(runtime / "backend/src") + os.pathsep + str(CHECKOUT),
        },
    )
    _require(
        result.returncode == 0 and result.stdout == "sealed\n" and result.stderr == "",
        "native_comparison_namespace_runtime_fence_failed",
    )


def _run_owned_comparison(
    runtime: Path, expected: str, lock: int
) -> tuple[int, dict[str, object]]:
    authority = uuid.uuid4().hex
    with subprocess.Popen(
        [sys.executable, str(WORKER), str(LIVE), authority, expected],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        pass_fds=(lock,),
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/dev",
            "LANG": "C.UTF-8",
            "PYTHONPATH": str(runtime / "backend/src") + os.pathsep + str(CHECKOUT),
        },
    ) as process:
        try:
            output, diagnostic = process.communicate(
                "START " + authority + "\n", timeout=125
            )
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)
            pytest.fail("native_comparison_owned_worker_timeout", pytrace=False)
    _require(
        len(output) <= 8192 and diagnostic == "",
        "native_comparison_closed_output_invalid",
    )
    if process.returncode in {2, 5, 6}:
        pytest.fail(
            {
                2: "native_comparison_worker_arguments_invalid",
                5: "native_comparison_worker_start_authority_refused",
                6: "native_comparison_worker_runtime_fence_refused",
            }[process.returncode],
            pytrace=False,
        )
    try:
        witness = json.loads(output)
    except (ValueError, TypeError):
        pytest.fail("native_comparison_closed_output_invalid", pytrace=False)
    _require(isinstance(witness, dict), "native_comparison_closed_output_invalid")
    assert process.returncode is not None and isinstance(witness, dict)
    return process.returncode, witness


def test_one_due_real_usage_read_matches_native_completed_usd() -> None:
    """Explicit opt-in; no HTTP retry, budget reset, selection config or copy."""
    _require(
        os.environ.get("AGENTMONITOR_M7_NATIVE_COMPARISON") == "authorized",
        "native_comparison_live_authorization_required",
    )
    expected = os.environ.get("AGENTMONITOR_M7_EXPECTED_REVISION", "")
    _require(
        re.fullmatch("[a-f0-9]{40}", expected) is not None,
        "native_comparison_revision_required",
    )
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
        and re.fullmatch("m6-candidate-" + expected + "-[a-f0-9]{64}", runtime.name)
        is not None,
        "native_comparison_installed_revision_mismatch",
    )
    _require(
        _verify_retained_baseline(runtime)[0] == expected,
        "native_comparison_release_seal_invalid",
    )
    service_before = _identity()
    reference = DatabaseRefV1(LIVE / "agentmonitor.db", LIVE)
    gate = ollama_cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
    candidates = monetary_schedule_candidates(reference, datetime.now(UTC))
    _require(bool(candidates), "native_comparison_monetary_context_unavailable")
    # Wait for both real admission conditions within the existing deadline.
    # A scheduler can take the worker between the gate read and lock attempt.
    # Retry only pre-request admission, never a provider request or dispatch.
    # Monetary contexts use fifteen-minute request windows. The shared HTTP
    # cooldown alone can end before any such context is eligible; allow the
    # same readiness envelope as the existing native cost comparisons.
    # This changes no source allowance, run deadline or request retry policy.
    deadline = time.monotonic() + 1000
    supervisor = BillingWorkerSupervisorV1(LIVE)
    reserve_seconds = BillingWorkerSupervisorV1._runtime_seconds
    lock: int | None = None
    release_at = deadline
    try:
        while True:
            while True:
                remaining = deadline - time.monotonic()
                _require(remaining > 0, "native_comparison_shared_gate_unavailable")
                now = datetime.now(UTC)
                state, next_allowed = gate.read_usage_gate_status(now)
                ready = monetary_schedule_ready_at(reference, candidates, now)
                if ready is not None:
                    ready = max(ready, next_allowed or now)
                if lock is not None:
                    if state == "ready" and ready is not None and ready <= now:
                        break
                    if ready is None or time.monotonic() >= release_at:
                        _release_lock(supervisor)
                        lock = None
                elif (
                    state in {"ready", "not_due"}
                    and ready is not None
                    and ready <= now + timedelta(seconds=reserve_seconds)
                ):
                    try:
                        acquired = supervisor._acquire_lock()
                    except BlockingIOError:
                        pass
                    else:
                        if supervisor._read_marker() == "":
                            # Reserve only an idle worker slot, for at most one
                            # existing worker interval. Real admission stays due.
                            lock = acquired
                            release_at = min(
                                deadline, time.monotonic() + reserve_seconds
                            )
                            print(
                                "M7 NATIVE USAGE: idle slot reserved; "
                                "waiting for existing allowance",
                                flush=True,
                            )
                            continue
                        _release_lock(supervisor)
                delay = (
                    max(0.05, min(5.0, (next_allowed - now).total_seconds()))
                    if next_allowed is not None
                    else 0.5
                )
                time.sleep(min(0.25 if lock is not None else delay, remaining))
            _require(_identity() == service_before, "native_comparison_service_changed")
            returncode, witness = _run_owned_comparison(runtime, expected, lock)
            if (
                returncode == 3
                and witness.get("schema") == "m7-native-usage-comparison-v1"
                and witness.get("revision") == expected
                and witness.get("state") == "not_run"
                and witness.get("reason") == "native_comparison_shared_gate_unavailable"
                and witness.get("admission_state") in {"busy", "not_due"}
                and type(witness.get("requests")) is int
                and witness["requests"] == 0
                and "run_id" not in witness
                and "report_id" not in witness
            ):
                # A balance worker can take the shared gate during preparation.
                # No source request occurred: release the billing lock and wait
                # within the original deadline, without retrying any HTTP read.
                _release_lock(supervisor)
                lock = None
                print(
                    "M7 NATIVE USAGE: admission race before any request; waiting",
                    flush=True,
                )
                continue
            break
        if returncode != 0:
            # Only known bounded reason codes may escape a failed runtime.
            reason = witness.get("reason")
            allowed = {
                "native_comparison_no_due_context",
                "native_comparison_owner_queue_precedes",
                "native_comparison_context_unavailable",
                "native_comparison_shared_gate_unavailable",
                "native_comparison_execution_unresolved",
                "native_comparison_request_not_started",
                "native_comparison_report_not_committed",
                "native_comparison_money_not_reported",
                "native_comparison_mismatch",
                "native_comparison_context_invalid",
            }
            failure = (
                reason
                if isinstance(reason, str) and reason in allowed
                else "native_comparison_failed"
            )
            stage = witness.get("failure_stage")
            if stage in {"native_extraction", "exact_comparison"}:
                failure += ":" + str(stage)
            admission_state = witness.get("admission_state")
            if admission_state in {
                "not_due",
                "busy",
                "no_candidate",
                "replayed_active",
                "replayed_terminal",
            }:
                failure += ":" + str(admission_state)
            preparation_ms = witness.get("preparation_ms")
            if type(preparation_ms) is int and 0 <= preparation_ms <= 120000:
                failure += ":preparation_ms=" + str(preparation_ms)
            pytest.fail(failure, pytrace=False)
        selected_after = subprocess.run(
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
        _require(
            selected_after.returncode == 0
            and Path(selected_after.stdout.strip()) == runtime,
            "native_comparison_runtime_changed",
        )
        _require(_identity() == service_before, "native_comparison_service_changed")
        _require(
            _verify_retained_baseline(runtime)[0] == expected,
            "native_comparison_release_seal_invalid",
        )
        _verify_committed(reference, expected, witness)
        witness["service_invocation_id"] = service_before.invocation_id
        harness = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=CHECKOUT,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        witness["harness_revision"] = harness
        witness["harness_digest"] = hashlib.sha256(
            WORKER.read_bytes()
            + WORKER.with_name("native_usage_comparison.py").read_bytes()
            + WORKER.with_name("budget_commit_retry_witness.py").read_bytes()
        ).hexdigest()
        print("M7 NATIVE COMPARISON: " + json.dumps(witness, sort_keys=True))
    finally:
        _release_lock(supervisor)


def _verify_committed(
    reference: DatabaseRefV1, expected: str, witness: dict[str, object]
) -> None:
    _require(
        witness.get("schema") == "m7-native-usage-comparison-v1"
        and witness.get("composition") == "alternate_real_test_worker"
        and witness.get("revision") == expected
        and witness.get("state") == "matched"
        and witness.get("reason") is None
        and witness.get("requests") == 1
        and witness.get("currency") == "USD",
        "native_comparison_witness_invalid",
    )
    _require(
        witness.get("commit_retry")
        == {
            "attempts": 2,
            "same_receipt": True,
            "same_run_fact_counts": True,
            "reopened_receipt_equal": True,
        },
        "native_comparison_commit_retry_unverified",
    )
    for field in ("run_id", "report_id", "account_id", "resource_id", "report_digest"):
        _require(type(witness.get(field)) is str, "native_comparison_identity_invalid")
    run_id = OpaqueIdV1(str(witness["run_id"]))
    account_id = OpaqueIdV1(str(witness["account_id"]))
    report_id = OpaqueIdV1(str(witness["report_id"]))
    run = SqliteCollectionRepositoryV1(reference).get_run(run_id)
    reports = SqliteBudgetReportRepositoryV1(reference)
    stored = reports.get_report(account_id, report_id)
    status = reports.get_commit_status(run_id, "api.usage")
    provenance = reports.get_report_provenance(account_id, report_id)
    _require(
        isinstance(run, BudgetCollectionRunViewV1)
        and run.state == "succeeded"
        and run.report_id == report_id
        and run.account_id == account_id
        and status.state == "committed"
        and status.receipt is not None
        and stored is not None
        and provenance is not None,
        "native_comparison_committed_lineage_missing",
    )
    assert stored is not None and status.receipt is not None and provenance is not None
    report = stored.report
    captured = SqliteCollectionRepositoryV1(reference).get_budget_target(run_id)
    _require(
        isinstance(captured, tuple), "native_comparison_captured_authority_missing"
    )
    assert isinstance(captured, tuple)
    captured_graph, captured_service, captured_context = captured
    registry = SqliteCloudCredentialRegistryV1(reference)
    graph = registry.read_monitoring_target(account_id)
    account = SqliteRegistryRepositoryV1(reference).get_account(account_id)
    _require(
        graph is not None
        and graph.lifecycle == "active"
        and account is not None
        and account.lifecycle == "active"
        and account.is_effective_monitoring_enabled,
        "native_comparison_current_authority_unavailable",
    )
    assert graph is not None
    service = registry.read_active_access_target(graph.access_target_id)
    _require(
        service is not None
        and service.authority_id == "ollama.com"
        and graph.resource_id == report.subject.resource_id
        and graph.binding.binding_id == report.binding_id
        and graph.binding.generation == report.binding_generation
        and graph.access_target_id == report.subject.provider_target.target_id
        and (captured_graph, captured_service) == (graph, service)
        and captured_context.scope == "self"
        and not captured_context.grouping
        and captured_context.interval_start == report.requested_period.start
        and captured_context.interval_end == report.requested_period.end,
        "native_comparison_current_authority_changed",
    )
    _require(
        status.receipt.run_id == run_id
        and status.receipt.report_id == report_id
        and status.receipt.target_generation
        == run.target_generation
        == graph.binding.generation
        and status.receipt.payload_digest == run.payload_digest
        and status.receipt.stored_at == stored.stored_at
        and status.receipt.payload_digest
        == witness["report_digest"]
        == budget_report_payload_digest(report)
        and len(status.receipt.fact_ids) == witness.get("fact_count")
        and hashlib.sha256(
            "\0".join(item.value for item in status.receipt.fact_ids).encode("ascii")
        ).hexdigest()
        == witness.get("fact_ids_digest"),
        "native_comparison_receipt_digest_mismatch",
    )
    _require(
        report.subject.resource_id.value == witness["resource_id"]
        and report.source_id == witness.get("source_id")
        and report.currency == "USD"
        and not report.grouping
        and report.completeness == "complete"
        and report.covered_period == report.requested_period
        and len(report.cost_buckets) == witness.get("matched_days")
        and len(report.cost_buckets)
        == (report.requested_period.end - report.requested_period.start).days
        and len(report.cost_buckets) in {7, 30}
        and provenance.parser_version == witness.get("parser_version"),
        "native_comparison_report_mismatch",
    )
    _require(
        witness.get("context")
        == {
            "scope": "self",
            "range": "7d"
            if (report.requested_period.end - report.requested_period.start).days == 7
            else "30d",
            "start": report.requested_period.start.isoformat(),
            "end": report.requested_period.end.isoformat(),
            "grouping": [],
        }
        and witness.get("collected_at") == report.collected_at.isoformat(),
        "native_comparison_context_mismatch",
    )
