"""M06 runtime repository over production file-backed SQLite."""
# ruff: noqa: E501 -- SQL statements preserve auditable column/value ordering.

from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.contracts.common_provenance_v1 import (
    FallbackAttemptV1,
    ObservationProvenanceV1,
)
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    AgentProcessRecordV1,
    AgentSessionRecordV1,
    CorrelationEvidenceInputV1,
    PresenceStateV1,
    ProcessCodeFieldV1,
    ProcessHistoryEntryV1,
    ProcessIdentityV1,
    ProcessLabelFieldV1,
    ProcessMetricFieldV1,
    RuntimeCommitReceiptV1,
    RuntimeCommitRequestV1,
    RuntimeCommitStatusV1,
    SessionCorrelationDecisionV1,
    SessionIdentityV1,
    SessionProcessLinkInputV1,
    SessionTopologyFactV1,
    SessionTopologySnapshotV1,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

_PROVENANCE_COLUMNS = (
    "provider_key",
    "capability_id",
    "capability_schema_version",
    "adapter_id",
    "adapter_version",
    "provider_protocol_version",
    "source_id",
    "source_class",
    "mechanism_version",
    "parser_version",
    "provider_version",
    "provider_version_availability",
    "observed_at",
    "observed_at_availability",
    "collected_at",
    "freshness_deadline",
    "freshness_availability",
    "freshness_policy_id",
    "precision",
    "confidence",
    "confidence_reason_code",
    "value_kind",
    "is_experimental",
    "operation_id",
    "correlation_id",
    "decision_reference",
    "derivation_method",
    "fallback_lineage_json",
    "warnings_json",
    "input_observation_ids_json",
)
_PROVENANCE_SELECT = ", ".join(
    f"r.{name} AS provenance_{name}" for name in _PROVENANCE_COLUMNS
)
_CURRENT_SESSION_SELECT = (
    "SELECT s.*, " + _PROVENANCE_SELECT + " FROM runtime_session AS s "
    "JOIN runtime_session_observation AS o "
    "ON o.observation_id=s.current_observation_id "
    "JOIN runtime_ingest_receipt AS r "
    "ON r.collection_run_id=o.collection_run_id "
    "AND r.source_id=o.source_id AND r.parser_version=o.parser_version "
)
_RECEIPT_COLUMNS = (
    "receipt_id",
    "collection_run_id",
    "target_generation",
    "capability_id",
    "payload_schema",
    "payload_digest",
    "consumer_key",
    "consumer_version",
    *_PROVENANCE_COLUMNS[:1],
    *_PROVENANCE_COLUMNS[2:],
    "observation_set_digest",
    "observation_ids_json",
    "affected_projection_ids_json",
    "projection_versions_json",
    "event_ids_json",
    "stored_at_start",
    "stored_at_end",
    "stored_at",
    "receipt_version",
)
_RECEIPT_INSERT_SQL = (
    "INSERT INTO runtime_ingest_receipt ("
    + ", ".join(_RECEIPT_COLUMNS)
    + ") VALUES ("
    + ", ".join("?" for _ in _RECEIPT_COLUMNS)
    + ")"
)


class RuntimeRepositoryErrorV1(ValueError):
    """Stable repository failure that exposes no SQL or stored metadata."""

    def __init__(self, code: str = "runtime_repository_unavailable") -> None:
        self.code = code
        super().__init__(code)


def _identifier() -> str:
    return secrets.token_urlsafe(24)


