"""Pure request/projection shape admission; no HTTP/provider stand-ins."""

import pytest
from agentmonitor.api.v1.schemas.budgets import BudgetDimensionWireV1
from agentmonitor.api.v1.schemas.cloud_usage_actions import CloudUsageContextV1

from backend.tests.contracts.test_cloud_budget_run_contract import NOW, _context


def test_cloud_wire_defaults_to_aggregate_and_preserves_model_choice() -> None:
    context = _context()
    fields = dict(
        scope="self",
        range_key="7d",
        interval_start=context.interval_start,
        interval_end=NOW,
    )
    assert CloudUsageContextV1.model_validate(fields).grouping == []
    assert CloudUsageContextV1.model_validate(
        {**fields, "grouping": ["model"]}
    ).grouping == ["model"]
    for invalid in (["model", "model"], ["project"], "model", None):
        with pytest.raises(ValueError):
            CloudUsageContextV1.model_validate({**fields, "grouping": invalid})


def test_wire_carries_explicit_remainder_and_preserves_legacy_default() -> None:
    assert BudgetDimensionWireV1(kind="model", value=None).is_remainder is False
    assert BudgetDimensionWireV1(
        kind="model", value=None, is_remainder=True
    ).is_remainder
    for fields in (
        dict(kind="model", value="named", is_remainder=True),
        dict(kind="api_key_id", value=None, is_remainder=True),
        dict(kind="model", value=None, is_remainder=1),
    ):
        with pytest.raises(ValueError):
            BudgetDimensionWireV1.model_validate(fields)
