"""Real empty schema expansion; no invented coverage or provider observations."""

from dataclasses import fields
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.contracts.registry_coverage_v1 import OrganizationProviderCoverageV1
from sqlalchemy import inspect


def test_real_migration_adds_empty_current_and_immutable_coverage_history(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    current = "reg_organization_provider_coverage"
    history = "reg_organization_provider_coverage_revision"
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            schema = inspect(connection)
            assert {current, history} <= set(schema.get_table_names())
            expected = {item.name for item in fields(OrganizationProviderCoverageV1)}
            for table in (current, history):
                assert {
                    column["name"] for column in schema.get_columns(table)
                } == expected
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )
            assert schema.get_pk_constraint(current)["constrained_columns"] == [
                "coverage_id"
            ]
            assert schema.get_pk_constraint(history)["constrained_columns"] == [
                "coverage_id",
                "record_version",
            ]
            assert {
                tuple(fk["constrained_columns"])
                for fk in schema.get_foreign_keys(current)
            } == {
                ("organization_id",),
                ("provider_key",),
                ("account_id",),
                ("account_organization_id",),
            }
            assert len(schema.get_foreign_keys(history)) == 1
            assert schema.get_foreign_keys(history)[0]["referred_table"] == current
            assert any(
                index["unique"]
                and index["column_names"] == ["organization_id", "provider_key"]
                for index in schema.get_indexes(current)
            )
            triggers = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_schema WHERE type='trigger'"
                ).scalars()
            )
            assert {
                "tr_reg_coverage_revision_no_update",
                "tr_reg_coverage_revision_no_delete",
            } <= triggers
            assert (
                connection.exec_driver_sql("PRAGMA foreign_key_check").first() is None
            )
