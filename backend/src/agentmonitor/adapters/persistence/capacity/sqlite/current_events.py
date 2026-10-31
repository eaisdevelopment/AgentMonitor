"""Closed M05 commit/forecast/availability event union and durable proof adapter."""

# ruff: noqa: E501 -- SQL and closed event keys stay auditable.

import hashlib
import json
import re
from datetime import datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    CapacityRepositoryErrorV1,
    _delivery_has_proof_columns,
    _event_query_valid,
    _event_record,
    _utc_text,
    _utc_value,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityAvailabilityChangedV1,
    CapacityForecastChangedV1,
    CapacityProjectionEventPayloadV1,
)
from agentmonitor.contracts.common_v1 import (
    EventEnvelopeV1,
    OpaqueIdV1,
    QueryAvailabilityV1,
)
from agentmonitor.contracts.events_v1 import DurableEventBatchV1, DurableEventV1
from agentmonitor.modules.capacity.domain.events import (
    capacity_event_acknowledgement_v1,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_REASON = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_STATES = {
    "capacity.forecast.changed.v1": {
        "available",
        "insufficient_input",
        "not_applicable",
        "stale",
        "conflicted",
    },
    "capacity.availability.changed.v1": {
        "available",
        "unavailable",
        "blocked",
        "reauthentication_required",
        "unknown",
        "unsupported",
        "stale",
        "withheld_or_denied",
    },
}
_TRANSITIONS = {
    "capacity.forecast.changed.v1": {
        "active",
        "invalidated",
        "recovered",
        "not_evaluable",
    },
    "capacity.availability.changed.v1": {"active", "recovered", "not_evaluable"},
}


def _decode_projection_event(
    connection: Connection, row: RowMapping
) -> DurableEventV1[CapacityProjectionEventPayloadV1]:
    if row["event_type"] == "capacity.committed.v1":
        original = _event_record(connection, row)
        return DurableEventV1(
            original.envelope,
            original.event_schema_major,
            original.stream_key,
            original.stream_sequence,
            original.payload,
            original.payload_digest,
        )
    event_type = str(row["event_type"])
    if (
        event_type not in _STATES
        or row["event_schema"] != event_type
        or row.get("producer_version") is None
    ):
        raise CapacityRepositoryErrorV1("capacity_projection_event_schema_unsupported")
    encoded = str(row["payload_json"])
    if len(encoded) > 4096:
        raise CapacityRepositoryErrorV1("capacity_projection_event_payload_invalid")
    try:
        value = json.loads(encoded)
        if not isinstance(value, dict) or encoded != json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ):
            raise ValueError("noncanonical")
        subject_key = (
            "window_id" if event_type == "capacity.forecast.changed.v1" else "stream_id"
        )
        if (
            set(value)
            != {
                subject_key,
                "previous_state",
                "current_state",
                "transition",
                "generation",
                "source_generation",
                "input_set_digest",
                "reason_code",
                "latest_observation_id",
                "occurred_at",
            }
            or value[subject_key] != row["subject_id"]
            or value["current_state"] not in _STATES[event_type]
            or value["transition"] not in _TRANSITIONS[event_type]
            or type(value["generation"]) is not int
            or value["generation"] != row["subject_version"]
            or type(value["source_generation"]) is not int
            or value["source_generation"] < 1
            or not isinstance(value["input_set_digest"], str)
            or _DIGEST.fullmatch(value["input_set_digest"]) is None
            or not isinstance(value["reason_code"], str)
            or _REASON.fullmatch(value["reason_code"]) is None
            or value["occurred_at"] != row["occurred_at"]
        ):
            raise ValueError("invalid")
        if (
            value["previous_state"] is not None
            and value["previous_state"] not in _STATES[event_type]
        ):
            raise ValueError("previous_state")
        observation_id = (
            OpaqueIdV1(value["latest_observation_id"])
            if value["latest_observation_id"] is not None
            else None
        )
        values = (
            OpaqueIdV1(value[subject_key]),
            value["previous_state"],
            value["current_state"],
            value["transition"],
            value["generation"],
            value["source_generation"],
            value["input_set_digest"],
            value["reason_code"],
            observation_id,
            _utc_value(value["occurred_at"]),
        )
        payload: CapacityProjectionEventPayloadV1 = (
            CapacityForecastChangedV1(*values)
            if event_type == "capacity.forecast.changed.v1"
            else CapacityAvailabilityChangedV1(*values)
        )
        return DurableEventV1(
            EventEnvelopeV1(
                OpaqueIdV1(str(row["event_id"])),
                event_type,
                _utc_value(str(row["occurred_at"])),
                _utc_value(str(row["recorded_at"])),
                "capacity",
                str(row["producer_version"]),
                OpaqueIdV1(str(row["correlation_id"])),
                OpaqueIdV1(str(row["causation_id"])) if row["causation_id"] else None,
                OpaqueIdV1(str(row["subject_id"])),
            ),
            1,
            str(row["projection_stream_key"]),
            int(row["stream_sequence"]),
            payload,
            hashlib.sha256(encoded.encode()).hexdigest(),
        )
    except (TypeError, ValueError, KeyError, IndexError):
        raise CapacityRepositoryErrorV1(
            "capacity_projection_event_payload_invalid"
        ) from None


