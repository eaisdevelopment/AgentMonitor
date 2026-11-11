"""Pure wire projection of cloud metadata; no service or provider fixtures."""

from agentmonitor.api.v1.routers.budgets import account_wire
from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentV1,
    BudgetCloudResourceCurrentV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.common_v1 import QueryAvailabilityV1

from backend.tests.contracts.test_cloud_budget_run_contract import NOW, _context, _graph


def test_cloud_resource_projects_without_exposing_binding_or_faking_enrollment() -> (
    None
):
    graph = _graph()
    context = _context()
    availability = QueryAvailabilityV1("available", "budget_account_read", NOW)
    value = AccountBudgetCurrentV1(
        graph.account_id,
        BudgetPeriodV1(context.interval_start, context.interval_end),
        NOW,
        availability,
        (),
        cloud_resources=(
            BudgetCloudResourceCurrentV1(
                graph, (), availability, (), None, availability
            ),
        ),
    )
    wire = account_wire(value)
    assert wire.resources == []
    assert len(wire.cloud_resources) == 1
    projected = wire.cloud_resources[0]
    assert projected.account_id == graph.account_id.value
    assert projected.resource_id == graph.resource_id.value
    serialized = projected.model_dump_json()
    assert graph.binding.binding_id.value not in serialized
    assert "connection" not in projected.model_dump()
