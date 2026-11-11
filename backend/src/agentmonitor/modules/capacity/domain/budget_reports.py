"""Select immutable complete coverage without retaining superseded charges."""

from agentmonitor.contracts.capacity_v1 import (
    BudgetReportInputV1,
    BudgetReportSelectionV1,
    BudgetReportViewV1,
)

# Preserve the internal import name while publishing one immutable DTO shape.
BudgetReportSelection = BudgetReportSelectionV1


def _same_context(left: BudgetReportInputV1, right: BudgetReportInputV1) -> bool:
    # Rotation preserves resolved financial scope, but an unresolved new binding
    # may access a different actor. Keep that access lineage as its own context.
    # budget_current_query.CURRENT_REPORT_METADATA_SQL uses the same conditional
    # binding pair, alongside the same scope/source/period/currency dimensions.
    left_lineage = (
        (left.binding_id, left.binding_generation)
        if left.scope_evidence == "unresolved"
        else None
    )
    right_lineage = (
        (right.binding_id, right.binding_generation)
        if right.scope_evidence == "unresolved"
        else None
    )
    return (
        left.subject == right.subject
        and left.scope_id == right.scope_id
        and left.scope_generation == right.scope_generation
        and left_lineage == right_lineage
        and left.source_id == right.source_id
        and left.source_category == right.source_category
        and left.cost_basis == right.cost_basis
        and left.grouping == right.grouping
        and left.requested_period == right.requested_period
        and left.currency == right.currency
    )


def select_current_report(
    reports: tuple[BudgetReportViewV1, ...],
) -> BudgetReportSelection:
    """Choose an entire replacement report within one queried compatible scope.

    The repository supplies a bounded same-context selection. Cross-pool/time/
    currency aggregation is a separate operation, never an incidental effect of
    merging historical rows. No clock, storage or provider access occurs here.
    """
    if not reports:
        return BudgetReportSelection(current=None, latest_attempt=None)
    if any(not _same_context(reports[0].report, item.report) for item in reports):
        raise ValueError("budget_incompatible_report_context")
    if len({item.report_id for item in reports}) != len(reports):
        raise ValueError("budget_duplicate_report_identity")
    ordered = sorted(
        reports,
        key=lambda item: (
            item.report.collected_at,
            item.stored_at,
            item.report_id.value,
        ),
        reverse=True,
    )
    current = next(
        (
            item
            for item in ordered
            if item.report.completeness == "complete"
            and item.report.covered_period == item.report.requested_period
        ),
        None,
    )
    return BudgetReportSelection(current=current, latest_attempt=ordered[0])
