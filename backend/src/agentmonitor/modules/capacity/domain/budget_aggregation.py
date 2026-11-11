"""Exact selected-period spend with explicit pool identity and coverage.

The caller supplies the complete filtered inventory and canonical pool/epoch
mapping established from provider scope or explicit owner association. Labels,
equal amounts and credential bindings never establish pool identity here.
Dashboard primary-group attribution belongs to that caller, not financial facts.
"""

from dataclasses import dataclass
from typing import Literal

from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1, BudgetReportViewV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_money import sum_money
from agentmonitor.modules.capacity.domain.budget_reports import BudgetReportSelection

IdentityEvidence = Literal["provider_verified", "owner_asserted", "unresolved"]
CoverageReason = Literal[
    "included",
    "shared_pool_duplicate",
    "unresolved_overlap",
    "missing_report",
    "incomplete_report",
    "currency_unavailable",
    "empty_zero_unproven",
    "breakdown_report",
    "incompatible_pool_reports",
    "selection_too_large",
]


@dataclass(frozen=True, slots=True)
class BudgetSpendInput:
    resource_id: OpaqueIdV1
    canonical_pool_id: OpaqueIdV1 | None
    identity_evidence: IdentityEvidence
    selection: BudgetReportSelection

    def __post_init__(self) -> None:
        if (
            not isinstance(self.resource_id, OpaqueIdV1)
            or self.identity_evidence
            not in {"provider_verified", "owner_asserted", "unresolved"}
            or (self.canonical_pool_id is None)
            != (self.identity_evidence == "unresolved")
            or self.canonical_pool_id is not None
            and not isinstance(self.canonical_pool_id, OpaqueIdV1)
            or not isinstance(self.selection, BudgetReportSelection)
        ):
            raise ValueError("budget_spend_identity_invalid")
        if any(
            report is not None and report.report.subject.resource_id != self.resource_id
            for report in (self.selection.current, self.selection.latest_attempt)
        ):
            raise ValueError("budget_spend_resource_mismatch")


@dataclass(frozen=True, slots=True)
class BudgetSpendContribution:
    canonical_pool_id: OpaqueIdV1
    identity_evidence: IdentityEvidence
    report: BudgetReportViewV1
    retained_after_later_attempt: bool


@dataclass(frozen=True, slots=True)
class BudgetSpendGroup:
    currency: str
    period: BudgetPeriodV1
    cost_basis: str
    source_category: str
    total: ExactMoneyV1
    contributions: tuple[BudgetSpendContribution, ...]


@dataclass(frozen=True, slots=True)
class BudgetSpendCoverage:
    resource_id: OpaqueIdV1
    canonical_pool_id: OpaqueIdV1 | None
    reason: CoverageReason
    selection: BudgetReportSelection


@dataclass(frozen=True, slots=True)
class BudgetSpendAggregation:
    groups: tuple[BudgetSpendGroup, ...]
    coverage: tuple[BudgetSpendCoverage, ...]
    reason: Literal["no_eligible_reports", "selection_too_large"] | None


def _exclusion(item: BudgetSpendInput) -> CoverageReason | None:
    if item.canonical_pool_id is None:
        return "unresolved_overlap"
    current = item.selection.current
    if current is None:
        return (
            "incomplete_report" if item.selection.latest_attempt else "missing_report"
        )
    report = current.report
    if (
        report.completeness != "complete"
        or report.covered_period != report.requested_period
    ):
        return "incomplete_report"
    if report.grouping:
        return "breakdown_report"
    if report.currency is None:
        return "currency_unavailable"
    if not report.cost_buckets and not report.empty_means_zero:
        return "empty_zero_unproven"
    return None


