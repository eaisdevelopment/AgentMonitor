"""Read real monetary schedule readiness without dispatching or changing it."""

import uuid
from datetime import datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.api.policy import (
    SOURCE_ID,
    completed_period,
)
from agentmonitor.composition.ollama_usage_run import (
    POLICY_VERSION,
    build_ollama_usage_run,
    usage_manifest_fingerprint,
    usage_request_for_run,
)
from agentmonitor.contracts.capacity_v1 import BudgetReportHistoryQueryV1
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def monetary_schedule_candidates(
    reference: DatabaseRefV1, now: datetime
) -> tuple[CloudBudgetCollectionRunAdmissionV1, ...]:
    """Prepare identities only; the real worker rechecks all authority and facts."""
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    candidates: list[CloudBudgetCollectionRunAdmissionV1] = []
    cursor = None
    scanned = 0
    while scanned < 1000:
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
            for range_key in ("7d", "30d"):
                period = completed_period(now, range_key)
                identity = OpaqueIdV1("comparison-readiness-" + uuid.uuid4().hex)
                candidate = build_ollama_usage_run(
                    graph=graph,
                    service=service,
                    context=CloudBudgetReportContextV1(
                        "self", range_key, period.start, period.end
                    ),
                    registry_revision=account.registry_revision,
                    scheduler_instance_id=identity,
                    run_id=identity,
                    request_id=identity,
                    requested_at=now,
                )
                request = usage_request_for_run(candidate, dispatched_at=now)
                page = reports.list_reports(
                    BudgetReportHistoryQueryV1(
                        account.account_id,
                        graph.resource_id,
                        period,
                        limit=50,
                        as_of=now,
                    )
                )
                retained = next(
                    (
                        item.report
                        for item in page.items
                        if item.report.source_id == SOURCE_ID
                        and item.report.source_category == "self_requests_and_cost"
                        and not item.report.grouping
                        and item.report.binding_id == graph.binding.binding_id
                        and item.report.binding_generation == graph.binding.generation
                        and item.report.scope_generation == request.scope_generation
                    ),
                    None,
                )
                if (
                    retained is not None
                    and retained.currency == "USD"
                    and retained.completeness == "complete"
                    and len(retained.cost_buckets) == (period.end - period.start).days
                ):
                    candidates.append(candidate)
        if len(accounts) < 100:
            return tuple(candidates)
        cursor = accounts[-1].account_id.value
    raise ValueError("native_comparison_inventory_limit")


def monetary_schedule_ready_at(
    reference: DatabaseRefV1,
    candidates: tuple[CloudBudgetCollectionRunAdmissionV1, ...],
    now: datetime,
) -> datetime | None:
    """Read the earliest actual monetary schedule and allowance; never dispatch."""
    if not candidates:
        return None
    runs = SqliteCollectionRepositoryV1(reference)
    snapshot = runs.read_budget_dispatch_snapshot(
        provider_key="ollama",
        capability_id="api.usage",
        source_id=SOURCE_ID,
        manifest_fingerprint=usage_manifest_fingerprint(),
        collection_policy_version=POLICY_VERSION,
        operation_families=tuple(
            sorted({item.operation_family for item in candidates})
        ),
        budget_scope_digests=tuple(
            sorted({item.budget_scope_digest for item in candidates})
        ),
        schedule_ids=tuple(item.schedule_id for item in candidates),
        as_of=now,
    )
    timing = {item.schedule_id: item for item in snapshot.schedules}
    ready: list[datetime] = []
    for candidate in candidates:
        schedule = timing.get(candidate.schedule_id)
        if schedule is not None and not schedule.has_active_lease:
            allowance = runs.get_budget_next_allowed_at(
                candidate.budget_scope_digest,
                candidate.budget_dimension,
                candidate.budget_unit,
                now,
            )
            ready.append(
                max(
                    now,
                    schedule.next_due_at,
                    schedule.not_before_at or now,
                    allowance or now,
                )
            )
    return min(ready, default=None)
