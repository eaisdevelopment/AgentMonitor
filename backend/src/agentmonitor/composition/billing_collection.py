"""Connect an admitted billing run to its source and fenced report sink.

Anthropic and OpenAI completed 7/30-day costs use the same fenced run lifecycle.
Anthropic usage uses its distinct typed source under the same request budget.
"""

import time
import uuid
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingAccessRepositoryV1,
    ensure_billing_access_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    AnthropicUsageRequestV1,
)
from agentmonitor.adapters.providers.claude.anthropic_api.source import (
    AnthropicCostResultV1,
    AnthropicUsageResultV1,
    collect_cost_report_in_worker_v1,
    collect_usage_report_in_worker_v1,
)
from agentmonitor.adapters.providers.codex.openai_api.policy import OpenAIUsageRequestV1
from agentmonitor.adapters.providers.codex.openai_api.source import (
    OpenAICostResultV1,
    OpenAIUsageResultV1,
)
from agentmonitor.adapters.providers.codex.openai_api.source import (
    collect_cost_report_in_worker_v1 as collect_openai_cost_report_in_worker_v1,
)
from agentmonitor.adapters.providers.codex.openai_api.source import (
    collect_usage_report_in_worker_v1 as collect_openai_usage_report_in_worker_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    approve_env_credential_file_v1,
    env_credential_file_lease_v1,
)
from agentmonitor.composition.billing_capacity_commit import billing_capacity_repository
from agentmonitor.composition.billing_context import (
    billing_report_operation_families as billing_report_operation_families,
)
from agentmonitor.composition.billing_context import (
    billing_source_operations,
)
from agentmonitor.composition.billing_env_authorization import (
    AnthropicEnvAuthorizationV1,
    OpenAIEnvAuthorizationV1,
)
from agentmonitor.composition.ollama_env_store import env_location_matches
from agentmonitor.composition.openai_billing_run import OPENAI_COST_AUTHORITY_ID_V1
from agentmonitor.contracts.capacity_v1 import BudgetReportInputV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunAdmissionV1,
    CollectionFailedV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1
from agentmonitor.modules.collection_control.application.budget_executor import (
    ExecuteBudgetCollectionRunV1,
)


