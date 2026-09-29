"""M04-owned durable current collector conditions and typed event delivery."""

# ruff: noqa: E501 -- SQL text keeps auditable column and predicate order.

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import cast

from agentmonitor.adapters.persistence._shared.sqlite.core.bounded_read import (
    open_bounded_sqlite_read,
)
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectorAlertConditionV1,
    CollectorAlertQueryV1,
    CollectorConditionReasonV1,
    CollectorFreshnessStateV1,
    CollectorHealthChangedV1,
    CollectorHealthStateV1,
    CollectorRetryCategoryV1,
)
from agentmonitor.contracts.common_v1 import (
    EventEnvelopeV1,
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.contracts.events_v1 import DurableEventBatchV1, DurableEventV1
from agentmonitor.modules.collection_control.domain.alert_conditions import (
    CollectorRunFactV1,
    CollectorSourceSnapshotV1,
    classify_collector_condition_v1,
)

from .condition_writer import (
    CollectorConditionStorageErrorV1,
    _ConditionWriterV1,
    _open_condition_writer,
)

_TABLES = frozenset(
    {
        "collection_schedule",
        "collection_run",
        "collection_run_observation_ref",
        "collection_alert_condition",
        "collection_event_outbox",
        "collection_event_delivery",
    }
)
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_CONSUMER = re.compile(r"[a-z][a-z0-9_.:-]{0,63}\Z")
_COLUMNS = (
    "schedule_id,account_id,provider_key,capability_id,record_version,"
    "health_state,freshness_state,retry_category,latest_run_id,"
    "last_successful_at,freshness_deadline,not_before_at,evaluated_at,reason_code"
)
_RUN_COLUMNS = (
    "run_id,record_version,target_generation,state,completed_at,"
    "provider_outcome_state,retry_disposition,retry_after,"
    "EXISTS(SELECT 1 FROM collection_run_observation_ref r "
    "WHERE r.run_id=collection_run.run_id)"
)


def _text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise CollectorConditionStorageErrorV1()
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _time(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CollectorConditionStorageErrorV1()
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() != timedelta(0):
        raise CollectorConditionStorageErrorV1()
    return result


def _condition(row: tuple[object, ...]) -> CollectorAlertConditionV1:
    return CollectorAlertConditionV1(
        OpaqueIdV1(str(row[0])),
        OpaqueIdV1(str(row[1])) if row[1] is not None else None,
        str(row[2]),
        str(row[3]),
        _integer(row[4]),
        cast(CollectorHealthStateV1, row[5]),
        cast(CollectorFreshnessStateV1, row[6]),
        cast(CollectorRetryCategoryV1, row[7]),
        OpaqueIdV1(str(row[8])) if row[8] is not None else None,
        _time(row[9]),
        _time(row[10]),
        _time(row[11]),
        _required_time(row[12]),
        cast(CollectorConditionReasonV1, row[13]),
    )


def _required_time(value: object) -> datetime:
    result = _time(value)
    if result is None:
        raise CollectorConditionStorageErrorV1()
    return result


def _integer(value: object) -> int:
    if type(value) is not int:
        raise CollectorConditionStorageErrorV1()
    return value


def _run(row: tuple[object, ...] | None) -> CollectorRunFactV1 | None:
    if row is None:
        return None
    return CollectorRunFactV1(
        OpaqueIdV1(str(row[0])),
        _integer(row[1]),
        _integer(row[2]),
        str(row[3]),
        _time(row[4]),
        str(row[5]) if row[5] is not None else None,
        str(row[6]) if row[6] is not None else None,
        _time(row[7]),
        bool(row[8]),
    )


def _payload(
    condition: CollectorAlertConditionV1, previous: tuple[str, str] | None
) -> str:
    return json.dumps(
        {
            "target_id": condition.target_id.value,
            "account_id": condition.account_id.value if condition.account_id else None,
            "provider_key": condition.provider_key,
            "capability_id": condition.capability_id,
            "generation": condition.generation,
            "health_state": condition.health_state,
            "freshness_state": condition.freshness_state,
            "retry_category": condition.retry_category,
            "latest_run_id": condition.latest_run_id.value
            if condition.latest_run_id
            else None,
            "last_successful_at": _text(condition.last_successful_at)
            if condition.last_successful_at
            else None,
            "freshness_deadline": _text(condition.freshness_deadline)
            if condition.freshness_deadline
            else None,
            "not_before_at": _text(condition.not_before_at)
            if condition.not_before_at
            else None,
            "evaluated_at": _text(condition.evaluated_at),
            "reason_code": condition.reason_code,
            "previous_health_state": previous[0] if previous else None,
            "previous_freshness_state": previous[1] if previous else None,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _parse_payload(value: object) -> CollectorHealthChangedV1:
    if not isinstance(value, str) or len(value) > 4096:
        raise CollectorConditionStorageErrorV1()
    data = json.loads(value)
    if not isinstance(data, dict) or set(data) != {
        "target_id",
        "account_id",
        "provider_key",
        "capability_id",
        "generation",
        "health_state",
        "freshness_state",
        "retry_category",
        "latest_run_id",
        "last_successful_at",
        "freshness_deadline",
        "not_before_at",
        "evaluated_at",
        "reason_code",
        "previous_health_state",
        "previous_freshness_state",
    }:
        raise CollectorConditionStorageErrorV1()
    current = _condition(
        (
            data["target_id"],
            data["account_id"],
            data["provider_key"],
            data["capability_id"],
            data["generation"],
            data["health_state"],
            data["freshness_state"],
            data["retry_category"],
            data["latest_run_id"],
            data["last_successful_at"],
            data["freshness_deadline"],
            data["not_before_at"],
            data["evaluated_at"],
            data["reason_code"],
        )
    )
    return CollectorHealthChangedV1(
        data["previous_health_state"], data["previous_freshness_state"], current
    )


def _selection(query: CollectorAlertQueryV1) -> tuple[str, tuple[object, ...]]:
    clauses: list[str] = []
    params: list[object] = []
    for field, value in (
        ("provider_key", query.provider_key),
        ("account_id", query.account_id.value if query.account_id else None),
        ("schedule_id", query.target_id.value if query.target_id else None),
    ):
        if value is not None:
            clauses.append(field + "=?")
            params.append(value)
    if query.after_target_id is not None:
        clauses.append("schedule_id>?")
        params.append(query.after_target_id.value)
    if query.minimum_generation is not None:
        clauses.append("record_version>=?")
        params.append(query.minimum_generation)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), tuple(params)


def _page(
    rows: tuple[tuple[object, ...], ...],
    query: CollectorAlertQueryV1,
    *,
    partial: bool = False,
    forced_next_key: str | None = None,
) -> QueryPageV1[CollectorAlertConditionV1]:
    has_more = len(rows) > query.limit or forced_next_key is not None
    items = tuple(_condition(row) for row in rows[: query.limit])
    # A persisted current reading past its deadline is not a current source
    # generation. The named refresh command will durably advance it.
    old = any(
        item.freshness_state == "current"
        and item.freshness_deadline is not None
        and item.freshness_deadline <= query.as_of
        for item in items
    )
    if old:
        items = tuple(
            item
            for item in items
            if item.freshness_state != "current"
            or item.freshness_deadline is None
            or item.freshness_deadline > query.as_of
        )
        partial = True
    return QueryPageV1(
        items,
        query.limit,
        has_more,
        forced_next_key
        if forced_next_key is not None
        else str(rows[query.limit - 1][0])
        if has_more
        else None,
        QueryAvailabilityV1(
            "partial" if partial else "available",
            "collector_projection_requires_refresh"
            if partial
            else "collector_condition_available",
            query.as_of,
        ),
    )


class SqliteCollectorAlertConditionsV1:
    """Producer-owned M04 adapter; refresh never calls a provider."""

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    async def get_current(
        self, query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]:
        if query.as_of > datetime.now(UTC):
            raise CollectorConditionStorageErrorV1(
                "collector_future_evaluation_invalid"
            )
        where, params = _selection(query)
        try:
            with open_bounded_sqlite_read(
                self._reference, deadline=query.deadline, allowed_tables=_TABLES
            ) as reader:
                rows = reader.fetch_many(
                    "SELECT "
                    + _COLUMNS
                    + ",source_schedule_record_version,"
                    + "(SELECT record_version FROM collection_schedule s "
                    + "WHERE s.schedule_id=collection_alert_condition.schedule_id)"
                    + " FROM collection_alert_condition"
                    + where
                    + " ORDER BY schedule_id LIMIT ?",
                    (*params, query.limit + 1),
                    limit=query.limit + 1,
                )
                # The projection can lag an actual schedule/run; absence is
                # partial, not a fabricated healthy or available condition.
                schedule_where = where.replace("record_version>=?", "1=1")
                schedule_params = (
                    params[:-1] if query.minimum_generation is not None else params
                )
                source_rows = reader.fetch_many(
                    "SELECT schedule_id FROM collection_schedule"
                    + schedule_where
                    + " ORDER BY schedule_id LIMIT ?",
                    (*schedule_params, query.limit + 1),
                    limit=query.limit + 1,
                )
            valid_rows = tuple(
                row
                for row in rows
                if row[14] == row[15] and _required_time(row[12]) <= query.as_of
            )
            visible_ids = {str(row[0]) for row in valid_rows}
            source_ids = {str(row[0]) for row in source_rows}
            return _page(
                valid_rows,
                query,
                partial=bool(source_ids - visible_ids) or len(valid_rows) != len(rows),
            )
        except (SqlitePolicyError, ValueError, TypeError, IndexError, KeyError):
            raise CollectorConditionStorageErrorV1() from None

    async def refresh(
        self, query: CollectorAlertQueryV1
    ) -> QueryPageV1[CollectorAlertConditionV1]:
        if query.as_of > datetime.now(UTC):
            raise CollectorConditionStorageErrorV1(
                "collector_future_evaluation_invalid"
            )
        try:
            with _open_condition_writer(self._reference, query.deadline) as writer:
                schedule_where, schedule_params = _selection(query)
                schedule_where = schedule_where.replace("record_version>=?", "1=1")
                if query.minimum_generation is not None:
                    schedule_params = schedule_params[:-1]
                schedules = writer.rows(
                    "SELECT schedule_id,account_id,provider_key,capability_id,"
                    "record_version,target_generation,state,effective_interval_seconds,"
                    "not_before_at,backoff_kind,last_attempted_run_id "
                    "FROM collection_schedule"
                    + schedule_where
                    + " ORDER BY schedule_id LIMIT ?",
                    (*schedule_params, query.limit + 1),
                    limit=query.limit + 1,
                )
                for schedule in schedules[: query.limit]:
                    self._refresh_one(writer, tuple(schedule), query)
                where, params = _selection(query)
                rows = tuple(
                    tuple(row)
                    for row in writer.rows(
                        "SELECT "
                        + _COLUMNS
                        + " FROM collection_alert_condition"
                        + where
                        + " ORDER BY schedule_id LIMIT ?",
                        (*params, query.limit + 1),
                        limit=query.limit + 1,
                    )
                )
            return _page(
                rows,
                query,
                forced_next_key=(
                    str(schedules[query.limit - 1][0])
                    if len(schedules) > query.limit
                    else None
                ),
                partial=bool(schedules) and not rows,
            )
        except (
            CollectorConditionStorageErrorV1,
            ValueError,
            TypeError,
            IndexError,
            KeyError,
        ):
            raise CollectorConditionStorageErrorV1() from None

    def _refresh_one(
        self,
        writer: _ConditionWriterV1,
        schedule: tuple[object, ...],
        query: CollectorAlertQueryV1,
    ) -> None:
        # Writer stays private to this adapter; only owned M04 tables are used.
        latest = (
            writer.rows(
                "SELECT "
                + _RUN_COLUMNS
                + " FROM collection_run WHERE run_id=? AND schedule_id=? LIMIT 1",
                (schedule[10], schedule[0]),
                limit=1,
            )
            if schedule[10] is not None
            else ()
        )
        success = writer.rows(
            "SELECT " + _RUN_COLUMNS + " FROM collection_run "
            "WHERE schedule_id=? AND target_generation=? AND state='succeeded' "
            "AND completed_at IS NOT NULL AND EXISTS "
            "(SELECT 1 FROM collection_run_observation_ref r WHERE r.run_id=collection_run.run_id) "
            "ORDER BY completed_at DESC, run_id DESC LIMIT 1",
            (schedule[0], schedule[5]),
            limit=1,
        )
        prior = writer.rows(
            "SELECT " + _COLUMNS + ",condition_digest,source_schedule_record_version,"
            "source_latest_run_record_version FROM collection_alert_condition "
            "WHERE schedule_id=? LIMIT 1",
            (schedule[0],),
            limit=1,
        )
        source = CollectorSourceSnapshotV1(
            OpaqueIdV1(str(schedule[0])),
            OpaqueIdV1(str(schedule[1])) if schedule[1] is not None else None,
            str(schedule[2]),
            str(schedule[3]),
            _integer(schedule[4]),
            _integer(schedule[5]),
            str(schedule[6]),
            _integer(schedule[7]),
            _time(schedule[8]),
            str(schedule[9]) if schedule[9] is not None else None,
            _run(tuple(latest[0])) if latest else None,
            _run(tuple(success[0])) if success else None,
        )
        prior_row = tuple(prior[0]) if prior else None
        if prior_row is not None and _required_time(prior_row[12]) > query.as_of:
            raise CollectorConditionStorageErrorV1("collector_evaluation_regressed")
        version = _integer(prior_row[4]) + 1 if prior_row else 1
        current = classify_collector_condition_v1(
            source, generation=version, as_of=query.as_of
        )
        latest_version = source.latest_run.record_version if source.latest_run else None
        semantic = json.dumps(
            (
                source.schedule_record_version,
                latest_version,
                current.health_state,
                current.freshness_state,
                current.retry_category,
                current.latest_run_id.value if current.latest_run_id else None,
                _text(current.last_successful_at)
                if current.last_successful_at
                else None,
                _text(current.freshness_deadline)
                if current.freshness_deadline
                else None,
                _text(current.not_before_at) if current.not_before_at else None,
                current.reason_code,
            ),
            separators=(",", ":"),
            ensure_ascii=True,
        )
        digest = hashlib.sha256(semantic.encode()).hexdigest()
        if prior_row is not None and prior_row[14] == digest:
            return
        writer.execute(
            "INSERT INTO collection_alert_condition "
            "(" + _COLUMNS + ",condition_digest,source_schedule_record_version,"
            "source_latest_run_record_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(schedule_id) DO UPDATE SET "
            "account_id=excluded.account_id,provider_key=excluded.provider_key,"
            "capability_id=excluded.capability_id,record_version=excluded.record_version,"
            "health_state=excluded.health_state,freshness_state=excluded.freshness_state,"
            "retry_category=excluded.retry_category,latest_run_id=excluded.latest_run_id,"
            "last_successful_at=excluded.last_successful_at,"
            "freshness_deadline=excluded.freshness_deadline,not_before_at=excluded.not_before_at,"
            "evaluated_at=excluded.evaluated_at,reason_code=excluded.reason_code,"
            "condition_digest=excluded.condition_digest,"
            "source_schedule_record_version=excluded.source_schedule_record_version,"
            "source_latest_run_record_version=excluded.source_latest_run_record_version",
            (
                source.target_id.value,
                source.account_id.value if source.account_id else None,
                source.provider_key,
                source.capability_id,
                version,
                current.health_state,
                current.freshness_state,
                current.retry_category,
                current.latest_run_id.value if current.latest_run_id else None,
                _text(current.last_successful_at)
                if current.last_successful_at
                else None,
                _text(current.freshness_deadline)
                if current.freshness_deadline
                else None,
                _text(current.not_before_at) if current.not_before_at else None,
                _text(current.evaluated_at),
                current.reason_code,
                digest,
                source.schedule_record_version,
                latest_version,
            ),
        )
        previous = (str(prior_row[5]), str(prior_row[6])) if prior_row else None
        payload = _payload(current, previous)
        stream_id = (
            "collector-condition/"
            + hashlib.sha256(source.target_id.value.encode()).hexdigest()[:40]
        )
        event_id = hashlib.sha256(
            f"{source.target_id.value}\x1fcollector.health_changed.v1\x1f{version}".encode()
        ).hexdigest()
        writer.execute(
            "INSERT INTO collection_event_outbox "
            "(event_id,event_type,event_schema,stream_id,stream_sequence,subject_id,"
            "correlation_id,causation_id,payload_json,occurred_at,recorded_at,available_at) "
            "VALUES (?,'collector.health_changed.v1','collector.health_changed.v1',"
            "?,?,?,?,?,?,?,?,?)",
            (
                event_id,
                stream_id,
                version,
                source.target_id.value,
                query.correlation_id.value,
                None,
                payload,
                _text(query.as_of),
                _text(query.as_of),
                _text(query.as_of),
            ),
        )

    def read_events(
        self,
        consumer_key: str,
        after_cursor: str | None,
        as_of: datetime,
        limit: int = 200,
    ) -> DurableEventBatchV1[CollectorHealthChangedV1]:
        if (
            not _CONSUMER.fullmatch(consumer_key)
            or type(limit) is not int
            or not 1 <= limit <= 200
            or as_of > datetime.now(UTC)
        ):
            raise CollectorConditionStorageErrorV1("collector_event_query_invalid")
        if after_cursor is not None and (
            not after_cursor.isdecimal() or len(after_cursor) > 20
        ):
            raise CollectorConditionStorageErrorV1("collector_event_cursor_invalid")
        try:
            with open_bounded_sqlite_read(
                self._reference,
                deadline=datetime.now(UTC) + timedelta(seconds=2),
                allowed_tables=_TABLES,
            ) as reader:
                rows = reader.fetch_many(
                    "SELECT o.rowid,o.event_id,o.event_type,o.stream_id,o.stream_sequence,"
                    "o.subject_id,o.correlation_id,o.causation_id,o.payload_json,"
                    "o.occurred_at,o.recorded_at,o.available_at,o.event_schema "
                    "FROM collection_event_outbox o WHERE o.rowid>? "
                    "AND o.event_type='collector.health_changed.v1' AND o.available_at<=? "
                    "AND NOT EXISTS (SELECT 1 FROM collection_event_delivery d "
                    "WHERE d.event_id=o.event_id AND d.consumer_key=? "
                    "AND d.state='acknowledged' AND d.consumer_receipt_id IS NOT NULL "
                    "AND d.ack_payload_digest IS NOT NULL) ORDER BY o.rowid LIMIT ?",
                    (int(after_cursor or "0"), _text(as_of), consumer_key, limit),
                    limit=limit,
                )
            events = tuple(self._event(tuple(row)) for row in rows)
            return DurableEventBatchV1(
                events,
                str(rows[-1][0]) if rows else after_cursor,
                QueryAvailabilityV1("available", "collector_events_available", as_of),
            )
        except (
            SqlitePolicyError,
            ValueError,
            TypeError,
            IndexError,
            KeyError,
            json.JSONDecodeError,
        ):
            raise CollectorConditionStorageErrorV1() from None

    @staticmethod
    def _event(row: tuple[object, ...]) -> DurableEventV1[CollectorHealthChangedV1]:
        payload = _parse_payload(row[8])
        expected_stream = (
            "collector-condition/"
            + hashlib.sha256(payload.current.target_id.value.encode()).hexdigest()[:40]
        )
        if (
            row[2] != "collector.health_changed.v1"
            or row[12] != "collector.health_changed.v1"
            or row[3] != expected_stream
            or row[5] != payload.current.target_id.value
            or row[4] != payload.current.generation
            or row[1]
            != hashlib.sha256(
                f"{payload.current.target_id.value}\x1fcollector.health_changed.v1\x1f{payload.current.generation}".encode()
            ).hexdigest()
            or _required_time(row[9]) != payload.current.evaluated_at
        ):
            raise CollectorConditionStorageErrorV1("collector_event_lineage_invalid")
        digest = hashlib.sha256(str(row[8]).encode()).hexdigest()
        envelope = EventEnvelopeV1(
            OpaqueIdV1(str(row[1])),
            str(row[2]),
            _required_time(row[9]),
            _required_time(row[10]),
            "collection_control",
            "1",
            OpaqueIdV1(str(row[6])),
            OpaqueIdV1(str(row[7])) if row[7] is not None else None,
            OpaqueIdV1(str(row[5])),
        )
        return DurableEventV1(
            envelope,
            1,
            str(row[3]),
            _integer(row[4]),
            payload,
            digest,
        )

    def acknowledge_event(
        self,
        consumer_key: str,
        event_id: OpaqueIdV1,
        payload_digest: str,
        receipt_id: OpaqueIdV1,
        as_of: datetime,
    ) -> None:
        if (
            not _CONSUMER.fullmatch(consumer_key)
            or _DIGEST.fullmatch(payload_digest) is None
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", receipt_id.value)
            or as_of > datetime.now(UTC)
        ):
            raise CollectorConditionStorageErrorV1("collector_event_proof_invalid")
        try:
            with _open_condition_writer(
                self._reference, datetime.now(UTC) + timedelta(seconds=2)
            ) as writer:
                rows = writer.rows(
                    "SELECT event_id,event_type,stream_id,stream_sequence,subject_id,"
                    "correlation_id,causation_id,payload_json,occurred_at,recorded_at,"
                    "available_at,event_schema FROM collection_event_outbox "
                    "WHERE event_id=? LIMIT 1",
                    (event_id.value,),
                    limit=1,
                )
                if not rows or rows[0][1] != "collector.health_changed.v1":
                    raise CollectorConditionStorageErrorV1("collector_event_not_found")
                event = self._event((0, *tuple(rows[0])))
                if (
                    event.payload_digest != payload_digest
                    or _required_time(rows[0][10]) > as_of
                ):
                    raise CollectorConditionStorageErrorV1(
                        "collector_event_proof_mismatch"
                    )
                previous = writer.rows(
                    "SELECT state,consumer_receipt_id,ack_payload_digest "
                    "FROM collection_event_delivery WHERE event_id=? AND consumer_key=? LIMIT 1",
                    (event_id.value, consumer_key),
                    limit=1,
                )
                if previous:
                    if previous[0][1] is None and previous[0][2] is None:
                        writer.execute(
                            "UPDATE collection_event_delivery SET state='acknowledged',"
                            "attempt_count=attempt_count+1,delivered_at=?,"
                            "acknowledged_at=?,consumer_receipt_id=?,ack_payload_digest=? "
                            "WHERE event_id=? AND consumer_key=?",
                            (
                                _text(as_of),
                                _text(as_of),
                                receipt_id.value,
                                payload_digest,
                                event_id.value,
                                consumer_key,
                            ),
                        )
                    elif (
                        previous[0][0] != "acknowledged"
                        or previous[0][1] != receipt_id.value
                        or previous[0][2] != payload_digest
                    ):
                        raise CollectorConditionStorageErrorV1(
                            "collector_event_proof_conflict"
                        )
                else:
                    writer.execute(
                        "INSERT INTO collection_event_delivery "
                        "(event_id,consumer_key,consumer_version,state,attempt_count,"
                        "delivered_at,acknowledged_at,consumer_receipt_id,ack_payload_digest) "
                        "VALUES (?,?,?,'acknowledged',1,?,?,?,?)",
                        (
                            event_id.value,
                            consumer_key,
                            "1",
                            _text(as_of),
                            _text(as_of),
                            receipt_id.value,
                            payload_digest,
                        ),
                    )
        except (
            CollectorConditionStorageErrorV1,
            ValueError,
            TypeError,
            IndexError,
            KeyError,
        ):
            raise CollectorConditionStorageErrorV1() from None
