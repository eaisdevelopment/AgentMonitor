"""Pure projection of normalized cloud report selections; no port stand-ins."""

from dataclasses import replace

from agentmonitor.contracts.capacity_v1 import (
    BudgetReportSelectionV1,
    BudgetReportViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application import cloud_budget_query

from backend.tests.capacity.pure.test_budget_codec import pure_report


def test_both_cloud_scopes_are_visible_but_default_spend_stays_self() -> None:
    base = replace(pure_report(), grouping=(), cost_buckets=(), usage_buckets=())
    selections = []
    for scope in ("self_requests_and_cost", "team_requests_and_cost", "unknown"):
        report = replace(base, source_category=scope)
        view = BudgetReportViewV1(OpaqueIdV1(scope), report, report.collected_at)
        selections.append(BudgetReportSelectionV1(view, view))
    visible = cloud_budget_query.visible_cloud_reports(tuple(selections))
    assert visible == tuple(selections[:2])
    assert cloud_budget_query.default_cloud_spend_reports(visible) == (selections[0],)
