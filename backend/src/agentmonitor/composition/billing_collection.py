"""Connect an admitted billing run to its source and fenced report sink.

The first lane is Anthropic's completed-week cost report. Other billing sources
must be integrated explicitly; a candidate adapter is not runtime admission.
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
from agentmonitor.adapters.providers.claude.anthropic_api.policy import SOURCE_ID
from agentmonitor.adapters.providers.claude.anthropic_api.source import (
    AnthropicCostResultV1,
    collect_cost_report_in_worker_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    approve_env_credential_file_v1,
    env_credential_file_lease_v1,
)
from agentmonitor.composition.billing_capacity_commit import billing_capacity_repository
from agentmonitor.composition.billing_env_authorization import (
    AnthropicEnvAuthorizationV1,
)
from agentmonitor.composition.ollama_env_store import env_location_matches
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
    """One internally selected run; caller cannot supply a provider URL or key."""

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
        recovery.recover_expired_runs(
            provider_key="claude",
            capability_id="api.cost",
            source_id=SOURCE_ID,
            as_of=now,
            owner_stale_before=now - timedelta(seconds=120),
            recovery_instance_id=recovery_owner,
            recovery_lease_expires_at=now + timedelta(seconds=30),
            maximum_runs=16,
        )
        recovery.recover_pending_commits(
            provider_key="claude",
            capability_id="api.cost",
            source_id=SOURCE_ID,
            as_of=now,
            owner_stale_before=now - timedelta(seconds=120),
            recovery_instance_id=recovery_owner,
            recovery_lease_expires_at=now + timedelta(seconds=30),
            maximum_runs=16,
        )
        if recovery_only:
            return 0
        if self._credential_env_file is None:
            return 3
        if time.monotonic() >= self._deadline - 5:
            return 4
        return self._dispatch_one()

    def _dispatch_one(self) -> int:
        from agentmonitor.composition.billing_run import (
            ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
            ANTHROPIC_COST_OPERATION_FAMILY_V1,
            anthropic_billing_budget_limit,
            anthropic_cost_manifest_fingerprint,
        )

        admission = self._runs.claim_next_budget_run(
            scheduler_instance_id=self._instance,
            as_of=datetime.now(UTC),
            resolve_budget_limit=anthropic_billing_budget_limit,
            provider_key="claude",
            capability_id="api.cost",
            source_id=SOURCE_ID,
            manifest_fingerprint=anthropic_cost_manifest_fingerprint(),
            collection_policy_version=ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
            operation_family=ANTHROPIC_COST_OPERATION_FAMILY_V1,
        )
        if admission is None:
            from agentmonitor.composition.billing_schedule import BillingScheduleV1

            scheduled = BillingScheduleV1(self._reference).enqueue_due(
                deadline_monotonic=self._deadline
            )
            if scheduled is None:
                return 0
            admission = self._runs.claim_next_budget_run(
                scheduler_instance_id=self._instance,
                as_of=datetime.now(UTC),
                resolve_budget_limit=anthropic_billing_budget_limit,
                provider_key="claude",
                capability_id="api.cost",
                source_id=SOURCE_ID,
                manifest_fingerprint=anthropic_cost_manifest_fingerprint(),
                collection_policy_version=ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
                operation_family=ANTHROPIC_COST_OPERATION_FAMILY_V1,
            )
            if admission is None:
                return 0
        return self._execute(admission)

    def _execute(self, admission: BudgetCollectionRunAdmissionV1) -> int:
        from agentmonitor.composition.billing_run import (
            anthropic_billing_outcome,
            anthropic_billing_request,
            normalize_anthropic_billing_outcome,
        )

        run = self._runs.assert_claimed_budget_run(admission, datetime.now(UTC))
        service_target = SqliteCloudCredentialRegistryV1(
            self._reference
        ).read_active_access_target(admission.provider_target.target_id)
        if (
            service_target is None
            or service_target.provider_key != admission.provider_key
            or service_target.authority_id != "anthropic.analytics"
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
        request = anthropic_billing_request(admission)
        with ExitStack() as stack:
            authorization: AnthropicEnvAuthorizationV1 | None = None
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
                authorization = AnthropicEnvAuthorizationV1(
                    target.binding.binding_id.value,
                    target.connection.account_id,
                    lock.inherited_lock(target.connection.account_id),
                    file.inherited_file(),
                )
            except (OSError, ValueError):
                # No source is invoked when the actual current authority fails.
                # The normal executor records this failure without freshening money.
                authorization = None

            def collect() -> CollectionOutcomeV1[BudgetReportInputV1]:
                now = datetime.now(UTC)
                remaining = (admission.deadline_at - now).total_seconds() - 5
                source_deadline = min(self._deadline - 5, time.monotonic() + remaining)
                if source_deadline <= time.monotonic():
                    result = AnthropicCostResultV1(
                        "deadline_exceeded", "anthropic_cost_deadline_exceeded", None, 0
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
                collect,
                normalize_anthropic_billing_outcome,
                as_of=datetime.now(UTC),
                completed_at=lambda: datetime.now(UTC),
            )
        # A durably recorded provider failure is a completed worker, not a
        # successful report. M04 state, never this exit code, drives the UI.
        return 0
