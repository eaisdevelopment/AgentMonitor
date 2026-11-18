"""Read/claim actual queued metadata in an isolated snapshot; no provider I/O."""

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
from agentmonitor.composition.cloud_usage_actions import (
    CloudUsageActionsV1,
    build_manual_usage_run,
)
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
    BudgetCollectionRunViewV1,
    BudgetDispatchSnapshotV1,
    CloudBudgetCollectionRunAdmissionV1,
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
            root, credential_env_file=None, deadline_monotonic=deadline
        )
        prepared = usage.prepare_runs()
        dispatch_as_of = datetime.now(UTC)
        work, _, automatic = prepare_financial_dispatch(
            runs,
            BillingScheduleV1(reference),
            prepared,
            deadline_monotonic=deadline,
            as_of=dispatch_as_of,
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
                # An accepted request retains its lease across a 15-minute
                # budget rollover. Only a current-window reservation suppresses
                # automatic eligibility; the same queued request still wins
                # this key and is claimed explicitly below in either case.
                assert runs.get_admission_state(run.run_id) == ("active", "reserved")
                cooldown = runs.get_budget_next_allowed_at(
                    key[1], "request", "count", dispatch_as_of
                )
                if dispatch_as_of < run.budget_window_end:
                    assert cooldown == run.budget_window_end
                    assert not work_by_key[key].scheduled_due
                else:
                    assert cooldown is None, "elapsed_reservation_blocks_new_window"
        assert {run.report_context.range_key for run in automatic.values()} == {
            "7d",
            "30d",
        }
        assert all(run.report_context.scope == "self" for run in automatic.values())
        # Manual admission must see the same fair turn as the worker. In the
        # real installed failure, a younger accepted request expired while an
        # older scheduled context consumed the shared allowance first.
        cloud_work = tuple(item for item in work if item.key[0] == "ollama")
        assert len(cloud_work) >= 2
        before_admission_read = hashlib.sha256(target.read_bytes()).hexdigest()
        actions = CloudUsageActionsV1(reference)
        deferred = 0
        for proposed in queued:
            key = ("ollama", proposed.budget_scope_digest, proposed.operation_family)
            has_turn = actions._has_dispatch_turn(proposed, datetime.now(UTC))
            assert has_turn == (key == cloud_work[0].key)
            deferred += not has_turn
        assert deferred > 0, "older_genuine_contender_required"
        assert hashlib.sha256(target.read_bytes()).hexdigest() == before_admission_read
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
        # The second run is already claimed. It cannot also witness a later
        # dispatch when eligible contexts happen to span different accounts.
        later = next(
            (
                run
                for run in queued
                if run.account_id != first.account_id and run.run_id != second.run_id
            ),
            None,
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


def test_real_dispatch_service_age_survives_reopen_expiry_and_budget_refusal(
    tmp_path: Path,
) -> None:
    """Private metadata claims and natural expiry; no credential/provider I/O."""
    root = tmp_path / "rounds"
    root.mkdir(mode=0o700)
    database = root / "agentmonitor.db"
    os.close(os.open(database, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    deadline = time.monotonic() + 175
    try:
        with sqlite3.connect(
            "file:/home/dev/.local/share/agentmonitor/agentmonitor.db?mode=ro", uri=True
        ) as source:
            with sqlite3.connect(database) as copied:
                source.backup(copied)
                principal = copied.execute(
                    "SELECT administrator_id FROM iam_administrator"
                ).fetchone()
        assert principal is not None, "real_owner_metadata_unavailable"
        reference = DatabaseRefV1(database, root)
        registry = SqliteRegistryRepositoryV1(reference)
        cloud = SqliteCloudCredentialRegistryV1(reference)

        def repository() -> SqliteCollectionRepositoryV1:
            return SqliteCollectionRepositoryV1(
                reference, cloud_admission_fence=cloud_usage_fence
            )

        def facts() -> tuple[int, ...]:
            with sqlite3.connect(database) as connection:
                return tuple(
                    int(
                        connection.execute(f"SELECT count(*) FROM {table}").fetchone()[
                            0
                        ]
                    )
                    for table in (
                        "capacity_budget_report",
                        "capacity_commit_receipt",
                        "capacity_budget_observation",
                        "capacity_usage_bucket",
                        "collection_ollama_cloud_admission",
                    )
                )

        def intent(run: CloudBudgetCollectionRunAdmissionV1) -> tuple[object, ...]:
            with sqlite3.connect(database) as connection:
                row = connection.execute(
                    "SELECT primary_request_id,request_digest,requested_at,"
                    "deadline_at,target_generation FROM collection_run WHERE run_id=?",
                    (run.run_id.value,),
                ).fetchone()
            assert row is not None, "original_claim_intent_missing"
            return tuple(row)

        accounts = tuple(
            account
            for account in registry.list_accounts(provider_key="ollama", page_size=100)
            if account.is_effective_monitoring_enabled
            and account.lifecycle == "active"
            and cloud.read_monitoring_target(account.account_id) is not None
        )[:2]
        assert len(accounts) == 2, "two_real_enabled_accounts_required"

        pending_competitors: dict[OpaqueIdV1, CloudBudgetCollectionRunAdmissionV1] = {}

        def build_round() -> tuple[CloudBudgetCollectionRunAdmissionV1, ...]:
            admitted: list[CloudBudgetCollectionRunAdmissionV1] = []
            for account in accounts:
                graph = cloud.read_monitoring_target(account.account_id)
                assert graph is not None and graph.lifecycle == "active"
                service = cloud.read_active_access_target(graph.access_target_id)
                assert service is not None, "real_cloud_authority_required"
                revision = CapacityScopeMembershipQueryV2(registry)(
                    "account", account.account_id
                ).registry_revision
                for range_key, scope in (
                    ("7d", "self"),
                    ("7d", "team"),
                    ("30d", "self"),
                    ("30d", "team"),
                ):
                    now = datetime.now(UTC)
                    period = completed_period(now, range_key)
                    command = CloudUsageCollectCommandV1(
                        account.account_id,
                        graph.resource_id,
                        account.record_version,
                        graph.record_version,
                        OpaqueIdV1(principal[0]),
                        OpaqueIdV1("round-command-" + secrets.token_hex(12)),
                        now,
                        CloudBudgetReportContextV1(
                            cast(Literal["self", "team"], scope),
                            cast(Literal["7d", "30d"], range_key),
                            period.start,
                            period.end,
                        ),
                    )
                    run = build_manual_usage_run(
                        command,
                        graph=graph,
                        service=service,
                        registry_revision=revision,
                    )
                    # Capture a second independent request at this actual
                    # observation time. Its original allowance window remains
                    # meaningful even if dispatch crosses a wall-clock slot.
                    pending_competitors[run.run_id] = build_manual_usage_run(
                        replace(
                            command,
                            command_id=OpaqueIdV1(
                                "competing-command-" + secrets.token_hex(12)
                            ),
                        ),
                        graph=graph,
                        service=service,
                        registry_revision=revision,
                    )
                    admitted.append(run)
            return tuple(admitted)

        baseline_facts = facts()
        admitted: list[CloudBudgetCollectionRunAdmissionV1] = []
        chosen: set[tuple[OpaqueIdV1, str]] = set()
        for run in build_round():
            context_key = (run.cloud_target.account_id, run.report_context.range_key)
            if context_key in chosen:
                continue
            try:
                repository().admit_run(run)
            except CollectionRepositoryErrorV1 as error:
                assert error.code in {
                    "collection_budget_exhausted",
                    "collection_lease_conflict",
                    "collection_schedule_conflict",
                    "collection_retry_deferred",
                }, error.code
                continue
            admitted.append(run)
            chosen.add(context_key)
        queued = tuple(admitted)
        original_intents = tuple(map(intent, queued))
        by_key = {
            ("ollama", run.budget_scope_digest, run.operation_family): run
            for run in queued
        }
        assert len(by_key) == 4, "four_independent_real_contexts_required"
        served: set[tuple[str, str, str]] = set()
        current_starts: dict[tuple[str, str, str], datetime] = {}
        for _ in range(len(by_key)):
            assert time.monotonic() < deadline, "real_round_deadline_exceeded"
            reopened = repository()
            usage = OllamaUsageCollectionV1(
                root, credential_env_file=None, deadline_monotonic=deadline
            )
            work, _, _ = prepare_financial_dispatch(
                reopened,
                BillingScheduleV1(reference),
                usage.prepare_runs(),
                deadline_monotonic=deadline,
            )
            eligible = tuple(
                item for item in work if item.key in by_key and item.queued_run_id
            )
            assert len(eligible) == len(by_key) - len(served)
            selected = eligible[0]
            assert (
                selected.last_started_at or datetime.min.replace(tzinfo=UTC)
            ) == min(
                item.last_started_at or datetime.min.replace(tzinfo=UTC)
                for item in eligible
            ), "older_eligible_context_overtaken"
            assert selected.key not in served, "eligible_context_starved"
            original = by_key[selected.key]
            before_intent = intent(original)
            started = datetime.now(UTC)
            claimed = reopened.claim_next_budget_run(
                scheduler_instance_id=OpaqueIdV1(
                    "round-worker-" + secrets.token_hex(12)
                ),
                as_of=started,
                resolve_budget_limit=usage_budget_limit,
                provider_key="ollama",
                capability_id="api.usage",
                source_id="ollama.cloud.usage.v1",
                manifest_fingerprint=usage_manifest_fingerprint(),
                collection_policy_version=POLICY_VERSION,
                operation_family=original.operation_family,
                expected_run_id=original.run_id,
            )
            assert isinstance(claimed, CloudBudgetCollectionRunAdmissionV1)
            assert claimed.run_id == original.run_id
            assert claimed.report_context == original.report_context
            assert intent(original) == before_intent
            snapshot = repository().read_budget_dispatch_snapshot(
                provider_key="ollama",
                capability_id="api.usage",
                source_id="ollama.cloud.usage.v1",
                manifest_fingerprint=usage_manifest_fingerprint(),
                collection_policy_version=POLICY_VERSION,
                operation_families=(original.operation_family,),
                budget_scope_digests=(original.budget_scope_digest,),
                schedule_ids=(original.schedule_id,),
                as_of=datetime.now(UTC),
            )
            assert len(snapshot.states) == 1
            assert snapshot.states[0].last_started_at == started
            assert snapshot.states[0].queued_run_id is None
            served.add(selected.key)
            current_starts[selected.key] = started
        assert served == set(by_key)
        assert facts() == baseline_facts, "metadata_claim_created_provider_facts"
        # Each genuine claim consumes its existing 15-minute allowance.
        # Check every independently captured competing request in that same
        # slot, without treating a naturally renewed slot as exhausted.
        for previous in queued:
            competing = pending_competitors[previous.run_id]
            assert competing.run_id != previous.run_id
            assert competing.budget_window_start == previous.budget_window_start
            assert competing.requested_at == previous.requested_at
            with pytest.raises(
                CollectionRepositoryErrorV1, match="^collection_budget_exhausted$"
            ):
                repository().admit_run(competing)
        # Claims were never sent to a provider. Let actual leases and
        # heartbeats expire without moving clocks or rewriting state.
        recover_at = max(current_starts.values()) + timedelta(seconds=120.1)
        while datetime.now(UTC) < recover_at:
            assert time.monotonic() < deadline, "real_expiry_deadline_exceeded"
            remaining = (recover_at - datetime.now(UTC)).total_seconds()
            time.sleep(max(0, min(20, remaining)))
        recovery = OllamaUsageCollectionV1(
            root, credential_env_file=None, deadline_monotonic=deadline
        )
        assert recovery.run(recovery_only=True) == 0
        for original in queued:
            reopened = repository()
            finished = reopened.get_run(original.run_id)
            assert isinstance(finished, BudgetCollectionRunViewV1)
            assert finished.state == "failed"
            assert finished.error_code == "collection_worker_interrupted"
            assert finished.report_id is None
            snapshot = reopened.read_budget_dispatch_snapshot(
                provider_key="ollama",
                capability_id="api.usage",
                source_id="ollama.cloud.usage.v1",
                manifest_fingerprint=usage_manifest_fingerprint(),
                collection_policy_version=POLICY_VERSION,
                operation_families=(original.operation_family,),
                budget_scope_digests=(original.budget_scope_digest,),
                schedule_ids=(original.schedule_id,),
                as_of=datetime.now(UTC),
            )
            assert len(snapshot.states) == 1
            assert (
                snapshot.states[0].last_started_at
                == current_starts[
                    "ollama", original.budget_scope_digest, original.operation_family
                ]
            ), "recovery_changed_service_age"
            assert snapshot.states[0].queued_run_id is None
            assert reopened.get_admission_state(original.run_id) == (
                "released",
                "expired_conservative",
            ), "recovery_released_conservative_budget"
            now = datetime.now(UTC)
            if now < original.budget_window_end:
                assert (
                    reopened.get_budget_next_allowed_at(
                        original.budget_scope_digest, "request", "count", now
                    )
                    == original.budget_window_end
                )
        assert facts() == baseline_facts, "recovery_created_provider_facts"
        assert tuple(map(intent, queued)) == original_intents
    finally:
        shutil.rmtree(root)
