"""Pure internal cursor encoding, without database or provider I/O."""

import base64
import json
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    BudgetRepositoryError,
    _cursor,
    _read_cursor,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetPeriodV1,
    BudgetReportHistoryQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def _query() -> BudgetReportHistoryQueryV1:
    return BudgetReportHistoryQueryV1(
        OpaqueIdV1("pure-account"),
        OpaqueIdV1("pure-resource"),
        BudgetPeriodV1(
            datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 8, tzinfo=UTC)
        ),
    )


def test_snapshot_cursor_retains_upper_bound_and_last_returned_sequence() -> None:
    query = _query()
    assert _read_cursor(query) is None
    assert _read_cursor(replace(query, after_key=_cursor(query, 123, 90))) == (123, 90)


@pytest.mark.parametrize("field", ["account_id", "resource_id", "period"])
def test_cursor_cannot_change_its_query_scope(field: str) -> None:
    query = _query()
    cursor_query = replace(query, after_key=_cursor(query, 123, 90))
    value = (
        OpaqueIdV1("other")
        if field != "period"
        else BudgetPeriodV1(
            datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 10, 8, tzinfo=UTC)
        )
    )
    with pytest.raises(BudgetRepositoryError, match="budget_history_cursor_invalid"):
        _read_cursor(replace(cursor_query, **cast(dict[str, Any], {field: value})))


@pytest.mark.parametrize(
    "snapshot,last", [(False, 1), (1, False), (1, 2), (1, 0), (-1, -1), (2**63, 1)]
)
def test_cursor_rejects_noninteger_or_invalid_bounds(
    snapshot: object, last: object
) -> None:
    query = _query()
    encoded = _cursor(query, 2, 1)
    data = json.loads(base64.urlsafe_b64decode(encoded))
    data[-2:] = [snapshot, last]
    modified = base64.urlsafe_b64encode(
        json.dumps(data, separators=(",", ":")).encode()
    ).decode()
    with pytest.raises(BudgetRepositoryError, match="budget_history_cursor_invalid"):
        _read_cursor(replace(query, after_key=modified))
