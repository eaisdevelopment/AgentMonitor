"""Read configured financial inventory and retained coverage through public ports.

This is neither a provider request nor an independent provider comparison.
Only typed counts/reasons are returned; account labels and identifiers stay local.
"""

from dataclasses import dataclass
from datetime import datetime

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
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.anthropic_api.manifest import (
    build_anthropic_analytics_manifest,
)
from agentmonitor.adapters.providers.codex.openai_api.manifest import (
    build_openai_analytics_manifest,
)
from agentmonitor.adapters.providers.ollama.api.manifest import (
    build_ollama_usage_manifest,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
)
from agentmonitor.composition.billing_run import anthropic_cost_manifest_fingerprint
from agentmonitor.composition.openai_billing_run import (
    OPENAI_COST_AUTHORITY_ID_V1,
    openai_cost_manifest_fingerprint,
)
from agentmonitor.contracts.capacity_v1 import BudgetReportInputV1
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetAuthorityV1,
    BillingBudgetReportContextV1,
    BudgetCollectionRunViewV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import CapabilityManifestV1
from agentmonitor.contracts.registry_billing_v1 import (
    AccountBillingConnectionsV1,
    BillingAccessTargetV1,
)
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1,
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
    ProviderAccessTargetV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)


@dataclass(frozen=True)
class ProviderInventoryCounts:
    provider: str
    accounts: int
    accounts_without_resource: int
    pending_accounts_without_resource: int
    resources: int
    pending: int
    disabled: int
    disconnected: int
    unavailable: int
    monitored: int
    retained_complete: int
    missing_retained_complete: int


@dataclass(frozen=True)
class ConfiguredInventoryEvidence:
    providers: tuple[ProviderInventoryCounts, ...]
    missing_provider_lanes: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class _Resource:
    account: AccountViewV1
    resource_id: OpaqueIdV1
    disposition: str
    target: BillingAccessTargetV1 | CloudMonitoringTargetV1 | None
    service: ProviderAccessTargetV1 | None
    binding: ActiveCredentialBindingRefV1 | None
    billing_status: AccountBillingConnectionsV1 | None = None


def _require(value: bool, code: str) -> None:
    if not value:
        raise ValueError("m7_inventory_" + code)


def _manifest(provider: str) -> CapabilityManifestV1:
    if provider == "claude":
        return build_anthropic_analytics_manifest()
    if provider == "codex":
        return build_openai_analytics_manifest()
    return build_ollama_usage_manifest()


def _inventory(
    reference: DatabaseRefV1, as_of: datetime
) -> tuple[tuple[AccountViewV1, ...], tuple[_Resource, ...]]:
    registry = SqliteRegistryRepositoryV1(reference)
    billing = SqliteBillingConnectionRepositoryV1(reference)
    access = SqliteBillingAccessRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    bindings = SqliteCredentialBindingsV1(reference)
    accounts: list[AccountViewV1] = []
    resources: list[_Resource] = []
    cursor = None
    seen: set[OpaqueIdV1] = set()
    while True:
        page = ListAccountsV1(registry).page(
            None, as_of=as_of, limit=100, after_key=cursor
        )
        _require(page.availability.state == "available", "account_read_unavailable")
        for account in page.items:
            _require(account.account_id not in seen, "account_cursor_repeated")
            seen.add(account.account_id)
            if account.provider_key not in {"claude", "codex", "ollama"}:
                continue
            accounts.append(account)
            if account.provider_key == "ollama":
                graph = cloud.read_monitoring_target(account.account_id)
                if graph is None:
                    continue
                binding = (
                    resolve_active_credential_binding(bindings.read(account.account_id))
                    if account.lifecycle in {"pending", "active"}
                    else None
                )
                service = cloud.read_active_access_target(graph.access_target_id)
                disabled = (
                    account.lifecycle != "active"
                    or graph.lifecycle != "active"
                    or not account.is_effective_monitoring_enabled
                )
                available = (
                    binding == graph.binding
                    and service is not None
                    and service.provider_key == "ollama"
                    and service.authority_id == "ollama.com"
                    and service.manifest_fingerprint == ollama_cloud_probe_fingerprint()
                )
                disposition = (
                    "disabled"
                    if disabled
                    else "monitored"
                    if available
                    else "unavailable"
                )
                resources.append(
                    _Resource(
                        account, graph.resource_id, disposition, graph, service, binding
                    )
                )
                continue
            status = billing.get(account.account_id)
            _require(status is not None, "billing_status_unavailable")
            assert status is not None
            authority = (
                "anthropic.analytics"
                if account.provider_key == "claude"
                else OPENAI_COST_AUTHORITY_ID_V1
            )
            service = cloud.read_access_target_for_authority(
                account.provider_key, authority
            )
            expected_manifest = (
                anthropic_cost_manifest_fingerprint()
                if account.provider_key == "claude"
                else openai_cost_manifest_fingerprint()
            )
            for connection in status.connections:
                target = access.resolve(
                    account.account_id, connection.resource_id, "monitoring"
                )
                binding = target.binding if target is not None else None
                disposition = (
                    "disconnected"
                    if connection.lifecycle == "disconnected"
                    else "pending"
                    if connection.lifecycle == "pending"
                    else "disabled"
                    if account.lifecycle in {"disabled", "archived"}
                    or connection.monitoring_preference != "enabled"
                    else "unavailable"
                    if target is None
                    or service is None
                    or service.manifest_fingerprint != expected_manifest
                    else "monitored"
                )
                resources.append(
                    _Resource(
                        account,
                        connection.resource_id,
                        disposition,
                        target,
                        service,
                        binding,
                        status,
                    )
                )
        if not page.has_more:
            break
        _require(
            page.next_key is not None and page.next_key != cursor,
            "account_cursor_invalid",
        )
        cursor = page.next_key
    _require(
        len({item.resource_id for item in resources}) == len(resources),
        "resource_duplicated",
    )
    return tuple(accounts), tuple(resources)


