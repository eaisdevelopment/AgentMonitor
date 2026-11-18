"""Closed admission of reviewed daily monetary replacement report semantics."""

from datetime import datetime, timedelta

from agentmonitor.adapters.providers.claude.anthropic_api.usage_policy import (
    TOKEN_CATEGORIES,
)
from agentmonitor.contracts.budget_forecast_v1 import BudgetSourceEvidenceV1
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1


def _midnight(value: datetime) -> bool:
    return value.utcoffset() == timedelta(0) and not any(
        (value.hour, value.minute, value.second, value.microsecond)
    )


def report_source_evidence(
    view: BudgetReportViewV1, provenance: ObservationProvenanceV1
) -> BudgetSourceEvidenceV1 | None:
    """Admit one immutable report, never combine revisions or infer freshness.

    Native single-dimension groups are alternative partitions of that report.
    Sparse observed days remain sparse; M05 selects its consecutive sample.
    Version selectors are deliberately closed, independent of future manifests.
    """
    report = view.report
    if (
        report.subject.provider_key != "claude"
        or report.source_id != "anthropic.analytics.cost.v1"
        or report.cost_basis != "discounted_before_credits"
        or report.completeness != "complete"
        or report.covered_period != report.requested_period
        or report.omission_codes
        or report.usage_buckets
        or report.currency != "USD"
        or provenance.provider_key != "claude"
        or provenance.source_id != report.source_id
        or provenance.capability_id != "api.cost"
        or provenance.capability_schema_version != "2.0.0"
        or provenance.adapter_id != "agentmonitor.claude.anthropic-api"
        or (
            provenance.adapter_version,
            provenance.parser_version,
            provenance.decision_reference,
        )
        not in {
            ("1.0.0", "1.0.0", "M7-A01-ANTHROPIC-DOCS-2026-11-11"),
            ("1.0.1", "1.0.1", "M7-A01-ANTHROPIC-DOCS-2026-11-11"),
            ("1.1.0", "1.1.0", "ANTHROPIC-ANALYTICS-1.1"),
            ("1.1.1", "1.1.1", "ANTHROPIC-ANALYTICS-1.1"),
        }
        or provenance.adapter_version in {"1.0.0", "1.0.1"}
        and bool(report.grouping)
        or provenance.provider_protocol_version != "1.0.0"
        or provenance.mechanism_version != "2026-10-21"
        or provenance.source_class != "documented_api"
        or provenance.collected_at != report.collected_at
        or provenance.precision != "exact"
        or provenance.value_kind != "provider_reported"
        or provenance.confidence != "confirmed"
        or provenance.fallback_lineage
        or provenance.derivation_method is not None
        or provenance.input_observation_ids
        or provenance.warnings
        or provenance.freshness_policy_id != "anthropic_cost_source_watermark_v1"
        or provenance.freshness_deadline is not None
        or provenance.freshness_availability.state != "unknown"
    ):
        return None
    if (
        (report.source_category, report.grouping)
        not in {
            ("cost", ()),
            ("cost", ("workspace",)),
            ("cost", ("api_key_id",)),
            ("cost", ("model",)),
            ("cost_tokens", ("token_category",)),
        }
        or report.source_data_through is None
        or report.source_data_through < report.requested_period.end
        or not report.empty_means_zero
        or provenance.observed_at != report.source_data_through
        or provenance.observed_at_availability.state != "available"
        or provenance.provider_version != "2026-10-21"
        or provenance.provider_version_availability.state != "available"
        or report.grouping == ("token_category",)
        and any(
            item.value not in TOKEN_CATEGORIES
            for row in report.cost_buckets
            for item in row.dimensions
        )
    ):
        return None
    period = report.requested_period
    if (
        period.end - period.start not in {timedelta(days=7), timedelta(days=30)}
        or not _midnight(period.start)
        or not _midnight(period.end)
        or period.end > report.collected_at
    ):
        return None
    # One fact per native day/partition; repeated adjustments cannot masquerade
    # as another disjoint charge. M05 separately rejects signed sample entries.
    seen = set()
    for bucket in report.cost_buckets:
        key = (bucket.period.start, bucket.dimensions)
        if (
            not _midnight(bucket.period.start)
            or bucket.period.end - bucket.period.start != timedelta(days=1)
            or any(item.is_remainder for item in bucket.dimensions)
            or tuple(item.kind for item in bucket.dimensions) != report.grouping
            or key in seen
        ):
            return None
        seen.add(key)
    return BudgetSourceEvidenceV1(
        view.report_id,
        "anthropic_cost_daily_snapshot_v1",
        "1.0.0",
        disjoint_costs=True,
        corrections_resolved=True,
        zero_day_coverage=False,
        cost_freshness_deadline=None,
    )
