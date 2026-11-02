"""M02 credential-binding storage; stores non-secret owner-asserted references only."""

# ruff: noqa: E501 -- SQL predicates remain explicit.

import secrets
from typing import Literal

from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    CredentialBindingAggregateV1,
    CredentialBindingRecordV1,
)
from agentmonitor.modules.registry.domain.account import RegistryPolicyErrorV1
from agentmonitor.modules.registry.domain.credential_binding import (
    activate_prepared_credential_binding,
    complete_credential_binding_cleanup,
    disconnect_active_credential_binding,
    ensure_binding_visible_for_account,
    mark_pending_credential_binding_cleanup,
    new_credential_binding_aggregate,
    prepare_credential_binding,
)


class CredentialBindingRepositoryErrorV1(ValueError):
    """Sanitized repository failure, excluding SQL, paths and values."""


def _load(
    connection: Connection, account_id: OpaqueIdV1
) -> CredentialBindingAggregateV1:
    account = connection.exec_driver_sql(
        "SELECT provider_key,lifecycle FROM reg_account WHERE account_id=?",
        (account_id.value,),
    ).first()
    if account is None or account[0] != "ollama":
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_account_unavailable"
        )
    state = connection.exec_driver_sql(
        "SELECT record_version,binding_generation FROM reg_credential_binding_state WHERE account_id=?",
        (account_id.value,),
    ).first()
    if state is None:
        return new_credential_binding_aggregate(account_id)
    rows = connection.exec_driver_sql(
        "SELECT binding_id,lifecycle,generation,association_provenance,reason_code "
        "FROM reg_credential_binding WHERE account_id=? ORDER BY binding_id",
        (account_id.value,),
    ).all()
    bindings = tuple(
        CredentialBindingRecordV1(
            account_id, OpaqueIdV1(row[0]), row[1], row[2], row[3], row[4]
        )
        for row in rows
    )
    result = CredentialBindingAggregateV1(account_id, state[0], state[1], bindings)
    ensure_binding_visible_for_account(result, account_lifecycle=account[1])
    return result


def archive_bindings_in_transaction(
    connection: Connection, account_id: OpaqueIdV1
) -> None:
    """Fence and retire nonterminal bindings under the caller's account write lock."""
    old = _load(connection, account_id)
    new = disconnect_active_credential_binding(
        old, expected_record_version=old.record_version, reason_code="account_archived"
    )
    if new == old:
        return
    updated = connection.exec_driver_sql(
        "UPDATE reg_credential_binding_state SET record_version=?,binding_generation=? "
        "WHERE account_id=? AND record_version=? AND binding_generation=?",
        (
            new.record_version,
            new.binding_generation,
            account_id.value,
            old.record_version,
            old.binding_generation,
        ),
    )
    if updated.rowcount != 1:
        raise CredentialBindingRepositoryErrorV1("credential_binding_conflict")
    expected = sum(item.lifecycle in {"pending", "active"} for item in old.bindings)
    changed = connection.exec_driver_sql(
        "UPDATE reg_credential_binding SET lifecycle='cleanup_pending', "
        "reason_code='account_archived' WHERE account_id=? "
        "AND lifecycle IN ('pending','active')",
        (account_id.value,),
    )
    if changed.rowcount != expected:
        raise CredentialBindingRepositoryErrorV1("credential_binding_conflict")