def _current_report(report: BudgetReportInputV1, resource: _Resource) -> bool:
    target = resource.target
    if target is None or resource.binding is None or resource.service is None:
        return False
    if not (
        report.subject.provider_key == resource.account.provider_key
        and report.subject.account_id == resource.account.account_id
        and report.subject.resource_id == resource.resource_id
        and report.subject.provider_target.target_id
        == resource.service.access_target_id
        and report.binding_id == resource.binding.binding_id
        and report.binding_generation == resource.binding.generation
    ):
        return False
    if isinstance(target, BillingAccessTargetV1):
        connection = target.connection
        return (
            report.scope_generation == connection.scope_generation
            and (report.scope_id.value if report.scope_id else None)
            == connection.scope_id
            and report.scope_evidence == connection.scope_evidence
        )
    return (
        report.scope_generation == 1
        and report.scope_id is None
        and report.scope_evidence == "unresolved"
    )


def _has_retained_coverage(
    reference: DatabaseRefV1, resource: _Resource, as_of: datetime
) -> bool:
    runs = SqliteCollectionRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    manifest = _manifest(resource.account.provider_key)
    sources = {
        source.source_id: source
        for declaration in manifest.declarations
        for source in declaration.sources
    }
    cursor = None
    seen: set[OpaqueIdV1] = set()
    while True:
        page = runs.list_runs(
            resource.account.provider_key,
            resource.account.account_id,
            as_of,
            100,
            cursor,
        )
        for run in page:
            _require(run.run_id not in seen, "run_cursor_repeated")
            seen.add(run.run_id)
            if not (
                isinstance(run, BudgetCollectionRunViewV1)
                and run.resource_id == resource.resource_id
                and run.state == "succeeded"
                and run.report_id is not None
                and run.source_id in sources
                and run.adapter_version == manifest.descriptor.adapter_version
                and run.completed_at is not None
                and run.completed_at <= as_of
            ):
                continue
            assert (
                isinstance(run, BudgetCollectionRunViewV1) and run.report_id is not None
            )
            stored = reports.get_report(resource.account.account_id, run.report_id)
            _require(stored is not None, "report_missing")
            assert stored is not None
            report = stored.report
            if not _current_report(report, resource):
                continue
            if (
                report.completeness != "complete"
                or report.covered_period != report.requested_period
            ):
                continue
            captured = runs.get_budget_target(run.run_id)
            context: BillingBudgetReportContextV1 | CloudBudgetReportContextV1
            if isinstance(captured, BillingBudgetAuthorityV1):
                if not isinstance(resource.target, BillingAccessTargetV1):
                    continue
                _require(
                    captured.target.binding == resource.binding,
                    "captured_binding_mismatch",
                )
                connection = captured.target.connection
                _require(
                    connection.account_id == report.subject.account_id
                    and connection.resource_id == report.subject.resource_id
                    and connection.provider_key == report.subject.provider_key
                    and connection.scope_generation == report.scope_generation
                    and connection.scope_id
                    == (report.scope_id.value if report.scope_id else None)
                    and connection.scope_evidence == report.scope_evidence,
                    "captured_scope_mismatch",
                )
                context = captured.report_context
                category = context.source_category
            elif isinstance(captured, tuple):
                graph, service, context = captured
                if graph != resource.target or service != resource.service:
                    continue
                category = context.scope + "_requests_and_cost"
            else:
                continue
            _require(
                report.source_id == run.source_id
                and report.source_category == category
                and report.grouping == context.grouping
                and report.requested_period.start == context.interval_start
                and report.requested_period.end == context.interval_end
                and context.interval_end <= run.requested_at
                and run.target_generation == report.binding_generation,
                "captured_context_mismatch",
            )
            provenance = reports.get_report_provenance(
                resource.account.account_id, run.report_id
            )
            source = sources[run.source_id]
            _require(
                provenance is not None
                and provenance.source_id == run.source_id
                and provenance.operation_id == run.run_id
                and provenance.capability_id
                == source.capability_id
                == run.capability_id
                and provenance.adapter_id == manifest.descriptor.adapter_id
                and provenance.adapter_version
                == provenance.parser_version
                == manifest.descriptor.adapter_version
                and provenance.mechanism_version == source.mechanism_version
                and run.provider_version == source.mechanism_version
                and provenance.decision_reference == source.evidence_reference,
                "current_source_provenance_mismatch",
            )
            status = reports.get_commit_status(run.run_id, run.capability_id)
            _require(
                status.state == "committed" and status.receipt is not None,
                "commit_receipt_missing",
            )
            assert status.receipt is not None
            receipt = status.receipt
            checks = (
                (
                    "identity",
                    receipt.run_id == run.run_id
                    and receipt.report_id == run.report_id
                    and receipt.target_generation == run.target_generation,
                ),
                (
                    "digest",
                    receipt.payload_digest
                    == run.payload_digest
                    == budget_report_payload_digest(report),
                ),
                (
                    "fact_ids",
                    set(receipt.fact_ids) == set(run.observation_ids)
                    and len(receipt.fact_ids) == len(run.observation_ids)
                    and len(set(receipt.fact_ids)) == len(receipt.fact_ids),
                ),
                (
                    "fact_count",
                    len(receipt.fact_ids)
                    == len(report.cost_buckets) + len(report.usage_buckets),
                ),
                ("stored_at", receipt.stored_at == stored.stored_at),
                ("completion_time", stored.stored_at <= run.completed_at),
            )
            for field, matches in checks:
                _require(matches, "receipt_" + field + "_mismatch")
            return True
        if len(page) < 100:
            return False
        cursor = page[-1].run_id.value


