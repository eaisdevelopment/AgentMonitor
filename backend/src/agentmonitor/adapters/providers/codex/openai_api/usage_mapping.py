"""Closed A02 native-measure mapping from the 2026-11-12 official reference.

https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage

These are pure domain policies, not a provider-response parser. Token subfields
overlap their totals, so every native field keeps a distinct unit even in a
token-category view. Storage bytes remain per-bucket bytes, never byte-hours.
"""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    BudgetDimensionKindV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetUsageBucketV1,
)
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import TechnicalValueV1

UsageCategoryV1 = Literal[
    "completions",
    "embeddings",
    "moderations",
    "images",
    "audio_speeches",
    "audio_transcriptions",
    "code_interpreter_sessions",
    "vector_stores",
    "file_search_calls",
    "web_search_calls",
    "decisions",
]
GROUP_FIELDS = MappingProxyType(
    {
        "project": "project_id",
        "api_key_id": "api_key_id",
        "model": "model",
    }
)


@dataclass(frozen=True, slots=True)
class UsageCategoryMappingV1:
    """One official endpoint's finite fields; no user/content dimensions."""

    category: UsageCategoryV1
    result_object: str
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    nullable: tuple[str, ...] = ()
    groupings: tuple[BudgetDimensionKindV1, ...] = ("project", "api_key_id", "model")
    other_null_fields: tuple[str, ...] = ("user_id",)

    @property
    def token_fields(self) -> tuple[str, ...]:
        return tuple(
            name for name in self.required + self.optional if name.endswith("_tokens")
        )

    @property
    def dimension_fields(self) -> tuple[str, ...]:
        return (
            tuple(GROUP_FIELDS[name] for name in self.groupings)
            + self.other_null_fields
        )


_TOKEN_OPTIONALS = (
    "input_audio_tokens",
    "input_cache_write_12h_tokens",
    "input_cache_write_30m_tokens",
    "input_cache_write_tokens",
    "input_cached_audio_tokens",
    "input_cached_image_tokens",
    "input_cached_text_tokens",
    "input_cached_tokens",
    "input_image_tokens",
    "input_text_tokens",
    "input_uncached_tokens",
    "output_audio_tokens",
    "output_image_tokens",
    "output_text_tokens",
)
USAGE_MAPPINGS: Mapping[str, UsageCategoryMappingV1] = MappingProxyType(
    {
        item.category: item
        for item in (
            UsageCategoryMappingV1(
                "completions",
                "organization.usage.completions.result",
                ("input_tokens", "output_tokens", "num_model_requests"),
                _TOKEN_OPTIONALS,
                ("input_cache_write_30m_tokens",),
                other_null_fields=("user_id", "api_source", "batch", "service_tier"),
            ),
            UsageCategoryMappingV1(
                "embeddings",
                "organization.usage.embeddings.result",
                ("input_tokens", "num_model_requests"),
            ),
            UsageCategoryMappingV1(
                "moderations",
                "organization.usage.moderations.result",
                ("input_tokens", "num_model_requests"),
            ),
            UsageCategoryMappingV1(
                "images",
                "organization.usage.images.result",
                ("images", "num_model_requests"),
                other_null_fields=("user_id", "size", "source"),
            ),
            UsageCategoryMappingV1(
                "audio_speeches",
                "organization.usage.audio_speeches.result",
                ("characters", "num_model_requests"),
            ),
            UsageCategoryMappingV1(
                "audio_transcriptions",
                "organization.usage.audio_transcriptions.result",
                ("seconds", "num_model_requests"),
            ),
            UsageCategoryMappingV1(
                "code_interpreter_sessions",
                "organization.usage.code_interpreter_sessions.result",
                ("num_sessions",),
                groupings=("project",),
                other_null_fields=(),
            ),
            UsageCategoryMappingV1(
                "vector_stores",
                "organization.usage.vector_stores.result",
                ("usage_bytes",),
                groupings=("project",),
                other_null_fields=(),
            ),
            UsageCategoryMappingV1(
                "file_search_calls",
                "organization.usage.file_searches.result",
                ("num_requests",),
                groupings=("project", "api_key_id"),
                other_null_fields=("user_id", "vector_store_id"),
            ),
            UsageCategoryMappingV1(
                "web_search_calls",
                "organization.usage.web_searches.result",
                ("num_requests", "num_model_requests"),
                other_null_fields=("user_id", "context_level", "api_source"),
            ),
            UsageCategoryMappingV1(
                "decisions",
                "organization.usage.decisions.result",
                ("input_tokens", "output_tokens", "num_model_requests"),
                _TOKEN_OPTIONALS,
                _TOKEN_OPTIONALS,
                other_null_fields=("user_id", "api_source", "batch", "service_tier"),
            ),
        )
    }
)
_SAFE_METADATA = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


