"""Sort the full canonical inventory before paging; pure values only."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Literal, TypedDict, cast

import pytest
from agentmonitor.contracts.budget_query_v1 import BudgetOverviewQueryV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_overview import (
    overview_result,
    project_budget_rows,
)

from backend.tests.capacity.pure.test_budget_overview import (
    NOW,
    PERIOD,
    _account,
    _current,
    _resource,
)


class _Options(TypedDict):
    registry_revision: int
    inventory_count: int
    subscription_account_ids: tuple[OpaqueIdV1, ...]
    organization_labels: Mapping[OpaqueIdV1, str | None]


@pytest.mark.parametrize("sort_by", ("account", "organization", "state"))
@pytest.mark.parametrize("direction", ("ascending", "descending"))
def test_first_page_comes_from_full_sorted_inventory(
    sort_by: Literal["account", "organization", "state"],
    direction: Literal["ascending", "descending"],
) -> None:
    query = BudgetOverviewQueryV1(
        PERIOD, NOW, limit=1, sort_by=sort_by, sort_direction=direction
    )
    row = project_budget_rows(_account(), (_resource(),), _current(), query)[0]
    first = replace(
        row,
        row_id="a" * 64,
        state_rank=1,
        account=replace(
            _account(1), friendly_name="Zulu", organization_id=OpaqueIdV1("z")
        ),
        pool_id=OpaqueIdV1("shared-pool"),
        pool_name="Alpha",
        primary_organization_id=OpaqueIdV1("a"),
    )
    last = replace(
        row,
        row_id="b" * 64,
        state_rank=3,
        account=replace(
            _account(2), friendly_name="Bravo", organization_id=OpaqueIdV1("b")
        ),
    )
    labels = {
        OpaqueIdV1("z"): "Zulu",
        OpaqueIdV1("a"): "Alpha",
        OpaqueIdV1("b"): "Bravo",
    }
    kwargs: _Options = dict(
        registry_revision=1,
        inventory_count=2,
        subscription_account_ids=(),
        organization_labels=labels,
    )
    result = overview_result((last, first), query, **kwargs)
    assert result.page.items == ((first,) if direction == "ascending" else (last,))
    assert result.page.has_more
    for changed in (
        replace(
            query,
            sort_direction="descending" if direction == "ascending" else "ascending",
        ),
        replace(query, sort_by="state" if sort_by != "state" else "account"),
    ):
        with pytest.raises(ValueError, match="budget_overview_cursor_expired"):
            overview_result(
                (first, last),
                replace(changed, after_key=result.page.next_key),
                **kwargs,
            )
    next_page = overview_result(
        (first, last), replace(query, after_key=result.page.next_key), **kwargs
    )
    assert len(next_page.page.items) == 1 and next_page.page.items != result.page.items


def test_direction_does_not_reverse_stable_ties_and_group_rename_expires_cursor() -> (
    None
):
    query = BudgetOverviewQueryV1(PERIOD, NOW, limit=1, sort_by="account")
    row = project_budget_rows(_account(), (_resource(),), _current(), query)[0]
    first = replace(
        row,
        row_id="a" * 64,
        account=replace(
            _account(1), friendly_name="Same", organization_id=OpaqueIdV1("a")
        ),
    )
    last = replace(
        row,
        row_id="b" * 64,
        account=replace(
            _account(2), friendly_name="same", organization_id=OpaqueIdV1("b")
        ),
    )
    labels = {OpaqueIdV1("a"): "Alpha", OpaqueIdV1("b"): "Bravo"}
    kwargs: _Options = dict(
        registry_revision=1,
        inventory_count=2,
        subscription_account_ids=(),
        organization_labels=labels,
    )
    result = overview_result((last, first), query, **kwargs)
    descending = overview_result(
        (last, first), replace(query, sort_direction="descending"), **kwargs
    )
    assert result.page.items == descending.page.items == (first,)
    with pytest.raises(ValueError, match="budget_overview_cursor_expired"):
        overview_result(
            (first, last),
            replace(query, after_key=result.page.next_key),
            registry_revision=1,
            inventory_count=2,
            subscription_account_ids=(),
            organization_labels={**labels, OpaqueIdV1("b"): "Before"},
        )


@pytest.mark.parametrize(
    "field,value", (("sort_by", "money"), ("sort_direction", "sideways"))
)
def test_unknown_sort_is_rejected(field: str, value: str) -> None:
    with pytest.raises(ValueError, match="unsupported-field-state"):
        # Deliberately malformed boundary input must still fail runtime validation.
        if field == "sort_by":
            replace(
                BudgetOverviewQueryV1(PERIOD, NOW),
                sort_by=cast(Literal["account", "organization", "state"], value),
            )
        else:
            replace(
                BudgetOverviewQueryV1(PERIOD, NOW),
                sort_direction=cast(Literal["ascending", "descending"], value),
            )
