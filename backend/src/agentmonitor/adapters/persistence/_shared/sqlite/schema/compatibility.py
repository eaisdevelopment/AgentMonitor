"""CTR-DB-001 inspection and explicit M1 metadata-only Alembic initialization.

This bounded runner admits only empty bootstrap and current-anchor no-op. Later
business upgrades require M08 backup and DEP quiescence/locking integrations;
they cannot become authorized by adding an unreviewed revision to this catalog.
Catalog and environment digests are pinned in the binary, revisions in catalog.
"""

import ast
import hashlib
import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseOpenModeV1,
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
    open_sqlite_inspection,
)
from agentmonitor.contracts.database_v1 import SchemaCompatibilityV1
from agentmonitor.contracts.foundation_v1 import MigrationMetadataV1
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

MIGRATIONS_PATH = Path(__file__).resolve().parents[7] / "migrations"
CATALOG_SHA256 = "8820eab011f6f99702261d7598f2b89fcbea805798339198c6250bc08a72b742"
ApplicationSchemaRangeV1 = SchemaCompatibilityV1
SchemaState = Literal[
    "missing",
    "empty",
    "upgrade_required",
    "compatible",
    "newer_than_binary",
    "locked",
    "unreadable",
    "corrupt",
    "unknown_revision",
    "multiple_heads",
    "checksum_mismatch",
    "policy_incompatible",
    "migration_failed",
]


