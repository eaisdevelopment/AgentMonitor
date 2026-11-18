"""Pure analytics normalization from typed counts and safe dimensions.

No raw provider payloads, clock, I/O, pricing or inferred quantities here.
The usage token-category view projects only the five disjoint native token
measures. Other views retain total_tokens as a separate unit, never an addend.
"""

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    COST_BASIS,
    GROUP_FIELDS,
    SOURCE_ID,
    USAGE_SOURCE_ID,
    AnthropicCostRequestV1,
    AnthropicUsageRequestV1,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetDimensionKindV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    BudgetUsageBucketV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)

TOKEN_CATEGORIES = (
    "uncached_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
    "cache_creation.ephemeral_1h_input_tokens",
    "cache_creation.ephemeral_5m_input_tokens",
)
_SAFE_METADATA = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class AnthropicUsageMeasuresV1:
    """Native reported counts; requests can include execution spans.

    requests is optional in the official SDK. None remains absent, unlike zero.
    total_tokens is retained without assuming it equals the component sum.
    """

    uncached_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    ephemeral_1h_input_tokens: int
    ephemeral_5m_input_tokens: int
    total_tokens: int
    requests: int | None
    web_search_requests: int

    def __post_init__(self) -> None:
        counts = (
            self.uncached_input_tokens,
            self.cache_read_input_tokens,
            self.output_tokens,
            self.ephemeral_1h_input_tokens,
            self.ephemeral_5m_input_tokens,
            self.total_tokens,
            self.web_search_requests,
        ) + (() if self.requests is None else (self.requests,))
        if any(type(count) is not int or not 0 <= count < 10**20 for count in counts):
            raise ValueError("anthropic_usage_count_invalid")

    def token_measures(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            zip(
                TOKEN_CATEGORIES,
                (
                    self.uncached_input_tokens,
                    self.cache_read_input_tokens,
                    self.output_tokens,
                    self.ephemeral_1h_input_tokens,
                    self.ephemeral_5m_input_tokens,
                ),
                strict=True,
            )
        )


def dimensions_for_grouping(
    grouping: tuple[BudgetDimensionKindV1, ...],
    value: str | None,
) -> tuple[BudgetDimensionV1, ...]:
    """Only source-safe identifiers survive; null is explicitly unassigned."""
    if not grouping:
        if value is not None:
            raise ValueError("anthropic_analytics_unrequested_dimension")
        return ()
    if len(grouping) != 1 or grouping[0] not in GROUP_FIELDS:
        raise ValueError("anthropic_analytics_grouping_invalid")
    kind = grouping[0]
    if value is not None and (
        type(value) is not str
        or _SAFE_METADATA.fullmatch(value) is None
        or kind == "api_key_id"
        and not value.startswith("apikey_")
        or kind == "workspace"
        and not value.startswith("wrkspc_")
        or kind == "token_category"
        and value not in TOKEN_CATEGORIES
    ):
        raise ValueError("anthropic_analytics_dimension_invalid")
    return (BudgetDimensionV1(kind, value),)


def bucket_key(
    period: BudgetPeriodV1,
    dimensions: tuple[BudgetDimensionV1, ...],
    unit: str | None = None,
) -> str:
    """Stable semantic row identity; keep the existing ungrouped cost identity."""
    key = "daily_" + period.start.strftime("%Y%m%d")
    if dimensions or unit is not None:
        identity = json.dumps(
            [unit, [[item.kind, item.value] for item in dimensions]],
            separators=(",", ":"),
            ensure_ascii=True,
        )
        key += "_" + hashlib.sha256(identity.encode("ascii")).hexdigest()
    return key


def usage_buckets(
    period: BudgetPeriodV1,
    measures: AnthropicUsageMeasuresV1,
    dimensions: tuple[BudgetDimensionV1, ...],
    *,
    token_categories: bool = False,
) -> tuple[BudgetUsageBucketV1, ...]:
    """Native measures or one token-category projection, never both totals."""
    if token_categories and dimensions:
        raise ValueError("anthropic_analytics_cross_product_unavailable")
    facts = measures.token_measures()
    if not token_categories:
        facts += (
            ("total_tokens", measures.total_tokens),
            ("web_search_requests", measures.web_search_requests),
        )
        if measures.requests is not None:
            facts += (("requests", measures.requests),)
    rows = []
    for category, count in facts:
        selected = (
            dimensions_for_grouping(("token_category",), category)
            if token_categories
            else dimensions
        )
        unit = "tokens" if token_categories else category
        rows.append(
            BudgetUsageBucketV1(
                bucket_key(period, selected, unit),
                period,
                ExactQuantityV1(CanonicalDecimalV1(str(count), 0), unit),
                selected,
            )
        )
    return tuple(rows)


def build_analytics_report(
    request: AnthropicCostRequestV1,
    rows: Sequence[BudgetCostBucketV1 | BudgetUsageBucketV1],
    refreshed: datetime | None,
    omission: str | None,
    collected: datetime,
) -> BudgetReportInputV1:
    """Preserve source identity, coverage and native units without clock I/O."""
    usage = isinstance(request, AnthropicUsageRequestV1)
    expected_row = BudgetUsageBucketV1 if usage else BudgetCostBucketV1
    if any(not isinstance(row, expected_row) for row in rows):
        raise ValueError("anthropic_analytics_row_category_invalid")
    if refreshed is not None and refreshed > collected:
        raise ValueError("anthropic_cost_future_refresh")
    if omission is None and (refreshed is None or refreshed < request.period.end):
        omission = (
            "provider_data_not_ready" if refreshed is None else "provider_data_delayed"
        )
    complete = omission is None
    token_categories = request.grouping == ("token_category",)
    return BudgetReportInputV1(
        subject=request.subject,
        binding_id=request.binding.binding_id,
        binding_generation=request.binding.generation,
        scope_generation=request.scope_generation,
        scope_id=request.scope_id,
        scope_evidence=request.scope_evidence,
        source_id=USAGE_SOURCE_ID if usage else SOURCE_ID,
        source_category=("usage_tokens" if token_categories else "usage")
        if usage
        else ("cost_tokens" if token_categories else "cost"),
        cost_basis="not_applicable" if usage else COST_BASIS,
        grouping=request.grouping,
        requested_period=request.period,
        covered_period=request.period if complete else None,
        source_data_through=refreshed,
        collected_at=collected,
        completeness="complete"
        if complete
        else "unknown"
        if refreshed is None
        else "partial",
        omission_codes=() if complete else (cast(str, omission),),
        currency=None if usage else "USD",
        empty_means_zero=complete and not usage,
        cost_buckets=tuple(row for row in rows if isinstance(row, BudgetCostBucketV1)),
        usage_buckets=tuple(
            row for row in rows if isinstance(row, BudgetUsageBucketV1)
        ),
    )
