"""M02 coverage record encoding and atomic revision/invalidation writes."""

from dataclasses import replace
from datetime import datetime
from typing import Literal, cast

from agentmonitor.adapters.persistence.registry.sqlite.registry_transaction import (
    _append_change,
    _append_outbox,
    _digest,
    _utc_text,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_coverage_v1 import (
    CoverageInvalidationReasonV1,
    CoverageOutcomeV1,
    CoverageUnavailableReasonV1,
    OrganizationProviderCoverageV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from sqlalchemy.engine import Connection, RowMapping

_COLUMNS = (
    "coverage_id,organization_id,provider_key,outcome,account_id,"
    "account_organization_id,unavailable_reason,provenance,confirmed_by,"
    "confirmed_at,record_version,registry_revision,invalidated_at,invalidation_reason"
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
