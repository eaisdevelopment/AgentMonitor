"""CTR-DB-001 real live metadata leaf; integrity checks occur only at startup."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from agentmonitor.adapters.persistence._shared.sqlite.core.bounded_read import (
    BoundedSqliteReadConnectionV1,
    open_bounded_sqlite_read,
)
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseOpenModeV1,
    DatabaseRefV1,
    SqlitePolicyError,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    SchemaCompatibilityError,
    SchemaCompatibilityViewV1,
    load_migration_catalog,
)
from agentmonitor.contracts.database_v1 import (
    DatabaseHealthReasonV1,
    DatabaseHealthRequestV1,
    DatabaseHealthV1,
    DatabaseSchemaStateV1,
    SchemaCompatibilityV1,
)

_METADATA_TABLES = frozenset({"sqlite_schema", "alembic_version"})
_MARKER_DEFINITION = (
    "CREATE TABLE alembic_version ( version_num VARCHAR(32) NOT NULL, "
    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num) )"
)


def _schema_metadata(reader: BoundedSqliteReadConnectionV1) -> tuple[str, bool, bool]:
    rows = reader.fetch_many(
        "SELECT type, name, sql FROM sqlite_schema ORDER BY type, name LIMIT 513",
        limit=513,
    )
    if len(rows) > 512:
        raise SqlitePolicyError("database_policy_incompatible")
    marker_valid = any(
        kind == "table"
        and name == "alembic_version"
        and isinstance(sql, str)
        and " ".join(sql.split()) == _MARKER_DEFINITION
        for kind, name, sql in rows
    )
    fingerprint = hashlib.sha256(
        json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return fingerprint, bool(rows), marker_valid


@dataclass(frozen=True, slots=True)
class StartupDatabaseHealthReceiptV1:
    """Internal receipt bound to an actual inspected file; never transported."""

    _identity: tuple[int, int] = field(repr=False)
    _revision: str = field(repr=False)
    _catalog_digest: str = field(repr=False)
    _schema_fingerprint: str = field(repr=False)
    _integrity_checked_at: datetime = field(repr=False)


def InspectStartupDatabaseHealthV1(
    database_ref: DatabaseRefV1,
    application_range: SchemaCompatibilityV1,
    mode: DatabaseOpenModeV1,
) -> tuple[SchemaCompatibilityViewV1, StartupDatabaseHealthReceiptV1 | None]:
    """Explicit startup action wrapping the existing genuine integrity check.

    Root invokes before runtime writer creation. Health GET never calls this.
    A missing or failed startup check cannot mint a receipt.
    """
    before = database_ref.validate(missing_ok=True)
    view = InspectSchemaCompatibilityV1(database_ref, application_range, mode)
    after = database_ref.validate(missing_ok=True)
    if before != after:
        raise SqlitePolicyError("database_identity_changed") from None
    if (
        before is None
        or view.state != "compatible"
        or view.integrity_state != "passed"
        or view.policy_state != "passed"
        or view.current_revision is None
    ):
        return view, None
    with open_bounded_sqlite_read(
        database_ref,
        deadline=datetime.now(UTC) + timedelta(seconds=2),
        allowed_tables=_METADATA_TABLES,
    ) as reader:
        fingerprint, _, marker_valid = _schema_metadata(reader)
        heads = reader.fetch_many(
            "SELECT version_num FROM alembic_version LIMIT 2", limit=2
        )
        if not marker_valid or heads != ((view.current_revision,),):
            raise SqlitePolicyError("database_startup_receipt_invalid")
    if database_ref.validate() != before:
        raise SqlitePolicyError("database_identity_changed") from None
    return view, StartupDatabaseHealthReceiptV1(
        before,
        view.current_revision,
        application_range.catalog_digest,
        fingerprint,
        view.checked_at,
    )


class LiveDatabaseHealthReaderV1:
    CONTRACT_ID: ClassVar[str] = "CTR-DB-001"
    OWNER: ClassVar[str] = "PLAN-DB"

    def __init__(
        self, database_ref: DatabaseRefV1, application_range: SchemaCompatibilityV1
    ) -> None:
        self._reference = database_ref
        self._range = application_range
        self._startup: StartupDatabaseHealthReceiptV1 | None = None
        self._catalog_verified = False
        self._order: dict[str, int] = {}
        try:
            catalog = load_migration_catalog()
            self._catalog_verified = catalog.digest == application_range.catalog_digest
            self._order = {
                "base": 0,
                **{
                    item.revision: index + 1
                    for index, item in enumerate(catalog.revisions)
                },
            }
        except SchemaCompatibilityError:
            pass

    def bind_startup_receipt(self, receipt: StartupDatabaseHealthReceiptV1) -> None:
        if self._startup is not None:
            raise SqlitePolicyError("database_startup_receipt_already_bound") from None
        if (
            not isinstance(receipt, StartupDatabaseHealthReceiptV1)
            or not self._catalog_verified
            or receipt._catalog_digest != self._range.catalog_digest
            or receipt._revision not in self._order
            or receipt._revision != self._range.migration_target_revision
            or receipt._integrity_checked_at.utcoffset() != timedelta(0)
            or receipt._integrity_checked_at > datetime.now(UTC)
            or self._reference.validate() != receipt._identity
        ):
            raise SqlitePolicyError("database_startup_receipt_invalid") from None
        self._startup = receipt

    def _range_state(self, revision: str) -> DatabaseSchemaStateV1 | None:
        bounds = (
            self._range.minimum_readable_revision,
            self._range.minimum_writable_revision,
            self._range.maximum_readable_revision,
            self._range.maximum_writable_revision,
            self._range.migration_target_revision,
        )
        if any(bound not in self._order for bound in bounds):
            return "unknown_revision"
        minimum_read, minimum_write, maximum_read, maximum_write, target = (
            self._order[bound] for bound in bounds
        )
        if (
            minimum_read > maximum_read
            or minimum_write > maximum_write
            or not minimum_write <= target <= maximum_write
        ):
            return "policy_incompatible"
        current = self._order[revision]
        if current > maximum_read or current > maximum_write:
            return "newer_than_binary"
        if current < minimum_read or current < minimum_write:
            return "upgrade_required"
        return None

    async def __call__(self, request: DatabaseHealthRequestV1) -> DatabaseHealthV1:
        """Small synchronous local read; closed before this coroutine returns."""
        state: DatabaseSchemaStateV1 | None = None
        revision: str | None = None
        integrity: str = "not_checked"
        integrity_at: datetime | None = None
        reachable = False
        policy: str = "not_checked"
        reason: DatabaseHealthReasonV1 = "database_health_unverified"
        if not self._catalog_verified:
            return DatabaseHealthV1(
                False,
                None,
                "checksum_mismatch",
                "not_checked",
                None,
                "not_checked",
                datetime.now(UTC),
                ("database_checksum_mismatch",),
            )
        try:
            if (
                self._startup is not None
                and self._reference.validate() != self._startup._identity
            ):
                raise SqlitePolicyError("database_identity_changed")
            with open_bounded_sqlite_read(
                self._reference,
                deadline=request.deadline,
                allowed_tables=_METADATA_TABLES,
            ) as reader:
                policy = "passed"
                fingerprint, has_objects, valid_marker = _schema_metadata(reader)
                reachable = True
                if not has_objects:
                    state, reason = "empty", "database_empty"
                elif not valid_marker:
                    state, reason = "migration_failed", "database_migration_failed"
                else:
                    heads = reader.fetch_many(
                        "SELECT version_num FROM alembic_version LIMIT 2", limit=2
                    )
                    if not heads:
                        state, reason = "upgrade_required", "database_upgrade_required"
                    elif len(heads) != 1:
                        state, reason = "multiple_heads", "database_multiple_heads"
                    elif (
                        not isinstance(heads[0][0], str)
                        or heads[0][0] not in self._order
                        or heads[0][0] == "base"
                    ):
                        state, reason = "unknown_revision", "database_unknown_revision"
                    else:
                        revision = heads[0][0]
                        state = self._range_state(revision)
                        if state == "upgrade_required":
                            reason = "database_upgrade_required"
                        elif state == "newer_than_binary":
                            reason = "database_newer_than_binary"
                        elif state == "unknown_revision":
                            reason = "database_unknown_revision"
                        elif state == "policy_incompatible":
                            reason = "database_policy_incompatible"
                        elif (
                            self._startup is not None
                            and self._startup._revision == revision
                        ):
                            if self._startup._schema_fingerprint != fingerprint:
                                state, reason = (
                                    "migration_failed",
                                    "database_schema_changed",
                                )
                            else:
                                state, reason = "compatible", "database_health_complete"
                                integrity, integrity_at = (
                                    "passed",
                                    self._startup._integrity_checked_at,
                                )
        except SqlitePolicyError as error:
            reachable = False
            revision = None
            integrity, integrity_at = "not_checked", None
            if error.code == "database_missing":
                state, reason = "missing", "database_missing"
            elif error.code in {"database_timeout", "persistence_busy"}:
                state = "locked"
                reason = (
                    "database_timeout"
                    if error.code == "database_timeout"
                    else "database_locked"
                )
            elif error.code == "database_identity_changed":
                state, reason = None, "database_identity_changed"
            elif error.code == "persistence_corrupt":
                state, reason = "corrupt", "database_corrupt"
            elif error.code in {
                "database_permissions_unsafe",
                "database_reference_unsafe",
                "database_policy_incompatible",
                "database_reference_invalid",
                "database_read_policy_invalid",
            }:
                state, reason, policy = (
                    "policy_incompatible",
                    "database_policy_incompatible",
                    "failed",
                )
            else:
                state, reason = "unreadable", "database_unreadable"
        return DatabaseHealthV1(
            reachable,
            revision,
            state,
            "passed" if integrity == "passed" else "not_checked",
            integrity_at,
            "passed"
            if policy == "passed"
            else "failed"
            if policy == "failed"
            else "not_checked",
            datetime.now(UTC),
            (reason,),
        )
