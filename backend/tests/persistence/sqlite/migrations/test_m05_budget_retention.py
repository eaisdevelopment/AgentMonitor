"""Financial expiration needs its own additive schema and prior-reader refusal."""

from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_inspection,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
    migrate_to_head,
)

from backend.tests.persistence.sqlite.migrations.test_m05_model_remainder import (
    historical_inspector,
    migrate_revision,
)


def test_fresh_schema_has_receipt_bound_expiration_marker(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    with open_sqlite_inspection(reference) as connection:
        columns = connection.exec_driver_sql(
            "PRAGMA table_info(capacity_budget_expired_report)"
        ).all()
        assert {column[1] for column in columns} == {
            "receipt_id",
            "report_id",
            "canonical_provenance_json",
            "expired_at",
        }, "financial_expiration_marker_missing"
        foreign_keys = connection.exec_driver_sql(
            "PRAGMA foreign_key_list(capacity_budget_expired_report)"
        ).all()
        assert len(foreign_keys) == 1
        assert foreign_keys[0][2:5] == (
            "capacity_commit_receipt",
            "receipt_id",
            "receipt_id",
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.current_revision == "v1_0736"
    assert view.state == "compatible"


def test_pre_retention_binary_refuses_new_schema_before_writes(tmp_path: Path) -> None:
    root = tmp_path / "database"
    root.mkdir(mode=0o700)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    migrate_revision(reference, "v1_0735", "migration_initialize")
    old = historical_inspector(
        tmp_path / "prior", "e25765dd4636cd54f4427bbb05b2f03f394a8948"
    )
    before = old.InspectSchemaCompatibilityV1(
        reference, old.application_schema_range(), "runtime_read_write"
    )
    assert old.RequireWritableSchemaV1(before).revision == "v1_0735"
    migrate_revision(reference, "v1_0736", "migration_existing")
    rejected = old.InspectSchemaCompatibilityV1(
        reference, old.application_schema_range(), "runtime_read_write"
    )
    assert rejected.state == "unknown_revision"
    with pytest.raises(old.SchemaCompatibilityError, match="schema_not_writable"):
        old.RequireWritableSchemaV1(rejected)
