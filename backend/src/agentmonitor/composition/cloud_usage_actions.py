"""Durable owner-selected cloud usage; admission performs no provider I/O."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

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
    SqliteCredentialBindingsV1,
    ensure_cloud_verification_enqueue_authority_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.api.policy import completed_period
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
)
from agentmonitor.composition.ollama_usage_fence import cloud_usage_fence
from agentmonitor.composition.ollama_usage_run import build_ollama_usage_run
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.cloud_usage_actions_v1 import (
    CloudUsageCollectCommandV1,
    CloudUsageEligibilityV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionRunViewV1,
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CloudMonitoringTargetV1,
    ProviderAccessTargetV1,
)
from agentmonitor.modules.registry.application.cloud_connection import (
    resolve_active_credential_binding,
)
from sqlalchemy.engine import Connection


@dataclass(frozen=True, slots=True)
class CloudUsageIdentifiersV1:
    run_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    request_id: OpaqueIdV1
    scheduler_instance_id: OpaqueIdV1
    idempotency_key_digest: str


def _digest(*values: str) -> str:
    return hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()


def cloud_usage_identifiers(
    command: CloudUsageCollectCommandV1,
) -> CloudUsageIdentifiersV1:
    owner = (command.principal_id.value, command.command_id.value)
    context = command.report_context
    target = (
        command.account_id.value,
        command.resource_id.value,
        str(command.expected_account_version),
        str(command.expected_target_version),
        context.scope,
        context.range_key,
        context.interval_start.isoformat(),
        context.interval_end.isoformat(),
    )
    return CloudUsageIdentifiersV1(
        OpaqueIdV1("usage-manual-run-" + _digest(*owner)[:40]),
        OpaqueIdV1("usage-manual-schedule-" + _digest(*target)[:40]),
        OpaqueIdV1("usage-manual-request-" + _digest(*owner)[:40]),
        OpaqueIdV1("usage-manual-producer-" + _digest(*owner)[:40]),
        _digest("cloud-usage-command-v1", *owner, *target),
    )


def build_manual_usage_run(
    command: CloudUsageCollectCommandV1,
    *,
    graph: CloudMonitoringTargetV1,
    service: ProviderAccessTargetV1,
    registry_revision: int,
) -> CloudBudgetCollectionRunAdmissionV1:
    """Reuse the scheduled source budget; manual intent does not alter monitoring."""

    if (
        command.account_id != graph.account_id
        or command.resource_id != graph.resource_id
        or command.expected_target_version != graph.record_version
    ):
        raise ValueError("cloud_usage_target_changed")
    identifiers = cloud_usage_identifiers(command)
    run = build_ollama_usage_run(
        graph=graph,
        service=service,
        context=command.report_context,
        registry_revision=registry_revision,
        scheduler_instance_id=identifiers.scheduler_instance_id,
        run_id=identifiers.run_id,
        request_id=identifiers.request_id,
        requested_at=command.requested_at,
    )
    return replace(
        run,
        trigger="manual",
        deadline_at=command.requested_at + timedelta(seconds=120),
        request_auth_method="browser_cookie",
        request_principal_id=command.principal_id,
        schedule_id=identifiers.schedule_id,
        target_key_digest=_digest(
            "cloud-usage-manual-target-v1", identifiers.schedule_id.value
        ),
        idempotency_key_digest=identifiers.idempotency_key_digest,
        request_digest=_digest(
            identifiers.idempotency_key_digest,
            graph.binding.binding_id.value,
            str(graph.binding.generation),
            service.manifest_fingerprint,
            str(service.record_version),
            run.manifest_fingerprint,
        ),
    )


class CloudUsageActionsV1:
    """Read current authority, then durably enqueue; credentials stay in worker."""

    def __init__(
        self,
        reference: DatabaseRefV1,
        *,
        can_dispatch: Callable[[], bool] | None = None,
        on_queued: Callable[[], None] | None = None,
    ) -> None:

        self._reference = reference
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._cloud = SqliteCloudCredentialRegistryV1(reference)
        self._bindings = SqliteCredentialBindingsV1(reference)
        self._runs = SqliteCollectionRepositoryV1(
            reference, cloud_admission_fence=cloud_usage_fence
        )
        self._gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
        self._ready = can_dispatch
        self._wake = on_queued

    def get_status(
        self, account_id: OpaqueIdV1, resource_id: OpaqueIdV1, run_id: OpaqueIdV1
    ) -> tuple[BudgetCollectionRunViewV1, CloudBudgetReportContextV1] | None:

        try:
            run = self._runs.get_run(run_id)
        except CollectionRepositoryErrorV1 as error:
            if error.code == "collection_run_not_found":
                return None
            raise ValueError("cloud_usage_unavailable") from None
        if (
            not isinstance(run, BudgetCollectionRunViewV1)
            or run.provider_key != "ollama"
            or run.capability_id != "api.usage"
            or run.account_id != account_id
            or run.resource_id != resource_id
        ):
            return None
        target = self._runs.get_budget_target(run_id)
        if not isinstance(target, tuple) or len(target) != 3:
            raise ValueError("cloud_usage_unavailable")
        graph, _, context = target
        if graph.account_id != account_id or graph.resource_id != resource_id:
            raise ValueError("cloud_usage_unavailable")
        return run, context

    def eligibility(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        context: CloudBudgetReportContextV1,
        as_of: datetime,
    ) -> CloudUsageEligibilityV1 | None:

        account = self._registry.get_account(account_id)
        graph = self._cloud.read_monitoring_target(account_id)
        if (
            account is None
            or account.provider_key != "ollama"
            or graph is None
            or graph.resource_id != resource_id
        ):
            return None
        reason, next_allowed = "cloud_usage_ready", None
        service = self._cloud.read_active_access_target(graph.access_target_id)
        binding = resolve_active_credential_binding(self._bindings.read(account_id))
        if account.lifecycle != "active" or graph.lifecycle != "active":
            reason = "cloud_usage_target_unavailable"
        elif not account.is_effective_monitoring_enabled:
            reason = "cloud_usage_monitoring_disabled"
        elif binding != graph.binding:
            reason = "cloud_usage_credential_required"
        elif (
            service is None
            or service.lifecycle != "active"
            or service.authority_id != "ollama.com"
            or service.manifest_fingerprint != ollama_cloud_probe_fingerprint()
        ):
            reason = "cloud_usage_authority_unavailable"
        elif BudgetPeriodV1(
            context.interval_start, context.interval_end
        ) != completed_period(as_of, context.range_key):
            reason = "cloud_usage_interval_unavailable"
        else:
            state, next_allowed = self._gate.read_usage_gate_status(as_of)
            if state != "ready":
                reason = (
                    "cloud_usage_request_unresolved"
                    if state == "unresolved"
                    else "cloud_usage_rate_limited"
                )
            else:
                sample = build_ollama_usage_run(
                    graph=graph,
                    service=service,
                    context=context,
                    registry_revision=account.registry_revision,
                    scheduler_instance_id=OpaqueIdV1("usage-eligibility"),
                    run_id=OpaqueIdV1("usage-eligibility"),
                    request_id=OpaqueIdV1("usage-eligibility"),
                    requested_at=as_of,
                )
                next_allowed = self._runs.get_budget_next_allowed_at(
                    sample.budget_scope_digest, "request", "count", as_of
                )
                if next_allowed is not None:
                    reason = "cloud_usage_rate_limited"
                else:
                    try:
                        ready = self._ready is not None and self._ready() is True
                    except Exception:
                        ready = False
                    if not ready:
                        reason = "cloud_usage_service_unavailable"
        if (
            self._registry.get_account(account_id) != account
            or self._cloud.read_monitoring_target(account_id) != graph
        ):
            raise ValueError("cloud_usage_target_changed")
        return CloudUsageEligibilityV1(
            account_id,
            resource_id,
            account.record_version,
            graph.record_version,
            None if binding is None else binding.generation,
            context,
            reason == "cloud_usage_ready",
            reason,
            next_allowed,
            as_of,
        )

    def collect(self, command: CloudUsageCollectCommandV1) -> BudgetCollectionRunViewV1:

        ids = cloud_usage_identifiers(command)
        previous = self.get_status(command.account_id, command.resource_id, ids.run_id)
        if previous is not None:
            run, context = previous
            if run.schedule_id != ids.schedule_id or context != command.report_context:
                raise ValueError("cloud_usage_idempotency_conflict")
            self._notify(run)
            return run
        # An existing differently scoped run with this owner's key is a conflict.
        try:
            self._runs.get_run(ids.run_id)
        except CollectionRepositoryErrorV1 as error:
            if error.code != "collection_run_not_found":
                raise ValueError("cloud_usage_unavailable") from None
        else:
            raise ValueError("cloud_usage_idempotency_conflict")
        eligibility = self.eligibility(
            command.account_id,
            command.resource_id,
            command.report_context,
            command.requested_at,
        )
        if eligibility is None:
            raise ValueError("cloud_usage_target_unavailable")
        if (
            eligibility.account_record_version != command.expected_account_version
            or eligibility.target_record_version != command.expected_target_version
        ):
            raise ValueError("cloud_usage_version_conflict")
        if not eligibility.can_collect:
            raise ValueError(eligibility.reason_code)
        graph = self._cloud.read_monitoring_target(command.account_id)
        account = self._registry.get_account(command.account_id)
        service = (
            None
            if graph is None
            else self._cloud.read_active_access_target(graph.access_target_id)
        )
        if graph is None or account is None or service is None:
            raise ValueError("cloud_usage_target_changed")
        admission = build_manual_usage_run(
            command,
            graph=graph,
            service=service,
            registry_revision=account.registry_revision,
        )

        def fence(
            connection: Connection,
            captured_graph: CloudMonitoringTargetV1,
            captured_service: ProviderAccessTargetV1,
            context: CloudBudgetReportContextV1,
        ) -> None:
            cloud_usage_fence(connection, captured_graph, captured_service, context)
            ensure_cloud_verification_enqueue_authority_in_transaction(
                connection,
                account_id=command.account_id,
                expected_account_record_version=command.expected_account_version,
                profile_id=captured_graph.profile_id,
                resource_id=captured_graph.resource_id,
                access_target_id=captured_graph.access_target_id,
                binding=captured_graph.binding,
                expected_manifest_fingerprint=captured_service.manifest_fingerprint,
            )

        try:
            admitted = SqliteCollectionRepositoryV1(
                self._reference, cloud_admission_fence=fence
            ).admit_run(admission)
        except CollectionRepositoryErrorV1 as error:
            reason = (
                "cloud_usage_idempotency_conflict"
                if error.code == "collection_idempotency_conflict"
                else "cloud_usage_rate_limited"
                if error.code
                in {"collection_budget_exhausted", "collection_retry_deferred"}
                else "cloud_usage_unavailable"
            )
            raise ValueError(reason) from None
        except ValueError:
            raise ValueError("cloud_usage_target_changed") from None
        if not isinstance(admitted, BudgetCollectionRunViewV1):
            raise ValueError("cloud_usage_unavailable")
        self._notify(admitted)
        return admitted

    def _notify(self, run: BudgetCollectionRunViewV1) -> None:
        if run.state == "queued" and self._wake is not None:
            try:
                self._wake()
            except Exception:
                pass
