"""Constructed normalized values exercise pure source policy, never external I/O."""

from dataclasses import replace
from datetime import timedelta

import pytest
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetDimensionKindV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetReportViewV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1

from backend.tests.capacity.pure.test_budget_commit_policy import pure_request


def _inputs(
    grouping: tuple[BudgetDimensionKindV1, ...] = (),
) -> tuple[BudgetReportViewV1, ObservationProvenanceV1]:
    original = pure_request()
    period = original.payload.requested_period
    rows = tuple(
        BudgetCostBucketV1(
            f"day-{day}-{partition}",
            BudgetPeriodV1(
                period.start + timedelta(days=day),
                period.start + timedelta(days=day + 1),
            ),
            ExactMoneyV1(CanonicalDecimalV1("2", 0), "USD"),
            (BudgetDimensionV1(grouping[0], partition),) if grouping else (),
            "charge",
        )
        for day in (3, 4, 5)
        for partition in (("first", "second") if grouping else ("only",))
    )
    report = replace(
        original.payload,
        subject=replace(original.payload.subject, provider_key="codex"),
        source_id="openai.organization.costs.v1",
        source_category="cost_tokens" if grouping == ("token_category",) else "cost",
        cost_basis="openai_reported_cost",
        grouping=grouping,
        cost_buckets=rows,
        usage_buckets=(),
        source_data_through=None,
        empty_means_zero=False,
    )
    provenance = replace(
        original.provenance,
        provider_key="codex",
        capability_id="api.cost",
        adapter_id="agentmonitor.codex.openai-api",
        adapter_version="1.1.0",
        parser_version="1.1.0",
        provider_protocol_version="1.0.0",
        source_id=report.source_id,
        mechanism_version="openai-organization-costs-docs-2026-11-11",
        observed_at=report.source_data_through,
        observed_at_availability=FieldAvailabilityV1("unknown"),
        provider_version=None,
        provider_version_availability=FieldAvailabilityV1("unknown"),
        freshness_policy_id="openai_cost_source_watermark_v1",
        decision_reference="OPENAI-ANALYTICS-1.1",
    )
    return BudgetReportViewV1(
        OpaqueIdV1("pure-report"), report, report.collected_at
    ), provenance


@pytest.mark.parametrize("grouping", [(), ("project",), ("api_key_id",)])
def test_sparse_observed_partition_has_exact_three_day_rate_without_zero_or_freshness(
    grouping: tuple[BudgetDimensionKindV1, ...],
) -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )
    from agentmonitor.contracts.budget_query_v1 import BudgetSelectedReportV1
    from agentmonitor.contracts.capacity_v1 import BudgetReportSelectionV1
    from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import (
        BudgetForecastEvidence,
        forecast,
    )

    view, provenance = _inputs(grouping)
    evidence = report_source_evidence(view, provenance)
    assert evidence is not None
    assert evidence.report_id == view.report_id
    assert evidence.disjoint_costs and evidence.corrections_resolved
    assert not evidence.zero_day_coverage
    assert evidence.cost_freshness_deadline is None
    spend = reported_spend(BudgetReportSelectionV1(view, view))
    assert spend is not None
    selected = BudgetSelectedReportV1(view, spend, view.stored_at)
    days = daily_costs(
        selected,
        disjoint_costs=evidence.disjoint_costs,
        zero_day_coverage=evidence.zero_day_coverage,
    )
    assert len(days.days) == 3 and not any(day.derived_zero for day in days.days)
    result = forecast(
        days,
        evidence=BudgetForecastEvidence(
            corrections_resolved=evidence.corrections_resolved
        ),
    )
    assert result.rate is not None
    assert result.rate.day_count == 3
    assert result.rate.covered_seconds == 3 * 86400
    assert result.rate.cost.amount == CanonicalDecimalV1("12" if grouping else "6", 0)
    assert result.rate.input_report_ids == (view.report_id,)
    assert result.exhaustion_at is None


@pytest.mark.parametrize(
    "version", ["1.0.0", "1.0.1", "1.0.2", "1.0.3", "1.1.0", "1.1.1", "1.1.2", "1.1.3"]
)
def test_reviewed_ungrouped_versions_retain_evidence(version: str) -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )

    view, provenance = _inputs()
    assert (
        report_source_evidence(
            view,
            replace(
                provenance,
                adapter_version=version,
                parser_version=version,
                decision_reference="M7-A02-OPENAI-COST-DOCS-2026-11-11"
                if version in {"1.0.0", "1.0.1", "1.0.2", "1.0.3"}
                else "OPENAI-ANALYTICS-1.1",
            ),
        )
        is not None
    )


@pytest.mark.parametrize(
    "adapter,parser", [("1.0.0", "1.1.0"), ("1.1.0", "1.0.0"), ("1.2.0", "1.2.0")]
)
def test_unreviewed_versions_are_not_admitted(adapter: str, parser: str) -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )

    view, provenance = _inputs()
    assert (
        report_source_evidence(
            view, replace(provenance, adapter_version=adapter, parser_version=parser)
        )
        is None
    )


