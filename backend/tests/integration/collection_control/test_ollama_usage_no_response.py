"""Real no-auth source and private genuine metadata; no HTTP request or key read."""

import os
import secrets
import shutil
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    ollama_cloud_admission as cloud_admission,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.api.policy import (
    OllamaUsageRequestV1,
    completed_period,
)
from agentmonitor.adapters.providers.ollama.api.source import (
    collect_usage_report_in_worker_v1,
)
from agentmonitor.composition.ollama_usage_collection import OllamaUsageCollectionV1
from agentmonitor.composition.ollama_usage_dispatch import usage_no_response_terminal
from agentmonitor.composition.ollama_usage_fence import cloud_usage_fence
from agentmonitor.composition.ollama_usage_run import (
    build_ollama_usage_run,
    usage_request_for_run,
)
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetReportContextV1,
    OllamaCloudRequestAcquireV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
)

LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


def test_actual_no_authorization_returns_before_request_access() -> None:
    # Deliberately absent request: the real source must reject missing authority
    # before request construction, socket access, or dedicated-worker checks.
    result = collect_usage_report_in_worker_v1(
        cast(OllamaUsageRequestV1, None),
        authorization=None,
    )
    assert result.state == "authorization_unavailable"
    assert result.requests_made == 0
    assert result.http_status is None
    assert result.report is None
    assert result.retry_after_seconds is None


def test_genuine_cloud_no_request_finalizes_without_response_or_consumption(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "agentmonitor.db"
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
            with sqlite3.connect(target) as copy:
                source.backup(copy)
                gate_state = copy.execute(
                    "SELECT next_allowed_at,active_admission_id "
                    "FROM collection_ollama_cloud_gate"
                ).fetchone()
        # A private snapshot retains the real global cooldown. Let that real
        # deadline elapse without changing any timestamp or admission state.
        # An active request needs recovery evidence, not a test-side release.
        if gate_state is not None:
            assert gate_state[1] is None, "snapshot_has_active_cloud_request"
            retry_at = datetime.fromisoformat(gate_state[0])
            delay = max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
            assert delay <= 130, "snapshot_cloud_cooldown_exceeds_test_bound"
            while delay > 0:
                time.sleep(min(delay, 30))
                delay = max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
        reference = DatabaseRefV1(target, root)
        collector = OllamaUsageCollectionV1(
            root, credential_env_file=None, deadline_monotonic=time.monotonic() + 90
        )
        finalizer = collector._finish_not_started
        registry = SqliteRegistryRepositoryV1(reference)
        cloud = SqliteCloudCredentialRegistryV1(reference)
        gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
        run = None
        lease = None
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
            for range_key in ("30d", "7d"):
                now = datetime.now(UTC)
                period = completed_period(now, range_key)
                run = build_ollama_usage_run(
                    graph=graph,
                    service=service,
                    context=CloudBudgetReportContextV1(
                        "self", range_key, period.start, period.end
                    ),
                    registry_revision=revision,
                    scheduler_instance_id=OpaqueIdV1(
                        "no-request-worker-" + secrets.token_hex(12)
                    ),
                    run_id=OpaqueIdV1("no-request-run-" + secrets.token_hex(12)),
                    request_id=OpaqueIdV1(
                        "no-request-request-" + secrets.token_hex(12)
                    ),
                    requested_at=now,
                )
                gate.register_schedule(run)
                decision = gate.acquire_usage(
                    OllamaCloudRequestAcquireV1(
                        OpaqueIdV1("no-request-admission-" + secrets.token_hex(12)),
                        run.scheduler_instance_id,
                        now,
                        run.deadline_at,
                        0,
                    ),
                    admission=run,
                )
                if decision.lease is not None:
                    lease = decision.lease
                    break
            if lease is not None:
                break
        assert run is not None and lease is not None, (
            "real_cloud_usage_not_due_or_unavailable"
        )
        runs = cloud_admission.SqliteOllamaCloudRunRepositoryV1(
            reference, lease, cloud_admission_fence=cloud_usage_fence
        )
        admitted = runs.admit_run(run)
        runs.mark_running(
            run.run_id,
            datetime.now(UTC),
            fencing_token=admitted.fencing_token,
            scheduler_instance_id=run.scheduler_instance_id,
        )
        runs.assert_claimed_budget_run(run, datetime.now(UTC))
        gate.mark_dispatched(lease, datetime.now(UTC))
        result = collect_usage_report_in_worker_v1(
            usage_request_for_run(run, dispatched_at=datetime.now(UTC)),
            authorization=None,
        )
        terminal = usage_no_response_terminal(
            result, lease, completed_at=datetime.now(UTC)
        )
        assert terminal is not None
        finalizer(run, lease, admitted.fencing_token, terminal, result)
        with sqlite3.connect(target) as copy:
            assert copy.execute(
                "SELECT active_admission_id FROM collection_ollama_cloud_gate"
            ).fetchone() == (None,)
            assert copy.execute(
                "SELECT state,outcome_code FROM collection_run WHERE run_id=?",
                (run.run_id.value,),
            ).fetchone() == ("blocked", "ollama_usage_authorization_unavailable")
            assert copy.execute(
                "SELECT state FROM collection_budget_reservation WHERE run_id=?",
                (run.run_id.value,),
            ).fetchone() == ("released",)
            assert copy.execute(
                "SELECT response_received_at,outcome "
                "FROM collection_ollama_cloud_admission "
                "WHERE admission_id=?",
                (lease.admission_id.value,),
            ).fetchone() == (None, None)
            assert copy.execute(
                "SELECT dispatch_certainty,source_state "
                "FROM collection_cloud_no_response_terminal "
                "WHERE admission_id=?",
                (lease.admission_id.value,),
            ).fetchone() == ("not_started", "authorization_unavailable")
            assert copy.execute(
                "SELECT count(*) FROM collection_cloud_uncertain_outcome "
                "WHERE admission_id=?",
                (lease.admission_id.value,),
            ).fetchone() == (0,)
            assert copy.execute(
                "SELECT count(*) FROM collection_lease WHERE run_id=?",
                (run.run_id.value,),
            ).fetchone() == (0,)
    finally:
        shutil.rmtree(root)
