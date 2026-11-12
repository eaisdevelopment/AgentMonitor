"""Read/claim actual queued metadata in an isolated snapshot; no provider I/O."""

import os
import secrets
import shutil
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
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
from agentmonitor.composition.billing_schedule import BillingScheduleV1
from agentmonitor.composition.cloud_usage_actions import build_manual_usage_run
from agentmonitor.composition.financial_dispatch import prepare_financial_dispatch
from agentmonitor.composition.ollama_usage_collection import OllamaUsageCollectionV1
from agentmonitor.composition.ollama_usage_fence import cloud_usage_fence
from agentmonitor.composition.ollama_usage_run import (
    POLICY_VERSION,
    usage_budget_limit,
    usage_manifest_fingerprint,
)
from agentmonitor.contracts.cloud_usage_actions_v1 import CloudUsageCollectCommandV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetDispatchSnapshotV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.accounts import (
    CapacityScopeMembershipQueryV2,
    EditAccountCommandV1,
    EditAccountV1,
)


def test_real_snapshot_selects_exact_later_run_and_updates_only_its_service_age(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "agentmonitor.db"
    os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        with sqlite3.connect(
            "file:/home/dev/.local/share/agentmonitor/agentmonitor.db?mode=ro", uri=True
        ) as source:
            with sqlite3.connect(target) as copied:
                source.backup(copied)
                principal = copied.execute(
                    "SELECT administrator_id FROM iam_administrator"
                ).fetchone()
        assert principal is not None, "real_owner_metadata_unavailable"
        reference = DatabaseRefV1(target, root)
        registry = SqliteRegistryRepositoryV1(reference)
        cloud = SqliteCloudCredentialRegistryV1(reference)
        runs = SqliteCollectionRepositoryV1(
            reference, cloud_admission_fence=cloud_usage_fence
        )
        queued = []
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
            for scope, range_key in (
                ("self", "30d"),
                ("team", "30d"),
                ("self", "7d"),
                ("team", "7d"),
            ):
                now = datetime.now(UTC)
                period = completed_period(now, range_key)
                command = CloudUsageCollectCommandV1(
                    account.account_id,
                    graph.resource_id,
                    account.record_version,
                    graph.record_version,
                    OpaqueIdV1(principal[0]),
                    OpaqueIdV1("fair-command-" + secrets.token_hex(12)),
                    now,
                    CloudBudgetReportContextV1(
                        cast(Literal["self", "team"], scope),
                        cast(Literal["7d", "30d"], range_key),
                        period.start,
                        period.end,
                    ),
                )
                admission = build_manual_usage_run(
                    command, graph=graph, service=service, registry_revision=revision
                )
                try:
                    runs.admit_run(admission)
                except CollectionRepositoryErrorV1 as error:
                    assert error.code in {
                        "collection_budget_exhausted",
                        "collection_lease_conflict",
                        "collection_schedule_conflict",
                        "collection_retry_deferred",
                    }, error.code
                    continue
                queued.append(admission)
        pairs = [
            tuple(run for run in queued if run.operation_family == operation)
            for operation in ("collect.ollama.usage.30d", "collect.ollama.usage.7d")
        ]
        candidates = next((pair for pair in pairs if len(pair) >= 2), ())
        assert len(candidates) >= 2, "two_real_usage_lanes_not_available"
        first, second = candidates[:2]
        scopes = tuple(sorted({run.budget_scope_digest for run in queued}))
        schedules = tuple(
            sorted({run.schedule_id for run in queued}, key=lambda item: item.value)
        )

        def snapshot(policy: str = POLICY_VERSION) -> BudgetDispatchSnapshotV1:
            return runs.read_budget_dispatch_snapshot(
                provider_key="ollama",
                capability_id="api.usage",
                source_id="ollama.cloud.usage.v1",
                manifest_fingerprint=usage_manifest_fingerprint(),
                collection_policy_version=policy,
                operation_families=(
                    "collect.ollama.usage.7d",
                    "collect.ollama.usage.30d",
                ),
                budget_scope_digests=scopes,
                schedule_ids=schedules,
                as_of=datetime.now(UTC),
            )

        before = snapshot()
        by_key = {
            (row.budget_scope_digest, row.operation_family): row
            for row in before.states
        }
        assert (
            by_key[first.budget_scope_digest, first.operation_family].queued_run_id
            == first.run_id
        )
        assert (
            by_key[second.budget_scope_digest, second.operation_family].queued_run_id
            == second.run_id
        )
        assert tuple(by_key) == tuple(sorted(by_key))
        assert len(before.schedules) == len(schedules)
        assert all(row.has_active_lease for row in before.schedules)
        wrong_policy = snapshot("unadmitted-version")
        assert wrong_policy.states == ()
        assert wrong_policy.schedules == ()
        deadline = time.monotonic() + 90
        usage = OllamaUsageCollectionV1(
            root, credential_env_file=root / "missing.env", deadline_monotonic=deadline
        )
        work, _, automatic = prepare_financial_dispatch(
            runs,
            BillingScheduleV1(reference),
            usage.prepare_runs(),
            deadline_monotonic=deadline,
        )
        ordered_keys = tuple(
            (
                item.last_started_at or datetime.min.replace(tzinfo=UTC),
                item.ready_since,
                item.key,
            )
            for item in work
        )
        assert ordered_keys == tuple(sorted(ordered_keys))
        work_by_key = {item.key: item for item in work}
        for run in queued:
            key = ("ollama", run.budget_scope_digest, run.operation_family)
            assert work_by_key[key].queued_run_id == run.run_id
            if run.report_context.scope == "self":
                # Manual and automatic schedules share the same source budget.
                # Its real reservation must not also advertise automatic work.
                assert not work_by_key[key].scheduled_due
                assert usage.dispatch_scheduled(automatic[key]) is False
        assert {run.report_context.range_key for run in automatic.values()} == {
            "7d",
            "30d",
        }
        assert all(run.report_context.scope == "self" for run in automatic.values())
        started_at = datetime.now(UTC)
        # This is the common M04 metadata transaction only. No cloud rate lease
        # or provider call is acquired or claimed by this test.
        claimed = runs.claim_next_budget_run(
            scheduler_instance_id=OpaqueIdV1("fair-worker-" + secrets.token_hex(12)),
            as_of=started_at,
            resolve_budget_limit=usage_budget_limit,
            provider_key="ollama",
            capability_id="api.usage",
            source_id="ollama.cloud.usage.v1",
            manifest_fingerprint=usage_manifest_fingerprint(),
            collection_policy_version=POLICY_VERSION,
            operation_family=second.operation_family,
            expected_run_id=second.run_id,
        )
        assert claimed is not None and claimed.run_id == second.run_id
        assert runs.get_run(first.run_id).state == "queued"
        after = {
            (row.budget_scope_digest, row.operation_family): row
            for row in snapshot().states
        }
        served = after[second.budget_scope_digest, second.operation_family]
        assert served.queued_run_id is None
        assert served.last_started_at == started_at
        assert (
            after[first.budget_scope_digest, first.operation_family]
            == by_key[first.budget_scope_digest, first.operation_family]
        )
        later = next(
            (run for run in queued if run.account_id != first.account_id), None
        )
        assert later is not None, "second_real_cloud_account_unavailable"
        disabled_account = registry.get_account(first.cloud_target.account_id)
        assert disabled_account is not None
        EditAccountV1(registry)(
            EditAccountCommandV1(
                disabled_account.account_id,
                disabled_account.record_version,
                OpaqueIdV1(principal[0]),
                OpaqueIdV1("private-disable-" + secrets.token_hex(12)),
                "monitoring",
                datetime.now(UTC),
                monitoring_preference="disabled",
            )
        )
        failed_owner = OpaqueIdV1("rejected-owner-" + secrets.token_hex(12))
        with pytest.raises(
            BudgetCollectionError, match="budget_dispatch_authority_unavailable"
        ):
            runs.claim_next_budget_run(
                scheduler_instance_id=failed_owner,
                as_of=datetime.now(UTC),
                resolve_budget_limit=usage_budget_limit,
                provider_key="ollama",
                capability_id="api.usage",
                source_id="ollama.cloud.usage.v1",
                manifest_fingerprint=usage_manifest_fingerprint(),
                collection_policy_version=POLICY_VERSION,
                operation_family=first.operation_family,
                expected_run_id=first.run_id,
            )
        assert runs.get_run(first.run_id).state == "queued"
        with sqlite3.connect(target) as copied:
            assert (
                copied.execute(
                    "SELECT 1 FROM collection_scheduler_instance WHERE instance_id=?",
                    (failed_owner.value,),
                ).fetchone()
                is None
            )
        later_claim = runs.claim_next_budget_run(
            scheduler_instance_id=OpaqueIdV1("later-worker-" + secrets.token_hex(12)),
            as_of=datetime.now(UTC),
            resolve_budget_limit=usage_budget_limit,
            provider_key="ollama",
            capability_id="api.usage",
            source_id="ollama.cloud.usage.v1",
            manifest_fingerprint=usage_manifest_fingerprint(),
            collection_policy_version=POLICY_VERSION,
            operation_family=later.operation_family,
            expected_run_id=later.run_id,
        )
        assert later_claim is not None and later_claim.run_id == later.run_id
    finally:
        shutil.rmtree(root)
