"""Pure funds identity, chronology and exact-money contract invariants."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from agentmonitor.contracts import budget_query_v1 as budget
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    CapacitySubjectV2,
    ExactMoneyFieldV1,
)
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1, ExactMoneyV1
from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    QueryAvailabilityV1,
)
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

from backend.tests.capacity.pure.test_alert_conditions import _window

NOW = datetime(2026, 11, 11, tzinfo=UTC)


def _component() -> budget.BudgetFundComponentV1:
    money = ExactMoneyFieldV1(
        FieldAvailabilityV1("available"),
        ExactMoneyV1(CanonicalDecimalV1.from_decimal(Decimal("0.004")), "USD"),
        "exact",
        "high",
        "provider_reported",
        None,
    )
    return budget.BudgetFundComponentV1(
        subject=CapacitySubjectV2(
            "ollama",
            ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32)),
            OpaqueIdV1("account"),
            OpaqueIdV1("resource"),
        ),
        component_id=OpaqueIdV1("window"),
        kind="included_credits",
        remaining=money,
        limit=replace(
            money,
            value=ExactMoneyV1(CanonicalDecimalV1.from_decimal(Decimal("100")), "USD"),
        ),
        period=None,
        renewal_at=None,
        expires_at=None,
        is_constraining=False,
        scope_evidence="unresolved",
        observation_id=OpaqueIdV1("observation"),
        collection_run_id=OpaqueIdV1("run"),
        observed_at=NOW,
        collected_at=NOW,
        stored_at=NOW,
        freshness="fresh",
        completeness="partial",
        provenance=_window().provenance,
    )


def test_funds_exist_without_spend_or_a_billing_connection() -> None:
    item = _component()
    funds = budget.AccountBudgetFundsV1(
        OpaqueIdV1("account"),
        NOW,
        QueryAvailabilityV1("partial", "funds_scope_unresolved", NOW),
        (item,),
        1,
    )
    result = budget.AccountBudgetCurrentV1(
        funds.account_id,
        BudgetPeriodV1(NOW - timedelta(days=7), NOW),
        NOW,
        QueryAvailabilityV1("available", "budget_account_read", NOW),
        (),
        funds,
    )
    assert result.resources == ()
    assert result.funds is not None
    assert result.funds.components[0].remaining.value is not None
    assert result.funds.components[0].remaining.value.amount.as_decimal() == Decimal(
        "0.004"
    )
    assert not result.funds.components[0].is_constraining
    with pytest.raises(ValueError, match="budget_account_query_invalid"):
        replace(result, account_id=OpaqueIdV1("different"))


def test_funds_reject_other_account_duplicates_and_future_readings() -> None:
    funds = budget.AccountBudgetFundsV1(
        OpaqueIdV1("account"),
        NOW,
        QueryAvailabilityV1("partial", "funds_scope_unresolved", NOW),
        (_component(),),
        1,
    )
    for changes in (
        {"account_id": OpaqueIdV1("different")},
        {"components": funds.components * 2},
        {"as_of": NOW - timedelta(seconds=1)},
        {"registry_revision": -1},
        {"components": (replace(_component(), stored_at=NOW + timedelta(seconds=1)),)},
    ):
        with pytest.raises(ValueError, match="budget_funds_query_invalid"):
            replace(funds, **changes)


def test_funds_do_not_mix_currencies_or_reverse_observation_order() -> None:
    item = _component()
    with pytest.raises(ValueError, match="budget_fund_component_invalid"):
        replace(
            item,
            limit=replace(
                item.limit,
                value=ExactMoneyV1(
                    CanonicalDecimalV1.from_decimal(Decimal("100")), "GBP"
                ),
            ),
        )
    with pytest.raises(ValueError, match="budget_fund_component_invalid"):
        replace(item, observed_at=NOW + timedelta(seconds=1))