def aggregate_budget_spend(
    inputs: tuple[BudgetSpendInput, ...],
) -> BudgetSpendAggregation:
    """Group compatible complete report totals, choosing one report per pool.

    No grand total mixes currencies, periods, bases or categories. Coverage
    includes every selected resource, even when no subtotal can be supplied.
    Original reports/watermarks and later attempts remain available; this policy
    has no clock and never asserts that a retained report is fresh.
    """
    if len({item.resource_id for item in inputs}) != len(inputs):
        raise ValueError("budget_spend_duplicate_resource")
    selected_pools = {
        ("pool", item.canonical_pool_id)
        if item.canonical_pool_id is not None
        else ("unresolved", item.resource_id)
        for item in inputs
    }
    if len(selected_pools) > 2000:
        return BudgetSpendAggregation(
            (),
            tuple(
                BudgetSpendCoverage(
                    item.resource_id,
                    item.canonical_pool_id,
                    "selection_too_large",
                    item.selection,
                )
                for item in inputs
            ),
            "selection_too_large",
        )

    # A category is another compatibility boundary: self/team or total/category
    # views are never silently combined even if their currency and basis match.
    type GroupKey = tuple[str, BudgetPeriodV1, str, str]
    candidates: dict[tuple[GroupKey, OpaqueIdV1], list[BudgetSpendInput]] = {}
    reasons: dict[OpaqueIdV1, CoverageReason] = {}
    for item in inputs:
        excluded = _exclusion(item)
        if excluded is not None:
            reasons[item.resource_id] = excluded
            continue
        current = item.selection.current
        assert current is not None and item.canonical_pool_id is not None
        report = current.report
        assert report.currency is not None
        key = (
            report.currency,
            report.requested_period,
            report.cost_basis,
            report.source_category,
        )
        candidates.setdefault((key, item.canonical_pool_id), []).append(item)

    grouped: dict[GroupKey, list[tuple[ExactMoneyV1, BudgetSpendContribution]]] = {}
    for (key, pool), candidates_for_pool in candidates.items():
        source_contexts = set()
        for item in candidates_for_pool:
            current = item.selection.current
            assert current is not None
            source_contexts.add(
                (
                    current.report.subject.provider_key,
                    current.report.subject.provider_target,
                    current.report.source_id,
                )
            )
        if len(source_contexts) != 1:
            for item in candidates_for_pool:
                reasons[item.resource_id] = "incompatible_pool_reports"
            continue

        def order(item: BudgetSpendInput) -> tuple[object, ...]:
            current = item.selection.current
            assert current is not None
            return (
                current.report.collected_at,
                current.stored_at,
                current.report_id.value,
                item.resource_id.value,
            )

        selected = max(candidates_for_pool, key=order)
        current = selected.selection.current
        assert current is not None
        amounts = tuple(row.amount for row in current.report.cost_buckets)
        amount = (
            sum_money(amounts)
            if amounts
            else ExactMoneyV1(CanonicalDecimalV1("0", 0), key[0])
        )
        latest = selected.selection.latest_attempt
        contribution = BudgetSpendContribution(
            pool,
            selected.identity_evidence,
            current,
            latest is not None
            and latest.report_id != current.report_id
            and latest.report.collected_at >= current.report.collected_at,
        )
        grouped.setdefault(key, []).append((amount, contribution))
        for item in candidates_for_pool:
            reasons[item.resource_id] = (
                "included"
                if item.resource_id == selected.resource_id
                else "shared_pool_duplicate"
            )

    groups = []
    for key in sorted(grouped, key=lambda k: (k[0], k[1].start, k[1].end, k[2], k[3])):
        values = sorted(
            grouped[key], key=lambda value: value[1].canonical_pool_id.value
        )
        groups.append(
            BudgetSpendGroup(
                *key,
                sum_money(tuple(value[0] for value in values)),
                tuple(value[1] for value in values),
            )
        )
    return BudgetSpendAggregation(
        tuple(groups),
        tuple(
            BudgetSpendCoverage(
                item.resource_id,
                item.canonical_pool_id,
                reasons[item.resource_id],
                item.selection,
            )
            for item in inputs
        ),
        None if groups else "no_eligible_reports",
    )
