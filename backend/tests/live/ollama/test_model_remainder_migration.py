"""Marker-only upgrade preserves genuine stored reports and receipt lineage."""

import hashlib
import os
import sqlite3
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
    open_sqlite_inspection,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    load_migration_catalog,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)

from backend.tests.live.ollama.test_budget_monetary_persistence import (
    _monetary_report,
    _receipt,
    _require,
)
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)
from backend.tests.persistence.sqlite.migrations.test_m05_model_remainder import (
    migrate_revision,
    schema_digest,
)
from tools.automation.implementations.auto_migrate import _create_sqlite_backup


def _private_prior_copy(root: Path) -> DatabaseRefV1:
    """After activation the operator selects a genuine retained prior backup."""
    selected = os.environ.get("AGENTMONITOR_M7_PRIOR_DATABASE")
    if selected is None:
        return _private_real_copy(root)
    source = Path(selected)
    _require(
        source.is_absolute() and source.resolve() == source,
        "prior_snapshot_path_invalid",
    )
    reference = DatabaseRefV1(source, source.parent)
    root.chmod(0o700)
    target = root / "agentmonitor.db"
    with open_sqlite_inspection(reference) as connection:
        driver = connection.connection.driver_connection
        _require(
            isinstance(driver, sqlite3.Connection), "prior_snapshot_driver_invalid"
        )
        assert isinstance(driver, sqlite3.Connection)
        _create_sqlite_backup(driver, target)
    return DatabaseRefV1(target, root)


def _retained_digest(reference: DatabaseRefV1) -> str:
    digest = hashlib.sha256()
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "capacity_budget_report",
                "capacity_commit_receipt",
                "capacity_commit_receipt_observation",
                "capacity_budget_observation",
                "capacity_budget_signed_cost_measure",
                "capacity_usage_bucket",
                "capacity_usage_dimension",
                "capacity_usage_measure",
                "collection_budget_run",
            ):
                digest.update(table.encode())
                for row in connection.exec_driver_sql(
                    f"SELECT * FROM {table} ORDER BY rowid"
                ):
                    digest.update(repr(tuple(row)).encode())
                    digest.update(b"\0")
    return digest.hexdigest()


def test_real_retained_reports_survive_model_remainder_marker(tmp_path: Path) -> None:
    reference = _private_prior_copy(tmp_path)
    with open_sqlite_inspection(reference) as connection:
        current = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
    _require(current == "v1_0734", "genuine_prior_schema_snapshot_required")
    structure = schema_digest(reference)
    run, report = _monetary_report(reference)
    before = _retained_digest(reference)

    migrate_revision(reference, "v1_0735", "migration_existing")

    _require(schema_digest(reference) == structure, "physical_schema_changed")
    view = InspectSchemaCompatibilityV1(
        reference,
        next(
            item.schema_range
            for item in load_migration_catalog().revisions
            if item.revision == "v1_0735"
        ),
        "runtime_read_write",
    )
    _require(
        view.state == "compatible" and view.current_revision == "v1_0735",
        "semantic_marker_not_compatible",
    )
    _require(_retained_digest(reference) == before, "retained_financial_rows_changed")
    assert run.account_id is not None and run.report_id is not None
    reread = SqliteBudgetReportRepositoryV1(reference).get_report(
        run.account_id, run.report_id
    )
    _require(reread == report, "legacy_report_read_changed")
    # The current receipt reader requires the expiration-marker schema.
    # Verify original report/receipt/fact bytes across that additive step too.
    migrate_revision(reference, load_migration_catalog().head, "migration_existing")
    _require(_retained_digest(reference) == before, "retained_rows_changed_at_head")
    receipt = _receipt(reference, run)
    _require(receipt.report_id == report.report_id, "legacy_receipt_changed")
    _require(receipt.payload_digest == run.payload_digest, "legacy_digest_changed")
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            _require(
                connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
                == "ok",
                "migrated_database_integrity_failed",
            )
            _require(
                connection.exec_driver_sql("PRAGMA foreign_key_check").first() is None,
                "migrated_foreign_key_check_failed",
            )
