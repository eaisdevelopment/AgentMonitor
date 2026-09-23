"""M03 compatibility persistence over the governed real SQLite boundary."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CompatibilityAssessmentInputV1,
    CompatibilityAssessmentViewV1,
    ProviderSystemOutboxEventV1,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

_ASSESSMENT_COLUMNS = (
    "assessment_id, registration_id, provider_key, adapter_id, adapter_version, "
    "protocol_version, installation_id, capability_id, "
    "capability_schema_version, source_id, provider_version_value, "
    "provider_version_state, version_scheme, version_rule_id, "
    "compatibility_state, reason_code, manifest_schema_version, "
    "manifest_fingerprint, input_fingerprint, assessed_at, valid_until, "
    "supersedes_assessment_id, correlation_id, is_current, record_version"
)
_OUTBOX_COLUMNS = (
    "event_id, event_type, assessment_id, registration_id, provider_key, "
    "capability_id, compatibility_state, reason_code, correlation_id, "
    "producer_sequence, occurred_at, recorded_at, delivery_state, available_at, "
    "claimed_at, delivered_at, attempt_count"
)
_MAX_QUERY_LIMIT = 100
_CAPABILITY_ID = re.compile(r"[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*){1,5}\Z")


class ProviderSystemRepositoryErrorV1(ValueError):
    """Safe repository failure carrying only a stable bounded code."""

    def __init__(self, code: str = "provider_system_repository_unavailable") -> None:
        self.code = code
        super().__init__(code)


def _identifier() -> str:
    return secrets.token_urlsafe(24)


def _utc_text(value: datetime) -> str:
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _utc_value(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderSystemRepositoryErrorV1(
            "provider_system_record_invalid"
        ) from None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ProviderSystemRepositoryErrorV1(
            "provider_system_record_invalid"
        ) from None
    if result.utcoffset() != timedelta(0):
        raise ProviderSystemRepositoryErrorV1("provider_system_record_invalid")
    return result


def _fingerprint(value: CompatibilityAssessmentInputV1) -> str:
    canonical = {
        "adapter_id": value.adapter_id,
        "adapter_version": value.adapter_version,
        "capability_id": value.capability_id,
        "capability_schema_version": value.capability_schema_version,
        "compatibility_state": value.compatibility_state,
        "installation_id": (
            value.installation_id.value if value.installation_id is not None else None
        ),
        "manifest_fingerprint": value.manifest_fingerprint,
        "manifest_schema_version": value.manifest_schema_version,
        "protocol_version": value.protocol_version,
        "provider_key": value.provider_key,
        "provider_version_state": value.provider_version_state,
        "provider_version_value": value.provider_version_value,
        "reason_code": value.reason_code,
        "registration_id": value.registration_id.value,
        "source_id": value.source_id,
        "valid_until": (
            _utc_text(value.valid_until) if value.valid_until is not None else None
        ),
        "version_rule_id": value.version_rule_id,
        "version_scheme": value.version_scheme,
    }
    payload = json.dumps(
        canonical, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _assessment(row: RowMapping) -> CompatibilityAssessmentViewV1:
    return CompatibilityAssessmentViewV1(
        assessment_id=OpaqueIdV1(str(row["assessment_id"])),
        registration_id=OpaqueIdV1(str(row["registration_id"])),
        provider_key=str(row["provider_key"]),
        adapter_id=str(row["adapter_id"]),
        adapter_version=str(row["adapter_version"]),
        protocol_version=str(row["protocol_version"]),
        installation_id=(
            OpaqueIdV1(str(row["installation_id"]))
            if row["installation_id"] is not None
            else None
        ),
        capability_id=str(row["capability_id"]),
        capability_schema_version=str(row["capability_schema_version"]),
        source_id=str(row["source_id"]) if row["source_id"] is not None else None,
        provider_version_value=(
            str(row["provider_version_value"])
            if row["provider_version_value"] is not None
            else None
        ),
        provider_version_state=row["provider_version_state"],
        version_scheme=_version_scheme(row["version_scheme"]),
        version_rule_id=(
            str(row["version_rule_id"]) if row["version_rule_id"] is not None else None
        ),
        compatibility_state=row["compatibility_state"],
        reason_code=str(row["reason_code"]),
        manifest_schema_version=str(row["manifest_schema_version"]),
        manifest_fingerprint=str(row["manifest_fingerprint"]),
        input_fingerprint=str(row["input_fingerprint"]),
        assessed_at=_required_utc(row["assessed_at"]),
        valid_until=_utc_value(row["valid_until"]),
        supersedes_assessment_id=(
            OpaqueIdV1(str(row["supersedes_assessment_id"]))
            if row["supersedes_assessment_id"] is not None
            else None
        ),
        correlation_id=OpaqueIdV1(str(row["correlation_id"])),
        is_current=bool(row["is_current"]),
        record_version=int(row["record_version"]),
    )


def _outbox_event(row: RowMapping) -> ProviderSystemOutboxEventV1:
    return ProviderSystemOutboxEventV1(
        event_id=OpaqueIdV1(str(row["event_id"])),
        event_type=str(row["event_type"]),
        assessment_id=OpaqueIdV1(str(row["assessment_id"])),
        registration_id=OpaqueIdV1(str(row["registration_id"])),
        provider_key=str(row["provider_key"]),
        capability_id=str(row["capability_id"]),
        compatibility_state=row["compatibility_state"],
        reason_code=str(row["reason_code"]),
        correlation_id=OpaqueIdV1(str(row["correlation_id"])),
        producer_sequence=int(row["producer_sequence"]),
        occurred_at=_required_utc(row["occurred_at"]),
        recorded_at=_required_utc(row["recorded_at"]),
        delivery_state=row["delivery_state"],
        available_at=_required_utc(row["available_at"]),
        claimed_at=_utc_value(row["claimed_at"]),
        delivered_at=_utc_value(row["delivered_at"]),
        attempt_count=int(row["attempt_count"]),
    )


def _required_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ProviderSystemRepositoryErrorV1("provider_system_record_invalid")
    result = _utc_value(value)
    if result is None:
        raise ProviderSystemRepositoryErrorV1("provider_system_record_invalid")
    return result


def _version_scheme(
    value: object,
) -> Literal["opaque_exact", "semantic_exact", "date_exact"] | None:
    if value is None:
        return None
    if value not in {"opaque_exact", "semantic_exact", "date_exact"}:
        raise ProviderSystemRepositoryErrorV1("provider_system_record_invalid")
    return value


def _validate_limit(limit: int) -> None:
    if type(limit) is not int or not 1 <= limit <= _MAX_QUERY_LIMIT:
        raise ProviderSystemRepositoryErrorV1("provider_system_query_invalid")


def _validate_opaque_id(value: object) -> None:
    if (
        not isinstance(value, OpaqueIdV1)
        or type(value.value) is not str
        or value.value != value.value.strip()
        or not 1 <= len(value.value) <= 64
        or not value.value.isprintable()
    ):
        raise ProviderSystemRepositoryErrorV1("provider_system_query_invalid")


def _validate_capability_id(value: object) -> None:
    if (
        type(value) is not str
        or len(value) > 128
        or _CAPABILITY_ID.fullmatch(value) is None
    ):
        raise ProviderSystemRepositoryErrorV1("provider_system_query_invalid")


def _validate_source_id(value: object) -> None:
    if value is not None and (
        type(value) is not str
        or value != value.strip()
        or not 1 <= len(value) <= 128
        or not value.isprintable()
    ):
        raise ProviderSystemRepositoryErrorV1("provider_system_query_invalid")


def _current_row(
    connection: Connection,
    *,
    registration_id: str,
    installation_id: str | None,
    capability_id: str,
    source_id: str | None,
) -> RowMapping | None:
    rows = (
        connection.exec_driver_sql(
            f"SELECT {_ASSESSMENT_COLUMNS} "  # noqa: S608 -- closed constant columns
            "FROM provider_system_compatibility_assessment "
            "WHERE registration_id=? AND installation_id IS ? "
            "AND capability_id=? AND source_id IS ? AND is_current=1 "
            "ORDER BY assessed_at DESC, assessment_id DESC LIMIT 2",
            (registration_id, installation_id, capability_id, source_id),
        )
        .mappings()
        .all()
    )
    if len(rows) > 1:
        raise ProviderSystemRepositoryErrorV1("provider_system_current_conflict")
    return rows[0] if rows else None


class SqliteProviderSystemCompatibilityRepositoryV1:
    """Own only M03 compatibility and outbox rows in schema ``v1_0300``."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        if not isinstance(database_ref, DatabaseRefV1):
            raise ProviderSystemRepositoryErrorV1()
        self._database_ref = database_ref

    def reopen(self) -> SqliteProviderSystemCompatibilityRepositoryV1:
        return SqliteProviderSystemCompatibilityRepositoryV1(self._database_ref)

    def record(
        self, value: CompatibilityAssessmentInputV1
    ) -> CompatibilityAssessmentViewV1:
        if not isinstance(value, CompatibilityAssessmentInputV1):
            raise ProviderSystemRepositoryErrorV1("provider_system_assessment_invalid")
        input_fingerprint = _fingerprint(value)
        installation_id = (
            value.installation_id.value if value.installation_id is not None else None
        )
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    existing = (
                        connection.exec_driver_sql(
                            f"SELECT {_ASSESSMENT_COLUMNS} "
                            "FROM provider_system_compatibility_assessment "
                            "WHERE input_fingerprint=? LIMIT 1",
                            (input_fingerprint,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if existing is not None:
                        result = _assessment(existing)
                        connection.rollback()
                        if not result.is_current:
                            raise ProviderSystemRepositoryErrorV1(
                                "provider_system_assessment_conflict"
                            )
                        return result
                    prior = _current_row(
                        connection,
                        registration_id=value.registration_id.value,
                        installation_id=installation_id,
                        capability_id=value.capability_id,
                        source_id=value.source_id,
                    )
                    prior_id = (
                        str(prior["assessment_id"]) if prior is not None else None
                    )
                    if prior is not None:
                        changed = connection.exec_driver_sql(
                            "UPDATE provider_system_compatibility_assessment "
                            "SET is_current=0, record_version=record_version+1 "
                            "WHERE assessment_id=? AND is_current=1",
                            (prior_id,),
                        ).rowcount
                        if changed != 1:
                            connection.rollback()
                            raise ProviderSystemRepositoryErrorV1(
                                "provider_system_current_conflict"
                            )
                    assessment_id = _identifier()
                    assessed_at = _utc_text(value.assessed_at)
                    valid_until = (
                        _utc_text(value.valid_until)
                        if value.valid_until is not None
                        else None
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO provider_system_compatibility_assessment "
                        "(assessment_id, registration_id, provider_key, adapter_id, "
                        "adapter_version, protocol_version, installation_id, "
                        "capability_id, capability_schema_version, source_id, "
                        "provider_version_value, provider_version_state, "
                        "version_scheme, version_rule_id, compatibility_state, "
                        "reason_code, manifest_schema_version, manifest_fingerprint, "
                        "input_fingerprint, assessed_at, valid_until, "
                        "supersedes_assessment_id, correlation_id, is_current, "
                        "record_version) VALUES "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                        "?, ?, ?, ?, ?, 1, 1)",
                        (
                            assessment_id,
                            value.registration_id.value,
                            value.provider_key,
                            value.adapter_id,
                            value.adapter_version,
                            value.protocol_version,
                            installation_id,
                            value.capability_id,
                            value.capability_schema_version,
                            value.source_id,
                            value.provider_version_value,
                            value.provider_version_state,
                            value.version_scheme,
                            value.version_rule_id,
                            value.compatibility_state,
                            value.reason_code,
                            value.manifest_schema_version,
                            value.manifest_fingerprint,
                            input_fingerprint,
                            assessed_at,
                            valid_until,
                            prior_id,
                            value.correlation_id.value,
                        ),
                    )
                    sequence = int(
                        connection.exec_driver_sql(
                            "SELECT coalesce(max(producer_sequence), 0) + 1 "
                            "FROM provider_system_event_outbox"
                        ).scalar_one()
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO provider_system_event_outbox "
                        "(event_id, event_type, assessment_id, registration_id, "
                        "provider_key, capability_id, compatibility_state, "
                        "reason_code, correlation_id, producer_sequence, occurred_at, "
                        "recorded_at, delivery_state, available_at, claimed_at, "
                        "delivered_at, attempt_count) VALUES "
                        "(?, 'provider.compatibility.assessed.v1', ?, ?, ?, ?, ?, ?, "
                        "?, ?, ?, ?, 'pending', ?, NULL, NULL, 0)",
                        (
                            _identifier(),
                            assessment_id,
                            value.registration_id.value,
                            value.provider_key,
                            value.capability_id,
                            value.compatibility_state,
                            value.reason_code,
                            value.correlation_id.value,
                            sequence,
                            assessed_at,
                            assessed_at,
                            assessed_at,
                        ),
                    )
                    row = (
                        connection.exec_driver_sql(
                            f"SELECT {_ASSESSMENT_COLUMNS} "
                            "FROM provider_system_compatibility_assessment "
                            "WHERE assessment_id=?",
                            (assessment_id,),
                        )
                        .mappings()
                        .one()
                    )
                    result = _assessment(row)
                    connection.commit()
                    return result
        except ProviderSystemRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise ProviderSystemRepositoryErrorV1() from None

    def get(self, assessment_id: OpaqueIdV1) -> CompatibilityAssessmentViewV1 | None:
        _validate_opaque_id(assessment_id)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            f"SELECT {_ASSESSMENT_COLUMNS} "
                            "FROM provider_system_compatibility_assessment "
                            "WHERE assessment_id=? LIMIT 1",
                            (assessment_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
            return _assessment(row) if row is not None else None
        except ProviderSystemRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise ProviderSystemRepositoryErrorV1() from None

    def current(
        self,
        *,
        registration_id: OpaqueIdV1,
        installation_id: OpaqueIdV1 | None,
        capability_id: str,
        source_id: str | None,
    ) -> CompatibilityAssessmentViewV1 | None:
        _validate_opaque_id(registration_id)
        if installation_id is not None:
            _validate_opaque_id(installation_id)
        _validate_capability_id(capability_id)
        _validate_source_id(source_id)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    row = _current_row(
                        connection,
                        registration_id=registration_id.value,
                        installation_id=(
                            installation_id.value
                            if installation_id is not None
                            else None
                        ),
                        capability_id=capability_id,
                        source_id=source_id,
                    )
            return _assessment(row) if row is not None else None
        except ProviderSystemRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise ProviderSystemRepositoryErrorV1() from None

    def history(
        self,
        registration_id: OpaqueIdV1,
        capability_id: str,
        *,
        limit: int,
    ) -> tuple[CompatibilityAssessmentViewV1, ...]:
        _validate_limit(limit)
        _validate_opaque_id(registration_id)
        _validate_capability_id(capability_id)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            f"SELECT {_ASSESSMENT_COLUMNS} "
                            "FROM provider_system_compatibility_assessment "
                            "WHERE registration_id=? AND capability_id=? "
                            "ORDER BY assessed_at DESC, assessment_id DESC LIMIT ?",
                            (registration_id.value, capability_id, limit),
                        )
                        .mappings()
                        .all()
                    )
            return tuple(_assessment(row) for row in rows)
        except ProviderSystemRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise ProviderSystemRepositoryErrorV1() from None

    def pending_outbox(self, *, limit: int) -> tuple[ProviderSystemOutboxEventV1, ...]:
        _validate_limit(limit)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            f"SELECT {_OUTBOX_COLUMNS} "
                            "FROM provider_system_event_outbox "
                            "WHERE delivery_state='pending' "
                            "ORDER BY producer_sequence LIMIT ?",
                            (limit,),
                        )
                        .mappings()
                        .all()
                    )
            return tuple(_outbox_event(row) for row in rows)
        except ProviderSystemRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise ProviderSystemRepositoryErrorV1() from None
