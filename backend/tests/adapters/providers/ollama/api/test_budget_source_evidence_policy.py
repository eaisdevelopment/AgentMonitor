"""Constructed normalized domain inputs only; no provider payload or I/O."""

from dataclasses import replace
from datetime import timedelta

import pytest
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetPeriodV1,
    BudgetReportViewV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.capacity.pure.test_budget_commit_policy import pure_request


def _inputs() -> tuple[BudgetReportViewV1, ObservationProvenanceV1]:
    request = pure_request()
    original = request.payload
    start = original.requested_period.start
    costs = tuple(
        BudgetCostBucketV1(
            f"cost-{index}",
            BudgetPeriodV1(
                start + timedelta(days=index), start + timedelta(days=index + 1)
            ),
            ExactMoneyV1(CanonicalDecimalV1(str(index), 0), "USD"),
            (),
            "charge",
        )
        for index in range(7)
    )
    report = replace(
        original,
        subject=replace(original.subject, provider_key="ollama"),
        source_id="ollama.cloud.usage.v1",
        source_category="self_requests_and_cost",
        cost_basis="provider_reported_usage_usd",
        grouping=(),
        cost_buckets=costs,
        usage_buckets=(),
    )
    provenance = replace(
        request.provenance,
        provider_key="ollama",
        capability_id="api.usage",
        adapter_id="agentmonitor.ollama.api-usage",
        adapter_version="1.0.0",
        provider_protocol_version="1.0.0",
        source_id=report.source_id,
        mechanism_version="ollama-cloud-usage-docs-2026-11-11",
        parser_version="1.0.0",
        freshness_policy_id="ollama_usage_source_watermark_v1",
    )
    return BudgetReportViewV1(
        OpaqueIdV1("pure-report"), report, report.collected_at
    ), provenance


def test_complete_daily_costs_support_only_historical_source_semantics() -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence

    view, provenance = _inputs()
    evidence = report_source_evidence(view, provenance)
    assert evidence is not None
    assert evidence.report_id == view.report_id
    assert evidence.disjoint_costs and evidence.corrections_resolved
    assert not evidence.zero_day_coverage
    assert evidence.cost_freshness_deadline is None


@pytest.mark.parametrize(
    "case",
    ["adapter", "parser", "mechanism", "source", "time", "gap", "money", "partial"],
)
def test_unknown_or_incomplete_evidence_fails_closed(case: str) -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence

    view, provenance = _inputs()
    if case == "adapter":
        provenance = replace(provenance, adapter_id="unknown.adapter")
    elif case == "parser":
        provenance = replace(provenance, parser_version="99.0.0")
    elif case == "mechanism":
        provenance = replace(provenance, mechanism_version="unknown")
    elif case == "source":
        provenance = replace(provenance, source_id="unknown.source")
    elif case == "time":
        provenance = replace(
            provenance, collected_at=provenance.collected_at + timedelta(seconds=1)
        )
    elif case == "gap":
        view = replace(
            view, report=replace(view.report, cost_buckets=view.report.cost_buckets[1:])
        )
    elif case == "money":
        view = replace(
            view, report=replace(view.report, cost_buckets=(), currency=None)
        )
    else:
        view = replace(
            view,
            report=replace(
                view.report, completeness="partial", omission_codes=("source_partial",)
            ),
        )
    assert report_source_evidence(view, provenance) is None
