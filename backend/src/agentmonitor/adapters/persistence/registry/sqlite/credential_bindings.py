"""M02 credential-binding storage; stores non-secret owner-asserted references only."""

# ruff: noqa: E501 -- SQL predicates remain explicit.

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

from agentmonitor.adapters.persistence._shared.sqlite.core.credential_guard import (
    acquire_credential_staging_guard,
)
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
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
    CredentialBindingAggregateV1,
    CredentialBindingRecordV1,
    CredentialBindingVerificationReceiptV1,
    ProviderAccessTargetV1,
    ProviderTargetRefV1,
)
from agentmonitor.modules.registry.domain.account import (
    RegistryPolicyErrorV1,
    decide_account_monitoring,
)
from agentmonitor.modules.registry.domain.cloud_verification import (
    require_cloud_verification_enqueue_authority,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    activate_prepared_credential_binding,
    complete_credential_binding_cleanup,
    disconnect_active_credential_binding,
    ensure_binding_visible_for_account,
    ensure_credential_binding_commit_current,
    mark_pending_credential_binding_cleanup,
    new_credential_binding_aggregate,
    prepare_credential_binding,
    resolve_active_credential_binding,
)


class CredentialBindingRepositoryErrorV1(ValueError):
    """Sanitized repository failure, excluding SQL, paths and values."""


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise CredentialBindingRepositoryErrorV1("credential_binding_time_invalid")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _utc_value(value: object) -> datetime:
    if not isinstance(value, str):
        raise CredentialBindingRepositoryErrorV1("credential_binding_unavailable")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_unavailable"
        ) from None
    if result.utcoffset() != timedelta(0):
        raise CredentialBindingRepositoryErrorV1("credential_binding_unavailable")
    return result.astimezone(UTC)


def _access_target_id(provider_key: str, authority_id: str) -> OpaqueIdV1:
    digest = hashlib.sha256(
        (provider_key + "\x00" + authority_id).encode("utf-8")
    ).hexdigest()
    return OpaqueIdV1("amat_" + digest[:32])


def _access_target(mapping: RowMapping) -> ProviderAccessTargetV1:
    return ProviderAccessTargetV1(
        access_target_id=OpaqueIdV1(mapping["access_target_id"]),
        provider_key=mapping["provider_key"],
        target_kind=mapping["target_kind"],
        authority_id=mapping["authority_id"],
        manifest_fingerprint=mapping["manifest_fingerprint"],
        lifecycle=mapping["lifecycle"],
        record_version=int(mapping["record_version"]),
    )


def _cloud_monitoring_target(mapping: RowMapping) -> CloudMonitoringTargetV1:
    account_id = OpaqueIdV1(mapping["account_id"])
    return CloudMonitoringTargetV1(
        profile_id=OpaqueIdV1(mapping["profile_id"]),
        resource_id=OpaqueIdV1(mapping["resource_id"]),
        account_id=account_id,
        access_target_id=OpaqueIdV1(mapping["access_target_id"]),
        binding=ActiveCredentialBindingRefV1(
            account_id=account_id,
            binding_id=OpaqueIdV1(mapping["binding_id"]),
            generation=int(mapping["binding_generation"]),
        ),
        lifecycle=mapping["lifecycle"],
        identity_state=mapping["identity_state"],
        owner_principal_id=OpaqueIdV1(mapping["owner_principal_id"]),
        owner_asserted_at=_utc_value(mapping["owner_asserted_at"]),
        record_version=int(mapping["record_version"]),
    )


def _verification_receipt(
    mapping: RowMapping,
) -> CredentialBindingVerificationReceiptV1:
    account_id = OpaqueIdV1(mapping["account_id"])
    return CredentialBindingVerificationReceiptV1(
        verification_id=OpaqueIdV1(mapping["verification_id"]),
        binding=ActiveCredentialBindingRefV1(
            account_id=account_id,
            binding_id=OpaqueIdV1(mapping["binding_id"]),
            generation=int(mapping["binding_generation"]),
        ),
        access_target_id=OpaqueIdV1(mapping["access_target_id"]),
        run_id=OpaqueIdV1(mapping["run_id"]),
        admission_id=OpaqueIdV1(mapping["admission_id"]),
        source_id=mapping["source_id"],
        adapter_version=mapping["adapter_version"],
        manifest_fingerprint=mapping["manifest_fingerprint"],
        payload_digest=mapping["payload_digest"],
        verified_at=_utc_value(mapping["verified_at"]),
        record_version=int(mapping["record_version"]),
    )


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


