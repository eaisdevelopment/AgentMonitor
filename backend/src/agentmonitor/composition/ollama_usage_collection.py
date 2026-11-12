"""One bounded usage report in the existing supervised billing worker."""

import secrets
import time
import uuid
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path

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
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.api.policy import (
    SOURCE_ID,
    completed_period,
)
from agentmonitor.adapters.providers.ollama.api.source import (
    OllamaUsageResultV1,
    collect_usage_report_in_worker_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    approve_env_credential_file_v1,
    env_credential_file_lease_v1,
)
from agentmonitor.composition.billing_env_authorization import (
    OllamaUsageEnvAuthorizationV1,
)
from agentmonitor.composition.ollama_env_store import env_location_matches
from agentmonitor.composition.ollama_usage_dispatch import usage_no_response_terminal
from agentmonitor.composition.ollama_usage_fence import (
    cloud_usage_fence,
    usage_capacity_repository,
)
from agentmonitor.composition.ollama_usage_result import (
    normalize_usage_report,
    usage_outcome,
)
from agentmonitor.composition.ollama_usage_run import (
    POLICY_VERSION,
    build_ollama_usage_run,
    usage_budget_limit,
    usage_manifest_fingerprint,
    usage_request_for_run,
)
from agentmonitor.contracts.capacity_v1 import BudgetReportInputV1
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
    CollectionFailedV1,
    CollectionFailurePolicyV1,
    OllamaCloudNoResponseCompletionV2,
    OllamaCloudRequestAcquireV1,
    OllamaCloudRequestCompletionV1,
    OllamaCloudRequestLeaseV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1
from agentmonitor.modules.collection_control.application.budget_executor import (
    ExecuteBudgetCollectionRunV1,
)


class _UsageAdmissionDeferred(Exception):
    """Known admission race before any provider dispatch."""


class _UsageNotStarted(Exception):
    """Internal control flow carrying only a proven sanitized no-request result."""

    def __init__(
        self, terminal: OllamaCloudNoResponseCompletionV2, result: OllamaUsageResultV1
    ) -> None:
        super().__init__("ollama_usage_request_not_started")
        self.terminal = terminal
        self.result = result


