"""M05 capacity repository over the production file-backed SQLite boundary."""

# ruff: noqa: E501 -- SQL text preserves auditable column and predicate ordering.

import hashlib
import json
import re
import secrets
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV1,
    CapacityAlertConditionQueryV1,
    CapacityCommitReceiptV1,
    CapacityCommitRequestV1,
    CapacityCommitStatusV1,
    CapacityCommittedNoticeV1,
    CapacityHealthViewV1,
    CapacityHistoryPointV1,
    CapacityHistoryQueryV1,
    CapacityObservationProvenanceViewV1,
    CapacitySubjectV1,
    ExactMetricFieldV1,
    InvalidCapacityContractV1,
    QuotaWindowViewV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import (
    EventEnvelopeV1,
    FieldAvailabilityV1,
    OpaqueIdV1,
    QueryAvailabilityV1,
)
from agentmonitor.contracts.events_v1 import DurableEventBatchV1, DurableEventV1
from agentmonitor.modules.capacity.application.ports import (
    CapacityCommittedPayloadPolicyV1,
    ClassifyCapacityProjectionV1,
    current_window_candidate_wins_v1,
    current_window_lifecycle_semantic_v1,
    omitted_current_window_keys_v1,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError


class CapacityRepositoryErrorV1(ValueError):
    """A bounded repository error that never exposes SQL or stored values."""

    def __init__(self, code: str = "capacity_repository_unavailable") -> None:
        self.code = code
        super().__init__(code)


def _identifier() -> str:
    return secrets.token_urlsafe(24)


def _stable_identifier(*values: str) -> str:
    return hashlib.sha256("\x1f".join(values).encode()).hexdigest()


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise CapacityRepositoryErrorV1("capacity_timestamp_invalid")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _utc_value(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _receipt(connection: Connection, row: RowMapping) -> CapacityCommitReceiptV1:
    observation_ids = tuple(
        OpaqueIdV1(str(value))
        for value in connection.exec_driver_sql(
            "SELECT observation_id FROM capacity_commit_receipt_observation "
            "WHERE receipt_id=? ORDER BY ordinal",
            (row["receipt_id"],),
        ).scalars()
    )
    projection_ids_raw = json.loads(str(row["affected_projection_ids_json"]))
    projection_versions_raw = json.loads(str(row["projection_versions_json"]))
    event_ids_raw = json.loads(str(row["event_ids_json"]))
    if (
        not isinstance(projection_ids_raw, list)
        or not all(isinstance(value, str) for value in projection_ids_raw)
        or not isinstance(projection_versions_raw, list)
        or not all(type(value) is int for value in projection_versions_raw)
        or not isinstance(event_ids_raw, list)
        or not all(isinstance(value, str) for value in event_ids_raw)
    ):
        raise CapacityRepositoryErrorV1()
    return CapacityCommitReceiptV1(
        run_id=OpaqueIdV1(str(row["collection_run_id"])),
        target_generation=int(row["target_generation"]),
        capability_id=str(row["capability_id"]),
        payload_schema=str(row["payload_schema"]),
        payload_digest=str(row["payload_digest"]),
        consumer_key=str(row["consumer_key"]),
        consumer_version=str(row["consumer_version"]),
        observation_ids=observation_ids,
        observation_set_digest=str(row["observation_set_digest"]),
        stored_at_start=_utc_value(str(row["stored_at_start"])),
        stored_at_end=_utc_value(str(row["stored_at_end"])),
        affected_projection_ids=tuple(
            OpaqueIdV1(value) for value in projection_ids_raw
        ),
        projection_versions=tuple(projection_versions_raw),
        event_ids=tuple(OpaqueIdV1(value) for value in event_ids_raw),
        stored_at=_utc_value(str(row["stored_at"])),
        receipt_version=int(row["receipt_version"]),
    )


def _field_values(field: ExactMetricFieldV1) -> tuple[object, ...]:
    value = field.value
    return (
        field.availability.state,
        value.amount.coefficient if value is not None else None,
        value.amount.scale if value is not None else None,
        value.unit if value is not None else None,
        field.precision,
        field.confidence,
        field.value_kind,
        field.reason_code,
    )


def _metric_field(row: RowMapping) -> ExactMetricFieldV1:
    value = (
        ExactQuantityV1(
            amount=CanonicalDecimalV1(
                coefficient=str(row["coefficient"]), scale=int(row["scale"])
            ),
            unit=str(row["unit"]),
        )
        if row["coefficient"] is not None
        else None
    )
    return ExactMetricFieldV1(
        availability=FieldAvailabilityV1(row["field_state"]),
        value=value,
        precision=row["precision"],
        confidence=row["confidence"],
        value_kind=row["value_kind"],
        reason_code=(
            str(row["reason_code"]) if row["reason_code"] is not None else None
        ),
    )


def _provenance(row: RowMapping) -> CapacityObservationProvenanceViewV1:
    return CapacityObservationProvenanceViewV1(
        capability_id=str(row["capability_id"]),
        capability_schema_version=str(row["capability_schema_version"]),
        adapter_id=str(row["adapter_id"]),
        adapter_version=str(row["adapter_version"]),
        provider_protocol_version=str(row["provider_protocol_version"]),
        source_id=str(row["source_id"]),
        source_class=row["source_class"],
        mechanism_version=str(row["mechanism_version"]),
        parser_version=(
            str(row["parser_version"]) if row["parser_version"] is not None else None
        ),
        provider_version=(
            str(row["provider_version"])
            if row["provider_version"] is not None
            else None
        ),
        freshness_deadline=(
            _utc_value(str(row["freshness_deadline"]))
            if row["freshness_deadline"] is not None
            else None
        ),
        freshness_policy_id=str(row["freshness_policy_id"]),
        precision=row["provenance_precision"],
        confidence=row["provenance_confidence"],
        confidence_reason_code=str(row["confidence_reason_code"]),
        is_experimental=bool(row["experimental"]),
        decision_reference=str(row["decision_reference"]),
    )


def _quota_window(
    connection: Connection, row: RowMapping, as_of: datetime
) -> QuotaWindowViewV1:
    measures = {
        str(measure["metric_kind"]): _metric_field(measure)
        for measure in connection.exec_driver_sql(
            "SELECT * FROM capacity_quota_measure WHERE observation_id=?",
            (row["observation_id"],),
        ).mappings()
    }
    return QuotaWindowViewV1(
        window_id=OpaqueIdV1(str(row["projection_id"])),
        subject=CapacitySubjectV1(
            provider_key=str(row["provider_key"]),
            installation_id=OpaqueIdV1(str(row["installation_id"])),
            account_id=OpaqueIdV1(str(row["account_id"])),
            resource_id=OpaqueIdV1(str(row["resource_id"])),
        ),
        window_key=str(row["native_window_key"]),
        safe_label=str(row["safe_label"]) if row["safe_label"] is not None else None,
        used=measures["used"],
        remaining=measures["remaining"],
        limit=measures["limit"],
        remaining_ratio=measures["remaining_ratio"],
        provenance=_provenance(row),
        freshness=(
            "conflicted"
            if row["conflict_state"] == "conflicted"
            else "freshness_unknown"
            if row["freshness_deadline"] is None
            else "stale"
            if _utc_value(str(row["freshness_deadline"])) <= as_of
            else "fresh"
        ),
        current_observation_id=OpaqueIdV1(str(row["observation_id"])),
        collection_run_id=OpaqueIdV1(str(row["collection_run_id"])),
        observed_at=(
            _utc_value(str(row["observed_at"]))
            if row["observed_at"] is not None
            else None
        ),
        collected_at=_utc_value(str(row["collected_at"])),
        stored_at=_utc_value(str(row["stored_at"])),
        semantic_role=str(row["semantic_role"]),
        is_constraining=(
            bool(row["is_constraining"]) if row["is_constraining"] is not None else None
        ),
        definition_version=int(row["definition_version"]),
        reset_at=_utc_value(str(row["reset_at"]))
        if row["reset_at"] is not None
        else None,
        reset_precision=row["reset_precision"],
        registry_revision=int(row["registry_revision"]),
        projection_version=int(row["projection_version"]),
        completeness=row["completeness"],
    )


def _has_constraint_metadata(connection: Connection) -> bool:
    return (
        connection.exec_driver_sql(
            "SELECT 1 FROM pragma_table_info('capacity_quota_window_definition') WHERE name='is_constraining'"
        ).scalar_one_or_none()
        is not None
    )


def _quota_metadata_columns(connection: Connection) -> str:
    constraint = "d.is_constraining" if _has_constraint_metadata(connection) else "NULL"
    return (
        "d.semantic_role, d.definition_version, d.reset_precision, o.reset_at, "
        "o.completeness, p.registry_revision, p.record_version AS projection_version, "
        + constraint
        + " AS is_constraining, "
    )


def _delivery_has_proof_columns(connection: Connection) -> bool:
    names = set(
        connection.exec_driver_sql(
            "SELECT name FROM pragma_table_info('capacity_event_delivery') "
            "WHERE name IN ('ack_receipt_id','ack_payload_digest')"
        ).scalars()
    )
    return names == {"ack_receipt_id", "ack_payload_digest"}


def _event_query_valid(consumer_key: str, after_cursor: str | None, limit: int) -> int:
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", consumer_key)
        or type(limit) is not int
        or not 1 <= limit <= 200
        or after_cursor is not None
        and not re.fullmatch(r"[0-9]{1,19}", after_cursor)
    ):
        raise CapacityRepositoryErrorV1("capacity_event_query_invalid")
    sequence = int(after_cursor) if after_cursor is not None else 0
    if not 0 <= sequence <= 9223372036854775807:
        raise CapacityRepositoryErrorV1("capacity_event_query_invalid")
    return sequence


def _event_record(
    connection: Connection, row: RowMapping
) -> DurableEventV1[CapacityCommittedNoticeV1]:
    if (
        row["event_type"] != "capacity.committed.v1"
        or row["event_schema"] != "capacity.committed.v1"
    ):
        raise CapacityRepositoryErrorV1("capacity_event_schema_unsupported")
    versions = (
        connection.exec_driver_sql(
            "SELECT DISTINCT r.consumer_version FROM capacity_commit_receipt r, "
            "json_each(r.event_ids_json) refs WHERE refs.value=?",
            (row["event_id"],),
        )
        .scalars()
        .all()
    )
    if len(versions) != 1:
        raise CapacityRepositoryErrorV1("capacity_event_producer_version_unknown")
    policy = CapacityCommittedPayloadPolicyV1()
    notice = policy.decode(str(row["payload_json"]))
    return DurableEventV1(
        EventEnvelopeV1(
            OpaqueIdV1(str(row["event_id"])),
            str(row["event_type"]),
            _utc_value(str(row["occurred_at"])),
            _utc_value(str(row["recorded_at"])),
            "capacity",
            str(versions[0]),
            OpaqueIdV1(str(row["correlation_id"])),
            OpaqueIdV1(str(row["causation_id"])) if row["causation_id"] else None,
            OpaqueIdV1(str(row["subject_id"])),
        ),
        1,
        str(row["projection_stream_key"]),
        int(row["stream_sequence"]),
        notice,
        policy.digest(notice),
    )


def _current_windows(
    connection: Connection,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    capability_id: str,
    as_of: datetime,
) -> tuple[QuotaWindowViewV1, ...]:
    rows = (
        connection.exec_driver_sql(
            "SELECT "
            + _quota_metadata_columns(connection)
            + "p.projection_id, p.account_id, p.resource_id, p.freshness_state, d.provider_key, "
            "d.installation_id, d.native_window_key, d.safe_label, "
            "o.observation_id, o.collection_run_id, o.observed_at, "
            "o.collected_at, o.stored_at, p.freshness_deadline, "
            "p.capability_id, o.capability_schema_version, "
            "v.adapter_id, v.adapter_version, v.provider_protocol_version, "
            "v.source_id, v.source_class, v.mechanism_version, "
            "v.parser_version, v.provider_version, v.freshness_policy_id, "
            "v.precision AS provenance_precision, v.confidence AS provenance_confidence, "
            "v.confidence_reason_code, v.experimental, v.decision_reference, p.conflict_state FROM "
            "capacity_current_projection AS p JOIN capacity_quota_window_definition AS d ON "
            "d.window_definition_id=p.window_definition_id JOIN capacity_quota_observation AS o ON "
            "o.observation_id=p.current_observation_id JOIN capacity_observation_provenance AS v ON "
            "v.provenance_id=o.provenance_id WHERE p.projection_kind='quota' AND p.account_id=? AND "
            "p.resource_id=? AND p.capability_id=? AND d.lifecycle='active' AND "
            "o.collected_at<=? ORDER BY d.native_window_key",
            (account_id.value, resource_id.value, capability_id, _utc_text(as_of)),
        )
        .mappings()
        .all()
    )
    return tuple(_quota_window(connection, row, as_of) for row in rows)


def _history_point(row: RowMapping, as_of: datetime) -> CapacityHistoryPointV1:
    collected_at = _utc_value(str(row["collected_at"]))
    freshness_deadline = (
        _utc_value(str(row["freshness_deadline"]))
        if row["freshness_deadline"] is not None
        else None
    )
    return CapacityHistoryPointV1(
        observation_id=OpaqueIdV1(str(row["observation_id"])),
        window_id=OpaqueIdV1(str(row["window_id"])),
        window_definition_id=OpaqueIdV1(str(row["window_definition_id"])),
        subject=CapacitySubjectV1(
            provider_key=str(row["provider_key"]),
            installation_id=OpaqueIdV1(str(row["installation_id"])),
            account_id=OpaqueIdV1(str(row["account_id"])),
            resource_id=OpaqueIdV1(str(row["resource_id"])),
        ),
        window_key=str(row["native_window_key"]),
        safe_label=str(row["safe_label"]) if row["safe_label"] is not None else None,
        semantic_role=str(row["semantic_role"]),
        native_unit=(
            str(row["native_unit"]) if row["native_unit"] is not None else None
        ),
        definition_version=int(row["definition_version"]),
        metric=row["metric_kind"],
        series_kind=row["observation_kind"],
        value=_metric_field(row),
        provenance=_provenance(row),
        freshness=(
            "freshness_unknown"
            if freshness_deadline is None
            else "stale"
            if freshness_deadline <= as_of
            else "fresh"
        ),
        completeness=row["completeness"],
        collection_run_id=OpaqueIdV1(str(row["collection_run_id"])),
        derivation_id=(
            OpaqueIdV1(str(row["derivation_id"]))
            if row["derivation_id"] is not None
            else None
        ),
        observed_at=_utc_value(str(row["observed_at"])),
        interval_start=(
            _utc_value(str(row["data_through_start"]))
            if row["data_through_start"] is not None
            else None
        ),
        interval_end=(
            _utc_value(str(row["data_through_end"]))
            if row["data_through_end"] is not None
            else None
        ),
        reset_at=(
            _utc_value(str(row["reset_at"])) if row["reset_at"] is not None else None
        ),
        reset_precision=row["reset_precision"],
        collected_at=collected_at,
        stored_at=_utc_value(str(row["stored_at"])),
    )


class SqliteCapacityRepositoryV1:
    """Commits immutable quota observations and an idempotent durable receipt."""

    CONSUMER_KEY = "capacity"
    CONSUMER_VERSION = "1.0.0"

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref
        self._health_policy = ClassifyCapacityProjectionV1()

    def read_capacity_events(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CapacityCommittedNoticeV1]:
        sequence = _event_query_valid(consumer_key, after_cursor, limit)
        as_of_text = _utc_text(as_of)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    skip_ack = (
                        " AND NOT EXISTS (SELECT 1 FROM capacity_event_delivery d WHERE "
                        "d.event_id=e.event_id AND d.consumer_key=? AND d.state='acknowledged' "
                        "AND d.ack_receipt_id IS NOT NULL AND d.ack_payload_digest IS NOT NULL)"
                        if _delivery_has_proof_columns(connection)
                        else ""
                    )
                    params: tuple[object, ...] = (sequence, as_of_text)
                    if skip_ack:
                        params += (consumer_key,)
                    params += (limit,)
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT e.* FROM capacity_event_outbox e WHERE e.producer_sequence>? "
                            "AND e.available_at<=? AND e.event_type='capacity.committed.v1'"
                            + skip_ack
                            + " ORDER BY e.producer_sequence LIMIT ?",
                            params,
                        )
                        .mappings()
                        .all()
                    )
                    events = tuple(_event_record(connection, row) for row in rows)
            return DurableEventBatchV1(
                events,
                str(rows[-1]["producer_sequence"]) if rows else after_cursor,
                QueryAvailabilityV1(
                    "available", "capacity_event_batch_available", as_of
                ),
            )
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError, KeyError):
            raise CapacityRepositoryErrorV1("capacity_event_read_unavailable") from None

    def acknowledge_capacity_event(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None:
        _event_query_valid(consumer_key, None, 1)
        if not re.fullmatch(r"[a-f0-9]{64}", payload_digest):
            raise CapacityRepositoryErrorV1("capacity_event_digest_invalid")
        as_of_text = _utc_text(as_of)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    if not _delivery_has_proof_columns(connection):
                        raise CapacityRepositoryErrorV1(
                            "capacity_event_proof_schema_required"
                        )
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_event_outbox WHERE event_id=?",
                            (event_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        raise CapacityRepositoryErrorV1("capacity_event_not_found")
                    event = _event_record(connection, row)
                    if _utc_value(str(row["available_at"])) > as_of:
                        raise CapacityRepositoryErrorV1("capacity_event_not_available")
                    previous = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_event_delivery WHERE event_id=? AND consumer_key=?",
                            (event_id.value, consumer_key),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    try:
                        disposition = CapacityCommittedPayloadPolicyV1().acknowledge(
                            actual_digest=event.payload_digest,
                            provided_digest=payload_digest,
                            receipt_id=receipt_id,
                            previous_receipt_id=OpaqueIdV1(
                                str(previous["ack_receipt_id"])
                            )
                            if previous is not None
                            and previous["ack_receipt_id"] is not None
                            else None,
                            previous_digest=str(previous["ack_payload_digest"])
                            if previous is not None
                            and previous["ack_payload_digest"] is not None
                            else None,
                            previously_acknowledged=previous is not None
                            and previous["state"] == "acknowledged",
                        )
                    except InvalidCapacityContractV1 as error:
                        raise CapacityRepositoryErrorV1(error.code) from None
                    if disposition == "duplicate":
                        connection.commit()
                        return
                    connection.exec_driver_sql(
                        "INSERT INTO capacity_event_delivery (event_id,consumer_key,consumer_version,state,"
                        "attempt_count,delivered_at,acknowledged_at,ack_receipt_id,ack_payload_digest) "
                        "VALUES (?,?,?,'acknowledged',1,?,?,?,?) ON CONFLICT(event_id,consumer_key) "
                        "DO UPDATE SET state='acknowledged',attempt_count=capacity_event_delivery.attempt_count+1,"
                        "delivered_at=excluded.delivered_at,acknowledged_at=excluded.acknowledged_at,"
                        "ack_receipt_id=excluded.ack_receipt_id,ack_payload_digest=excluded.ack_payload_digest",
                        (
                            event_id.value,
                            consumer_key,
                            "unknown",
                            as_of_text,
                            as_of_text,
                            receipt_id.value,
                            payload_digest,
                        ),
                    )
                    connection.commit()
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError, KeyError):
            raise CapacityRepositoryErrorV1(
                "capacity_event_acknowledgement_unavailable"
            ) from None

    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> CapacityCommitStatusV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_commit_receipt "
                            "WHERE collection_run_id=? AND capability_id=? "
                            "ORDER BY receipt_version DESC LIMIT 1",
                            (run_id.value, capability_id),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        return CapacityCommitStatusV1(
                            state="not_committed", receipt=None
                        )
                    return CapacityCommitStatusV1(
                        state="committed", receipt=_receipt(connection, row)
                    )
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CapacityRepositoryErrorV1() from None

    def list_quota_windows(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        as_of: datetime,
    ) -> tuple[QuotaWindowViewV1, ...]:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    return _current_windows(
                        connection,
                        account_id,
                        resource_id,
                        capability_id,
                        as_of,
                    )
        except (SqlitePolicyError, SQLAlchemyError, KeyError, ValueError, TypeError):
            raise CapacityRepositoryErrorV1() from None

    def _account_capacity_scopes(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> tuple[tuple[OpaqueIdV1, str], ...]:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT DISTINCT p.resource_id, p.capability_id FROM "
                            "capacity_current_projection p JOIN "
                            "capacity_quota_window_definition d ON "
                            "d.window_definition_id=p.window_definition_id JOIN "
                            "capacity_quota_observation o ON "
                            "o.observation_id=p.current_observation_id WHERE "
                            "p.projection_kind='quota' AND p.account_id=? AND "
                            "d.lifecycle='active' AND o.collected_at<=? ORDER BY p.resource_id, "
                            "p.capability_id LIMIT 100",
                            (account_id.value, _utc_text(as_of)),
                        )
                        .mappings()
                        .all()
                    )
            return tuple(
                (OpaqueIdV1(str(row["resource_id"])), str(row["capability_id"]))
                for row in rows
            )
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CapacityRepositoryErrorV1() from None

    def list_account_quota_windows(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> tuple[QuotaWindowViewV1, ...]:
        return tuple(
            window
            for resource_id, capability_id in self._account_capacity_scopes(
                account_id, as_of
            )
            for window in self.list_quota_windows(
                account_id, resource_id, capability_id, as_of
            )
        )

    def page_account_quota_windows(
        self,
        account_id: OpaqueIdV1,
        as_of: datetime,
        page_size: int,
        after_key: str | None,
    ) -> tuple[QuotaWindowViewV1, ...]:
        return self._page_current_windows(account_id, as_of, page_size, after_key)

    def page_capacity_alert_windows(
        self, query: CapacityAlertConditionQueryV1, page_size: int
    ) -> tuple[QuotaWindowViewV1, ...]:
        return self._page_current_windows(
            query.account_id,
            query.as_of,
            page_size,
            query.after_key,
            resource_id=query.resource_id,
            window_id=query.window_id,
        )

    def _page_current_windows(
        self,
        account_id: OpaqueIdV1,
        as_of: datetime,
        page_size: int,
        after_key: str | None,
        *,
        resource_id: OpaqueIdV1 | None = None,
        window_id: OpaqueIdV1 | None = None,
    ) -> tuple[QuotaWindowViewV1, ...]:
        if type(page_size) is not int or not 1 <= page_size <= 201:
            raise CapacityRepositoryErrorV1("capacity_query_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT "
                            + _quota_metadata_columns(connection)
                            + "p.projection_id, p.account_id, p.resource_id, p.freshness_state, "
                            "d.provider_key, d.installation_id, d.native_window_key, d.safe_label, "
                            "o.observation_id, o.collection_run_id, o.observed_at, o.collected_at, "
                            "o.stored_at, p.freshness_deadline, p.capability_id, "
                            "o.capability_schema_version, v.adapter_id, v.adapter_version, "
                            "v.provider_protocol_version, v.source_id, v.source_class, "
                            "v.mechanism_version, v.parser_version, v.provider_version, "
                            "v.freshness_policy_id, "
                            "v.precision AS provenance_precision, "
                            "v.confidence AS provenance_confidence, "
                            "v.confidence_reason_code, v.experimental, v.decision_reference, "
                            "p.conflict_state FROM "
                            "capacity_current_projection AS p JOIN capacity_quota_window_definition AS d "
                            "ON d.window_definition_id=p.window_definition_id JOIN capacity_quota_observation AS o "
                            "ON o.observation_id=p.current_observation_id JOIN "
                            "capacity_observation_provenance AS v ON "
                            "v.provenance_id=o.provenance_id WHERE p.projection_kind='quota' "
                            "AND p.account_id=? AND d.lifecycle='active' AND o.collected_at<=? AND (? IS NULL OR "
                            "p.resource_id=?) AND (? IS NULL OR p.projection_id=?) AND (? IS NULL OR "
                            "(p.resource_id, d.native_window_key, p.projection_id) > ("
                            "SELECT p2.resource_id, d2.native_window_key, p2.projection_id FROM "
                            "capacity_current_projection p2 JOIN capacity_quota_window_definition d2 "
                            "ON d2.window_definition_id=p2.window_definition_id WHERE p2.projection_id=?)) "
                            "ORDER BY p.resource_id, d.native_window_key, p.projection_id LIMIT ?",
                            (
                                account_id.value,
                                _utc_text(as_of),
                                resource_id.value if resource_id else None,
                                resource_id.value if resource_id else None,
                                window_id.value if window_id else None,
                                window_id.value if window_id else None,
                                after_key,
                                after_key,
                                page_size,
                            ),
                        )
                        .mappings()
                        .all()
                    )
                    return tuple(_quota_window(connection, row, as_of) for row in rows)
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, KeyError, ValueError, TypeError):
            raise CapacityRepositoryErrorV1() from None

    def page_capacity_history(
        self,
        query: CapacityHistoryQueryV1,
        page_size: int,
        *,
        _recent: bool = False,
    ) -> tuple[CapacityHistoryPointV1, ...]:
        """Read one exact immutable quota series without collecting or deriving."""
        if (
            not isinstance(query, CapacityHistoryQueryV1)
            or type(page_size) is not int
            or not 1 <= page_size <= 201
        ):
            raise CapacityRepositoryErrorV1("capacity_query_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT p.projection_id AS window_id, "
                            "d.window_definition_id, d.provider_key, "
                            "d.installation_id, d.account_id, d.resource_id, "
                            "d.native_window_key, d.safe_label, d.semantic_role, "
                            "d.native_unit, d.definition_version, "
                            "d.reset_precision, o.observation_id, "
                            "o.observation_kind, o.completeness, o.observed_at, "
                            "o.reset_at, o.data_through_start, "
                            "o.data_through_end, o.collected_at, o.stored_at, "
                            "o.collection_run_id, o.capability_schema_version, "
                            "m.metric_kind, m.field_state, m.coefficient, m.scale, "
                            "m.unit, m.precision, m.confidence, m.value_kind, "
                            "m.reason_code, m.derivation_id, v.capability_id, "
                            "v.adapter_id, v.adapter_version, "
                            "v.provider_protocol_version, v.source_id, "
                            "v.source_class, v.mechanism_version, "
                            "v.parser_version, v.provider_version, "
                            "v.freshness_deadline, v.freshness_policy_id, "
                            "v.precision AS provenance_precision, "
                            "v.confidence AS provenance_confidence, "
                            "v.confidence_reason_code, v.experimental, "
                            "v.decision_reference FROM "
                            "capacity_quota_window_definition AS d JOIN "
                            "capacity_quota_observation AS o INDEXED BY "
                            "ix_capacity_quota_window_time ON "
                            "o.window_definition_id=d.window_definition_id JOIN "
                            "capacity_quota_measure AS m ON "
                            "m.observation_id=o.observation_id JOIN "
                            "capacity_observation_provenance AS v ON "
                            "v.provenance_id=o.provenance_id JOIN "
                            "capacity_current_projection AS p ON "
                            "p.projection_kind='quota' AND "
                            "p.provider_key=d.provider_key AND "
                            "p.account_id=d.account_id AND "
                            "p.resource_id=d.resource_id AND "
                            "p.capability_id=d.capability_id JOIN "
                            "capacity_quota_window_definition AS current_d ON "
                            "current_d.window_definition_id=p.window_definition_id "
                            "AND current_d.native_window_key=d.native_window_key "
                            "WHERE d.account_id=? AND m.metric_kind=? AND "
                            "o.observation_kind=? AND o.observed_at IS NOT NULL "
                            "AND o.observed_at>=? AND o.observed_at<? AND "
                            "o.stored_at<=? AND (? IS NULL OR d.resource_id=?) "
                            "AND (? IS NULL OR p.projection_id=?) AND "
                            "(? IS NULL OR (o.observed_at, o.observation_id) > "
                            "(SELECT cursor_observation.observed_at, "
                            "cursor_observation.observation_id FROM "
                            "capacity_quota_observation AS cursor_observation "
                            "WHERE cursor_observation.observation_id=? AND "
                            "cursor_observation.observed_at IS NOT NULL)) "
                            + (
                                "ORDER BY o.observed_at DESC, o.observation_id DESC "
                                if _recent
                                else "ORDER BY o.observed_at, o.observation_id "
                            )
                            + "LIMIT ?",
                            (
                                query.subject_id.value,
                                query.metric,
                                query.series_kind,
                                _utc_text(query.range_start),
                                _utc_text(query.range_before),
                                _utc_text(query.as_of),
                                (
                                    query.resource_id.value
                                    if query.resource_id is not None
                                    else None
                                ),
                                (
                                    query.resource_id.value
                                    if query.resource_id is not None
                                    else None
                                ),
                                (
                                    query.window_id.value
                                    if query.window_id is not None
                                    else None
                                ),
                                (
                                    query.window_id.value
                                    if query.window_id is not None
                                    else None
                                ),
                                query.after_key,
                                query.after_key,
                                page_size,
                            ),
                        )
                        .mappings()
                        .all()
                    )
                    return tuple(_history_point(row, query.as_of) for row in rows)
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, KeyError, ValueError, TypeError):
            raise CapacityRepositoryErrorV1() from None

    def recent_capacity_history(
        self,
        query: CapacityHistoryQueryV1,
        page_size: int,
    ) -> tuple[CapacityHistoryPointV1, ...]:
        if query.after_key is not None:
            raise CapacityRepositoryErrorV1("capacity_forecast_cursor_invalid")
        return tuple(
            reversed(self.page_capacity_history(query, page_size, _recent=True))
        )

    def list_account_capacities(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> tuple[AccountCapacityViewV1, ...]:
        results: list[AccountCapacityViewV1] = []
        for resource_id, capability_id in self._account_capacity_scopes(
            account_id, as_of
        ):
            windows = self.list_quota_windows(
                account_id, resource_id, capability_id, as_of
            )
            if not windows:
                continue
            try:
                health = self.get_capacity_health(
                    account_id, resource_id, capability_id, as_of
                )
            except CapacityRepositoryErrorV1 as error:
                if error.code != "capacity_health_not_found":
                    raise
                health = None
            results.append(
                AccountCapacityViewV1(
                    subject=windows[0].subject,
                    windows=windows,
                    health=health,
                )
            )
        return tuple(results)

    def get_capacity_health(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        as_of: datetime,
    ) -> CapacityHealthViewV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_health_projection WHERE "
                            "account_id=? AND resource_id=? AND capability_id=? AND "
                            "evaluated_at<=? LIMIT 1",
                            (
                                account_id.value,
                                resource_id.value,
                                capability_id,
                                _utc_text(as_of),
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        raise CapacityRepositoryErrorV1("capacity_health_not_found")
                    windows = _current_windows(
                        connection,
                        account_id,
                        resource_id,
                        capability_id,
                        as_of,
                    )
                    if not windows:
                        raise CapacityRepositoryErrorV1("capacity_health_not_found")
                    return self._health_policy(windows)
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError):
            raise CapacityRepositoryErrorV1() from None

    def get_account_capacity(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        as_of: datetime,
    ) -> AccountCapacityViewV1:
        windows = self.list_quota_windows(account_id, resource_id, capability_id, as_of)
        if not windows:
            raise CapacityRepositoryErrorV1("capacity_not_found")
        return AccountCapacityViewV1(
            subject=windows[0].subject,
            windows=windows,
            health=self.get_capacity_health(
                account_id, resource_id, capability_id, as_of
            ),
        )

    def commit(self, request: CapacityCommitRequestV1) -> CapacityCommitReceiptV1:
        """Commit an already-collected typed result; perform no provider I/O."""
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    existing = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_commit_receipt WHERE "
                            "collection_run_id=? AND capability_id=?",
                            (
                                request.run_id.value,
                                request.capability_id,
                            ),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if existing is not None:
                        if (
                            existing["target_generation"] != request.target_generation
                            or existing["payload_schema"] != request.payload_schema
                            or existing["payload_digest"] != request.payload_digest
                        ):
                            connection.rollback()
                            raise CapacityRepositoryErrorV1("capacity_commit_conflict")
                        result = _receipt(connection, existing)
                        connection.commit()
                        return result
                    result = self._insert_commit(connection, request)
                    connection.commit()
                    return result
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError):
            raise CapacityRepositoryErrorV1() from None

    def _insert_commit(
        self, connection: Connection, request: CapacityCommitRequestV1
    ) -> CapacityCommitReceiptV1:
        payload = request.payload
        provenance = request.provenance
        if not _has_constraint_metadata(connection):
            raise CapacityRepositoryErrorV1(
                "capacity_projection_metadata_schema_required"
            )
        if (
            payload.subject.provider_key != provenance.provider_key
            or request.capability_id != provenance.capability_id
            or payload.capability_schema_version != provenance.capability_schema_version
        ):
            raise CapacityRepositoryErrorV1("capacity_provenance_mismatch")
        stored_at = datetime.now(UTC)
        stored_text = _utc_text(stored_at)
        provenance_id = _identifier()
        connection.exec_driver_sql(
            "INSERT INTO capacity_observation_provenance "
            "(provenance_id, provider_key, capability_id, "
            "capability_schema_version, adapter_id, adapter_version, "
            "provider_protocol_version, source_id, source_class, "
            "mechanism_version, parser_version, provider_version, value_kind, "
            "precision, confidence, confidence_reason_code, freshness_deadline, "
            "freshness_policy_id, experimental, operation_id, correlation_id, "
            "decision_reference) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                provenance_id,
                provenance.provider_key,
                provenance.capability_id,
                provenance.capability_schema_version,
                provenance.adapter_id,
                provenance.adapter_version,
                provenance.provider_protocol_version,
                provenance.source_id,
                provenance.source_class,
                provenance.mechanism_version,
                provenance.parser_version,
                provenance.provider_version,
                provenance.value_kind,
                provenance.precision,
                provenance.confidence,
                provenance.confidence_reason_code,
                _utc_text(provenance.freshness_deadline)
                if provenance.freshness_deadline is not None
                else None,
                provenance.freshness_policy_id,
                int(provenance.is_experimental),
                provenance.operation_id.value,
                provenance.correlation_id.value,
                provenance.decision_reference,
            ),
        )
        incoming_semantic = provenance.observed_at or provenance.collected_at
        incoming_semantic_text = _utc_text(incoming_semantic)
        if payload.completeness == "complete_scope":
            scoped_current = (
                connection.exec_driver_sql(
                    "SELECT d.window_definition_id,d.provider_key,"
                    "d.installation_id,d.account_id,d.resource_id,d.capability_id,"
                    "d.native_window_key,d.identity_scheme_version,d.lifecycle,"
                    "d.last_observed_at,"
                    "o.observed_at,o.collected_at FROM "
                    "capacity_current_projection p JOIN "
                    "capacity_quota_window_definition d ON "
                    "d.window_definition_id=p.window_definition_id JOIN "
                    "capacity_quota_observation o ON "
                    "o.observation_id=p.current_observation_id WHERE "
                    "p.projection_kind='quota' AND p.provider_key=? AND "
                    "p.installation_id=? AND p.account_id=? AND p.resource_id=? AND "
                    "p.capability_id=? AND d.provider_key=? AND d.installation_id=? "
                    "AND d.account_id=? AND d.resource_id=? AND d.capability_id=? "
                    "AND d.identity_scheme_version=1 AND "
                    "d.lifecycle IN ('active','not_observed_currently') "
                    "ORDER BY d.native_window_key,p.projection_id",
                    (
                        payload.subject.provider_key,
                        payload.subject.installation_id.value,
                        payload.subject.account_id.value,
                        payload.subject.resource_id.value,
                        request.capability_id,
                        payload.subject.provider_key,
                        payload.subject.installation_id.value,
                        payload.subject.account_id.value,
                        payload.subject.resource_id.value,
                        request.capability_id,
                    ),
                )
                .mappings()
                .all()
            )
            scoped_keys = tuple(str(row["native_window_key"]) for row in scoped_current)
            if len(scoped_keys) != len(set(scoped_keys)):
                raise CapacityRepositoryErrorV1("capacity_window_scope_conflict")
            observed_keys = tuple(window.window_key for window in payload.windows)
            for row in scoped_current:
                projected_semantic = _utc_value(
                    str(row["observed_at"] or row["collected_at"])
                )
                lifecycle_semantic = _utc_value(str(row["last_observed_at"]))
                omitted = omitted_current_window_keys_v1(
                    (str(row["native_window_key"]),),
                    observed_keys,
                    completeness=payload.completeness,
                    current_lifecycle=row["lifecycle"],
                    current_semantic_at=max(
                        projected_semantic,
                        lifecycle_semantic,
                    ),
                    incoming_semantic_at=incoming_semantic,
                    identity_scheme_proven=row["identity_scheme_version"] == 1,
                    current_scope=(
                        str(row["provider_key"]),
                        str(row["installation_id"]),
                        str(row["account_id"]),
                        str(row["resource_id"]),
                        str(row["capability_id"]),
                        int(row["identity_scheme_version"]),
                    ),
                    incoming_scope=(
                        payload.subject.provider_key,
                        payload.subject.installation_id.value,
                        payload.subject.account_id.value,
                        payload.subject.resource_id.value,
                        request.capability_id,
                        1,
                    ),
                )
                if omitted:
                    updated = connection.exec_driver_sql(
                        "UPDATE capacity_quota_window_definition SET "
                        "lifecycle='not_observed_currently',last_observed_at=?,"
                        "updated_at=? WHERE "
                        "window_definition_id=? AND "
                        "lifecycle IN ('active','not_observed_currently')",
                        (
                            incoming_semantic_text,
                            stored_text,
                            row["window_definition_id"],
                        ),
                    )
                    if updated.rowcount != 1:
                        raise CapacityRepositoryErrorV1(
                            "capacity_window_lifecycle_conflict"
                        )
        observation_ids: list[OpaqueIdV1] = []
        projection_ids: list[str] = []
        for window in payload.windows:
            native_unit = next(
                (
                    field.value.unit
                    for field in (window.used, window.remaining, window.limit)
                    if field.value is not None
                ),
                None,
            )
            observed_text = incoming_semantic_text
            reset_text = (
                _utc_text(window.reset_at) if window.reset_at is not None else None
            )
            safe_label_state = (
                "available" if window.safe_label is not None else "unknown"
            )
            projection_key = _stable_identifier(
                "quota",
                payload.subject.provider_key,
                payload.subject.account_id.value,
                payload.subject.resource_id.value,
                request.capability_id,
                window.window_key,
                "quota_window",
            )
            projection_id = _stable_identifier("current", projection_key)
            current = (
                connection.exec_driver_sql(
                    "SELECT p.current_observation_id, o.observed_at, o.collected_at, "
                    "o.payload_digest FROM capacity_current_projection AS p JOIN "
                    "capacity_quota_observation AS o ON "
                    "o.observation_id=p.current_observation_id WHERE p.projection_key=?",
                    (projection_key,),
                )
                .mappings()
                .one_or_none()
            )
            current_semantic = (
                _utc_value(str(current["observed_at"] or current["collected_at"]))
                if current is not None
                else None
            )
            latest_definition = (
                connection.exec_driver_sql(
                    "SELECT *,MAX(last_observed_at) OVER () AS "
                    "lifecycle_semantic_at FROM "
                    "capacity_quota_window_definition WHERE "
                    "provider_key=? AND resource_id=? AND capability_id=? AND "
                    "identity_scheme_version=1 "
                    "AND native_window_key=? ORDER BY definition_version DESC LIMIT 1",
                    (
                        payload.subject.provider_key,
                        payload.subject.resource_id.value,
                        request.capability_id,
                        window.window_key,
                    ),
                )
                .mappings()
                .one_or_none()
            )
            definition_lifecycle_semantic = (
                _utc_value(str(latest_definition["lifecycle_semantic_at"]))
                if latest_definition is not None
                else None
            )
            candidate_is_current = current_window_candidate_wins_v1(
                current_semantic_at=current_semantic,
                lifecycle_semantic_at=definition_lifecycle_semantic,
                incoming_semantic_at=incoming_semantic,
            )
            same_semantics = latest_definition is not None and all(
                (
                    latest_definition["installation_id"]
                    == payload.subject.installation_id.value,
                    latest_definition["account_id"] == payload.subject.account_id.value,
                    latest_definition["safe_label"] == window.safe_label,
                    latest_definition["safe_label_state"] == safe_label_state,
                    latest_definition["semantic_role"] == window.semantic_role,
                    latest_definition["native_unit"] == native_unit,
                    latest_definition["reset_at"] == reset_text,
                    latest_definition["reset_precision"] == window.reset_precision,
                    latest_definition["is_constraining"] == int(window.is_constraining),
                )
            )
            if same_semantics and latest_definition is not None:
                window_definition_id = str(latest_definition["window_definition_id"])
                definition_version = int(latest_definition["definition_version"])
                last_observed_at = current_window_lifecycle_semantic_v1(
                    definition_lifecycle_semantic,
                    incoming_semantic,
                )
                if last_observed_at is None:
                    raise CapacityRepositoryErrorV1(
                        "capacity_window_lifecycle_conflict"
                    )
                connection.exec_driver_sql(
                    "UPDATE capacity_quota_window_definition SET "
                    "last_observed_at=?,lifecycle=?,updated_at=? WHERE "
                    "window_definition_id=?",
                    (
                        _utc_text(last_observed_at),
                        "active"
                        if candidate_is_current
                        else str(latest_definition["lifecycle"]),
                        stored_text,
                        window_definition_id,
                    ),
                )
            else:
                definition_version = (
                    int(latest_definition["definition_version"]) + 1
                    if latest_definition is not None
                    else 1
                )
                window_definition_id = _stable_identifier(
                    payload.subject.provider_key,
                    payload.subject.account_id.value,
                    payload.subject.resource_id.value,
                    request.capability_id,
                    window.window_key,
                    str(definition_version),
                )
                definition_last_observed_at = current_window_lifecycle_semantic_v1(
                    current_semantic,
                    definition_lifecycle_semantic,
                    incoming_semantic,
                )
                if definition_last_observed_at is None:
                    raise CapacityRepositoryErrorV1(
                        "capacity_window_lifecycle_conflict"
                    )
                connection.exec_driver_sql(
                    "INSERT INTO capacity_quota_window_definition "
                    "(window_definition_id, provider_key, installation_id, "
                    "account_id, resource_id, capability_id, "
                    "identity_scheme_version, native_window_key, "
                    "definition_version, lifecycle, safe_label, safe_label_state, "
                    "semantic_role, native_unit, window_start, window_end, reset_at, "
                    "renewal_semantic, reset_precision, timezone_precision, "
                    "provider_timezone, extension_schema_ref, first_observed_at, "
                    "last_observed_at, decision_reference, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, "
                    "NULL, NULL, ?, 'provider_native', ?, 'unknown', NULL, NULL, "
                    "?, ?, ?, ?, ?)",
                    (
                        window_definition_id,
                        payload.subject.provider_key,
                        payload.subject.installation_id.value,
                        payload.subject.account_id.value,
                        payload.subject.resource_id.value,
                        request.capability_id,
                        window.window_key,
                        definition_version,
                        "active" if candidate_is_current else "not_observed_currently",
                        window.safe_label,
                        safe_label_state,
                        window.semantic_role,
                        native_unit,
                        reset_text,
                        window.reset_precision,
                        observed_text,
                        _utc_text(definition_last_observed_at),
                        provenance.decision_reference,
                        stored_text,
                        stored_text,
                    ),
                )
                connection.exec_driver_sql(
                    "UPDATE capacity_quota_window_definition SET is_constraining=? WHERE window_definition_id=?",
                    (int(window.is_constraining), window_definition_id),
                )
            observation_id = OpaqueIdV1(_identifier())
            observation_ids.append(observation_id)
            connection.exec_driver_sql(
                "INSERT INTO capacity_quota_observation "
                "(observation_id, window_definition_id, definition_version, "
                "account_id, resource_id, observation_kind, completeness, "
                "provider_status_state, provider_status_code, observed_at, "
                "reset_at, data_through_start, data_through_end, collected_at, "
                "stored_at, provenance_id, collection_run_id, payload_digest, "
                "capability_schema_version, current_candidate, invalidation_reason) "
                "VALUES (?, ?, ?, ?, ?, 'poll_snapshot', ?, 'available', NULL, ?, "
                "?, NULL, NULL, ?, ?, ?, ?, ?, ?, 1, NULL)",
                (
                    observation_id.value,
                    window_definition_id,
                    definition_version,
                    payload.subject.account_id.value,
                    payload.subject.resource_id.value,
                    (
                        "complete"
                        if payload.completeness == "complete_scope"
                        else "partial"
                    ),
                    _utc_text(provenance.observed_at)
                    if provenance.observed_at is not None
                    else None,
                    _utc_text(window.reset_at) if window.reset_at is not None else None,
                    _utc_text(provenance.collected_at),
                    stored_text,
                    provenance_id,
                    request.run_id.value,
                    request.payload_digest,
                    payload.capability_schema_version,
                ),
            )
            for metric_kind, field in (
                ("used", window.used),
                ("remaining", window.remaining),
                ("limit", window.limit),
                ("remaining_ratio", window.remaining_ratio),
            ):
                connection.exec_driver_sql(
                    "INSERT INTO capacity_quota_measure "
                    "(observation_id, metric_kind, field_state, coefficient, scale, "
                    "unit, precision, confidence, value_kind, reason_code, "
                    "derivation_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (observation_id.value, metric_kind, *_field_values(field)),
                )
            projection_ids.append(projection_id)
            freshness_state = (
                "stale"
                if provenance.freshness_availability.state == "stale"
                else "fresh"
                if provenance.freshness_deadline is not None
                else "freshness_unknown"
            )
            if candidate_is_current:
                connection.exec_driver_sql(
                    "INSERT INTO capacity_current_projection "
                    "(projection_id, projection_key, projection_kind, provider_key, "
                    "installation_id, account_id, resource_id, capability_id, "
                    "window_definition_id, "
                    "budget_definition_id, metric_key, definition_version, "
                    "current_observation_id, collection_run_id, target_generation, "
                    "freshness_state, freshness_deadline, completeness, "
                    "conflict_state, registry_revision, source_generation, "
                    "projection_policy_id, projection_policy_version, evaluated_at, "
                    "updated_at, projected_at, record_version) VALUES "
                    "(?, ?, 'quota', ?, ?, ?, ?, ?, ?, NULL, 'quota_window', ?, ?, ?, "
                    "?, ?, ?, ?, 'none', ?, ?, 'capacity-current-v1', '1.0.0', ?, "
                    "?, ?, 1) ON CONFLICT(projection_key) DO UPDATE SET "
                    "window_definition_id=excluded.window_definition_id, "
                    "current_observation_id=excluded.current_observation_id, "
                    "collection_run_id=excluded.collection_run_id, "
                    "target_generation=excluded.target_generation, "
                    "freshness_state=excluded.freshness_state, "
                    "freshness_deadline=excluded.freshness_deadline, "
                    "completeness=excluded.completeness, conflict_state='none', "
                    "registry_revision=excluded.registry_revision, "
                    "source_generation=excluded.source_generation, "
                    "evaluated_at=excluded.evaluated_at, "
                    "updated_at=excluded.updated_at, "
                    "projected_at=excluded.projected_at, "
                    "record_version=capacity_current_projection.record_version+1",
                    (
                        projection_id,
                        projection_key,
                        payload.subject.provider_key,
                        payload.subject.installation_id.value,
                        payload.subject.account_id.value,
                        payload.subject.resource_id.value,
                        request.capability_id,
                        window_definition_id,
                        definition_version,
                        observation_id.value,
                        request.run_id.value,
                        request.target_generation,
                        freshness_state,
                        _utc_text(provenance.freshness_deadline)
                        if provenance.freshness_deadline is not None
                        else None,
                        (
                            "complete"
                            if payload.completeness == "complete_scope"
                            else "partial"
                        ),
                        payload.registry_revision,
                        request.target_generation,
                        stored_text,
                        stored_text,
                        stored_text,
                    ),
                )
            elif current is not None and (
                current_semantic == incoming_semantic
                and current["payload_digest"] != request.payload_digest
            ):
                connection.exec_driver_sql(
                    "UPDATE capacity_current_projection SET "
                    "conflict_state='conflicted', evaluated_at=?, updated_at=?, "
                    "record_version=record_version+1 WHERE projection_key=?",
                    (stored_text, stored_text, projection_key),
                )
        current_windows = _current_windows(
            connection,
            payload.subject.account_id,
            payload.subject.resource_id,
            request.capability_id,
            stored_at,
        )
        health = self._health_policy(current_windows)
        policy = self._health_policy.policy
        constraining_definition = (
            connection.exec_driver_sql(
                "SELECT window_definition_id FROM capacity_current_projection WHERE projection_id=?",
                (health.constraining_window_id,),
            ).scalar_one_or_none()
            if health.constraining_window_id is not None
            else None
        )
        deadlines = tuple(
            window.provenance.freshness_deadline for window in current_windows
        )
        valid_until = (
            min(deadline for deadline in deadlines if deadline is not None)
            if deadlines and all(deadline is not None for deadline in deadlines)
            else None
        )
        health_projection_id = _stable_identifier(
            "health",
            payload.subject.provider_key,
            payload.subject.account_id.value,
            payload.subject.resource_id.value,
            request.capability_id,
        )
        columns = (
            "health_projection_id",
            "provider_key",
            "account_id",
            "resource_id",
            "capability_id",
            "subject_scope_kind",
            "subject_scope_id",
            "health_state",
            "completeness",
            "freshness_state",
            "constraining_window_definition_id",
            "constraining_resource_id",
            "policy_id",
            "policy_version",
            "constrained_coefficient",
            "constrained_scale",
            "critical_coefficient",
            "critical_scale",
            "availability_signal_id",
            "availability_signal_generation",
            "input_set_digest",
            "derivation_id",
            "explanation_codes_json",
            "evaluated_at",
            "valid_until",
            "updated_at",
            "projected_at",
            "record_version",
        )
        input_digest = hashlib.sha256(
            "\x1f".join(
                sorted(
                    window.current_observation_id.value for window in current_windows
                )
            ).encode()
        ).hexdigest()
        values = (
            health_projection_id,
            payload.subject.provider_key,
            payload.subject.account_id.value,
            payload.subject.resource_id.value,
            request.capability_id,
            "resource",
            payload.subject.resource_id.value,
            health.state,
            health.completeness,
            health.freshness,
            constraining_definition,
            payload.subject.resource_id.value if constraining_definition else None,
            policy.policy_id,
            policy.policy_version,
            policy.constrained_remaining_ratio.coefficient,
            policy.constrained_remaining_ratio.scale,
            policy.critical_remaining_ratio.coefficient,
            policy.critical_remaining_ratio.scale,
            None,
            None,
            input_digest,
            None,
            json.dumps(health.explanation_codes, separators=(",", ":")),
            stored_text,
            _utc_text(valid_until) if valid_until else None,
            stored_text,
            stored_text,
            1,
        )
        updates = ", ".join(column + "=excluded." + column for column in columns[7:-1])
        connection.exec_driver_sql(
            "INSERT INTO capacity_health_projection ("
            + ", ".join(columns)
            + ") VALUES ("
            + ", ".join("?" for _ in columns)
            + ") ON CONFLICT(provider_key, account_id, resource_id, capability_id) DO UPDATE SET "
            + updates
            + ", record_version=capacity_health_projection.record_version+1",
            values,
        )
        producer_sequence = int(
            connection.exec_driver_sql(
                "SELECT coalesce(max(producer_sequence), 0) + 1 "
                "FROM capacity_event_outbox"
            ).scalar_one()
        )
        stream_key = _stable_identifier("capacity", payload.subject.resource_id.value)
        stream_sequence = int(
            connection.exec_driver_sql(
                "SELECT coalesce(max(stream_sequence), 0) + 1 "
                "FROM capacity_event_outbox WHERE projection_stream_key=?",
                (stream_key,),
            ).scalar_one()
        )
        event_id = _stable_identifier(
            "capacity-committed", request.run_id.value, request.payload_digest
        )
        event_payload = json.dumps(
            {
                "capability_id": request.capability_id,
                "projection_count": len(projection_ids),
                "state": request.terminal_state,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        connection.exec_driver_sql(
            "INSERT INTO capacity_event_outbox "
            "(event_id, event_type, event_schema, projection_stream_key, "
            "stream_sequence, subject_id, subject_version, producer_sequence, "
            "correlation_id, causation_id, payload_json, occurred_at, recorded_at, "
            "available_at) VALUES (?, 'capacity.committed.v1', "
            "'capacity.committed.v1', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                stream_key,
                stream_sequence,
                payload.subject.resource_id.value,
                request.target_generation,
                producer_sequence,
                provenance.correlation_id.value,
                provenance.operation_id.value,
                event_payload,
                stored_text,
                stored_text,
                stored_text,
            ),
        )
        receipt_id = _identifier()
        observation_set_digest = hashlib.sha256(
            "\x1f".join(sorted(item.value for item in observation_ids)).encode()
        ).hexdigest()
        projection_versions = [
            int(
                connection.exec_driver_sql(
                    "SELECT record_version FROM capacity_current_projection "
                    "WHERE projection_id=?",
                    (projection_id,),
                ).scalar_one()
            )
            for projection_id in projection_ids
        ]
        connection.exec_driver_sql(
            "INSERT INTO capacity_commit_receipt "
            "(receipt_id, collection_run_id, target_generation, capability_id, "
            "payload_schema, payload_digest, consumer_key, consumer_version, "
            "observation_set_digest, stored_at_start, stored_at_end, stored_at, "
            "created_at, conflict_state, conflict_reason, "
            "affected_projection_ids_json, projection_versions_json, event_ids_json, "
            "receipt_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, "
            "NULL, ?, ?, ?, 1)",
            (
                receipt_id,
                request.run_id.value,
                request.target_generation,
                request.capability_id,
                request.payload_schema,
                request.payload_digest,
                self.CONSUMER_KEY,
                self.CONSUMER_VERSION,
                observation_set_digest,
                stored_text,
                stored_text,
                stored_text,
                stored_text,
                json.dumps(projection_ids, separators=(",", ":")),
                json.dumps(projection_versions, separators=(",", ":")),
                json.dumps([event_id], separators=(",", ":")),
            ),
        )
        for ordinal, observation_id in enumerate(observation_ids):
            connection.exec_driver_sql(
                "INSERT INTO capacity_commit_receipt_observation "
                "(receipt_id, ordinal, observation_kind, observation_id) "
                "VALUES (?, ?, 'quota', ?)",
                (receipt_id, ordinal, observation_id.value),
            )
        return CapacityCommitReceiptV1(
            run_id=request.run_id,
            target_generation=request.target_generation,
            capability_id=request.capability_id,
            payload_schema=request.payload_schema,
            payload_digest=request.payload_digest,
            consumer_key=self.CONSUMER_KEY,
            consumer_version=self.CONSUMER_VERSION,
            observation_ids=tuple(observation_ids),
            observation_set_digest=observation_set_digest,
            stored_at_start=stored_at,
            stored_at_end=stored_at,
            affected_projection_ids=tuple(
                OpaqueIdV1(projection_id) for projection_id in projection_ids
            ),
            projection_versions=tuple(projection_versions),
            event_ids=(OpaqueIdV1(event_id),),
            stored_at=stored_at,
            receipt_version=1,
        )