def ensure_active_binding_in_transaction(
    connection: Connection, reference: ActiveCredentialBindingRefV1
) -> None:
    """M02-owned adapter port: verify authority using the caller's write transaction."""
    if not connection.in_transaction():
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    aggregate = _load(connection, reference.account_id)
    account = connection.exec_driver_sql(
        "SELECT lifecycle,monitoring_preference,identity_state FROM reg_account WHERE account_id=?",
        (reference.account_id.value,),
    ).first()
    if (
        account is None
        or not decide_account_monitoring(
            lifecycle=account[0],
            monitoring_preference=account[1],
            identity_state=account[2],
        ).is_enabled
    ):
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_monitoring_disabled"
        )
    ensure_credential_binding_commit_current(aggregate, reference)


def ensure_current_binding_in_transaction(
    connection: Connection, reference: ActiveCredentialBindingRefV1
) -> None:
    """Fence first verification before monitoring eligibility is established."""
    if not connection.in_transaction():
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    ensure_credential_binding_commit_current(
        _load(connection, reference.account_id), reference
    )


def resolve_active_credential_binding_in_transaction(
    connection: Connection, account_id: OpaqueIdV1
) -> ActiveCredentialBindingRefV1 | None:
    """Resolve the current non-secret generation under a caller transaction."""
    if not connection.in_transaction():
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    return resolve_active_credential_binding(_load(connection, account_id))


def ensure_access_target_in_transaction(
    connection: Connection, access_target_id: OpaqueIdV1
) -> ProviderAccessTargetV1:
    """Return one exact active Ollama cloud target under the caller's transaction."""
    if not connection.in_transaction():
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM reg_provider_access_target WHERE access_target_id=?",
            (access_target_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if (
        row is None
        or row["provider_key"] != "ollama"
        or row["target_kind"] != "cloud_service"
        or row["lifecycle"] != "active"
    ):
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_target_unavailable"
        )
    return _access_target(row)


def reconcile_access_target_in_transaction(
    connection: Connection,
    *,
    provider_key: str,
    authority_id: str,
    manifest_fingerprint: str,
    as_of: datetime,
) -> ProviderAccessTargetV1:
    """Create/replay one code-owned access target in the caller transaction."""
    if not connection.in_transaction():
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    target_id = _access_target_id(provider_key, authority_id)
    candidate = ProviderAccessTargetV1(
        access_target_id=target_id,
        provider_key=provider_key,
        target_kind="cloud_service",
        authority_id=authority_id,
        manifest_fingerprint=manifest_fingerprint,
        lifecycle="active",
        record_version=1,
    )
    instant = _utc_text(as_of)
    provider = connection.exec_driver_sql(
        "SELECT lifecycle FROM reg_provider_definition WHERE provider_key=?",
        (provider_key,),
    ).scalar_one_or_none()
    if provider != "active":
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_target_unavailable"
        )
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM reg_provider_access_target "
            "WHERE provider_key=? AND authority_id=?",
            (provider_key, authority_id),
        )
        .mappings()
        .one_or_none()
    )
    if row is not None:
        existing = _access_target(row)
        if existing != candidate:
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_target_conflict"
            )
        return existing
    connection.exec_driver_sql(
        "INSERT INTO reg_provider_access_target "
        "(access_target_id,provider_key,target_kind,authority_id,"
        "manifest_fingerprint,lifecycle,record_version,created_at,updated_at) "
        "VALUES (?,?,?,?,?,'active',1,?,?)",
        (
            target_id.value,
            provider_key,
            "cloud_service",
            authority_id,
            manifest_fingerprint,
            instant,
            instant,
        ),
    )
    return candidate


