"""Queued usage claims on a private real metadata snapshot; no key or request."""

import hashlib
import os
import secrets
import shutil
import sqlite3
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    ollama_cloud_admission as cloud_admission,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    CollectionRepositoryErrorV1,
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.api.policy import completed_period
from agentmonitor.composition.cloud_usage_actions import (
    CloudUsageActionsV1,
    build_manual_usage_run,
)
from agentmonitor.composition.ollama_usage_collection import OllamaUsageCollectionV1
from agentmonitor.composition.ollama_usage_fence import cloud_usage_fence
from agentmonitor.composition.ollama_usage_run import (
    POLICY_VERSION,
    build_ollama_usage_run,
    usage_budget_limit,
    usage_manifest_fingerprint,
)
from agentmonitor.contracts.cloud_usage_actions_v1 import CloudUsageCollectCommandV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunViewV1,
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
    OllamaCloudRequestAcquireV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
)

LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


def _require_recovery(condition: bool, code: str) -> None:
    if not condition:
        pytest.fail(code, pytrace=False)


def _recovery_evidence_counts(database: Path) -> tuple[int, ...]:
    with sqlite3.connect(database) as connection:
        return tuple(
            int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            for table in (
                "capacity_commit_receipt",
                "capacity_budget_report",
                "capacity_budget_observation",
                "capacity_usage_bucket",
                "collection_ollama_cloud_admission",
            )
        )


