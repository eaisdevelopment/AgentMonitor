"""M02-local atomic invalidation of independent billing monitoring authority."""

from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence.registry.sqlite.registry_transaction import (
    _append_outbox,
    _digest,
    _identifier,
    _next_revision,
    _utc_text,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from sqlalchemy.engine import Connection


def invalidate_billing_monitoring_in_transaction(
    connection: Connection,
    account_id: OpaqueIdV1,
    *,
    disconnected: bool,
) -> None:
    """Revoke enabled billing authority in the binding/account transaction."""
    if not connection.in_transaction():
        raise ValueError("billing_monitoring_transaction_required")
    row = (
        connection.exec_driver_sql(
            "SELECT resource_id,lifecycle,monitoring_preference,record_version,"
            "updated_at FROM reg_billing_connection WHERE account_id=?",
            (account_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return
    target_lifecycle = "disconnected" if disconnected else "pending"
    if row["lifecycle"] == "disconnected":
        return
    if (
        row["lifecycle"] == target_lifecycle
        and row["monitoring_preference"] == "disabled"
    ):
        return
    occurred_at = datetime.now(UTC)
    instant = _utc_text(occurred_at)
    if instant < row["updated_at"]:
        raise ValueError("billing_monitoring_time_invalid")
    version = int(row["record_version"]) + 1
    revision = _next_revision(connection, instant)
    updated = connection.exec_driver_sql(
        "UPDATE reg_billing_connection SET lifecycle=?,"
        "monitoring_preference='disabled',record_version=?,registry_revision=?,"
        "updated_at=? WHERE account_id=? AND resource_id=? AND lifecycle=? "
        "AND monitoring_preference=? AND record_version=? AND updated_at=?",
        (
            target_lifecycle,
            version,
            revision,
            instant,
            account_id.value,
            row["resource_id"],
            row["lifecycle"],
            row["monitoring_preference"],
            row["record_version"],
            row["updated_at"],
        ),
    )
    if updated.rowcount != 1:
        raise ValueError("billing_monitoring_conflict")
    correlation_id = _identifier()
    connection.exec_driver_sql(
        "INSERT INTO reg_registry_change "
        "(change_id,subject_type,subject_id,aggregate_version,registry_revision,"
        "change_kind,previous_name,new_name,previous_organization_id,"
        "new_organization_id,previous_lifecycle,new_lifecycle,actor_class,"
        "actor_id,correlation_id,command_digest,occurred_at,recorded_at,expires_at) "
        "VALUES (?,'resource',?,?,?,?,NULL,NULL,NULL,NULL,?,?,'system',"
        "'agentmonitor',?,?,?,?,?)",
        (
            _identifier(),
            row["resource_id"],
            version,
            revision,
            "billing_monitoring_invalidated",
            row["lifecycle"],
            target_lifecycle,
            correlation_id,
            _digest(correlation_id),
            instant,
            instant,
            _utc_text(occurred_at + timedelta(days=365)),
        ),
    )
    _append_outbox(
        connection,
        subject_type="resource",
        subject_id=str(row["resource_id"]),
        aggregate_version=version,
        revision=revision,
        change_kind="billing_monitoring_invalidated",
        correlation_id=correlation_id,
        causation_id=correlation_id,
        instant=instant,
    )