def ensure_cloud_verification_enqueue_authority_in_transaction(
    connection: Connection,
    *,
    account_id: OpaqueIdV1,
    expected_account_record_version: int,
    profile_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    access_target_id: OpaqueIdV1,
    binding: ActiveCredentialBindingRefV1,
    expected_manifest_fingerprint: str,
) -> None:
    """Fence a new M04 verification job by current M02 authority atomically."""
    if not connection.in_transaction() or binding.account_id != account_id:
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    account = (
        connection.exec_driver_sql(
            "SELECT provider_key,lifecycle,identity_state,monitoring_preference,"
            "record_version FROM reg_account WHERE account_id=?",
            (account_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    if account is None:
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_enqueue_authority_unavailable"
        )
    target = (
        connection.exec_driver_sql(
            "SELECT t.provider_key,t.target_kind,t.authority_id,"
            "t.manifest_fingerprint,t.lifecycle "
            "FROM reg_provider_access_target t JOIN reg_provider_definition p "
            "ON p.provider_key=t.provider_key AND p.lifecycle='active' "
            "WHERE t.access_target_id=?",
            (access_target_id.value,),
        )
        .mappings()
        .one_or_none()
    )
    graph_is_exact = (
        connection.exec_driver_sql(
            "SELECT 1 FROM reg_cloud_monitoring_target WHERE account_id=? "
            "AND profile_id=? AND resource_id=? AND access_target_id=? "
            "AND binding_id=? AND binding_generation=? AND lifecycle='active' "
            "AND identity_state='owner_confirmed'",
            (
                account_id.value,
                profile_id.value,
                resource_id.value,
                access_target_id.value,
                binding.binding_id.value,
                binding.generation,
            ),
        ).first()
        is not None
    )
    binding_is_current = (
        resolve_active_credential_binding(_load(connection, account_id)) == binding
    )
    try:
        require_cloud_verification_enqueue_authority(
            account_provider=str(account["provider_key"]),
            account_lifecycle=str(account["lifecycle"]),
            account_identity_state=str(account["identity_state"]),
            account_monitoring_preference=str(account["monitoring_preference"]),
            account_record_version=int(account["record_version"]),
            expected_account_record_version=expected_account_record_version,
            target_provider=str(target["provider_key"]) if target is not None else "",
            target_kind=str(target["target_kind"]) if target is not None else "",
            target_authority=(
                str(target["authority_id"]) if target is not None else ""
            ),
            target_lifecycle=str(target["lifecycle"]) if target is not None else "",
            target_manifest_is_exact=(
                target is not None
                and target["manifest_fingerprint"] == expected_manifest_fingerprint
            ),
            graph_is_exact=graph_is_exact,
            binding_is_current=binding_is_current,
        )
    except ValueError as error:
        if str(error) == "registry_account_version_conflict":
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_account_version_conflict"
            ) from None
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_enqueue_authority_unavailable"
        ) from None


def ensure_cloud_target_graph_in_transaction(
    connection: Connection,
    *,
    account_id: OpaqueIdV1,
    profile_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    access_target_id: OpaqueIdV1,
    binding: ActiveCredentialBindingRefV1,
) -> None:
    """M02 port for one owner-confirmed cloud account/profile/resource graph."""
    if not connection.in_transaction() or binding.account_id != account_id:
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    found = connection.exec_driver_sql(
        "SELECT 1 FROM reg_cloud_monitoring_target WHERE account_id=? AND profile_id=? "
        "AND resource_id=? AND access_target_id=? AND binding_id=? "
        "AND binding_generation=? AND lifecycle='active' "
        "AND identity_state='owner_confirmed'",
        (
            account_id.value,
            profile_id.value,
            resource_id.value,
            access_target_id.value,
            binding.binding_id.value,
            binding.generation,
        ),
    ).first()
    if found is None:
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_target_unavailable"
        )
    ensure_current_binding_in_transaction(connection, binding)


