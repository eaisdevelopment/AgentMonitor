"""Pure captured intent: UTC coverage and bounded source selectors, without I/O."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts import collection_control_v1 as contracts

from backend.tests.contracts.test_budget_run_contract import _admission


@pytest.mark.parametrize("days", [7, 30])
def test_billing_context_preserves_exact_selected_interval(days: int) -> None:
    end = datetime(2026, 10, 1, tzinfo=UTC)
    context = contracts.BillingBudgetReportContextV1(
        "7d" if days == 7 else "30d",
        end - timedelta(days=days),
        end,
        "cost",
        ("project",),
    )
    assert context.interval_end == end
    assert context.interval_start == end - timedelta(days=days)
    assert context.source_category == "cost"
    assert context.grouping == ("project",)


@pytest.mark.parametrize(
    "case", ["duration", "midnight", "category", "grouping", "too_many"]
)
def test_billing_context_rejects_ambiguous_or_unbounded_selectors(case: str) -> None:
    end = datetime(2026, 10, 1, tzinfo=UTC)
    start = end - timedelta(days=7)
    category = "cost"
    grouping: tuple[str, ...] = ()
    if case == "duration":
        start -= timedelta(days=1)
    elif case == "midnight":
        start += timedelta(hours=1)
        end += timedelta(hours=1)
    elif case == "category":
        category = "cost?query=other"
    elif case == "grouping":
        grouping = ("model/value",)
    else:
        grouping = ("model", "project")
    with pytest.raises(ValueError, match="billing_budget_context_invalid"):
        contracts.BillingBudgetReportContextV1("7d", start, end, category, grouping)


def test_context_admission_keeps_legacy_target_and_request_time() -> None:
    old = _admission()
    end = old.requested_at - timedelta(days=1)
    context = contracts.BillingBudgetReportContextV1(
        "30d",
        end - timedelta(days=30),
        end,
        "cost",
    )
    admission = contracts.BudgetCollectionRunAdmissionV2(
        **{field.name: getattr(old, field.name) for field in fields(old)},
        report_context=context,
    )
    authority = contracts.BillingBudgetAuthorityV1(old.billing_target, context)
    assert isinstance(admission, contracts.BudgetCollectionRunAdmissionV1)
    assert admission.requested_at == old.requested_at
    assert admission.billing_target == authority.target == old.billing_target
    assert admission.report_context == authority.report_context == context


def test_context_admission_rejects_uncompleted_future_interval() -> None:
    old = _admission()
    end = old.requested_at + timedelta(days=1)
    context = contracts.BillingBudgetReportContextV1(
        "7d",
        end - timedelta(days=7),
        end,
        "cost",
    )
    with pytest.raises(ValueError, match="billing_budget_admission_invalid"):
        contracts.BudgetCollectionRunAdmissionV2(
            **{field.name: getattr(old, field.name) for field in fields(old)},
            report_context=context,
        )