def usage_mapping(category: str) -> UsageCategoryMappingV1:
    """Unknown future categories are not silently admitted."""
    if type(category) is not str or category not in USAGE_MAPPINGS:
        raise ValueError("openai_usage_category_unsupported")
    return USAGE_MAPPINGS[category]


def validate_grouping(
    grouping: tuple[BudgetDimensionKindV1, ...],
    supported: tuple[BudgetDimensionKindV1, ...],
) -> None:
    if (
        not isinstance(grouping, tuple)
        or len(grouping) > 1
        or any(name not in supported for name in grouping)
    ):
        raise ValueError("openai_report_grouping_unsupported")


def dimensions_for_grouping(
    grouping: tuple[BudgetDimensionKindV1, ...],
    value: str | None,
) -> tuple[BudgetDimensionV1, ...]:
    """Safe bounded IDs, never credential-like material or user identities."""
    validate_grouping(grouping, ("project", "api_key_id", "model", "token_category"))
    if not grouping:
        if value is not None:
            raise ValueError("openai_report_unrequested_dimension")
        return ()
    if value is not None and (
        type(value) is not str
        or _SAFE_METADATA.fullmatch(value) is None
        or value.lower().startswith(("sk-", "sk_", "bearer"))
    ):
        raise ValueError("openai_report_dimension_invalid")
    return (BudgetDimensionV1(grouping[0], value),)


def bucket_key(
    period: BudgetPeriodV1,
    dimensions: tuple[BudgetDimensionV1, ...],
    unit: str | None = None,
) -> str:
    """Stable identity independent of row ordering, preserving old total keys."""
    key = "daily_" + period.start.strftime("%Y%m%d")
    if dimensions or unit is not None:
        identity = json.dumps(
            [unit, [(item.kind, item.value) for item in dimensions]],
            separators=(",", ":"),
            ensure_ascii=True,
        )
        key += "_" + hashlib.sha256(identity.encode("ascii")).hexdigest()
    return key


@dataclass(frozen=True, slots=True)
class OpenAIUsageMeasuresV1(TechnicalValueV1):
    """Native normalized integer counts; absence is distinct from reported zero."""

    category: UsageCategoryV1
    quantities: tuple[ExactQuantityV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        mapping = usage_mapping(self.category)
        if not isinstance(self.quantities, tuple) or any(
            not isinstance(item, ExactQuantityV1) for item in self.quantities
        ):
            raise ValueError("openai_usage_quantities_invalid")
        units = tuple(item.unit for item in self.quantities)
        if (
            units != tuple(sorted(set(units)))
            or not set(mapping.required) <= set(units)
            or set(units) - set(mapping.required + mapping.optional)
            or any(
                item.amount.scale != 0 or not 0 <= int(item.amount.coefficient) < 10**20
                for item in self.quantities
            )
        ):
            raise ValueError("openai_usage_quantities_invalid")


def usage_buckets(
    period: BudgetPeriodV1,
    measures: OpenAIUsageMeasuresV1,
    dimensions: tuple[BudgetDimensionV1, ...],
    *,
    token_categories: bool = False,
) -> tuple[BudgetUsageBucketV1, ...]:
    """Keep overlapping token measures distinct; never manufacture a subtotal."""
    mapping = usage_mapping(measures.category)
    validate_grouping(tuple(item.kind for item in dimensions), mapping.groupings)
    for dimension in dimensions:
        dimensions_for_grouping((dimension.kind,), dimension.value)
    if token_categories and (dimensions or not mapping.token_fields):
        raise ValueError("openai_report_grouping_unsupported")
    rows = []
    for quantity in measures.quantities:
        if token_categories and quantity.unit not in mapping.token_fields:
            continue
        selected = (
            dimensions_for_grouping(("token_category",), quantity.unit)
            if token_categories
            else dimensions
        )
        rows.append(
            BudgetUsageBucketV1(
                bucket_key(period, selected, quantity.unit),
                period,
                quantity,
                selected,
            )
        )
    return tuple(rows)