def test_genuine_queued_usage_claim_binds_gate_and_busy_claim_rolls_back(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "agentmonitor.db"
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        reference = DatabaseRefV1(target, root)
        gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
        snapshot_deadline = time.monotonic() + 30
        # An unchanged copy of an in-flight provider admission cannot finish
        # itself. Capture real idle metadata rather than rewriting that state
        # or waiting for a copied live owner that does not exist in this DB.
        while True:
            with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
                with sqlite3.connect(target) as copied:
                    source.backup(copied)
                    principal = copied.execute(
                        "SELECT administrator_id FROM iam_administrator"
                    ).fetchone()
            assert principal is not None, "real_owner_metadata_unavailable"
            state, retry_at = gate.read_usage_gate_status(datetime.now(UTC))
            assert state != "unresolved", "snapshot_has_unresolved_cloud_request"
            if state != "busy":
                break
            assert time.monotonic() < snapshot_deadline, (
                "live_cloud_request_did_not_finish_within_snapshot_bound"
            )
            time.sleep(0.25)
        if retry_at is not None:
            delay = max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
            assert delay <= 130, "snapshot_cloud_cooldown_exceeds_test_bound"
            while delay > 0:
                time.sleep(min(delay, 30))
                delay = max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
        # Preserve the real balance schedule and clock. The regression needs a
        # genuinely due automatic competitor, not fabricated provider state.
        with sqlite3.connect(target) as copied:
            balance_times = copied.execute(
                "SELECT s.next_due_at,s.not_before_at FROM collection_schedule s "
                "JOIN collection_cloud_schedule_lane lane USING(schedule_id) "
                "LEFT JOIN collection_lease l USING(schedule_id) "
                "WHERE s.provider_key='ollama' AND s.state='enabled' "
                "AND lane.source_id='ollama.cloud.balance.v1' "
                "AND l.schedule_id IS NULL"
            ).fetchall()
        assert balance_times, "real_balance_schedule_unavailable"
        balance_due = min(
            max(datetime.fromisoformat(due), datetime.fromisoformat(not_before or due))
            for due, not_before in balance_times
        )
        delay = max(0.0, (balance_due - datetime.now(UTC)).total_seconds())
        assert delay <= 310, "real_balance_schedule_exceeds_test_bound"
        while delay > 0:
            time.sleep(min(delay, 30))
            delay = max(0.0, (balance_due - datetime.now(UTC)).total_seconds())
        registry = SqliteRegistryRepositoryV1(reference)
        cloud = SqliteCloudCredentialRegistryV1(reference)
        runs = SqliteCollectionRepositoryV1(
            reference, cloud_admission_fence=cloud_usage_fence
        )
        queued: list[CloudBudgetCollectionRunAdmissionV1] = []
        command: CloudUsageCollectCommandV1 | None = None
        with sqlite3.connect(target) as copied:
            attempts_before = copied.execute(
                "SELECT count(*) FROM collection_ollama_cloud_admission"
            ).fetchone()
        for account in registry.list_accounts(provider_key="ollama", page_size=100):
            if not account.is_effective_monitoring_enabled:
                continue
            graph = cloud.read_monitoring_target(account.account_id)
            if graph is None or graph.lifecycle != "active":
                continue
            service = cloud.read_active_access_target(graph.access_target_id)
            if service is None:
                continue
            revision = CapacityScopeMembershipQueryV2(registry)(
                "account", account.account_id
            ).registry_revision
            # Supported command admission uses actual enabled metadata; it does
            # not claim provider team entitlement or team observations.
            for scope, range_key in (
                ("self", "30d"),
                ("self", "7d"),
                ("team", "30d"),
                ("team", "7d"),
            ):
                now = datetime.now(UTC)
                period = completed_period(now, range_key)
                run = build_ollama_usage_run(
                    graph=graph,
                    service=service,
                    context=CloudBudgetReportContextV1(
                        cast(Literal["self", "team"], scope),
                        cast(Literal["7d", "30d"], range_key),
                        period.start,
                        period.end,
                    ),
                    registry_revision=revision,
                    scheduler_instance_id=OpaqueIdV1(
                        "queue-owner-" + secrets.token_hex(12)
                    ),
                    run_id=OpaqueIdV1("queue-run-" + secrets.token_hex(12)),
                    request_id=OpaqueIdV1("queue-request-" + secrets.token_hex(12)),
                    requested_at=now,
                )
                run = replace(
                    run,
                    trigger="manual",
                    request_auth_method="browser_session",
                    request_principal_id=OpaqueIdV1(principal[0]),
                    idempotency_key_digest=hashlib.sha256(
                        run.request_id.value.encode()
                    ).hexdigest(),
                    deadline_at=now + timedelta(seconds=120),
                )
                if queued:
                    command = CloudUsageCollectCommandV1(
                        account.account_id,
                        graph.resource_id,
                        account.record_version,
                        graph.record_version,
                        OpaqueIdV1(principal[0]),
                        OpaqueIdV1("real-command-" + secrets.token_hex(12)),
                        now,
                        run.report_context,
                    )
                    run = build_manual_usage_run(
                        command,
                        graph=graph,
                        service=service,
                        registry_revision=revision,
                    )
                try:
                    admitted = runs.admit_run(run)
                except CollectionRepositoryErrorV1 as error:
                    assert error.code in {
                        "collection_budget_exhausted",
                        "collection_lease_conflict",
                        "collection_schedule_conflict",
                        "collection_retry_deferred",
                    }, error.code
                    continue
                assert admitted.state == "queued"
                queued.append(run)
                if len(queued) == 2:
                    break
            if len(queued) == 2:
                break
        assert len(queued) == 2, "two_real_usage_contexts_not_available"
        with sqlite3.connect(target) as copied:
            assert (
                copied.execute(
                    "SELECT count(*) FROM collection_ollama_cloud_admission"
                ).fetchone()
                == attempts_before
            )
        first, second = queued
        now = datetime.now(UTC)
        balance = gate.acquire(
            OllamaCloudRequestAcquireV1(
                OpaqueIdV1("balance-contender-" + secrets.token_hex(12)),
                OpaqueIdV1("balance-worker-" + secrets.token_hex(12)),
                now,
                now + timedelta(seconds=60),
                0,
            )
        )
        assert balance.state == "not_due", "balance_overtook_accepted_manual_usage"
        assert balance.lease is None
        assert balance.retry_at == min(item.deadline_at for item in queued)
        assert gate.read_usage_gate_status(datetime.now(UTC)) == ("ready", None)
        assert command is not None
        actions = CloudUsageActionsV1(reference)
        assert actions.get_status(
            command.account_id, command.resource_id, second.run_id
        ) == (runs.get_run(second.run_id), command.report_context)
        replay = actions.collect(replace(command, requested_at=datetime.now(UTC)))
        assert replay.run_id == second.run_id
        assert replay.requested_at == second.requested_at
        with pytest.raises(ValueError, match="cloud_usage_idempotency_conflict"):
            actions.collect(
                replace(
                    command,
                    report_context=replace(
                        command.report_context,
                        scope="team"
                        if command.report_context.scope == "self"
                        else "self",
                    ),
                )
            )
        worker = OpaqueIdV1("queue-worker-" + secrets.token_hex(12))
        claimed = gate.claim_next_usage_run(
            scheduler_instance_id=worker,
            as_of=datetime.now(UTC),
            resolve_budget_limit=usage_budget_limit,
            manifest_fingerprint=usage_manifest_fingerprint(),
            collection_policy_version=POLICY_VERSION,
            operation_family=first.operation_family,
            cloud_admission_fence=cloud_usage_fence,
            jitter_seconds=0,
        )
        assert claimed is not None, "real_queue_claim_not_available"
        actual, lease = claimed
        assert actual.run_id == first.run_id
        assert actual.scheduler_instance_id == worker
        assert actual.report_context == first.report_context
        assert actual.requested_at == first.requested_at
        assert actual.deadline_at == first.deadline_at
        assert lease.lease_expires_at <= actual.deadline_at
        assert lease.lease_expires_at - lease.started_at <= timedelta(seconds=60)
        runs.assert_claimed_budget_run(actual, datetime.now(UTC))
        assert runs.admit_run(first).run_id == first.run_id
        assert gate.read_usage_gate_status(datetime.now(UTC))[0] == "busy"
        with sqlite3.connect(target) as copied:
            assert copied.execute(
                "SELECT run_id,phase FROM collection_cloud_attempt_journal "
                "WHERE admission_id=?",
                (lease.admission_id.value,),
            ).fetchone() == (first.run_id.value, "reserved")
            before = copied.execute(
                "SELECT r.state,r.fencing_token,l.owner_instance_id,b.state "
                "FROM collection_run r JOIN collection_lease l ON l.run_id=r.run_id "
                "JOIN collection_budget_reservation b ON b.run_id=r.run_id "
                "WHERE r.run_id=?",
                (second.run_id.value,),
            ).fetchone()
        deferred_worker = OpaqueIdV1("deferred-worker-" + secrets.token_hex(12))
        assert (
            gate.claim_next_usage_run(
                scheduler_instance_id=deferred_worker,
                as_of=datetime.now(UTC),
                resolve_budget_limit=usage_budget_limit,
                manifest_fingerprint=usage_manifest_fingerprint(),
                collection_policy_version=POLICY_VERSION,
                operation_family=second.operation_family,
                cloud_admission_fence=cloud_usage_fence,
                jitter_seconds=0,
            )
            is None
        )
        with sqlite3.connect(target) as copied:
            after = copied.execute(
                "SELECT r.state,r.fencing_token,l.owner_instance_id,b.state "
                "FROM collection_run r JOIN collection_lease l ON l.run_id=r.run_id "
                "JOIN collection_budget_reservation b ON b.run_id=r.run_id "
                "WHERE r.run_id=?",
                (second.run_id.value,),
            ).fetchone()
            assert after == before
            assert before[0] == "queued"
            assert (
                copied.execute(
                    "SELECT 1 FROM collection_scheduler_instance WHERE instance_id=?",
                    (deferred_worker.value,),
                ).fetchone()
                is None
            )
            assert copied.execute(
                "SELECT active_admission_id FROM collection_ollama_cloud_gate"
            ).fetchone() == (lease.admission_id.value,)
            original_requests = tuple(
                copied.execute(
                    "SELECT r.primary_request_id,r.request_digest,r.requested_at,"
                    "r.deadline_at,r.target_generation,b.canonical_target_json "
                    "FROM collection_run r JOIN collection_budget_run b USING(run_id) "
                    "WHERE r.run_id=?",
                    (item.run_id.value,),
                ).fetchone()
                for item in queued
            )
        evidence_counts = _recovery_evidence_counts(target)
        # A real reserved attempt has made no request. Let its genuine worker
        # heartbeat become stale before exercising the next worker's recovery.
        recover_at = lease.started_at + timedelta(seconds=120.1)
        delay = max(0.0, (recover_at - datetime.now(UTC)).total_seconds())
        while delay > 0:
            time.sleep(min(delay, 30))
            delay = max(0.0, (recover_at - datetime.now(UTC)).total_seconds())
        assert gate.read_usage_gate_status(datetime.now(UTC))[0] == "unresolved"
        collector = OllamaUsageCollectionV1(
            root, credential_env_file=None, deadline_monotonic=time.monotonic() + 30
        )
        assert collector.dispatch_manual() is False
        with sqlite3.connect(target) as copied:
            assert copied.execute(
                "SELECT active_admission_id FROM collection_ollama_cloud_gate"
            ).fetchone() == (None,)
            assert copied.execute(
                "SELECT dispatch_certainty,reason_code "
                "FROM collection_cloud_no_response_terminal WHERE admission_id=?",
                (lease.admission_id.value,),
            ).fetchone() == ("not_started", "pre_dispatch_failed")
            assert (
                copied.execute(
                    "SELECT 1 FROM collection_scheduler_instance WHERE instance_id=?",
                    (collector._instance.value,),
                ).fetchone()
                is None
            ), "recovery_consumed_manual_dispatch_owner"
            retained_requests = tuple(
                copied.execute(
                    "SELECT r.primary_request_id,r.request_digest,r.requested_at,"
                    "r.deadline_at,r.target_generation,b.canonical_target_json "
                    "FROM collection_run r JOIN collection_budget_run b USING(run_id) "
                    "WHERE r.run_id=?",
                    (item.run_id.value,),
                ).fetchone()
                for item in queued
            )
        _require_recovery(
            retained_requests == original_requests,
            "recovery_changed_original_request_or_context",
        )
        recovered = []
        reports = SqliteBudgetReportRepositoryV1(reference)
        for index, original in enumerate(queued):
            status = actions.get_status(
                original.cloud_target.account_id,
                original.cloud_target.resource_id,
                original.run_id,
            )
            _require_recovery(status is not None, "recovery_status_missing")
            assert status is not None
            view, context = status
            _require_recovery(
                isinstance(view, BudgetCollectionRunViewV1)
                and view.run_id == original.run_id
                and view.requested_at == original.requested_at
                and view.deadline_at == original.deadline_at
                and context == original.report_context
                and view.state == "failed"
                and view.error_code
                == (
                    "collection_worker_interrupted"
                    if index == 0
                    else "collection_queued_expired"
                )
                and (view.started_at is not None) == (index == 0)
                and view.report_id is None
                and not view.observation_ids
                and view.payload_digest is None,
                "recovery_terminal_context_or_outcome_changed",
            )
            _require_recovery(
                reports.get_commit_status(original.run_id, original.capability_id).state
                == "not_committed",
                "recovery_invented_report_receipt",
            )
            recovered.append(status)
        # A new worker repeats normal recovery; original failed work stays
        # terminal without recollection, new facts or an extra provider attempt.
        next_worker = OllamaUsageCollectionV1(
            root, credential_env_file=None, deadline_monotonic=time.monotonic() + 30
        )
        _require_recovery(
            next_worker.run(recovery_only=True) == 0,
            "repeated_recovery_failed",
        )
        for original, prior in zip(queued, recovered, strict=True):
            _require_recovery(
                actions.get_status(
                    original.cloud_target.account_id,
                    original.cloud_target.resource_id,
                    original.run_id,
                )
                == prior,
                "repeated_recovery_changed_original_status",
            )
        _require_recovery(
            _recovery_evidence_counts(target) == evidence_counts,
            "recovery_created_observations_receipts_or_attempts",
        )
        now = datetime.now(UTC)
        resumed_balance = gate.acquire(
            OllamaCloudRequestAcquireV1(
                OpaqueIdV1("resumed-balance-" + secrets.token_hex(12)),
                OpaqueIdV1("resumed-balance-worker-" + secrets.token_hex(12)),
                now,
                now + timedelta(seconds=60),
                0,
            )
        )
        assert resumed_balance.state == "acquired", "expired_usage_blocked_balance"
    finally:
        shutil.rmtree(root)
