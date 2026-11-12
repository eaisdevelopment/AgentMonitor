"""Actual empty SQLite M7 report structures; never seed financial observations."""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseOpenModeV1,
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    InspectSchemaCompatibilityV1,
    application_schema_range,
    load_migration_catalog,
    migrate_to_head,
)
from alembic import command
from alembic.config import Config


def test_real_budget_schema_has_report_coverage_and_signed_money(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    result = InspectSchemaCompatibilityV1(
        ref, application_schema_range(), "runtime_read_write"
    )
    assert result.state == "compatible"
    assert result.current_revision == "v1_0734"
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            tables = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_schema WHERE type='table'"
                ).scalars()
            )
            assert {
                "capacity_budget_report",
                "capacity_budget_signed_cost_measure",
            } <= tables
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM capacity_budget_report"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM capacity_budget_signed_cost_measure"
                ).scalar_one()
                == 0
            )
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
            assert (
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok"
            )


def test_actual_setup_schema_upgrades_without_manufacturing_reports(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    catalog = load_migration_catalog()
    transitions: tuple[tuple[str, DatabaseOpenModeV1], ...] = (
        ("v1_0731", "migration_initialize"),
        ("v1_0732", "migration_existing"),
        ("v1_0733", "migration_existing"),
        ("v1_0734", "migration_existing"),
    )
    for target, mode in transitions:
        with open_sqlite_database(ref, mode) as handle:
            with handle.connect() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                config = Config()
                config.set_main_option("script_location", str(MIGRATIONS_PATH))
                config.attributes.update(
                    connection=connection,
                    migrations_path=MIGRATIONS_PATH,
                    catalog_digest=catalog.digest,
                )
                command.upgrade(config, target)
                connection.commit()
                assert (
                    connection.exec_driver_sql(
                        "SELECT COUNT(*) FROM capacity_commit_receipt"
                    ).scalar_one()
                    == 0
                )
                if target in {"v1_0732", "v1_0733", "v1_0734"}:
                    assert (
                        connection.exec_driver_sql(
                            "SELECT COUNT(*) FROM capacity_budget_report"
                        ).scalar_one()
                        == 0
                    )
                    assert (
                        connection.exec_driver_sql(
                            "SELECT COUNT(*) FROM capacity_budget_signed_cost_measure"
                        ).scalar_one()
                        == 0
                    )
                if target == "v1_0734":
                    for table in (
                        "reg_financial_pool",
                        "reg_financial_pool_membership",
                    ):
                        assert (
                            connection.exec_driver_sql(
                                f"SELECT COUNT(*) FROM {table}"
                            ).scalar_one()
                            == 0
                        )
                assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
    result = InspectSchemaCompatibilityV1(
        ref, application_schema_range(), "runtime_read_write"
    )
    assert result.state == "compatible"
    assert result.current_revision == "v1_0734"
