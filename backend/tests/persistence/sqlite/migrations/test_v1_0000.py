"""FND-DB-001/002/004, FND-MIG-003 and DB-MIG: real Alembic only."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "backend/src"))
MODULE = "agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility"

if TYPE_CHECKING:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )


def implementation() -> ModuleType:
    assert (
        (ROOT / "backend/src" / Path(*MODULE.split("."))).with_suffix(".py").is_file()
    ), "FND-DB-001: production explicit migration and inspection are absent"
    return importlib.import_module(MODULE)


def initialize_historical_anchor(ref: DatabaseRefV1, schema: ModuleType) -> None:
    """Run the real Alembic chain to its immutable prior-release anchor."""
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )

    catalog = schema.load_migration_catalog()
    with open_sqlite_database(ref, "migration_initialize") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            config = Config()
            config.set_main_option("script_location", str(schema.MIGRATIONS_PATH))
            config.attributes.update(
                connection=connection,
                migrations_path=schema.MIGRATIONS_PATH,
                catalog_digest=catalog.digest,
            )
            command.upgrade(config, "v1_0000")
            connection.commit()


def test_v1_0000_uses_real_file_and_creates_no_business_tables(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    path = tmp_path / "agentmonitor.db"
    ref = DatabaseRefV1(path, tmp_path)
    initialize_historical_anchor(ref, schema)
    assert path.is_file()
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name"
            ).scalars().all() == ["alembic_version"]
            assert (
                connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                ).scalar()
                == "v1_0000"
            )
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
    view = schema.InspectSchemaCompatibilityV1(
        ref, schema.application_schema_range(), "runtime_read_write"
    )
    assert view.state == "upgrade_required"
    assert view.current_revision == "v1_0000"
    assert view.migration_required
    with pytest.raises(schema.SchemaCompatibilityError):
        schema.RequireWritableSchemaV1(view)
    before = path.read_bytes()
    with pytest.raises(schema.SchemaCompatibilityError) as caught:
        schema.migrate_to_head(ref)
    assert caught.value.code == "migration_preflight_refused"
    assert path.read_bytes() == before


def test_inspection_never_creates_or_migrates(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    path = tmp_path / "agentmonitor.db"
    ref = DatabaseRefV1(path, tmp_path)
    app = schema.application_schema_range()
    assert schema.InspectSchemaCompatibilityV1(
        ref, app, "runtime_read_write"
    ).state == ("missing")
    assert not path.exists()
    with open_sqlite_database(ref, "migration_initialize"):
        pass
    before = path.read_bytes()
    view = schema.InspectSchemaCompatibilityV1(ref, app, "runtime_read_write")
    assert view.state == "empty"
    assert view.migration_required
    with pytest.raises(schema.SchemaCompatibilityError):
        schema.RequireWritableSchemaV1(view)
    assert path.read_bytes() == before


def test_newer_binary_range_refuses_writes_without_ddl(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    # Real current DB against a pre-anchor binary range; no fabricated schema.
    app = dataclasses.replace(
        schema.application_schema_range(),
        minimum_readable_revision="base",
        minimum_writable_revision="base",
        maximum_readable_revision="base",
        maximum_writable_revision="base",
        migration_target_revision="base",
    )
    view = schema.InspectSchemaCompatibilityV1(ref, app, "runtime_read_write")
    assert view.state == "newer_than_binary"
    with pytest.raises(schema.SchemaCompatibilityError) as caught:
        schema.RequireWritableSchemaV1(view)
    assert caught.value.code == "schema_not_writable"


@pytest.mark.parametrize("mutation", ["checksum", "duplicate", "head", "metadata"])
def test_changed_catalog_or_revision_fails_before_database_creation(
    tmp_path: Path, mutation: str
) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )

    copied = tmp_path / "migrations"
    shutil.copytree(ROOT / "backend/migrations", copied)
    catalog = copied / "catalog.toml"
    revision = copied / "versions/v1_0000_fnd_anchor.py"
    if mutation == "checksum":
        revision.write_text(revision.read_text() + "\n# changed immutable revision\n")
    elif mutation == "duplicate":
        source = catalog.read_text()
        catalog.write_text(
            source + "\n[[revisions]]" + source.split("[[revisions]]")[1]
        )
    elif mutation == "head":
        shutil.copyfile(revision, revision.with_name("v1_0001_competing.py"))
    else:
        catalog.write_text(catalog.read_text().replace("none_empty_bootstrap", ""))
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with pytest.raises(schema.SchemaCompatibilityError) as caught:
        schema.migrate_to_head(ref, migrations_path=copied)
    assert caught.value.code in {
        "migration_catalog_invalid",
        "migration_checksum_mismatch",
    }
    assert not (tmp_path / "agentmonitor.db").exists()
    assert str(tmp_path) not in str(caught.value)


def test_catalog_and_revision_metadata_are_complete_and_immutable() -> None:
    schema = implementation()
    catalog = schema.load_migration_catalog()
    assert len(catalog.revisions) == 18
    assert catalog.head == "v1_0603"
    metadata = catalog.revisions[0]
    assert metadata.revision == "v1_0000"
    assert metadata.parent_revision is None
    assert metadata.owner == "PLAN-FND"
    assert metadata.plan_id == "PLAN-FND"
    assert metadata.requirement_ids
    assert metadata.tables == ()
    assert metadata.backup_prerequisite == "none_empty_bootstrap"
    assert metadata.recovery_policy
    assert metadata.validation_ids
    assert metadata.portability_notes
    assert metadata.schema_range.catalog_digest == catalog.digest
    with pytest.raises(dataclasses.FrozenInstanceError):
        metadata.owner = "another-owner"
    iam = catalog.revisions[1]
    assert iam.revision == "v1_0100"
    assert iam.parent_revision == "v1_0000"
    assert iam.owner == "M01"
    assert len(iam.tables) == 7
    assert iam.backup_prerequisite == "none_empty_bootstrap"
    registry = catalog.revisions[2:7]
    assert tuple(item.revision for item in registry) == (
        "v1_0200",
        "v1_0201",
        "v1_0202",
        "v1_0203",
        "v1_0204",
    )
    assert all(item.owner == "M02" for item in registry)
    assert sum(len(item.tables) for item in registry) == 15
    assert all(
        item.backup_prerequisite == "required_existing_database" for item in registry
    )
    assert catalog.revisions[7].revision == "v1_0300"
    assert catalog.revisions[7].owner == "M03"
    assert catalog.revisions[8].revision == "v1_0400"
    assert catalog.revisions[8].owner == "M04"
    capacity = catalog.revisions[9:14]
    assert tuple(item.revision for item in capacity) == (
        "v1_0500",
        "v1_0501",
        "v1_0502",
        "v1_0503",
        "v1_0504",
    )
    assert all(item.owner == "M05" for item in capacity)
    runtime = catalog.revisions[14:]
    assert tuple(item.revision for item in runtime) == (
        "v1_0600",
        "v1_0601",
        "v1_0602",
        "v1_0603",
    )
    assert all(item.owner == "M06" for item in runtime)


def test_schema_marker_failures_refuse_writes_and_are_preserved(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    # Exercise only Alembic technical metadata on the real production schema.
    # No alternate schema or business rows are introduced.
    for revisions, expected in (
        (("unrecognized",), "unknown_revision"),
        (("v1_0000", "unrecognized"), "multiple_heads"),
        ((), "migration_failed"),
    ):
        with open_sqlite_database(ref, "migration_existing") as handle:
            with handle.connect() as connection:
                connection.exec_driver_sql("DELETE FROM alembic_version")
                for revision in revisions:
                    connection.exec_driver_sql(
                        "INSERT INTO alembic_version (version_num) VALUES (?)",
                        (revision,),
                    )
                connection.commit()
        before = (tmp_path / "agentmonitor.db").read_bytes()
        view = schema.InspectSchemaCompatibilityV1(
            ref, schema.application_schema_range(), "runtime_read_write"
        )
        assert view.state == expected
        with pytest.raises(schema.SchemaCompatibilityError):
            schema.RequireWritableSchemaV1(view)
        with pytest.raises(schema.SchemaCompatibilityError) as caught:
            schema.migrate_to_head(ref)
        assert caught.value.code == "migration_preflight_refused"
        assert (tmp_path / "agentmonitor.db").read_bytes() == before


def test_locked_migration_is_bounded_preserves_target_and_closes(
    tmp_path: Path,
) -> None:
    import time

    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with open_sqlite_database(ref, "migration_initialize") as holder:
        with holder.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            started = time.monotonic()
            with pytest.raises(schema.SchemaCompatibilityError) as caught:
                schema.migrate_to_head(ref)
            assert caught.value.code == "migration_preflight_refused"
            assert time.monotonic() - started < 1
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM sqlite_schema WHERE type='table'"
                ).scalar()
                == 0
            )
            connection.rollback()
    with pytest.raises(schema.SchemaCompatibilityError) as caught:
        schema.migrate_to_head(ref)
    assert caught.value.code == "migration_preflight_refused"
    assert (
        schema.InspectSchemaCompatibilityV1(
            ref, schema.application_schema_range(), "runtime_read_write"
        ).state
        == "empty"
    )


def test_read_only_policy_mismatch_and_permissions_are_distinct(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    path = tmp_path / "agentmonitor.db"
    ref = DatabaseRefV1(path, tmp_path)
    schema.migrate_to_head(ref)
    with open_sqlite_database(ref, "migration_existing") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=DELETE")
    before = path.read_bytes()
    app = schema.application_schema_range()
    view = schema.InspectSchemaCompatibilityV1(ref, app, "runtime_read_write")
    assert view.state == "policy_incompatible"
    assert path.read_bytes() == before
    path.chmod(0o000)
    view = schema.InspectSchemaCompatibilityV1(ref, app, "runtime_read_write")
    assert view.state == "unreadable"
    path.chmod(0o600)


def test_failed_schema_validation_preserves_existing_metadata(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    path = tmp_path / "agentmonitor.db"
    ref = DatabaseRefV1(path, tmp_path)
    schema.migrate_to_head(ref)
    with open_sqlite_database(ref, "migration_existing") as handle:
        with handle.connect() as connection:
            # A real extra technical index violates the anchor's object inventory.
            connection.exec_driver_sql(
                "CREATE INDEX unowned_index ON alembic_version (version_num)"
            )
            connection.commit()
    before = path.read_bytes()
    view = schema.InspectSchemaCompatibilityV1(
        ref, schema.application_schema_range(), "runtime_read_write"
    )
    assert view.state == "migration_failed"
    with pytest.raises(schema.SchemaCompatibilityError):
        schema.migrate_to_head(ref)
    assert path.read_bytes() == before


def test_invalid_range_cannot_report_compatible(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    app = dataclasses.replace(
        schema.application_schema_range(), migration_target_revision="base"
    )
    view = schema.InspectSchemaCompatibilityV1(ref, app, "runtime_read_write")
    assert view.state == "policy_incompatible"


def test_actual_revision_metadata_cannot_mutate_and_downgrade_is_refused(
    tmp_path: Path,
) -> None:
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    catalog = schema.load_migration_catalog()
    config = Config()
    config.set_main_option("script_location", str(ROOT / "backend/migrations"))
    script = ScriptDirectory.from_config(config).get_revision("v1_0000")
    assert script is not None
    with pytest.raises(TypeError):
        script.module.METADATA["owner"] = "changed"
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    with open_sqlite_database(ref, "migration_existing") as handle:
        with handle.connect() as connection:
            config.attributes.update(
                connection=connection,
                migrations_path=ROOT / "backend/migrations",
                catalog_digest=catalog.digest,
            )
            with pytest.raises(ValueError, match="migration_downgrade_unsupported"):
                command.downgrade(config, "base")
            connection.rollback()
    assert (
        schema.InspectSchemaCompatibilityV1(
            ref, schema.application_schema_range(), "runtime_read_write"
        ).state
        == "compatible"
    )


def database_inventory(root: Path) -> dict[str, tuple[int, int, str]]:
    """Record actual main file and every journal/sidecar, including timestamps."""
    return {
        path.name: (
            path.stat().st_size,
            path.stat().st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in root.iterdir()
        if path.name.startswith("agentmonitor.db")
    }


def test_closed_database_inspection_never_creates_or_changes_sidecars(
    tmp_path: Path,
) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    before = database_inventory(tmp_path)
    assert set(before) == {"agentmonitor.db"}
    view = schema.InspectSchemaCompatibilityV1(
        ref, schema.application_schema_range(), "runtime_read_write"
    )
    assert database_inventory(tmp_path) == before
    assert view.state == "compatible"
    schema.RequireWritableSchemaV1(view)
    assert database_inventory(tmp_path) == before


def test_live_wal_inspection_refuses_without_sidecar_mutation(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    with open_sqlite_database(ref, "runtime_read_write") as writer:
        with writer.connect() as connection:
            connection.exec_driver_sql("PRAGMA user_version=1")
            connection.commit()
            before = database_inventory(tmp_path)
            assert {"agentmonitor.db-wal", "agentmonitor.db-shm"} <= before.keys()
            view = schema.InspectSchemaCompatibilityV1(
                ref, schema.application_schema_range(), "runtime_read_write"
            )
            assert database_inventory(tmp_path) == before
            assert view.state == "locked"
            with pytest.raises(schema.SchemaCompatibilityError):
                schema.RequireWritableSchemaV1(view)
            assert database_inventory(tmp_path) == before
            connection.rollback()


@pytest.mark.parametrize(
    "definition",
    [
        "version_num VARCHAR(32) NOT NULL PRIMARY KEY, unowned_metadata TEXT",
        "renamed_version VARCHAR(32) NOT NULL PRIMARY KEY",
        "version_num VARCHAR(32) PRIMARY KEY",
        "version_num VARCHAR(32) NOT NULL UNIQUE",
        "version_num TEXT NOT NULL PRIMARY KEY",
        "version_num VARCHAR(32) NOT NULL DEFAULT 'v1_0000' PRIMARY KEY",
        "version_num VARCHAR(32) COLLATE NOCASE NOT NULL PRIMARY KEY",
        "version_num VARCHAR(32) NOT NULL PRIMARY KEY DESC",
        "version_num VARCHAR(32) NOT NULL PRIMARY KEY CHECK(length(version_num)>0)",
    ],
    ids=[
        "extra",
        "renamed",
        "nullable",
        "no-pk",
        "type",
        "default",
        "collation",
        "descending",
        "check",
    ],
)
def test_marker_structure_changes_refuse_without_inspection_mutation(
    tmp_path: Path, definition: str
) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    with open_sqlite_database(ref, "migration_existing") as handle:
        with handle.connect() as connection:
            # Mutate only the real migrated technical marker, preserving its row.
            # Each deliberate defect tests refusal, never an alternate valid schema.
            connection.exec_driver_sql(
                "ALTER TABLE alembic_version RENAME TO old_marker"
            )
            connection.exec_driver_sql(f"CREATE TABLE alembic_version ({definition})")
            target = (
                "renamed_version" if definition.startswith("renamed") else "version_num"
            )
            connection.exec_driver_sql(
                f"INSERT INTO alembic_version ({target}) "
                "SELECT version_num FROM old_marker"
            )
            connection.exec_driver_sql("DROP TABLE old_marker")
            connection.commit()
    before = database_inventory(tmp_path)
    view = schema.InspectSchemaCompatibilityV1(
        ref, schema.application_schema_range(), "runtime_read_write"
    )
    assert view.state == "migration_failed"
    with pytest.raises(schema.SchemaCompatibilityError):
        schema.RequireWritableSchemaV1(view)
    assert database_inventory(tmp_path) == before


def test_added_column_to_real_anchor_refuses_writable_receipt(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    with open_sqlite_database(ref, "migration_existing") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE alembic_version ADD COLUMN unowned_metadata TEXT"
            )
            connection.commit()
    before = database_inventory(tmp_path)
    view = schema.InspectSchemaCompatibilityV1(
        ref, schema.application_schema_range(), "runtime_read_write"
    )
    assert view.state == "migration_failed"
    with pytest.raises(schema.SchemaCompatibilityError):
        schema.RequireWritableSchemaV1(view)
    assert database_inventory(tmp_path) == before


def test_stale_sidecars_also_refuse_before_sqlite_open(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        open_sqlite_database,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    # Real ordinary SQLite read-only use can leave sidecars after its final close.
    with open_sqlite_database(ref, "runtime_read_only") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").all()
    before = database_inventory(tmp_path)
    assert {"agentmonitor.db-wal", "agentmonitor.db-shm"} <= before.keys()
    view = schema.InspectSchemaCompatibilityV1(
        ref, schema.application_schema_range(), "runtime_read_write"
    )
    assert view.state == "locked"
    assert database_inventory(tmp_path) == before


def test_immutable_inspection_rejects_actual_change_during_read(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        SqlitePolicyError,
        open_sqlite_database,
        open_sqlite_inspection,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    before = database_inventory(tmp_path)
    with pytest.raises(SqlitePolicyError) as caught:
        with open_sqlite_inspection(ref) as reader:
            assert reader.exec_driver_sql("PRAGMA journal_mode").scalar() == "delete"
            assert reader.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert database_inventory(tmp_path) == before
            with open_sqlite_database(ref, "runtime_read_write") as writer:
                with writer.connect() as connection:
                    connection.exec_driver_sql("PRAGMA user_version=2")
                    connection.commit()
            after_writer = database_inventory(tmp_path)
    assert caught.value.code == "database_inspection_changed"
    assert database_inventory(tmp_path) == after_writer
    assert before != after_writer


def test_immutable_inspection_refuses_actual_write_attempt(tmp_path: Path) -> None:
    schema = implementation()
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
        SqlitePolicyError,
        open_sqlite_inspection,
    )

    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    schema.migrate_to_head(ref)
    before = database_inventory(tmp_path)
    with pytest.raises(SqlitePolicyError) as caught:
        with open_sqlite_inspection(ref) as reader:
            reader.exec_driver_sql("PRAGMA user_version=9")
    assert caught.value.code == "persistence_read_only"
    assert database_inventory(tmp_path) == before
