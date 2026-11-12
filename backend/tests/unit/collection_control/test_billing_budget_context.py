"""Pure captured billing metadata; constructed reports never enter storage."""

import json
from dataclasses import fields, replace
from datetime import timedelta

import pytest
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    budget,
    budget_dispatch,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetAuthorityV1,
    BillingBudgetReportContextV1,
    BudgetCollectionRunAdmissionV2,
)

from backend.tests.collection_control.pure.test_budget_dispatch_policy import snapshot
from backend.tests.contracts.test_budget_report_contract import _report


def authority(days: int = 30) -> BillingBudgetAuthorityV1:
    original, _ = snapshot()
    end = original.requested_at
    return BillingBudgetAuthorityV1(
        original.billing_target,
        BillingBudgetReportContextV1(
            "7d" if days == 7 else "30d",
            end - timedelta(days=days),
            end,
            "cost",
            ("project",),
        ),
    )


@pytest.mark.parametrize("days", [7, 30])
def test_context_roundtrip_preserves_exact_intent(days: int) -> None:
    original = authority(days)
    text = budget.encode_billing_budget_target(original)
    assert budget.decode_billing_budget_target(text) == original
    assert budget.decode_budget_target(text) == original
    assert (
        budget.decode_budget_target(budget.encode_billing_target(original.target))
        == original.target
    )


@pytest.mark.parametrize("corruption", ["tag", "unknown", "duplicate", "date", "range"])
def test_context_codec_rejects_noncanonical_or_changed_shape(corruption: str) -> None:
    text = budget.encode_billing_budget_target(authority())
    document = json.loads(text)
    if corruption == "tag":
        document["tag"] = "billing_budget_target.v999"
    elif corruption == "unknown":
        document["report_context"]["other"] = 1
    elif corruption == "date":
        document["report_context"]["interval_end"] = "2026-11-11T00:00:00+00:00"
    elif corruption == "range":
        document["report_context"]["range_key"] = "7d"
    else:
        text = text.replace(
            '"source_category":"cost"',
            '"source_category":"cost","source_category":"cost"',
        )
    if corruption != "duplicate":
        text = json.dumps(document, sort_keys=True, separators=(",", ":"))
    with pytest.raises(budget.BudgetCollectionError):
        budget.decode_budget_target(text)


def test_reconstruction_keeps_v2_context_and_legacy_v1() -> None:
    original, raw = snapshot()
    captured = authority()
    expected = BudgetCollectionRunAdmissionV2(
        **{field.name: getattr(original, field.name) for field in fields(original)},
        report_context=captured.report_context,
    )
    assert (
        budget_dispatch.restore_budget_admission(raw, captured, resolved_budget_limit=1)
        == expected
    )
    assert (
        budget_dispatch.restore_budget_admission(
            raw, original.billing_target, resolved_budget_limit=1
        )
        == original
    )


@pytest.mark.parametrize("change", ["period", "category", "grouping", "scope"])
def test_report_fence_rejects_context_drift(change: str) -> None:
    captured = authority()
    target, context = captured.target, captured.report_context
    period = BudgetPeriodV1(context.interval_start, context.interval_end)
    report = replace(
        _report(),
        binding_id=target.binding.binding_id,
        binding_generation=target.binding.generation,
        scope_generation=target.connection.scope_generation,
        scope_id=None,
        scope_evidence="unresolved",
        requested_period=period,
        covered_period=period,
        source_data_through=None,
        collected_at=context.interval_end,
        source_category=context.source_category,
        grouping=("project",),
        empty_means_zero=False,
    )
    budget.require_budget_report_authority(captured, report)
    if change == "period":
        period = BudgetPeriodV1(
            period.start + timedelta(days=1), period.end + timedelta(days=1)
        )
        report = replace(report, requested_period=period, covered_period=period)
    elif change == "category":
        report = replace(report, source_category="usage")
    elif change == "grouping":
        report = replace(report, grouping=())
    else:
        report = replace(report, scope_generation=2)
    with pytest.raises(
        budget.BudgetCollectionError, match="budget_commit_run_mismatch"
    ):
        budget.require_budget_report_authority(captured, report)


def test_latest_selection_requires_exact_context_but_none_remains_unfiltered() -> None:
    captured = authority()
    connection = captured.target.connection
    args = (connection.account_id, connection.resource_id, connection.scope_generation)
    assert budget.budget_target_matches_query(captured, *args)
    assert budget.budget_target_matches_query(captured, *args, captured.report_context)
    assert not budget.budget_target_matches_query(
        captured, *args, authority(7).report_context
    )
    assert not budget.budget_target_matches_query(
        captured.target, *args, captured.report_context
    )
    assert not budget.budget_target_matches_query(
        captured, *args, replace(captured.report_context, grouping=())
    )