def record_credential_binding_verification_in_transaction(
    connection: Connection,
    *,
    binding: ActiveCredentialBindingRefV1,
    access_target_id: OpaqueIdV1,
    run_id: OpaqueIdV1,
    admission_id: OpaqueIdV1,
    source_id: Literal["ollama.cloud.balance.v1"],
    adapter_version: str,
    manifest_fingerprint: str,
    payload_digest: str,
    verified_at: datetime,
) -> CredentialBindingVerificationReceiptV1:
    """Create/replay a receipt inside the surrounding M05 commit transaction."""
    if not connection.in_transaction():
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    ensure_current_binding_in_transaction(connection, binding)
    ensure_access_target_in_transaction(connection, access_target_id)
    graph = connection.exec_driver_sql(
        "SELECT 1 FROM reg_cloud_monitoring_target WHERE account_id=? "
        "AND access_target_id=? AND binding_id=? AND binding_generation=? "
        "AND lifecycle='active' AND identity_state='owner_confirmed'",
        (
            binding.account_id.value,
            access_target_id.value,
            binding.binding_id.value,
            binding.generation,
        ),
    ).first()
    if graph is None:
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_target_unavailable"
        )
    existing = (
        connection.exec_driver_sql(
            "SELECT * FROM reg_credential_binding_verification "
            "WHERE run_id=? OR admission_id=?",
            (run_id.value, admission_id.value),
        )
        .mappings()
        .all()
    )
    if existing:
        if len(existing) != 1:
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_verification_conflict"
            )
        receipt = _verification_receipt(existing[0])
        if (
            receipt.binding != binding
            or receipt.access_target_id != access_target_id
            or receipt.run_id != run_id
            or receipt.admission_id != admission_id
            or receipt.source_id != source_id
            or receipt.adapter_version != adapter_version
            or receipt.manifest_fingerprint != manifest_fingerprint
            or receipt.payload_digest != payload_digest
            or receipt.verified_at != verified_at
        ):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_verification_conflict"
            )
        return receipt
    receipt = CredentialBindingVerificationReceiptV1(
        verification_id=OpaqueIdV1("amvr_" + secrets.token_hex(16)),
        binding=binding,
        access_target_id=access_target_id,
        run_id=run_id,
        admission_id=admission_id,
        source_id=source_id,
        adapter_version=adapter_version,
        manifest_fingerprint=manifest_fingerprint,
        payload_digest=payload_digest,
        verified_at=verified_at,
        record_version=1,
    )
    connection.exec_driver_sql(
        "INSERT INTO reg_credential_binding_verification "
        "(verification_id,account_id,binding_id,binding_generation,access_target_id,"
        "run_id,admission_id,source_id,adapter_version,manifest_fingerprint,"
        "payload_digest,verified_at,record_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (
            receipt.verification_id.value,
            binding.account_id.value,
            binding.binding_id.value,
            binding.generation,
            access_target_id.value,
            run_id.value,
            admission_id.value,
            source_id,
            adapter_version,
            manifest_fingerprint,
            payload_digest,
            _utc_text(verified_at),
        ),
    )
    return receipt


def ensure_monitored_graph_in_transaction(
    connection: Connection,
    account_id: OpaqueIdV1,
    profile_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    installation_id: OpaqueIdV1,
) -> None:
    """M02 port for the live account/profile/resource monitoring graph."""
    if not connection.in_transaction():
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_transaction_required"
        )
    found = connection.exec_driver_sql(
        "SELECT 1 FROM reg_monitoring_profile p "
        "JOIN reg_profile_resource_link l ON l.account_id=p.account_id AND l.profile_id=p.profile_id "
        "JOIN reg_account_resource r ON r.account_id=l.account_id AND r.resource_id=l.resource_id "
        "WHERE p.account_id=? AND p.profile_id=? AND r.resource_id=? AND p.provider_installation_id=? "
        "AND p.lifecycle='active' AND p.management_state='managed' AND p.protected_default_profile=0 "
        "AND p.compatibility_state='compatible' AND p.identity_verification_state IN ('owner_confirmed','provider_verified') "
        "AND p.purpose IN ('subscription','combined') AND r.lifecycle='active' AND r.kind='subscription_pool'",
        (account_id.value, profile_id.value, resource_id.value, installation_id.value),
    ).first()
    if found is None:
        raise CredentialBindingRepositoryErrorV1(
            "credential_binding_target_unavailable"
        )


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


