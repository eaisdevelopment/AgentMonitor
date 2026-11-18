"""Pure startup metadata policy; no fabricated process or manager boundary."""

import pytest
from agentmonitor.composition.worker_invocation import checked_worker_invocation


def test_loaded_preinvocation_waits_only_at_startup() -> None:
    properties = {
        "InvocationID": "",
        "LoadState": "loaded",
        "ActiveState": "inactive",
        "ControlGroup": "",
    }
    assert checked_worker_invocation(properties, allow_pending=True) == ""
    with pytest.raises(ValueError, match="unit_identity_invalid"):
        checked_worker_invocation(properties)


@pytest.mark.parametrize(
    "change",
    [
        {"LoadState": "not-found"},
        {"ActiveState": "active"},
        {"ActiveState": "failed"},
        {"ControlGroup": "/already-running"},
        {"InvocationID": "broken"},
        {"InvocationID": "z" * 32},
    ],
)
def test_startup_does_not_allow_other_incomplete_or_invalid_identity(
    change: dict[str, str],
) -> None:
    properties = {
        "InvocationID": "",
        "LoadState": "loaded",
        "ActiveState": "inactive",
        "ControlGroup": "",
    } | change
    with pytest.raises(ValueError, match="unit_identity_invalid"):
        checked_worker_invocation(properties, allow_pending=True)


def test_assigned_invocation_retains_strict_identity() -> None:
    properties = {"InvocationID": "a" * 32}
    assert checked_worker_invocation(properties) == "a" * 32
    assert checked_worker_invocation(properties, allow_pending=True) == "a" * 32


@pytest.mark.parametrize(
    "missing", ["InvocationID", "LoadState", "ActiveState", "ControlGroup"]
)
def test_missing_metadata_never_counts_as_pending(missing: str) -> None:
    properties = {
        "InvocationID": "",
        "LoadState": "loaded",
        "ActiveState": "inactive",
        "ControlGroup": "",
    }
    del properties[missing]
    with pytest.raises(ValueError, match="unit_identity_invalid"):
        checked_worker_invocation(properties, allow_pending=True)