class SchemaCompatibilityError(ValueError):
    """Public safe bounded classification, without paths, SQL or stored values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class MigrationCatalogV1:
    version: str
    digest: str
    head: str
    revisions: tuple[MigrationMetadataV1, ...]


@dataclass(frozen=True, slots=True)
class SchemaCompatibilityViewV1:
    state: SchemaState
    current_revision: str | None
    application_range: ApplicationSchemaRangeV1
    integrity_state: Literal["passed", "failed", "not_checked"]
    policy_state: Literal["passed", "failed", "not_checked"]
    migration_required: bool
    reason_codes: tuple[str, ...]
    checked_at: datetime
    catalog_version: str
    mode: DatabaseOpenModeV1


@dataclass(frozen=True, slots=True)
class WritableSchemaReceiptV1:
    revision: str
    catalog_digest: str
    checked_at: datetime


def _read_artifact(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise SchemaCompatibilityError("migration_catalog_invalid")
    return path.read_bytes()


def _text(record: dict[str, object], key: str, *, empty: bool = False) -> str:
    value = record.get(key)
    if not isinstance(value, str) or (not empty and not value) or len(value) > 256:
        raise SchemaCompatibilityError("migration_catalog_invalid")
    return value


def _strings(
    record: dict[str, object], key: str, *, empty: bool = False
) -> tuple[str, ...]:
    value = record.get(key)
    if not isinstance(value, list) or len(value) > 32 or (not value and not empty):
        raise SchemaCompatibilityError("migration_catalog_invalid")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 256:
            raise SchemaCompatibilityError("migration_catalog_invalid")
        result.append(item)
    return tuple(result)


def _metadata(record: dict[str, object], digest: str) -> MigrationMetadataV1:
    revisions = _strings(record, "schema_range")
    if len(revisions) != 5 or any(item != "v1_0000" for item in revisions):
        raise SchemaCompatibilityError("migration_catalog_invalid")
    app = ApplicationSchemaRangeV1(*revisions, catalog_digest=digest)
    return MigrationMetadataV1(
        revision=_text(record, "revision"),
        parent_revision=_text(record, "parent_revision", empty=True) or None,
        owner=_text(record, "owner"),
        plan_id=_text(record, "plan_id"),
        requirement_ids=_strings(record, "requirement_ids"),
        schema_range=app,
        tables=_strings(record, "tables", empty=True),
        portability_notes=_strings(record, "portability_notes"),
        lock_policy=_text(record, "lock_policy"),
        downtime_policy=_text(record, "downtime_policy"),
        expected_data_volume=_text(record, "expected_data_volume"),
        backup_prerequisite=_text(record, "backup_prerequisite"),
        validation_ids=_strings(record, "validation_ids"),
        recovery_policy=_text(record, "recovery_policy"),
        reviewer=_text(record, "reviewer"),
    )


def _validate_revision(source: bytes, record: dict[str, object]) -> None:
    """Inspect literals without executing migration code before trust checks."""
    assignments: dict[str, ast.expr] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id in assignments:
                        raise SchemaCompatibilityError("migration_catalog_invalid")
                    assignments[target.id] = node.value
    for name, expected in (
        ("revision", record["revision"]),
        ("down_revision", None),
        ("branch_labels", None),
        ("depends_on", None),
    ):
        if ast.literal_eval(assignments[name]) != expected:
            raise SchemaCompatibilityError("migration_catalog_invalid")
    metadata = assignments["METADATA"]
    if (
        not isinstance(metadata, ast.Call)
        or not isinstance(metadata.func, ast.Name)
        or metadata.func.id != "MappingProxyType"
        or len(metadata.args) != 1
        or metadata.keywords
    ):
        raise SchemaCompatibilityError("migration_catalog_invalid")
    literal = ast.literal_eval(metadata.args[0])
    expected_metadata = {
        key: tuple(value) if isinstance(value, list) else value
        for key, value in record.items()
        if key not in {"ordinal", "filename", "sha256", "status", "reviewed_at"}
    }
    if literal != expected_metadata:
        raise SchemaCompatibilityError("migration_catalog_invalid")


def load_migration_catalog(
    migrations_path: Path = MIGRATIONS_PATH,
) -> MigrationCatalogV1:
    """Validate the reviewed catalog, full revision inventory and immutable bytes."""
    failure: str | None = None
    result: MigrationCatalogV1 | None = None
    try:
        if migrations_path.is_symlink() or (migrations_path / "versions").is_symlink():
            raise SchemaCompatibilityError("migration_catalog_invalid")
        source = _read_artifact(migrations_path / "catalog.toml")
        digest = hashlib.sha256(source).hexdigest()
        if digest != CATALOG_SHA256:
            raise SchemaCompatibilityError("migration_checksum_mismatch")
        document = tomllib.loads(source.decode("utf-8"))
        if document.keys() != {"version", "head", "env_sha256", "revisions"}:
            raise SchemaCompatibilityError("migration_catalog_invalid")
        records = document["revisions"]
        if (
            document["version"] != "1.0.0"
            or document["head"] != "v1_0000"
            or not isinstance(records, list)
            or len(records) != 1
            or not isinstance(records[0], dict)
        ):
            raise SchemaCompatibilityError("migration_catalog_invalid")
        record = records[0]
        filename = _text(record, "filename")
        if filename != "v1_0000_fnd_anchor.py" or record["ordinal"] != 0:
            raise SchemaCompatibilityError("migration_catalog_invalid")
        inventory = {path.name for path in (migrations_path / "versions").glob("*.py")}
        if inventory != {filename}:
            raise SchemaCompatibilityError("migration_catalog_invalid")
        for path, expected in (
            (migrations_path / "env.py", document["env_sha256"]),
            (migrations_path / "versions" / filename, _text(record, "sha256")),
        ):
            if not isinstance(expected, str) or not re.fullmatch(
                r"[a-f0-9]{64}", expected
            ):
                raise SchemaCompatibilityError("migration_catalog_invalid")
            if hashlib.sha256(_read_artifact(path)).hexdigest() != expected:
                raise SchemaCompatibilityError("migration_checksum_mismatch")
        _validate_revision(
            _read_artifact(migrations_path / "versions" / filename), record
        )
        metadata = _metadata(record, digest)
        if (
            metadata.revision != "v1_0000"
            or metadata.parent_revision is not None
            or metadata.owner != "PLAN-FND"
            or metadata.plan_id != "PLAN-FND"
            or metadata.tables
            or metadata.backup_prerequisite != "none_empty_bootstrap"
            or record["status"] != "shared"
            or not _text(record, "reviewed_at")
        ):
            raise SchemaCompatibilityError("migration_catalog_invalid")
        result = MigrationCatalogV1("1.0.0", digest, "v1_0000", (metadata,))
    except SchemaCompatibilityError as error:
        failure = error.code
    except (OSError, ValueError, KeyError, TypeError, SyntaxError, UnicodeError):
        failure = "migration_catalog_invalid"
    if failure is not None or result is None:
        raise SchemaCompatibilityError(failure or "migration_catalog_invalid") from None
    return result


def application_schema_range() -> ApplicationSchemaRangeV1:
    return load_migration_catalog().revisions[-1].schema_range


def _objects(connection: Connection) -> set[tuple[str, str]]:
    # Schema metadata only: never read business rows or sqlite_schema.sql.
    return {
        (row[0], row[1])
        for row in connection.exec_driver_sql(
            "SELECT type, name FROM sqlite_schema ORDER BY type, name LIMIT 64"
        )
    }


def _inspect(
    connection: Connection, app: ApplicationSchemaRangeV1
) -> tuple[SchemaState, str | None]:
    if connection.exec_driver_sql("PRAGMA quick_check").scalars().fetchmany(2) != [
        "ok"
    ]:
        return "corrupt", None
    objects = _objects(connection)
    if not objects:
        return "empty", None
    allowed = {
        ("table", "alembic_version"),
        ("index", "sqlite_autoindex_alembic_version_1"),
    }
    if not objects <= allowed or ("table", "alembic_version") not in objects:
        return "migration_failed", None
    if not _marker_structure_is_valid(connection):
        return "migration_failed", None
    heads = (
        connection.exec_driver_sql("SELECT version_num FROM alembic_version LIMIT 2")
        .scalars()
        .all()
    )
    if not heads:
        return "upgrade_required", None
    if len(heads) != 1:
        return "multiple_heads", None
    if heads[0] != "v1_0000":
        return "unknown_revision", None
    order = {"base": -1, "v1_0000": 0}
    bounds = (
        app.minimum_readable_revision,
        app.minimum_writable_revision,
        app.maximum_readable_revision,
        app.maximum_writable_revision,
        app.migration_target_revision,
    )
    if any(bound not in order for bound in bounds):
        return "unknown_revision", "v1_0000"
    if (
        order[app.minimum_readable_revision] > order[app.maximum_readable_revision]
        or order[app.minimum_writable_revision] > order[app.maximum_writable_revision]
        or not order[app.minimum_writable_revision]
        <= order[app.migration_target_revision]
        <= order[app.maximum_writable_revision]
    ):
        return "policy_incompatible", "v1_0000"
    if (
        order[app.maximum_readable_revision] < 0
        or order[app.maximum_writable_revision] < 0
    ):
        return "newer_than_binary", "v1_0000"
    return "compatible", "v1_0000"


def _marker_structure_is_valid(connection: Connection) -> bool:
    """Exact admitted Alembic marker, including otherwise invisible constraints.

    All statements/identifiers are code-owned. Only technical schema metadata is
    read, never business content. SQL text remains inside this validator and is
    not returned or attached to errors. Any externally changed structure refuses.
    """
    expected: tuple[tuple[str, list[tuple[object, ...]]], ...] = (
        (
            "PRAGMA table_xinfo(alembic_version)",
            [(0, "version_num", "VARCHAR(32)", 1, None, 1, 0)],
        ),
        (
            "PRAGMA index_list(alembic_version)",
            [(0, "sqlite_autoindex_alembic_version_1", 1, "pk", 0)],
        ),
        (
            "PRAGMA index_xinfo(sqlite_autoindex_alembic_version_1)",
            [(0, 0, "version_num", 0, "BINARY", 1), (1, -1, None, 0, "BINARY", 0)],
        ),
        ("PRAGMA foreign_key_list(alembic_version)", []),
    )
    for statement, rows in expected:
        actual = [
            tuple(row) for row in connection.exec_driver_sql(statement).fetchmany(3)
        ]
        if actual != rows:
            return False
    definition = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_schema WHERE type='table' AND name='alembic_version'"
    ).scalar()
    # PRAGMA does not expose CHECK expressions or the PK constraint name. The
    # pinned Alembic dialect emits this one statement for the approved anchor.
    return isinstance(definition, str) and " ".join(definition.split()) == (
        "CREATE TABLE alembic_version ( version_num VARCHAR(32) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num) )"
    )


def InspectSchemaCompatibilityV1(
    database_ref: DatabaseRefV1,
    application_range: ApplicationSchemaRangeV1,
    mode: DatabaseOpenModeV1,
) -> SchemaCompatibilityViewV1:
    """Read-only inspection. Never creates a file, DDL, revision or repair."""
    state: SchemaState = "policy_incompatible"
    current: str | None = None
    integrity: Literal["passed", "failed", "not_checked"] = "not_checked"
    policy: Literal["passed", "failed", "not_checked"] = "not_checked"
    catalog_version = "unknown"
    try:
        catalog = load_migration_catalog()
        catalog_version = catalog.version
        if application_range.catalog_digest != catalog.digest:
            state = "checksum_mismatch"
        elif mode not in {"runtime_read_only", "runtime_read_write"}:
            state = "policy_incompatible"
        elif database_ref.validate(missing_ok=True) is None:
            state = "missing"
        else:
            with open_sqlite_inspection(database_ref) as connection:
                state, current = _inspect(connection, application_range)
                policy = "passed"
                integrity = "failed" if state == "corrupt" else "passed"
    except SchemaCompatibilityError:
        state = "checksum_mismatch"
    except SqlitePolicyError as error:
        states: dict[str, SchemaState] = {
            "database_missing": "missing",
            "persistence_busy": "locked",
            "database_inspection_requires_quiescence": "locked",
            "database_inspection_changed": "locked",
            "database_identity_changed": "locked",
            "persistence_corrupt": "corrupt",
            "database_policy_incompatible": "policy_incompatible",
        }
        state = states.get(error.code, "unreadable")
        if state == "policy_incompatible":
            policy = "failed"
        if state == "corrupt":
            integrity = "failed"
    except OSError:
        state = "unreadable"
    return SchemaCompatibilityViewV1(
        state,
        current,
        application_range,
        integrity,
        policy,
        state in {"missing", "empty", "upgrade_required"},
        (state,),
        datetime.now(UTC),
        catalog_version,
        mode,
    )


def RequireWritableSchemaV1(view: SchemaCompatibilityViewV1) -> WritableSchemaReceiptV1:
    """A readiness receipt, not a connection or authorization for migration."""
    if (
        view.state != "compatible"
        or view.current_revision != "v1_0000"
        or view.integrity_state != "passed"
        or view.policy_state != "passed"
        or view.mode != "runtime_read_write"
        or view.migration_required
        or view.application_range != application_schema_range()
    ):
        raise SchemaCompatibilityError("schema_not_writable") from None
    return WritableSchemaReceiptV1(
        view.current_revision, view.application_range.catalog_digest, view.checked_at
    )


def migrate_to_head(
    database_ref: DatabaseRefV1, *, migrations_path: Path = MIGRATIONS_PATH
) -> None:
    """Explicit offline M1 bootstrap through real Alembic; no business upgrades.

    BEGIN IMMEDIATE serializes competing writers. On failure rollback/close and
    preserve the exact target; there is no delete, retry, downgrade or recovery
    claim. AUTO-MIGRATE's later backup/quiescence workflow remains separate.
    """
    catalog = load_migration_catalog(migrations_path)
    exists = database_ref.validate(missing_ok=True) is not None
    if exists:
        view = InspectSchemaCompatibilityV1(
            database_ref, catalog.revisions[-1].schema_range, "runtime_read_write"
        )
        if view.state == "compatible":
            return
        if view.state not in {"empty", "upgrade_required"}:
            raise SchemaCompatibilityError("migration_preflight_refused") from None
    failure: str | None = None
    try:
        mode: DatabaseOpenModeV1 = (
            "migration_existing" if exists else "migration_initialize"
        )
        with open_sqlite_database(database_ref, mode) as handle:
            with handle.connect() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                state, _ = _inspect(connection, catalog.revisions[-1].schema_range)
                if state not in {"empty", "upgrade_required", "compatible"}:
                    raise SchemaCompatibilityError("migration_preflight_refused")
                config = Config()
                config.set_main_option(
                    "script_location", str(migrations_path).replace("%", "%%")
                )
                config.attributes.update(
                    connection=connection,
                    migrations_path=migrations_path,
                    catalog_digest=catalog.digest,
                )
                command.upgrade(config, catalog.head)
                if (
                    _inspect(connection, catalog.revisions[-1].schema_range)[0]
                    != "compatible"
                    or connection.exec_driver_sql("PRAGMA integrity_check")
                    .scalars()
                    .fetchmany(2)
                    != ["ok"]
                    or connection.exec_driver_sql("PRAGMA foreign_key_check").first()
                    is not None
                ):
                    raise SchemaCompatibilityError("migration_validation_failed")
                connection.commit()
    except (SchemaCompatibilityError, SqlitePolicyError) as error:
        failure = error.code
    except Exception:
        # Alembic boundary: never expose script paths, SQL or stored values.
        failure = "migration_failed"
    if failure is not None:
        raise SchemaCompatibilityError(failure) from None
