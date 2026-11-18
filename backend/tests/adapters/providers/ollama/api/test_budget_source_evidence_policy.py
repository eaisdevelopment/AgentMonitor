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


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0"])
def test_reviewed_versions_retain_cost_evidence_with_sparse_token_facts(
    version: str,
) -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence
    from agentmonitor.contracts.capacity_v1 import BudgetUsageBucketV1
    from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1

    view, provenance = _inputs()
    provenance = replace(provenance, adapter_version=version, parser_version=version)
    original = report_source_evidence(view, provenance)
    assert original is not None
    sparse = tuple(
        BudgetUsageBucketV1(
            f"input-{index}",
            view.report.cost_buckets[index].period,
            ExactQuantityV1(CanonicalDecimalV1(str(index), 0), "input_tokens"),
            (),
        )
        for index in (0, 2)
    )
    with_tokens = replace(view, report=replace(view.report, usage_buckets=sparse))
    assert report_source_evidence(with_tokens, provenance) == original

    from agentmonitor.contracts.budget_query_v1 import BudgetSelectedReportV1
    from agentmonitor.contracts.capacity_v1 import BudgetReportSelectionV1
    from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import (
        BudgetForecastEvidence,
        forecast,
    )

    def selected(value: BudgetReportViewV1) -> BudgetSelectedReportV1:
        spend = reported_spend(BudgetReportSelectionV1(value, value))
        assert spend is not None
        return BudgetSelectedReportV1(value, spend, value.stored_at)

    before, after = selected(view), selected(with_tokens)
    assert after.reported_spend == before.reported_spend
    original_days = daily_costs(before, disjoint_costs=True)
    token_days = daily_costs(after, disjoint_costs=True)
    assert (
        token_days.days == original_days.days
        and token_days.reason == original_days.reason
    )
    evidence = BudgetForecastEvidence(corrections_resolved=True)
    assert (
        forecast(token_days, evidence=evidence).rate
        == forecast(original_days, evidence=evidence).rate
    )
    assert with_tokens.report.usage_buckets == sparse


@pytest.mark.parametrize(
    "adapter,parser", [("1.0.0", "1.1.0"), ("1.1.0", "1.0.0"), ("1.2.0", "1.2.0")]
)
def test_unreviewed_parser_adapter_pair_is_not_admitted(
    adapter: str, parser: str
) -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence

    view, provenance = _inputs()
    assert (
        report_source_evidence(
            view, replace(provenance, adapter_version=adapter, parser_version=parser)
        )
        is None
    )


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


def _model_inputs() -> tuple[BudgetReportViewV1, ObservationProvenanceV1]:
    from agentmonitor.contracts.capacity_v1 import BudgetDimensionV1

    view, provenance = _inputs()
    rows = tuple(
        replace(row, dimensions=(BudgetDimensionV1("model", "alpha"),))
        for row in view.report.cost_buckets
    )
    remainder = replace(
        rows[0],
        bucket_key="reported-remainder",
        dimensions=(BudgetDimensionV1("model", None, is_remainder=True),),
    )
    return replace(
        view,
        report=replace(
            view.report, grouping=("model",), cost_buckets=(*rows, remainder)
        ),
    ), replace(
        provenance,
        adapter_version="1.2.0",
        parser_version="1.2.0",
        mechanism_version="ollama-cloud-usage-docs-2026-11-12",
        decision_reference="M7-A03-OLLAMA-MODEL-DOCS-2026-11-12",
    )


def test_reviewed_models_and_remainder_are_disjoint_without_zero_day_proof() -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence
    from agentmonitor.contracts.capacity_v1 import BudgetReportSelectionV1
    from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend

    view, provenance = _model_inputs()
    evidence = report_source_evidence(view, provenance)
    assert evidence is not None and evidence.disjoint_costs
    assert evidence.corrections_resolved and not evidence.zero_day_coverage
    assert evidence.cost_freshness_deadline is None
    spend = reported_spend(BudgetReportSelectionV1(view, view))
    assert spend is not None and spend.total is None
    assert spend.reason_code == "breakdown_not_total"
    sparse = replace(
        view, report=replace(view.report, cost_buckets=view.report.cost_buckets[1:])
    )
    assert report_source_evidence(sparse, provenance) is not None


def test_current_ungrouped_and_legacy_ungrouped_provenance_stay_separate() -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence

    view, old = _inputs()
    _, current = _model_inputs()
    assert report_source_evidence(view, old) is not None
    assert report_source_evidence(view, current) is not None
    assert (
        report_source_evidence(
            view, replace(current, decision_reference=old.decision_reference)
        )
        is None
    )
    assert (
        report_source_evidence(
            view, replace(current, mechanism_version=old.mechanism_version)
        )
        is None
    )


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0"])
def test_old_provenance_cannot_admit_model_remainder_semantics(version: str) -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence

    view, _ = _model_inputs()
    _, old = _inputs()
    assert (
        report_source_evidence(
            view, replace(old, adapter_version=version, parser_version=version)
        )
        is None
    )


def test_model_unknown_is_not_the_explicit_reported_remainder() -> None:
    from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence
    from agentmonitor.contracts.capacity_v1 import BudgetDimensionV1

    view, provenance = _model_inputs()
    row = replace(
        view.report.cost_buckets[-1], dimensions=(BudgetDimensionV1("model", None),)
    )
    invalid = replace(
        view,
        report=replace(view.report, cost_buckets=(*view.report.cost_buckets[:-1], row)),
    )
    assert report_source_evidence(invalid, provenance) is None
