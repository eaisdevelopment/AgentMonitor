"""Only fixed phase and error categories may leave the native billing worker."""

import pytest

from backend.tests.live.billing.native_cost_comparison_worker import failure_context


@pytest.mark.parametrize(
    ("witness", "expected"),
    [
        (
            {"phase": "dispatch_prepare", "error_kind": "ValueError"},
            "dispatch_prepare:ValueError",
        ),
        (
            {"phase": "enqueue", "error_kind": "OperationalError"},
            "enqueue:OperationalError",
        ),
        (
            {"phase": "private arbitrary value", "error_kind": "private message"},
            "unknown:unknown",
        ),
        ({"phase": [], "error_kind": {}}, "unknown:unknown"),
        ({}, "unknown:unknown"),
    ],
)
def test_native_cost_failure_context_is_closed(
    witness: dict[str, object], expected: str
) -> None:
    assert failure_context(witness) == expected