@pytest.mark.parametrize(
    "case",
    [
        "source",
        "mechanism",
        "capability",
        "schema",
        "time",
        "partial",
        "usage",
        "interval",
        "legacy_group",
        "duplicate_partition",
        "watermark",
    ],
)
def test_incompatible_source_context_fails_closed(case: str) -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )

    view, provenance = _inputs()
    report = view.report
    if case == "source":
        provenance = replace(provenance, source_id="unreviewed.source")
    elif case == "mechanism":
        provenance = replace(provenance, mechanism_version="unreviewed")
    elif case == "capability":
        provenance = replace(provenance, capability_id="api.usage")
    elif case == "schema":
        provenance = replace(provenance, capability_schema_version="99.0.0")
    elif case == "time":
        provenance = replace(
            provenance, collected_at=provenance.collected_at + timedelta(seconds=1)
        )
    elif case == "partial":
        report = replace(
            report,
            empty_means_zero=False,
            completeness="partial",
            omission_codes=("source_partial",),
        )
    elif case == "usage":
        report = replace(report, source_category="usage")
    elif case == "interval":
        row = report.cost_buckets[0]
        report = replace(
            report,
            cost_buckets=(
                replace(
                    row,
                    period=BudgetPeriodV1(
                        row.period.start, row.period.end + timedelta(days=1)
                    ),
                ),
            ),
        )
    elif case == "legacy_group":
        view, provenance = _inputs(("api_key_id",))
        report = view.report
        provenance = replace(
            provenance,
            adapter_version="1.0.0",
            parser_version="1.0.0",
            decision_reference="M7-A02-OPENAI-COST-DOCS-2026-11-11",
        )
    elif case == "duplicate_partition":
        row = report.cost_buckets[0]
        report = replace(
            report,
            cost_buckets=(
                *report.cost_buckets,
                replace(row, bucket_key="duplicate", kind="adjustment"),
            ),
        )
    else:
        report = replace(
            report,
            empty_means_zero=False,
            source_data_through=report.requested_period.end,
        )
    assert report_source_evidence(replace(view, report=report), provenance) is None


def test_gaps_and_adjustments_do_not_become_eligible_three_day_samples() -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )
    from agentmonitor.contracts.budget_query_v1 import BudgetSelectedReportV1
    from agentmonitor.contracts.capacity_v1 import BudgetReportSelectionV1
    from agentmonitor.modules.capacity.domain.budget_account_spend import reported_spend
    from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
    from agentmonitor.modules.capacity.domain.budget_forecast import (
        BudgetForecastEvidence,
        forecast,
    )

    view, provenance = _inputs()
    first, middle, last = view.report.cost_buckets
    for rows in ((first, last), (first, replace(middle, kind="adjustment"), last)):
        selected_view = replace(view, report=replace(view.report, cost_buckets=rows))
        source = report_source_evidence(selected_view, provenance)
        assert source is not None
        spend = reported_spend(BudgetReportSelectionV1(selected_view, selected_view))
        assert spend is not None
        days = daily_costs(
            BudgetSelectedReportV1(selected_view, spend, selected_view.stored_at),
            disjoint_costs=source.disjoint_costs,
            zero_day_coverage=source.zero_day_coverage,
        )
        result = forecast(
            days,
            evidence=BudgetForecastEvidence(
                corrections_resolved=source.corrections_resolved
            ),
        )
        assert result.rate is None
        assert result.exhaustion_at is None
        assert not any(day.derived_zero for day in days.days)


def test_revision_evidence_is_bound_to_selected_report_without_finality_wait() -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )

    view, provenance = _inputs()
    original = report_source_evidence(view, provenance)
    assert original is not None
    replacement = replace(
        view,
        report_id=OpaqueIdV1("replacement"),
        report=replace(view.report, cost_buckets=view.report.cost_buckets[1:]),
    )
    updated = report_source_evidence(replacement, provenance)
    assert updated is not None
    assert updated.report_id == replacement.report_id != original.report_id
    assert updated.corrections_resolved
    assert report_source_evidence(view, provenance) == original


def test_empty_report_retains_only_admitted_source_zero_semantics() -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )

    view, provenance = _inputs()
    empty = replace(view, report=replace(view.report, cost_buckets=(), currency=None))
    evidence = report_source_evidence(empty, provenance)
    assert evidence is None
    assert not empty.report.empty_means_zero


def test_native_non_usd_currency_is_not_relabelled_or_converted() -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )

    view, provenance = _inputs()
    rows = tuple(
        replace(row, amount=ExactMoneyV1(row.amount.amount, "GBP"))
        for row in view.report.cost_buckets
    )
    sterling = replace(
        view, report=replace(view.report, currency="GBP", cost_buckets=rows)
    )
    evidence = report_source_evidence(sterling, provenance)
    assert evidence is not None
    assert sterling.report.currency == "GBP"
    assert tuple(row.amount.amount for row in rows) == tuple(
        row.amount.amount for row in view.report.cost_buckets
    )


@pytest.mark.parametrize(
    "version,reference",
    [
        ("1.0.0", "M7-T005"),
        ("1.1.0", "M7-T005"),
        ("1.0.0", "OPENAI-ANALYTICS-1.1"),
        ("1.1.0", "M7-A02-OPENAI-COST-DOCS-2026-11-11"),
    ],
)
def test_mapping_reference_must_match_exact_reviewed_version(
    version: str, reference: str
) -> None:
    from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
        report_source_evidence,
    )

    view, provenance = _inputs()
    assert (
        report_source_evidence(
            view,
            replace(
                provenance,
                adapter_version=version,
                parser_version=version,
                decision_reference=reference,
            ),
        )
        is None
    )
