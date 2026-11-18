"""Pure typed model partitions only; no provider payload, transport or fixtures."""

from dataclasses import replace
from decimal import Decimal, localcontext
from typing import Any, Literal

import pytest
from agentmonitor.adapters.providers.ollama.api.policy import (
    dollars_to_money,
    request_path,
    usage_quantities,
    validate_response_context,
)
from agentmonitor.contracts.capacity_v1 import BudgetDimensionV1

from backend.tests.adapters.providers.ollama.api.test_ollama_usage_policy import (
    _request,
)


@pytest.mark.parametrize("scope", ["self", "team"])
def test_model_request_is_explicit_and_preserves_ungrouped_path(
    scope: Literal["self", "team"],
) -> None:
    request = replace(_request(), scope=scope)
    assert request_path(request) == f"/api/usage?range=7d&scope={scope}"
    grouped = replace(request, grouping=("model",))
    assert request_path(grouped) == f"/api/usage?range=7d&scope={scope}&group_by=model"
    validate_response_context(
        grouped,
        range_key="7d",
        scope=scope,
        granularity="day",
        start=grouped.period.start,
        end=grouped.requested_at,
        grouping="model",
    )
    with pytest.raises(ValueError):
        validate_response_context(
            grouped,
            range_key="7d",
            scope=scope,
            granularity="day",
            start=grouped.period.start,
            end=grouped.requested_at,
        )


@pytest.mark.parametrize(
    "grouping", [("project",), ("model", "model"), ["model"], "model"]
)
def test_unknown_duplicate_or_mutable_grouping_is_rejected(grouping: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        replace(_request(), grouping=grouping)


def metrics(requests: int, money: str | None, **tokens: int) -> Any:
    from agentmonitor.adapters.providers.ollama.api.grouping import UsageMetrics

    return UsageMetrics(
        usage_quantities(request_count=requests, **tokens),
        None if money is None else dollars_to_money(Decimal(money)),
    )


def group(name: str | None, requests: int, money: str | None, **tokens: int) -> Any:
    from agentmonitor.adapters.providers.ollama.api.grouping import ModelUsage

    dimension = BudgetDimensionV1("model", name, is_remainder=name is None)
    return ModelUsage(dimension, metrics(requests, money, **tokens))


def test_exact_partition_preserves_native_units_and_explicit_remainder() -> None:
    from agentmonitor.adapters.providers.ollama.api.grouping import (
        reconcile_model_usage,
    )

    groups = (
        group(
            "alpha",
            2,
            "12345678901234567890.123456",
            input_tokens=10,
            cached_input_tokens=4,
        ),
    )
    remainder = group(None, 1, "-0.003456", input_tokens=2, cached_input_tokens=1)
    parent = metrics(
        3, "12345678901234567890.120000", input_tokens=12, cached_input_tokens=5
    )
    with localcontext() as context:
        context.prec = 2
        result = reconcile_model_usage(parent, groups, remainder)
    assert result.money_availability == "available"
    assert result.components == (*groups, remainder)
    assert result.components[-1].dimension.is_remainder
    assert result.components[-1].dimension.value is None
    assert len(result.components) == 2  # The aggregate is not an additional row.


@pytest.mark.parametrize("field", ["requests", "money", "tokens"])
def test_native_partition_discrepancy_is_rejected_without_tolerance(field: str) -> None:
    from agentmonitor.adapters.providers.ollama.api.grouping import (
        reconcile_model_usage,
    )

    parent = metrics(
        3 if field == "requests" else 2,
        "0.000001" if field == "money" else "0",
        input_tokens=3 if field == "tokens" else 2,
    )
    with pytest.raises(ValueError, match="ollama_usage_partition_invalid"):
        reconcile_model_usage(parent, (group("alpha", 2, "0", input_tokens=2),), None)


@pytest.mark.parametrize(
    "parent,child,expected",
    [
        (None, None, "not_reported"),
        ("1", None, "partial"),
        (None, "1", "partial"),
        ("1", "1", "available"),
    ],
)
def test_missing_money_is_neither_zero_nor_full_coverage(
    parent: str | None, child: str | None, expected: str
) -> None:
    from agentmonitor.adapters.providers.ollama.api.grouping import (
        reconcile_model_usage,
    )

    result = reconcile_model_usage(
        metrics(1, parent), (group("alpha", 1, child),), None
    )
    assert result.money_availability == expected
    assert (
        result.components[0].metrics.money is None
        if child is None
        else result.components[0].metrics.money is not None
    )


def test_explicit_empty_partition_has_no_synthetic_zero_or_model_rows() -> None:
    from agentmonitor.adapters.providers.ollama.api.grouping import (
        reconcile_model_usage,
    )

    result = reconcile_model_usage(metrics(0, "0"), (), None)
    assert result.components == ()
    assert result.money_availability == "available"


def test_partial_optional_tokens_stay_absent_in_component() -> None:
    from agentmonitor.adapters.providers.ollama.api.grouping import (
        reconcile_model_usage,
    )

    result = reconcile_model_usage(
        metrics(1, None, input_tokens=8), (group("alpha", 1, None),), None
    )
    assert tuple(q.unit for q in result.components[0].metrics.quantities) == (
        "requests",
    )


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "too_many",
        "zero_requests",
        "remainder_in_groups",
        "ordinary_remainder",
    ],
)
def test_ambiguous_or_unbounded_group_sets_are_rejected(case: str) -> None:
    from agentmonitor.adapters.providers.ollama.api.grouping import (
        reconcile_model_usage,
    )

    groups: tuple[Any, ...] = (group("alpha", 1, None),)
    remainder = None
    if case == "duplicate":
        groups = groups * 2
    elif case == "too_many":
        groups = tuple(group(f"model-{i}", 1, None) for i in range(11))
    elif case == "zero_requests":
        groups = (group("alpha", 0, None),)
    elif case == "remainder_in_groups":
        groups = (group(None, 1, None),)
    else:
        remainder = group("other", 1, None)
    with pytest.raises(ValueError):
        reconcile_model_usage(metrics(len(groups), None), groups, remainder)


def test_bucket_models_are_an_ordered_subset_of_native_range_selection() -> None:
    from agentmonitor.adapters.providers.ollama.api.grouping import (
        validate_model_selection,
    )

    validate_model_selection(("alpha", "beta", "gamma"), ("alpha", "gamma"))
    validate_model_selection(("alpha",), ())
    for invalid in (("gamma", "alpha"), ("other",), ("alpha", "alpha")):
        with pytest.raises(ValueError):
            validate_model_selection(("alpha", "beta", "gamma"), invalid)


def test_empty_partition_preserves_coverage_without_claiming_retained_money() -> None:
    from agentmonitor.adapters.providers.ollama.api.grouping import (
        report_money_availability,
    )

    assert (
        report_money_availability(("available",) * 7, has_costs=False) == "not_reported"
    )
    assert report_money_availability(("available",) * 7, has_costs=True) == "available"
    assert (
        report_money_availability(("not_reported",) * 7, has_costs=False)
        == "not_reported"
    )
    assert report_money_availability(("partial",) * 7, has_costs=False) == "partial"
    assert (
        report_money_availability(("available", "not_reported"), has_costs=True)
        == "partial"
    )
