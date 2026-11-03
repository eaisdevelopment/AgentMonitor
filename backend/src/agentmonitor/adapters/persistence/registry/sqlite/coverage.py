"""M02 transactional coverage declarations over the real SQLite registry."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import ClassVar, Literal, cast

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    RegistryRepositoryErrorV1,
    _append_change,
    _append_outbox,
    _current_revision,
    _digest,
    _fingerprint,
    _identifier,
    _next_revision,
    _utc_text,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_coverage_v1 import (
    CoverageInvalidationReasonV1,
    CoverageOutcomeV1,
    CoverageUnavailableReasonV1,
    OrganizationProviderCoverageSelectionV1,
    OrganizationProviderCoverageSnapshotV1,
    OrganizationProviderCoverageV1,
    RevokeOrganizationProviderCoverageCommandV1,
    SetOrganizationProviderCoverageCommandV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from agentmonitor.modules.registry.domain.coverage import coverage_reference_failure
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

_COLUMNS = (
    "coverage_id,organization_id,provider_key,outcome,account_id,"
    "account_organization_id,unavailable_reason,provenance,confirmed_by,"
    "confirmed_at,record_version,registry_revision,invalidated_at,invalidation_reason"
)
_Command = (
    SetOrganizationProviderCoverageCommandV1
    | RevokeOrganizationProviderCoverageCommandV1
)


def _time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("registry_coverage_timestamp_invalid")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _optional_id(value: object) -> OpaqueIdV1 | None:
    return None if value is None else OpaqueIdV1(str(value))


def _view(row: RowMapping) -> OrganizationProviderCoverageV1:
    return OrganizationProviderCoverageV1(
        coverage_id=OpaqueIdV1(str(row["coverage_id"])),
        organization_id=OpaqueIdV1(str(row["organization_id"])),
        provider_key=str(row["provider_key"]),
        outcome=cast(CoverageOutcomeV1, row["outcome"]),
        account_id=_optional_id(row["account_id"]),
        account_organization_id=_optional_id(row["account_organization_id"]),
        unavailable_reason=cast(
            CoverageUnavailableReasonV1 | None, row["unavailable_reason"]
        ),
        provenance=cast("Literal['owner_asserted']", row["provenance"]),
        confirmed_by=OpaqueIdV1(str(row["confirmed_by"])),
        confirmed_at=_time(row["confirmed_at"]),
        record_version=int(row["record_version"]),
        registry_revision=int(row["registry_revision"]),
        invalidated_at=None
        if row["invalidated_at"] is None
        else _time(row["invalidated_at"]),
        invalidation_reason=cast(
            CoverageInvalidationReasonV1 | None, row["invalidation_reason"]
        ),
    )


def _find(
    connection: Connection, organization_id: str, provider_key: str
) -> OrganizationProviderCoverageV1 | None:
    row = (
        connection.exec_driver_sql(
            "SELECT " + _COLUMNS + " FROM reg_organization_provider_coverage "
            "WHERE organization_id=? AND provider_key=?",
            (organization_id, provider_key),
        )
        .mappings()
        .one_or_none()
    )
    return None if row is None else _view(row)


def _values(item: OrganizationProviderCoverageV1) -> tuple[object, ...]:
    return (
        item.coverage_id.value,
        item.organization_id.value,
        item.provider_key,
        item.outcome,
        item.account_id.value if item.account_id else None,
        item.account_organization_id.value if item.account_organization_id else None,
        item.unavailable_reason,
        item.provenance,
        item.confirmed_by.value,
        _utc_text(item.confirmed_at),
        item.record_version,
        item.registry_revision,
        _utc_text(item.invalidated_at) if item.invalidated_at else None,
        item.invalidation_reason,
    )


def _persist(
    connection: Connection,
    item: OrganizationProviderCoverageV1,
    *,
    principal_id: str,
    command_id: str,
    instant: str,
    change_kind: str,
) -> None:
    columns = _COLUMNS.split(",")
    assignments = ",".join(column + "=excluded." + column for column in columns[1:])
    connection.exec_driver_sql(
        "INSERT INTO reg_organization_provider_coverage (" + _COLUMNS + ") "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(coverage_id) DO UPDATE SET "
        + assignments,
        _values(item),
    )
    connection.exec_driver_sql(
        "INSERT INTO reg_organization_provider_coverage_revision (" + _COLUMNS + ") "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _values(item),
    )
    _append_change(
        connection,
        subject_type="organization_provider_coverage",
        subject_id=item.coverage_id.value,
        aggregate_version=item.record_version,
        revision=item.registry_revision,
        change_kind=change_kind,
        actor_id=principal_id,
        correlation_id=command_id,
        command_digest=_digest(command_id),
        instant=instant,
    )
    _append_outbox(
        connection,
        subject_type="organization_provider_coverage",
        subject_id=item.coverage_id.value,
        aggregate_version=item.record_version,
        revision=item.registry_revision,
        change_kind=change_kind,
        correlation_id=command_id,
        causation_id=command_id,
        instant=instant,
    )


def _reference_failure(
    connection: Connection, item: OrganizationProviderCoverageV1
) -> CoverageInvalidationReasonV1 | None:
    active_orgs = set(
        connection.exec_driver_sql(
            "SELECT organization_id FROM reg_organization WHERE lifecycle='active' "
            "AND organization_id IN (?,?)",
            (
                item.organization_id.value,
                item.account_organization_id.value
                if item.account_organization_id
                else None,
            ),
        ).scalars()
    )
    provider = connection.exec_driver_sql(
        "SELECT lifecycle FROM reg_provider_definition WHERE provider_key=?",
        (item.provider_key,),
    ).scalar_one_or_none()
    account = (
        connection.exec_driver_sql(
            "SELECT lifecycle,provider_key,organization_id FROM reg_account "
            "WHERE account_id=?",
            (item.account_id.value if item.account_id else None,),
        )
        .mappings()
        .one_or_none()
    )
    return coverage_reference_failure(
        outcome=item.outcome,
        organization_id=item.organization_id.value,
        account_organization_id=str(account["organization_id"])
        if account is not None and account["organization_id"] is not None
        else None,
        recorded_account_organization_id=item.account_organization_id.value
        if item.account_organization_id
        else None,
        organization_active=item.organization_id.value in active_orgs,
        provider_active=provider == "active",
        account_present=account is not None,
        account_archived=account is not None and account["lifecycle"] == "archived",
        provider_matches=account is not None
        and account["provider_key"] == item.provider_key,
        source_organization_active=item.account_organization_id is not None
        and item.account_organization_id.value in active_orgs,
    )


def invalidate_coverage_in_transaction(
    connection: Connection,
    *,
    account_id: str | None = None,
    organization_id: str | None = None,
    reason: CoverageInvalidationReasonV1,
    revision: int,
    principal_id: str,
    command_id: str,
    instant: str,
) -> None:
    """Retire assertions atomically with the actual owning registry mutation."""
    if (account_id is None) == (organization_id is None):
        raise ValueError("registry_coverage_invalidation_selector_invalid")
    rows = (
        connection.exec_driver_sql(
            "SELECT " + _COLUMNS + " FROM reg_organization_provider_coverage "
            "WHERE invalidated_at IS NULL AND (account_id=? OR organization_id=? "
            "OR account_organization_id=?) ORDER BY coverage_id",
            (account_id, organization_id, organization_id),
        )
        .mappings()
        .all()
    )
    at = _time(instant)
    for row in rows:
        item = _view(row)
        selected_reason = reason
        if (
            reason == "organization_archived"
            and item.organization_id.value != organization_id
        ):
            selected_reason = "source_organization_archived"
        if at < item.confirmed_at:
            raise RegistryCommandConflictV1("registry_coverage_timestamp_conflict")
        invalidated = replace(
            item,
            invalidated_at=at,
            invalidation_reason=selected_reason,
            record_version=item.record_version + 1,
            registry_revision=revision,
        )
        _persist(
            connection,
            invalidated,
            principal_id=principal_id,
            command_id=command_id,
            instant=instant,
            change_kind="invalidated",
        )


class SqliteOrganizationProviderCoverageRepositoryV1:
    CONTRACT_ID: ClassVar[str] = "CTR-REG-013"
    OWNER: ClassVar[str] = "PLAN-M02"

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    def read_coverage(
        self, selection: OrganizationProviderCoverageSelectionV1
    ) -> OrganizationProviderCoverageSnapshotV1:
        revision = 0
        try:
            with open_sqlite_database(self._reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    revision = _current_revision(connection)
                    items = tuple(
                        item
                        for organization_id in selection.organization_ids
                        if (
                            item := _find(
                                connection,
                                organization_id.value,
                                selection.provider_key,
                            )
                        )
                        is not None
                    )
                    if any(
                        item.invalidated_at is None
                        and _reference_failure(connection, item)
                        for item in items
                    ):
                        raise RegistryRepositoryErrorV1(
                            "registry_coverage_reference_invalid"
                        )
                    return OrganizationProviderCoverageSnapshotV1(
                        selection, items, revision, "complete", datetime.now(UTC)
                    )
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            return OrganizationProviderCoverageSnapshotV1(
                selection, (), revision, "unavailable", datetime.now(UTC)
            )

    def set_coverage(
        self, command: SetOrganizationProviderCoverageCommandV1
    ) -> OrganizationProviderCoverageV1:
        return self._write(command)

    def revoke_coverage(
        self, command: RevokeOrganizationProviderCoverageCommandV1
    ) -> OrganizationProviderCoverageV1:
        return self._write(command)

    def _write(self, command: _Command) -> OrganizationProviderCoverageV1:
        operation = (
            "set_organization_provider_coverage"
            if isinstance(command, SetOrganizationProviderCoverageCommandV1)
            else "revoke_organization_provider_coverage"
        )
        command_digest = _digest(command.command_id.value)
        payload: dict[str, object] = {
            "organization_id": command.organization_id.value,
            "provider_key": command.provider_key,
            "expected_version": command.expected_version,
        }
        if isinstance(command, SetOrganizationProviderCoverageCommandV1):
            payload.update(
                outcome=command.outcome,
                account_id=command.account_id.value if command.account_id else None,
                expected_account_record_version=command.expected_account_record_version,
                unavailable_reason=command.unavailable_reason,
            )
        fingerprint = _fingerprint(payload)
        instant = _utc_text(command.requested_at)
        try:
            with open_sqlite_database(self._reference, "runtime_read_write") as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    current = _find(
                        connection, command.organization_id.value, command.provider_key
                    )
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint,outcome_subject_id,"
                            "outcome_record_version "
                            "FROM reg_command_receipt WHERE principal_id=? "
                            "AND operation_key=? "
                            "AND idempotency_key_digest=?",
                            (command.principal_id.value, operation, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if receipt is not None:
                        if receipt["request_fingerprint"] != fingerprint:
                            raise RegistryCommandConflictV1(
                                "registry_idempotency_conflict"
                            )
                        if (
                            current is None
                            or current.coverage_id.value
                            != receipt["outcome_subject_id"]
                            or current.record_version
                            != receipt["outcome_record_version"]
                        ):
                            raise RegistryCommandConflictV1("registry_replay_stale")
                        if current.invalidated_at is None and _reference_failure(
                            connection, current
                        ):
                            raise RegistryCommandConflictV1(
                                "registry_coverage_reference_invalid"
                            )
                        connection.rollback()
                        return current
                    if (
                        current.record_version if current else 0
                    ) != command.expected_version:
                        raise RegistryCommandConflictV1("registry_version_conflict")
                    if current is not None and command.requested_at < max(
                        current.confirmed_at,
                        current.invalidated_at or current.confirmed_at,
                    ):
                        raise RegistryCommandConflictV1(
                            "registry_coverage_timestamp_conflict"
                        )
                    if isinstance(command, SetOrganizationProviderCoverageCommandV1):
                        next_item = self._set_record(connection, command, current)
                        change_kind = "asserted"
                    else:
                        if current is None:
                            raise RegistryCommandConflictV1(
                                "registry_subject_not_found"
                            )
                        next_item = replace(
                            current,
                            record_version=current.record_version + 1,
                            registry_revision=_next_revision(connection, instant),
                            invalidated_at=command.requested_at,
                            invalidation_reason="owner_revoked",
                        )
                        change_kind = "revoked"
                    _persist(
                        connection,
                        next_item,
                        principal_id=command.principal_id.value,
                        command_id=command.command_id.value,
                        instant=instant,
                        change_kind=change_kind,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id,principal_id,operation_key,"
                        "idempotency_key_digest,request_fingerprint,outcome_subject_type,"
                        "outcome_subject_id,outcome_record_version,registry_revision,"
                        "created_at,expires_at) "
                        "VALUES (?,?,?,?,?,'organization_provider_coverage',?,?,?,?,?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            fingerprint,
                            next_item.coverage_id.value,
                            next_item.record_version,
                            next_item.registry_revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    connection.commit()
                    return next_item
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1(
                "registry_coverage_repository_unavailable"
            ) from None

    @staticmethod
    def _set_record(
        connection: Connection,
        command: SetOrganizationProviderCoverageCommandV1,
        current: OrganizationProviderCoverageV1 | None,
    ) -> OrganizationProviderCoverageV1:
        account_org: OpaqueIdV1 | None = None
        if command.account_id is not None:
            account = (
                connection.exec_driver_sql(
                    "SELECT record_version,organization_id FROM reg_account "
                    "WHERE account_id=?",
                    (command.account_id.value,),
                )
                .mappings()
                .one_or_none()
            )
            if account is None:
                raise RegistryCommandConflictV1("registry_subject_not_found")
            if account["record_version"] != command.expected_account_record_version:
                raise RegistryCommandConflictV1("registry_account_version_conflict")
            account_org = _optional_id(account["organization_id"])
            if account_org is None or (
                (command.outcome == "account")
                != (account_org == command.organization_id)
            ):
                raise RegistryCommandConflictV1("registry_coverage_reference_invalid")
        item = OrganizationProviderCoverageV1(
            coverage_id=current.coverage_id if current else OpaqueIdV1(_identifier()),
            organization_id=command.organization_id,
            provider_key=command.provider_key,
            outcome=command.outcome,
            account_id=command.account_id,
            account_organization_id=account_org,
            unavailable_reason=command.unavailable_reason,
            provenance="owner_asserted",
            confirmed_by=command.principal_id,
            confirmed_at=command.requested_at,
            record_version=(current.record_version if current else 0) + 1,
            registry_revision=max(1, _current_revision(connection)),
            invalidated_at=None,
            invalidation_reason=None,
        )
        if _reference_failure(connection, item) is not None:
            raise RegistryCommandConflictV1("registry_coverage_reference_invalid")
        return replace(
            item,
            registry_revision=_next_revision(
                connection, _utc_text(command.requested_at)
            ),
        )
