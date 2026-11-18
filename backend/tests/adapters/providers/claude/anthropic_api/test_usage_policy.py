"""Constructed normalized counts only: pure policies, never provider payloads."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    AnthropicCostRequestV1,
    AnthropicUsageRequestV1,
    completed_week,
    request_path,
)
from agentmonitor.adapters.providers.claude.anthropic_api.usage_policy import (
    AnthropicUsageMeasuresV1,
    bucket_key,
    build_analytics_report,
    dimensions_for_grouping,
    usage_buckets,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetDimensionKindV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    ProviderTargetRefV1,
)


def request() -> AnthropicCostRequestV1:
    instant = datetime(2026, 11, 11, tzinfo=UTC)
    account = OpaqueIdV1("pure-account")
    return AnthropicCostRequestV1(
        CapacitySubjectV2(
            "claude",
            ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32)),
            account,
            OpaqueIdV1("pure-resource"),
        ),
        ActiveCredentialBindingRefV1(account, OpaqueIdV1("amcb_" + "b" * 32), 1),
        None,
        "unresolved",
        1,
        completed_week(instant),
        instant,
    )


def measures() -> AnthropicUsageMeasuresV1:
    return AnthropicUsageMeasuresV1(1, 2, 3, 4, 5, 15, None, 0)


def period() -> BudgetPeriodV1:
    start = datetime(2026, 11, 9, tzinfo=UTC)
    return BudgetPeriodV1(start, start + timedelta(days=1))


def test_usage_query_selects_usage_path_and_only_one_supported_dimension() -> None:
    cost = request()
    value = AnthropicUsageRequestV1(
        cost.subject,
        cost.binding,
        cost.scope_id,
        cost.scope_evidence,
        cost.scope_generation,
        cost.period,
        cost.requested_at,
    )
    assert request_path(value, None).startswith("/v1/organizations/analytics/usage?")
    assert "group_by%5B%5D=model" in request_path(
        replace(value, grouping=("model",)), None
    )
    # Tokens are native measures on usage, not a server-supported grouping.
    assert "group_by" not in request_path(
        replace(value, grouping=("token_category",)), None
    )


def test_native_usage_units_never_double_count_total_or_invent_missing_requests() -> (
    None
):
    rows = usage_buckets(period(), measures(), ())
    facts = {row.quantity.unit: int(row.quantity.amount.coefficient) for row in rows}
    assert facts == {
        "uncached_input_tokens": 1,
        "cache_read_input_tokens": 2,
        "output_tokens": 3,
        "cache_creation.ephemeral_1h_input_tokens": 4,
        "cache_creation.ephemeral_5m_input_tokens": 5,
        "total_tokens": 15,
        "web_search_requests": 0,
    }
    assert len({row.bucket_key for row in rows}) == len(rows)
    with_requests = usage_buckets(period(), replace(measures(), requests=0), ())
    assert len(with_requests) == len(rows) + 1


def test_token_projection_has_five_disjoint_categories_without_total_or_requests() -> (
    None
):
    rows = usage_buckets(period(), measures(), (), token_categories=True)
    assert len(rows) == 5
    assert all(row.quantity.unit == "tokens" for row in rows)
    assert all(row.dimensions[0].kind == "token_category" for row in rows)
    assert sum(int(row.quantity.amount.coefficient) for row in rows) == 15
    assert {row.dimensions[0].value for row in rows} == {
        "uncached_input_tokens",
        "cache_read_input_tokens",
        "output_tokens",
        "cache_creation.ephemeral_1h_input_tokens",
        "cache_creation.ephemeral_5m_input_tokens",
    }


@pytest.mark.parametrize("count", [-1, True, 1.5, 10**20])
def test_usage_measures_reject_nonintegral_negative_or_oversized_counts(
    count: object,
) -> None:
    with pytest.raises(ValueError):
        # Deliberately violate the static type to exercise domain admission.
        replace(measures(), output_tokens=cast(int, count))


def test_dimensions_preserve_source_null_without_guessing_other() -> None:
    assert dimensions_for_grouping(("model",), None) == (
        BudgetDimensionV1("model", None),
    )
    assert dimensions_for_grouping(("api_key_id",), "apikey_public-id") == (
        BudgetDimensionV1("api_key_id", "apikey_public-id"),
    )
    with pytest.raises(ValueError):
        dimensions_for_grouping(("api_key_id",), "sk-not-a-safe-identifier")
    with pytest.raises(ValueError):
        dimensions_for_grouping(("workspace",), "a@example.invalid")


def test_grouped_keys_keep_null_distinct_and_preserve_total_identity() -> None:
    assert bucket_key(period(), ()) == "daily_20261109"
    null = dimensions_for_grouping(("model",), None)
    literal = dimensions_for_grouping(("model",), "null")
    assert bucket_key(period(), null) != bucket_key(period(), literal)
    assert bucket_key(period(), null) == bucket_key(period(), null)


@pytest.mark.parametrize(
    "grouping", [("actor",), ("model", "workspace"), ("model", "model")]
)
def test_unapproved_dimensions_and_cross_products_are_rejected(
    grouping: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError):
        # Runtime validation must also reject unknown dimension strings.
        replace(request(), grouping=cast(tuple[BudgetDimensionKindV1, ...], grouping))


def test_cost_report_cannot_accept_usage_rows_under_monetary_provenance() -> None:
    selected = request()
    rows = list(usage_buckets(period(), measures(), ()))
    with pytest.raises(ValueError, match="anthropic_analytics_row_category_invalid"):
        build_analytics_report(
            selected,
            rows,
            selected.period.end,
            None,
            selected.requested_at,
        )


@pytest.mark.parametrize("days", [7, 30])
def test_usage_report_preserves_complete_coverage_without_claiming_money(
    days: int,
) -> None:
    selected = request()
    interval = BudgetPeriodV1(
        selected.period.end - timedelta(days=days), selected.period.end
    )
    usage = AnthropicUsageRequestV1(
        selected.subject,
        selected.binding,
        selected.scope_id,
        selected.scope_evidence,
        selected.scope_generation,
        interval,
        selected.requested_at,
    )
    report = build_analytics_report(
        usage, [], interval.end, None, selected.requested_at
    )
    assert report.source_id == "anthropic.analytics.usage.v1"
    assert report.source_category == "usage"
    assert report.currency is None
    assert report.cost_basis == "not_applicable"
    assert not report.empty_means_zero
    assert report.covered_period == interval
    assert report.completeness == "complete"
    assert not report.cost_buckets and not report.usage_buckets


def test_missing_or_lagging_watermark_never_claims_complete_coverage() -> None:
    selected = request()
    for refreshed, completeness, reason in (
        (None, "unknown", "provider_data_not_ready"),
        (selected.period.start, "partial", "provider_data_delayed"),
    ):
        report = build_analytics_report(
            selected, [], refreshed, None, selected.requested_at
        )
        assert report.completeness == completeness
        assert report.covered_period is None
        assert not report.empty_means_zero
        assert report.omission_codes == (reason,)


def test_token_cost_projection_cannot_be_confused_with_complete_cost_total() -> None:
    selected = replace(request(), grouping=("token_category",))
    report = build_analytics_report(
        selected, [], selected.period.end, None, selected.requested_at
    )
    assert report.source_id == "anthropic.analytics.cost.v1"
    assert report.source_category == "cost_tokens"
    assert report.grouping == ("token_category",)
    assert report.cost_basis == "discounted_before_credits"