def _stable_identifier(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def _process_identifier(identity: ProcessIdentityV1) -> str:
    return _stable_identifier(
        identity.platform_source,
        identity.platform_scope_id,
        str(identity.pid),
        str(identity.start_time_ticks),
    )


def _session_identifier(identity: SessionIdentityV1) -> str:
    return _stable_identifier(
        identity.provider_key,
        identity.installation_id,
        identity.identity_kind,
        identity.identity_value,
    )


def _reconcile_process_attribution(
    *,
    existing_executable_identity: str | None,
    existing_provider_key: str | None,
    existing_installation_id: str | None,
    observed_executable_identity: str | None,
    observed_provider_key: str | None,
    observed_installation_id: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Enrich an identity monotonically and reject contradictory evidence."""

    def valid_fingerprint(value: str | None) -> bool:
        return value is None or (
            len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )

    if not valid_fingerprint(existing_executable_identity) or not valid_fingerprint(
        observed_executable_identity
    ):
        raise RuntimeRepositoryErrorV1("runtime_process_identity_conflict")
    for existing, observed in (
        (existing_executable_identity, observed_executable_identity),
        (existing_provider_key, observed_provider_key),
        (existing_installation_id, observed_installation_id),
    ):
        if existing is not None and observed is not None and existing != observed:
            raise RuntimeRepositoryErrorV1("runtime_process_identity_conflict")

    executable_identity = existing_executable_identity or observed_executable_identity
    provider_key = existing_provider_key or observed_provider_key
    installation_id = existing_installation_id or observed_installation_id
    if (installation_id is not None and provider_key is None) or (
        (provider_key is not None or installation_id is not None)
        and executable_identity is None
    ):
        raise RuntimeRepositoryErrorV1("runtime_process_identity_conflict")
    return executable_identity, provider_key, installation_id


def _may_promote_process_snapshot(
    *,
    current_observed_at: str,
    current_provider_key: str | None,
    observed_at: str,
    observed_provider_key: str | None,
) -> bool:
    """Keep the current projection chronological without losing stronger identity."""
    if observed_at < current_observed_at:
        return False
    return not (current_provider_key is not None and observed_provider_key is None)


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise RuntimeRepositoryErrorV1("runtime_timestamp_invalid")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _utc_value(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() != timedelta(0):
        raise RuntimeRepositoryErrorV1("runtime_stored_timestamp_invalid")
    return result


def _safe_id_list(value: object) -> tuple[OpaqueIdV1, ...]:
    if not isinstance(value, str):
        raise RuntimeRepositoryErrorV1("runtime_receipt_invalid")
    parsed = json.loads(value)
    if (
        not isinstance(parsed, list)
        or not parsed
        or not all(isinstance(item, str) for item in parsed)
    ):
        raise RuntimeRepositoryErrorV1("runtime_receipt_invalid")
    return tuple(OpaqueIdV1(item) for item in parsed)


def _safe_int_list(value: object) -> tuple[int, ...]:
    if not isinstance(value, str):
        raise RuntimeRepositoryErrorV1("runtime_receipt_invalid")
    parsed = json.loads(value)
    if (
        not isinstance(parsed, list)
        or not parsed
        or not all(type(item) is int and item > 0 for item in parsed)
    ):
        raise RuntimeRepositoryErrorV1("runtime_receipt_invalid")
    return tuple(parsed)


def _safe_text_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise RuntimeRepositoryErrorV1("runtime_provenance_invalid")
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(
        isinstance(item, str) for item in parsed
    ):
        raise RuntimeRepositoryErrorV1("runtime_provenance_invalid")
    return tuple(parsed)


def _safe_fallbacks(value: object) -> tuple[FallbackAttemptV1, ...]:
    if not isinstance(value, str):
        raise RuntimeRepositoryErrorV1("runtime_provenance_invalid")
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise RuntimeRepositoryErrorV1("runtime_provenance_invalid")
    try:
        return tuple(
            FallbackAttemptV1(source_id=item[0], failure_code=item[1])
            for item in parsed
            if isinstance(item, list) and len(item) == 2
        )
    except (TypeError, ValueError):
        raise RuntimeRepositoryErrorV1("runtime_provenance_invalid") from None


def _optional_utc(value: object) -> datetime | None:
    return None if value is None else _utc_value(str(value))


def _presence(value: object) -> PresenceStateV1:
    if value == "running":
        return "running"
    if value == "exited":
        return "exited"
    if value == "unknown":
        return "unknown"
    raise RuntimeRepositoryErrorV1("runtime_process_presence_invalid")


def _process_metric(
    row: RowMapping, prefix: str, value_column: str
) -> ProcessMetricFieldV1:
    value = row[value_column]
    unit = row[f"{prefix}_unit"]
    reason_code = row[f"{prefix}_reason_code"]
    return ProcessMetricFieldV1(
        state=row[f"{prefix}_state"],
        value=int(value) if value is not None else None,
        unit=str(unit) if unit is not None else None,
        reason_code=str(reason_code) if reason_code is not None else None,
    )


def _provenance(row: RowMapping) -> ObservationProvenanceV1:
    fallback_lineage = _safe_fallbacks(row["provenance_fallback_lineage_json"])
    raw_fallbacks = json.loads(str(row["provenance_fallback_lineage_json"]))
    if len(fallback_lineage) != len(raw_fallbacks):
        raise RuntimeRepositoryErrorV1("runtime_provenance_invalid")
    return ObservationProvenanceV1(
        provider_key=str(row["provenance_provider_key"]),
        capability_id=str(row["provenance_capability_id"]),
        capability_schema_version=str(row["provenance_capability_schema_version"]),
        adapter_id=str(row["provenance_adapter_id"]),
        adapter_version=str(row["provenance_adapter_version"]),
        provider_protocol_version=str(row["provenance_provider_protocol_version"]),
        source_id=str(row["provenance_source_id"]),
        source_class=row["provenance_source_class"],
        mechanism_version=str(row["provenance_mechanism_version"]),
        parser_version=(
            str(row["provenance_parser_version"])
            if row["provenance_parser_version"] is not None
            else None
        ),
        provider_version=(
            str(row["provenance_provider_version"])
            if row["provenance_provider_version"] is not None
            else None
        ),
        provider_version_availability=FieldAvailabilityV1(
            row["provenance_provider_version_availability"]
        ),
        observed_at=_optional_utc(row["provenance_observed_at"]),
        observed_at_availability=FieldAvailabilityV1(
            row["provenance_observed_at_availability"]
        ),
        collected_at=_utc_value(str(row["provenance_collected_at"])),
        freshness_deadline=_optional_utc(row["provenance_freshness_deadline"]),
        freshness_availability=FieldAvailabilityV1(
            row["provenance_freshness_availability"]
        ),
        freshness_policy_id=str(row["provenance_freshness_policy_id"]),
        precision=row["provenance_precision"],
        confidence=row["provenance_confidence"],
        confidence_reason_code=str(row["provenance_confidence_reason_code"]),
        value_kind=row["provenance_value_kind"],
        is_experimental=bool(row["provenance_is_experimental"]),
        fallback_lineage=fallback_lineage,
        warnings=_safe_text_list(row["provenance_warnings_json"]),
        operation_id=OpaqueIdV1(str(row["provenance_operation_id"])),
        correlation_id=OpaqueIdV1(str(row["provenance_correlation_id"])),
        decision_reference=str(row["provenance_decision_reference"]),
        derivation_method=(
            str(row["provenance_derivation_method"])
            if row["provenance_derivation_method"] is not None
            else None
        ),
        input_observation_ids=tuple(
            OpaqueIdV1(value)
            for value in _safe_text_list(row["provenance_input_observation_ids_json"])
        ),
    )


def _receipt_provenance_matches(
    row: RowMapping, provenance: ObservationProvenanceV1
) -> bool:
    """Compare replay lineage using the exact canonical SQLite representation."""
    expected: dict[str, object] = {
        "provider_key": provenance.provider_key,
        "capability_id": provenance.capability_id,
        "capability_schema_version": provenance.capability_schema_version,
        "adapter_id": provenance.adapter_id,
        "adapter_version": provenance.adapter_version,
        "provider_protocol_version": provenance.provider_protocol_version,
        "source_id": provenance.source_id,
        "source_class": provenance.source_class,
        "mechanism_version": provenance.mechanism_version,
        "parser_version": provenance.parser_version,
        "provider_version": provenance.provider_version,
        "provider_version_availability": provenance.provider_version_availability.state,
        "observed_at": (
            _utc_text(provenance.observed_at)
            if provenance.observed_at is not None
            else None
        ),
        "observed_at_availability": provenance.observed_at_availability.state,
        "collected_at": _utc_text(provenance.collected_at),
        "freshness_deadline": (
            _utc_text(provenance.freshness_deadline)
            if provenance.freshness_deadline is not None
            else None
        ),
        "freshness_availability": provenance.freshness_availability.state,
        "freshness_policy_id": provenance.freshness_policy_id,
        "precision": provenance.precision,
        "confidence": provenance.confidence,
        "confidence_reason_code": provenance.confidence_reason_code,
        "value_kind": provenance.value_kind,
        "is_experimental": int(provenance.is_experimental),
        "operation_id": provenance.operation_id.value,
        "correlation_id": provenance.correlation_id.value,
        "decision_reference": provenance.decision_reference,
        "derivation_method": provenance.derivation_method,
        "fallback_lineage_json": json.dumps(
            [
                [item.source_id, item.failure_code]
                for item in provenance.fallback_lineage
            ],
            separators=(",", ":"),
        ),
        "warnings_json": json.dumps(provenance.warnings, separators=(",", ":")),
        "input_observation_ids_json": json.dumps(
            [item.value for item in provenance.input_observation_ids],
            separators=(",", ":"),
        ),
    }
    return all(row[name] == value for name, value in expected.items())


def _receipt(row: RowMapping) -> RuntimeCommitReceiptV1:
    return RuntimeCommitReceiptV1(
        run_id=OpaqueIdV1(str(row["collection_run_id"])),
        target_generation=int(row["target_generation"]),
        capability_id=str(row["capability_id"]),
        payload_schema=str(row["payload_schema"]),
        payload_digest=str(row["payload_digest"]),
        consumer_key=str(row["consumer_key"]),
        consumer_version=str(row["consumer_version"]),
        observation_ids=_safe_id_list(row["observation_ids_json"]),
        observation_set_digest=str(row["observation_set_digest"]),
        stored_at_start=_utc_value(str(row["stored_at_start"])),
        stored_at_end=_utc_value(str(row["stored_at_end"])),
        affected_projection_ids=_safe_id_list(row["affected_projection_ids_json"]),
        projection_versions=_safe_int_list(row["projection_versions_json"]),
        event_ids=_safe_id_list(row["event_ids_json"]),
        stored_at=_utc_value(str(row["stored_at"])),
        receipt_version=int(row["receipt_version"]),
    )


def _validate_query(as_of: datetime, page_size: int) -> None:
    if (
        as_of.utcoffset() != timedelta(0)
        or type(page_size) is not int
        or not 1 <= page_size <= 500
    ):
        raise RuntimeRepositoryErrorV1("runtime_query_invalid")


class SqliteRuntimeObservationRepositoryV1:
    """Atomic runtime commit, replay, current projection, and bounded history."""

    CONSUMER_KEY = "runtime_observation"
    CONSUMER_VERSION = "1.0.0"
    PAYLOAD_SCHEMA = "runtime-observation-batch.v1"

    def __init__(
        self,
        database_ref: DatabaseRefV1,
        correlation_evaluator: Callable[
            [SessionIdentityV1, tuple[CorrelationEvidenceInputV1, ...]],
            SessionCorrelationDecisionV1,
        ]
        | None = None,
    ) -> None:
        self._database_ref = database_ref
        self._correlation_evaluator = correlation_evaluator

    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> RuntimeCommitStatusV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM runtime_ingest_receipt WHERE collection_run_id=? AND capability_id=?",
                            (run_id.value, capability_id),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        return RuntimeCommitStatusV1(
                            state="not_committed", receipt=None
                        )
                    return RuntimeCommitStatusV1(
                        state="committed", receipt=_receipt(row)
                    )
        except RuntimeRepositoryErrorV1:
            raise
        except (
            SqlitePolicyError,
            SQLAlchemyError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            raise RuntimeRepositoryErrorV1() from None

    def commit(self, request: RuntimeCommitRequestV1) -> RuntimeCommitReceiptV1:
        """Persist one typed batch without invoking a provider or platform."""
        if request.payload_schema != self.PAYLOAD_SCHEMA:
            raise RuntimeRepositoryErrorV1("runtime_input_schema_incompatible")
        if request.payload.canonical_digest() != request.payload_digest:
            raise RuntimeRepositoryErrorV1("runtime_payload_digest_mismatch")
        expected_terminal_state = (
            "partial"
            if request.payload.completeness == "partial_scope"
            else "succeeded"
        )
        if request.terminal_state != expected_terminal_state:
            raise RuntimeRepositoryErrorV1("runtime_terminal_state_mismatch")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    existing = (
                        connection.exec_driver_sql(
                            "SELECT * FROM runtime_ingest_receipt WHERE collection_run_id=? AND capability_id=?",
                            (request.run_id.value, request.capability_id),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if existing is not None:
                        if (
                            int(existing["target_generation"])
                            != request.target_generation
                            or str(existing["payload_schema"]) != request.payload_schema
                            or str(existing["payload_digest"]) != request.payload_digest
                            or not _receipt_provenance_matches(
                                existing, request.provenance
                            )
                        ):
                            connection.rollback()
                            raise RuntimeRepositoryErrorV1("runtime_commit_conflict")
                        result = _receipt(existing)
                        connection.commit()
                        return result
                    result = self._insert_commit(connection, request)
                    connection.commit()
                    return result
        except RuntimeRepositoryErrorV1:
            raise
        except (
            SqlitePolicyError,
            SQLAlchemyError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            raise RuntimeRepositoryErrorV1() from None

    def _insert_commit(
        self, connection: Connection, request: RuntimeCommitRequestV1
    ) -> RuntimeCommitReceiptV1:
        payload = request.payload
        provenance = request.provenance
        if payload.session_observations and self._correlation_evaluator is None:
            raise RuntimeRepositoryErrorV1("runtime_correlation_policy_unavailable")
        provider_keys = {
            item.provider_key
            for item in payload.process_snapshots
            if item.provider_key is not None
        }
        provider_keys.update(
            item.session_identity.provider_key for item in payload.session_observations
        )
        if (
            provider_keys - {provenance.provider_key}
            or request.capability_id != provenance.capability_id
        ):
            raise RuntimeRepositoryErrorV1("runtime_provenance_mismatch")
        if any(
            item.source_id != provenance.source_id
            or item.adapter_version != provenance.adapter_version
            or (
                provenance.observed_at is not None
                and item.observed_at != provenance.observed_at
            )
            for item in payload.process_snapshots
        ):
            raise RuntimeRepositoryErrorV1("runtime_provenance_mismatch")
        if any(
            item.source_id != provenance.source_id
            or item.parser_version != provenance.parser_version
            or item.provider_version != provenance.provider_version
            for item in payload.session_observations
        ):
            raise RuntimeRepositoryErrorV1("runtime_provenance_mismatch")
        if any(
            item.source_id != provenance.source_id
            or item.parser_version != provenance.parser_version
            or item.provider_version != provenance.provider_version
            for item in payload.metric_observations
        ):
            raise RuntimeRepositoryErrorV1("runtime_provenance_mismatch")
        if any(
            item.source_id != provenance.source_id
            for item in payload.session_process_links
        ):
            raise RuntimeRepositoryErrorV1("runtime_provenance_mismatch")
        stored_at = datetime.now(UTC)
        stored_text = _utc_text(stored_at)
        observation_ids: list[str] = []
        projection_versions: dict[str, int] = {}

        for item in payload.process_snapshots:
            process_id = _process_identifier(item.identity)
            observed_text = _utc_text(item.observed_at)
            current = (
                connection.exec_driver_sql(
                    "SELECT last_observed_at, presence_state, current_snapshot_id, "
                    "record_version, executable_identity, provider_key, installation_id "
                    "FROM runtime_process_instance WHERE process_id=?",
                    (process_id,),
                )
                .mappings()
                .one_or_none()
            )
            snapshot_id = item.observation_id
            if current is None:
                connection.exec_driver_sql(
                    "INSERT INTO runtime_process_instance (process_id, platform_source, platform_scope_id, pid, start_time_ticks, executable_identity, executable_label, provider_key, installation_id, first_observed_at, last_observed_at, presence_state, current_snapshot_id, record_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                    (
                        process_id,
                        item.identity.platform_source,
                        item.identity.platform_scope_id,
                        item.identity.pid,
                        item.identity.start_time_ticks,
                        item.executable_identity,
                        item.executable_label.value,
                        item.provider_key,
                        item.installation_id,
                        observed_text,
                        observed_text,
                        item.presence,
                        snapshot_id,
                    ),
                )
                version = 1
            else:
                version = int(current["record_version"])
                existing_executable_identity = (
                    str(current["executable_identity"])
                    if current["executable_identity"] is not None
                    else None
                )
                existing_provider_key = (
                    str(current["provider_key"])
                    if current["provider_key"] is not None
                    else None
                )
                existing_installation_id = (
                    str(current["installation_id"])
                    if current["installation_id"] is not None
                    else None
                )
                (
                    executable_identity,
                    provider_key,
                    installation_id,
                ) = _reconcile_process_attribution(
                    existing_executable_identity=existing_executable_identity,
                    existing_provider_key=existing_provider_key,
                    existing_installation_id=existing_installation_id,
                    observed_executable_identity=item.executable_identity,
                    observed_provider_key=item.provider_key,
                    observed_installation_id=item.installation_id,
                )
                promotes_snapshot = current["current_snapshot_id"] is None or (
                    _may_promote_process_snapshot(
                        current_observed_at=str(current["last_observed_at"]),
                        current_provider_key=existing_provider_key,
                        observed_at=observed_text,
                        observed_provider_key=item.provider_key,
                    )
                )
                if promotes_snapshot:
                    version += 1
                    connection.exec_driver_sql(
                        "UPDATE runtime_process_instance SET executable_identity=?, "
                        "provider_key=?, installation_id=?, last_observed_at=?, "
                        "presence_state=?, current_snapshot_id=?, record_version=? "
                        "WHERE process_id=?",
                        (
                            executable_identity,
                            provider_key,
                            installation_id,
                            observed_text,
                            item.presence,
                            snapshot_id,
                            version,
                            process_id,
                        ),
                    )
            connection.exec_driver_sql(
                "INSERT INTO runtime_process_snapshot (snapshot_id, process_id, collection_run_id, source_observation_id, observed_at, collected_at, stored_at, source_id, source_version, adapter_version, presence_state, executable_label_state, executable_label, executable_label_reason_code, parent_pid_state, parent_pid, parent_pid_unit, parent_pid_reason_code, user_cpu_state, user_cpu_ticks, user_cpu_unit, user_cpu_reason_code, system_cpu_state, system_cpu_ticks, system_cpu_unit, system_cpu_reason_code, resident_state, resident_pages, resident_unit, resident_reason_code, thread_state, thread_count, thread_unit, thread_reason_code, kernel_state_state, kernel_state, kernel_state_unit, kernel_state_reason_code, clock_ticks_per_second, page_size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    snapshot_id,
                    process_id,
                    request.run_id.value,
                    item.observation_id,
                    observed_text,
                    _utc_text(provenance.collected_at),
                    stored_text,
                    item.source_id,
                    item.source_version,
                    item.adapter_version,
                    item.presence,
                    item.executable_label.state,
                    item.executable_label.value,
                    item.executable_label.reason_code,
                    item.parent_pid.state,
                    item.parent_pid.value,
                    item.parent_pid.unit,
                    item.parent_pid.reason_code,
                    item.user_cpu_ticks.state,
                    item.user_cpu_ticks.value,
                    item.user_cpu_ticks.unit,
                    item.user_cpu_ticks.reason_code,
                    item.system_cpu_ticks.state,
                    item.system_cpu_ticks.value,
                    item.system_cpu_ticks.unit,
                    item.system_cpu_ticks.reason_code,
                    item.resident_pages.state,
                    item.resident_pages.value,
                    item.resident_pages.unit,
                    item.resident_pages.reason_code,
                    item.thread_count.state,
                    item.thread_count.value,
                    item.thread_count.unit,
                    item.thread_count.reason_code,
                    item.kernel_state.state,
                    item.kernel_state.value,
                    "state_code" if item.kernel_state.state == "present" else None,
                    item.kernel_state.reason_code,
                    item.clock_ticks_per_second,
                    item.page_size_bytes,
                ),
            )
            observation_ids.append(snapshot_id)
            projection_versions[process_id] = version

        sessions: dict[SessionIdentityV1, tuple[str, datetime]] = {}
        for session_item in payload.session_observations:
            identity = session_item.session_identity
            session_id = _session_identifier(identity)
            sessions[identity] = (session_id, session_item.observed_at)
            observed_text = _utc_text(session_item.observed_at)
            current = (
                connection.exec_driver_sql(
                    "SELECT last_observed_at, record_version FROM runtime_session WHERE session_id=?",
                    (session_id,),
                )
                .mappings()
                .one_or_none()
            )
            if current is None:
                connection.exec_driver_sql(
                    "INSERT INTO runtime_session (session_id, provider_key, installation_id, identity_kind, identity_value, first_observed_at, last_observed_at, current_observation_id, correlation_state, account_id, current_decision_id, record_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unresolved', NULL, NULL, 1)",
                    (
                        session_id,
                        identity.provider_key,
                        identity.installation_id,
                        identity.identity_kind,
                        identity.identity_value,
                        observed_text,
                        observed_text,
                        session_item.observation_id,
                    ),
                )
                version = 1
            else:
                version = int(current["record_version"])
                if observed_text >= str(current["last_observed_at"]):
                    version += 1
                    connection.exec_driver_sql(
                        "UPDATE runtime_session SET last_observed_at=?, current_observation_id=?, record_version=? WHERE session_id=?",
                        (
                            observed_text,
                            session_item.observation_id,
                            version,
                            session_id,
                        ),
                    )
            connection.exec_driver_sql(
                "INSERT INTO runtime_session_observation (observation_id, session_id, collection_run_id, source_observation_id, observed_at, collected_at, stored_at, source_id, source_version, parser_version, provider_version, activity_state, activity_code, activity_reason_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session_item.observation_id,
                    session_id,
                    request.run_id.value,
                    session_item.observation_id,
                    observed_text,
                    _utc_text(provenance.collected_at),
                    stored_text,
                    session_item.source_id,
                    session_item.source_version,
                    session_item.parser_version,
                    session_item.provider_version,
                    session_item.activity_state,
                    session_item.activity_code,
                    session_item.activity_reason_code,
                ),
            )
            observation_ids.append(session_item.observation_id)
            projection_versions[session_id] = version

        for link_item in payload.session_process_links:
            session_id = _session_identifier(link_item.session_identity)
            process_id = _process_identifier(link_item.process_identity)
            if link_item.session_identity not in sessions:
                raise RuntimeRepositoryErrorV1("runtime_link_session_missing")
            current_process = (
                connection.exec_driver_sql(
                    "SELECT provider_key, installation_id "
                    "FROM runtime_process_instance WHERE process_id=?",
                    (process_id,),
                )
                .mappings()
                .one_or_none()
            )
            if current_process is None:
                raise RuntimeRepositoryErrorV1("runtime_link_process_missing")
            if (
                current_process["provider_key"]
                != link_item.session_identity.provider_key
                or current_process["installation_id"]
                != link_item.session_identity.installation_id
            ):
                raise RuntimeRepositoryErrorV1("runtime_link_scope_mismatch")
            existing_link = (
                connection.exec_driver_sql(
                    "SELECT session_id, process_id, relationship_kind, "
                    "evidence_class, certainty, source_id, source_version, "
                    "valid_from FROM runtime_session_process_link WHERE link_id=?",
                    (link_item.link_id,),
                )
                .mappings()
                .one_or_none()
            )
            if existing_link is not None:
                expected = (
                    session_id,
                    process_id,
                    link_item.relationship_kind,
                    link_item.evidence_class,
                    link_item.certainty,
                    link_item.source_id,
                    link_item.source_version,
                    _utc_text(link_item.observed_at),
                )
                actual = (
                    str(existing_link["session_id"]),
                    str(existing_link["process_id"]),
                    str(existing_link["relationship_kind"]),
                    str(existing_link["evidence_class"]),
                    str(existing_link["certainty"]),
                    str(existing_link["source_id"]),
                    str(existing_link["source_version"]),
                    str(existing_link["valid_from"]),
                )
                if actual != expected:
                    raise RuntimeRepositoryErrorV1("runtime_link_conflict")
                observation_ids.append(link_item.link_id)
                continue
            current_primary = connection.exec_driver_sql(
                "SELECT process_id FROM runtime_session_process_link "
                "WHERE session_id=? AND relationship_kind='primary' "
                "AND is_current=1 AND conflict_state='clear' LIMIT 1",
                (session_id,),
            ).scalar_one_or_none()
            if current_primary is not None and str(current_primary) != process_id:
                raise RuntimeRepositoryErrorV1("runtime_link_primary_conflict")
            connection.exec_driver_sql(
                "INSERT INTO runtime_session_process_link "
                "(link_id, session_id, process_id, relationship_kind, "
                "evidence_class, certainty, source_id, source_version, "
                "valid_from, valid_until, is_current, conflict_state) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 1, 'clear')",
                (
                    link_item.link_id,
                    session_id,
                    process_id,
                    link_item.relationship_kind,
                    link_item.evidence_class,
                    link_item.certainty,
                    link_item.source_id,
                    link_item.source_version,
                    _utc_text(link_item.observed_at),
                ),
            )
            observation_ids.append(link_item.link_id)

        for metric_item in payload.metric_observations:
            session_id = _session_identifier(metric_item.session_identity)
            if metric_item.session_identity not in sessions:
                raise RuntimeRepositoryErrorV1("runtime_metric_session_missing")
            metric_process_id = (
                _process_identifier(metric_item.process_identity)
                if metric_item.process_identity is not None
                else None
            )
            connection.exec_driver_sql(
                "INSERT INTO runtime_metric_observation (metric_id, session_id, process_id, collection_run_id, metric_kind, coefficient, scale, unit, scope, measurement_semantics, overlap_class, interval_start, interval_end, observed_at, collected_at, stored_at, source_id, source_version, parser_version, provider_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    metric_item.metric_id,
                    session_id,
                    metric_process_id,
                    request.run_id.value,
                    metric_item.metric_kind,
                    metric_item.coefficient,
                    metric_item.scale,
                    metric_item.unit,
                    metric_item.scope,
                    metric_item.semantics,
                    metric_item.overlap_class,
                    _utc_text(metric_item.interval_start)
                    if metric_item.interval_start is not None
                    else None,
                    _utc_text(metric_item.interval_end)
                    if metric_item.interval_end is not None
                    else None,
                    _utc_text(metric_item.observed_at),
                    _utc_text(provenance.collected_at),
                    stored_text,
                    metric_item.source_id,
                    metric_item.source_version,
                    metric_item.parser_version,
                    metric_item.provider_version,
                ),
            )
            observation_ids.append(metric_item.metric_id)

        for identity, (session_id, observed_at) in sessions.items():
            evidence = tuple(
                evidence_item
                for evidence_item in payload.correlation_evidence
                if evidence_item.session_identity == identity
            )
            for evidence_item in evidence:
                connection.exec_driver_sql(
                    "INSERT INTO runtime_correlation_evidence (evidence_id, session_id, evidence_class, rule_id, account_id, source_id, source_version, reason_code, observed_at, expires_at, conflict_state, is_valid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'clear', 1)",
                    (
                        evidence_item.evidence_id,
                        session_id,
                        evidence_item.evidence_class,
                        evidence_item.rule_id,
                        evidence_item.account_id,
                        evidence_item.source_id,
                        evidence_item.source_version,
                        evidence_item.reason_code,
                        _utc_text(evidence_item.observed_at),
                    ),
                )
                observation_ids.append(evidence_item.evidence_id)
            assert self._correlation_evaluator is not None
            decision = self._correlation_evaluator(identity, evidence)
            evidence_digest = hashlib.sha256(
                "\x1f".join(decision.evidence_ids).encode()
            ).hexdigest()
            prior_version = int(
                connection.exec_driver_sql(
                    "SELECT coalesce(max(decision_version), 0) FROM runtime_session_correlation_decision WHERE session_id=?",
                    (session_id,),
                ).scalar_one()
            )
            decision_id = _stable_identifier(
                session_id,
                evidence_digest,
                decision.state,
                decision.account_id or "",
                str(prior_version + 1),
            )
            connection.exec_driver_sql(
                "UPDATE runtime_session_correlation_decision SET is_current=0, valid_until=? WHERE session_id=? AND is_current=1",
                (_utc_text(observed_at), session_id),
            )
            connection.exec_driver_sql(
                "INSERT INTO runtime_session_correlation_decision (decision_id, session_id, decision_state, account_id, evidence_set_digest, reason_code, decided_at, is_current, decision_version) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
                (
                    decision_id,
                    session_id,
                    decision.state,
                    decision.account_id,
                    evidence_digest,
                    decision.reason_code,
                    _utc_text(observed_at),
                    prior_version + 1,
                ),
            )
            connection.exec_driver_sql(
                "UPDATE runtime_session SET correlation_state=?, account_id=?, current_decision_id=?, record_version=record_version+1 WHERE session_id=?",
                (decision.state, decision.account_id, decision_id, session_id),
            )
            projection_versions[session_id] += 1

        if not observation_ids or not projection_versions:
            raise RuntimeRepositoryErrorV1("runtime_commit_empty")
        producer_sequence = int(
            connection.exec_driver_sql(
                "SELECT coalesce(max(producer_sequence), 0) + 1 FROM runtime_event_outbox"
            ).scalar_one()
        )
        subject_id = sorted(projection_versions)[0]
        stream_sequence = int(
            connection.exec_driver_sql(
                "SELECT coalesce(max(stream_sequence), 0) + 1 FROM runtime_event_outbox WHERE subject_id=?",
                (subject_id,),
            ).scalar_one()
        )
        event_id = _stable_identifier(
            "runtime-committed", request.run_id.value, request.payload_digest
        )
        event_payload = json.dumps(
            {
                "capability_id": request.capability_id,
                "observation_count": len(observation_ids),
                "state": request.terminal_state,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        connection.exec_driver_sql(
            "INSERT INTO runtime_event_outbox (event_id, event_type, event_schema, subject_id, stream_sequence, producer_sequence, correlation_id, causation_id, payload_json, occurred_at, recorded_at, available_at, delivery_state, attempt_count) VALUES (?, 'runtime.committed.v1', 'runtime.committed.v1', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)",
            (
                event_id,
                subject_id,
                stream_sequence,
                producer_sequence,
                provenance.correlation_id.value,
                provenance.operation_id.value,
                event_payload,
                stored_text,
                stored_text,
                stored_text,
            ),
        )
        observation_ids = sorted(set(observation_ids))
        projection_ids = sorted(projection_versions)
        observation_digest = hashlib.sha256(
            "\x1f".join(observation_ids).encode()
        ).hexdigest()
        receipt_id = _identifier()
        fallback_json = json.dumps(
            [
                [item.source_id, item.failure_code]
                for item in provenance.fallback_lineage
            ],
            separators=(",", ":"),
        )
        connection.exec_driver_sql(
            _RECEIPT_INSERT_SQL,
            (
                receipt_id,
                request.run_id.value,
                request.target_generation,
                request.capability_id,
                request.payload_schema,
                request.payload_digest,
                self.CONSUMER_KEY,
                self.CONSUMER_VERSION,
                provenance.provider_key,
                provenance.capability_schema_version,
                provenance.adapter_id,
                provenance.adapter_version,
                provenance.provider_protocol_version,
                provenance.source_id,
                provenance.source_class,
                provenance.mechanism_version,
                provenance.parser_version,
                provenance.provider_version,
                provenance.provider_version_availability.state,
                _utc_text(provenance.observed_at)
                if provenance.observed_at is not None
                else None,
                provenance.observed_at_availability.state,
                _utc_text(provenance.collected_at),
                _utc_text(provenance.freshness_deadline)
                if provenance.freshness_deadline is not None
                else None,
                provenance.freshness_availability.state,
                provenance.freshness_policy_id,
                provenance.precision,
                provenance.confidence,
                provenance.confidence_reason_code,
                provenance.value_kind,
                int(provenance.is_experimental),
                provenance.operation_id.value,
                provenance.correlation_id.value,
                provenance.decision_reference,
                provenance.derivation_method,
                fallback_json,
                json.dumps(provenance.warnings, separators=(",", ":")),
                json.dumps(
                    [item.value for item in provenance.input_observation_ids],
                    separators=(",", ":"),
                ),
                observation_digest,
                json.dumps(observation_ids, separators=(",", ":")),
                json.dumps(projection_ids, separators=(",", ":")),
                json.dumps(
                    [projection_versions[item] for item in projection_ids],
                    separators=(",", ":"),
                ),
                json.dumps([event_id], separators=(",", ":")),
                stored_text,
                stored_text,
                stored_text,
                1,
            ),
        )
        row = (
            connection.exec_driver_sql(
                "SELECT * FROM runtime_ingest_receipt WHERE receipt_id=?", (receipt_id,)
            )
            .mappings()
            .one()
        )
        return _receipt(row)

    def list_processes(
        self,
        provider_key: str | None,
        as_of: datetime,
        page_size: int,
        after_key: str | None = None,
    ) -> tuple[AgentProcessRecordV1, ...]:
        _validate_query(as_of, page_size)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT p.*, s.parent_pid_state, s.parent_pid, "
                            "s.parent_pid_unit, s.parent_pid_reason_code, "
                            "s.user_cpu_state, s.user_cpu_ticks, s.user_cpu_unit, "
                            "s.user_cpu_reason_code, s.system_cpu_state, "
                            "s.system_cpu_ticks, s.system_cpu_unit, "
                            "s.system_cpu_reason_code, s.resident_state, "
                            "s.resident_pages, s.resident_unit, "
                            "s.resident_reason_code, s.thread_state, "
                            "s.thread_count, s.thread_unit, s.thread_reason_code, "
                            "s.kernel_state_state, s.kernel_state, "
                            "s.kernel_state_reason_code, s.clock_ticks_per_second, "
                            "s.page_size_bytes, "
                            + _PROVENANCE_SELECT
                            + " FROM runtime_process_instance AS p "
                            "JOIN runtime_process_snapshot AS s "
                            "ON s.snapshot_id=p.current_snapshot_id "
                            "JOIN runtime_ingest_receipt AS r "
                            "ON r.collection_run_id=s.collection_run_id "
                            "AND r.capability_id='local.process.observation' "
                            "WHERE (? IS NULL OR p.provider_key=?) AND p.first_observed_at<=? "
                            "AND (? IS NULL OR p.last_observed_at < (SELECT last_observed_at FROM runtime_process_instance WHERE process_id=?) "
                            "OR (p.last_observed_at = (SELECT last_observed_at FROM runtime_process_instance WHERE process_id=?) AND p.process_id>?)) "
                            "ORDER BY p.last_observed_at DESC, p.process_id LIMIT ?",
                            (
                                provider_key,
                                provider_key,
                                _utc_text(as_of),
                                after_key,
                                after_key,
                                after_key,
                                after_key,
                                page_size,
                            ),
                        )
                        .mappings()
                        .all()
                    )
            return tuple(self._process_record(row, as_of) for row in rows)
        except RuntimeRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RuntimeRepositoryErrorV1() from None

    @staticmethod
    def _process_record(row: RowMapping, as_of: datetime) -> AgentProcessRecordV1:
        provenance = _provenance(row)
        stored_presence = _presence(row["presence_state"])
        freshness_deadline = provenance.freshness_deadline
        presence = stored_presence
        if stored_presence == "running" and (
            provenance.freshness_availability.state != "available"
            or freshness_deadline is None
            or freshness_deadline < as_of
        ):
            presence = "unknown"
        return AgentProcessRecordV1(
            process_id=OpaqueIdV1(str(row["process_id"])),
            identity=ProcessIdentityV1(
                platform_source=str(row["platform_source"]),
                platform_scope_id=str(row["platform_scope_id"]),
                pid=int(row["pid"]),
                start_time_ticks=int(row["start_time_ticks"]),
            ),
            provider_key=(
                str(row["provider_key"]) if row["provider_key"] is not None else None
            ),
            installation_id=(
                str(row["installation_id"])
                if row["installation_id"] is not None
                else None
            ),
            executable_label=(
                ProcessLabelFieldV1(
                    state="present",
                    value=str(row["executable_label"]),
                    reason_code=None,
                )
                if row["executable_label"] is not None
                else ProcessLabelFieldV1(
                    state="not_found",
                    value=None,
                    reason_code="executable_label_not_found",
                )
            ),
            parent_pid=_process_metric(row, "parent_pid", "parent_pid"),
            user_cpu_ticks=_process_metric(row, "user_cpu", "user_cpu_ticks"),
            system_cpu_ticks=_process_metric(row, "system_cpu", "system_cpu_ticks"),
            resident_pages=_process_metric(row, "resident", "resident_pages"),
            thread_count=_process_metric(row, "thread", "thread_count"),
            kernel_state=ProcessCodeFieldV1(
                state=row["kernel_state_state"],
                value=(
                    str(row["kernel_state"])
                    if row["kernel_state"] is not None
                    else None
                ),
                reason_code=(
                    str(row["kernel_state_reason_code"])
                    if row["kernel_state_reason_code"] is not None
                    else None
                ),
            ),
            clock_ticks_per_second=int(row["clock_ticks_per_second"]),
            page_size_bytes=int(row["page_size_bytes"]),
            provenance=provenance,
            first_observed_at=_utc_value(str(row["first_observed_at"])),
            last_observed_at=_utc_value(str(row["last_observed_at"])),
            presence=presence,
            current_snapshot_id=OpaqueIdV1(str(row["current_snapshot_id"])),
            revision=int(row["record_version"]),
        )

    def list_process_history(
        self, process_id: OpaqueIdV1, as_of: datetime, page_size: int
    ) -> tuple[ProcessHistoryEntryV1, ...]:
        _validate_query(as_of, page_size)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT s.snapshot_id, s.process_id, s.observed_at, "
                            "s.collection_run_id, s.source_id, s.presence_state, "
                            + _PROVENANCE_SELECT
                            + " FROM runtime_process_snapshot AS s "
                            "JOIN runtime_ingest_receipt AS r "
                            "ON r.collection_run_id=s.collection_run_id "
                            "AND r.capability_id='local.process.observation' "
                            "WHERE s.process_id=? AND s.observed_at<=? "
                            "ORDER BY s.observed_at DESC, s.snapshot_id DESC LIMIT ?",
                            (process_id.value, _utc_text(as_of), page_size),
                        )
                        .mappings()
                        .all()
                    )
            return tuple(
                ProcessHistoryEntryV1(
                    snapshot_id=OpaqueIdV1(str(row["snapshot_id"])),
                    process_id=OpaqueIdV1(str(row["process_id"])),
                    observed_at=_utc_value(str(row["observed_at"])),
                    collection_run_id=OpaqueIdV1(str(row["collection_run_id"])),
                    source_id=str(row["source_id"]),
                    presence=row["presence_state"],
                    provenance=_provenance(row),
                )
                for row in rows
            )
        except RuntimeRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RuntimeRepositoryErrorV1() from None

    def list_sessions(
        self,
        provider_key: str | None,
        as_of: datetime,
        page_size: int,
        after_key: str | None = None,
        account_id: OpaqueIdV1 | None = None,
    ) -> tuple[AgentSessionRecordV1, ...]:
        _validate_query(as_of, page_size)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    where = (
                        "WHERE (? IS NULL OR s.provider_key=?) AND "
                        "(? IS NULL OR s.account_id=?) AND "
                        "s.first_observed_at<=? AND (? IS NULL OR "
                        "s.last_observed_at < (SELECT last_observed_at FROM runtime_session WHERE session_id=?) "
                        "OR (s.last_observed_at = (SELECT last_observed_at FROM runtime_session WHERE session_id=?) AND s.session_id>?)) "
                    )
                    parameters: tuple[object, ...] = (
                        provider_key,
                        provider_key,
                        account_id.value if account_id is not None else None,
                        account_id.value if account_id is not None else None,
                        _utc_text(as_of),
                        after_key,
                        after_key,
                        after_key,
                        after_key,
                        page_size,
                    )
                    rows = (
                        connection.exec_driver_sql(
                            _CURRENT_SESSION_SELECT
                            + where
                            + "ORDER BY s.last_observed_at DESC, s.session_id LIMIT ?",
                            parameters,
                        )
                        .mappings()
                        .all()
                    )
            return tuple(self._session_record(row) for row in rows)
        except RuntimeRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RuntimeRepositoryErrorV1() from None

    def get_session(
        self, session_id: OpaqueIdV1, as_of: datetime
    ) -> AgentSessionRecordV1:
        _validate_query(as_of, 1)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            _CURRENT_SESSION_SELECT
                            + "WHERE s.session_id=? AND s.first_observed_at<=? LIMIT 1",
                            (session_id.value, _utc_text(as_of)),
                        )
                        .mappings()
                        .one_or_none()
                    )
            if row is None:
                raise RuntimeRepositoryErrorV1("runtime_subject_not_found")
            return self._session_record(row)
        except RuntimeRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RuntimeRepositoryErrorV1() from None

    def get_session_process_links(
        self, observation_ids: tuple[OpaqueIdV1, ...]
    ) -> tuple[SessionProcessLinkInputV1, ...]:
        """Resolve only exact link IDs already named by an M06 commit receipt."""
        if not observation_ids or len(observation_ids) > 64:
            raise RuntimeRepositoryErrorV1("runtime_query_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = []
                    for observation_id in observation_ids:
                        row = (
                            connection.exec_driver_sql(
                                "SELECT l.*, s.provider_key, s.installation_id, "
                                "s.identity_kind, s.identity_value, "
                                "p.platform_source, p.platform_scope_id, p.pid, "
                                "p.start_time_ticks "
                                "FROM runtime_session_process_link AS l "
                                "JOIN runtime_session AS s ON s.session_id=l.session_id "
                                "JOIN runtime_process_instance AS p "
                                "ON p.process_id=l.process_id WHERE l.link_id=?",
                                (observation_id.value,),
                            )
                            .mappings()
                            .one_or_none()
                        )
                        if row is not None:
                            rows.append(row)
            return tuple(
                SessionProcessLinkInputV1(
                    link_id=str(row["link_id"]),
                    session_identity=SessionIdentityV1(
                        provider_key=str(row["provider_key"]),
                        installation_id=str(row["installation_id"]),
                        identity_kind=str(row["identity_kind"]),
                        identity_value=str(row["identity_value"]),
                    ),
                    process_identity=ProcessIdentityV1(
                        platform_source=str(row["platform_source"]),
                        platform_scope_id=str(row["platform_scope_id"]),
                        pid=int(row["pid"]),
                        start_time_ticks=int(row["start_time_ticks"]),
                    ),
                    relationship_kind=row["relationship_kind"],
                    evidence_class=row["evidence_class"],
                    certainty=row["certainty"],
                    source_id=str(row["source_id"]),
                    source_version=str(row["source_version"]),
                    observed_at=_utc_value(str(row["valid_from"])),
                )
                for row in rows
            )
        except RuntimeRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RuntimeRepositoryErrorV1() from None

    @staticmethod
    def _session_record(row: RowMapping) -> AgentSessionRecordV1:
        return AgentSessionRecordV1(
            session_id=OpaqueIdV1(str(row["session_id"])),
            identity=SessionIdentityV1(
                provider_key=str(row["provider_key"]),
                installation_id=str(row["installation_id"]),
                identity_kind=str(row["identity_kind"]),
                identity_value=str(row["identity_value"]),
            ),
            provenance=_provenance(row),
            first_observed_at=_utc_value(str(row["first_observed_at"])),
            last_observed_at=_utc_value(str(row["last_observed_at"])),
            correlation_state=row["correlation_state"],
            account_id=str(row["account_id"])
            if row["account_id"] is not None
            else None,
            revision=int(row["record_version"]),
        )

    def get_session_topology(
        self,
        root_session_id: OpaqueIdV1,
        as_of: datetime,
        source_limit: int,
    ) -> tuple[SessionTopologySnapshotV1, bool]:
        """Read a bounded topology snapshot that always preserves its root."""

        _validate_query(as_of, source_limit)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    root_row = (
                        connection.exec_driver_sql(
                            _CURRENT_SESSION_SELECT
                            + "WHERE s.session_id=? AND s.first_observed_at<=? LIMIT 1",
                            (root_session_id.value, _utc_text(as_of)),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if root_row is None:
                        raise RuntimeRepositoryErrorV1("runtime_subject_not_found")
                    companion_rows = (
                        connection.exec_driver_sql(
                            _CURRENT_SESSION_SELECT
                            + "WHERE s.session_id<>? AND s.first_observed_at<=? "
                            "ORDER BY s.session_id LIMIT ?",
                            (
                                root_session_id.value,
                                _utc_text(as_of),
                                source_limit,
                            ),
                        )
                        .mappings()
                        .all()
                    )
                    source_truncated = len(companion_rows) >= source_limit
                    session_rows = [root_row, *companion_rows[: source_limit - 1]]
                    session_ids = tuple(str(row["session_id"]) for row in session_rows)
                    placeholders = ",".join("?" for _ in session_ids)
                    link_rows = (
                        connection.exec_driver_sql(
                            "SELECT session_id, process_id, relationship_kind, "
                            "evidence_class, certainty, conflict_state FROM ("
                            "SELECT session_id, process_id, relationship_kind, "
                            "evidence_class, certainty, conflict_state, link_id, "
                            "ROW_NUMBER() OVER (PARTITION BY session_id "
                            "ORDER BY link_id) AS link_rank "
                            "FROM runtime_session_process_link "
                            "WHERE is_current=1 AND valid_from<=? "
                            "AND relationship_kind='primary' "
                            f"AND session_id IN ({placeholders})"
                            ") WHERE link_rank<=2 ORDER BY session_id, link_id",
                            (_utc_text(as_of), *session_ids),
                        )
                        .mappings()
                        .all()
                    )
                    links_by_session: dict[str, list[RowMapping]] = {}
                    for row in link_rows:
                        links_by_session.setdefault(str(row["session_id"]), []).append(
                            row
                        )
                    process_ids = sorted(
                        {
                            str(links[0]["process_id"])
                            for links in links_by_session.values()
                            if len(links) == 1
                            and links[0]["evidence_class"] == "strong"
                            and links[0]["certainty"] == "definitive"
                            and links[0]["conflict_state"] == "clear"
                        }
                    )
                    process_rows: list[RowMapping] = []
                    if process_ids:
                        process_placeholders = ",".join("?" for _ in process_ids)
                        process_rows = list(
                            connection.exec_driver_sql(
                                "SELECT p.*, s.parent_pid_state, s.parent_pid, "
                                "s.parent_pid_unit, s.parent_pid_reason_code, "
                                "s.user_cpu_state, s.user_cpu_ticks, "
                                "s.user_cpu_unit, s.user_cpu_reason_code, "
                                "s.system_cpu_state, s.system_cpu_ticks, "
                                "s.system_cpu_unit, s.system_cpu_reason_code, "
                                "s.resident_state, s.resident_pages, "
                                "s.resident_unit, s.resident_reason_code, "
                                "s.thread_state, s.thread_count, s.thread_unit, "
                                "s.thread_reason_code, s.kernel_state_state, "
                                "s.kernel_state, s.kernel_state_reason_code, "
                                "s.clock_ticks_per_second, s.page_size_bytes, "
                                + _PROVENANCE_SELECT
                                + " FROM runtime_process_instance AS p "
                                "JOIN runtime_process_snapshot AS s "
                                "ON s.snapshot_id=p.current_snapshot_id "
                                "JOIN runtime_ingest_receipt AS r "
                                "ON r.collection_run_id=s.collection_run_id "
                                "AND r.capability_id='local.process.observation' "
                                f"WHERE p.process_id IN ({process_placeholders}) "
                                "AND p.first_observed_at<=? "
                                "ORDER BY p.process_id LIMIT ?",
                                (*process_ids, _utc_text(as_of), source_limit),
                            )
                            .mappings()
                            .all()
                        )

            facts: list[SessionTopologyFactV1] = []
            for row in session_rows:
                session = self._session_record(row)
                links = links_by_session.get(session.session_id.value, [])
                exact = [
                    link
                    for link in links
                    if link["evidence_class"] == "strong"
                    and link["certainty"] == "definitive"
                    and link["conflict_state"] == "clear"
                ]
                if len(links) > 1 or len(exact) > 1:
                    facts.append(
                        SessionTopologyFactV1(
                            session,
                            None,
                            "excluded",
                            "session_process_link_ambiguous",
                        )
                    )
                elif len(exact) == 1 and len(links) == 1:
                    facts.append(
                        SessionTopologyFactV1(
                            session,
                            OpaqueIdV1(str(exact[0]["process_id"])),
                            "eligible",
                            "session_process_link_strong",
                        )
                    )
                elif links:
                    facts.append(
                        SessionTopologyFactV1(
                            session,
                            None,
                            "excluded",
                            "session_process_link_not_strong",
                        )
                    )
                else:
                    facts.append(
                        SessionTopologyFactV1(
                            session,
                            None,
                            "unknown",
                            "session_process_link_missing",
                        )
                    )
            return SessionTopologySnapshotV1(
                sessions=tuple(facts),
                processes=tuple(
                    self._process_record(row, as_of) for row in process_rows
                ),
            ), source_truncated
        except RuntimeRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise RuntimeRepositoryErrorV1() from None