class SqliteCapacityProjectionEventRepositoryV1:
    """Producer-owned outbox; composition checks consumer receipt before ack."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def read_capacity_projection_events(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CapacityProjectionEventPayloadV1]:
        sequence = _event_query_valid(consumer_key, after_cursor, limit)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    proof = _delivery_has_proof_columns(connection)
                    skip = (
                        " AND NOT EXISTS (SELECT 1 FROM capacity_event_delivery d WHERE "
                        "d.event_id=e.event_id AND d.consumer_key=? AND d.state='acknowledged' "
                        "AND d.ack_receipt_id IS NOT NULL AND d.ack_payload_digest IS NOT NULL)"
                        if proof
                        else ""
                    )
                    params: tuple[object, ...] = (sequence, _utc_text(as_of))
                    if proof:
                        params += (consumer_key,)
                    params += (limit,)
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT e.* FROM capacity_event_outbox e WHERE e.producer_sequence>? "
                            "AND e.available_at<=?"
                            + skip
                            + " ORDER BY e.producer_sequence LIMIT ?",
                            params,
                        )
                        .mappings()
                        .all()
                    )
                    return DurableEventBatchV1(
                        tuple(
                            _decode_projection_event(connection, row) for row in rows
                        ),
                        str(rows[-1]["producer_sequence"]) if rows else after_cursor,
                        QueryAvailabilityV1(
                            "available",
                            "capacity_projection_event_batch_available",
                            as_of,
                        ),
                    )
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, TypeError, ValueError, KeyError):
            raise CapacityRepositoryErrorV1(
                "capacity_projection_event_read_unavailable"
            ) from None

    def acknowledge_capacity_projection_event(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None:
        _event_query_valid(consumer_key, None, 1)
        if _DIGEST.fullmatch(payload_digest) is None:
            raise CapacityRepositoryErrorV1("capacity_event_digest_invalid")
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
                    event = _decode_projection_event(connection, row)
                    if _utc_value(str(row["available_at"])) > as_of:
                        raise CapacityRepositoryErrorV1("capacity_event_not_available")
                    prior = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_event_delivery WHERE event_id=? AND consumer_key=?",
                            (event_id.value, consumer_key),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    try:
                        disposition = capacity_event_acknowledgement_v1(
                            actual_digest=event.payload_digest,
                            provided_digest=payload_digest,
                            receipt_id=receipt_id,
                            previous_receipt_id=OpaqueIdV1(str(prior["ack_receipt_id"]))
                            if prior and prior["ack_receipt_id"]
                            else None,
                            previous_digest=str(prior["ack_payload_digest"])
                            if prior and prior["ack_payload_digest"]
                            else None,
                            previously_acknowledged=prior is not None
                            and prior["state"] == "acknowledged",
                        )
                    except ValueError as error:
                        raise CapacityRepositoryErrorV1(str(error)) from None
                    if disposition == "duplicate":
                        connection.commit()
                        return
                    when = _utc_text(as_of)
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
                            when,
                            when,
                            receipt_id.value,
                            payload_digest,
                        ),
                    )
                    connection.commit()
        except CapacityRepositoryErrorV1:
            raise
        except (SqlitePolicyError, SQLAlchemyError, TypeError, ValueError, KeyError):
            raise CapacityRepositoryErrorV1(
                "capacity_projection_event_ack_unavailable"
            ) from None
