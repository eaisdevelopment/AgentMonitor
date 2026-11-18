"""Read retained A01/A02 reports through published ports, without source calls.

This is stored-data verification, not a fresh permission probe or an independent
comparison against provider originals. Only closed counts and mapping names leave
this helper. The caller owns a genuine private SQLite snapshot, never secrets.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

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
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.anthropic_api import (
    manifest as anthropic_manifest,
)
from agentmonitor.adapters.providers.claude.anthropic_api import (
    policy as anthropic_policy,
)
from agentmonitor.adapters.providers.claude.anthropic_api.usage_policy import (
    TOKEN_CATEGORIES,
)
from agentmonitor.adapters.providers.codex.openai_api import manifest as openai_manifest
from agentmonitor.adapters.providers.codex.openai_api import policy as openai_policy
from agentmonitor.adapters.providers.codex.openai_api.usage_mapping import usage_mapping
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetReportInputV1,
    BudgetUsageBucketV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetAuthorityV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import BillingAccessTargetV1
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1

Provider = Literal["anthropic", "openai"]
Selection = tuple[str, tuple[str, ...]]


@dataclass(frozen=True)
class RetainedReportEvidence:
    """Coverage axes are separate; none asserts fresh or independent source proof."""

    provider: Provider
    connections: int
    configured_targets: int
    report_scan_performed: bool
    retained_reports: int
    historical_binding_reports: int
    historical_mapping_reports: int
    incomplete_reports: int
    complete_empty_reports: int
    complete_populated_reports: int
    resources_without_complete_report: int
    failed_or_unfinished_runs: int
    missing_mappings: tuple[Selection, ...]
    missing_populated_mappings: tuple[Selection, ...]
    missing_ranges: tuple[str, ...]

    @property
    def coverage_reason(self) -> str | None:
        if not self.connections:
            return "billing_connection_absent"
        if not self.configured_targets:
            return "billing_current_access_not_configured"
        if not self.retained_reports:
            return "retained_provider_reports_absent"
        if self.resources_without_complete_report:
            return "current_resource_complete_report_absent"
        if self.missing_mappings or self.missing_ranges:
            return "retained_mapping_or_range_coverage_incomplete"
        return None


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError("m7_retained_" + code)


def _native_semantics(provider: Provider, report: BudgetReportInputV1) -> None:
    """Do not add overlapping counters, fill absent measures or infer prices."""
    usage = report.source_category.startswith("usage")
    _require(
        not report.cost_buckets if usage else not report.usage_buckets,
        "fact_family_mismatch",
    )
    if provider == "anthropic":
        _require(report.currency == (None if usage else "USD"), "currency_mismatch")
        _require(
            report.cost_basis
            == ("not_applicable" if usage else anthropic_policy.COST_BASIS),
            "cost_basis_mismatch",
        )
        _require(
            report.empty_means_zero
            == (not usage and report.completeness == "complete"),
            "empty_semantics_changed",
        )
        if report.completeness == "complete":
            _require(
                report.source_data_through is not None
                and report.source_data_through >= report.requested_period.end,
                "anthropic_watermark_missing",
            )
        units = (
            {"tokens"}
            if report.source_category == "usage_tokens"
            else set(TOKEN_CATEGORIES)
        )
        if report.source_category != "usage_tokens":
            units.update(("total_tokens", "web_search_requests", "requests"))
    else:
        _require(
            report.source_data_through is None and not report.empty_means_zero,
            "openai_watermark_or_zero_invented",
        )
        _require(
            report.cost_basis
            == ("not_applicable" if usage else openai_policy.COST_BASIS),
            "cost_basis_mismatch",
        )
        _require(not usage or report.currency is None, "usage_currency_invented")
        units = set()
        if usage:
            category = report.source_category.removeprefix("usage_")
            token_only = category.endswith("_tokens")
            mapping = usage_mapping(
                category.removesuffix("_tokens") if token_only else category
            )
            units.update(
                mapping.token_fields
                if token_only
                else mapping.required + mapping.optional
            )
    facts: tuple[BudgetCostBucketV1 | BudgetUsageBucketV1, ...] = (
        *report.cost_buckets,
        *report.usage_buckets,
    )
    for bucket in facts:
        _require(
            tuple(item.kind for item in bucket.dimensions) == report.grouping,
            "grouping_mismatch",
        )
        _require(
            report.requested_period.start
            <= bucket.period.start
            < bucket.period.end
            <= report.requested_period.end,
            "bucket_outside_requested_period",
        )
    for bucket in report.cost_buckets:
        _require(bucket.amount.currency == report.currency, "native_currency_changed")
    for bucket in report.usage_buckets:
        _require(
            bucket.quantity.unit in units and bucket.quantity.amount.scale == 0,
            "native_usage_unit_changed",
        )
        if report.grouping == ("token_category",):
            _require(
                (
                    bucket.dimensions[0].value in TOKEN_CATEGORIES
                    if provider == "anthropic"
                    else bucket.dimensions[0].value == bucket.quantity.unit
                ),
                "token_category_mismatch",
            )


def _same_binding(
    report: BudgetReportInputV1, target: BillingAccessTargetV1 | None
) -> bool:
    return target is not None and (
        report.subject.provider_key == target.connection.provider_key
        and report.subject.account_id == target.connection.account_id
        and report.subject.resource_id == target.connection.resource_id
        and report.binding_id == target.binding.binding_id
        and report.binding_generation == target.binding.generation
        and report.scope_generation == target.connection.scope_generation
        and (report.scope_id.value if report.scope_id else None)
        == target.connection.scope_id
        and report.scope_evidence == target.connection.scope_evidence
    )


def inspect_retained_reports(
    reference: DatabaseRefV1, provider: Provider
) -> RetainedReportEvidence:
    """Exhaust actual account/run pages on a closed snapshot; never dispatch."""
    if provider == "anthropic":
        provider_key = "claude"
        manifest = anthropic_manifest.build_anthropic_analytics_manifest()
        selections: set[Selection] = set(anthropic_policy.ANALYTICS_REPORT_SELECTIONS)
    elif provider == "openai":
        provider_key = "codex"
        manifest = openai_manifest.build_openai_analytics_manifest()
        selections = set(openai_policy.ANALYTICS_REPORT_SELECTIONS)
    else:
        raise ValueError("m7_retained_provider_invalid")
    sources = {
        source.source_id: source
        for declaration in manifest.declarations
        for source in declaration.sources
    }
    as_of = datetime.now(UTC)
    registry = SqliteRegistryRepositoryV1(reference)
    connections = SqliteBillingConnectionRepositoryV1(reference)
    access = SqliteBillingAccessRepositoryV1(reference)
    current: dict[tuple[OpaqueIdV1, OpaqueIdV1], BillingAccessTargetV1] = {}
    connection_count = 0
    connection_accounts: list[OpaqueIdV1] = []
    cursor = None
    seen_accounts: set[OpaqueIdV1] = set()
    while True:
        page = ListAccountsV1(registry).page(
            provider_key, as_of=as_of, limit=100, after_key=cursor
        )
        _require(
            page.availability.state == "available", "account_inventory_unavailable"
        )
        for account in page.items:
            _require(account.account_id not in seen_accounts, "account_cursor_repeated")
            seen_accounts.add(account.account_id)
            connection_status = connections.get(account.account_id)
            if connection_status is None:
                continue
            if connection_status.connections:
                connection_accounts.append(account.account_id)
            for connection in connection_status.connections:
                connection_count += 1
                target = access.resolve(
                    account.account_id, connection.resource_id, "verification"
                )
                if target is not None:
                    current[(account.account_id, connection.resource_id)] = target
        if not page.has_more:
            break
        _require(
            page.next_key is not None and page.next_key != cursor,
            "account_cursor_invalid",
        )
        cursor = page.next_key
    if not connection_count:
        return RetainedReportEvidence(
            provider=provider,
            connections=0,
            configured_targets=0,
            report_scan_performed=False,
            retained_reports=0,
            historical_binding_reports=0,
            historical_mapping_reports=0,
            incomplete_reports=0,
            complete_empty_reports=0,
            complete_populated_reports=0,
            resources_without_complete_report=0,
            failed_or_unfinished_runs=0,
            missing_mappings=tuple(sorted(selections)),
            missing_populated_mappings=tuple(sorted(selections)),
            missing_ranges=("30d", "7d"),
        )
    runs = SqliteCollectionRepositoryV1(reference)
    repository = SqliteBudgetReportRepositoryV1(reference)
    reopened = SqliteBudgetReportRepositoryV1(reference)
    covered: set[Selection] = set()
    populated: set[Selection] = set()
    ranges: set[str] = set()
    covered_resources: set[tuple[OpaqueIdV1, OpaqueIdV1]] = set()
    counts = dict(
        retained=0,
        historical=0,
        old_mapping=0,
        incomplete=0,
        empty=0,
        populated=0,
        unfinished=0,
    )
    seen_runs: set[OpaqueIdV1] = set()
    for account_id in connection_accounts:
        cursor = None
        while True:
            page_runs = runs.list_runs(provider_key, account_id, as_of, 100, cursor)
            for run in page_runs:
                _require(run.run_id not in seen_runs, "run_cursor_repeated")
                seen_runs.add(run.run_id)
                if (
                    not isinstance(run, BudgetCollectionRunViewV1)
                    or run.source_id not in sources
                ):
                    continue
                if run.report_id is None:
                    counts["unfinished"] += 1
                    continue
                _require(run.account_id is not None, "report_account_absent")
                assert run.account_id is not None
                stored = repository.get_report(run.account_id, run.report_id)
                _require(stored is not None, "committed_report_missing")
                assert stored is not None
                report = stored.report
                status = repository.get_commit_status(run.run_id, run.capability_id)
                _require(
                    status.state == "committed" and status.receipt is not None,
                    "receipt_missing",
                )
                assert status.receipt is not None
                receipt = status.receipt
                provenance = repository.get_report_provenance(
                    run.account_id, run.report_id
                )
                _require(provenance is not None, "provenance_missing")
                assert provenance is not None
                _require(
                    receipt.report_id == stored.report_id
                    and receipt.run_id == run.run_id
                    and receipt.stored_at == stored.stored_at
                    and receipt.payload_digest
                    == budget_report_payload_digest(report)
                    == run.payload_digest
                    and set(receipt.fact_ids) == set(run.observation_ids)
                    and len(receipt.fact_ids) == len(run.observation_ids)
                    and len(set(receipt.fact_ids)) == len(receipt.fact_ids)
                    and len(receipt.fact_ids)
                    == len(report.cost_buckets) + len(report.usage_buckets),
                    "receipt_report_lineage_mismatch",
                )
                _require(
                    provenance.operation_id == run.run_id
                    and provenance.source_id == report.source_id == run.source_id
                    and provenance.provider_key
                    == report.subject.provider_key
                    == provider_key
                    and report.subject.account_id == run.account_id
                    and provenance.collected_at == report.collected_at
                    and provenance.capability_id == run.capability_id,
                    "provenance_lineage_mismatch",
                )
                _require(
                    reopened.get_report(run.account_id, run.report_id) == stored
                    and reopened.get_commit_status(run.run_id, run.capability_id)
                    == status
                    and reopened.get_report_provenance(run.account_id, run.report_id)
                    == provenance,
                    "reopened_exact_report_changed",
                )
                authority = runs.get_budget_target(run.run_id)
                captured = (
                    authority.target
                    if isinstance(authority, BillingBudgetAuthorityV1)
                    else authority
                )
                _require(
                    isinstance(captured, BillingAccessTargetV1),
                    "billing_authority_missing",
                )
                assert isinstance(captured, BillingAccessTargetV1)
                _require(_same_binding(report, captured), "captured_authority_mismatch")
                counts["retained"] += 1
                identity = (report.subject.account_id, report.subject.resource_id)
                current_binding = _same_binding(report, current.get(identity))
                if not current_binding:
                    counts["historical"] += 1
                source = sources[run.source_id]
                reviewed = (
                    provenance.adapter_id == manifest.descriptor.adapter_id
                    and provenance.adapter_version
                    == manifest.descriptor.adapter_version
                    and provenance.parser_version == manifest.descriptor.adapter_version
                    and provenance.decision_reference == source.evidence_reference
                    and provenance.mechanism_version == source.mechanism_version
                )
                if not reviewed or not isinstance(authority, BillingBudgetAuthorityV1):
                    counts["old_mapping"] += 1
                    continue
                context = authority.report_context
                selection = (report.source_category, tuple(report.grouping))
                _require(
                    selection in selections
                    and selection == (context.source_category, context.grouping),
                    "report_selection_mismatch",
                )
                _require(
                    report.requested_period.start == context.interval_start
                    and report.requested_period.end == context.interval_end
                    and report.requested_period.end <= run.requested_at,
                    "captured_period_mismatch",
                )
                _require(
                    provenance.source_class == "documented_api"
                    and provenance.precision == "exact"
                    and provenance.value_kind == "provider_reported"
                    and provenance.observed_at == report.source_data_through,
                    "source_semantics_changed",
                )
                _require(
                    source.capability_id == run.capability_id
                    and (source.capability_id == "api.usage")
                    == report.source_category.startswith("usage"),
                    "source_capability_mismatch",
                )
                _native_semantics(provider, report)
                complete = (
                    report.completeness == "complete"
                    and report.covered_period == report.requested_period
                )
                if not complete:
                    counts["incomplete"] += 1
                elif current_binding:
                    covered.add(selection)
                    ranges.add(context.range_key)
                    covered_resources.add(identity)
                    if report.cost_buckets or report.usage_buckets:
                        populated.add(selection)
                        counts["populated"] += 1
                    else:
                        counts["empty"] += 1
            if len(page_runs) < 100:
                break
            cursor = page_runs[-1].run_id.value
    return RetainedReportEvidence(
        provider,
        connection_count,
        len(current),
        True,
        counts["retained"],
        counts["historical"],
        counts["old_mapping"],
        counts["incomplete"],
        counts["empty"],
        counts["populated"],
        len(set(current) - covered_resources),
        counts["unfinished"],
        tuple(sorted(selections - covered)),
        tuple(sorted(selections - populated)),
        tuple(sorted({"7d", "30d"} - ranges)),
    )