def inspect_configured_inventory(
    reference: DatabaseRefV1, as_of: datetime
) -> ConfiguredInventoryEvidence:
    accounts, resources = _inventory(reference, as_of)
    covered = {
        resource.resource_id
        for resource in resources
        if resource.disposition == "monitored"
        and _has_retained_coverage(reference, resource, as_of)
    }
    _require(
        _inventory(reference, as_of) == (accounts, resources),
        "metadata_changed_during_read",
    )
    counts = []
    reasons = []
    missing = []
    for provider in ("claude", "codex", "ollama"):
        selected = tuple(
            item for item in resources if item.account.provider_key == provider
        )
        without = tuple(
            account
            for account in accounts
            if account.provider_key == provider
            and not any(
                item.account.account_id == account.account_id for item in selected
            )
        )
        states = {
            state: sum(item.disposition == state for item in selected)
            for state in (
                "pending",
                "disabled",
                "disconnected",
                "unavailable",
                "monitored",
            )
        }
        complete = sum(item.resource_id in covered for item in selected)
        if complete == 0:
            missing.append(provider)
        if states["unavailable"]:
            reasons.append(provider + "_monitored_authority_unavailable")
        if states["monitored"] != complete:
            reasons.append(provider + "_monitored_resource_report_missing")
        counts.append(
            ProviderInventoryCounts(
                provider,
                sum(account.provider_key == provider for account in accounts),
                len(without),
                sum(account.lifecycle == "pending" for account in without),
                len(selected),
                states["pending"],
                states["disabled"],
                states["disconnected"],
                states["unavailable"],
                states["monitored"],
                complete,
                states["monitored"] - complete,
            )
        )
    return ConfiguredInventoryEvidence(tuple(counts), tuple(missing), tuple(reasons))
