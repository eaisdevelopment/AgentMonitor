"""Compose bounded usage reads from the existing owner-configured cloud graph."""

import hashlib
from datetime import datetime, timedelta

from agentmonitor.adapters.providers.ollama.api.manifest import (
    ADAPTER_VERSION,
    PROVIDER_VERSION,
    build_ollama_usage_manifest,
)
from agentmonitor.adapters.providers.ollama.api.policy import (
    SOURCE_ID,
    OllamaUsageRequestV1,
    completed_period,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, CapacitySubjectV2
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CloudMonitoringTargetV1,
    ProviderAccessTargetV1,
    ProviderTargetRefV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)

BUDGET_POLICY_ID = "ollama-usage-report-requests-v1"
POLICY_VERSION = "1.0.0"


def _digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def usage_manifest_fingerprint() -> str:
    return _digest(
        "provider-manifest-fingerprint-v1",
        get_manifest_fingerprint_v1(build_ollama_usage_manifest()),
    )


def usage_budget_limit(policy_id: str, version: str) -> int:
    if policy_id != BUDGET_POLICY_ID or version != POLICY_VERSION:
        raise ValueError("ollama_usage_budget_policy_unknown")
    return 1


def build_ollama_usage_run(
    *,
    graph: CloudMonitoringTargetV1,
    service: ProviderAccessTargetV1,
    context: CloudBudgetReportContextV1,
    registry_revision: int,
    scheduler_instance_id: OpaqueIdV1,
    run_id: OpaqueIdV1,
    request_id: OpaqueIdV1,
    requested_at: datetime,
) -> CloudBudgetCollectionRunAdmissionV1:
    """Pure scheduled admission; live graph/rate fences are separately required."""
    period = BudgetPeriodV1(context.interval_start, context.interval_end)
    if period != completed_period(requested_at, context.range_key):
        raise ValueError("ollama_usage_interval_no_longer_dispatchable")
    target_digest = _digest(
        "ollama-usage-target-v1",
        graph.account_id.value,
        graph.resource_id.value,
        graph.profile_id.value,
        graph.access_target_id.value,
        context.scope,
        context.range_key,
        SOURCE_ID,
    )
    window_start = requested_at.replace(
        minute=(requested_at.minute // 15) * 15, second=0, microsecond=0
    )
    fingerprint = usage_manifest_fingerprint()
    return CloudBudgetCollectionRunAdmissionV1(
        cloud_target=graph,
        service_target=service,
        report_context=context,
        run_id=run_id,
        schedule_id=OpaqueIdV1("ollama-usage-" + target_digest[:40]),
        request_id=request_id,
        trigger="scheduled",
        operation_family="collect.ollama.usage." + context.range_key,
        requested_capability_ids=("api.usage",),
        capability_set_version="2.0.0",
        request_auth_method="internal_scheduler",
        request_principal_id=None,
        correlation_id=request_id,
        causation_id=None,
        target_key_digest=target_digest,
        provider_key="ollama",
        provider_target=ProviderTargetRefV1("cloud_service", graph.access_target_id),
        account_id=graph.account_id,
        profile_id=graph.profile_id,
        resource_id=graph.resource_id,
        capability_id="api.usage",
        source_id=SOURCE_ID,
        adapter_version=ADAPTER_VERSION,
        provider_version=PROVIDER_VERSION,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint=fingerprint,
        collection_policy_version=POLICY_VERSION,
        registry_revision=registry_revision,
        retry_chain_id=request_id,
        attempt_ordinal=1,
        target_generation=graph.binding.generation,
        scheduler_instance_id=scheduler_instance_id,
        lease_policy_version="1.0.0",
        budget_policy_id=BUDGET_POLICY_ID,
        budget_policy_version=POLICY_VERSION,
        budget_scope_digest=_digest("ollama-usage-budget-v1", target_digest),
        budget_dimension="request",
        budget_unit="count",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=window_start,
        budget_window_end=window_start + timedelta(minutes=15),
        payload_schema="budget.report.v1",
        idempotency_key_digest=None,
        request_digest=_digest(
            "ollama-usage-request-v1",
            target_digest,
            fingerprint,
            service.manifest_fingerprint,
            graph.binding.binding_id.value,
            str(graph.binding.generation),
            str(graph.record_version),
            str(service.record_version),
            str(registry_revision),
            context.interval_start.isoformat(),
            context.interval_end.isoformat(),
            requested_at.isoformat(),
        ),
        requested_at=requested_at,
        deadline_at=requested_at + timedelta(seconds=60),
    )


def usage_request_for_run(
    run: CloudBudgetCollectionRunAdmissionV1, *, dispatched_at: datetime
) -> OllamaUsageRequestV1:
    """Native rolling ranges cannot be replayed under yesterday's selected cutoff."""
    context = run.report_context
    period = BudgetPeriodV1(context.interval_start, context.interval_end)
    if period != completed_period(dispatched_at, context.range_key):
        raise ValueError("ollama_usage_interval_no_longer_dispatchable")
    return OllamaUsageRequestV1(
        subject=CapacitySubjectV2(
            "ollama",
            run.provider_target,
            run.cloud_target.account_id,
            run.cloud_target.resource_id,
        ),
        binding=run.cloud_target.binding,
        scope_id=None,
        scope_evidence="unresolved",
        scope_generation=1,
        range_key=context.range_key,
        period=period,
        requested_at=run.requested_at,
        scope=context.scope,
    )
