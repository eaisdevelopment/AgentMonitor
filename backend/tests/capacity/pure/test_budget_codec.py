"""Constructed normalized reports stay entirely inside pure codec policy."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.capacity_v1 import (
    BudgetCostBucketV1,
    BudgetDimensionV1,
    BudgetPeriodV1,
    BudgetReportInputV1,
    BudgetUsageBucketV1,
    CapacitySubjectV2,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactMoneyV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1
from agentmonitor.modules.capacity.domain.budget_codec import (
    BudgetCodecError,
    budget_report_digest,
    decode_budget_report,
    encode_budget_report,
)


def pure_report() -> BudgetReportInputV1:
    start = datetime(2026, 11, 1, tzinfo=UTC)
    period = BudgetPeriodV1(start, start + timedelta(days=7))
    dimensions = (BudgetDimensionV1("cost_type", "adjustment"),)
    return BudgetReportInputV1(
        CapacitySubjectV2(
            "claude",
            ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32)),
            OpaqueIdV1("pure-account"),
            OpaqueIdV1("pure-resource"),
        ),
        OpaqueIdV1("pure-binding"),
        1,
        2,
        None,
        "unresolved",
        "pure-cost",
        "costs",
        "reported_cost",
        ("cost_type",),
        period,
        period,
        None,
        period.end,
        "complete",
        (),
        "USD",
        False,
        (
            BudgetCostBucketV1(
                "adjustment",
                period,
                ExactMoneyV1(CanonicalDecimalV1("-123456789012345678901", 18), "USD"),
                dimensions,
                "adjustment",
            ),
        ),
        (
            BudgetUsageBucketV1(
                "requests",
                period,
                ExactQuantityV1(CanonicalDecimalV1("123", 0), "requests"),
                dimensions,
            ),
        ),
    )


def test_roundtrip_exact_signed_money_usage_and_utc() -> None:
    report = pure_report()
    encoded = encode_budget_report(report)
    assert decode_budget_report(encoded) == report
    assert '"coefficient":"-123456789012345678901"' in encoded
    assert '"scale":18' in encoded
    assert "2026-11-01T00:00:00.000000Z" in encoded
    assert len(budget_report_digest(report)) == 64
    assert budget_report_digest(report) != budget_report_digest(
        replace(report, binding_generation=2)
    )


def test_empty_coverage_roundtrips_without_invented_facts() -> None:
    report = replace(pure_report(), cost_buckets=(), usage_buckets=(), currency=None)
    assert decode_budget_report(encode_budget_report(report)) == report


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown",
        "duplicate",
        "float",
        "noncanonical",
        "wrong_enum",
        "bad_decimal",
        "oversize",
    ],
)
def test_decoder_rejects_ambiguous_or_unbounded_json(mutation: str) -> None:
    encoded = encode_budget_report(pure_report())
    if mutation == "unknown":
        encoded = encoded[:-1] + ',"raw_provider_body":"forbidden"}'
    elif mutation == "duplicate":
        encoded = encoded[:-1] + ',"binding_generation":1}'
    elif mutation == "float":
        encoded = encoded.replace('"scale":18', '"scale":18.0')
    elif mutation == "noncanonical":
        encoded = json.dumps(json.loads(encoded), indent=2)
    elif mutation == "wrong_enum":
        encoded = encoded.replace('"unresolved"', '"made_up"')
    elif mutation == "bad_decimal":
        encoded = encoded.replace('"scale":18', '"scale":19')
    else:
        encoded = " " * (16 * 1024 * 1024 + 1)
    with pytest.raises(BudgetCodecError):
        decode_budget_report(encoded)
