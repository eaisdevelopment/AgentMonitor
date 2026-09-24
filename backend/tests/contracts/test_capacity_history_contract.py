"""Pure invariants for CTR-CAP-006 bounded capacity-history queries."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest


def test_capacity_history_query_is_utc_half_open_and_bounded() -> None:
    """M05-PURE-060: ranges, pages, and unsupported buckets fail closed."""
    from agentmonitor.contracts.capacity_v1 import (
        CapacityHistoryQueryV1,
        InvalidCapacityContractV1,
    )
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    start = datetime(2026, 1, 1, tzinfo=UTC)
    valid = CapacityHistoryQueryV1(
        subject_id=OpaqueIdV1("account-1"),
        resource_id=None,
        window_id=None,
        metric="remaining_ratio",
        series_kind="poll_snapshot",
        range_start=start,
        range_before=start + timedelta(days=365),
        as_of=start + timedelta(days=365),
        limit=200,
        after_key=None,
        bucket_method=None,
        bucket_seconds=None,
    )
    assert valid.range_before - valid.range_start == timedelta(days=365)

    for change, code in (
        ({"range_before": start}, "capacity_history_range_invalid"),
        (
            {"range_before": start + timedelta(days=365, microseconds=1)},
            "capacity_history_range_too_large",
        ),
        ({"limit": 201}, "capacity_history_limit_invalid"),
        (
            {"bucket_method": "last", "bucket_seconds": 300},
            "capacity_history_bucket_unsupported",
        ),
    ):
        values: dict[str, Any] = {
            "subject_id": valid.subject_id,
            "resource_id": valid.resource_id,
            "window_id": valid.window_id,
            "metric": valid.metric,
            "series_kind": valid.series_kind,
            "range_start": valid.range_start,
            "range_before": valid.range_before,
            "as_of": valid.as_of,
            "limit": valid.limit,
            "after_key": valid.after_key,
            "bucket_method": valid.bucket_method,
            "bucket_seconds": valid.bucket_seconds,
            **change,
        }
        with pytest.raises(InvalidCapacityContractV1) as failure:
            CapacityHistoryQueryV1(**values)
        assert failure.value.code == code