class SqliteCredentialBindingsV1:
    """Serialize each complete aggregate update using BEGIN IMMEDIATE.

    Callers must separately serialize local Secret Service operations and commit
    provider observations against the generation within their own transaction.
    This repository does not access a keyring or claim that those fences exist.
    """

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    def read(self, account_id: OpaqueIdV1) -> CredentialBindingAggregateV1:
        try:
            with open_sqlite_database(self._reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    return _load(connection, account_id)
        except (SqlitePolicyError, SQLAlchemyError):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_unavailable"
            ) from None

    def transition(
        self,
        account_id: OpaqueIdV1,
        *,
        expected_record_version: int,
        action: Literal["prepare", "activate", "abandon", "disconnect", "cleanup"],
        binding_id: OpaqueIdV1 | None = None,
        reason: Literal[
            "owner_disconnected", "account_archived", "account_deleted"
        ] = "owner_disconnected",
    ) -> CredentialBindingAggregateV1:
        with account_credential_lock(self._reference, account_id):
            return self.transition_locked(
                account_id,
                expected_record_version=expected_record_version,
                action=action,
                binding_id=binding_id,
                reason=reason,
            )

    def transition_locked(
        self,
        account_id: OpaqueIdV1,
        *,
        expected_record_version: int,
        action: Literal["prepare", "activate", "abandon", "disconnect", "cleanup"],
        binding_id: OpaqueIdV1 | None = None,
        reason: Literal[
            "owner_disconnected", "account_archived", "account_deleted"
        ] = "owner_disconnected",
    ) -> CredentialBindingAggregateV1:
        """Caller must hold account_credential_lock until external work completes."""
        try:
            with open_sqlite_database(self._reference, "runtime_read_write") as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    old = _load(connection, account_id)
                    if action in {"prepare", "activate"}:
                        account_state = connection.exec_driver_sql(
                            "SELECT lifecycle FROM reg_account WHERE account_id=?",
                            (account_id.value,),
                        ).scalar_one()
                        if account_state == "archived":
                            raise CredentialBindingRepositoryErrorV1(
                                "credential_binding_account_unavailable"
                            )
                    if action == "prepare":
                        if binding_id is not None:
                            raise CredentialBindingRepositoryErrorV1(
                                "credential_binding_id_not_allowed"
                            )
                        new = prepare_credential_binding(
                            old,
                            binding_id=OpaqueIdV1("amcb_" + secrets.token_hex(16)),
                            expected_record_version=expected_record_version,
                        )
                    elif action == "disconnect":
                        new = disconnect_active_credential_binding(
                            old,
                            expected_record_version=expected_record_version,
                            reason_code=reason,
                        )
                    elif (
                        action in {"activate", "abandon", "cleanup"}
                        and binding_id is not None
                    ):
                        operation = {
                            "activate": activate_prepared_credential_binding,
                            "abandon": mark_pending_credential_binding_cleanup,
                            "cleanup": complete_credential_binding_cleanup,
                        }[action]
                        new = operation(
                            old,
                            binding_id=binding_id,
                            expected_record_version=expected_record_version,
                        )
                    else:
                        raise CredentialBindingRepositoryErrorV1(
                            "credential_binding_action_invalid"
                        )
                    if new == old:
                        connection.rollback()
                        return new
                    if old.record_version == 0:
                        connection.exec_driver_sql(
                            "INSERT INTO reg_credential_binding_state (account_id,record_version,binding_generation) VALUES (?,?,?)",
                            (
                                account_id.value,
                                new.record_version,
                                new.binding_generation,
                            ),
                        )
                    else:
                        updated = connection.exec_driver_sql(
                            "UPDATE reg_credential_binding_state SET record_version=?,binding_generation=? WHERE account_id=? AND record_version=? AND binding_generation=?",
                            (
                                new.record_version,
                                new.binding_generation,
                                account_id.value,
                                old.record_version,
                                old.binding_generation,
                            ),
                        )
                        if updated.rowcount != 1:
                            raise CredentialBindingRepositoryErrorV1(
                                "credential_binding_conflict"
                            )
                    old_ids = {item.binding_id for item in old.bindings}
                    # Retire old active rows before activating the replacement.
                    for item in sorted(
                        new.bindings, key=lambda value: value.lifecycle == "active"
                    ):
                        values = (
                            item.lifecycle,
                            item.generation,
                            item.association_provenance,
                            item.reason_code,
                        )
                        if item.binding_id in old_ids:
                            connection.exec_driver_sql(
                                "UPDATE reg_credential_binding SET lifecycle=?,generation=?,association_provenance=?,reason_code=? WHERE binding_id=? AND account_id=?",
                                (*values, item.binding_id.value, account_id.value),
                            )
                        else:
                            connection.exec_driver_sql(
                                "INSERT INTO reg_credential_binding (lifecycle,generation,association_provenance,reason_code,binding_id,account_id) VALUES (?,?,?,?,?,?)",
                                (*values, item.binding_id.value, account_id.value),
                            )
                    connection.commit()
                    return new
        except RegistryPolicyErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_unavailable"
            ) from None
