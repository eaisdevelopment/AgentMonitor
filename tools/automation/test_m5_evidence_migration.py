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