class OllamaUsageCollectionV1:
    """Reuse existing metadata, rate gate, worker lifetime and report receipts."""

    def __init__(
        self,
        data_root: Path,
        *,
        credential_env_file: Path | None,
        deadline_monotonic: float,
    ) -> None:
        self._root = data_root
        self._reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
        self._env_file = credential_env_file
        self._deadline = deadline_monotonic
        self._instance = OpaqueIdV1("usage-worker-" + uuid.uuid4().hex)
        self._recovered = False
        self._gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(
            self._reference
        )

    def _recover(self) -> None:
        """Reconcile expired authority before either queued or scheduled work."""
        if self._recovered:
            return
        now = datetime.now(UTC)
        stale = now - timedelta(seconds=120)
        recovery_owner = OpaqueIdV1("usage-recovery-" + uuid.uuid4().hex)
        self._gate.recover_rate_gate(now, owner_stale_before=stale)
        runs = SqliteCollectionRepositoryV1(
            self._reference, cloud_admission_fence=cloud_usage_fence
        )
        recovery = ExecuteBudgetCollectionRunV1(
            runs, SqliteBudgetReportRepositoryV1(self._reference)
        )
        recovery.recover_expired_runs(
            provider_key="ollama",
            capability_id="api.usage",
            source_id=SOURCE_ID,
            as_of=now,
            owner_stale_before=stale,
            recovery_instance_id=recovery_owner,
            recovery_lease_expires_at=now + timedelta(seconds=30),
            maximum_runs=16,
        )
        recovery.recover_pending_commits(
            provider_key="ollama",
            capability_id="api.usage",
            source_id=SOURCE_ID,
            as_of=now,
            owner_stale_before=stale,
            recovery_instance_id=recovery_owner,
            recovery_lease_expires_at=now + timedelta(seconds=30),
            maximum_runs=16,
        )
        self._recovered = True

    def run(self, *, recovery_only: bool = False) -> int:
        self._recover()
        if recovery_only:
            return 0
        if self._env_file is None:
            return 3
        from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
            BudgetCollectionError,
        )
        from agentmonitor.composition.billing_schedule import BillingScheduleV1
        from agentmonitor.composition.financial_dispatch import (
            prepare_financial_dispatch,
        )

        work, _, scheduled = prepare_financial_dispatch(
            SqliteCollectionRepositoryV1(self._reference),
            BillingScheduleV1(self._reference),
            self.prepare_runs(),
            deadline_monotonic=self._deadline,
        )
        for candidate in work:
            if candidate.key[0] != "ollama":
                continue
            if candidate.queued_run_id is not None:
                try:
                    if self.dispatch_manual(
                        operation_family=candidate.key[2],
                        expected_run_id=candidate.queued_run_id,
                    ):
                        return 0
                except BudgetCollectionError as error:
                    if error.code != "budget_dispatch_authority_unavailable":
                        raise
            if candidate.scheduled_due and self.dispatch_scheduled(
                scheduled[candidate.key]
            ):
                return 0
        return 0

    def prepare_runs(self) -> tuple[CloudBudgetCollectionRunAdmissionV1, ...]:
        """Read the complete bounded inventory before selecting any usage work."""
        self._recover()
        registry = SqliteRegistryRepositoryV1(self._reference)
        cloud = SqliteCloudCredentialRegistryV1(self._reference)
        cursor = None
        scanned = 0
        prepared: list[CloudBudgetCollectionRunAdmissionV1] = []
        while scanned < 1000:
            if time.monotonic() >= self._deadline - 20:
                raise ValueError("ollama_usage_inventory_deadline")
            accounts = registry.list_accounts(
                provider_key="ollama", page_size=100, after_key=cursor
            )
            scanned += len(accounts)
            for account in accounts:
                if (
                    not account.is_effective_monitoring_enabled
                    or account.lifecycle != "active"
                ):
                    continue
                graph = cloud.read_monitoring_target(account.account_id)
                if graph is None or graph.lifecycle != "active":
                    continue
                service = cloud.read_active_access_target(graph.access_target_id)
                if service is None:
                    continue
                for scope in ("self", "team"):
                    for range_key in ("7d", "30d"):
                        now = datetime.now(UTC)
                        period = completed_period(now, range_key)
                        run = build_ollama_usage_run(
                            graph=graph,
                            service=service,
                            context=CloudBudgetReportContextV1(
                                scope, range_key, period.start, period.end
                            ),
                            registry_revision=account.registry_revision,
                            scheduler_instance_id=self._instance,
                            run_id=OpaqueIdV1("usage-run-" + uuid.uuid4().hex),
                            request_id=OpaqueIdV1("usage-request-" + uuid.uuid4().hex),
                            requested_at=now,
                        )
                        # Team reads remain explicit owner requests; inventory
                        # includes their scope only to find already queued work.
                        if scope == "self":
                            self._gate.register_schedule(run)
                        prepared.append(run)
            if len(accounts) < 100:
                return tuple(prepared)
            cursor = accounts[-1].account_id.value
        raise ValueError("ollama_usage_target_limit")

    def dispatch_scheduled(self, run: CloudBudgetCollectionRunAdmissionV1) -> bool:
        if self._env_file is None or time.monotonic() >= self._deadline - 20:
            return False
        now = datetime.now(UTC)
        if run.deadline_at <= now or run.report_context.scope != "self":
            return False
        if (
            SqliteCollectionRepositoryV1(self._reference).get_budget_next_allowed_at(
                run.budget_scope_digest, run.budget_dimension, run.budget_unit, now
            )
            is not None
        ):
            return False
        decision = self._gate.acquire_usage(
            OllamaCloudRequestAcquireV1(
                OpaqueIdV1("usage-admission-" + uuid.uuid4().hex),
                self._instance,
                now,
                run.deadline_at,
                secrets.randbelow(11),
            ),
            admission=run,
        )
        if decision.lease is None:
            return False
        try:
            self._execute(run, decision.lease)
        except _UsageAdmissionDeferred:
            return False
        return True

    def dispatch_manual(
        self,
        *,
        operation_family: str | None = None,
        expected_run_id: OpaqueIdV1 | None = None,
    ) -> bool:
        """Claim durable owner work and shared rate authority in one transaction."""
        self._recover()
        if self._env_file is None or time.monotonic() >= self._deadline - 20:
            return False
        operations = (
            (operation_family,)
            if operation_family is not None
            else ("collect.ollama.usage.7d", "collect.ollama.usage.30d")
        )
        for operation in operations:
            claimed = self._gate.claim_next_usage_run(
                scheduler_instance_id=self._instance,
                as_of=datetime.now(UTC),
                resolve_budget_limit=usage_budget_limit,
                manifest_fingerprint=usage_manifest_fingerprint(),
                collection_policy_version=POLICY_VERSION,
                operation_family=operation,
                expected_run_id=expected_run_id,
                cloud_admission_fence=cloud_usage_fence,
                jitter_seconds=secrets.randbelow(11),
            )
            if claimed is not None:
                self._execute(*claimed, claimed=True)
                return True
        return False

    def _execute(
        self,
        run: CloudBudgetCollectionRunAdmissionV1,
        lease: OllamaCloudRequestLeaseV1,
        *,
        claimed: bool = False,
    ) -> None:
        completion: OllamaCloudRequestCompletionV1 | None = None
        runs = cloud_admission.SqliteOllamaCloudRunRepositoryV1(
            self._reference, lease, cloud_admission_fence=cloud_usage_fence
        )
        try:
            request = usage_request_for_run(run, dispatched_at=datetime.now(UTC))
            with ExitStack() as stack:
                lock = stack.enter_context(
                    account_credential_lock(
                        self._reference, run.cloud_target.account_id
                    )
                )
                if self._env_file is None or not env_location_matches(
                    self._root, self._env_file
                ):
                    raise ValueError("ollama_usage_credential_location_unavailable")
                file = stack.enter_context(
                    env_credential_file_lease_v1(
                        approve_env_credential_file_v1(self._env_file)
                    )
                )
                authorization = OllamaUsageEnvAuthorizationV1(
                    run.cloud_target.binding.binding_id.value,
                    run.cloud_target.account_id,
                    lock.inherited_lock(run.cloud_target.account_id),
                    file.inherited_file(),
                )
                try:
                    admitted = (
                        runs.get_run(run.run_id) if claimed else runs.admit_run(run)
                    )
                except CollectionRepositoryErrorV1 as error:
                    if not claimed and error.code in {
                        "collection_budget_exhausted",
                        "collection_retry_deferred",
                        "collection_schedule_conflict",
                        "collection_generation_conflict",
                    }:
                        raise _UsageAdmissionDeferred() from None
                    raise
                if claimed:
                    runs.assert_claimed_budget_run(run, as_of=datetime.now(UTC))
                else:
                    runs.mark_running(
                        run.run_id,
                        datetime.now(UTC),
                        fencing_token=admitted.fencing_token,
                        scheduler_instance_id=self._instance,
                    )
                executor = ExecuteBudgetCollectionRunV1(
                    runs,
                    usage_capacity_repository(
                        self._reference,
                        admission=run,
                        lease=lease,
                        fencing_token=admitted.fencing_token,
                    ),
                )

                def collect() -> CollectionOutcomeV1[BudgetReportInputV1]:
                    nonlocal completion
                    self._gate.mark_dispatched(lease, datetime.now(UTC))
                    remaining = (
                        min(run.deadline_at, lease.lease_expires_at) - datetime.now(UTC)
                    ).total_seconds() - 5
                    result = collect_usage_report_in_worker_v1(
                        request,
                        authorization=authorization,
                        deadline_monotonic=min(
                            self._deadline - 5, time.monotonic() + remaining
                        ),
                    )
                    completed = datetime.now(UTC)
                    terminal = usage_no_response_terminal(
                        result, lease, completed_at=completed
                    )
                    if terminal is not None:
                        raise _UsageNotStarted(terminal, result)
                    if result.http_status is None:
                        # Dispatched with no known response: retain uncertainty until
                        # the existing expired-owner recovery proves it can release.
                        raise ValueError("ollama_usage_outcome_unresolved")
                    successful = result.state in {"success", "partial"}
                    completion = OllamaCloudRequestCompletionV1(
                        lease.admission_id,
                        lease.scheduler_instance_id,
                        lease.schedule_id,
                        lease.fencing_token,
                        lease.started_at,
                        completed,
                        "succeeded"
                        if successful
                        else "rate_limited"
                        if result.state == "rate_limited"
                        else "failed",
                        result.retry_after_seconds
                        if result.state == "rate_limited"
                        else None,
                        secrets.randbelow(11),
                    )
                    self._gate.record_completion(
                        lease,
                        completion,
                        failure_code=None if successful else result.state,
                    )
                    return usage_outcome(run, result, completed_at=completed)

                try:
                    executor.execute_claimed(
                        run,
                        collect,
                        normalize_usage_report,
                        as_of=datetime.now(UTC),
                        completed_at=lambda: datetime.now(UTC),
                    )
                except _UsageNotStarted as stopped:
                    self._finish_not_started(
                        run,
                        lease,
                        admitted.fencing_token,
                        stopped.terminal,
                        stopped.result,
                    )
                    return
                if completion is not None:
                    self._gate.complete(completion)
        except BaseException:
            try:
                self._gate.recover_rate_gate(
                    datetime.now(UTC), expected=lease, reserved_only=True
                )
            except Exception:  # noqa: BLE001 - retain original, safe worker failure.
                pass
            raise

    def _finish_not_started(
        self,
        run: CloudBudgetCollectionRunAdmissionV1,
        lease: OllamaCloudRequestLeaseV1,
        fencing_token: int,
        terminal: OllamaCloudNoResponseCompletionV2,
        result: OllamaUsageResultV1,
    ) -> None:
        """Release only proven no-request work and preserve its actionable failure."""
        if (
            usage_no_response_terminal(result, lease, completed_at=terminal.terminal_at)
            != terminal
        ):
            raise ValueError("ollama_usage_no_request_proof_invalid")
        outcome = usage_outcome(run, result, completed_at=terminal.terminal_at)
        failed = normalize_usage_report(run, outcome, terminal.terminal_at)
        if not isinstance(failed, CollectionFailedV1) or outcome.error is None:
            raise ValueError("ollama_usage_no_request_proof_invalid")
        self._gate.finish_no_response(lease, terminal)
        cloud_admission.SqliteOllamaNoResponseRunRepositoryV1(
            self._reference, lease.admission_id
        ).finalize_failed(
            failed,
            fencing_token=fencing_token,
            scheduler_instance_id=run.scheduler_instance_id,
            provider_policy=CollectionFailurePolicyV1(
                outcome.state, outcome.error.retry
            ),
        )
