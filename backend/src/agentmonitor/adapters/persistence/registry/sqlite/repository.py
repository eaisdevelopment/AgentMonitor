"""M02 production repository over the real file-backed SQLite policy."""

# ruff: noqa: E501 -- SQL text preserves auditable column and predicate ordering.

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import DiscoveryOutcomeV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    ConfirmIdentityAssociationCommandV1,
    DiscoveryCandidateViewV1,
    DiscoveryReconciliationViewV1,
    MaskedRegistryFieldV1,
    MonitoringProfileViewV1,
    OrganizationViewV1,
    ProviderInstallationViewV1,
    RegistryScopeKindV1,
    RegistryScopeSnapshotV1,
)
from agentmonitor.modules.registry.application.accounts import (
    EnrollMonitoringGraphCommandV1,
    RegistryPolicyErrorV1,
    decide_account_monitoring,
    decide_candidate_evidence_transition,
    decide_command_replay,
    ensure_candidate_confirmation_is_current,
    safe_registry_event_projection,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationCommandV1,
    RegistryCommandConflictV1,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError


class RegistryRepositoryErrorV1(ValueError):
    """Safe persistence failure; no SQL, path, or stored value is exposed."""

    def __init__(self, code: str = "registry_repository_unavailable") -> None:
        self.code = code
        super().__init__(code)


def _identifier() -> str:
    return secrets.token_urlsafe(24)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise RegistryRepositoryErrorV1("registry_timestamp_invalid")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _utc_value(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _next_revision(connection: Connection, instant: str) -> int:
    current = connection.exec_driver_sql(
        "SELECT registry_revision FROM reg_registry_state WHERE singleton_key=1"
    ).scalar_one_or_none()
    if current is None:
        connection.exec_driver_sql(
            "INSERT INTO reg_registry_state "
            "(singleton_key, registry_revision, domain_policy_version, "
            "created_at, updated_at) "
            "VALUES (1, 1, 'registry-v1', ?, ?)",
            (instant, instant),
        )
        return 1
    revision = int(current) + 1
    connection.exec_driver_sql(
        "UPDATE reg_registry_state SET registry_revision=?, updated_at=? "
        "WHERE singleton_key=1",
        (revision, instant),
    )
    return revision


def _current_revision(connection: Connection) -> int:
    value = connection.exec_driver_sql(
        "SELECT registry_revision FROM reg_registry_state WHERE singleton_key=1"
    ).scalar_one_or_none()
    return int(value) if value is not None else 0


def _append_change(
    connection: Connection,
    *,
    subject_type: str,
    subject_id: str,
    aggregate_version: int,
    revision: int,
    change_kind: str,
    actor_id: str,
    correlation_id: str,
    command_digest: str,
    instant: str,
    new_name: str | None = None,
    new_organization_id: str | None = None,
    new_lifecycle: str | None = None,
) -> None:
    expires_at = _utc_text(
        datetime.fromisoformat(instant.replace("Z", "+00:00")) + timedelta(days=365)
    )
    connection.exec_driver_sql(
        "INSERT INTO reg_registry_change "
        "(change_id, subject_type, subject_id, aggregate_version, registry_revision, "
        "change_kind, previous_name, new_name, previous_organization_id, "
        "new_organization_id, previous_lifecycle, new_lifecycle, actor_class, "
        "actor_id, correlation_id, command_digest, occurred_at, recorded_at, "
        "expires_at) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?, NULL, ?, "
        "'owner', ?, ?, ?, ?, ?, ?)",
        (
            _identifier(),
            subject_type,
            subject_id,
            aggregate_version,
            revision,
            change_kind,
            new_name,
            new_organization_id,
            new_lifecycle,
            actor_id,
            correlation_id,
            command_digest,
            instant,
            instant,
            expires_at,
        ),
    )


def _append_outbox(
    connection: Connection,
    *,
    subject_type: str,
    subject_id: str,
    aggregate_version: int,
    revision: int,
    change_kind: str,
    correlation_id: str,
    causation_id: str | None,
    instant: str,
) -> None:
    projection = safe_registry_event_projection(
        subject_type=subject_type,
        subject_id=OpaqueIdV1(subject_id),
        aggregate_version=aggregate_version,
        registry_revision=revision,
        change_kind=change_kind,
    )
    sequence = int(
        connection.exec_driver_sql(
            "SELECT coalesce(max(producer_sequence), 0) + 1 FROM reg_event_outbox"
        ).scalar_one()
    )
    payload = json.dumps(
        {
            "aggregate_version": projection.aggregate_version,
            "change_kind": projection.change_kind,
            "registry_revision": projection.registry_revision,
            "subject_id": projection.subject_id.value,
            "subject_type": projection.subject_type,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    connection.exec_driver_sql(
        "INSERT INTO reg_event_outbox "
        "(event_id, event_type, subject_type, subject_id, aggregate_version, "
        "registry_revision, producer_sequence, correlation_id, causation_id, "
        "occurred_at, recorded_at, payload_schema, payload_json, delivery_state, "
        "available_at, claimed_at, delivered_at, attempt_count) "
        "VALUES (?, 'registry.changed.v1', ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "'registry.changed.v1', ?, 'pending', ?, NULL, NULL, 0)",
        (
            _identifier(),
            subject_type,
            subject_id,
            aggregate_version,
            revision,
            sequence,
            correlation_id,
            causation_id,
            instant,
            instant,
            payload,
            instant,
        ),
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

    def list_organizations(self) -> tuple[OrganizationViewV1, ...]:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
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
                            "WHERE s.singleton_key=1 ORDER BY o.lifecycle, "
                            "o.display_order, "
                            "o.organization_id LIMIT 100"
                        )
                        .mappings()
                        .all()
                    )
            return tuple(_organization(row) for row in rows)
        except (SqlitePolicyError, SQLAlchemyError, ValueError):
            raise RegistryRepositoryErrorV1() from None

    def reconcile_discovery(
        self, outcome: DiscoveryOutcomeV1, *, reconciled_at: datetime
    ) -> DiscoveryReconciliationViewV1:
        if outcome.value is None or outcome.provenance is None:
            raise RegistryRepositoryErrorV1("registry_discovery_outcome_invalid")
        instant = _utc_text(reconciled_at)
        provider_key = outcome.provenance.provider_key
        operation_id = outcome.provenance.operation_id.value
        correlation_id = outcome.provenance.correlation_id.value
        operation = "reconcile_provider_discovery"
        command_digest = _digest(operation_id)
        service_principal = _digest(f"registry-discovery\x00{provider_key}")
        request_fingerprint = _fingerprint(
            {
                "accounts": [
                    {
                        "candidate_ref": item.candidate_ref.value,
                        "decision_reference": item.provenance.decision_reference,
                        "evidence_strength": item.evidence_strength,
                        "installation_ref": item.installation_ref.value,
                        "owner_confirmation_required": (
                            item.owner_confirmation_required
                        ),
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
        )
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
