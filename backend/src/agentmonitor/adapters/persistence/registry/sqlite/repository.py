"""M02 production repository over the real file-backed SQLite policy."""

# ruff: noqa: E501 -- SQL text preserves auditable column and predicate ordering.

from datetime import datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    archive_bindings_in_transaction,
    ensure_access_target_in_transaction,
    ensure_current_binding_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.persistence.registry.sqlite.registry_transaction import (
    RegistryRepositoryErrorV1 as RegistryRepositoryErrorV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.registry_transaction import (
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
from agentmonitor.contracts.provider_system_v1 import DiscoveryOutcomeV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    ActiveCredentialBindingRefV1,
    AssertCredentialAccountOwnershipCommandV1,
    CloudMonitoringTargetV1,
    ConfirmIdentityAssociationCommandV1,
    ConfirmProviderIdentityFingerprintCommandV1,
    DiscoveryCandidateViewV1,
    DiscoveryReconciliationViewV1,
    MaskedRegistryFieldV1,
    MonitoringProfileViewV1,
    OrganizationOrderingViewV1,
    OrganizationViewV1,
    ProviderIdentityResolutionV1,
    ProviderInstallationViewV1,
    ProviderTargetRefV1,
    RegistryCloudResourceMembershipV2,
    RegistryLocalResourceTargetV2,
    RegistryScopeKindV1,
    RegistryScopeSnapshotV1,
    RegistryScopeSnapshotV2,
    ResolveProviderIdentityFingerprintQueryV1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    EnrollMonitoringGraphCommandV1,
    RegistryPolicyErrorV1,
    decide_account_monitoring,
    decide_candidate_evidence_transition,
    decide_command_replay,
    decide_installation_only_reconciliation,
    decide_provider_identity_confirmation,
    ensure_candidate_confirmation_is_current,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationCommandV1,
    EditOrganizationCommandV1,
    RegistryCommandConflictV1,
    ReorderOrganizationsCommandV1,
)
from agentmonitor.modules.registry.domain.cloud_verification import (
    cloud_verification_enqueue_account_version,
    decide_cloud_binding_reassertion,
    decide_cloud_owner_assertion,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError


def _candidate_evidence_set_digest(row: RowMapping) -> str:
    """Digest every current identity-evidence field without exposing its values."""
    return _candidate_evidence_set_digest_from_values(
        candidate_id=row["candidate_id"],
        evidence_class=row["evidence_class"],
        evidence_reference=row["evidence_reference"],
        provider_installation_id=row["provider_installation_id"],
        provider_key=row["provider_key"],
        source_class=row["source_class"],
        source_identity_fingerprint=row["source_identity_fingerprint"],
        source_schema=row["source_schema"],
    )


def _candidate_evidence_set_digest_from_values(
    *,
    candidate_id: str,
    evidence_class: str,
    evidence_reference: str,
    provider_installation_id: str,
    provider_key: str,
    source_class: str,
    source_identity_fingerprint: str,
    source_schema: str,
) -> str:
    return _fingerprint(
        {
            "candidate_id": candidate_id,
            "evidence_class": evidence_class,
            "evidence_reference": evidence_reference,
            "provider_installation_id": provider_installation_id,
            "provider_key": provider_key,
            "source_class": source_class,
            "source_identity_fingerprint": source_identity_fingerprint,
            "source_schema": source_schema,
        }
    )


def _utc_value(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _installation_only_protected_state(
    connection: Connection, provider_key: str
) -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Snapshot provider-owned identity/account/profile rows inside one transaction."""
    statements = (
        (
            "SELECT * FROM reg_discovery_candidate WHERE provider_key=? "
            "ORDER BY candidate_id",
            (provider_key,),
        ),
        (
            "SELECT * FROM reg_account WHERE provider_key=? ORDER BY account_id",
            (provider_key,),
        ),
        (
            "SELECT p.* FROM reg_monitoring_profile p "
            "JOIN reg_account a ON a.account_id=p.account_id "
            "WHERE a.provider_key=? ORDER BY p.profile_id",
            (provider_key,),
        ),
        (
            "SELECT l.* FROM reg_profile_resource_link l "
            "JOIN reg_monitoring_profile p ON p.profile_id=l.profile_id "
            "JOIN reg_account a ON a.account_id=p.account_id "
            "WHERE a.provider_key=? ORDER BY l.profile_id, l.resource_id",
            (provider_key,),
        ),
    )
    return tuple(
        tuple(tuple(row) for row in connection.exec_driver_sql(sql, parameters).all())
        for sql, parameters in statements
    )


def _provider_identity_resolution(
    connection: Connection, query: ResolveProviderIdentityFingerprintQueryV1
) -> ProviderIdentityResolutionV1:
    revision = _current_revision(connection)
    rows = (
        connection.exec_driver_sql(
            "SELECT c.identity_scheme_version, "
            "c.decision_state AS claim_decision_state, "
            "c.evidence_class AS claim_evidence_class, "
            "c.owner_principal_id, c.owner_confirmed_at, "
            "c.account_id, a.provider_key AS account_provider_key, "
            "a.lifecycle AS account_lifecycle, "
            "a.identity_state AS account_identity_state, "
            "a.record_version AS account_record_version, "
            "d.decision_state AS identity_decision_state, "
            "d.evidence_class AS identity_decision_evidence_class, "
            "d.account_id AS identity_decision_account_id, "
            "d.source_contract_version, d.evidence_set_digest "
            "FROM reg_provider_identity_claim c "
            "LEFT JOIN reg_account a ON a.account_id=c.account_id "
            "LEFT JOIN reg_identity_decision d ON d.claim_id=c.claim_id "
            "AND d.invalidated_at IS NULL "
            "WHERE c.provider_key=? AND c.identity_scheme=? "
            "AND c.identity_scope=? AND c.subject_fingerprint=? "
            "AND c.invalidated_at IS NULL",
            (
                query.provider_key,
                query.identity_scheme,
                query.identity_scope,
                query.subject_fingerprint,
            ),
        )
        .mappings()
        .all()
    )
    if not rows:
        return ProviderIdentityResolutionV1(
            "unresolved", None, None, "provider_identity_unresolved", revision
        )
    if len(rows) != 1:
        return ProviderIdentityResolutionV1(
            "conflict", None, None, "provider_identity_conflict", revision
        )
    row = rows[0]
    is_exact_active_owner_claim = (
        int(row["identity_scheme_version"]) == query.identity_scheme_version
        and row["claim_decision_state"] == "owner_confirmed"
        and row["claim_evidence_class"] == "owner_confirmed"
        and row["owner_principal_id"] is not None
        and row["owner_confirmed_at"] is not None
        and row["account_id"] is not None
        and row["account_provider_key"] == query.provider_key
        and row["account_lifecycle"] == "active"
        and row["account_identity_state"] == "owner_confirmed"
        and row["account_record_version"] is not None
        and row["identity_decision_state"] == "owner_confirmed"
        and row["identity_decision_evidence_class"] == "owner_confirmed"
        and row["identity_decision_account_id"] == row["account_id"]
        and row["source_contract_version"] == "registry.v1"
        and isinstance(row["evidence_set_digest"], str)
        and len(row["evidence_set_digest"]) == 64
        and all(value in "0123456789abcdef" for value in row["evidence_set_digest"])
    )
    if not is_exact_active_owner_claim:
        return ProviderIdentityResolutionV1(
            "conflict", None, None, "provider_identity_conflict", revision
        )
    return ProviderIdentityResolutionV1(
        "resolved",
        OpaqueIdV1(str(row["account_id"])),
        int(row["account_record_version"]),
        "provider_identity_owner_confirmed",
        revision,
    )


def _invalidate_other_provider_identity_claims(
    connection: Connection,
    *,
    provider_key: str,
    identity_scheme: str,
    identity_scope: str,
    identity_scheme_version: int,
    account_id: str,
    retained_claim_id: str | None,
    revision: int,
    correlation_id: str,
    causation_id: str,
    instant: str,
) -> None:
    """Retire an account's replaced fingerprint in the confirmation transaction."""
    rows = (
        connection.exec_driver_sql(
            "SELECT claim_id, record_version FROM reg_provider_identity_claim "
            "WHERE provider_key=? AND identity_scheme=? AND identity_scope=? "
            "AND identity_scheme_version=? AND account_id=? "
            "AND invalidated_at IS NULL AND (? IS NULL OR claim_id<>?) "
            "ORDER BY claim_id",
            (
                provider_key,
                identity_scheme,
                identity_scope,
                identity_scheme_version,
                account_id,
                retained_claim_id,
                retained_claim_id,
            ),
        )
        .mappings()
        .all()
    )
    for row in rows:
        claim_id = str(row["claim_id"])
        claim_version = int(row["record_version"]) + 1
        connection.exec_driver_sql(
            "UPDATE reg_identity_decision SET invalidated_at=?, "
            "record_version=record_version+1 WHERE claim_id=? "
            "AND invalidated_at IS NULL",
            (instant, claim_id),
        )
        connection.exec_driver_sql(
            "UPDATE reg_provider_identity_claim SET invalidated_at=?, "
            "record_version=? WHERE claim_id=? AND invalidated_at IS NULL",
            (instant, claim_version, claim_id),
        )
        _append_outbox(
            connection,
            subject_type="identity",
            subject_id=claim_id,
            aggregate_version=claim_version,
            revision=revision,
            change_kind="invalidated",
            correlation_id=correlation_id,
            causation_id=causation_id,
            instant=instant,
        )


def _organization(row: RowMapping) -> OrganizationViewV1:
    return OrganizationViewV1(
        organization_id=OpaqueIdV1(row["organization_id"]),
        name=row["display_name"],
        description=row["description"],
        display_order=row["display_order"],
        lifecycle=row["lifecycle"],
        active_account_count=row["active_account_count"],
        archived_account_count=row["archived_account_count"],
        record_version=row["record_version"],
        registry_revision=row["registry_revision"],
        created_at=_utc_value(row["created_at"]),  # type: ignore[arg-type]
        updated_at=_utc_value(row["updated_at"]),  # type: ignore[arg-type]
        archived_at=_utc_value(row["archived_at"]),
    )


def _account(row: RowMapping) -> AccountViewV1:
    identity_state = row["identity_state"]
    preference = row["monitoring_preference"]
    lifecycle = row["lifecycle"]
    monitoring = decide_account_monitoring(
        lifecycle=lifecycle,
        monitoring_preference=preference,
        identity_state=identity_state,
    )
    organization_id = row["organization_id"]
    return AccountViewV1(
        account_id=OpaqueIdV1(row["account_id"]),
        provider_key=row["provider_key"],
        friendly_name=row["friendly_name"],
        organization_id=(
            OpaqueIdV1(organization_id) if organization_id is not None else None
        ),
        lifecycle=lifecycle,
        monitoring_preference=preference,
        is_effective_monitoring_enabled=monitoring.is_enabled,
        effective_monitoring_reason=monitoring.reason_code,
        identity_state=identity_state,
        masked_identity=MaskedRegistryFieldV1(
            "withheld", None, "identity_privacy_minimized"
        ),
        record_version=row["record_version"],
        registry_revision=row["registry_revision"],
        created_at=_utc_value(row["created_at"]),  # type: ignore[arg-type]
        updated_at=_utc_value(row["updated_at"]),  # type: ignore[arg-type]
        archived_at=_utc_value(row["archived_at"]),
    )


class SqliteRegistryRepositoryV1:
    """Owns only ``reg_*`` rows and bounded M02 transactions."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    @staticmethod
    def _organization_by_id(
        connection: Connection, organization_id: str
    ) -> OrganizationViewV1:
        row = (
            connection.exec_driver_sql(
                "SELECT o.*, s.registry_revision, "
                "(SELECT count(*) FROM reg_account a "
                "WHERE a.organization_id=o.organization_id "
                "AND a.lifecycle <> 'archived') AS active_account_count, "
                "(SELECT count(*) FROM reg_account a "
                "WHERE a.organization_id=o.organization_id "
                "AND a.lifecycle = 'archived') AS archived_account_count "
                "FROM reg_organization o CROSS JOIN reg_registry_state s "
                "WHERE s.singleton_key=1 AND o.organization_id=?",
                (organization_id,),
            )
            .mappings()
            .one()
        )
        return _organization(row)

    def create_organization(
        self, command: CreateOrganizationCommandV1
    ) -> OrganizationViewV1:
        operation = "create_organization"
        command_digest = _digest(command.command_id.value)
        request_fingerprint = _fingerprint(
            {
                "description": command.description,
                "name": command.name,
                "operation": operation,
            }
        )
        instant = _utc_text(command.requested_at)
        normalized_name = command.name.casefold()
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint, outcome_subject_id "
                            "FROM reg_command_receipt WHERE principal_id=? "
                            "AND operation_key=? AND idempotency_key_digest=?",
                            (command.principal_id.value, operation, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if receipt is not None:
                        if receipt["request_fingerprint"] != request_fingerprint:
                            connection.rollback()
                            raise RegistryCommandConflictV1(
                                "registry_idempotency_conflict"
                            )
                        result = self._organization_by_id(
                            connection, receipt["outcome_subject_id"]
                        )
                        connection.rollback()
                        return result
                    duplicate = connection.exec_driver_sql(
                        "SELECT 1 FROM reg_organization WHERE normalized_name=? "
                        "AND lifecycle='active' LIMIT 1",
                        (normalized_name,),
                    ).scalar_one_or_none()
                    if duplicate is not None:
                        connection.rollback()
                        raise RegistryCommandConflictV1("registry_name_conflict")
                    organization_id = _identifier()
                    display_order = int(
                        connection.exec_driver_sql(
                            "SELECT coalesce(max(display_order), -1) + 1 "
                            "FROM reg_organization WHERE lifecycle='active'"
                        ).scalar_one()
                    )
                    revision = _next_revision(connection, instant)
                    connection.exec_driver_sql(
                        "INSERT INTO reg_organization "
                        "(organization_id, normalized_name, display_name, description, "
                        "lifecycle, display_order, record_version, created_at, "
                        "updated_at, "
                        "archived_at, creation_command_digest) "
                        "VALUES (?, ?, ?, ?, 'active', ?, 1, ?, ?, NULL, ?)",
                        (
                            organization_id,
                            normalized_name,
                            command.name,
                            command.description,
                            display_order,
                            instant,
                            instant,
                            command_digest,
                        ),
                    )
                    _append_change(
                        connection,
                        subject_type="organization",
                        subject_id=organization_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="created",
                        actor_id=command.principal_id.value,
                        correlation_id=command.command_id.value,
                        command_digest=command_digest,
                        instant=instant,
                        new_name=command.name,
                        new_lifecycle="active",
                    )
                    _append_outbox(
                        connection,
                        subject_type="organization",
                        subject_id=organization_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="created",
                        correlation_id=command.command_id.value,
                        causation_id=command.command_id.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, "
                        "expires_at) "
                        "VALUES (?, ?, ?, ?, ?, 'organization', ?, 1, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            request_fingerprint,
                            organization_id,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    result = self._organization_by_id(connection, organization_id)
                    connection.commit()
                    return result
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def list_organizations(
        self, page_size: int = 100, after_key: str | None = None
    ) -> tuple[OrganizationViewV1, ...]:
        if type(page_size) is not int or not 1 <= page_size <= 201:
            raise ValueError("registry_page_size_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    after: tuple[str, int, str] | None = None
                    if after_key is not None:
                        cursor_row = connection.exec_driver_sql(
                            "SELECT lifecycle, display_order, organization_id "
                            "FROM reg_organization WHERE organization_id=?",
                            (after_key,),
                        ).one_or_none()
                        if cursor_row is None:
                            raise ValueError("registry_cursor_invalid")
                        after = (
                            str(cursor_row.lifecycle),
                            int(cursor_row.display_order),
                            str(cursor_row.organization_id),
                        )
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT o.*, s.registry_revision, "
                            "(SELECT count(*) FROM reg_account a "
                            "WHERE a.organization_id=o.organization_id "
                            "AND a.lifecycle <> 'archived') AS active_account_count, "
                            "(SELECT count(*) FROM reg_account a "
                            "WHERE a.organization_id=o.organization_id "
                            "AND a.lifecycle = 'archived') AS archived_account_count "
                            "FROM reg_organization o CROSS JOIN reg_registry_state s "
                            "WHERE s.singleton_key=1 AND "
                            "(? IS NULL OR (o.lifecycle, o.display_order, "
                            "o.organization_id) > (?, ?, ?)) "
                            "ORDER BY o.lifecycle, "
                            "o.display_order, "
                            "o.organization_id LIMIT ?",
                            (
                                after_key,
                                after[0] if after else None,
                                after[1] if after else None,
                                after[2] if after else None,
                                page_size,
                            ),
                        )
                        .mappings()
                        .all()
                    )
            return tuple(_organization(row) for row in rows)
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def get_organization(
        self, organization_id: OpaqueIdV1
    ) -> OrganizationViewV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    exists = connection.exec_driver_sql(
                        "SELECT 1 FROM reg_organization WHERE organization_id=?",
                        (organization_id.value,),
                    ).scalar_one_or_none()
                    return (
                        self._organization_by_id(connection, organization_id.value)
                        if exists is not None
                        else None
                    )
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def edit_organization(
        self, command: EditOrganizationCommandV1
    ) -> OrganizationViewV1:
        operation = "edit_organization_" + command.action
        command_digest = _digest(command.command_id.value)
        request_fingerprint = _fingerprint(
            {
                "organization_id": command.organization_id.value,
                "expected_version": command.expected_version,
                "action": command.action,
                "name": command.name,
            }
        )
        instant = _utc_text(command.requested_at)
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
                            (command.principal_id.value, operation, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if receipt is not None:
                        if receipt["request_fingerprint"] != request_fingerprint:
                            raise RegistryCommandConflictV1(
                                "registry_idempotency_conflict"
                            )
                        result = self._organization_by_id(
                            connection, receipt["outcome_subject_id"]
                        )
                        if result.record_version != receipt["outcome_record_version"]:
                            raise RegistryCommandConflictV1("registry_replay_stale")
                        connection.rollback()
                        return result
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM reg_organization WHERE organization_id=?",
                            (command.organization_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        raise RegistryCommandConflictV1("registry_subject_not_found")
                    if row["record_version"] != command.expected_version:
                        raise RegistryCommandConflictV1("registry_version_conflict")
                    name = row["display_name"]
                    lifecycle = row["lifecycle"]
                    archived_at = row["archived_at"]
                    display_order = row["display_order"]
                    if command.action == "rename":
                        name = command.name
                    elif command.action == "archive":
                        if lifecycle == "archived":
                            raise RegistryCommandConflictV1("registry_subject_archived")
                        assigned = connection.exec_driver_sql(
                            "SELECT 1 FROM reg_account WHERE organization_id=? "
                            "AND lifecycle <> 'archived' LIMIT 1",
                            (command.organization_id.value,),
                        ).scalar_one_or_none()
                        if assigned is not None:
                            raise RegistryCommandConflictV1(
                                "registry_organization_not_empty"
                            )
                        lifecycle = "archived"
                        archived_at = instant
                    elif command.action == "restore":
                        if lifecycle != "archived":
                            raise RegistryCommandConflictV1(
                                "registry_subject_not_archived"
                            )
                        lifecycle = "active"
                        archived_at = None
                        display_order = int(
                            connection.exec_driver_sql(
                                "SELECT coalesce(max(display_order), -1) + 1 "
                                "FROM reg_organization WHERE lifecycle='active'"
                            ).scalar_one()
                        )
                    if lifecycle == "active":
                        duplicate = connection.exec_driver_sql(
                            "SELECT 1 FROM reg_organization WHERE normalized_name=? "
                            "AND lifecycle='active' AND organization_id<>? LIMIT 1",
                            (name.casefold(), command.organization_id.value),
                        ).scalar_one_or_none()
                        if duplicate is not None:
                            raise RegistryCommandConflictV1("registry_name_conflict")
                    if name == row["display_name"] and lifecycle == row["lifecycle"]:
                        result = self._organization_by_id(
                            connection, command.organization_id.value
                        )
                        connection.rollback()
                        return result
                    version = command.expected_version + 1
                    revision = _next_revision(connection, instant)
                    connection.exec_driver_sql(
                        "UPDATE reg_organization SET display_name=?, normalized_name=?, "
                        "lifecycle=?, archived_at=?, display_order=?, "
                        "record_version=?, updated_at=? WHERE organization_id=? "
                        "AND record_version=?",
                        (
                            name,
                            name.casefold(),
                            lifecycle,
                            archived_at,
                            display_order,
                            version,
                            instant,
                            command.organization_id.value,
                            command.expected_version,
                        ),
                    )
                    if command.action == "archive":
                        from agentmonitor.adapters.persistence.registry.sqlite.coverage_records import (
                            invalidate_coverage_in_transaction,
                        )

                        invalidate_coverage_in_transaction(
                            connection,
                            organization_id=command.organization_id.value,
                            reason="organization_archived",
                            revision=revision,
                            principal_id=command.principal_id.value,
                            command_id=command.command_id.value,
                            instant=instant,
                        )
                    _append_change(
                        connection,
                        subject_type="organization",
                        subject_id=command.organization_id.value,
                        aggregate_version=version,
                        revision=revision,
                        change_kind=command.action,
                        actor_id=command.principal_id.value,
                        correlation_id=command.command_id.value,
                        command_digest=command_digest,
                        instant=instant,
                        previous_name=row["display_name"],
                        new_name=name,
                        previous_lifecycle=row["lifecycle"],
                        new_lifecycle=lifecycle,
                    )
                    _append_outbox(
                        connection,
                        subject_type="organization",
                        subject_id=command.organization_id.value,
                        aggregate_version=version,
                        revision=revision,
                        change_kind=command.action,
                        correlation_id=command.command_id.value,
                        causation_id=command.command_id.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, 'organization', ?, ?, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            request_fingerprint,
                            command.organization_id.value,
                            version,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    result = self._organization_by_id(
                        connection, command.organization_id.value
                    )
                    connection.commit()
                    return result
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def reorder_organizations(
        self, command: ReorderOrganizationsCommandV1
    ) -> OrganizationOrderingViewV1:
        operation = "reorder_organizations"
        command_digest = _digest(command.command_id.value)
        ids = tuple(item.value for item in command.ordered_organization_ids)
        request_fingerprint = _fingerprint(
            {"ids": ids, "expected_revision": command.expected_registry_revision}
        )
        instant = _utc_text(command.requested_at)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint, registry_revision "
                            "FROM reg_command_receipt WHERE principal_id=? "
                            "AND operation_key=? AND idempotency_key_digest=?",
                            (command.principal_id.value, operation, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if receipt is not None:
                        if receipt["request_fingerprint"] != request_fingerprint:
                            raise RegistryCommandConflictV1(
                                "registry_idempotency_conflict"
                            )
                        if (
                            _current_revision(connection)
                            != receipt["registry_revision"]
                        ):
                            raise RegistryCommandConflictV1("registry_replay_stale")
                        connection.rollback()
                        return OrganizationOrderingViewV1(
                            command.ordered_organization_ids,
                            receipt["registry_revision"],
                        )
                    current_revision = _current_revision(connection)
                    if current_revision != command.expected_registry_revision:
                        raise RegistryCommandConflictV1("registry_revision_conflict")
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT organization_id, display_order, record_version "
                            "FROM reg_organization WHERE lifecycle='active' "
                            "ORDER BY display_order, organization_id"
                        )
                        .mappings()
                        .all()
                    )
                    current_ids = tuple(row["organization_id"] for row in rows)
                    if len(current_ids) != len(ids) or set(current_ids) != set(ids):
                        raise RegistryCommandConflictV1("registry_order_set_invalid")
                    if current_ids == ids:
                        connection.rollback()
                        return OrganizationOrderingViewV1(
                            command.ordered_organization_ids, current_revision
                        )
                    revision = _next_revision(connection, instant)
                    by_id = {row["organization_id"]: row for row in rows}
                    for index, organization_id in enumerate(ids):
                        row = by_id[organization_id]
                        if row["display_order"] == index:
                            continue
                        version = int(row["record_version"]) + 1
                        connection.exec_driver_sql(
                            "UPDATE reg_organization SET display_order=?, "
                            "record_version=?, updated_at=? WHERE organization_id=?",
                            (index, version, instant, organization_id),
                        )
                        _append_change(
                            connection,
                            subject_type="organization",
                            subject_id=organization_id,
                            aggregate_version=version,
                            revision=revision,
                            change_kind="reordered",
                            actor_id=command.principal_id.value,
                            correlation_id=command.command_id.value,
                            command_digest=command_digest,
                            instant=instant,
                        )
                        _append_outbox(
                            connection,
                            subject_type="organization",
                            subject_id=organization_id,
                            aggregate_version=version,
                            revision=revision,
                            change_kind="reordered",
                            correlation_id=command.command_id.value,
                            causation_id=command.command_id.value,
                            instant=instant,
                        )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, 'organization_ordering', ?, 1, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            request_fingerprint,
                            command.command_id.value,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    connection.commit()
                    return OrganizationOrderingViewV1(
                        command.ordered_organization_ids, revision
                    )
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1() from None

    def register_pending_account(
        self, command: CreatePendingAccountCommandV1
    ) -> AccountViewV1:
        operation = "register_pending_account"
        command_digest = _digest(command.command_id.value)
        request_fingerprint = _fingerprint(
            {
                "provider_key": command.provider_key,
                "manifest_reference": command.manifest_reference,
                "friendly_name": command.friendly_name,
                "organization_id": (
                    command.organization_id.value if command.organization_id else None
                ),
                "operation": operation,
            }
        )
        instant = _utc_text(command.requested_at)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint, outcome_subject_id "
                            "FROM reg_command_receipt WHERE principal_id=? "
                            "AND operation_key=? AND idempotency_key_digest=?",
                            (command.principal_id.value, operation, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if receipt is not None:
                        if receipt["request_fingerprint"] != request_fingerprint:
                            raise RegistryCommandConflictV1(
                                "registry_idempotency_conflict"
                            )
                        result = self._account_by_id(
                            connection, receipt["outcome_subject_id"]
                        )
                        connection.rollback()
                        return result
                    if command.organization_id is not None:
                        lifecycle = connection.exec_driver_sql(
                            "SELECT lifecycle FROM reg_organization WHERE organization_id=?",
                            (command.organization_id.value,),
                        ).scalar_one_or_none()
                        if lifecycle != "active":
                            raise RegistryCommandConflictV1(
                                "registry_organization_unavailable"
                            )
                    duplicate = connection.exec_driver_sql(
                        "SELECT 1 FROM reg_account WHERE provider_key=? "
                        "AND normalized_name=? AND lifecycle <> 'archived' LIMIT 1",
                        (command.provider_key, command.friendly_name.casefold()),
                    ).scalar_one_or_none()
                    if duplicate is not None:
                        raise RegistryCommandConflictV1("registry_alias_conflict")
                    provider = connection.exec_driver_sql(
                        "SELECT lifecycle FROM reg_provider_definition WHERE provider_key=?",
                        (command.provider_key,),
                    ).scalar_one_or_none()
                    if provider is None:
                        connection.exec_driver_sql(
                            "INSERT INTO reg_provider_definition "
                            "(provider_key, manifest_reference, lifecycle, "
                            "first_admitted_at, last_admitted_at, record_version) "
                            "VALUES (?, ?, 'active', ?, ?, 1)",
                            (
                                command.provider_key,
                                command.manifest_reference,
                                instant,
                                instant,
                            ),
                        )
                    elif provider != "active":
                        raise RegistryCommandConflictV1("registry_provider_unavailable")
                    account_id = _identifier()
                    revision = _next_revision(connection, instant)
                    connection.exec_driver_sql(
                        "INSERT INTO reg_account "
                        "(account_id, provider_key, friendly_name, normalized_name, "
                        "organization_id, lifecycle, identity_state, monitoring_preference, "
                        "record_version, created_at, updated_at, archived_at, "
                        "creation_command_digest) "
                        "VALUES (?, ?, ?, ?, ?, 'pending', 'unresolved', 'disabled', "
                        "1, ?, ?, NULL, ?)",
                        (
                            account_id,
                            command.provider_key,
                            command.friendly_name,
                            command.friendly_name.casefold(),
                            command.organization_id.value
                            if command.organization_id
                            else None,
                            instant,
                            instant,
                            command_digest,
                        ),
                    )
                    _append_change(
                        connection,
                        subject_type="account",
                        subject_id=account_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="registered_pending",
                        actor_id=command.principal_id.value,
                        correlation_id=command.command_id.value,
                        command_digest=command_digest,
                        instant=instant,
                        new_name=command.friendly_name,
                        new_organization_id=(
                            command.organization_id.value
                            if command.organization_id
                            else None
                        ),
                        new_lifecycle="pending",
                    )
                    _append_outbox(
                        connection,
                        subject_type="account",
                        subject_id=account_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="registered_pending",
                        correlation_id=command.command_id.value,
                        causation_id=command.command_id.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, 'account', ?, 1, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            request_fingerprint,
                            account_id,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    result = self._account_by_id(connection, account_id)
                    connection.commit()
                    return result
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def edit_account(self, command: EditAccountCommandV1) -> AccountViewV1:
        if command.action == "archive":
            account = self.get_account(command.account_id)
            if account is not None and account.provider_key == "ollama":
                with account_credential_lock(self._database_ref, command.account_id):
                    return self._edit_account_locked(command)
        return self._edit_account_locked(command)

    def _edit_account_locked(self, command: EditAccountCommandV1) -> AccountViewV1:
        operation = "edit_account_" + command.action
        command_digest = _digest(command.command_id.value)
        request_fingerprint = _fingerprint(
            {
                "account_id": command.account_id.value,
                "expected_version": command.expected_version,
                "action": command.action,
                "friendly_name": command.friendly_name,
                "monitoring_preference": command.monitoring_preference,
                "organization_id": (
                    command.organization_id.value if command.organization_id else None
                ),
            }
        )
        instant = _utc_text(command.requested_at)
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
                            (command.principal_id.value, operation, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if receipt is not None:
                        if receipt["request_fingerprint"] != request_fingerprint:
                            raise RegistryCommandConflictV1(
                                "registry_idempotency_conflict"
                            )
                        result = self._account_by_id(
                            connection, receipt["outcome_subject_id"]
                        )
                        if result.record_version != receipt["outcome_record_version"]:
                            raise RegistryCommandConflictV1("registry_replay_stale")
                        connection.rollback()
                        return result
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM reg_account WHERE account_id=?",
                            (command.account_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        raise RegistryCommandConflictV1("registry_subject_not_found")
                    if row["record_version"] != command.expected_version:
                        raise RegistryCommandConflictV1("registry_version_conflict")
                    name = row["friendly_name"]
                    organization_id = row["organization_id"]
                    lifecycle = row["lifecycle"]
                    archived_at = row["archived_at"]
                    preference = row["monitoring_preference"]
                    if command.action == "rename":
                        if command.friendly_name is None:
                            raise RegistryRepositoryErrorV1()
                        name = command.friendly_name
                        duplicate = connection.exec_driver_sql(
                            "SELECT 1 FROM reg_account WHERE provider_key=? "
                            "AND normalized_name=? AND lifecycle <> 'archived' "
                            "AND account_id<>? LIMIT 1",
                            (
                                row["provider_key"],
                                name.casefold(),
                                command.account_id.value,
                            ),
                        ).scalar_one_or_none()
                        if duplicate is not None:
                            raise RegistryCommandConflictV1("registry_alias_conflict")
                    elif command.action == "assign":
                        if lifecycle == "archived":
                            raise RegistryCommandConflictV1("registry_subject_archived")
                        organization_id = (
                            command.organization_id.value
                            if command.organization_id is not None
                            else None
                        )
                    elif command.action == "monitoring":
                        if lifecycle == "archived":
                            raise RegistryCommandConflictV1("registry_subject_archived")
                        if command.monitoring_preference == "enabled":
                            if lifecycle != "active" or row["identity_state"] not in {
                                "matched",
                                "owner_confirmed",
                            }:
                                raise RegistryCommandConflictV1(
                                    "registry_monitoring_not_eligible"
                                )
                            eligible = connection.exec_driver_sql(
                                "SELECT 1 FROM reg_monitoring_profile p "
                                "JOIN reg_account_resource r ON r.account_id=p.account_id "
                                "WHERE p.account_id=? AND p.lifecycle='active' "
                                "AND p.compatibility_state='compatible' "
                                "AND p.identity_verification_state IN "
                                "('owner_confirmed', 'provider_verified', 'matched') "
                                "AND r.lifecycle='active' LIMIT 1",
                                (command.account_id.value,),
                            ).scalar_one_or_none()
                            if eligible is None:
                                raise RegistryCommandConflictV1(
                                    "registry_monitoring_not_eligible"
                                )
                        preference = command.monitoring_preference
                    elif command.action == "archive":
                        if lifecycle == "archived":
                            raise RegistryCommandConflictV1("registry_subject_archived")
                        lifecycle = "archived"
                        archived_at = instant
                        preference = "disabled"
                    elif command.action == "restore":
                        if lifecycle != "archived":
                            raise RegistryCommandConflictV1(
                                "registry_subject_not_archived"
                            )
                        lifecycle = (
                            "active"
                            if row["identity_state"] in {"matched", "owner_confirmed"}
                            else "pending"
                        )
                        archived_at = None
                    if organization_id is not None and command.action in {
                        "assign",
                        "restore",
                    }:
                        organization_state = connection.exec_driver_sql(
                            "SELECT lifecycle FROM reg_organization WHERE organization_id=?",
                            (organization_id,),
                        ).scalar_one_or_none()
                        if organization_state != "active":
                            raise RegistryCommandConflictV1(
                                "registry_organization_unavailable"
                            )
                    if (
                        name == row["friendly_name"]
                        and organization_id == row["organization_id"]
                        and lifecycle == row["lifecycle"]
                        and preference == row["monitoring_preference"]
                    ):
                        result = self._account_by_id(
                            connection, command.account_id.value
                        )
                        connection.rollback()
                        return result
                    version = command.expected_version + 1
                    if command.action == "archive" and row["provider_key"] == "ollama":
                        archive_bindings_in_transaction(connection, command.account_id)
                    revision = _next_revision(connection, instant)
                    connection.exec_driver_sql(
                        "UPDATE reg_account SET friendly_name=?, normalized_name=?, "
                        "organization_id=?, lifecycle=?, archived_at=?, "
                        "monitoring_preference=?, record_version=?, updated_at=? "
                        "WHERE account_id=? AND record_version=?",
                        (
                            name,
                            name.casefold(),
                            organization_id,
                            lifecycle,
                            archived_at,
                            preference,
                            version,
                            instant,
                            command.account_id.value,
                            command.expected_version,
                        ),
                    )
                    if command.action == "archive" or (
                        command.action == "assign"
                        and organization_id != row["organization_id"]
                    ):
                        from agentmonitor.adapters.persistence.registry.sqlite.coverage_records import (
                            invalidate_coverage_in_transaction,
                        )

                        invalidate_coverage_in_transaction(
                            connection,
                            account_id=command.account_id.value,
                            reason=(
                                "account_archived"
                                if command.action == "archive"
                                else "account_reassigned"
                            ),
                            revision=revision,
                            principal_id=command.principal_id.value,
                            command_id=command.command_id.value,
                            instant=instant,
                        )
                    _append_change(
                        connection,
                        subject_type="account",
                        subject_id=command.account_id.value,
                        aggregate_version=version,
                        revision=revision,
                        change_kind=command.action,
                        actor_id=command.principal_id.value,
                        correlation_id=command.command_id.value,
                        command_digest=command_digest,
                        instant=instant,
                        previous_name=row["friendly_name"],
                        new_name=name,
                        previous_organization_id=row["organization_id"],
                        new_organization_id=organization_id,
                        previous_lifecycle=row["lifecycle"],
                        new_lifecycle=lifecycle,
                    )
                    _append_outbox(
                        connection,
                        subject_type="account",
                        subject_id=command.account_id.value,
                        aggregate_version=version,
                        revision=revision,
                        change_kind=command.action,
                        correlation_id=command.command_id.value,
                        causation_id=command.command_id.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, 'account', ?, ?, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            request_fingerprint,
                            command.account_id.value,
                            version,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    result = self._account_by_id(connection, command.account_id.value)
                    connection.commit()
                    return result
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1() from None

    def reconcile_discovery(
        self, outcome: DiscoveryOutcomeV1, *, reconciled_at: datetime
    ) -> DiscoveryReconciliationViewV1:
        return self._reconcile_discovery(
            outcome,
            reconciled_at=reconciled_at,
            installation_only=False,
        )

    def reconcile_installation_only_discovery(
        self, outcome: DiscoveryOutcomeV1, *, reconciled_at: datetime
    ) -> DiscoveryReconciliationViewV1:
        """Run the operator-only installation invariant in the write transaction."""
        return self._reconcile_discovery(
            outcome,
            reconciled_at=reconciled_at,
            installation_only=True,
        )

    def _reconcile_discovery(
        self,
        outcome: DiscoveryOutcomeV1,
        *,
        reconciled_at: datetime,
        installation_only: bool,
    ) -> DiscoveryReconciliationViewV1:
        if outcome.value is None or outcome.provenance is None:
            raise RegistryRepositoryErrorV1("registry_discovery_outcome_invalid")
        instant = _utc_text(reconciled_at)
        provider_key = outcome.provenance.provider_key
        operation_id = outcome.provenance.operation_id.value
        correlation_id = outcome.provenance.correlation_id.value
        operation = (
            "reconcile_installation_only_discovery"
            if installation_only
            else "reconcile_provider_discovery"
        )
        command_digest = _digest(operation_id)
        service_principal = _digest(f"registry-discovery\x00{provider_key}")
        fingerprint_payload: dict[str, object] = {
            "accounts": [
                {
                    "candidate_ref": item.candidate_ref.value,
                    "decision_reference": item.provenance.decision_reference,
                    "evidence_strength": item.evidence_strength,
                    "installation_ref": item.installation_ref.value,
                    "owner_confirmation_required": item.owner_confirmation_required,
                    "source_class": item.provenance.source_class,
                }
                for item in outcome.value.accounts
            ],
            "installations": [
                {
                    "decision_reference": item.provenance.decision_reference,
                    "installation_ref": item.installation_ref.value,
                    "platform_id": item.platform_id,
                    "product_version": item.product_version,
                }
                for item in outcome.value.installations
            ],
            "operation": operation,
            "provider_key": provider_key,
            "state": outcome.state,
        }
        if installation_only:
            fingerprint_payload["installation_only_scope"] = {
                "capability_id": outcome.provenance.capability_id,
                "correlation_id": correlation_id,
                "decision_reference": outcome.provenance.decision_reference,
                "installation_provider_keys": [
                    item.provider_key for item in outcome.value.installations
                ],
            }
        request_fingerprint = _fingerprint(fingerprint_payload)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    installation_only_identity: str | None = None
                    installation_only_platform: str | None = None
                    installation_only_version: str | None = None
                    installation_only_existing_id: str | None = None
                    installation_only_protected_state = None
                    if installation_only:
                        incoming_installation = (
                            outcome.value.installations[0]
                            if len(outcome.value.installations) == 1
                            else None
                        )
                        installation_only_identity = (
                            _digest(
                                f"{provider_key}\x00"
                                f"{incoming_installation.installation_ref.value}"
                            )
                            if incoming_installation is not None
                            else ""
                        )
                        installation_only_platform = (
                            incoming_installation.platform_id
                            if incoming_installation is not None
                            else ""
                        )
                        installation_only_version = (
                            incoming_installation.product_version
                            if incoming_installation is not None
                            else None
                        )
                        existing_installation_rows = (
                            connection.exec_driver_sql(
                                "SELECT provider_installation_id, "
                                "installation_identity_fingerprint, platform_key "
                                "FROM reg_provider_installation "
                                "WHERE provider_key=? ORDER BY "
                                "provider_installation_id",
                                (provider_key,),
                            )
                            .mappings()
                            .all()
                        )
                        existing_installations = tuple(
                            (
                                str(row["installation_identity_fingerprint"]),
                                str(row["platform_key"]),
                            )
                            for row in existing_installation_rows
                        )
                        try:
                            installation_decision = (
                                decide_installation_only_reconciliation(
                                    capability_id=outcome.provenance.capability_id,
                                    account_count=len(outcome.value.accounts),
                                    installation_count=len(outcome.value.installations),
                                    outcome_provider_key=provider_key,
                                    incoming_provider_key=(
                                        incoming_installation.provider_key
                                        if incoming_installation is not None
                                        else ""
                                    ),
                                    incoming_identity_fingerprint=(
                                        installation_only_identity
                                    ),
                                    incoming_platform_key=installation_only_platform,
                                    existing_installations=existing_installations,
                                )
                            )
                        except RegistryPolicyErrorV1 as error:
                            connection.rollback()
                            raise RegistryRepositoryErrorV1(str(error)) from None
                        if installation_decision == "not_applicable":
                            connection.rollback()
                            raise RegistryRepositoryErrorV1(
                                "registry_installation_scope_invalid"
                            )
                        if installation_decision == "update":
                            installation_only_existing_id = str(
                                existing_installation_rows[0][
                                    "provider_installation_id"
                                ]
                            )
                        installation_only_protected_state = (
                            _installation_only_protected_state(connection, provider_key)
                        )
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint FROM reg_command_receipt "
                            "WHERE principal_id=? AND operation_key=? "
                            "AND idempotency_key_digest=?",
                            (service_principal, operation, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    try:
                        replay_decision = decide_command_replay(
                            receipt["request_fingerprint"]
                            if receipt is not None
                            else None,
                            request_fingerprint,
                        )
                    except RegistryPolicyErrorV1 as error:
                        connection.rollback()
                        raise RegistryCommandConflictV1(str(error)) from None
                    if replay_decision == "replay":
                        result = self._discovery_view(connection, provider_key)
                        connection.rollback()
                        return result
                    revision = _next_revision(connection, instant)
                    connection.exec_driver_sql(
                        "INSERT INTO reg_provider_definition "
                        "(provider_key, manifest_reference, lifecycle, "
                        "first_admitted_at, last_admitted_at, record_version) "
                        "VALUES (?, ?, 'active', ?, ?, 1) "
                        "ON CONFLICT(provider_key) DO UPDATE SET "
                        "manifest_reference=excluded.manifest_reference, "
                        "last_admitted_at=excluded.last_admitted_at, "
                        "record_version=reg_provider_definition.record_version+1",
                        (
                            provider_key,
                            outcome.provenance.decision_reference,
                            instant,
                            instant,
                        ),
                    )
                    installation_ids: dict[str, str] = {}
                    for installation in outcome.value.installations:
                        if installation.provider_key != provider_key:
                            raise RegistryRepositoryErrorV1(
                                "registry_discovery_outcome_invalid"
                            )
                        identity = _digest(
                            f"{provider_key}\x00{installation.installation_ref.value}"
                        )
                        current = (
                            connection.exec_driver_sql(
                                "SELECT provider_installation_id, record_version "
                                "FROM reg_provider_installation WHERE provider_key=? "
                                "AND installation_identity_fingerprint=?",
                                (provider_key, identity),
                            )
                            .mappings()
                            .one_or_none()
                        )
                        if current is None:
                            installation_id = _identifier()
                            version = 1
                            connection.exec_driver_sql(
                                "INSERT INTO reg_provider_installation "
                                "(provider_installation_id, provider_key, "
                                "installation_identity_scheme, "
                                "installation_identity_fingerprint, platform_key, "
                                "reported_version, version_state, presence_state, "
                                "first_seen_at, last_seen_at, "
                                "last_discovery_operation_id, "
                                "compatibility_reference, record_version) "
                                "VALUES (?, ?, 'm03_opaque_ref_sha256_v1', ?, ?, ?, ?, "
                                "'present', ?, ?, ?, ?, 1)",
                                (
                                    installation_id,
                                    provider_key,
                                    identity,
                                    installation.platform_id,
                                    installation.product_version,
                                    "known"
                                    if installation.product_version
                                    else "unknown",
                                    instant,
                                    instant,
                                    operation_id,
                                    installation.provenance.decision_reference,
                                ),
                            )
                            change_kind = "discovered"
                        else:
                            installation_id = current["provider_installation_id"]
                            version = int(current["record_version"]) + 1
                            connection.exec_driver_sql(
                                "UPDATE reg_provider_installation SET "
                                "reported_version=?, version_state=?, "
                                "presence_state='present', last_seen_at=?, "
                                "last_discovery_operation_id=?, "
                                "compatibility_reference=?, "
                                "record_version=? WHERE provider_installation_id=?",
                                (
                                    installation.product_version,
                                    "known"
                                    if installation.product_version
                                    else "unknown",
                                    instant,
                                    operation_id,
                                    installation.provenance.decision_reference,
                                    version,
                                    installation_id,
                                ),
                            )
                            change_kind = "presence_changed"
                        installation_ids[installation.installation_ref.value] = (
                            installation_id
                        )
                        _append_outbox(
                            connection,
                            subject_type="installation",
                            subject_id=installation_id,
                            aggregate_version=version,
                            revision=revision,
                            change_kind=change_kind,
                            correlation_id=correlation_id,
                            causation_id=operation_id,
                            instant=instant,
                        )
                    for candidate in outcome.value.accounts:
                        candidate_installation_id = installation_ids.get(
                            candidate.installation_ref.value
                        )
                        if candidate_installation_id is None:
                            raise RegistryRepositoryErrorV1(
                                "registry_discovery_outcome_invalid"
                            )
                        source_fingerprint = _digest(
                            f"{provider_key}\x00{candidate.candidate_ref.value}"
                        )
                        evidence_class = {
                            "strong": "provider_verified",
                            "owner_confirmation_required": "corroborated",
                            "unresolved": "unknown",
                        }[candidate.evidence_strength]
                        current = (
                            connection.exec_driver_sql(
                                "SELECT * "
                                "FROM reg_discovery_candidate WHERE provider_key=? "
                                "AND source_identity_fingerprint=?",
                                (provider_key, source_fingerprint),
                            )
                            .mappings()
                            .one_or_none()
                        )
                        if current is None:
                            candidate_id = _identifier()
                            version = 1
                            connection.exec_driver_sql(
                                "INSERT INTO reg_discovery_candidate "
                                "(candidate_id, provider_key, "
                                "provider_installation_id, candidate_kind, "
                                "source_operation_id, source_schema, source_class, "
                                "source_identity_fingerprint, evidence_class, "
                                "evidence_reference, association_state, "
                                "associated_subject_id, reason_code, first_seen_at, "
                                "last_seen_at, reviewed_at, record_version, "
                                "expires_at) VALUES (?, ?, ?, 'account', ?, "
                                "'DiscoveryOutcomeV1', ?, ?, ?, ?, "
                                "'owner_confirmation_required', NULL, "
                                "'owner_confirmation_required', ?, ?, NULL, 1, ?)",
                                (
                                    candidate_id,
                                    provider_key,
                                    candidate_installation_id,
                                    operation_id,
                                    candidate.provenance.source_class,
                                    source_fingerprint,
                                    evidence_class,
                                    candidate.provenance.decision_reference,
                                    instant,
                                    instant,
                                    _utc_text(reconciled_at + timedelta(days=365)),
                                ),
                            )
                            change_kind = "confirmation_required"
                        else:
                            candidate_id = current["candidate_id"]
                            version = int(current["record_version"]) + 1
                            current_evidence_digest = _candidate_evidence_set_digest(
                                current
                            )
                            proposed_evidence_digest = (
                                _candidate_evidence_set_digest_from_values(
                                    candidate_id=candidate_id,
                                    evidence_class=evidence_class,
                                    evidence_reference=(
                                        candidate.provenance.decision_reference
                                    ),
                                    provider_installation_id=(
                                        candidate_installation_id
                                    ),
                                    provider_key=provider_key,
                                    source_class=candidate.provenance.source_class,
                                    source_identity_fingerprint=source_fingerprint,
                                    source_schema="DiscoveryOutcomeV1",
                                )
                            )
                            transition = decide_candidate_evidence_transition(
                                current_state=current["association_state"],
                                current_evidence_set_digest=current_evidence_digest,
                                proposed_evidence_set_digest=proposed_evidence_digest,
                            )
                            connection.exec_driver_sql(
                                "UPDATE reg_discovery_candidate SET "
                                "source_operation_id=?, "
                                "provider_installation_id=?, source_class=?, "
                                "evidence_class=?, evidence_reference=?, "
                                "association_state=?, reason_code=?, last_seen_at=?, "
                                "record_version=? "
                                "WHERE candidate_id=?",
                                (
                                    operation_id,
                                    candidate_installation_id,
                                    candidate.provenance.source_class,
                                    evidence_class,
                                    candidate.provenance.decision_reference,
                                    transition.state,
                                    transition.reason_code,
                                    instant,
                                    version,
                                    candidate_id,
                                ),
                            )
                            if transition.invalidate_account_eligibility:
                                associated_account_id = current["associated_subject_id"]
                                if associated_account_id is None:
                                    raise RegistryRepositoryErrorV1(
                                        "registry_identity_conflict"
                                    )
                                connection.exec_driver_sql(
                                    "UPDATE reg_account SET identity_state='conflict', "
                                    "record_version=record_version+1, updated_at=? "
                                    "WHERE account_id=?",
                                    (instant, associated_account_id),
                                )
                                connection.exec_driver_sql(
                                    "UPDATE reg_provider_identity_claim SET "
                                    "decision_state='conflict', last_verified_at=?, "
                                    "record_version=record_version+1 "
                                    "WHERE account_id=? AND invalidated_at IS NULL",
                                    (instant, associated_account_id),
                                )
                                connection.exec_driver_sql(
                                    "UPDATE reg_identity_decision SET "
                                    "invalidated_at=?, "
                                    "record_version=record_version+1 "
                                    "WHERE candidate_id=? AND invalidated_at IS NULL",
                                    (instant, candidate_id),
                                )
                                connection.exec_driver_sql(
                                    "INSERT INTO reg_identity_decision "
                                    "(decision_id, candidate_id, claim_id, profile_id, "
                                    "account_id, decision_state, evidence_class, "
                                    "reason_code, evidence_set_digest, "
                                    "source_contract_version, owner_principal_id, "
                                    "owner_confirmed_at, valid_from, invalidated_at, "
                                    "record_version, registry_revision) "
                                    "VALUES (?, ?, NULL, NULL, ?, 'conflict', ?, ?, ?, "
                                    "'registry.v1', NULL, NULL, ?, NULL, 1, ?)",
                                    (
                                        _identifier(),
                                        candidate_id,
                                        associated_account_id,
                                        evidence_class,
                                        transition.reason_code,
                                        proposed_evidence_digest,
                                        instant,
                                        revision,
                                    ),
                                )
                            change_kind = (
                                "conflict_detected"
                                if transition.state == "conflict"
                                else "owner_confirmed"
                                if transition.state == "owner_confirmed"
                                else "confirmation_required"
                            )
                        _append_outbox(
                            connection,
                            subject_type="identity",
                            subject_id=candidate_id,
                            aggregate_version=version,
                            revision=revision,
                            change_kind=change_kind,
                            correlation_id=correlation_id,
                            causation_id=operation_id,
                            instant=instant,
                        )
                    if installation_only_protected_state is not None:
                        protected_state_after = _installation_only_protected_state(
                            connection, provider_key
                        )
                        installations_after = (
                            connection.exec_driver_sql(
                                "SELECT provider_installation_id, "
                                "installation_identity_fingerprint, "
                                "platform_key, reported_version, presence_state "
                                "FROM reg_provider_installation WHERE provider_key=?",
                                (provider_key,),
                            )
                            .mappings()
                            .all()
                        )
                        expected_installation_state = (
                            installation_only_existing_id
                            or installation_ids[
                                outcome.value.installations[0].installation_ref.value
                            ],
                            installation_only_identity,
                            installation_only_platform,
                            installation_only_version,
                            "present",
                        )
                        actual_installation_state = (
                            (
                                installations_after[0]["provider_installation_id"],
                                installations_after[0][
                                    "installation_identity_fingerprint"
                                ],
                                installations_after[0]["platform_key"],
                                installations_after[0]["reported_version"],
                                installations_after[0]["presence_state"],
                            )
                            if len(installations_after) == 1
                            else None
                        )
                        if (
                            protected_state_after != installation_only_protected_state
                            or len(installations_after) != 1
                            or actual_installation_state != expected_installation_state
                        ):
                            connection.rollback()
                            raise RegistryRepositoryErrorV1(
                                "registry_installation_reconciliation_invariant"
                            )
                    provider_record_version = connection.exec_driver_sql(
                        "SELECT record_version FROM reg_provider_definition "
                        "WHERE provider_key=?",
                        (provider_key,),
                    ).scalar_one()
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, "
                        "expires_at) VALUES (?, ?, ?, ?, ?, 'provider', ?, ?, ?, ?, ?)",
                        (
                            _identifier(),
                            service_principal,
                            operation,
                            command_digest,
                            request_fingerprint,
                            provider_key,
                            provider_record_version,
                            revision,
                            instant,
                            _utc_text(reconciled_at + timedelta(days=365)),
                        ),
                    )
                    if installation_only:
                        stored_fingerprint = connection.exec_driver_sql(
                            "SELECT request_fingerprint FROM reg_command_receipt "
                            "WHERE principal_id=? AND operation_key=? "
                            "AND idempotency_key_digest=?",
                            (service_principal, operation, command_digest),
                        ).scalar_one_or_none()
                        try:
                            verified_replay = decide_command_replay(
                                stored_fingerprint, request_fingerprint
                            )
                        except RegistryPolicyErrorV1 as error:
                            connection.rollback()
                            raise RegistryRepositoryErrorV1(str(error)) from None
                        if verified_replay != "replay":
                            connection.rollback()
                            raise RegistryRepositoryErrorV1(
                                "registry_installation_replay_invariant"
                            )
                    result = self._discovery_view(connection, provider_key)
                    connection.commit()
                    return result
        except (RegistryCommandConflictV1, RegistryRepositoryErrorV1):
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, KeyError):
            raise RegistryRepositoryErrorV1() from None

    @staticmethod
    def _discovery_view(
        connection: Connection, provider_key: str
    ) -> DiscoveryReconciliationViewV1:
        revision = _current_revision(connection)
        installations = tuple(
            ProviderInstallationViewV1(
                provider_installation_id=OpaqueIdV1(row["provider_installation_id"]),
                provider_key=row["provider_key"],
                platform_key=row["platform_key"],
                version=MaskedRegistryFieldV1(
                    "known_masked"
                    if row["reported_version"] is not None
                    else "unknown",
                    row["reported_version"],
                    "provider_reported_version"
                    if row["reported_version"] is not None
                    else "provider_version_unknown",
                ),
                presence_state=row["presence_state"],
                first_seen_at=_utc_value(row["first_seen_at"]),  # type: ignore[arg-type]
                last_seen_at=_utc_value(row["last_seen_at"]),  # type: ignore[arg-type]
                record_version=row["record_version"],
                registry_revision=revision,
            )
            for row in connection.exec_driver_sql(
                "SELECT * FROM reg_provider_installation WHERE provider_key=? "
                "ORDER BY provider_installation_id LIMIT 100",
                (provider_key,),
            ).mappings()
        )
        candidates = tuple(
            DiscoveryCandidateViewV1(
                candidate_id=OpaqueIdV1(row["candidate_id"]),
                provider_key=row["provider_key"],
                provider_installation_id=OpaqueIdV1(row["provider_installation_id"]),
                candidate_kind="account",
                association_state=row["association_state"],
                evidence_classes=(row["evidence_class"],),
                evidence_set_digest=_candidate_evidence_set_digest(row),
                masked_label=MaskedRegistryFieldV1(
                    "withheld", None, "identity_privacy_minimized"
                ),
                owner_action_required=row["association_state"]
                == "owner_confirmation_required",
                first_seen_at=_utc_value(row["first_seen_at"]),  # type: ignore[arg-type]
                last_seen_at=_utc_value(row["last_seen_at"]),  # type: ignore[arg-type]
                record_version=row["record_version"],
                registry_revision=revision,
            )
            for row in connection.exec_driver_sql(
                "SELECT * FROM reg_discovery_candidate WHERE provider_key=? "
                "ORDER BY last_seen_at, candidate_id LIMIT 100",
                (provider_key,),
            ).mappings()
        )
        return DiscoveryReconciliationViewV1(installations, candidates, revision)

    def list_discovery_candidates(
        self, provider_key: str | None = None
    ) -> tuple[DiscoveryCandidateViewV1, ...]:
        query = "SELECT * FROM reg_discovery_candidate"
        parameters: tuple[object, ...] = ()
        if provider_key is not None:
            query += " WHERE provider_key=?"
            parameters = (provider_key,)
        query += " ORDER BY last_seen_at, candidate_id LIMIT 100"
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    revision = _current_revision(connection)
                    rows = (
                        connection.exec_driver_sql(query, parameters).mappings().all()
                    )
            return tuple(
                DiscoveryCandidateViewV1(
                    candidate_id=OpaqueIdV1(row["candidate_id"]),
                    provider_key=row["provider_key"],
                    provider_installation_id=OpaqueIdV1(
                        row["provider_installation_id"]
                    ),
                    candidate_kind="account",
                    association_state=row["association_state"],
                    evidence_classes=(row["evidence_class"],),
                    evidence_set_digest=_candidate_evidence_set_digest(row),
                    masked_label=MaskedRegistryFieldV1(
                        "withheld", None, "identity_privacy_minimized"
                    ),
                    owner_action_required=row["association_state"]
                    == "owner_confirmation_required",
                    first_seen_at=_utc_value(row["first_seen_at"]),  # type: ignore[arg-type]
                    last_seen_at=_utc_value(row["last_seen_at"]),  # type: ignore[arg-type]
                    record_version=row["record_version"],
                    registry_revision=revision,
                )
                for row in rows
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def list_provider_installations(
        self,
        provider_key: str | None = None,
        page_size: int = 100,
        after_key: str | None = None,
    ) -> tuple[ProviderInstallationViewV1, ...]:
        query = (
            "SELECT i.*, s.registry_revision FROM reg_provider_installation i "
            "CROSS JOIN reg_registry_state s WHERE s.singleton_key=1"
        )
        parameters: tuple[object, ...] = ()
        if provider_key is not None:
            query += " AND i.provider_key=?"
            parameters = (provider_key,)
        if type(page_size) is not int or not 1 <= page_size <= 201:
            raise RegistryRepositoryErrorV1("registry_query_invalid")
        if after_key is not None:
            query += " AND (i.provider_key, i.provider_installation_id) > ("
            query += "(SELECT provider_key FROM reg_provider_installation WHERE provider_installation_id=?), ?)"
            parameters = (*parameters, after_key, after_key)
        query += " ORDER BY i.provider_key, i.provider_installation_id LIMIT ?"
        parameters = (*parameters, page_size)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(query, parameters).mappings().all()
                    )
            return tuple(
                ProviderInstallationViewV1(
                    provider_installation_id=OpaqueIdV1(
                        str(row["provider_installation_id"])
                    ),
                    provider_key=str(row["provider_key"]),
                    platform_key=str(row["platform_key"]),
                    version=MaskedRegistryFieldV1(
                        "known_masked"
                        if row["reported_version"] is not None
                        else "unknown",
                        str(row["reported_version"])
                        if row["reported_version"] is not None
                        else None,
                        "provider_reported_version"
                        if row["reported_version"] is not None
                        else "provider_version_unknown",
                    ),
                    presence_state=row["presence_state"],
                    first_seen_at=_utc_value(row["first_seen_at"]),  # type: ignore[arg-type]
                    last_seen_at=_utc_value(row["last_seen_at"]),  # type: ignore[arg-type]
                    record_version=int(row["record_version"]),
                    registry_revision=int(row["registry_revision"]),
                )
                for row in rows
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1() from None

    def resolve_provider_identity_fingerprint(
        self, query: ResolveProviderIdentityFingerprintQueryV1
    ) -> ProviderIdentityResolutionV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    return _provider_identity_resolution(connection, query)
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1() from None

    def confirm_provider_identity_fingerprint(
        self, command: ConfirmProviderIdentityFingerprintCommandV1
    ) -> ProviderIdentityResolutionV1:
        operation = "confirm_provider_identity_fingerprint"
        command_digest = _digest(command.idempotency_key.value)
        query = ResolveProviderIdentityFingerprintQueryV1(
            provider_key=command.provider_key,
            identity_scheme=command.identity_scheme,
            identity_scope=command.identity_scope,
            identity_scheme_version=command.identity_scheme_version,
            subject_fingerprint=command.subject_fingerprint,
        )
        request_fingerprint = _fingerprint(
            {
                "account_id": command.account_id.value,
                "expected_account_record_version": (
                    command.expected_account_record_version
                ),
                "identity_scheme": command.identity_scheme,
                "identity_scheme_version": command.identity_scheme_version,
                "identity_scope": command.identity_scope,
                "operation": operation,
                "parser_version": command.parser_version,
                "provider_key": command.provider_key,
                "source_id": command.source_id,
                "source_version": command.source_version,
                "subject_fingerprint": command.subject_fingerprint,
                "evidence_reference": command.evidence_reference.value,
                "expected_evidence_digest": command.expected_evidence_digest,
                **(
                    {"activate_pending_account": True}
                    if command.activate_pending_account
                    else {}
                ),
            }
        )
        instant = _utc_text(command.requested_at)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint FROM reg_command_receipt "
                            "WHERE principal_id=? AND operation_key=? "
                            "AND idempotency_key_digest=?",
                            (
                                command.principal_id.value,
                                operation,
                                command_digest,
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if receipt is not None:
                        if receipt["request_fingerprint"] != request_fingerprint:
                            connection.rollback()
                            raise RegistryCommandConflictV1(
                                "registry_idempotency_conflict"
                            )
                        result = _provider_identity_resolution(connection, query)
                        connection.rollback()
                        return result
                    account = (
                        connection.exec_driver_sql(
                            "SELECT provider_key, lifecycle, identity_state, "
                            "record_version FROM reg_account WHERE account_id=?",
                            (command.account_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if account is None:
                        connection.rollback()
                        raise RegistryCommandConflictV1("registry_subject_not_found")
                    if int(account["record_version"]) != (
                        command.expected_account_record_version
                    ):
                        connection.rollback()
                        raise RegistryCommandConflictV1(
                            "registry_account_version_conflict"
                        )
                    activate_pending = (
                        command.activate_pending_account
                        and account["lifecycle"] == "pending"
                        and account["identity_state"] == "unresolved"
                    )
                    if account["provider_key"] != command.provider_key or (
                        not activate_pending
                        and (
                            account["lifecycle"] != "active"
                            or account["identity_state"] != "owner_confirmed"
                        )
                    ):
                        connection.rollback()
                        raise RegistryCommandConflictV1("registry_identity_conflict")
                    existing_claim = (
                        connection.exec_driver_sql(
                            "SELECT claim_id, account_id, evidence_reference, "
                            "last_verified_at, record_version, invalidated_at "
                            "FROM reg_provider_identity_claim "
                            "WHERE provider_key=? AND identity_scheme=? "
                            "AND identity_scope=? AND subject_fingerprint=?",
                            (
                                command.provider_key,
                                command.identity_scheme,
                                command.identity_scope,
                                command.subject_fingerprint,
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    current = _provider_identity_resolution(connection, query)
                    try:
                        confirmation_action = decide_provider_identity_confirmation(
                            resolution_state=current.state,
                            current_account_matches=(
                                current.account_id == command.account_id
                            ),
                            existing_claim=existing_claim is not None,
                        )
                    except RegistryPolicyErrorV1:
                        connection.rollback()
                        raise RegistryCommandConflictV1(
                            "registry_identity_conflict"
                        ) from None
                    if confirmation_action == "refresh":
                        if existing_claim is None:
                            connection.rollback()
                            raise RegistryCommandConflictV1(
                                "registry_identity_conflict"
                            )
                        current_decision = (
                            connection.exec_driver_sql(
                                "SELECT decision_id, valid_from, record_version "
                                "FROM reg_identity_decision WHERE claim_id=? "
                                "AND invalidated_at IS NULL",
                                (existing_claim["claim_id"],),
                            )
                            .mappings()
                            .one_or_none()
                        )
                        if (
                            current_decision is None
                            or existing_claim["account_id"] != command.account_id.value
                            or instant < str(current_decision["valid_from"])
                            or (
                                existing_claim["last_verified_at"] is not None
                                and instant < str(existing_claim["last_verified_at"])
                            )
                        ):
                            connection.rollback()
                            raise RegistryCommandConflictV1(
                                "registry_identity_conflict"
                            )
                        claim_version = int(existing_claim["record_version"]) + 1
                        revision = _next_revision(connection, instant)
                        _invalidate_other_provider_identity_claims(
                            connection,
                            provider_key=command.provider_key,
                            identity_scheme=command.identity_scheme,
                            identity_scope=command.identity_scope,
                            identity_scheme_version=command.identity_scheme_version,
                            account_id=command.account_id.value,
                            retained_claim_id=str(existing_claim["claim_id"]),
                            revision=revision,
                            correlation_id=command.idempotency_key.value,
                            causation_id=command.evidence_reference.value,
                            instant=instant,
                        )
                        connection.exec_driver_sql(
                            "UPDATE reg_provider_identity_claim SET "
                            "evidence_reference=?, last_verified_at=?, "
                            "owner_principal_id=?, owner_confirmed_at=?, "
                            "record_version=? WHERE claim_id=? "
                            "AND invalidated_at IS NULL",
                            (
                                command.evidence_reference.value,
                                instant,
                                command.principal_id.value,
                                instant,
                                claim_version,
                                existing_claim["claim_id"],
                            ),
                        )
                        connection.exec_driver_sql(
                            "UPDATE reg_identity_decision SET invalidated_at=?, "
                            "record_version=record_version+1 WHERE decision_id=? "
                            "AND invalidated_at IS NULL",
                            (instant, current_decision["decision_id"]),
                        )
                        connection.exec_driver_sql(
                            "INSERT INTO reg_identity_decision "
                            "(decision_id, candidate_id, claim_id, profile_id, "
                            "account_id, decision_state, evidence_class, "
                            "reason_code, evidence_set_digest, "
                            "source_contract_version, owner_principal_id, "
                            "owner_confirmed_at, valid_from, invalidated_at, "
                            "record_version, registry_revision) VALUES "
                            "(?, NULL, ?, NULL, ?, 'owner_confirmed', "
                            "'owner_confirmed', "
                            "'provider_identity_owner_confirmed', ?, "
                            "'registry.v1', ?, ?, ?, NULL, 1, ?)",
                            (
                                _identifier(),
                                existing_claim["claim_id"],
                                command.account_id.value,
                                command.expected_evidence_digest,
                                command.principal_id.value,
                                instant,
                                instant,
                                revision,
                            ),
                        )
                        _append_outbox(
                            connection,
                            subject_type="identity",
                            subject_id=existing_claim["claim_id"],
                            aggregate_version=claim_version,
                            revision=revision,
                            change_kind="owner_confirmed",
                            correlation_id=command.idempotency_key.value,
                            causation_id=command.evidence_reference.value,
                            instant=instant,
                        )
                        connection.exec_driver_sql(
                            "INSERT INTO reg_command_receipt "
                            "(receipt_id, principal_id, operation_key, "
                            "idempotency_key_digest, request_fingerprint, "
                            "outcome_subject_type, outcome_subject_id, "
                            "outcome_record_version, registry_revision, created_at, "
                            "expires_at) VALUES "
                            "(?, ?, ?, ?, ?, 'identity_claim', ?, ?, ?, ?, ?)",
                            (
                                _identifier(),
                                command.principal_id.value,
                                operation,
                                command_digest,
                                request_fingerprint,
                                existing_claim["claim_id"],
                                claim_version,
                                revision,
                                instant,
                                _utc_text(command.requested_at + timedelta(days=365)),
                            ),
                        )
                        result = _provider_identity_resolution(connection, query)
                        connection.commit()
                        return result
                    claim_id = _identifier()
                    decision_id = _identifier()
                    revision = _next_revision(connection, instant)
                    if activate_pending:
                        connection.exec_driver_sql(
                            "UPDATE reg_account SET lifecycle='active', "
                            "identity_state='owner_confirmed', updated_at=?, "
                            "record_version=record_version+1 WHERE account_id=?",
                            (instant, command.account_id.value),
                        )
                        _append_outbox(
                            connection,
                            subject_type="account",
                            subject_id=command.account_id.value,
                            aggregate_version=command.expected_account_record_version
                            + 1,
                            revision=revision,
                            change_kind="owner_confirmed",
                            correlation_id=command.idempotency_key.value,
                            causation_id=command.evidence_reference.value,
                            instant=instant,
                        )
                    _invalidate_other_provider_identity_claims(
                        connection,
                        provider_key=command.provider_key,
                        identity_scheme=command.identity_scheme,
                        identity_scope=command.identity_scope,
                        identity_scheme_version=command.identity_scheme_version,
                        account_id=command.account_id.value,
                        retained_claim_id=None,
                        revision=revision,
                        correlation_id=command.idempotency_key.value,
                        causation_id=command.evidence_reference.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_provider_identity_claim "
                        "(claim_id, provider_key, identity_scheme, identity_scope, "
                        "identity_scheme_version, subject_fingerprint, account_id, "
                        "evidence_class, decision_state, evidence_reference, "
                        "valid_from, invalidated_at, last_verified_at, "
                        "owner_principal_id, owner_confirmed_at, record_version) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, 'owner_confirmed', "
                        "'owner_confirmed', ?, ?, "
                        "NULL, ?, ?, ?, 1)",
                        (
                            claim_id,
                            command.provider_key,
                            command.identity_scheme,
                            command.identity_scope,
                            command.identity_scheme_version,
                            command.subject_fingerprint,
                            command.account_id.value,
                            command.evidence_reference.value,
                            instant,
                            instant,
                            command.principal_id.value,
                            instant,
                        ),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_identity_decision "
                        "(decision_id, candidate_id, claim_id, profile_id, account_id, "
                        "decision_state, evidence_class, reason_code, "
                        "evidence_set_digest, source_contract_version, "
                        "owner_principal_id, owner_confirmed_at, valid_from, "
                        "invalidated_at, record_version, registry_revision) "
                        "VALUES (?, NULL, ?, NULL, ?, 'owner_confirmed', "
                        "'owner_confirmed', 'provider_identity_owner_confirmed', ?, "
                        "'registry.v1', ?, ?, ?, NULL, 1, ?)",
                        (
                            decision_id,
                            claim_id,
                            command.account_id.value,
                            command.expected_evidence_digest,
                            command.principal_id.value,
                            instant,
                            instant,
                            revision,
                        ),
                    )
                    _append_outbox(
                        connection,
                        subject_type="identity",
                        subject_id=claim_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="owner_confirmed",
                        correlation_id=command.idempotency_key.value,
                        causation_id=command.evidence_reference.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, "
                        "expires_at) VALUES "
                        "(?, ?, ?, ?, ?, 'identity_claim', ?, 1, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            request_fingerprint,
                            claim_id,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    result = _provider_identity_resolution(connection, query)
                    connection.commit()
                    return result
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1() from None

    @staticmethod
    def _cloud_target_by_account(
        connection: Connection, account_id: str
    ) -> CloudMonitoringTargetV1:
        row = (
            connection.exec_driver_sql(
                "SELECT * FROM reg_cloud_monitoring_target WHERE account_id=?",
                (account_id,),
            )
            .mappings()
            .one()
        )
        binding_account = OpaqueIdV1(row["account_id"])
        return CloudMonitoringTargetV1(
            profile_id=OpaqueIdV1(row["profile_id"]),
            resource_id=OpaqueIdV1(row["resource_id"]),
            account_id=binding_account,
            access_target_id=OpaqueIdV1(row["access_target_id"]),
            binding=ActiveCredentialBindingRefV1(
                account_id=binding_account,
                binding_id=OpaqueIdV1(row["binding_id"]),
                generation=int(row["binding_generation"]),
            ),
            lifecycle=row["lifecycle"],
            identity_state=row["identity_state"],
            owner_principal_id=OpaqueIdV1(row["owner_principal_id"]),
            owner_asserted_at=_utc_value(row["owner_asserted_at"]),  # type: ignore[arg-type]
            record_version=int(row["record_version"]),
        )

    def _assert_credential_account_ownership_in_transaction(
        self,
        connection: Connection,
        command: AssertCredentialAccountOwnershipCommandV1,
    ) -> tuple[AccountViewV1, CloudMonitoringTargetV1]:
        """Apply/replay one M02 assertion inside an integration transaction."""
        if not connection.in_transaction():
            raise RegistryCommandConflictV1("registry_transaction_required")
        operation = "assert_credential_account_ownership"
        command_digest = _digest(command.command_id.value)
        request_fingerprint = _fingerprint(
            {
                "access_target_id": command.access_target_id.value,
                "account_id": command.account_id.value,
                "binding_generation": command.binding.generation,
                "binding_id": command.binding.binding_id.value,
                "expected_account_record_version": (
                    command.expected_account_record_version
                ),
                "operation": operation,
            }
        )
        instant = _utc_text(command.requested_at)
        receipt = (
            connection.exec_driver_sql(
                "SELECT request_fingerprint,outcome_subject_id "
                "FROM reg_command_receipt WHERE principal_id=? "
                "AND operation_key=? AND idempotency_key_digest=?",
                (
                    command.principal_id.value,
                    operation,
                    command_digest,
                ),
            )
            .mappings()
            .one_or_none()
        )
        if receipt is not None:
            if receipt["request_fingerprint"] != request_fingerprint:
                raise RegistryCommandConflictV1("registry_idempotency_conflict")
            return (
                self._account_by_id(connection, receipt["outcome_subject_id"]),
                self._cloud_target_by_account(
                    connection, receipt["outcome_subject_id"]
                ),
            )
        account_row = (
            connection.exec_driver_sql(
                "SELECT * FROM reg_account WHERE account_id=?",
                (command.account_id.value,),
            )
            .mappings()
            .one_or_none()
        )
        if account_row is None:
            raise RegistryCommandConflictV1("registry_subject_not_found")
        access_target = ensure_access_target_in_transaction(
            connection, command.access_target_id
        )
        try:
            ensure_current_binding_in_transaction(connection, command.binding)
            lifecycle, identity, preference, version = decide_cloud_owner_assertion(
                account_provider=account_row["provider_key"],
                account_lifecycle=account_row["lifecycle"],
                account_identity_state=account_row["identity_state"],
                account_monitoring_preference=account_row["monitoring_preference"],
                account_record_version=int(account_row["record_version"]),
                expected_account_record_version=(
                    command.expected_account_record_version
                ),
                target_provider=access_target.provider_key,
                target_lifecycle=access_target.lifecycle,
                binding_is_current=True,
            )
        except ValueError as error:
            raise RegistryCommandConflictV1(str(error)) from None
        updated = connection.exec_driver_sql(
            "UPDATE reg_account SET lifecycle=?,identity_state=?,"
            "monitoring_preference=?,record_version=?,updated_at=? "
            "WHERE account_id=? AND record_version=? AND lifecycle='pending' "
            "AND identity_state='unresolved'",
            (
                lifecycle,
                identity,
                preference,
                version,
                instant,
                command.account_id.value,
                command.expected_account_record_version,
            ),
        )
        if updated.rowcount != 1:
            raise RegistryCommandConflictV1("registry_account_version_conflict")
        profile_id = _identifier()
        resource_id = _identifier()
        connection.exec_driver_sql(
            "INSERT INTO reg_cloud_monitoring_target "
            "(profile_id,resource_id,account_id,access_target_id,"
            "binding_id,binding_generation,lifecycle,identity_state,"
            "owner_principal_id,owner_asserted_at,record_version,"
            "created_at,updated_at) VALUES (?,?,?,?,?,?,'active',"
            "'owner_confirmed',?,?,1,?,?)",
            (
                profile_id,
                resource_id,
                command.account_id.value,
                command.access_target_id.value,
                command.binding.binding_id.value,
                command.binding.generation,
                command.principal_id.value,
                instant,
                instant,
                instant,
            ),
        )
        revision = _next_revision(connection, instant)
        _append_change(
            connection,
            subject_type="account",
            subject_id=command.account_id.value,
            aggregate_version=version,
            revision=revision,
            change_kind="owner_confirmed",
            actor_id=command.principal_id.value,
            correlation_id=command.command_id.value,
            command_digest=command_digest,
            instant=instant,
            previous_lifecycle=account_row["lifecycle"],
            new_lifecycle=lifecycle,
        )
        _append_outbox(
            connection,
            subject_type="account",
            subject_id=command.account_id.value,
            aggregate_version=version,
            revision=revision,
            change_kind="owner_confirmed",
            correlation_id=command.command_id.value,
            causation_id=command.command_id.value,
            instant=instant,
        )
        connection.exec_driver_sql(
            "INSERT INTO reg_command_receipt "
            "(receipt_id,principal_id,operation_key,"
            "idempotency_key_digest,request_fingerprint,"
            "outcome_subject_type,outcome_subject_id,"
            "outcome_record_version,registry_revision,created_at,"
            "expires_at) VALUES (?,?,?,?,?,'account',?,?,?,?,?)",
            (
                _identifier(),
                command.principal_id.value,
                operation,
                command_digest,
                request_fingerprint,
                command.account_id.value,
                version,
                revision,
                instant,
                _utc_text(command.requested_at + timedelta(days=365)),
            ),
        )
        return (
            self._account_by_id(connection, command.account_id.value),
            self._cloud_target_by_account(connection, command.account_id.value),
        )

    def _reassert_cloud_verification_graph_in_transaction(
        self,
        connection: Connection,
        command: AssertCredentialAccountOwnershipCommandV1,
        account: AccountViewV1,
        graph: CloudMonitoringTargetV1,
    ) -> tuple[AccountViewV1, CloudMonitoringTargetV1]:
        """Rebind an existing owner graph inside the atomic verification request."""
        if not connection.in_transaction():
            raise RegistryCommandConflictV1("registry_transaction_required")
        target = ensure_access_target_in_transaction(
            connection, command.access_target_id
        )
        ensure_current_binding_in_transaction(connection, command.binding)
        try:
            version = decide_cloud_binding_reassertion(
                account_provider=account.provider_key,
                account_lifecycle=account.lifecycle,
                account_identity_state=account.identity_state,
                account_monitoring_preference=account.monitoring_preference,
                account_record_version=account.record_version,
                expected_account_record_version=command.expected_account_record_version,
                target_provider=target.provider_key,
                target_kind=target.target_kind,
                target_authority=target.authority_id,
                target_lifecycle=target.lifecycle,
                graph_lifecycle=graph.lifecycle,
                graph_identity_state=graph.identity_state,
                binding_is_current=True,
            )
        except ValueError as error:
            raise RegistryCommandConflictV1(str(error)) from None
        instant = _utc_text(command.requested_at)
        updated = connection.exec_driver_sql(
            "UPDATE reg_account SET record_version=?,updated_at=? "
            "WHERE account_id=? AND record_version=? AND provider_key='ollama' "
            "AND lifecycle='active' AND identity_state='owner_confirmed' "
            "AND monitoring_preference='enabled'",
            (
                version,
                instant,
                command.account_id.value,
                command.expected_account_record_version,
            ),
        )
        if updated.rowcount != 1:
            raise RegistryCommandConflictV1("registry_account_version_conflict")
        refreshed = connection.exec_driver_sql(
            "UPDATE reg_cloud_monitoring_target SET access_target_id=?,binding_id=?,"
            "binding_generation=?,owner_principal_id=?,owner_asserted_at=?,"
            "record_version=record_version+1,updated_at=? "
            "WHERE account_id=? AND profile_id=? AND resource_id=? "
            "AND access_target_id=? AND binding_id=? AND binding_generation=? "
            "AND record_version=? AND lifecycle='active' AND identity_state='owner_confirmed'",
            (
                command.access_target_id.value,
                command.binding.binding_id.value,
                command.binding.generation,
                command.principal_id.value,
                instant,
                instant,
                command.account_id.value,
                graph.profile_id.value,
                graph.resource_id.value,
                graph.access_target_id.value,
                graph.binding.binding_id.value,
                graph.binding.generation,
                graph.record_version,
            ),
        )
        if refreshed.rowcount != 1:
            raise RegistryCommandConflictV1("registry_cloud_graph_invalid")
        revision = _next_revision(connection, instant)
        _append_change(
            connection,
            subject_type="account",
            subject_id=command.account_id.value,
            aggregate_version=version,
            revision=revision,
            change_kind="owner_confirmed",
            actor_id=command.principal_id.value,
            correlation_id=command.command_id.value,
            command_digest=_digest(command.command_id.value),
            instant=instant,
            previous_lifecycle=account.lifecycle,
            new_lifecycle=account.lifecycle,
        )
        _append_outbox(
            connection,
            subject_type="account",
            subject_id=command.account_id.value,
            aggregate_version=version,
            revision=revision,
            change_kind="owner_confirmed",
            correlation_id=command.command_id.value,
            causation_id=command.command_id.value,
            instant=instant,
        )
        return (
            self._account_by_id(connection, command.account_id.value),
            self._cloud_target_by_account(connection, command.account_id.value),
        )

    def _prepare_cloud_verification_graph_in_transaction(
        self,
        connection: Connection,
        command: AssertCredentialAccountOwnershipCommandV1,
    ) -> tuple[AccountViewV1, CloudMonitoringTargetV1, int]:
        """Read or create the exact owner graph for one atomic initiation."""
        if not connection.in_transaction():
            raise RegistryCommandConflictV1("registry_transaction_required")
        account_version = connection.exec_driver_sql(
            "SELECT record_version FROM reg_account WHERE account_id=?",
            (command.account_id.value,),
        ).scalar_one_or_none()
        graph_exists = (
            connection.exec_driver_sql(
                "SELECT 1 FROM reg_cloud_monitoring_target WHERE account_id=?",
                (command.account_id.value,),
            ).first()
            is not None
        )
        owner_assertion_required = (
            not graph_exists
            or account_version is None
            or int(account_version) != command.expected_account_record_version
        )
        if owner_assertion_required:
            account, graph = self._assert_credential_account_ownership_in_transaction(
                connection, command
            )
        else:
            account = self._account_by_id(connection, command.account_id.value)
            graph = self._cloud_target_by_account(connection, command.account_id.value)
            if (
                graph.binding != command.binding
                or graph.access_target_id != command.access_target_id
            ):
                account, graph = self._reassert_cloud_verification_graph_in_transaction(
                    connection, command, account, graph
                )
                owner_assertion_required = True
        return (
            account,
            graph,
            cloud_verification_enqueue_account_version(
                command_expected_version=command.expected_account_record_version,
                owner_assertion_required=owner_assertion_required,
            ),
        )

    def assert_credential_account_ownership(
        self, command: AssertCredentialAccountOwnershipCommandV1
    ) -> tuple[AccountViewV1, CloudMonitoringTargetV1]:
        """Record one signed-in owner assertion without a provider identity claim."""
        try:
            with account_credential_lock(self._database_ref, command.account_id):
                with open_sqlite_database(
                    self._database_ref, "runtime_read_write"
                ) as handle:
                    with handle.connect() as connection:
                        connection.exec_driver_sql("BEGIN IMMEDIATE")
                        result = (
                            self._assert_credential_account_ownership_in_transaction(
                                connection, command
                            )
                        )
                        connection.commit()
                        return result
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1() from None

    def confirm_identity(
        self, command: ConfirmIdentityAssociationCommandV1
    ) -> AccountViewV1:
        operation = "confirm_identity_association"
        command_digest = _digest(command.command_id.value)
        request_fingerprint = _fingerprint(
            {
                "candidate_id": command.candidate_id.value,
                "evidence_set_digest": command.evidence_set_digest,
                "expected_candidate_record_version": (
                    command.expected_candidate_record_version
                ),
                "friendly_name": command.friendly_name,
                "organization_id": command.organization_id.value
                if command.organization_id
                else None,
                "operation": operation,
            }
        )
        instant = _utc_text(command.requested_at)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint, outcome_subject_id "
                            "FROM reg_command_receipt WHERE principal_id=? "
                            "AND operation_key=? AND idempotency_key_digest=?",
                            (command.principal_id.value, operation, command_digest),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if receipt is not None:
                        if receipt["request_fingerprint"] != request_fingerprint:
                            connection.rollback()
                            raise RegistryCommandConflictV1(
                                "registry_idempotency_conflict"
                            )
                        result = self._account_by_id(
                            connection, receipt["outcome_subject_id"]
                        )
                        connection.rollback()
                        return result
                    candidate = (
                        connection.exec_driver_sql(
                            "SELECT * FROM reg_discovery_candidate "
                            "WHERE candidate_id=?",
                            (command.candidate_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if candidate is None:
                        connection.rollback()
                        raise RegistryCommandConflictV1("registry_subject_not_found")
                    current_evidence_set_digest = _candidate_evidence_set_digest(
                        candidate
                    )
                    try:
                        ensure_candidate_confirmation_is_current(
                            expected_record_version=(
                                command.expected_candidate_record_version
                            ),
                            current_record_version=candidate["record_version"],
                            expected_evidence_set_digest=command.evidence_set_digest,
                            current_evidence_set_digest=current_evidence_set_digest,
                        )
                    except RegistryPolicyErrorV1 as error:
                        connection.rollback()
                        raise RegistryCommandConflictV1(str(error)) from None
                    if candidate["association_state"] not in {
                        "owner_confirmation_required",
                        "owner_confirmed",
                    }:
                        connection.rollback()
                        raise RegistryCommandConflictV1("registry_identity_conflict")
                    if candidate["association_state"] == "owner_confirmed":
                        associated_account_id = candidate["associated_subject_id"]
                        if associated_account_id is None:
                            connection.rollback()
                            raise RegistryCommandConflictV1(
                                "registry_identity_conflict"
                            )
                        result = self._account_by_id(connection, associated_account_id)
                        if (
                            result.provider_key != candidate["provider_key"]
                            or result.friendly_name != command.friendly_name
                            or result.organization_id != command.organization_id
                        ):
                            connection.rollback()
                            raise RegistryCommandConflictV1(
                                "registry_identity_conflict"
                            )
                        revision = _current_revision(connection)
                        connection.exec_driver_sql(
                            "INSERT INTO reg_command_receipt "
                            "(receipt_id, principal_id, operation_key, "
                            "idempotency_key_digest, request_fingerprint, "
                            "outcome_subject_type, outcome_subject_id, "
                            "outcome_record_version, registry_revision, created_at, "
                            "expires_at) VALUES "
                            "(?, ?, ?, ?, ?, 'account', ?, ?, ?, ?, ?)",
                            (
                                _identifier(),
                                command.principal_id.value,
                                operation,
                                command_digest,
                                request_fingerprint,
                                result.account_id.value,
                                result.record_version,
                                revision,
                                instant,
                                _utc_text(command.requested_at + timedelta(days=365)),
                            ),
                        )
                        connection.commit()
                        return result
                    if command.organization_id is not None:
                        organization = connection.exec_driver_sql(
                            "SELECT lifecycle FROM reg_organization "
                            "WHERE organization_id=?",
                            (command.organization_id.value,),
                        ).scalar_one_or_none()
                        if organization != "active":
                            connection.rollback()
                            raise RegistryCommandConflictV1("registry_subject_archived")
                    duplicate = connection.exec_driver_sql(
                        "SELECT 1 FROM reg_account WHERE normalized_name=? "
                        "AND lifecycle <> 'archived' LIMIT 1",
                        (command.friendly_name.casefold(),),
                    ).scalar_one_or_none()
                    if duplicate is not None:
                        connection.rollback()
                        raise RegistryCommandConflictV1("registry_alias_conflict")
                    account_id = _identifier()
                    claim_id = _identifier()
                    decision_id = _identifier()
                    revision = _next_revision(connection, instant)
                    connection.exec_driver_sql(
                        "INSERT INTO reg_account "
                        "(account_id, provider_key, friendly_name, normalized_name, "
                        "organization_id, lifecycle, identity_state, "
                        "monitoring_preference, "
                        "record_version, created_at, updated_at, archived_at, "
                        "creation_command_digest) "
                        "VALUES (?, ?, ?, ?, ?, 'active', 'owner_confirmed', "
                        "'disabled', "
                        "1, ?, ?, NULL, ?)",
                        (
                            account_id,
                            candidate["provider_key"],
                            command.friendly_name,
                            command.friendly_name.casefold(),
                            command.organization_id.value
                            if command.organization_id
                            else None,
                            instant,
                            instant,
                            command_digest,
                        ),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_provider_identity_claim "
                        "(claim_id, provider_key, identity_scheme, identity_scope, "
                        "identity_scheme_version, subject_fingerprint, account_id, "
                        "evidence_class, decision_state, evidence_reference, "
                        "valid_from, "
                        "invalidated_at, last_verified_at, owner_principal_id, "
                        "owner_confirmed_at, record_version) "
                        "VALUES (?, ?, 'm03_candidate_ref_sha256', "
                        "'provider_account', 1, ?, ?, ?, "
                        "'owner_confirmed', ?, ?, NULL, ?, ?, ?, 1)",
                        (
                            claim_id,
                            candidate["provider_key"],
                            candidate["source_identity_fingerprint"],
                            account_id,
                            candidate["evidence_class"],
                            candidate["evidence_reference"],
                            instant,
                            instant,
                            command.principal_id.value,
                            instant,
                        ),
                    )
                    connection.exec_driver_sql(
                        "UPDATE reg_discovery_candidate SET "
                        "association_state='owner_confirmed', associated_subject_id=?, "
                        "reason_code='owner_confirmed', reviewed_at=?, "
                        "record_version=record_version+1 WHERE candidate_id=?",
                        (account_id, instant, command.candidate_id.value),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_identity_decision "
                        "(decision_id, candidate_id, claim_id, profile_id, account_id, "
                        "decision_state, evidence_class, reason_code, "
                        "evidence_set_digest, source_contract_version, "
                        "owner_principal_id, owner_confirmed_at, valid_from, "
                        "invalidated_at, record_version, registry_revision) "
                        "VALUES (?, ?, ?, NULL, ?, 'owner_confirmed', ?, "
                        "'owner_confirmed', ?, 'registry.v1', ?, ?, ?, NULL, 1, ?)",
                        (
                            decision_id,
                            command.candidate_id.value,
                            claim_id,
                            account_id,
                            candidate["evidence_class"],
                            current_evidence_set_digest,
                            command.principal_id.value,
                            instant,
                            instant,
                            revision,
                        ),
                    )
                    _append_change(
                        connection,
                        subject_type="account",
                        subject_id=account_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="registered",
                        actor_id=command.principal_id.value,
                        correlation_id=command.command_id.value,
                        command_digest=command_digest,
                        instant=instant,
                        new_name=command.friendly_name,
                        new_organization_id=(
                            command.organization_id.value
                            if command.organization_id
                            else None
                        ),
                        new_lifecycle="active",
                    )
                    _append_outbox(
                        connection,
                        subject_type="identity",
                        subject_id=account_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="owner_confirmed",
                        correlation_id=command.command_id.value,
                        causation_id=command.candidate_id.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, "
                        "expires_at) "
                        "VALUES (?, ?, ?, ?, ?, 'account', ?, 1, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            request_fingerprint,
                            account_id,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    result = self._account_by_id(connection, account_id)
                    connection.commit()
                    return result
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    @staticmethod
    def _account_by_id(connection: Connection, account_id: str) -> AccountViewV1:
        row = (
            connection.exec_driver_sql(
                "SELECT a.*, s.registry_revision FROM reg_account a "
                "CROSS JOIN reg_registry_state s WHERE s.singleton_key=1 "
                "AND a.account_id=?",
                (account_id,),
            )
            .mappings()
            .one()
        )
        return _account(row)

    def get_account(self, account_id: OpaqueIdV1) -> AccountViewV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT a.*, s.registry_revision FROM reg_account a "
                            "CROSS JOIN reg_registry_state s WHERE s.singleton_key=1 "
                            "AND a.account_id=?",
                            (account_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return _account(row) if row is not None else None
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def list_accounts(
        self,
        provider_key: str | None = None,
        page_size: int = 100,
        after_key: str | None = None,
    ) -> tuple[AccountViewV1, ...]:
        query = (
            "SELECT a.*, s.registry_revision FROM reg_account a "
            "CROSS JOIN reg_registry_state s WHERE s.singleton_key=1"
        )
        parameters: tuple[object, ...] = ()
        if provider_key is not None:
            query += " AND a.provider_key=?"
            parameters = (provider_key,)
        if type(page_size) is not int or not 1 <= page_size <= 201:
            raise RegistryRepositoryErrorV1("registry_query_invalid")
        if after_key is not None:
            query += " AND (a.provider_key, a.normalized_name, a.account_id) > ("
            query += "(SELECT provider_key FROM reg_account WHERE account_id=?), "
            query += "(SELECT normalized_name FROM reg_account WHERE account_id=?), ?)"
            parameters = (*parameters, after_key, after_key, after_key)
        query += " ORDER BY a.provider_key, a.normalized_name, a.account_id LIMIT ?"
        parameters = (*parameters, page_size)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(query, parameters).mappings().all()
                    )
            return tuple(_account(row) for row in rows)
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    @staticmethod
    def _monitoring_graph_by_profile(
        connection: Connection,
        *,
        profile_id: str,
        enrollment_evidence_reference: str,
    ) -> tuple[MonitoringProfileViewV1, AccountResourceViewV1]:
        revision = _current_revision(connection)
        profile_row = (
            connection.exec_driver_sql(
                "SELECT * FROM reg_monitoring_profile WHERE profile_id=?",
                (profile_id,),
            )
            .mappings()
            .one()
        )
        resource_id = connection.exec_driver_sql(
            "SELECT resource_id FROM reg_profile_resource_link "
            "WHERE profile_id=? AND evidence_reference=? "
            "AND invalidated_at IS NULL",
            (profile_id, enrollment_evidence_reference),
        ).scalar_one()
        resource_row = (
            connection.exec_driver_sql(
                "SELECT * FROM reg_account_resource WHERE resource_id=?",
                (resource_id,),
            )
            .mappings()
            .one()
        )
        profile_resource_ids = tuple(
            OpaqueIdV1(value)
            for value in connection.exec_driver_sql(
                "SELECT resource_id FROM reg_profile_resource_link "
                "WHERE profile_id=? AND invalidated_at IS NULL "
                "ORDER BY resource_id",
                (profile_id,),
            ).scalars()
        )
        resource_profile_ids = tuple(
            OpaqueIdV1(value)
            for value in connection.exec_driver_sql(
                "SELECT profile_id FROM reg_profile_resource_link "
                "WHERE resource_id=? AND invalidated_at IS NULL "
                "ORDER BY profile_id",
                (resource_id,),
            ).scalars()
        )
        profile = MonitoringProfileViewV1(
            profile_id=OpaqueIdV1(profile_row["profile_id"]),
            account_id=OpaqueIdV1(profile_row["account_id"]),
            provider_installation_id=OpaqueIdV1(
                profile_row["provider_installation_id"]
            ),
            purpose=profile_row["purpose"],
            lifecycle=profile_row["lifecycle"],
            management_state=profile_row["management_state"],
            compatibility_state=profile_row["compatibility_state"],
            is_protected_default=bool(profile_row["protected_default_profile"]),
            locator_state="configured",
            identity_state=profile_row["identity_verification_state"],
            last_verified_at=_utc_value(profile_row["last_verified_at"]),
            resource_ids=profile_resource_ids,
            record_version=profile_row["record_version"],
            registry_revision=revision,
        )
        parent_resource_id = resource_row["parent_resource_id"]
        resource = AccountResourceViewV1(
            resource_id=OpaqueIdV1(resource_row["resource_id"]),
            account_id=OpaqueIdV1(resource_row["account_id"]),
            kind=resource_row["kind"],
            parent_resource_id=(
                OpaqueIdV1(parent_resource_id)
                if parent_resource_id is not None
                else None
            ),
            label=MaskedRegistryFieldV1(
                "withheld", None, "resource_label_privacy_minimized"
            ),
            lifecycle=resource_row["lifecycle"],
            linked_profile_ids=resource_profile_ids,
            record_version=resource_row["record_version"],
            registry_revision=revision,
            created_at=_utc_value(resource_row["created_at"]),  # type: ignore[arg-type]
            updated_at=_utc_value(resource_row["updated_at"]),  # type: ignore[arg-type]
        )
        return profile, resource

    def enroll_monitoring_graph(
        self, command: EnrollMonitoringGraphCommandV1
    ) -> tuple[MonitoringProfileViewV1, AccountResourceViewV1]:
        operation = "enroll_monitoring_graph"
        command_digest = _digest(command.command_id.value)
        enrollment_evidence_reference = f"owner_enrollment:{command_digest}"
        request_fingerprint = _fingerprint(
            {
                "account_id": command.account_id.value,
                "is_protected_default": command.is_protected_default,
                "locator_fingerprint": command.locator_fingerprint,
                "management_state": command.management_state,
                "compatibility_state": command.compatibility_state,
                "operation": operation,
                "parent_resource_id": (
                    command.parent_resource_id.value
                    if command.parent_resource_id is not None
                    else None
                ),
                "provider_installation_id": command.provider_installation_id.value,
                "purpose": command.purpose,
                "resource_kind": command.resource_kind,
            }
        )
        instant = _utc_text(command.requested_at)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    receipt = (
                        connection.exec_driver_sql(
                            "SELECT request_fingerprint, outcome_subject_id "
                            "FROM reg_command_receipt WHERE principal_id=? "
                            "AND operation_key=? AND idempotency_key_digest=?",
                            (
                                command.principal_id.value,
                                operation,
                                command_digest,
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    try:
                        replay_decision = decide_command_replay(
                            receipt["request_fingerprint"]
                            if receipt is not None
                            else None,
                            request_fingerprint,
                        )
                    except RegistryPolicyErrorV1 as error:
                        connection.rollback()
                        raise RegistryCommandConflictV1(str(error)) from None
                    if replay_decision == "replay":
                        if receipt is None:
                            raise RegistryRepositoryErrorV1()
                        result = self._monitoring_graph_by_profile(
                            connection,
                            profile_id=receipt["outcome_subject_id"],
                            enrollment_evidence_reference=(
                                enrollment_evidence_reference
                            ),
                        )
                        connection.rollback()
                        return result
                    account_provider = connection.exec_driver_sql(
                        "SELECT provider_key FROM reg_account WHERE account_id=? "
                        "AND lifecycle='active'",
                        (command.account_id.value,),
                    ).scalar_one_or_none()
                    installation_provider = connection.exec_driver_sql(
                        "SELECT provider_key FROM reg_provider_installation "
                        "WHERE provider_installation_id=?",
                        (command.provider_installation_id.value,),
                    ).scalar_one_or_none()
                    if (
                        account_provider is None
                        or account_provider != installation_provider
                    ):
                        connection.rollback()
                        raise RegistryCommandConflictV1("registry_invalid_relationship")
                    if command.parent_resource_id is not None:
                        parent_account = connection.exec_driver_sql(
                            "SELECT account_id FROM reg_account_resource "
                            "WHERE resource_id=?",
                            (command.parent_resource_id.value,),
                        ).scalar_one_or_none()
                        if parent_account != command.account_id.value:
                            connection.rollback()
                            raise RegistryCommandConflictV1(
                                "registry_invalid_relationship"
                            )
                    profile_id = _identifier()
                    resource_id = _identifier()
                    revision = _next_revision(connection, instant)
                    connection.exec_driver_sql(
                        "INSERT INTO reg_monitoring_profile "
                        "(profile_id, account_id, provider_installation_id, "
                        "purpose, lifecycle, "
                        "management_state, compatibility_state, "
                        "private_locator_ref, locator_scheme, locator_scheme_version, "
                        "locator_fingerprint, protected_default_profile, "
                        "identity_verification_state, expected_identity_claim_id, "
                        "last_verification_reference, last_verified_at, "
                        "record_version, "
                        "created_at, updated_at, archived_at) "
                        "VALUES (?, ?, ?, ?, 'active', ?, ?, ?, 'adapter_opaque_v1', "
                        "1, ?, ?, 'owner_confirmed', NULL, "
                        "'owner_enrollment', ?, 1, ?, ?, NULL)",
                        (
                            profile_id,
                            command.account_id.value,
                            command.provider_installation_id.value,
                            command.purpose,
                            command.management_state,
                            command.compatibility_state,
                            command.profile_locator_ref.reveal_for_persistence(),
                            command.locator_fingerprint,
                            int(command.is_protected_default),
                            instant,
                            instant,
                            instant,
                        ),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_account_resource "
                        "(resource_id, account_id, kind, provider_specific_kind, "
                        "provider_specific_kind_version, parent_resource_id, "
                        "safe_label_state, safe_masked_label, "
                        "provider_resource_fingerprint, identity_scheme, "
                        "identity_scheme_version, lifecycle, first_verified_at, "
                        "last_verified_at, "
                        "record_version, created_at, updated_at) "
                        "VALUES (?, ?, ?, NULL, NULL, ?, 'withheld', NULL, "
                        "NULL, NULL, NULL, "
                        "'active', ?, ?, 1, ?, ?)",
                        (
                            resource_id,
                            command.account_id.value,
                            command.resource_kind,
                            command.parent_resource_id.value
                            if command.parent_resource_id
                            else None,
                            instant,
                            instant,
                            instant,
                            instant,
                        ),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_profile_resource_link "
                        "(account_id, profile_id, resource_id, evidence_class, "
                        "evidence_reference, "
                        "owner_confirmed, owner_confirmed_at, valid_from, "
                        "invalidated_at, "
                        "record_version) VALUES (?, ?, ?, 'owner_confirmed', "
                        "?, 1, ?, ?, NULL, 1)",
                        (
                            command.account_id.value,
                            profile_id,
                            resource_id,
                            enrollment_evidence_reference,
                            instant,
                            instant,
                        ),
                    )
                    _append_change(
                        connection,
                        subject_type="profile",
                        subject_id=profile_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="enrolled",
                        actor_id=command.principal_id.value,
                        correlation_id=command.command_id.value,
                        command_digest=command_digest,
                        instant=instant,
                        new_lifecycle="active",
                    )
                    _append_outbox(
                        connection,
                        subject_type="profile",
                        subject_id=profile_id,
                        aggregate_version=1,
                        revision=revision,
                        change_kind="enrolled",
                        correlation_id=command.command_id.value,
                        causation_id=command.command_id.value,
                        instant=instant,
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO reg_command_receipt "
                        "(receipt_id, principal_id, operation_key, "
                        "idempotency_key_digest, request_fingerprint, "
                        "outcome_subject_type, outcome_subject_id, "
                        "outcome_record_version, registry_revision, created_at, "
                        "expires_at) VALUES (?, ?, ?, ?, ?, "
                        "'monitoring_profile', ?, 1, ?, ?, ?)",
                        (
                            _identifier(),
                            command.principal_id.value,
                            operation,
                            command_digest,
                            request_fingerprint,
                            profile_id,
                            revision,
                            instant,
                            _utc_text(command.requested_at + timedelta(days=365)),
                        ),
                    )
                    result = self._monitoring_graph_by_profile(
                        connection,
                        profile_id=profile_id,
                        enrollment_evidence_reference=enrollment_evidence_reference,
                    )
                    connection.commit()
                    return result
        except RegistryCommandConflictV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def list_monitoring_profiles(
        self, account_id: OpaqueIdV1
    ) -> tuple[MonitoringProfileViewV1, ...]:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    revision = _current_revision(connection)
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT * FROM reg_monitoring_profile WHERE account_id=? "
                            "ORDER BY profile_id LIMIT 100",
                            (account_id.value,),
                        )
                        .mappings()
                        .all()
                    )
                    links: dict[str, list[OpaqueIdV1]] = {
                        row["profile_id"]: [] for row in rows
                    }
                    for link in connection.exec_driver_sql(
                        "SELECT profile_id, resource_id FROM reg_profile_resource_link "
                        "WHERE invalidated_at IS NULL ORDER BY profile_id, resource_id"
                    ).mappings():
                        if link["profile_id"] in links:
                            links[link["profile_id"]].append(
                                OpaqueIdV1(link["resource_id"])
                            )
            return tuple(
                MonitoringProfileViewV1(
                    profile_id=OpaqueIdV1(row["profile_id"]),
                    account_id=OpaqueIdV1(row["account_id"]),
                    provider_installation_id=OpaqueIdV1(
                        row["provider_installation_id"]
                    ),
                    purpose=row["purpose"],
                    lifecycle=row["lifecycle"],
                    management_state=row["management_state"],
                    compatibility_state=row["compatibility_state"],
                    is_protected_default=bool(row["protected_default_profile"]),
                    locator_state="configured",
                    identity_state=row["identity_verification_state"],
                    last_verified_at=_utc_value(row["last_verified_at"]),
                    resource_ids=tuple(links[row["profile_id"]]),
                    record_version=row["record_version"],
                    registry_revision=revision,
                )
                for row in rows
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def list_account_resources(
        self, account_id: OpaqueIdV1
    ) -> tuple[AccountResourceViewV1, ...]:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    revision = _current_revision(connection)
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT * FROM reg_account_resource WHERE account_id=? "
                            "ORDER BY resource_id LIMIT 100",
                            (account_id.value,),
                        )
                        .mappings()
                        .all()
                    )
                    links: dict[str, list[OpaqueIdV1]] = {
                        row["resource_id"]: [] for row in rows
                    }
                    for link in connection.exec_driver_sql(
                        "SELECT profile_id, resource_id FROM reg_profile_resource_link "
                        "WHERE invalidated_at IS NULL ORDER BY resource_id, profile_id"
                    ).mappings():
                        if link["resource_id"] in links:
                            links[link["resource_id"]].append(
                                OpaqueIdV1(link["profile_id"])
                            )
            return tuple(
                AccountResourceViewV1(
                    resource_id=OpaqueIdV1(row["resource_id"]),
                    account_id=OpaqueIdV1(row["account_id"]),
                    kind=row["kind"],
                    parent_resource_id=(
                        OpaqueIdV1(row["parent_resource_id"])
                        if row["parent_resource_id"] is not None
                        else None
                    ),
                    label=MaskedRegistryFieldV1(
                        "withheld", None, "resource_label_privacy_minimized"
                    ),
                    lifecycle=row["lifecycle"],
                    linked_profile_ids=tuple(links[row["resource_id"]]),
                    record_version=row["record_version"],
                    registry_revision=revision,
                    created_at=_utc_value(row["created_at"]),  # type: ignore[arg-type]
                    updated_at=_utc_value(row["updated_at"]),  # type: ignore[arg-type]
                )
                for row in rows
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def get_registry_scope_snapshot(
        self, scope_kind: RegistryScopeKindV1, scope_id: OpaqueIdV1 | None
    ) -> RegistryScopeSnapshotV1:
        if (scope_kind == "global") != (scope_id is None):
            raise RegistryRepositoryErrorV1("registry_scope_invalid")
        scope_value = scope_id.value if scope_id is not None else None
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    revision = _current_revision(connection)
                    account_rows = (
                        connection.exec_driver_sql(
                            "SELECT account_id, organization_id, provider_key "
                            "FROM reg_account WHERE lifecycle <> 'archived' "
                            "ORDER BY provider_key, normalized_name, account_id"
                        )
                        .mappings()
                        .all()
                    )
                    if scope_kind == "organization":
                        account_rows = [
                            row
                            for row in account_rows
                            if row["organization_id"] == scope_value
                        ]
                    elif scope_kind == "provider":
                        account_rows = [
                            row
                            for row in account_rows
                            if row["provider_key"] == scope_value
                        ]
                    elif scope_kind == "account":
                        account_rows = [
                            row
                            for row in account_rows
                            if row["account_id"] == scope_value
                        ]
                    account_ids = tuple(
                        sorted(
                            (OpaqueIdV1(row["account_id"]) for row in account_rows),
                            key=lambda item: item.value,
                        )
                    )
                    account_values = {item.value for item in account_ids}
                    resource_ids = tuple(
                        sorted(
                            (
                                OpaqueIdV1(row["resource_id"])
                                for row in connection.exec_driver_sql(
                                    "SELECT resource_id, account_id "
                                    "FROM reg_account_resource "
                                    "WHERE lifecycle='active' ORDER BY resource_id"
                                ).mappings()
                                if row["account_id"] in account_values
                            ),
                            key=lambda item: item.value,
                        )
                    )
                    if scope_kind == "global":
                        organization_values = tuple(
                            connection.exec_driver_sql(
                                "SELECT organization_id FROM reg_organization "
                                "WHERE lifecycle='active' "
                                "ORDER BY display_order, organization_id"
                            ).scalars()
                        )
                    elif scope_kind == "organization":
                        organization_values = (
                            (scope_value,)
                            if connection.exec_driver_sql(
                                "SELECT 1 FROM reg_organization "
                                "WHERE organization_id=? AND lifecycle='active'",
                                (scope_value,),
                            ).scalar_one_or_none()
                            is not None
                            else ()
                        )
                    else:
                        active_organization_values = set(
                            connection.exec_driver_sql(
                                "SELECT organization_id FROM reg_organization "
                                "WHERE lifecycle='active'"
                            ).scalars()
                        )
                        organization_values = tuple(
                            sorted(
                                {
                                    row["organization_id"]
                                    for row in account_rows
                                    if row["organization_id"]
                                    in active_organization_values
                                }
                            )
                        )
                    organization_ids = tuple(
                        OpaqueIdV1(value) for value in organization_values
                    )
            return RegistryScopeSnapshotV1(
                scope_kind=scope_kind,
                scope_id=scope_id,
                organization_ids=organization_ids,
                account_ids=account_ids,
                resource_ids=resource_ids,
                completeness_state="complete",
                registry_revision=revision,
            )
        except RegistryRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def get_registry_capacity_scope_v2(
        self, scope_kind: RegistryScopeKindV1, scope_id: OpaqueIdV1 | None
    ) -> RegistryScopeSnapshotV2:
        """Read local and cloud resource membership in one SQLite snapshot."""
        if (scope_kind == "global") != (scope_id is None):
            raise RegistryRepositoryErrorV1("registry_scope_invalid")
        scope_value = scope_id.value if scope_id is not None else None
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    revision = _current_revision(connection)
                    account_filter = ""
                    account_parameters: tuple[str, ...] = ()
                    if scope_kind == "organization":
                        account_filter = " AND organization_id=?"
                        account_parameters = (scope_value or "",)
                    elif scope_kind == "provider":
                        account_filter = " AND provider_key=?"
                        account_parameters = (scope_value or "",)
                    elif scope_kind == "account":
                        account_filter = " AND account_id=?"
                        account_parameters = (scope_value or "",)
                    account_rows = (
                        connection.exec_driver_sql(
                            "SELECT account_id,organization_id,provider_key "
                            "FROM reg_account WHERE lifecycle<>'archived' "
                            + account_filter
                            + " ORDER BY provider_key,normalized_name,account_id "
                            "LIMIT 201",
                            account_parameters,
                        )
                        .mappings()
                        .all()
                    )
                    if len(account_rows) > 200:
                        raise RegistryRepositoryErrorV1(
                            "registry_scope_membership_limit_exceeded"
                        )
                    account_ids = tuple(
                        sorted(
                            (
                                OpaqueIdV1(str(row["account_id"]))
                                for row in account_rows
                            ),
                            key=lambda item: item.value,
                        )
                    )
                    account_values = {item.value for item in account_ids}
                    ordered_account_values = tuple(sorted(account_values))
                    account_providers = {
                        str(row["account_id"]): str(row["provider_key"])
                        for row in account_rows
                    }
                    placeholders = ",".join("?" for _ in ordered_account_values)
                    all_local_rows = (
                        connection.exec_driver_sql(
                            "SELECT resource_id,account_id FROM reg_account_resource "
                            "WHERE lifecycle='active' AND account_id IN ("
                            + placeholders
                            + ") ORDER BY resource_id LIMIT 2001",
                            ordered_account_values,
                        )
                        .mappings()
                        .all()
                        if ordered_account_values
                        else []
                    )
                    if len(all_local_rows) > 2000:
                        raise RegistryRepositoryErrorV1(
                            "registry_scope_membership_limit_exceeded"
                        )
                    local_resource_ids = tuple(
                        sorted(
                            (
                                OpaqueIdV1(str(row["resource_id"]))
                                for row in all_local_rows
                            ),
                            key=lambda item: item.value,
                        )
                    )
                    local_target_rows = (
                        connection.exec_driver_sql(
                            "SELECT DISTINCT r.resource_id,r.account_id,a.provider_key,"
                            "p.provider_installation_id FROM reg_account_resource r "
                            "JOIN reg_account a ON a.account_id=r.account_id "
                            "JOIN reg_profile_resource_link l ON l.account_id=r.account_id "
                            "AND l.resource_id=r.resource_id "
                            "AND l.invalidated_at IS NULL "
                            "JOIN reg_monitoring_profile p ON p.profile_id=l.profile_id "
                            "AND p.account_id=r.account_id "
                            "JOIN reg_provider_installation i ON "
                            "i.provider_installation_id=p.provider_installation_id "
                            "AND i.provider_key=a.provider_key "
                            "WHERE r.lifecycle='active' AND p.lifecycle='active' "
                            "AND r.account_id IN (" + placeholders + ") "
                            "ORDER BY r.resource_id,p.provider_installation_id LIMIT 4001",
                            ordered_account_values,
                        )
                        .mappings()
                        .all()
                        if ordered_account_values
                        else []
                    )
                    if len(local_target_rows) > 4000:
                        raise RegistryRepositoryErrorV1(
                            "registry_scope_membership_limit_exceeded"
                        )
                    local_targets = tuple(
                        RegistryLocalResourceTargetV2(
                            OpaqueIdV1(str(row["resource_id"])),
                            OpaqueIdV1(str(row["account_id"])),
                            str(row["provider_key"]),
                            OpaqueIdV1(str(row["provider_installation_id"])),
                            revision,
                        )
                        for row in local_target_rows
                    )
                    cloud_rows = (
                        connection.exec_driver_sql(
                            "SELECT c.resource_id,c.account_id,t.provider_key,"
                            "t.access_target_id FROM reg_cloud_monitoring_target c "
                            "JOIN reg_provider_access_target t "
                            "ON t.access_target_id=c.access_target_id "
                            "WHERE c.lifecycle='active' AND t.lifecycle='active' "
                            "AND c.account_id IN ("
                            + placeholders
                            + ") ORDER BY c.resource_id LIMIT 2001",
                            ordered_account_values,
                        )
                        .mappings()
                        .all()
                        if ordered_account_values
                        else []
                    )
                    if len(cloud_rows) > 2000:
                        raise RegistryRepositoryErrorV1(
                            "registry_scope_membership_limit_exceeded"
                        )
                    cloud_resources = tuple(
                        RegistryCloudResourceMembershipV2(
                            resource_id=OpaqueIdV1(str(row["resource_id"])),
                            account_id=OpaqueIdV1(str(row["account_id"])),
                            provider_key=str(row["provider_key"]),
                            provider_target=ProviderTargetRefV1(
                                target_kind="cloud_service",
                                target_id=OpaqueIdV1(str(row["access_target_id"])),
                            ),
                            relationship_state="unresolved",
                            registry_revision=revision,
                        )
                        for row in cloud_rows
                        if account_providers.get(str(row["account_id"]))
                        == row["provider_key"]
                    )
                    selected_cloud_resources = {
                        item.resource_id.value for item in cloud_resources
                    }
                    expected_cloud_resources = {
                        str(row["resource_id"]) for row in cloud_rows
                    }
                    if selected_cloud_resources != expected_cloud_resources:
                        raise RegistryRepositoryErrorV1(
                            "registry_cloud_resource_membership_invalid"
                        )
                    if scope_kind == "global":
                        organization_values = tuple(
                            connection.exec_driver_sql(
                                "SELECT organization_id FROM reg_organization "
                                "WHERE lifecycle='active' "
                                "ORDER BY display_order,organization_id"
                            ).scalars()
                        )
                    elif scope_kind == "organization":
                        organization_values = (
                            (scope_value,)
                            if connection.exec_driver_sql(
                                "SELECT 1 FROM reg_organization "
                                "WHERE organization_id=? AND lifecycle='active'",
                                (scope_value,),
                            ).scalar_one_or_none()
                            is not None
                            else ()
                        )
                    else:
                        active_organizations = set(
                            connection.exec_driver_sql(
                                "SELECT organization_id FROM reg_organization "
                                "WHERE lifecycle='active'"
                            ).scalars()
                        )
                        organization_values = tuple(
                            sorted(
                                {
                                    str(row["organization_id"])
                                    for row in account_rows
                                    if row["organization_id"] in active_organizations
                                }
                            )
                        )
                    organization_ids = tuple(
                        OpaqueIdV1(str(value)) for value in organization_values
                    )
                    return RegistryScopeSnapshotV2(
                        scope_kind=scope_kind,
                        scope_id=scope_id,
                        organization_ids=organization_ids,
                        account_ids=account_ids,
                        local_resource_ids=local_resource_ids,
                        cloud_resources=cloud_resources,
                        completeness_state="complete",
                        registry_revision=revision,
                        local_targets=local_targets,
                    )
        except RegistryRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RegistryRepositoryErrorV1() from None
