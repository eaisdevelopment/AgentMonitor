"""M02 billing metadata transactions, independent of subscription enrollment."""

from datetime import datetime, timedelta
from typing import Literal, cast

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    read_credential_bindings_in_transaction,
    resolve_active_credential_binding_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.registry_transaction import (
    RegistryRepositoryErrorV1,
    _append_change,
    _append_outbox,
    _digest,
    _fingerprint,
    _identifier,
    _next_revision,
    _utc_text,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    AccountBillingConnectionsV1,
    BillingAccessPurposeV1,
    BillingAccessTargetV1,
    BillingConnectionViewV1,
    CreateBillingConnectionCommandV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from agentmonitor.modules.registry.domain.billing_connection import (
    billing_access_target,
    billing_connection_eligibility,
    billing_credential_status,
    ensure_billing_access_current,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

_OPERATION = "create_billing_connection"


def _view(row: RowMapping, provider: str) -> BillingConnectionViewV1:
    return BillingConnectionViewV1(
        account_id=OpaqueIdV1(row["account_id"]),
        resource_id=OpaqueIdV1(row["resource_id"]),
        provider_key=cast(Literal["claude", "codex", "ollama"], provider),
        scope_id=row["scope_id"],
        scope_evidence=row["scope_evidence"],
        scope_generation=row["scope_generation"],
        monitoring_preference=row["monitoring_preference"],
        lifecycle=row["lifecycle"],
        record_version=row["record_version"],
        registry_revision=row["registry_revision"],
        created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
    )


def _get(
    connection: Connection, account_id: OpaqueIdV1
) -> AccountBillingConnectionsV1 | None:
    account = (
        connection.exec_driver_sql(
            "SELECT provider_key, lifecycle, record_version FROM reg_account "
            "WHERE account_id=?",
            (account_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if account is None:
        return None
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM reg_billing_connection WHERE account_id=?",
            (account_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    connections = () if row is None else (_view(row, account["provider_key"]),)
    can_add, reason = billing_connection_eligibility(
        account["provider_key"], account["lifecycle"], bool(connections)
    )
    return AccountBillingConnectionsV1(
        account_id=account_id,
        provider_key=account["provider_key"],
        account_lifecycle=account["lifecycle"],
        account_record_version=account["record_version"],
        can_add_connection=can_add,
        reason_code=reason,
        connections=connections,
        credential_status=(
            billing_credential_status(
                read_credential_bindings_in_transaction(connection, account_id)
            )
            if connections
            else None
        ),
    )


class SqliteBillingConnectionRepositoryV1:
    """CTR-REG-014 metadata only; never accesses credentials or provider APIs."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def get(self, account_id: OpaqueIdV1) -> AccountBillingConnectionsV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    result = _get(connection, account_id)
                    connection.rollback()
                    return result
        except (SQLAlchemyError, SqlitePolicyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def create(
        self, command: CreateBillingConnectionCommandV1
    ) -> BillingConnectionViewV1:
        instant = _utc_text(command.requested_at)
        command_digest = _digest(command.command_id.value)
        fingerprint = _fingerprint(
            {
                "operation": _OPERATION,
                "account_id": command.account_id.value,
                "expected_account_version": command.expected_account_version,
                "scope_id": command.scope_id,
            }
        )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint, outcome_subject_id, "
                            "outcome_record_version FROM reg_command_receipt "
                            "WHERE principal_id=? AND operation_key=? "
                            "AND idempotency_key_digest=?",
                            (command.principal_id.value, _OPERATION, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if (
                        receipt is not None
                        and receipt["request_fingerprint"] != fingerprint
                    ):
                        raise RegistryCommandConflictV1("registry_idempotency_conflict")
                    status = _get(connection, command.account_id)
                    if receipt is not None:
                        if status is None or not status.connections:
                            raise RegistryCommandConflictV1("registry_replay_stale")
                        result = status.connections[0]
                        if (
                            result.resource_id.value != receipt["outcome_subject_id"]
                            or result.record_version
                            != receipt["outcome_record_version"]
                        ):
                            raise RegistryCommandConflictV1("registry_replay_stale")
                        connection.rollback()
                        return result
                    if status is None:
                        raise RegistryCommandConflictV1("registry_subject_not_found")
                    if (
                        status.account_record_version
                        != command.expected_account_version
                    ):
                        raise RegistryCommandConflictV1("registry_version_conflict")
                    if not status.can_add_connection:
                        raise RegistryCommandConflictV1(status.reason_code)
                    resource_id = _identifier()
                    revision = _next_revision(connection, instant)
                    connection.exec_driver_sql(
                        "INSERT INTO reg_account_resource "
                        "(resource_id, account_id, kind, safe_label_state, lifecycle, "
                        "record_version, created_at, updated_at) "
                        "VALUES (?, ?, 'api_organization', 'unknown', "
                        "'active', 1, ?, ?)",
                        (resource_id, command.account_id.value, instant, instant),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_billing_connection "
                        "(resource_id, account_id, scope_id, scope_evidence, "
                        "scope_generation, monitoring_preference, lifecycle, "
                        "record_version, registry_revision, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, 1, 'disabled', 'pending', 1, ?, ?, ?)",
                        (
                            resource_id,
                            command.account_id.value,
                            command.scope_id,
                            "unresolved"
                            if command.scope_id is None
                            else "owner_asserted",
                            revision,
                            instant,
                            instant,
                        ),
                    )
                    _append_change(
                        connection,
                        subject_type="resource",
                        subject_id=resource_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="billing_connection_created",
                        actor_id=command.principal_id.value,
                        correlation_id=command.command_id.value,
                        command_digest=command_digest,
                        instant=instant,
                        new_lifecycle="active",
                    )
                    _append_outbox(
                        connection,
                        subject_type="resource",
                        subject_id=resource_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="billing_connection_created",
                        correlation_id=command.command_id.value,
                        causation_id=command.command_id.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, "
                        "created_at, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, 'resource', ?, 1, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            _OPERATION,
                            command_digest,
                            fingerprint,
                            resource_id,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    persisted = _get(connection, command.account_id)
                    if persisted is None or not persisted.connections:
                        raise RegistryRepositoryErrorV1()
                    result = persisted.connections[0]
                    connection.commit()
                    return result
        except RegistryCommandConflictV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, ValueError):
            raise RegistryRepositoryErrorV1() from None


def resolve_billing_access_in_transaction(
    connection: Connection,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    purpose: BillingAccessPurposeV1,
) -> BillingAccessTargetV1 | None:
    """Resolve metadata and the current binding under one M02 transaction.

    Ollama keeps its existing cloud graph; this port resolves the independent
    Anthropic/OpenAI billing graph, with no CLI profile or identity prerequisite.
    """
    if not connection.in_transaction():
        raise ValueError("billing_transaction_required")
    if purpose not in {"verification", "monitoring"}:
        raise ValueError("billing_purpose_invalid")
    status = _get(connection, account_id)
    if (
        status is None
        or status.provider_key not in {"claude", "codex"}
        or status.account_lifecycle not in {"pending", "active"}
        or not status.connections
    ):
        return None
    selected = status.connections[0]
    if (
        selected.resource_id != resource_id
        or selected.lifecycle not in {"pending", "active"}
        or purpose == "monitoring"
        and (
            selected.lifecycle != "active"
            or selected.monitoring_preference != "enabled"
        )
    ):
        return None
    resource = connection.exec_driver_sql(
        "SELECT lifecycle FROM reg_account_resource "
        "WHERE resource_id=? AND account_id=?",
        (resource_id.value, account_id.value),
    ).one_or_none()
    if resource is None or resource[0] != "active":
        return None
    binding = resolve_active_credential_binding_in_transaction(connection, account_id)
    if binding is None:
        return None
    return billing_access_target(
        selected,
        binding,
        account_lifecycle=status.account_lifecycle,
        resource_lifecycle=resource[0],
        purpose=purpose,
    )


def ensure_billing_access_in_transaction(
    connection: Connection, expected: BillingAccessTargetV1
) -> None:
    """Composition calls this M02 adapter in the actual report-write transaction."""
    ensure_billing_access_current(
        resolve_billing_access_in_transaction(
            connection,
            expected.connection.account_id,
            expected.connection.resource_id,
            expected.purpose,
        ),
        expected,
    )


class SqliteBillingAccessRepositoryV1:
    """CTR-REG-014 1.3.0 current billing authority without credential access."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def resolve(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        purpose: BillingAccessPurposeV1,
    ) -> BillingAccessTargetV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    result = resolve_billing_access_in_transaction(
                        connection, account_id, resource_id, purpose
                    )
                    connection.rollback()
                    return result
        except (SQLAlchemyError, SqlitePolicyError, ValueError):
            raise RegistryRepositoryErrorV1() from None
