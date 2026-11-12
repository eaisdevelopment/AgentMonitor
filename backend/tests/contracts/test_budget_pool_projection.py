"""Pure additive financial-pool projection shape, with no I/O collaborators."""

from dataclasses import fields

from agentmonitor.contracts.budget_query_v1 import (
    BudgetOverviewContextV1,
    BudgetOverviewFundV1,
    BudgetOverviewRowV1,
)


def test_pool_rows_retain_owner_attribution_and_access_paths() -> None:
    names = {field.name for field in fields(BudgetOverviewRowV1)}
    assert {
        "pool_id",
        "pool_name",
        "pool_selector",
        "primary_organization_id",
        "association_evidence",
        "counted_in_selection",
        "access_paths",
    } <= names, "budget_pool_projection_missing"


def test_shared_readings_retain_actual_authorized_link_owners() -> None:
    assert {"report_account_id", "report_resource_id"} <= {
        field.name for field in fields(BudgetOverviewContextV1)
    }, "budget_pool_report_link_missing"
    assert {"source_account_id", "source_resource_id"} <= {
        field.name for field in fields(BudgetOverviewFundV1)
    }, "budget_pool_funds_link_missing"
