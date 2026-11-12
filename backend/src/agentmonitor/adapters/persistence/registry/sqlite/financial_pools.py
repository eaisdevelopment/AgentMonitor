"""M02 owner-only pool metadata over real billing and cloud resource graphs."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    resolve_active_credential_binding_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.registry_transaction import (
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
from agentmonitor.contracts.common_v1 import OpaqueIdV1, QueryAvailabilityV1
from agentmonitor.contracts.registry_billing_v1 import (
    AssignFinancialPoolCommandV1,
    EditFinancialPoolCommandV1,
    FinancialPoolConfigurationV1,
    FinancialPoolMembershipV1,
    FinancialPoolPageV1,
    FinancialPoolSnapshotV1,
    FinancialPoolViewV1,
    FinancialResourceScopeV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

type Selector = Literal["billing", "self", "team"]
type Provider = Literal["claude", "codex", "ollama"]
type PoolCommand = AssignFinancialPoolCommandV1 | EditFinancialPoolCommandV1


def _pool(row: RowMapping) -> FinancialPoolViewV1:
    return FinancialPoolViewV1(
        pool_id=OpaqueIdV1(row["pool_id"]),
        provider_key=row["provider_key"],
        primary_organization_id=(
            OpaqueIdV1(row["primary_organization_id"])
            if row["primary_organization_id"] is not None
            else None
        ),
        record_version=row["record_version"],
        registry_revision=row["registry_revision"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        display_name=row["display_name"],
        selector=row["selector"],
    )


def _membership(row: RowMapping) -> FinancialPoolMembershipV1:
    scope = FinancialResourceScopeV1(
        account_id=OpaqueIdV1(row["account_id"]),
        resource_id=OpaqueIdV1(row["resource_id"]),
        provider_key=row["provider_key"],
        selector=row["selector"],
        scope_generation=row["scope_generation"],
        provider_scope_id=row["provider_scope_id"],
        scope_evidence=row["scope_evidence"],
        binding_id=OpaqueIdV1(row["binding_id"]) if row["binding_id"] else None,
        binding_generation=row["binding_generation"],
    )
    return FinancialPoolMembershipV1(
        OpaqueIdV1(row["association_id"]),
        scope,
        OpaqueIdV1(row["pool_id"]),
        row["association_evidence"],
        datetime.fromisoformat(row["valid_from"]),
        datetime.fromisoformat(row["valid_until"]) if row["valid_until"] else None,
        row["record_version"],
        row["registry_revision"],
    )


def _read_pool(
    connection: Connection, pool_id: OpaqueIdV1
) -> FinancialPoolViewV1 | None:
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM reg_financial_pool WHERE pool_id=?", (pool_id.value,)
        )
        .mappings()
        .one_or_none()
    )
    return _pool(row) if row is not None else None


def _open_membership(
    connection: Connection, resource_id: OpaqueIdV1, selector: Selector
) -> FinancialPoolMembershipV1 | None:
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM reg_financial_pool_membership WHERE resource_id=? "
            "AND selector=? AND valid_until IS NULL",
            (resource_id.value, selector),
        )
        .mappings()
        .one_or_none()
    )
    return _membership(row) if row is not None else None


def _require_organization(
    connection: Connection, organization_id: OpaqueIdV1 | None
) -> None:
    if (
        organization_id is not None
        and connection.exec_driver_sql(
            "SELECT 1 FROM reg_organization WHERE organization_id=? AND "
            "lifecycle='active'",
            (organization_id.value,),
        ).scalar_one_or_none()
        is None
    ):
        raise RegistryCommandConflictV1("financial_pool_organization_unavailable")


def _not_after(row: RowMapping | None, as_of: datetime | None) -> None:
    if (
        row is not None
        and as_of is not None
        and datetime.fromisoformat(row["updated_at"]) > as_of
    ):
        raise RegistryCommandConflictV1("financial_pool_snapshot_changed")


def _configuration(
    connection: Connection,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    selector: Selector,
    *,
    as_of: datetime | None = None,
) -> FinancialPoolConfigurationV1 | None:
    account = (
        connection.exec_driver_sql(
            "SELECT a.*,p.lifecycle AS provider_lifecycle FROM reg_account a "
            "JOIN reg_provider_definition p ON p.provider_key=a.provider_key "
            "WHERE account_id=?",
            (account_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if account is None:
        return None
    _not_after(account, as_of)
    provider = account["provider_key"]
    if selector == "billing" and provider in {"claude", "codex"}:
        source = (
            connection.exec_driver_sql(
                "SELECT b.*,r.lifecycle AS resource_lifecycle FROM "
                "reg_billing_connection b "
                "JOIN reg_account_resource r ON r.resource_id=b.resource_id "
                "AND r.account_id=b.account_id "
                "WHERE b.account_id=? AND b.resource_id=?",
                (account_id.value, resource_id.value),
            )
            .mappings()
            .one_or_none()
        )
    elif selector in {"self", "team"} and provider == "ollama":
        source = (
            connection.exec_driver_sql(
                "SELECT g.*,t.lifecycle AS resource_lifecycle,t.updated_at "
                "AS target_updated_at "
                "FROM reg_cloud_monitoring_target g JOIN reg_provider_access_target t "
                "ON t.access_target_id=g.access_target_id AND t.provider_key='ollama' "
                "WHERE g.account_id=? AND g.resource_id=?",
                (account_id.value, resource_id.value),
            )
            .mappings()
            .one_or_none()
        )
    else:
        return None
    if source is None:
        return None
    _not_after(source, as_of)
    if (
        selector != "billing"
        and as_of is not None
        and datetime.fromisoformat(source["target_updated_at"]) > as_of
    ):
        raise RegistryCommandConflictV1("financial_pool_snapshot_changed")
    revision = _current_revision(connection)
    scope = None
    reason = "financial_pool_resource_unavailable"
    if (
        account["lifecycle"] in {"pending", "active"}
        and account["provider_lifecycle"] == "active"
        and source["lifecycle"] in {"pending", "active"}
        and source["resource_lifecycle"] == "active"
    ):
        scope_id = source["scope_id"] if selector == "billing" else None
        evidence: Literal["unresolved", "owner_asserted", "provider_verified"] = (
            source["scope_evidence"] if selector == "billing" else "unresolved"
        )
        generation = source["scope_generation"] if selector == "billing" else 1
        binding = None
        if evidence == "unresolved":
            binding = resolve_active_credential_binding_in_transaction(
                connection, account_id
            )
            if (
                selector != "billing"
                and binding is not None
                and (
                    binding.binding_id.value != source["binding_id"]
                    or binding.generation != source["binding_generation"]
                )
            ):
                binding = None
        if evidence != "unresolved" or binding is not None:
            scope = FinancialResourceScopeV1(
                account_id,
                resource_id,
                provider,
                selector,
                generation,
                scope_id,
                evidence,
                binding.binding_id if binding is not None else None,
                binding.generation if binding is not None else None,
            )
            reason = "financial_pool_unassociated"
        else:
            reason = "financial_pool_binding_unavailable"
    membership = _open_membership(connection, resource_id, selector)
    if membership is not None and membership.scope != scope:
        membership = None
    pool = (
        _read_pool(connection, membership.pool_id) if membership is not None else None
    )
    if membership is not None:
        if pool is None:
            raise RegistryRepositoryErrorV1()
        reason = "financial_pool_associated"
    return FinancialPoolConfigurationV1(
        account_id,
        resource_id,
        selector,
        scope,
        membership,
        pool,
        revision,
        reason,
    )


def _receipt(
    connection: Connection, command: PoolCommand, operation: str, fingerprint: str
) -> RowMapping | None:
    receipt = (
        connection.exec_driver_sql(
            "SELECT * FROM reg_command_receipt WHERE principal_id=? AND "
            "operation_key=? "
            "AND idempotency_key_digest=?",
            (command.principal_id.value, operation, _digest(command.command_id.value)),
        )
        .mappings()
        .one_or_none()
    )
    if receipt is not None and receipt["request_fingerprint"] != fingerprint:
        raise RegistryCommandConflictV1("registry_idempotency_conflict")
    return receipt


def _assignment_outcome(
    connection: Connection, scope: FinancialResourceScopeV1
) -> tuple[str, str, int]:
    """Name an actual association epoch, or the source for an empty unlink."""
    member = connection.exec_driver_sql(
        "SELECT association_id,record_version FROM reg_financial_pool_membership "
        "WHERE resource_id=? AND selector=? ORDER BY valid_from DESC,association_id "
        "DESC LIMIT 1",
        (scope.resource_id.value, scope.selector),
    ).one_or_none()
    if member is not None:
        return "financial_pool_membership", str(member[0]), int(member[1])
    query = (
        "SELECT record_version FROM reg_billing_connection WHERE resource_id=?"
        if scope.selector == "billing"
        else "SELECT record_version FROM reg_cloud_monitoring_target "
        "WHERE resource_id=?"
    )
    version = connection.exec_driver_sql(query, (scope.resource_id.value,)).scalar_one()
    return "resource", scope.resource_id.value, int(version)


def _save_receipt(
    connection: Connection,
    command: PoolCommand,
    operation: str,
    fingerprint: str,
    subject_type: str,
    subject_id: str,
    version: int,
    revision: int,
) -> None:
    connection.exec_driver_sql(
        "INSERT INTO reg_command_receipt "
        "(receipt_id,principal_id,operation_key,idempotency_key_digest,"
        "request_fingerprint,"
        "outcome_subject_type,outcome_subject_id,outcome_record_version,"
        "registry_revision,created_at,expires_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            _identifier(),
            command.principal_id.value,
            operation,
            _digest(command.command_id.value),
            fingerprint,
            subject_type,
            subject_id,
            version,
            revision,
            _utc_text(command.requested_at),
            _utc_text(command.requested_at + timedelta(days=365)),
        ),
    )


def _event(
    connection: Connection,
    command: PoolCommand,
    subject_type: str,
    subject_id: str,
    version: int,
    revision: int,
    kind: str,
) -> None:
    _append_change(
        connection,
        subject_type=subject_type,
        subject_id=subject_id,
        aggregate_version=version,
        revision=revision,
        change_kind=kind,
        actor_id=command.principal_id.value,
        correlation_id=command.command_id.value,
        command_digest=_digest(command.command_id.value),
        instant=_utc_text(command.requested_at),
    )
    _append_outbox(
        connection,
        subject_type=subject_type,
        subject_id=subject_id,
        aggregate_version=version,
        revision=revision,
        change_kind=kind,
        correlation_id=command.command_id.value,
        causation_id=command.command_id.value,
        instant=_utc_text(command.requested_at),
    )


def _guard_revision(
    connection: Connection, expected: int, instant: datetime | None = None
) -> int:
    row = (
        connection.exec_driver_sql(
            "SELECT registry_revision,updated_at FROM reg_registry_state "
            "WHERE singleton_key=1"
        )
        .mappings()
        .one_or_none()
    )
    revision = int(row["registry_revision"]) if row is not None else 0
    if revision != expected:
        raise RegistryCommandConflictV1("registry_revision_conflict")
    if (
        instant is not None
        and row is not None
        and datetime.fromisoformat(row["updated_at"]) > instant
    ):
        raise RegistryCommandConflictV1("financial_pool_time_conflict")
    return revision


class SqliteFinancialPoolRepositoryV1:
    """CTR-REG-014 1.5.0; association proves neither access nor wider coverage."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[Connection]:
        try:
            mode: Literal["runtime_read_write", "runtime_read_only"] = (
                "runtime_read_write" if write else "runtime_read_only"
            )
            with open_sqlite_database(self._database_ref, mode) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE" if write else "BEGIN")
                    yield connection
                    connection.rollback()
        except RegistryCommandConflictV1:
            raise
        except (SQLAlchemyError, SqlitePolicyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1(
                "financial_pool_repository_unavailable"
            ) from None

    def get_configuration(
        self, account_id: OpaqueIdV1, resource_id: OpaqueIdV1, selector: Selector
    ) -> FinancialPoolConfigurationV1 | None:
        with self._connection() as connection:
            return _configuration(connection, account_id, resource_id, selector)

    def list_pools(
        self,
        provider_key: Provider,
        *,
        limit: int = 50,
        after: OpaqueIdV1 | None = None,
        expected_registry_revision: int | None = None,
    ) -> FinancialPoolPageV1:
        if (
            provider_key not in {"claude", "codex", "ollama"}
            or type(limit) is not int
            or not 1 <= limit <= 200
            or after is not None
            and (
                not isinstance(after, OpaqueIdV1) or expected_registry_revision is None
            )
        ):
            raise RegistryCommandConflictV1("financial_pool_query_invalid")
        with self._connection() as connection:
            revision = _current_revision(connection)
            if expected_registry_revision is not None:
                _guard_revision(connection, expected_registry_revision)
            rows = (
                connection.exec_driver_sql(
                    "SELECT * FROM reg_financial_pool WHERE provider_key=? "
                    "AND pool_id>? ORDER BY pool_id LIMIT ?",
                    (provider_key, after.value if after is not None else "", limit + 1),
                )
                .mappings()
                .all()
            )
            pools = tuple(_pool(row) for row in rows[:limit])
            return FinancialPoolPageV1(
                pools, pools[-1].pool_id if len(rows) > limit else None, revision
            )

    def assign(
        self, command: AssignFinancialPoolCommandV1
    ) -> FinancialPoolConfigurationV1:
        operation = "assign_financial_pool"
        fingerprint = _fingerprint(
            {
                "operation": operation,
                "scope": asdict(command.scope),
                "expected_registry_revision": command.expected_registry_revision,
                "action": command.action,
                "pool_id": command.pool_id.value if command.pool_id else None,
                "primary_organization_id": command.primary_organization_id.value
                if command.primary_organization_id
                else None,
            }
        )
        with self._connection(write=True) as connection:
            receipt = _receipt(connection, command, operation, fingerprint)
            config = _configuration(
                connection,
                command.scope.account_id,
                command.scope.resource_id,
                command.scope.selector,
            )
            if receipt is not None:
                if config is None or config.scope != command.scope:
                    raise RegistryCommandConflictV1("registry_replay_stale")
                if command.action == "unlink":
                    newer = connection.exec_driver_sql(
                        "SELECT 1 FROM reg_financial_pool_membership WHERE "
                        "resource_id=? AND selector=? AND "
                        "registry_revision>? LIMIT 1",
                        (
                            command.scope.resource_id.value,
                            command.scope.selector,
                            receipt["registry_revision"],
                        ),
                    ).scalar_one_or_none()
                    if config.membership is not None or newer is not None:
                        raise RegistryCommandConflictV1("registry_replay_stale")
                elif (
                    config.membership is None
                    or config.pool is None
                    or config.membership.association_id.value
                    != receipt["outcome_subject_id"]
                    or config.membership.record_version
                    != receipt["outcome_record_version"]
                    or config.pool.registry_revision > receipt["registry_revision"]
                ):
                    raise RegistryCommandConflictV1("registry_replay_stale")
                return config
            _guard_revision(
                connection, command.expected_registry_revision, command.requested_at
            )
            if config is None:
                raise RegistryCommandConflictV1("registry_subject_not_found")
            if config.scope != command.scope:
                raise RegistryCommandConflictV1("financial_pool_scope_changed")
            if command.action not in {"create", "join", "unlink"}:
                raise RegistryCommandConflictV1("financial_pool_query_invalid")
            _require_organization(connection, command.primary_organization_id)
            pool = None
            if command.action == "join":
                assert command.pool_id is not None
                pool = _read_pool(connection, command.pool_id)
                if pool is None:
                    raise RegistryCommandConflictV1("financial_pool_unavailable")
                if (
                    pool.provider_key != command.scope.provider_key
                    or pool.selector != command.scope.selector
                ):
                    raise RegistryCommandConflictV1("financial_pool_incompatible")
                _require_organization(connection, pool.primary_organization_id)
                if (
                    command.scope.provider_scope_id is not None
                    and connection.exec_driver_sql(
                        "SELECT 1 FROM reg_financial_pool_membership WHERE pool_id=? "
                        "AND provider_scope_id IS NOT NULL AND "
                        "provider_scope_id<>? LIMIT 1",
                        (pool.pool_id.value, command.scope.provider_scope_id),
                    ).scalar_one_or_none()
                    is not None
                ):
                    raise RegistryCommandConflictV1("financial_pool_incompatible")
            previous = _open_membership(
                connection, command.scope.resource_id, command.scope.selector
            )
            unchanged = (command.action == "unlink" and previous is None) or (
                command.action == "join"
                and config.membership is not None
                and pool is not None
                and config.membership.pool_id == pool.pool_id
            )
            if unchanged:
                result = config
            else:
                instant = _utc_text(command.requested_at)
                if previous is not None and command.requested_at <= previous.valid_from:
                    raise RegistryCommandConflictV1("financial_pool_time_conflict")
                revision = _next_revision(connection, instant)
                if previous is not None:
                    connection.exec_driver_sql(
                        "UPDATE reg_financial_pool_membership SET "
                        "valid_until=?,record_version=record_version+1,"
                        "registry_revision=? WHERE association_id=? AND "
                        "valid_until IS NULL",
                        (instant, revision, previous.association_id.value),
                    )
                if command.action == "create":
                    account_name = connection.exec_driver_sql(
                        "SELECT friendly_name FROM reg_account WHERE account_id=?",
                        (command.scope.account_id.value,),
                    ).scalar_one()
                    pool_id = _identifier()
                    suffix = " · " + command.scope.selector
                    display_name = account_name[: 256 - len(suffix)] + suffix
                    connection.exec_driver_sql(
                        "INSERT INTO reg_financial_pool (pool_id,"
                        "provider_key,selector,primary_organization_id,"
                        "display_name,record_version,registry_revision,"
                        "created_at,updated_at) VALUES (?,?,?,?,?,1,?,?,?)",
                        (
                            pool_id,
                            command.scope.provider_key,
                            command.scope.selector,
                            command.primary_organization_id.value
                            if command.primary_organization_id
                            else None,
                            display_name,
                            revision,
                            instant,
                            instant,
                        ),
                    )
                    pool = _read_pool(connection, OpaqueIdV1(pool_id))
                if command.action != "unlink":
                    assert pool is not None
                    scope = command.scope
                    connection.exec_driver_sql(
                        "INSERT INTO reg_financial_pool_membership "
                        "(association_id,account_id,resource_id,"
                        "billing_resource_id,cloud_resource_id,provider_key,"
                        "selector,scope_generation,provider_scope_id,"
                        "scope_evidence,binding_id,binding_generation,"
                        "pool_id,association_evidence,valid_from,valid_until,"
                        "record_version,registry_revision) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'owner_asserted',"
                        "?,NULL,1,?)",
                        (
                            _identifier(),
                            scope.account_id.value,
                            scope.resource_id.value,
                            scope.resource_id.value
                            if scope.selector == "billing"
                            else None,
                            scope.resource_id.value
                            if scope.selector != "billing"
                            else None,
                            scope.provider_key,
                            scope.selector,
                            scope.scope_generation,
                            scope.provider_scope_id,
                            scope.scope_evidence,
                            scope.binding_id.value if scope.binding_id else None,
                            scope.binding_generation,
                            pool.pool_id.value,
                            instant,
                            revision,
                        ),
                    )
                persisted = _configuration(
                    connection,
                    command.scope.account_id,
                    command.scope.resource_id,
                    command.scope.selector,
                )
                assert persisted is not None
                result = persisted
                subject_type, subject_id, version = _assignment_outcome(
                    connection, command.scope
                )
                _event(
                    connection,
                    command,
                    subject_type,
                    subject_id,
                    version,
                    revision,
                    "financial_pool_association_changed",
                )
            subject_type, subject_id, version = _assignment_outcome(
                connection, command.scope
            )
            _save_receipt(
                connection,
                command,
                operation,
                fingerprint,
                subject_type,
                subject_id,
                version,
                result.registry_revision,
            )
            connection.commit()
            return result

    def edit(self, command: EditFinancialPoolCommandV1) -> FinancialPoolViewV1:
        operation = "edit_financial_pool"
        fingerprint = _fingerprint(
            {
                "operation": operation,
                "pool_id": command.pool_id.value,
                "expected_record_version": command.expected_record_version,
                "expected_registry_revision": command.expected_registry_revision,
                "primary_organization_id": command.primary_organization_id.value
                if command.primary_organization_id
                else None,
            }
        )
        with self._connection(write=True) as connection:
            receipt = _receipt(connection, command, operation, fingerprint)
            current = _read_pool(connection, command.pool_id)
            if receipt is not None:
                if (
                    current is None
                    or current.record_version != receipt["outcome_record_version"]
                ):
                    raise RegistryCommandConflictV1("registry_replay_stale")
                _require_organization(connection, current.primary_organization_id)
                return current
            _guard_revision(
                connection, command.expected_registry_revision, command.requested_at
            )
            if current is None:
                raise RegistryCommandConflictV1("financial_pool_unavailable")
            if current.record_version != command.expected_record_version:
                raise RegistryCommandConflictV1("registry_version_conflict")
            _require_organization(connection, command.primary_organization_id)
            if current.primary_organization_id != command.primary_organization_id:
                revision = _next_revision(connection, _utc_text(command.requested_at))
                connection.exec_driver_sql(
                    "UPDATE reg_financial_pool SET primary_organization_id=?,"
                    "record_version=record_version+1,registry_revision=?,"
                    "updated_at=? WHERE pool_id=?",
                    (
                        command.primary_organization_id.value
                        if command.primary_organization_id
                        else None,
                        revision,
                        _utc_text(command.requested_at),
                        command.pool_id.value,
                    ),
                )
                current = _read_pool(connection, command.pool_id)
                assert current is not None
                _event(
                    connection,
                    command,
                    "financial_pool",
                    command.pool_id.value,
                    current.record_version,
                    revision,
                    "financial_pool_attribution_changed",
                )
            _save_receipt(
                connection,
                command,
                operation,
                fingerprint,
                "financial_pool",
                command.pool_id.value,
                current.record_version,
                _current_revision(connection),
            )
            connection.commit()
            return current

    def __call__(
        self,
        resource_ids: tuple[OpaqueIdV1, ...],
        *,
        expected_registry_revision: int,
        as_of: datetime,
    ) -> FinancialPoolSnapshotV1:
        if (
            len(resource_ids) > 2000
            or len(set(resource_ids)) != len(resource_ids)
            or any(not isinstance(value, OpaqueIdV1) for value in resource_ids)
        ):
            raise RegistryCommandConflictV1("financial_pool_query_invalid")
        revision = expected_registry_revision
        try:
            with self._connection() as connection:
                revision = _guard_revision(
                    connection, expected_registry_revision, as_of
                )
                memberships = []
                pools = {}
                for resource_id in resource_ids:
                    rows = connection.exec_driver_sql(
                        "SELECT account_id,'billing' AS selector FROM "
                        "reg_billing_connection WHERE resource_id=? "
                        "UNION ALL SELECT account_id,'self' FROM "
                        "reg_cloud_monitoring_target WHERE resource_id=?",
                        (resource_id.value, resource_id.value),
                    ).all()
                    if len(rows) != 1:
                        raise RegistryCommandConflictV1(
                            "financial_pool_resource_unavailable"
                        )
                    account_id, selector = rows[0]
                    for selected in (
                        ("self", "team") if selector == "self" else ("billing",)
                    ):
                        config = _configuration(
                            connection,
                            OpaqueIdV1(account_id),
                            resource_id,
                            selected,
                            as_of=as_of,
                        )
                        if (
                            config is not None
                            and config.membership is not None
                            and config.pool is not None
                        ):
                            _require_organization(
                                connection, config.pool.primary_organization_id
                            )
                            memberships.append(config.membership)
                            pools[config.pool.pool_id] = config.pool
                return FinancialPoolSnapshotV1(
                    resource_ids,
                    tuple(sorted(pools.values(), key=lambda p: p.pool_id.value)),
                    tuple(
                        sorted(
                            memberships,
                            key=lambda m: (m.scope.resource_id.value, m.scope.selector),
                        )
                    ),
                    revision,
                    as_of,
                    QueryAvailabilityV1(
                        "available", "financial_pool_snapshot_available", as_of
                    ),
                )
        except (RegistryCommandConflictV1, RegistryRepositoryErrorV1, ValueError):
            return FinancialPoolSnapshotV1(
                resource_ids,
                (),
                (),
                revision,
                as_of,
                QueryAvailabilityV1(
                    "unavailable", "financial_pool_snapshot_unavailable", as_of
                ),
            )
