"""T006/T008/T015: real cost comparison, with no owner configuration.

Alternate test worker under the sealed installed runtime; no source fixtures.
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
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingAccessRepositoryV1,
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.billing_run import anthropic_billing_budget_scope_digest
from agentmonitor.composition.billing_schedule import (
    BillingScheduleV1,
    billing_schedule_intent,
)
from agentmonitor.composition.billing_worker_supervisor import BillingWorkerSupervisorV1
from agentmonitor.composition.openai_billing_run import (
    OPENAI_COST_AUTHORITY_ID_V1,
    openai_billing_budget_scope_digest,
)
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetAuthorityV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1

from backend.tests.live.ollama.test_budget_interrupted_receipt import _release_lock
from backend.tests.live.ollama.test_budget_monetary_persistence import _require
from tools.automation.implementations.m6_cutover import _verify_retained_baseline
from tools.automation.implementations.m6_recovery_interval import _identity

LIVE = Path("/home/dev/.local/share/agentmonitor")
WORKER = Path(__file__).with_name("native_cost_comparison_worker.py")
CHECKOUT = Path(__file__).resolve().parents[4]
PROVIDERS = {"anthropic": "claude", "openai": "codex"}


@pytest.mark.parametrize("provider", tuple(PROVIDERS))
def test_native_cost_worker_refuses_before_start(tmp_path: Path, provider: str) -> None:
    absent = tmp_path / "must-not-open"
    result = subprocess.run(
        [
            sys.executable,
            str(WORKER),
            str(absent),
            uuid.uuid4().hex,
            "0" * 40,
            provider,
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "PYTHONPATH": str(CHECKOUT / "backend/src") + os.pathsep + str(CHECKOUT),
        },
    )
    _require(result.returncode == 5, "native_cost_start_refusal_failed")
    _require(result.stdout == result.stderr == "", "native_cost_refusal_output")
    _require(not absent.exists(), "native_cost_prestart_state_created")


def _runtime(expected: str) -> Path:
    result = subprocess.run(
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
    path = Path(result.stdout.strip())
    _require(
        result.returncode == 0
        and path.parent == LIVE / "releases"
        and re.fullmatch("m6-candidate-" + expected + "-[a-f0-9]{64}", path.name)
        is not None,
        "native_cost_installed_revision_mismatch",
    )
    _require(_verify_retained_baseline(path)[0] == expected, "native_cost_seal_invalid")
    return path


def _require_monitored_resource(reference: DatabaseRefV1, provider: str) -> None:
    registry = SqliteRegistryRepositoryV1(reference)
    connections = SqliteBillingConnectionRepositoryV1(reference)
    access = SqliteBillingAccessRepositoryV1(reference)
    cursor = None
    seen: set[OpaqueIdV1] = set()
    as_of = datetime.now(UTC)
    while True:
        page = ListAccountsV1(registry).page(
            PROVIDERS[provider], as_of=as_of, limit=100, after_key=cursor
        )
        _require(
            page.availability.state == "available", "native_cost_inventory_unavailable"
        )
        for account in page.items:
            _require(
                account.account_id not in seen, "native_cost_inventory_cursor_invalid"
            )
            seen.add(account.account_id)
            status = connections.get(account.account_id)
            if status is None:
                continue
            for connection in status.connections:
                if (
                    access.resolve(
                        account.account_id, connection.resource_id, "monitoring"
                    )
                    is not None
                ):
                    return
        if not page.has_more:
            break
        _require(
            page.next_key is not None and page.next_key != cursor,
            "native_cost_inventory_cursor_invalid",
        )
        cursor = page.next_key
    pytest.fail("native_cost_monitored_resource_required", pytrace=False)


def _cost_slot_ready_at(
    reference: DatabaseRefV1, provider: str, now: datetime
) -> datetime | None:
    """Read actual allowance and the next scheduled monetary opportunity."""
    from backend.tests.live.billing.native_cost_comparison_worker import (
        _has_monetary_baseline,
    )

    scheduler = BillingScheduleV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    targets = SqliteCloudCredentialRegistryV1(reference)
    provider_key = PROVIDERS[provider]
    service = targets.read_access_target_for_authority(
        provider_key,
        OPENAI_COST_AUTHORITY_ID_V1 if provider == "openai" else "anthropic.analytics",
    )
    _require(service is not None, "native_cost_service_target_unavailable")
    assert service is not None
    ready: list[datetime] = []
    for target in scheduler.read_targets(deadline_monotonic=time.monotonic() + 30):
        if (
            target.connection.provider_key != provider_key
            or target.purpose != "monitoring"
        ):
            continue
        scope = (
            openai_billing_budget_scope_digest
            if provider == "openai"
            else anthropic_billing_budget_scope_digest
        )(
            target,
            ProviderTargetRefV1("cloud_service", service.access_target_id),
        )
        allowance = runs.get_budget_next_allowed_at(scope, "request", "count", now)
        for range_key in ("7d", "30d"):
            intent = billing_schedule_intent(target, now, range_key=range_key)
            latest = runs.get_latest_budget_run(
                target.connection.account_id,
                target.connection.resource_id,
                target.connection.scope_generation,
                now,
                report_context=intent.report_context,
            )
            if latest is not None and latest.requested_at >= intent.window_start:
                # Preview the existing next 15-minute schedule with its actual
                # jitter. All storage reads use now; no future facts are written
                # or treated as observed. The child rechecks real due admission.
                intent = billing_schedule_intent(
                    target,
                    intent.window_start + timedelta(minutes=15),
                    range_key=range_key,
                )
            if _has_monetary_baseline(reference, intent, now):
                ready.append(max(now, intent.due_at, allowance or now))
    return min(ready, default=None)


def _wait_for_cost_slot(
    reference: DatabaseRefV1, provider: str, supervisor: BillingWorkerSupervisorV1
) -> int:
    """Acquire an idle slot before the stock worker consumes the due context."""
    stop = time.monotonic() + 1000
    # Only the alternate test worker reserves this idle slot. A running worker
    # is never stopped. Reserve at most one worker interval before admission;
    # source reads still wait for the real allowance and normal claim fences.
    reserve_seconds = BillingWorkerSupervisorV1._runtime_seconds
    lock: int | None = None
    release_at = stop
    print("M7 NATIVE COST COMPARISON: waiting for an idle, due cost window", flush=True)
    while time.monotonic() < stop:
        now = datetime.now(UTC)
        ready = _cost_slot_ready_at(reference, provider, now)
        if lock is not None:
            if ready is not None and ready <= now:
                return lock
            if ready is None or time.monotonic() >= release_at:
                _release_lock(supervisor)
                lock = None
        elif ready is not None and ready <= now + timedelta(seconds=reserve_seconds):
            try:
                acquired = supervisor._acquire_lock()
                if supervisor._read_marker() == "":
                    lock = acquired
                    release_at = min(stop, time.monotonic() + reserve_seconds)
                    print(
                        "M7 NATIVE COST COMPARISON: idle slot reserved; "
                        "waiting for existing allowance",
                        flush=True,
                    )
                    continue
            except BlockingIOError:
                pass
            _release_lock(supervisor)
        time.sleep(0.25 if lock is not None else 1)
    pytest.fail("native_cost_no_due_context", pytrace=False)


@pytest.mark.parametrize("provider", tuple(PROVIDERS))
def test_real_native_cost_comparison(provider: str) -> None:
    _require(
        os.environ.get("AGENTMONITOR_M7_NATIVE_COST_COMPARISON") == "authorized",
        "native_cost_runtime_authorization_required",
    )
    expected = os.environ.get("AGENTMONITOR_M7_EXPECTED_REVISION", "")
    _require(
        re.fullmatch("[a-f0-9]{40}", expected) is not None,
        "native_cost_revision_required",
    )
    runtime = _runtime(expected)
    before = _identity()
    reference = DatabaseRefV1(LIVE / "agentmonitor.db", LIVE)
    _require_monitored_resource(reference, provider)
    supervisor = BillingWorkerSupervisorV1(LIVE)
    try:
        lock = _wait_for_cost_slot(reference, provider, supervisor)
        _require(_identity() == before, "native_cost_service_changed")
        authority = uuid.uuid4().hex
        with subprocess.Popen(
            [sys.executable, str(WORKER), str(LIVE), authority, expected, provider],
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
                pytest.fail("native_cost_owned_worker_timeout", pytrace=False)
        _require(
            len(output) <= 8192 and diagnostic == "",
            "native_cost_closed_output_invalid",
        )
        _require(
            process.returncode not in {2, 5, 6}, "native_cost_worker_authority_refused"
        )
        try:
            witness = json.loads(output)
        except (ValueError, TypeError):
            pytest.fail("native_cost_closed_output_invalid", pytrace=False)
        _require(isinstance(witness, dict), "native_cost_closed_output_invalid")
        if process.returncode != 0:
            # Enumerated worker outcomes only; never expose exception text.
            reason = witness.get("reason")
            if reason == "native_cost_execution_unresolved":
                from backend.tests.live.billing.native_cost_comparison_worker import (
                    failure_context,
                )

                print("M7 NATIVE COST FAILURE: " + failure_context(witness), flush=True)
            allowed = {
                "native_cost_monitoring_resource_unavailable",
                "native_cost_credential_location_unavailable",
                "native_cost_admission_unavailable",
                "native_cost_authorization_unavailable",
                "native_cost_service_target_unavailable",
                "native_cost_monetary_comparison_incomplete",
                "native_cost_no_due_context",
                "native_cost_owner_queue_precedes",
                "native_cost_monitored_resource_required",
                "native_cost_context_unavailable",
                "native_cost_execution_unresolved",
                "native_cost_request_not_started",
                "native_cost_report_not_committed",
                "native_cost_money_not_reported",
                "native_cost_mismatch",
                "native_cost_context_invalid",
            }
            pytest.fail(
                reason
                if isinstance(reason, str) and reason in allowed
                else "native_cost_comparison_failed",
                pytrace=False,
            )
        _require(
            _runtime(expected) == runtime and _identity() == before,
            "native_cost_service_changed",
        )
        _verify_committed(reference, provider, expected, witness)
        witness["service_invocation_id"] = before.invocation_id
        witness["harness_revision"] = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=CHECKOUT,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        witness["harness_digest"] = hashlib.sha256(
            b"".join(
                WORKER.with_name(name).read_bytes()
                for name in (
                    "native_cost_comparison_worker.py",
                    "native_cost_comparison.py",
                    "native_cost_sources.py",
                    "test_m7_native_cost_comparison.py",
                )
            )
        ).hexdigest()
        print("M7 NATIVE COST COMPARISON: " + json.dumps(witness, sort_keys=True))
    finally:
        _release_lock(supervisor)


def _verify_committed(
    reference: DatabaseRefV1, provider: str, expected: str, witness: dict[str, object]
) -> None:
    requests = witness.get("requests")
    _require(
        witness.get("schema") == "m7-native-cost-comparison-v1"
        and witness.get("composition") == "alternate_real_test_worker"
        and witness.get("provider") == provider
        and witness.get("revision") == expected
        and witness.get("state") == "matched"
        and witness.get("reason") is None
        and witness.get("pages_exhausted") is True
        and witness.get("source_state") == "success"
        and type(requests) is int
        and 1 <= requests <= 20,
        "native_cost_witness_invalid",
    )
    for field in ("run_id", "report_id", "account_id", "resource_id", "report_digest"):
        _require(type(witness.get(field)) is str, "native_cost_identity_invalid")
    run_id, report_id, account_id = (
        OpaqueIdV1(str(witness[key])) for key in ("run_id", "report_id", "account_id")
    )
    runs = SqliteCollectionRepositoryV1(reference)
    repository = SqliteBudgetReportRepositoryV1(reference)
    run = runs.get_run(run_id)
    stored = repository.get_report(account_id, report_id)
    receipt_status = repository.get_commit_status(run_id, "api.cost")
    provenance = repository.get_report_provenance(account_id, report_id)
    _require(
        isinstance(run, BudgetCollectionRunViewV1)
        and run.state == "succeeded"
        and run.report_id == report_id
        and run.account_id == account_id
        and stored is not None
        and receipt_status.state == "committed"
        and receipt_status.receipt is not None
        and provenance is not None,
        "native_cost_committed_lineage_missing",
    )
    assert (
        isinstance(run, BudgetCollectionRunViewV1)
        and stored is not None
        and receipt_status.receipt is not None
        and provenance is not None
    )
    report, receipt = stored.report, receipt_status.receipt
    authority = runs.get_budget_target(run_id)
    _require(
        isinstance(authority, BillingBudgetAuthorityV1),
        "native_cost_captured_authority_missing",
    )
    assert isinstance(authority, BillingBudgetAuthorityV1)
    current = SqliteBillingAccessRepositoryV1(reference).resolve(
        account_id, report.subject.resource_id, "monitoring"
    )
    _require(current == authority.target, "native_cost_current_authority_changed")
    service = SqliteCloudCredentialRegistryV1(reference).read_active_access_target(
        report.subject.provider_target.target_id
    )
    _require(service is not None, "native_cost_service_target_unavailable")
    assert service is not None
    _require(
        service.access_target_id.value == witness.get("service_target_id")
        and service.record_version == witness.get("service_record_version")
        and service.manifest_fingerprint == witness.get("service_manifest_fingerprint")
        and service.provider_key == PROVIDERS[provider]
        and service.authority_id
        == (
            "anthropic.analytics" if provider == "anthropic" else "openai.organization"
        ),
        "native_cost_service_target_changed",
    )
    context = authority.report_context
    _require(
        witness.get("context")
        == {
            "range": context.range_key,
            "start": context.interval_start.isoformat(),
            "end": context.interval_end.isoformat(),
            "source_category": context.source_category,
            "grouping": list(context.grouping),
        },
        "native_cost_witness_context_mismatch",
    )
    _require(
        report.subject.provider_key == PROVIDERS[provider]
        and report.subject.account_id == account_id
        and report.subject.resource_id.value == witness["resource_id"]
        and report.binding_id == authority.target.binding.binding_id
        and report.binding_generation
        == receipt.target_generation
        == run.target_generation
        == authority.target.binding.generation
        and report.scope_generation == authority.target.connection.scope_generation
        and (report.scope_id.value if report.scope_id else None)
        == authority.target.connection.scope_id
        and report.scope_evidence == authority.target.connection.scope_evidence
        and report.requested_period.start == context.interval_start
        and report.requested_period.end == context.interval_end
        and report.source_category == context.source_category
        and not report.grouping
        and not context.grouping
        and report.completeness == "complete"
        and report.covered_period == report.requested_period
        and report.currency is not None
        and report.currency == witness.get("currency")
        and report.cost_basis == witness.get("cost_basis")
        and (
            report.source_data_through.isoformat()
            if report.source_data_through
            else None
        )
        == witness.get("source_data_through"),
        "native_cost_report_context_mismatch",
    )
    _require(
        report.collected_at.isoformat() == witness.get("collected_at")
        and len(report.cost_buckets) == witness.get("compared_rows")
        and (bool(report.cost_buckets) or report.empty_means_zero)
        and not report.usage_buckets
        and report.source_id
        == run.source_id
        == provenance.source_id
        == witness.get("source_id")
        and provenance.parser_version == witness.get("parser_version")
        and provenance.operation_id == run_id
        and provenance.capability_id == "api.cost"
        and provenance.provider_key == PROVIDERS[provider]
        and provenance.collected_at == report.collected_at,
        "native_cost_source_proof_mismatch",
    )
    _require(
        receipt.run_id == run_id
        and receipt.report_id == report_id
        and receipt.stored_at == stored.stored_at
        and receipt.payload_digest
        == run.payload_digest
        == witness["report_digest"]
        == budget_report_payload_digest(report)
        and set(receipt.fact_ids) == set(run.observation_ids)
        and len(receipt.fact_ids) == len(run.observation_ids)
        and len(set(receipt.fact_ids)) == len(receipt.fact_ids)
        and len(receipt.fact_ids)
        == witness.get("fact_count")
        == len(report.cost_buckets)
        and hashlib.sha256(
            "\0".join(item.value for item in receipt.fact_ids).encode("ascii")
        ).hexdigest()
        == witness.get("fact_ids_digest"),
        "native_cost_receipt_mismatch",
    )
    reopened = SqliteBudgetReportRepositoryV1(reference)
    _require(
        reopened.get_report(account_id, report_id) == stored
        and reopened.get_commit_status(run_id, "api.cost") == receipt_status
        and reopened.get_report_provenance(account_id, report_id) == provenance,
        "native_cost_reopened_lineage_changed",
    )


@pytest.mark.parametrize("provider", tuple(PROVIDERS))
def test_native_cost_empty_registry_refuses_without_enrollment(
    tmp_path: Path, provider: str
) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        migrate_to_head,
    )

    from backend.tests.live.billing.native_cost_comparison_worker import _run

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    before = hashlib.sha256((tmp_path / "agentmonitor.db").read_bytes()).hexdigest()
    witness: dict[str, object] = {"requests": 0}
    _run(tmp_path, provider, witness)
    assert witness == {
        "requests": 0,
        "phase": "targets",
        "reason": "native_cost_monitoring_resource_unavailable",
    }
    assert (
        hashlib.sha256((tmp_path / "agentmonitor.db").read_bytes()).hexdigest()
        == before
    )
