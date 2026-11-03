"""Bounded read-only recovery evidence from M04-owned durable records."""

from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.bounded_read import (
    BoundedSqliteReadConnectionV1,
    open_bounded_sqlite_read,
)
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.contracts.collection_recovery_v1 import (
    CollectionRecoveryPageV1,
    CollectionRecoveryQueryV1,
    CollectionRecoveryRunV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

_TABLES = frozenset(
    {
        "collection_run",
        "collection_run_observation_ref",
        "collection_cloud_attempt_journal",
        "collection_ollama_cloud_admission",
        "collection_cloud_no_response_terminal",
    }
)
_COLUMNS = (
    "run_id,provider_key,account_id,provider_target_kind,provider_target_id,"
    "target_generation,capability_id,source_id,adapter_version,manifest_fingerprint,"
    "payload_schema,requested_at,completed_at,state,payload_digest"
)


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("collection_recovery_record_invalid")
    return value


def _optional(value: object) -> str | None:
    return None if value is None else _text(value)


def _time(value: object) -> datetime:
    return datetime.fromisoformat(_text(value).replace("Z", "+00:00"))


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _run(
    reader: BoundedSqliteReadConnectionV1, row: tuple[object, ...]
) -> CollectionRecoveryRunV1:
    journal = reader.fetch_many(
        "SELECT j.phase,j.outcome,j.failure_code,j.response_received_at,"
        "a.account_id,a.schedule_id,r.account_id,r.schedule_id,"
        "t.dispatch_certainty,t.reason_code,t.source_state "
        "FROM collection_cloud_attempt_journal j "
        "JOIN collection_ollama_cloud_admission a ON a.admission_id=j.admission_id "
        "JOIN collection_run r ON r.run_id=j.run_id "
        "LEFT JOIN collection_cloud_no_response_terminal t "
        "ON t.admission_id=j.admission_id "
        "WHERE j.run_id=? LIMIT 2",
        (row[0],),
        limit=2,
    )
    if len(journal) > 1:
        raise ValueError("collection_recovery_lineage_ambiguous")
    certainty = outcome = failure = None
    if journal:
        record = journal[0]
        if record[4:6] != record[6:8]:
            raise ValueError("collection_recovery_lineage_invalid")
        if record[8] is not None:
            certainty = _text(record[8])
            failure = _optional(record[10]) or _optional(record[9])
        elif record[0] == "outcome" and record[3] is not None:
            certainty = "response_received"
            outcome = _optional(record[1])
            failure = _optional(record[2])
        elif record[0] == "reserved":
            certainty = "not_started"
        else:
            certainty = "may_have_started"
    observations = reader.fetch_many(
        "SELECT observation_id FROM collection_run_observation_ref "
        "WHERE run_id=? ORDER BY observation_id LIMIT 201",
        (row[0],),
        limit=201,
    )
    if len(observations) > 200 or type(row[5]) is not int:
        raise ValueError("collection_recovery_record_invalid")
    return CollectionRecoveryRunV1(
        OpaqueIdV1(_text(row[0])),
        _text(row[1]),
        OpaqueIdV1(_text(row[2])) if row[2] is not None else None,
        _optional(row[3]),
        OpaqueIdV1(_text(row[4])) if row[4] is not None else None,
        row[5],
        _text(row[6]),
        _text(row[7]),
        _text(row[8]),
        _text(row[9]),
        _text(row[10]),
        _time(row[11]),
        _time(row[12]),
        _text(row[13]),
        certainty,
        outcome,
        failure,
        _optional(row[14]),
        tuple(OpaqueIdV1(_text(item[0])) for item in observations),
    )


class SqliteCollectionRecoveryQueryV1:
    """No schema writes, arbitrary SQL, provider calls or cross-module tables."""

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._reference = reference

    def read_recovery_runs(
        self, query: CollectionRecoveryQueryV1
    ) -> CollectionRecoveryPageV1:
        if not isinstance(query, CollectionRecoveryQueryV1):
            raise ValueError("collection_recovery_query_invalid")
        where = (
            "provider_key=? AND requested_at>=? AND requested_at<? "
            "AND completed_at<? AND state IN "
            "('succeeded','partial','failed','blocked','cancelled','unsupported')"
        )
        params: tuple[object, ...] = (
            query.provider_key,
            _stamp(query.from_at),
            _stamp(query.before_at),
            _stamp(query.before_at),
        )
        scope = query.scope
        if scope is not None:
            if query.provider_key != scope.provider_key:
                raise ValueError("collection_recovery_query_invalid")
            where += (
                " AND account_id=? AND provider_target_kind='cloud_service' "
                "AND provider_target_id=? AND target_generation=? AND capability_id=? "
                "AND source_id=? AND adapter_version=? AND manifest_fingerprint=? "
                "AND payload_schema=?"
            )
            params += (
                scope.account_id.value,
                scope.access_target_id.value,
                scope.binding_generation,
                scope.capability_id,
                scope.source_id,
                scope.adapter_version,
                scope.source_fingerprint,
                scope.payload_schema,
            )
        with open_bounded_sqlite_read(
            self._reference,
            deadline=datetime.now(UTC) + timedelta(seconds=1.9),
            allowed_tables=_TABLES,
        ) as reader:
            rows = reader.fetch_many(
                "SELECT "
                + _COLUMNS
                + " FROM collection_run WHERE "
                + where
                + " ORDER BY requested_at DESC,run_id DESC LIMIT ?",
                (*params, query.limit + 1),
                limit=query.limit + 1,
            )
            items = tuple(_run(reader, row) for row in rows[: query.limit])
        return CollectionRecoveryPageV1(items, len(rows) > query.limit)
