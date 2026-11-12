"""Compose genuine run/receipt/report proof for independent billing monitoring."""

from collections.abc import Callable
from datetime import UTC, datetime

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
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionCommitStatusV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    BillingAccessTargetV1,
    BillingConnectionViewV1,
    BillingMonitoringProofV1,
    BillingMonitoringStatusV1,
    SetBillingMonitoringCommandV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)


def monitoring_proof(
    current: BillingAccessTargetV1,
    captured: BillingAccessTargetV1,
    run: BudgetCollectionRunViewV1,
    commit: BudgetCollectionCommitStatusV1,
    stored: BudgetReportViewV1,
    as_of: datetime,
) -> BillingMonitoringProofV1:
    """Pure lineage check; no constructed proof is persisted by this function.

    Connection preference/version may change after verification. Provider scope
    and credential identity/generation may not. M02 rechecks the full current
    target under its mutation lock, closing the read-to-enable rotation race.
    """
    connection = current.connection
    previous = captured.connection
    report = stored.report
    receipt = commit.receipt
    if (
        current.purpose != "verification"
        or current.binding != captured.binding
        or (
            connection.account_id,
            connection.resource_id,
            connection.provider_key,
            connection.scope_id,
            connection.scope_evidence,
            connection.scope_generation,
        )
        != (
            previous.account_id,
            previous.resource_id,
            previous.provider_key,
            previous.scope_id,
            previous.scope_evidence,
            previous.scope_generation,
        )
        or run.state != "succeeded"
        or run.completed_at is None
        or run.completed_at > as_of
        or run.account_id != connection.account_id
        or run.resource_id != connection.resource_id
        or run.provider_key != connection.provider_key
        or run.report_id != stored.report_id
        or report.subject.account_id != connection.account_id
        or report.subject.resource_id != connection.resource_id
        or report.subject.provider_key != connection.provider_key
        or report.binding_id != current.binding.binding_id
        or report.binding_generation != current.binding.generation
        or report.scope_generation != connection.scope_generation
        or (None if report.scope_id is None else report.scope_id.value)
        != connection.scope_id
        or report.scope_evidence != connection.scope_evidence
        or report.source_id != run.source_id
        or report.completeness != "complete"
        or report.covered_period != report.requested_period
        or report.collected_at < run.requested_at
        or stored.stored_at > run.completed_at
        or commit.state != "committed"
        or receipt is None
        or receipt.run_id != run.run_id
        or receipt.report_id != stored.report_id
        or receipt.target_generation != run.target_generation
        or receipt.capability_id != run.capability_id
        or receipt.payload_schema != "budget.report.v1"
        or receipt.stored_at != stored.stored_at
        or receipt.payload_digest != run.payload_digest
        or receipt.payload_digest != budget_report_payload_digest(report)
    ):
        raise ValueError("billing_monitoring_verification_required")
    return BillingMonitoringProofV1(
        current_target=current,
        run_id=run.run_id,
        report_id=stored.report_id,
        payload_digest=receipt.payload_digest,
        verified_at=run.completed_at,
    )


class BillingMonitoringActionsV1:
    """Current eligibility and mutation; only normal collection contacts providers."""

    def __init__(
        self,
        reference: DatabaseRefV1,
        *,
        can_dispatch: Callable[[], bool] | None = None,
        on_enabled: Callable[[], None] | None = None,
    ) -> None:
        self._connections = SqliteBillingConnectionRepositoryV1(reference)
        self._access = SqliteBillingAccessRepositoryV1(reference)
        self._runs = SqliteCollectionRepositoryV1(reference)
        self._reports = SqliteBudgetReportRepositoryV1(reference)
        self._can_dispatch = can_dispatch
        self._on_enabled = on_enabled

    def _proof(
        self, target: BillingAccessTargetV1, instant: datetime
    ) -> BillingMonitoringProofV1:
        selected = target.connection
        run = self._runs.get_latest_budget_run(
            selected.account_id,
            selected.resource_id,
            selected.scope_generation,
            instant,
        )
        if run is None or run.state != "succeeded" or run.report_id is None:
            raise ValueError("billing_monitoring_verification_required")
        captured = self._runs.get_billing_target(run.run_id)
        committed = self._reports.get_commit_status(run.run_id, run.capability_id)
        report = self._reports.get_report(selected.account_id, run.report_id)
        if report is None:
            raise ValueError("billing_monitoring_verification_required")
        return monitoring_proof(target, captured, run, committed, report, instant)

    def _runtime_ready(self, provider_key: str) -> bool:
        # The supervised worker explicitly admits Anthropic and OpenAI costs.
        if provider_key not in {"claude", "codex"} or self._can_dispatch is None:
            return False
        try:
            return self._can_dispatch() is True
        except Exception:
            return False

    def get_status(
        self, account_id: OpaqueIdV1, resource_id: OpaqueIdV1
    ) -> BillingMonitoringStatusV1 | None:
        metadata = self._connections.get(account_id)
        if metadata is None or not metadata.connections:
            return None
        connection = metadata.connections[0]
        if connection.resource_id != resource_id:
            return None
        credential = metadata.credential_status
        generation = None if credential is None else credential.active_generation
        proof = None
        reason = "billing_monitoring_verification_required"
        if (
            metadata.account_lifecycle not in {"pending", "active"}
            or connection.lifecycle == "disconnected"
        ):
            reason = "billing_monitoring_account_unavailable"
        elif generation is None:
            reason = "billing_monitoring_credential_required"
        else:
            target = self._access.resolve(account_id, resource_id, "verification")
            if target is not None:
                if target.connection != connection:
                    raise ValueError("billing_monitoring_target_changed")
                try:
                    proof = self._proof(target, datetime.now(UTC))
                except ValueError as error:
                    if str(error) != "billing_monitoring_verification_required":
                        reason = "billing_monitoring_unavailable"
                if proof is not None:
                    reason = (
                        "billing_monitoring_verified"
                        if self._runtime_ready(connection.provider_key)
                        else "billing_monitoring_runtime_unavailable"
                    )
        if self._connections.get(account_id) != metadata:
            raise ValueError("billing_monitoring_target_changed")
        enabled = connection.monitoring_preference == "enabled"
        return BillingMonitoringStatusV1(
            connection=connection,
            account_record_version=metadata.account_record_version,
            binding_generation=generation,
            can_enable=not enabled and reason == "billing_monitoring_verified",
            can_disable=enabled,
            reason_code=reason,
            verified_run_id=None if proof is None else proof.run_id,
            verified_at=None if proof is None else proof.verified_at,
        )

    def set_monitoring(
        self, command: SetBillingMonitoringCommandV1
    ) -> BillingConnectionViewV1:
        replay = self._connections.replay_monitoring(command)
        if replay is not None:
            return replay
        proof = None
        if command.monitoring_preference == "enabled":
            target = self._access.resolve(
                command.account_id, command.resource_id, "verification"
            )
            if target is None:
                raise ValueError("billing_monitoring_verification_required")
            if not self._runtime_ready(target.connection.provider_key):
                raise ValueError("billing_monitoring_runtime_unavailable")
            proof = self._proof(target, command.requested_at)
            if proof.run_id != command.verified_run_id:
                raise ValueError("billing_monitoring_target_changed")
        result = self._connections.set_monitoring(command, proof)
        if result.monitoring_preference == "enabled" and self._on_enabled is not None:
            try:
                self._on_enabled()
            except Exception:
                # Persisted preference is authoritative; scheduling recovers.
                pass
        return result
