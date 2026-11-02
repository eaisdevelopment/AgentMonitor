"""Real empty SQLite migration evidence; no seeded account or credential data."""

from pathlib import Path

from sqlalchemy import inspect

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)


def test_migrated_database_has_guarded_credential_binding_schema(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    with open_sqlite_database(ref, "runtime_read_only") as database:
        with database.connect() as connection:
            inspector = inspect(connection)
            assert {"reg_credential_binding_state", "reg_credential_binding"} <= set(
                inspector.get_table_names()
            )
            indexes = {
                item["name"]: item
                for item in inspector.get_indexes("reg_credential_binding")
            }
            assert indexes["uq_reg_binding_one_active"]["unique"]
            assert indexes["uq_reg_binding_one_pending"]["unique"]
            assert inspector.get_pk_constraint("reg_credential_binding")[
                "constrained_columns"
            ] == ["binding_id"]
            assert any(
                fk["referred_table"] == "reg_account"
                for fk in inspector.get_foreign_keys("reg_credential_binding_state")
            )
