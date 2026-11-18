"""Pure admission for bounded, completed-day official Ollama usage reports."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal
from urllib.parse import urlencode

from agentmonitor.contracts.budget_forecast_v1 import BudgetSourceEvidenceV1
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetPeriodV1,
    BudgetReportViewV1,
    BudgetUsageBucketV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactMoneyV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1

HOST = "ollama.com"
PATH = "/api/usage"
SOURCE_ID = "ollama.cloud.usage.v1"
COST_BASIS = "provider_reported_usage_usd"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
REQUEST_SECONDS = 10
MAX_REQUESTS = 1
MINIMUM_INTERVAL_SECONDS = 15 * 60
# Official endpoint limit is shared per user across keys/devices. Composition
# must coordinate it with other local access paths; this source does not retry.
OFFICIAL_REQUESTS_PER_MINUTE = 10


def report_source_evidence(
    view: BudgetReportViewV1, provenance: ObservationProvenanceV1
) -> BudgetSourceEvidenceV1 | None:
    """Recognize only the reviewed daily replacement snapshot semantics.

    These closed version selectors intentionally do not follow a future manifest
    automatically. New parsers must establish their own analysis semantics.
    The endpoint supplies neither omitted-day zero proof nor a freshness bound.
    """
    report = view.report
    version = (provenance.adapter_version, provenance.parser_version)
    current = (
        version == ("1.2.0", "1.2.0")
        and provenance.mechanism_version == "ollama-cloud-usage-docs-2026-11-12"
        and provenance.decision_reference == "M7-A03-OLLAMA-MODEL-DOCS-2026-11-12"
    )
    legacy = (
        version in {("1.0.0", "1.0.0"), ("1.1.0", "1.1.0")}
        and provenance.mechanism_version == "ollama-cloud-usage-docs-2026-11-11"
        and not report.grouping
    )
    if (
        report.subject.provider_key != "ollama"
        or report.source_id != SOURCE_ID
        or report.source_category
        not in {"self_requests_and_cost", "team_requests_and_cost"}
        or report.cost_basis != COST_BASIS
        or report.grouping not in {(), ("model",)}
        or not (current or legacy)
        or report.completeness != "complete"
        or report.covered_period != report.requested_period
        or report.currency != "USD"
        or report.empty_means_zero
        or report.source_data_through is not None
        or provenance.provider_key != "ollama"
        or provenance.source_id != SOURCE_ID
        or provenance.capability_id != "api.usage"
        or provenance.capability_schema_version != "2.0.0"
        or provenance.adapter_id != "agentmonitor.ollama.api-usage"
        or provenance.provider_protocol_version != "1.0.0"
        or provenance.source_class != "documented_api"
        or provenance.collected_at != report.collected_at
        or provenance.precision != "exact"
        or provenance.value_kind != "provider_reported"
        or provenance.confidence != "confirmed"
        or provenance.fallback_lineage
        or provenance.derivation_method is not None
        or provenance.input_observation_ids
        or provenance.freshness_policy_id != "ollama_usage_source_watermark_v1"
        or provenance.freshness_deadline is not None
        or provenance.freshness_availability.state != "unknown"
    ):
        return None
    period = report.requested_period
    days = (period.end - period.start).days
    if (
        days not in {7, 30}
        or period.start
        != period.start.replace(hour=0, minute=0, second=0, microsecond=0)
        or period.end != period.start + timedelta(days=days)
    ):
        return None
    if report.grouping:
        # Only the reviewed model parser establishes disjoint components. Sparse
        # days remain sparse; it exposes no watermark or omitted-day zero proof.
        rows: tuple[BudgetCostBucketV1 | BudgetUsageBucketV1, ...] = (
            *report.cost_buckets,
            *report.usage_buckets,
        )
        if not report.cost_buckets or any(
            len(row.dimensions) != 1
            or row.dimensions[0].kind != "model"
            or (row.dimensions[0].value is None) != row.dimensions[0].is_remainder
            or row.period.start
            != row.period.start.replace(hour=0, minute=0, second=0, microsecond=0)
            or row.period.end != row.period.start + timedelta(days=1)
            for row in rows
        ):
            return None
        names = {
            row.dimensions[0].value
            for row in rows
            if not row.dimensions[0].is_remainder
        }
        identities = {(row.period.start, row.dimensions) for row in report.cost_buckets}
        if len(names) > 10 or len(identities) != len(report.cost_buckets):
            return None
    else:
        costs = sorted(report.cost_buckets, key=lambda bucket: bucket.period.start)
        if len(costs) != days or any(
            bucket.dimensions
            or bucket.period.start != period.start + timedelta(days=index)
            or bucket.period.end != period.start + timedelta(days=index + 1)
            for index, bucket in enumerate(costs)
        ):
            return None
    return BudgetSourceEvidenceV1(
        view.report_id,
        "ollama_usage_model_snapshot_v1"
        if report.grouping
        else "ollama_usage_daily_snapshot_v1",
        "1.0.0",
        disjoint_costs=True,
        corrections_resolved=True,
        zero_day_coverage=False,
        cost_freshness_deadline=None,
    )


def completed_period(instant: datetime, range_key: str) -> BudgetPeriodV1:
    if (
        not isinstance(instant, datetime)
        or instant.utcoffset() != timedelta(0)
        or range_key not in {"7d", "30d"}
    ):
        raise ValueError("ollama_usage_period_invalid")
    end = instant.replace(hour=0, minute=0, second=0, microsecond=0)
    return BudgetPeriodV1(end - timedelta(days=7 if range_key == "7d" else 30), end)


@dataclass(frozen=True, slots=True)
class OllamaUsageRequestV1(TechnicalValueV1):
    """Captured actual binding/scope; neither the key nor GET proves identity."""

    subject: CapacitySubjectV2
    binding: ActiveCredentialBindingRefV1
    scope_id: OpaqueIdV1 | None
    scope_evidence: Literal["provider_verified", "owner_asserted", "unresolved"]
    scope_generation: int
    range_key: Literal["7d", "30d"]
    period: BudgetPeriodV1
    requested_at: datetime
    scope: Literal["self", "team"] = "self"
    grouping: tuple[Literal["model"], ...] = ()

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not isinstance(self.subject, CapacitySubjectV2)
            or self.subject.provider_key != "ollama"
            or self.subject.provider_target.target_kind != "cloud_service"
            or not isinstance(self.binding, ActiveCredentialBindingRefV1)
            or self.binding.account_id != self.subject.account_id
            or self.scope not in {"self", "team"}
            or type(self.grouping) is not tuple
            or self.grouping not in {(), ("model",)}
            or self.scope_evidence
            not in {"provider_verified", "owner_asserted", "unresolved"}
            or (self.scope_id is None) != (self.scope_evidence == "unresolved")
            or self.scope_id is not None
            and not isinstance(self.scope_id, OpaqueIdV1)
            or type(self.scope_generation) is not int
            or self.scope_generation < 1
            or self.period != completed_period(self.requested_at, self.range_key)
        ):
            raise ValueError("ollama_usage_request_invalid")


def request_path(request: OllamaUsageRequestV1) -> str:
    query: dict[str, str] = {"range": request.range_key, "scope": request.scope}
    if request.grouping:
        query["group_by"] = "model"
    return PATH + "?" + urlencode(query)


def validate_response_context(
    request: OllamaUsageRequestV1,
    *,
    range_key: object,
    scope: object,
    granularity: object,
    start: datetime,
    end: datetime,
    grouping: object = None,
) -> None:
    """Native coverage must match the fixed selected cutoff, including midnight."""
    if (
        grouping != ("model" if request.grouping else None)
        or range_key != request.range_key
        or scope != request.scope
        or granularity != "day"
        or start != request.period.start
        or start.utcoffset() != timedelta(0)
        or end.utcoffset() != timedelta(0)
        or not request.period.end <= end < request.period.end + timedelta(days=1)
    ):
        raise ValueError("ollama_usage_response_context_invalid")


def dollars_to_money(value: Decimal) -> ExactMoneyV1:
    return ExactMoneyV1(CanonicalDecimalV1.from_decimal(value), "USD")


def usage_quantities(
    *,
    request_count: object,
    input_tokens: object = None,
    cached_input_tokens: object = None,
    output_tokens: object = None,
) -> tuple[ExactQuantityV1, ...]:
    """Preserve optional typed measures separately, without coercion or sums.

    Missing token measures do not mean zero. Cached input is retained as its
    own reported measure; no relationship with input tokens is inferred.
    """
    quantities = []
    for unit, count in (
        ("requests", request_count),
        ("input_tokens", input_tokens),
        ("cached_input_tokens", cached_input_tokens),
        ("output_tokens", output_tokens),
    ):
        if count is None and unit != "requests":
            continue
        if type(count) is not int or count < 0 or len(str(count)) > 78:
            raise ValueError("ollama_usage_count_invalid")
        quantities.append(ExactQuantityV1(CanonicalDecimalV1(str(count), 0), unit))
    return tuple(quantities)


def bounded_deadline(now: float, requested: float | None) -> float:
    if not math.isfinite(now) or (
        requested is not None and (not math.isfinite(requested) or requested <= now)
    ):
        raise TimeoutError("ollama_usage_deadline_exceeded")
    return (
        min(now + REQUEST_SECONDS, requested)
        if requested is not None
        else now + REQUEST_SECONDS
    )


def retry_after_seconds(value: str | None) -> int | None:
    if (
        value is None
        or not 1 <= len(value) <= 19
        or not value.isascii()
        or not value.isdigit()
    ):
        return None
    seconds = int(value)
    return seconds if seconds <= 2**63 - 1 else None
