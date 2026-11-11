"""Real private SQLite snapshot and genuine cloud metadata; no provider requests."""

import os
import secrets
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

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
from agentmonitor.composition.ollama_usage_run import build_ollama_usage_run
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetReportContextV1,
    OllamaCloudRequestAcquireV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
)

LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


def test_genuine_cloud_usage_uses_existing_balance_rate_gate(tmp_path: Path) -> None:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "agentmonitor.db"
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
            with sqlite3.connect(target) as copy:
                source.backup(copy)
                row = copy.execute(
                    "SELECT account_id FROM reg_cloud_monitoring_target "
                    "WHERE lifecycle='active' LIMIT 1"
                ).fetchone()
                assert row is not None, "real_cloud_account_required"
        reference = DatabaseRefV1(target, root)
        cloud = SqliteCloudCredentialRegistryV1(reference)
        account_id = OpaqueIdV1(row[0])
        graph = cloud.read_monitoring_target(account_id)
        assert graph is not None
        service = cloud.read_active_access_target(graph.access_target_id)
        assert service is not None
        membership = CapacityScopeMembershipQueryV2(
            SqliteRegistryRepositoryV1(reference)
        )("account", account_id)
        now = datetime.now(UTC)
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)

        def ident(prefix: str) -> OpaqueIdV1:
            return OpaqueIdV1(prefix + secrets.token_hex(12))

        run = build_ollama_usage_run(
            graph=graph,
            service=service,
            context=CloudBudgetReportContextV1(
                "self", "7d", cutoff - timedelta(days=7), cutoff
            ),
            registry_revision=membership.registry_revision,
            scheduler_instance_id=ident("usage-worker-"),
            run_id=ident("usage-run-"),
            request_id=ident("usage-request-"),
            requested_at=now,
        )
        from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
            open_sqlite_database,
        )
        from agentmonitor.composition.ollama_usage_fence import cloud_usage_fence

        with open_sqlite_database(reference, "runtime_read_write") as handle:
            with handle.connect() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                cloud_usage_fence(connection, graph, service, run.report_context)
                connection.rollback()
        repository = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
        repository.register_schedule(run)
        request = OllamaCloudRequestAcquireV1(
            ident("usage-admission-"),
            run.scheduler_instance_id,
            now,
            now + timedelta(seconds=60),
            0,
        )
        result = repository.acquire_usage(request, admission=run)
        assert result.state in {"acquired", "busy", "not_due", "no_candidate"}
        with sqlite3.connect(target) as copy:
            if result.state == "no_candidate":
                due = copy.execute(
                    "SELECT next_due_at FROM collection_schedule WHERE schedule_id=?",
                    (run.schedule_id.value,),
                ).fetchone()
                assert due is not None
                assert datetime.fromisoformat(due[0]) > now
            assert (
                copy.execute(
                    "SELECT COUNT(*) FROM collection_ollama_cloud_gate"
                ).fetchone()[0]
                == 1
            )
            assert (
                copy.execute(
                    "SELECT effective_interval_seconds FROM collection_schedule "
                    "WHERE schedule_id=?",
                    (run.schedule_id.value,),
                ).fetchone()[0]
                == 900
            )
            assert (
                copy.execute(
                    "SELECT source_id FROM collection_cloud_schedule_lane "
                    "WHERE schedule_id=?",
                    (run.schedule_id.value,),
                ).fetchone()[0]
                == "ollama.cloud.usage.v1"
            )
        if result.state == "acquired":
            assert result.lease is not None
            from agentmonitor.contracts.collection_control_v1 import (
                BudgetCollectionRunViewV1,
            )

            runs = cloud_admission.SqliteOllamaCloudRunRepositoryV1(
                reference, result.lease, cloud_admission_fence=cloud_usage_fence
            )
            admitted = runs.admit_run(run)
            assert isinstance(admitted, BudgetCollectionRunViewV1)
            assert admitted.state == "queued"
            assert runs.get_budget_target(run.run_id) == (
                graph,
                service,
                run.report_context,
            )
            runs.mark_running(
                run.run_id,
                datetime.now(UTC),
                fencing_token=admitted.fencing_token,
                scheduler_instance_id=run.scheduler_instance_id,
            )
            assert (
                runs.assert_claimed_budget_run(run, datetime.now(UTC)).state
                == "running"
            )
            balance = repository.acquire(
                OllamaCloudRequestAcquireV1(
                    ident("balance-admission-"),
                    run.scheduler_instance_id,
                    now,
                    now + timedelta(seconds=60),
                    0,
                )
            )
            assert balance.state == "busy"
        assert repository.acquire_usage(request, admission=run).state in {
            "replayed_active",
            "busy",
            "not_due",
            "no_candidate",
        }
    finally:
        shutil.rmtree(root)
