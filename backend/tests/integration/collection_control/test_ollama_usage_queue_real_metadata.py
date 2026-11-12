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
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
)

LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


def test_genuine_queued_usage_claim_binds_gate_and_busy_claim_rolls_back(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "agentmonitor.db"
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
            with sqlite3.connect(target) as copied:
                source.backup(copied)
                principal = copied.execute(
                    "SELECT administrator_id FROM iam_administrator"
                ).fetchone()
        assert principal is not None, "real_owner_metadata_unavailable"
        reference = DatabaseRefV1(target, root)
        gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
        state, retry_at = gate.read_usage_gate_status(datetime.now(UTC))
        assert state != "unresolved", "snapshot_has_unresolved_cloud_request"
        assert state != "busy", "snapshot_has_active_cloud_request"
        if retry_at is not None:
            delay = max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
            assert delay <= 130, "snapshot_cloud_cooldown_exceeds_test_bound"
            while delay > 0:
                time.sleep(min(delay, 30))
                delay = max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
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
    finally:
        shutil.rmtree(root)
