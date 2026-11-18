"""Passive current-source scheduling evidence from real installed records.

No worker, browser, provider request or account mutation is performed. This
proves retained automatic progress and immutable lineage, not browser closure,
retrospective eligibility order or all-provider scheduling acceptance.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
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
from agentmonitor.adapters.providers.ollama.api.manifest import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    EVIDENCE_REFERENCE,
    PROVIDER_VERSION,
)
from agentmonitor.adapters.providers.ollama.api.policy import (
    SOURCE_ID,
    completed_period,
)
from agentmonitor.composition.ollama_usage_run import (
    POLICY_VERSION,
    usage_manifest_fingerprint,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CloudMonitoringTargetV1,
    ProviderAccessTargetV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)

LIVE = Path("/home/dev/.local/share/agentmonitor")
Authority = tuple[CloudMonitoringTargetV1, ProviderAccessTargetV1]


def _require(condition: bool, code: str) -> None:
    if not condition:
        pytest.fail(code, pytrace=False)


def _inventory(reference: DatabaseRefV1) -> dict[OpaqueIdV1, Authority]:
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    selected: dict[OpaqueIdV1, Authority] = {}
    cursor = None
    for _ in range(10):
        accounts = registry.list_accounts("ollama", 100, cursor)
        for account in accounts:
            if (
                account.lifecycle != "active"
                or not account.is_effective_monitoring_enabled
            ):
                continue
            graph = cloud.read_monitoring_target(account.account_id)
            if graph is None or graph.lifecycle != "active":
                continue
            service = cloud.read_active_access_target(graph.access_target_id)
            if service is not None:
                selected[graph.resource_id] = (graph, service)
        if len(accounts) < 100:
            return selected
        cursor = accounts[-1].account_id.value
    pytest.fail("m7_scheduling_inventory_limit", pytrace=False)


def _scheduled_metadata(
    reference: DatabaseRefV1, graph: CloudMonitoringTargetV1, cutoff: datetime
) -> tuple[dict[str, Any], ...]:
    """M04-owned test read of closed run/request metadata missing from run DTOs."""
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT r.run_id,r.schedule_id,r.request_digest,r.primary_request_id,"
                "r.trigger_kind,r.manifest_fingerprint,r.collection_policy_version,"
                "q.trigger_kind AS request_trigger,q.request_auth_method,"
                "q.operation_family,q.request_fingerprint,q.linked_run_id,"
                "q.schedule_id AS request_schedule,q.requested_at AS request_time,"
                "q.expires_at AS request_deadline,b.window_start,b.window_end "
                "FROM collection_run r JOIN collection_request q "
                "ON q.request_id=r.primary_request_id "
                "JOIN collection_budget_reservation b ON b.run_id=r.run_id "
                "AND b.reservation_id=r.budget_reservation_id "
                "WHERE r.provider_key='ollama' AND r.capability_id='api.usage' "
                "AND r.source_id=? AND r.adapter_version=? "
                "AND r.manifest_fingerprint=? AND r.collection_policy_version=? "
                "AND r.account_id=? AND r.resource_id=? AND r.target_generation=? "
                "AND r.trigger_kind='scheduled' AND r.state='succeeded' "
                "AND r.completed_at<=? ORDER BY r.started_at DESC,r.run_id LIMIT 100",
                (
                    SOURCE_ID,
                    ADAPTER_VERSION,
                    usage_manifest_fingerprint(),
                    POLICY_VERSION,
                    graph.account_id.value,
                    graph.resource_id.value,
                    graph.binding.generation,
                    cutoff.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                ),
            ).mappings()
            return tuple(dict(row) for row in rows)


def test_current_ollama_scheduled_ranges_recur_with_immutable_report_lineage() -> None:
    reference = DatabaseRefV1(LIVE / "agentmonitor.db", LIVE)
    authority = _inventory(reference)
    _require(bool(authority), "m7_current_scheduled_resources_unavailable")
    cutoff = datetime.now(UTC)
    runs = SqliteCollectionRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    observed: dict[
        tuple[OpaqueIdV1, str], list[tuple[BudgetCollectionRunViewV1, dict[str, Any]]]
    ] = {(resource, period): [] for resource in authority for period in ("7d", "30d")}

    for resource, (graph, service) in authority.items():
        for metadata in _scheduled_metadata(reference, graph, cutoff):
            run = runs.get_run(OpaqueIdV1(metadata["run_id"]))
            _require(
                isinstance(run, BudgetCollectionRunViewV1), "m7_scheduled_run_missing"
            )
            assert isinstance(run, BudgetCollectionRunViewV1)
            captured = runs.get_budget_target(run.run_id)
            _require(isinstance(captured, tuple), "m7_scheduled_authority_invalid")
            assert isinstance(captured, tuple)
            old_graph, old_service, context = captured
            if (old_graph, old_service) != (graph, service):
                continue
            _require(
                context.scope == "self" and context.grouping == (),
                "m7_unapproved_automatic_context",
            )
            key = (resource, context.range_key)
            _require(key in observed, "m7_scheduled_range_unadmitted")
            if len(observed[key]) >= 2:
                continue
            _require(
                metadata["trigger_kind"] == metadata["request_trigger"] == "scheduled"
                and metadata["request_auth_method"] == "internal_scheduler"
                and metadata["operation_family"]
                == "collect.ollama.usage." + context.range_key
                and metadata["request_fingerprint"] == metadata["request_digest"]
                and metadata["linked_run_id"] == run.run_id.value
                and metadata["request_schedule"] == run.schedule_id.value
                and metadata["schedule_id"] == run.schedule_id.value
                and datetime.fromisoformat(metadata["request_time"]) == run.requested_at
                and datetime.fromisoformat(metadata["request_deadline"])
                == run.deadline_at,
                "m7_scheduled_request_lineage_mismatch",
            )
            _require(
                run.state == "succeeded"
                and run.source_id == SOURCE_ID
                and run.adapter_version == ADAPTER_VERSION
                and run.provider_version == PROVIDER_VERSION
                and run.account_id == graph.account_id
                and run.resource_id == resource
                and run.target_generation == graph.binding.generation
                and run.report_id is not None,
                "m7_scheduled_current_run_mismatch",
            )
            assert run.report_id is not None
            stored = reports.get_report(graph.account_id, run.report_id)
            status = reports.get_commit_status(run.run_id, run.capability_id)
            provenance = reports.get_report_provenance(graph.account_id, run.report_id)
            _require(
                stored is not None
                and status.state == "committed"
                and status.receipt is not None
                and provenance is not None,
                "m7_scheduled_commit_lineage_missing",
            )
            assert (
                stored is not None
                and status.receipt is not None
                and provenance is not None
            )
            report, receipt = stored.report, status.receipt
            period = BudgetPeriodV1(context.interval_start, context.interval_end)
            _require(
                period == completed_period(run.requested_at, context.range_key)
                and report.requested_period == report.covered_period == period
                and report.completeness == "complete"
                and report.source_id == SOURCE_ID
                and report.source_category == "self_requests_and_cost"
                and report.grouping == ()
                and report.subject.account_id == graph.account_id
                and report.subject.resource_id == resource
                and report.subject.provider_target.target_id == service.access_target_id
                and report.binding_id == graph.binding.binding_id
                and report.binding_generation == graph.binding.generation
                and report.scope_generation == 1
                and report.scope_id is None
                and report.scope_evidence == "unresolved"
                and receipt.run_id == run.run_id
                and receipt.report_id == run.report_id
                and receipt.target_generation == run.target_generation
                and receipt.payload_digest
                == run.payload_digest
                == budget_report_payload_digest(report)
                and receipt.stored_at == stored.stored_at,
                "m7_scheduled_report_context_mismatch",
            )
            _require(
                provenance.provider_key == "ollama"
                and provenance.capability_id == "api.usage"
                and provenance.adapter_id == ADAPTER_ID
                and provenance.adapter_version
                == provenance.parser_version
                == ADAPTER_VERSION
                and provenance.source_id == SOURCE_ID
                and provenance.operation_id == run.run_id
                and provenance.decision_reference == EVIDENCE_REFERENCE
                and run.started_at is not None
                and run.completed_at is not None
                and run.requested_at
                <= run.started_at
                <= report.collected_at
                <= stored.stored_at
                <= run.completed_at
                <= run.deadline_at,
                "m7_scheduled_provenance_or_times_mismatch",
            )
            _require(
                SqliteCollectionRepositoryV1(reference).get_run(run.run_id) == run
                and SqliteCollectionRepositoryV1(reference).get_budget_target(
                    run.run_id
                )
                == captured
                and SqliteBudgetReportRepositoryV1(reference).get_report(
                    graph.account_id, run.report_id
                )
                == stored
                and SqliteBudgetReportRepositoryV1(reference).get_commit_status(
                    run.run_id, run.capability_id
                )
                == status,
                "m7_scheduled_lineage_changed_on_reopen",
            )
            observed[key].append((run, metadata))

    _require(
        _inventory(reference) == authority, "m7_current_scheduling_inventory_changed"
    )
    covered = {
        period: sum(
            bool(values) for (_, key), values in observed.items() if key == period
        )
        for period in ("7d", "30d")
    }
    repeated = 0
    for values in observed.values():
        if len(values) < 2:
            continue
        (later, later_meta), (earlier, earlier_meta) = values
        _require(
            later.run_id != earlier.run_id
            and later.report_id != earlier.report_id
            and later.schedule_id == earlier.schedule_id
            and later_meta["primary_request_id"] != earlier_meta["primary_request_id"]
            and later.requested_at > earlier.requested_at
            and earlier.completed_at is not None
            and earlier.completed_at <= later.requested_at
            and datetime.fromisoformat(earlier_meta["window_end"])
            <= datetime.fromisoformat(later_meta["window_start"]),
            "m7_scheduled_recurrence_lineage_invalid",
        )
        repeated += 1
    print(
        "M7 CURRENT SCHEDULED COLLECTION: "
        f"resources={len(authority)} covered_7d={covered['7d']} "
        f"covered_30d={covered['30d']} recurring_contexts={repeated}; "
        "browser_closed=not_observed; all_provider_coverage=not_claimed"
    )
    for range_key in ("7d", "30d"):
        _require(
            covered[range_key] == len(authority),
            f"m7_current_scheduled_{range_key}_coverage_missing",
        )
    _require(repeated > 0, "m7_current_scheduled_natural_recurrence_missing")
