"""M02 SQLite revision, receipt and sanitized event transaction primitives."""

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.accounts import (
    safe_registry_event_projection,
)
from sqlalchemy.engine import Connection


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


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise RegistryRepositoryErrorV1("registry_timestamp_invalid")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


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
    previous_name: str | None = None,
    new_name: str | None = None,
    previous_organization_id: str | None = None,
    new_organization_id: str | None = None,
    previous_lifecycle: str | None = None,
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
        "expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "'owner', ?, ?, ?, ?, ?, ?)",
        (
            _identifier(),
            subject_type,
            subject_id,
            aggregate_version,
            revision,
            change_kind,
            previous_name,
            new_name,
            previous_organization_id,
            new_organization_id,
            previous_lifecycle,
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