class SqliteCloudCredentialRegistryV1:
    """Non-secret M02 access-target and verification receipt repository."""

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    def read_active_access_target(
        self, access_target_id: OpaqueIdV1
    ) -> ProviderAccessTargetV1 | None:
        """Return one exact active target without creating or updating it."""
        try:
            ProviderTargetRefV1("cloud_service", access_target_id)
        except (TypeError, ValueError):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_target_query_invalid"
            ) from None
        try:
            with open_sqlite_database(self._reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT t.* FROM reg_provider_access_target t "
                            "JOIN reg_provider_definition p "
                            "ON p.provider_key=t.provider_key "
                            "WHERE t.access_target_id=? AND t.lifecycle='active' "
                            "AND p.lifecycle='active'",
                            (access_target_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return _access_target(row) if row is not None else None
        except CredentialBindingRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_unavailable"
            ) from None

    def reconcile_access_target(
        self,
        *,
        provider_key: str,
        authority_id: str,
        manifest_fingerprint: str,
        as_of: datetime,
    ) -> ProviderAccessTargetV1:
        try:
            with open_sqlite_database(self._reference, "runtime_read_write") as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    result = reconcile_access_target_in_transaction(
                        connection,
                        provider_key=provider_key,
                        authority_id=authority_id,
                        manifest_fingerprint=manifest_fingerprint,
                        as_of=as_of,
                    )
                    connection.commit()
                    return result
        except CredentialBindingRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_unavailable"
            ) from None

    def read_monitoring_target(
        self, account_id: OpaqueIdV1
    ) -> CloudMonitoringTargetV1 | None:
        try:
            with open_sqlite_database(self._reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM reg_cloud_monitoring_target WHERE account_id=?",
                            (account_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return _cloud_monitoring_target(row) if row is not None else None
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_unavailable"
            ) from None

    def read_current_verification(
        self, binding: ActiveCredentialBindingRefV1
    ) -> CredentialBindingVerificationReceiptV1 | None:
        try:
            with open_sqlite_database(self._reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM reg_credential_binding_verification "
                            "WHERE account_id=? AND binding_id=? AND binding_generation=?",
                            (
                                binding.account_id.value,
                                binding.binding_id.value,
                                binding.generation,
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return _verification_receipt(row) if row is not None else None
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_unavailable"
            ) from None

    def read_verification_by_run(
        self, run_id: OpaqueIdV1, admission_id: OpaqueIdV1
    ) -> CredentialBindingVerificationReceiptV1 | None:
        """Read one immutable non-secret receipt by its exact M04 lineage."""
        if not isinstance(run_id, OpaqueIdV1) or not isinstance(
            admission_id, OpaqueIdV1
        ):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_verification_query_invalid"
            )
        try:
            with open_sqlite_database(self._reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM reg_credential_binding_verification "
                            "WHERE run_id=? AND admission_id=?",
                            (run_id.value, admission_id.value),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return _verification_receipt(row) if row is not None else None
        except CredentialBindingRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CredentialBindingRepositoryErrorV1(
                "credential_binding_unavailable"
            ) from None


class SqliteCredentialBindingsV1:
    """Serialize each complete aggregate update using BEGIN IMMEDIATE.

    Callers must separately serialize local managed credential operations and commit
    provider observations against the generation within their own transaction.
    This repository does not access credentials or claim that those fences exist.
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

    def has_unfinished_bindings(self) -> bool:
        """Return whether any local credential still needs authority or cleanup."""
        try:
            with open_sqlite_database(self._reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    return bool(
                        connection.exec_driver_sql(
                            "SELECT EXISTS(SELECT 1 FROM reg_credential_binding "
                            "WHERE lifecycle IN ('pending','active','cleanup_pending'))"
                        ).scalar_one()
                    )
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
        """Fence binding creation against orphan cleanup before database I/O."""
        if action != "prepare":
            return self._transition_locked_under_guard(
                account_id,
                expected_record_version=expected_record_version,
                action=action,
                binding_id=binding_id,
                reason=reason,
            )
        root, guard = acquire_credential_staging_guard(self._reference._approved_root)
        try:
            return self._transition_locked_under_guard(
                account_id,
                expected_record_version=expected_record_version,
                action=action,
                binding_id=binding_id,
                reason=reason,
            )
        finally:
            os.close(guard)
            os.close(root)

    def _transition_locked_under_guard(
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
