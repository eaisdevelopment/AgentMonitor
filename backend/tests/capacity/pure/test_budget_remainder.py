"""Pure normalized dimension identity; never a fabricated provider response."""

import json
from dataclasses import replace
from typing import Any

import pytest
from agentmonitor.contracts.capacity_v1 import BudgetDimensionV1, BudgetReportInputV1
from agentmonitor.modules.capacity.domain.budget_codec import (
    BudgetCodecError,
    budget_report_digest,
    decode_budget_report,
    encode_budget_report,
)

from backend.tests.capacity.pure.test_budget_codec import pure_report


def _report(dimension: BudgetDimensionV1) -> BudgetReportInputV1:
    base = pure_report()
    return replace(
        base,
        grouping=("model",),
        cost_buckets=(replace(base.cost_buckets[0], dimensions=(dimension,)),),
        usage_buckets=(),
    )


def test_explicit_remainder_is_distinct_from_unknown_model() -> None:
    unknown = _report(BudgetDimensionV1("model", None))
    remainder = _report(BudgetDimensionV1("model", None, is_remainder=True))
    assert budget_report_digest(unknown) != budget_report_digest(remainder)
    encoded = encode_budget_report(remainder)
    assert '"is_remainder":true' in encoded
    assert decode_budget_report(encoded) == remainder


def test_default_dimension_retains_legacy_encoding() -> None:
    report = _report(BudgetDimensionV1("model", "model-a"))
    encoded = encode_budget_report(report)
    assert "is_remainder" not in encoded
    assert (
        decode_budget_report(encoded).cost_buckets[0].dimensions[0].is_remainder
        is False
    )
    doc = json.loads(encoded)
    doc["cost_buckets"][0]["dimensions"][0]["is_remainder"] = False
    with pytest.raises(BudgetCodecError):
        decode_budget_report(json.dumps(doc, sort_keys=True, separators=(",", ":")))


@pytest.mark.parametrize(
    "kind,value,flag",
    [
        ("model", "named", True),
        ("api_key_id", None, True),
        ("model", None, 1),
        ("model", None, "true"),
        ("model", None, None),
    ],
)
def test_remainder_requires_explicit_boolean_and_unnamed_model(
    kind: Any, value: Any, flag: Any
) -> None:
    with pytest.raises(ValueError):
        BudgetDimensionV1(kind, value, is_remainder=flag)
