"""Pure exact-schema admission; no inferred future upgrade permissions."""

import pytest

from tools.automation.implementations.m6_cutover import _retained_migration_source


@pytest.mark.parametrize(
    ("target", "source"),
    [("v1_0719", "v1_0718"), ("v1_0720", "v1_0719")],
)
def test_only_reviewed_retained_schema_predecessors(target: str, source: str) -> None:
    assert _retained_migration_source(target) == source


@pytest.mark.parametrize("target", ["", "v1_0718", "v1_0721", "v1_07200", "v1_0720 "])
def test_unknown_target_does_not_infer_upgrade_permission(target: str) -> None:
    assert _retained_migration_source(target) is None
