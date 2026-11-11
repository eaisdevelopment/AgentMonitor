"""Pure current-report selection query limits; no provider or storage fixtures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts import capacity_v1 as contracts
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_current_query_requires_one_real_scope_and_bounded_contexts() -> None:
    now = datetime(2026, 11, 11, tzinfo=UTC)
    query = contracts.BudgetCurrentQueryV1(
        account_id=OpaqueIdV1("account"),
        resource_id=OpaqueIdV1("resource"),
        scope_generation=1,
        period=contracts.BudgetPeriodV1(now - timedelta(days=7), now),
        as_of=now,
        limit=200,
    )
    for change in (
        {"limit": 0},
        {"limit": 201},
        {"limit": True},
        {"scope_generation": 0},
        {"scope_generation": True},
    ):
        with pytest.raises(ValueError, match="budget_current_query_invalid"):
            replace(query, **change)


def test_unresolved_current_query_captures_exact_active_binding() -> None:
    from dataclasses import fields

    from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1

    assert "active_binding" in {
        f.name for f in fields(contracts.BudgetCurrentQueryV1)
    }, "current budget query cannot select the active unresolved lineage"
    now = datetime(2026, 11, 11, tzinfo=UTC)
    binding = ActiveCredentialBindingRefV1(
        OpaqueIdV1("account"), OpaqueIdV1("amcb_" + "a" * 32), 2
    )
    query = contracts.BudgetCurrentQueryV1(
        OpaqueIdV1("account"),
        OpaqueIdV1("resource"),
        1,
        contracts.BudgetPeriodV1(now - timedelta(days=7), now),
        now,
        active_binding=binding,
    )
    assert query.active_binding == binding
    assert replace(query, active_binding=None).active_binding is None
    with pytest.raises(ValueError, match="budget_current_query_invalid"):
        replace(query, active_binding=replace(binding, account_id=OpaqueIdV1("other")))