class BillingCollectionV1:
    """Sequential eligible runs within one supervised worker's fixed deadline."""

    def __init__(
        self,
        data_root: Path,
        *,
        credential_env_file: Path | None,
        deadline_monotonic: float,
    ) -> None:
        self._reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
        self._reference.validate()
        self._data_root = data_root
        self._credential_env_file = credential_env_file
        self._deadline = deadline_monotonic
        self._instance = OpaqueIdV1("billing-worker-" + uuid.uuid4().hex)
        self._runs = SqliteCollectionRepositoryV1(
            self._reference,
            billing_admission_fence=ensure_billing_access_in_transaction,
        )

    def run(self, *, recovery_only: bool = False) -> int:
        """Reconcile receipts before admitting any new provider work."""
        now = datetime.now(UTC)
        recovery = ExecuteBudgetCollectionRunV1(
            self._runs, SqliteBudgetReportRepositoryV1(self._reference)
        )
        recovery_owner = OpaqueIdV1("billing-recovery-" + uuid.uuid4().hex)
        recovery_sources = tuple(
            (provider, capability, source)
            for provider in ("claude", "codex")
            for capability, source, _ in billing_source_operations(provider)
        )
        for provider, capability, source in recovery_sources:
            recovery.recover_expired_runs(
                provider_key=provider,
                capability_id=capability,
                source_id=source,
                as_of=now,
                owner_stale_before=now - timedelta(seconds=120),
                recovery_instance_id=recovery_owner,
                recovery_lease_expires_at=now + timedelta(seconds=30),
                maximum_runs=16,
            )
            recovery.recover_pending_commits(
                provider_key=provider,
                capability_id=capability,
                source_id=source,
                as_of=now,
                owner_stale_before=now - timedelta(seconds=120),
                recovery_instance_id=recovery_owner,
                recovery_lease_expires_at=now + timedelta(seconds=30),
                maximum_runs=16,
            )
        if recovery_only:
            from agentmonitor.composition.ollama_usage_collection import (
                OllamaUsageCollectionV1,
            )

            return OllamaUsageCollectionV1(
                self._data_root,
                credential_env_file=self._credential_env_file,
                deadline_monotonic=self._deadline,
            ).run(recovery_only=True)
        if self._credential_env_file is None:
            return 3
        if time.monotonic() >= self._deadline - 5:
            return 4
        # Re-read persisted eligibility after every completed attempt. Sleeping
        # between eligible keys can expire an accepted manual request while the
        # worker is idle. Keep the existing ordering, source budgets and deadline.
        while time.monotonic() < self._deadline - 20:
            # M04 claim owners are single-use attempt identities, not process IDs.
            # Keep that fence intact while the same process dispatches sequentially.
            self._instance = OpaqueIdV1("billing-worker-" + uuid.uuid4().hex)
            if not self._dispatch_one():
                break
        return 0

    def _claim_one(
        self, *, provider_key: str, operation_family: str, expected_run_id: OpaqueIdV1
    ) -> BudgetCollectionRunAdmissionV1 | None:
        from agentmonitor.composition.billing_run import (
            ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
            anthropic_billing_budget_limit,
            anthropic_cost_manifest_fingerprint,
        )
        from agentmonitor.composition.openai_billing_run import (
            OPENAI_COST_COLLECTION_POLICY_VERSION_V1,
            openai_billing_budget_limit,
            openai_cost_manifest_fingerprint,
        )

        # Exact selected run retains the source-specific authority/rate fence.
        for provider, fingerprint, policy, limit in (
            (
                "claude",
                anthropic_cost_manifest_fingerprint(),
                ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
                anthropic_billing_budget_limit,
            ),
            (
                "codex",
                openai_cost_manifest_fingerprint(),
                OPENAI_COST_COLLECTION_POLICY_VERSION_V1,
                openai_billing_budget_limit,
            ),
        ):
            if provider != provider_key:
                continue
            for capability, source, operations in billing_source_operations(provider):
                if operation_family not in operations:
                    continue
                admission = self._runs.claim_next_budget_run(
                    scheduler_instance_id=self._instance,
                    as_of=datetime.now(UTC),
                    resolve_budget_limit=limit,
                    provider_key=provider,
                    capability_id=capability,
                    source_id=source,
                    manifest_fingerprint=fingerprint,
                    collection_policy_version=policy,
                    operation_family=operation_family,
                    expected_run_id=expected_run_id,
                )
                if admission is not None:
                    if not isinstance(admission, BudgetCollectionRunAdmissionV1):
                        raise ValueError("billing_admission_provider_mismatch")
                    return admission
        return None

    def _dispatch_one(self) -> bool:
        """Return whether a real run was dispatched, including recorded failures."""
        from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
            BudgetCollectionError,
        )
        from agentmonitor.composition.billing_schedule import BillingScheduleV1
        from agentmonitor.composition.financial_dispatch import (
            prepare_financial_dispatch,
        )
        from agentmonitor.composition.ollama_usage_collection import (
            OllamaUsageCollectionV1,
        )

        scheduler = BillingScheduleV1(self._reference)
        usage = OllamaUsageCollectionV1(
            self._data_root,
            credential_env_file=self._credential_env_file,
            deadline_monotonic=self._deadline,
        )
        work, billing_due, usage_due = prepare_financial_dispatch(
            self._runs,
            scheduler,
            usage.prepare_runs(),
            deadline_monotonic=self._deadline,
        )
        for candidate in work:
            if time.monotonic() >= self._deadline - 20:
                return False
            provider, _, operation = candidate.key
            try:
                if candidate.queued_run_id is not None:
                    if provider == "ollama":
                        if usage.dispatch_manual(
                            operation_family=operation,
                            expected_run_id=candidate.queued_run_id,
                        ):
                            return True
                    else:
                        admission = self._claim_one(
                            provider_key=provider,
                            operation_family=operation,
                            expected_run_id=candidate.queued_run_id,
                        )
                        if admission is not None:
                            self._execute(admission)
                            return True
            except BudgetCollectionError as error:
                if error.code != "budget_dispatch_authority_unavailable":
                    raise
                # No lease/owner was changed: allow valid scheduled work or a
                # later resource rather than repeating the invalid head forever.
            if not candidate.scheduled_due:
                continue
            if provider == "ollama":
                if usage.dispatch_scheduled(usage_due[candidate.key]):
                    return True
            else:
                scheduled = scheduler.enqueue_intent(
                    billing_due[candidate.key], deadline_monotonic=self._deadline
                )
                if scheduled is not None:
                    try:
                        admission = self._claim_one(
                            provider_key=provider,
                            operation_family=operation,
                            expected_run_id=scheduled.run_id,
                        )
                    except BudgetCollectionError as error:
                        if error.code != "budget_dispatch_authority_unavailable":
                            raise
                        continue
                    if admission is not None:
                        self._execute(admission)
                        return True
        return False

    def _execute(self, admission: BudgetCollectionRunAdmissionV1) -> int:
        from agentmonitor.composition.billing_run import (
            anthropic_billing_outcome,
            anthropic_billing_request,
            normalize_anthropic_billing_outcome,
        )
        from agentmonitor.composition.openai_billing_run import (
            normalize_openai_billing_outcome,
            openai_billing_outcome,
            openai_billing_request,
        )

        if admission.provider_key not in {"claude", "codex"}:
            raise ValueError("billing_admission_provider_mismatch")
        is_openai = admission.provider_key == "codex"
        run = self._runs.assert_claimed_budget_run(admission, datetime.now(UTC))
        service_target = SqliteCloudCredentialRegistryV1(
            self._reference
        ).read_active_access_target(admission.provider_target.target_id)
        if (
            service_target is None
            or service_target.provider_key != admission.provider_key
            or service_target.authority_id
            != (OPENAI_COST_AUTHORITY_ID_V1 if is_openai else "anthropic.analytics")
            or service_target.manifest_fingerprint != admission.manifest_fingerprint
        ):
            self._runs.finalize_failed(
                CollectionFailedV1(
                    admission.run_id,
                    "blocked",
                    "billing_service_target_unavailable",
                    datetime.now(UTC),
                ),
                fencing_token=run.fencing_token,
                scheduler_instance_id=self._instance,
            )
            return 0
        executor = ExecuteBudgetCollectionRunV1(
            self._runs,
            billing_capacity_repository(
                self._reference,
                scheduler_instance_id=self._instance,
                fencing_token=run.fencing_token,
                access_target=service_target,
            ),
        )
        target = admission.billing_target
        with ExitStack() as stack:
            authorization: (
                AnthropicEnvAuthorizationV1 | OpenAIEnvAuthorizationV1 | None
            ) = None
            try:
                lock = stack.enter_context(
                    account_credential_lock(
                        self._reference, target.connection.account_id
                    )
                )
                SqliteBillingAccessRepositoryV1(self._reference).ensure_current(target)
                if self._credential_env_file is None or not env_location_matches(
                    self._data_root, self._credential_env_file
                ):
                    raise ValueError("billing_credential_location_unavailable")
                file = stack.enter_context(
                    env_credential_file_lease_v1(
                        approve_env_credential_file_v1(self._credential_env_file)
                    )
                )
                authorize = (
                    OpenAIEnvAuthorizationV1
                    if is_openai
                    else AnthropicEnvAuthorizationV1
                )
                authorization = authorize(
                    target.binding.binding_id.value,
                    target.connection.account_id,
                    lock.inherited_lock(target.connection.account_id),
                    file.inherited_file(),
                )
            except (OSError, ValueError):
                # No source is invoked when the actual current authority fails.
                # The normal executor records this failure without freshening money.
                authorization = None

            def deadline() -> float:
                remaining = (
                    admission.deadline_at - datetime.now(UTC)
                ).total_seconds() - 5
                return min(self._deadline - 5, time.monotonic() + remaining)

            def collect_openai() -> CollectionOutcomeV1[BudgetReportInputV1]:
                assert authorization is None or isinstance(
                    authorization, OpenAIEnvAuthorizationV1
                )
                request = openai_billing_request(admission)
                source_deadline = deadline()
                if source_deadline <= time.monotonic():
                    result_type = (
                        OpenAIUsageResultV1
                        if isinstance(request, OpenAIUsageRequestV1)
                        else OpenAICostResultV1
                    )
                    result = result_type(
                        "deadline_exceeded", "openai_report_deadline_exceeded", None, 0
                    )
                elif isinstance(request, OpenAIUsageRequestV1):
                    result = collect_openai_usage_report_in_worker_v1(
                        request,
                        authorization=authorization,
                        deadline_monotonic=source_deadline,
                    )
                else:
                    result = collect_openai_cost_report_in_worker_v1(
                        request,
                        authorization=authorization,
                        deadline_monotonic=source_deadline,
                    )
                return openai_billing_outcome(admission, result, datetime.now(UTC))

            def collect_anthropic() -> CollectionOutcomeV1[BudgetReportInputV1]:
                assert authorization is None or isinstance(
                    authorization, AnthropicEnvAuthorizationV1
                )
                request = anthropic_billing_request(admission)
                source_deadline = deadline()
                usage_request = isinstance(request, AnthropicUsageRequestV1)
                if source_deadline <= time.monotonic():
                    result_type = (
                        AnthropicUsageResultV1
                        if usage_request
                        else AnthropicCostResultV1
                    )
                    result = result_type(
                        "deadline_exceeded",
                        "anthropic_analytics_deadline_exceeded",
                        None,
                        0,
                    )
                elif isinstance(request, AnthropicUsageRequestV1):
                    result = collect_usage_report_in_worker_v1(
                        request,
                        authorization=authorization,
                        deadline_monotonic=source_deadline,
                    )
                else:
                    result = collect_cost_report_in_worker_v1(
                        request,
                        authorization=authorization,
                        deadline_monotonic=source_deadline,
                    )
                return anthropic_billing_outcome(admission, result, datetime.now(UTC))

            executor.execute_claimed(
                admission,
                collect_openai if is_openai else collect_anthropic,
                normalize_openai_billing_outcome
                if is_openai
                else normalize_anthropic_billing_outcome,
                as_of=datetime.now(UTC),
                completed_at=lambda: datetime.now(UTC),
            )
        # A durably recorded provider failure is a completed worker, not a
        # successful report. M04 state, never this exit code, drives the UI.
        return 0
