"""Pure provenance policy for retaining real predecessor evidence."""

import pytest

from tools.automation.implementations import m5_evidence_migration


def test_migration_requires_exact_provenance_and_unchanged_application() -> None:
    validate = m5_evidence_migration.validate_predecessor_binding_v1
    kwargs = dict(
        old_revision="a" * 40,
        archived_revision="a" * 40,
        old_pid=12,
        archived_pid=12,
        old_start=34,
        archived_start=34,
        application_changed=False,
    )
    validate(**kwargs)
    for change in (
        {"archived_revision": "b" * 40},
        {"archived_pid": 13},
        {"archived_start": 35},
        {"application_changed": True},
    ):
        with pytest.raises(ValueError):
            validate(**(kwargs | change))


def test_only_reviewed_history_view_change_is_eligible() -> None:
    policy = m5_evidence_migration.reviewed_paths_v1
    approved = m5_evidence_migration.REVIEWED_HISTORY_VIEW_SHA256
    path = "frontend/src/features/command/CapacityPanel.tsx"
    assert policy(["docs/example.md", path], approved)
    assert not policy(["backend/src/other.py"], approved)
    assert not policy([path], "0" * 64)
    assert not policy(["frontend/src/app/other.tsx"], approved)


def test_current_service_selectors_are_atomic() -> None:
    select = m5_evidence_migration.current_service_binding_v1
    previous = ("a" * 40, 12, 34)
    assert select({}, previous) == previous
    current = {
        "AGENTMONITOR_M5_SERVICE_IMPLEMENTATION_REVISION": "b" * 40,
        "AGENTMONITOR_M5_CURRENT_SERVICE_PID": "56",
        "AGENTMONITOR_M5_CURRENT_SERVICE_START_TIME_TICKS": "78",
    }
    assert select(current, previous) == ("b" * 40, 56, 78)
    with pytest.raises(ValueError):
        select({"AGENTMONITOR_M5_CURRENT_SERVICE_PID": "56"}, previous)
