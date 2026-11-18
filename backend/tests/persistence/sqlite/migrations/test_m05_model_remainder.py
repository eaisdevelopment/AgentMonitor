"""Real semantic-marker migration; no fabricated reports or physical changes."""

import hashlib
import importlib.util
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseOpenModeV1,
    DatabaseRefV1,
    open_sqlite_database,
    open_sqlite_inspection,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH,
    InspectSchemaCompatibilityV1,
    RequireWritableSchemaV1,
    SchemaCompatibilityError,
    application_schema_range,
    load_migration_catalog,
    migrate_to_head,
)
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[5]
HISTORICAL_REVISION = "42d87bd97abac0eee3a9d225233ef8deb8ed3d0d"
INSPECTOR_PATH = (
    "backend/src/agentmonitor/adapters/persistence/_shared/sqlite/"
    "schema/compatibility.py"
)


def migrate_revision(
    reference: DatabaseRefV1, revision: str, mode: DatabaseOpenModeV1
) -> None:
    """Use the reviewed real Alembic entry on a test-owned database only."""
    catalog = load_migration_catalog()
    with open_sqlite_database(reference, mode) as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            config = Config()
            config.set_main_option("script_location", str(MIGRATIONS_PATH))
            config.attributes.update(
                connection=connection,
                migrations_path=MIGRATIONS_PATH,
                catalog_digest=catalog.digest,
            )
            command.upgrade(config, revision)
            connection.commit()


def schema_digest(reference: DatabaseRefV1) -> str:
    with open_sqlite_inspection(reference) as connection:
        rows = connection.exec_driver_sql(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name"
        )
        return hashlib.sha256(repr(tuple(rows)).encode()).hexdigest()


def historical_inspector(
    destination: Path, revision: str = HISTORICAL_REVISION
) -> ModuleType:
    """Load unchanged checked-in old inspector and its checksum-pinned catalog."""
    migration_root = destination / "backend/migrations"
    (migration_root / "versions").mkdir(parents=True)
    for relative in (INSPECTOR_PATH, "backend/migrations/catalog.toml"):
        result = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            timeout=10,
        )
        if result.returncode != 0:
            pytest.fail("historical_inspector_checkout_required", pytrace=False)
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.stdout)
    catalog = tomllib.loads((migration_root / "catalog.toml").read_text())
    shutil.copyfile(MIGRATIONS_PATH / "env.py", migration_root / "env.py")
    for record in catalog["revisions"]:
        filename = record["filename"]
        shutil.copyfile(
            MIGRATIONS_PATH / "versions" / filename,
            migration_root / "versions" / filename,
        )
    name = "agentmonitor_historical_model_remainder_inspector"
    spec = importlib.util.spec_from_file_location(name, destination / INSPECTOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.modules[name]
    return module


def test_real_model_remainder_marker_preserves_schema_and_old_binary_refuses(
    tmp_path: Path,
) -> None:
    root = tmp_path / "database"
    root.mkdir(mode=0o700)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    migrate_revision(reference, "v1_0734", "migration_initialize")
    old = historical_inspector(tmp_path / "old")
    before = schema_digest(reference)
    assert (
        old.InspectSchemaCompatibilityV1(
            reference, old.application_schema_range(), "runtime_read_write"
        ).state
        == "compatible"
    )

    migrate_revision(reference, "v1_0735", "migration_existing")

    assert schema_digest(reference) == before
    view = InspectSchemaCompatibilityV1(
        reference,
        next(
            item.schema_range
            for item in load_migration_catalog().revisions
            if item.revision == "v1_0735"
        ),
        "runtime_read_write",
    )
    assert view.state == "compatible"
    assert view.current_revision == "v1_0735"
    # Explicit historical inspection is not permission for this newer binary
    # to write before the expiration-marker migration.
    with pytest.raises(SchemaCompatibilityError, match="schema_not_writable"):
        RequireWritableSchemaV1(view)
    old_view = old.InspectSchemaCompatibilityV1(
        reference, old.application_schema_range(), "runtime_read_write"
    )
    assert old_view.state == "unknown_revision"
    with pytest.raises(old.SchemaCompatibilityError, match="schema_not_writable"):
        old.RequireWritableSchemaV1(old_view)


def test_fresh_database_uses_marker_and_refuses_downgrade(tmp_path: Path) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert RequireWritableSchemaV1(view).revision == load_migration_catalog().head
    before = schema_digest(reference)
    catalog = load_migration_catalog()
    with open_sqlite_database(reference, "migration_existing") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            config = Config()
            config.set_main_option("script_location", str(MIGRATIONS_PATH))
            config.attributes.update(
                connection=connection,
                migrations_path=MIGRATIONS_PATH,
                catalog_digest=catalog.digest,
            )
            with pytest.raises(ValueError, match="migration_downgrade_unsupported"):
                command.downgrade(config, "v1_0734")
            connection.rollback()
    assert schema_digest(reference) == before
    assert (
        InspectSchemaCompatibilityV1(
            reference, application_schema_range(), "runtime_read_write"
        ).current_revision
        == load_migration_catalog().head
    )


@pytest.mark.parametrize("revision", ["v1_0732", "v1_0733", "v1_0734", "v1_0735"])
def test_prior_schema_requires_explicit_upgrade_without_inspector_writes(
    tmp_path: Path, revision: str
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_revision(reference, revision, "migration_initialize")
    before = reference._path.read_bytes()
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.state == "upgrade_required"
    assert view.current_revision == revision
    with pytest.raises(SchemaCompatibilityError, match="schema_not_writable"):
        RequireWritableSchemaV1(view)
    assert reference._path.read_bytes() == before
