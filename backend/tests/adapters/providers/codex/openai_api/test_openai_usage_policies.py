"""M7 T008: pure request/count policies, no provider responses or I/O substitutes."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest
from agentmonitor.adapters.providers.codex.openai_api.policy import (
    OpenAIUsageRequestV1,
    request_path,
)
from agentmonitor.adapters.providers.codex.openai_api.source import _report
from agentmonitor.adapters.providers.codex.openai_api.usage_mapping import (
    OpenAIUsageMeasuresV1,
    UsageCategoryV1,
    bucket_key,
    dimensions_for_grouping,
    usage_buckets,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetDimensionKindV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
)
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1

from backend.tests.adapters.providers.codex.openai_api import (
    test_openai_cost_request_policy as request_policy,
)

request = request_policy.request

CASES = (
    ("completions", ("input_tokens", "num_model_requests", "output_tokens")),
    ("embeddings", ("input_tokens", "num_model_requests")),
    ("moderations", ("input_tokens", "num_model_requests")),
    ("images", ("images", "num_model_requests")),
    ("audio_speeches", ("characters", "num_model_requests")),
    ("audio_transcriptions", ("num_model_requests", "seconds")),
    ("code_interpreter_sessions", ("num_sessions",)),
    ("vector_stores", ("usage_bytes",)),
    ("file_search_calls", ("num_requests",)),
    ("web_search_calls", ("num_model_requests", "num_requests")),
    ("decisions", ("input_tokens", "num_model_requests", "output_tokens")),
)


def usage_request(category: UsageCategoryV1, days: int = 7) -> OpenAIUsageRequestV1:
    cost = request(days)
    return OpenAIUsageRequestV1(
        cost.subject,
        cost.binding,
        cost.scope_id,
        cost.scope_evidence,
        cost.scope_generation,
        cost.period,
        cost.requested_at,
        category=category,
    )


def quantities(*units: str, value: Decimal = Decimal(3)) -> tuple[ExactQuantityV1, ...]:
    return tuple(
        ExactQuantityV1.from_decimal(value, unit=unit) for unit in sorted(units)
    )


def daily_period() -> BudgetPeriodV1:
    start = request().period.start
    return BudgetPeriodV1(start, start + timedelta(days=1))


@pytest.mark.parametrize("category,units", CASES)
@pytest.mark.parametrize("days", [7, 30])
def test_each_usage_endpoint_preserves_its_native_units_and_interval(
    category: UsageCategoryV1,
    units: tuple[str, ...],
    days: int,
) -> None:
    selected = usage_request(category, days)
    path = urlsplit(request_path(selected, "cursor/+?=&"))
    assert path.path == "/v1/organization/usage/" + category
    query = parse_qs(path.query)
    assert query["bucket_width"] == ["1d"]
    assert query["limit"] == [str(days)]
    assert query["start_time"] == [str(int(selected.period.start.timestamp()))]
    assert query["end_time"] == [str(int(selected.period.end.timestamp()))]
    assert query["page"] == ["cursor/+?=&"]
    assert "group_by" not in query
    facts = OpenAIUsageMeasuresV1(category, quantities(*units))
    rows = usage_buckets(daily_period(), facts, ())
    assert {row.quantity.unit for row in rows} == set(units)
    assert all(row.quantity.amount.as_decimal() == 3 for row in rows)
    assert len({row.bucket_key for row in rows}) == len(rows)
    for omit in units:
        with pytest.raises(ValueError):
            OpenAIUsageMeasuresV1(
                category, tuple(item for item in facts.quantities if item.unit != omit)
            )


@pytest.mark.parametrize("category", ["completions", "decisions"])
def test_overlapping_tokens_remain_separate_without_pricing_or_subtraction(
    category: UsageCategoryV1,
) -> None:
    facts = OpenAIUsageMeasuresV1(
        category,
        tuple(
            sorted(
                (
                    ExactQuantityV1.from_decimal(Decimal(100), unit="input_tokens"),
                    ExactQuantityV1.from_decimal(
                        Decimal(80), unit="input_cached_tokens"
                    ),
                    ExactQuantityV1.from_decimal(
                        Decimal(40), unit="input_cache_write_tokens"
                    ),
                    ExactQuantityV1.from_decimal(Decimal(7), unit="output_tokens"),
                    ExactQuantityV1.from_decimal(Decimal(1), unit="num_model_requests"),
                ),
                key=lambda item: item.unit,
            )
        ),
    )
    rows = usage_buckets(daily_period(), facts, (), token_categories=True)
    assert {row.quantity.unit: row.quantity.as_decimal() for row in rows} == {
        "input_tokens": 100,
        "input_cached_tokens": 80,
        "input_cache_write_tokens": 40,
        "output_tokens": 7,
    }
    assert all(
        row.dimensions == (BudgetDimensionV1("token_category", row.quantity.unit),)
        for row in rows
    )
    assert "group_by" not in request_path(
        replace(usage_request(category), grouping=("token_category",)), None
    )


def test_absent_optional_measure_is_not_a_reported_zero() -> None:
    basic = OpenAIUsageMeasuresV1(
        "completions", quantities("input_tokens", "num_model_requests", "output_tokens")
    )
    assert "input_cached_tokens" not in {
        row.quantity.unit for row in usage_buckets(daily_period(), basic, ())
    }
    observed_zero = replace(
        basic,
        quantities=tuple(
            sorted(
                basic.quantities + quantities("input_cached_tokens", value=Decimal(0)),
                key=lambda item: item.unit,
            )
        ),
    )
    assert len(usage_buckets(daily_period(), observed_zero, ())) == 4


@pytest.mark.parametrize(
    "category",
    [
        "completions",
        "decisions",
        "embeddings",
        "moderations",
        "images",
        "audio_speeches",
        "audio_transcriptions",
        "web_search_calls",
    ],
)
def test_supported_project_key_and_model_select_one_safe_dimension(
    category: UsageCategoryV1,
) -> None:
    selected = usage_request(category)
    pairs: tuple[tuple[BudgetDimensionKindV1, str], ...] = (
        ("project", "project_id"),
        ("api_key_id", "api_key_id"),
        ("model", "model"),
    )
    for dimension, field in pairs:
        query = parse_qs(
            urlsplit(request_path(replace(selected, grouping=(dimension,)), None)).query
        )
        assert query["group_by[]"] == [field]
        assert "group_by" not in query


@pytest.mark.parametrize("category", ["embeddings", "moderations"])
def test_input_only_token_category_excludes_model_request_count(
    category: UsageCategoryV1,
) -> None:
    facts = OpenAIUsageMeasuresV1(
        category, quantities("input_tokens", "num_model_requests")
    )
    selected = replace(usage_request(category), grouping=("token_category",))
    rows = usage_buckets(daily_period(), facts, (), token_categories=True)
    assert len(rows) == 1
    assert rows[0].quantity.unit == "input_tokens"
    assert rows[0].dimensions == (BudgetDimensionV1("token_category", "input_tokens"),)
    assert "group_by" not in request_path(selected, None)


@pytest.mark.parametrize("value", [Decimal(-1), Decimal("0.5"), Decimal(10) ** 20])
def test_usage_counts_reject_negative_fractional_and_unbounded_amounts(
    value: Decimal,
) -> None:
    with pytest.raises(ValueError):
        OpenAIUsageMeasuresV1("vector_stores", quantities("usage_bytes", value=value))


def test_project_only_source_cannot_publish_model_dimensions() -> None:
    facts = OpenAIUsageMeasuresV1("vector_stores", quantities("usage_bytes"))
    with pytest.raises(ValueError, match="openai_report_grouping_unsupported"):
        usage_buckets(
            daily_period(), facts, (BudgetDimensionV1("model", "pure-model"),)
        )


@pytest.mark.parametrize("category", ["vector_stores", "code_interpreter_sessions"])
def test_project_only_endpoints_refuse_key_model_and_token_dimensions(
    category: UsageCategoryV1,
) -> None:
    selected = usage_request(category)
    assert parse_qs(
        urlsplit(request_path(replace(selected, grouping=("project",)), None)).query
    )["group_by[]"] == ["project_id"]
    for dimension in ("api_key_id", "model", "token_category"):
        with pytest.raises(ValueError):
            replace(selected, grouping=(dimension,))


def test_file_search_supports_project_and_key_but_not_model_or_tokens() -> None:
    selected = usage_request("file_search_calls")
    assert parse_qs(
        urlsplit(request_path(replace(selected, grouping=("api_key_id",)), None)).query
    )["group_by[]"] == ["api_key_id"]
    for dimension in ("model", "token_category"):
        with pytest.raises(ValueError):
            replace(selected, grouping=(dimension,))


def test_cost_model_and_token_views_are_not_inferred_from_line_items() -> None:
    for dimension in ("model", "token_category", "line_item"):
        with pytest.raises(ValueError):
            replace(request(), grouping=(dimension,))


def test_unknown_category_and_dimension_products_are_refused() -> None:
    with pytest.raises(ValueError):
        usage_request(cast(UsageCategoryV1, "unknown_future_category"))
    with pytest.raises(ValueError):
        replace(usage_request("completions"), grouping=("project", "model"))


def test_safe_identifier_null_is_not_a_synthetic_other_bucket_or_credential() -> None:
    null = dimensions_for_grouping(("api_key_id",), None)
    named = dimensions_for_grouping(("api_key_id",), "null")
    assert null == (BudgetDimensionV1("api_key_id", None),)
    assert bucket_key(daily_period(), null) != bucket_key(daily_period(), named)
    assert bucket_key(daily_period(), ()) == "daily_20261104"
    for unsafe in (
        "sk-proj-not-a-public-id",
        "user@example.invalid",
        "two words",
        "x" * 129,
    ):
        with pytest.raises(ValueError):
            dimensions_for_grouping(("api_key_id",), unsafe)


@pytest.mark.parametrize("category,units", CASES)
def test_usage_empty_coverage_has_no_monetary_zero_or_invented_watermark(
    category: UsageCategoryV1,
    units: tuple[str, ...],
) -> None:
    selected = usage_request(category)
    report = _report(selected, [], set(), set(), collected_at=selected.requested_at)
    assert report.source_id == "openai.organization.usage.v1"
    assert report.source_category == "usage_" + category
    assert report.completeness == "complete"
    assert report.covered_period == selected.period
    assert report.currency is None and report.source_data_through is None
    assert report.cost_basis == "not_applicable" and not report.empty_means_zero
    assert not report.cost_buckets and not report.usage_buckets


def test_partial_usage_and_pagination_failure_cannot_claim_full_coverage() -> None:
    selected = usage_request("completions")
    for starts, omissions in (
        ({selected.period.start}, set()),
        (set(), {"page_budget_exceeded"}),
    ):
        report = _report(
            selected, [], starts, omissions, collected_at=selected.requested_at
        )
        assert report.completeness == "partial"
        assert report.covered_period is None and report.omission_codes
        assert not report.empty_means_zero and report.currency is None


def test_usage_rows_cannot_cross_into_cost_source_provenance() -> None:
    facts = OpenAIUsageMeasuresV1("vector_stores", quantities("usage_bytes"))
    rows = usage_buckets(daily_period(), facts, ())
    selected = request()
    with pytest.raises(ValueError, match="openai_report_row_category_invalid"):
        _report(
            selected,
            rows,
            {selected.period.start},
            set(),
            collected_at=selected.requested_at,
        )
