"""M05 durable current projection adapter over genuine owned quota history."""

# ruff: noqa: E501 -- explicit SQL predicates are reviewable here.

import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.capacity.sqlite.forecast_snapshot import (
    ForecastSnapshotInvalidV1,
    decode_forecast_snapshot_v1,
    encode_forecast_snapshot_v1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    CapacityRepositoryErrorV1,
    SqliteCapacityRepositoryV1,
    _identifier,
    _stable_identifier,
    _utc_text,
    _utc_value,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityAvailabilityAlertConditionV1,
    CapacityAvailabilityQueryV1,
    CapacityForecastQueryV1,
    CapacityForecastV1,
    CurrentCapacityForecastV1,
    QuotaWindowViewV1,
)
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityStateV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.modules.capacity.application.queries import ListCapacityForecastsV1
from agentmonitor.modules.capacity.domain.current_projection import (
    classify_capability_availability_v1,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError


def _schema_ready(connection: Connection) -> bool:
    forecast_columns = set(
        connection.exec_driver_sql(
            "SELECT name FROM pragma_table_info('capacity_forecast_projection') "
            "WHERE name IN ('window_projection_id','source_projection_version','snapshot_json')"
        ).scalars()
    )
    return forecast_columns == {
        "window_projection_id",
        "source_projection_version",
        "snapshot_json",
    } and (
        connection.exec_driver_sql(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='capacity_availability_current'"
        ).scalar_one_or_none()
        is not None
    )


def _availability(
    state: QueryAvailabilityStateV1, reason: str, as_of: datetime
) -> QueryAvailabilityV1:
    return QueryAvailabilityV1(state, reason, as_of)


def _forecast_key(window: QuotaWindowViewV1) -> str:
    return _stable_identifier(
        "capacity.current.forecast.v1",
        window.window_id.value,
        "used",
        "bounded-secant-v1",
    )


def _missing_history_forecast(
    window: QuotaWindowViewV1, definition_id: OpaqueIdV1, as_of: datetime
) -> CapacityForecastV1:
    state: Literal["stale", "conflicted", "insufficient_input"] = (
        "stale"
        if window.freshness == "stale"
        else "conflicted"
        if window.freshness == "conflicted"
        else "insufficient_input"
    )
    reason = (
        "current_observation_stale"
        if state == "stale"
        else "current_observation_conflicted"
        if state == "conflicted"
        else "history_absent"
    )
    digest = _stable_identifier(
        "capacity.forecast.no_history.v1",
        window.window_id.value,
        window.current_observation_id.value,
        str(window.projection_version),
        reason,
    )
    return CapacityForecastV1(
        OpaqueIdV1(_forecast_key(window)),
        1,
        window.subject,
        window.window_id,
        definition_id,
        "used",
        state,
        None,
        None,
        None,
        "unknown",
        "unknown",
        "unknown",
        (),
        (reason,),
        (window.current_observation_id,),
        digest,
        "bounded-secant-v1",
        "1.0.0",
        as_of,
        window.provenance.freshness_deadline,
    )


def _semantic_forecast(forecast: CapacityForecastV1) -> CapacityForecastV1:
    return replace(
        forecast,
        forecast_id=OpaqueIdV1("semantic-forecast"),
        generation=1,
        generated_at=datetime(2000, 1, 1, tzinfo=UTC),
    )


def _event(
    connection: Connection,
    *,
    event_type: str,
    stream_key: str,
    subject_id: str,
    generation: int,
    correlation_id: str,
    causation_id: str,
    payload: dict[str, object],
    as_of: datetime,
) -> None:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    if len(encoded) > 4096:
        raise CapacityRepositoryErrorV1("capacity_projection_event_too_large")
    sequence = int(
        connection.exec_driver_sql(
            "SELECT COALESCE(MAX(producer_sequence),0)+1 FROM capacity_event_outbox"
        ).scalar_one()
    )
    stream_sequence = int(
        connection.exec_driver_sql(
            "SELECT COALESCE(MAX(stream_sequence),0)+1 FROM capacity_event_outbox WHERE projection_stream_key=?",
            (stream_key,),
        ).scalar_one()
    )
    recorded_at = datetime.now(UTC)
    connection.exec_driver_sql(
        "INSERT INTO capacity_event_outbox (event_id,event_type,event_schema,projection_stream_key,"
        "stream_sequence,subject_id,subject_version,producer_sequence,correlation_id,causation_id,"
        "payload_json,occurred_at,recorded_at,available_at,producer_version) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _identifier(),
            event_type,
            event_type,
            stream_key,
            stream_sequence,
            subject_id,
            generation,
            sequence,
            correlation_id,
            causation_id,
            encoded,
            _utc_text(as_of),
            _utc_text(recorded_at),
            _utc_text(recorded_at),
            SqliteCapacityRepositoryV1.CONSUMER_VERSION,
        ),
    )


def _forecast_derivation(
    connection: Connection,
    forecast: CapacityForecastV1,
    source_generation: int,
    as_of: datetime,
) -> str | None:
    burn = forecast.burn_rate
    if burn is None:
        return None
    derivation_id = _stable_identifier(
        "exhaustion_forecast",
        forecast.method_id,
        forecast.method_version,
        forecast.input_set_digest,
    )
    connection.exec_driver_sql(
        "INSERT OR IGNORE INTO capacity_derivation (derivation_id,derivation_kind,method_id,"
        "method_version,input_set_digest,result_type,result_coefficient,result_scale,result_unit,"
        "time_basis,precision,confidence,uncertainty,reason_code,policy_generation,"
        "schema_generation,source_generation,explanation_codes_json,derived_at,valid_until) "
        "VALUES (?,'exhaustion_forecast',?,?,?,'burn_rate',?, ?,?,'second',?,?,?,?,1,1,?,?,?,?)",
        (
            derivation_id,
            forecast.method_id,
            forecast.method_version,
            forecast.input_set_digest,
            burn.estimate.amount.coefficient,
            burn.estimate.amount.scale,
            burn.estimate.unit,
            forecast.precision,
            forecast.confidence,
            "bounded",
            "forecast_available",
            source_generation,
            json.dumps(list(forecast.uncertainty_codes), separators=(",", ":")),
            _utc_text(as_of),
            _utc_text(forecast.valid_until) if forecast.valid_until else None,
        ),
    )
    stored = (
        connection.exec_driver_sql(
            "SELECT derivation_kind,method_id,method_version,input_set_digest,source_generation "
            "FROM capacity_derivation WHERE derivation_id=?",
            (derivation_id,),
        )
        .mappings()
        .one_or_none()
    )
    if (
        stored is None
        or stored["derivation_kind"] != "exhaustion_forecast"
        or stored["method_id"] != forecast.method_id
        or stored["method_version"] != forecast.method_version
        or stored["input_set_digest"] != forecast.input_set_digest
        or stored["source_generation"] != source_generation
    ):
        raise CapacityRepositoryErrorV1("capacity_forecast_derivation_conflict")
    for ordinal, observation_id in enumerate(forecast.input_observation_ids):
        row = (
            connection.exec_driver_sql(
                "SELECT payload_digest,observed_at FROM capacity_quota_observation WHERE observation_id=?",
                (observation_id.value,),
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CapacityRepositoryErrorV1("capacity_forecast_input_changed")
        connection.exec_driver_sql(
            "INSERT OR IGNORE INTO capacity_derivation_input (derivation_id,ordinal,input_kind,"
            "input_role,input_id,input_version,input_digest,semantic_time) "
            "VALUES (?,?,'quota_observation','forecast_sample',?,1,?,?)",
            (
                derivation_id,
                ordinal,
                observation_id.value,
                row["payload_digest"],
                row["observed_at"],
            ),
        )
    return derivation_id


def _current_forecast_row(row: RowMapping) -> CurrentCapacityForecastV1:
    forecast = decode_forecast_snapshot_v1(str(row["snapshot_json"]))
    if (
        forecast.generation != int(row["record_version"])
        or forecast.state != row["forecast_state"]
        or forecast.window_id.value != row["window_projection_id"]
        or forecast.subject.account_id.value != row["account_id"]
        or forecast.subject.resource_id.value != row["resource_id"]
    ):
        raise CapacityRepositoryErrorV1("capacity_forecast_snapshot_mismatch")
    return CurrentCapacityForecastV1(
        forecast,
        OpaqueIdV1(str(row["window_projection_id"])),
        int(row["source_projection_version"]),
        _utc_value(str(row["reset_at"]))
        if row["reset_at"] is not None and row["reset_precision"] == "exact"
        else None,
        _utc_value(str(row["observed_at"])) if row["observed_at"] is not None else None,
        _utc_value(str(row["updated_at"])),
        _utc_value(str(row["freshness_deadline"]))
        if row["freshness_deadline"] is not None
        else None,
    )


class SqliteCurrentCapacityRepositoryV1:
    """Owned durable producer. Never invokes provider or mutates owner profiles."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref
        self._quota = SqliteCapacityRepositoryV1(database_ref)

    def page_current_forecasts(
        self, query: CapacityForecastQueryV1
    ) -> QueryPageV1[CurrentCapacityForecastV1]:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    if not _schema_ready(connection):
                        return QueryPageV1(
                            (),
                            query.limit,
                            False,
                            None,
                            _availability(
                                "unavailable",
                                "capacity_current_schema_required",
                                query.as_of,
                            ),
                        )
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT f.*,o.reset_at,d.reset_precision,o.observed_at,p.freshness_deadline "
                            "FROM capacity_forecast_projection f JOIN capacity_current_projection p "
                            "ON p.projection_id=f.window_projection_id AND p.record_version=f.source_projection_version "
                            "JOIN capacity_quota_observation o ON o.observation_id=p.current_observation_id "
                            "JOIN capacity_quota_window_definition d ON d.window_definition_id=p.window_definition_id "
                            "WHERE f.snapshot_json IS NOT NULL AND f.account_id=? "
                            "AND (? IS NULL OR f.resource_id=?) AND (? IS NULL OR f.window_projection_id=?) "
                            "AND (? IS NULL OR f.window_projection_id>?) "
                            "ORDER BY f.window_projection_id LIMIT ?",
                            (
                                query.account_id.value,
                                query.resource_id.value if query.resource_id else None,
                                query.resource_id.value if query.resource_id else None,
                                query.window_id.value if query.window_id else None,
                                query.window_id.value if query.window_id else None,
                                query.after_key,
                                query.after_key,
                                query.limit + 1,
                            ),
                        )
                        .mappings()
                        .all()
                    )
                    selected = tuple(
                        _current_forecast_row(row) for row in rows[: query.limit]
                    )
                    selected = tuple(
                        item
                        for item in selected
                        if item.freshness_deadline is None
                        or query.as_of < item.freshness_deadline
                        or item.forecast.state == "stale"
                    )
                    has_more = len(rows) > query.limit
                    return QueryPageV1(
                        selected,
                        query.limit,
                        has_more,
                        rows[query.limit - 1]["window_projection_id"]
                        if has_more
                        else None,
                        _availability(
                            "available" if selected else "unavailable",
                            "capacity_current_forecasts_available"
                            if selected
                            else "capacity_current_forecasts_absent",
                            query.as_of,
                        ),
                    )
        except (
            SqlitePolicyError,
            SQLAlchemyError,
            ValueError,
            TypeError,
            KeyError,
            ForecastSnapshotInvalidV1,
        ):
            raise CapacityRepositoryErrorV1(
                "capacity_current_forecast_read_unavailable"
            ) from None

    def page_current_availability(
        self, query: CapacityAvailabilityQueryV1
    ) -> QueryPageV1[CapacityAvailabilityAlertConditionV1]:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    if not _schema_ready(connection):
                        return QueryPageV1(
                            (),
                            query.limit,
                            False,
                            None,
                            _availability(
                                "unavailable",
                                "capacity_current_schema_required",
                                query.as_of,
                            ),
                        )
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT a.* FROM capacity_availability_current a JOIN capacity_current_projection p "
                            "ON a.signal_kind='capability' AND p.projection_id=a.source_subject_id "
                            "AND p.record_version=a.source_generation WHERE a.account_id=? "
                            "AND (? IS NULL OR a.resource_id=?) AND (? IS NULL OR a.capability_id=?) "
                            "AND (? IS NULL OR a.signal_kind=?) AND (? IS NULL OR a.stream_id>?) "
                            "ORDER BY a.stream_id LIMIT ?",
                            (
                                query.account_id.value,
                                query.resource_id.value if query.resource_id else None,
                                query.resource_id.value if query.resource_id else None,
                                query.capability_id,
                                query.capability_id,
                                query.signal_kind,
                                query.signal_kind,
                                query.after_key,
                                query.after_key,
                                query.limit + 1,
                            ),
                        )
                        .mappings()
                        .all()
                    )
                    items = tuple(
                        self._availability_row(row) for row in rows[: query.limit]
                    )
                    items = tuple(
                        item
                        for item in items
                        if item.freshness_deadline is None
                        or query.as_of < item.freshness_deadline
                        or item.state == "stale"
                    )
                    has_more = len(rows) > query.limit
                    return QueryPageV1(
                        items,
                        query.limit,
                        has_more,
                        rows[query.limit - 1]["stream_id"] if has_more else None,
                        _availability(
                            "available" if items else "unavailable",
                            "capacity_current_availability_available"
                            if items
                            else "capacity_current_availability_absent",
                            query.as_of,
                        ),
                    )
        except (SqlitePolicyError, SQLAlchemyError, ValueError, TypeError, KeyError):
            raise CapacityRepositoryErrorV1(
                "capacity_current_availability_read_unavailable"
            ) from None

    @staticmethod
    def _availability_row(row: RowMapping) -> CapacityAvailabilityAlertConditionV1:
        ids = json.loads(str(row["observation_ids_json"]))
        if not isinstance(ids, list) or len(ids) > 200:
            raise CapacityRepositoryErrorV1("capacity_availability_lineage_invalid")
        return CapacityAvailabilityAlertConditionV1(
            OpaqueIdV1(str(row["resource_id"])),
            OpaqueIdV1(str(row["account_id"])),
            int(row["record_version"]),
            row["state"],
            tuple(OpaqueIdV1(value) for value in ids),
            _utc_value(str(row["evaluated_at"])),
            str(row["reason_code"]),
            str(row["capability_id"]),
            row["signal_kind"],
            OpaqueIdV1(str(row["source_subject_id"])),
            OpaqueIdV1(str(row["source_record_id"])),
            int(row["source_generation"]),
            str(row["source_contract_id"]),
            _utc_value(str(row["source_observed_at"]))
            if row["source_observed_at"]
            else None,
            _utc_value(str(row["source_recorded_at"])),
            _utc_value(str(row["freshness_deadline"]))
            if row["freshness_deadline"]
            else None,
            int(row["recovery_of_generation"])
            if row["recovery_of_generation"] is not None
            else None,
        )

    def refresh_current_projections(
        self, as_of: datetime, after_key: str | None, limit: int
    ) -> QueryPageV1[CurrentCapacityForecastV1]:
        if (
            type(limit) is not int
            or not 1 <= limit <= 32
            or after_key is not None
            and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", after_key) is None
        ):
            raise CapacityRepositoryErrorV1("capacity_refresh_query_invalid")
        if as_of.utcoffset() != timedelta(0) or as_of > datetime.now(UTC):
            raise CapacityRepositoryErrorV1("capacity_refresh_time_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    if not _schema_ready(connection):
                        raise CapacityRepositoryErrorV1(
                            "capacity_current_schema_required"
                        )
                    source_rows = (
                        connection.exec_driver_sql(
                            "SELECT p.projection_id,p.window_definition_id,p.account_id,p.resource_id,p.capability_id "
                            "FROM capacity_current_projection p JOIN capacity_quota_observation o "
                            "ON o.observation_id=p.current_observation_id WHERE p.projection_kind='quota' "
                            "AND o.collected_at<=? AND (? IS NULL OR p.projection_id>?) "
                            "ORDER BY p.projection_id LIMIT ?",
                            (_utc_text(as_of), after_key, after_key, limit + 1),
                        )
                        .mappings()
                        .all()
                    )
            selected = source_rows[:limit]
            completed: list[CurrentCapacityForecastV1] = []
            for source in selected:
                windows = self._quota.list_quota_windows(
                    OpaqueIdV1(str(source["account_id"])),
                    OpaqueIdV1(str(source["resource_id"])),
                    str(source["capability_id"]),
                    as_of,
                )
                window = next(
                    (
                        item
                        for item in windows
                        if item.window_id.value == source["projection_id"]
                    ),
                    None,
                )
                if window is None:
                    continue
                if window.projection_version is None:
                    continue
                exploratory = ListCapacityForecastsV1(self._quota)._window_forecast(
                    window, as_of
                )
                forecast = (
                    exploratory
                    if exploratory is not None
                    else _missing_history_forecast(
                        window, OpaqueIdV1(str(source["window_definition_id"])), as_of
                    )
                )
                if (
                    forecast.input_observation_ids
                    and forecast.input_observation_ids[-1]
                    != window.current_observation_id
                ):
                    forecast = replace(
                        forecast,
                        state="insufficient_input",
                        burn_rate=None,
                        earliest_exhaustion_at=None,
                        latest_exhaustion_at=None,
                        reset_relation="unknown",
                        confidence="unknown",
                        precision="unknown",
                        reason_codes=("current_observation_not_in_history",),
                    )
                if forecast.state != "stale" and window.freshness == "stale":
                    forecast = replace(
                        forecast,
                        state="stale",
                        burn_rate=None,
                        earliest_exhaustion_at=None,
                        latest_exhaustion_at=None,
                        reset_relation="unknown",
                        confidence="unknown",
                        precision="unknown",
                        reason_codes=("current_observation_stale",),
                    )
                if forecast.state != "conflicted" and window.freshness == "conflicted":
                    forecast = replace(
                        forecast,
                        state="conflicted",
                        burn_rate=None,
                        earliest_exhaustion_at=None,
                        latest_exhaustion_at=None,
                        reset_relation="unknown",
                        confidence="unknown",
                        precision="unknown",
                        reason_codes=("current_observation_conflicted",),
                    )
                forecast = replace(
                    forecast,
                    input_set_digest=_stable_identifier(
                        "capacity.current.forecast.input.v1",
                        forecast.input_set_digest,
                        str(window.projection_version),
                        window.current_observation_id.value,
                    ),
                )
                self._write_current(window, forecast, as_of)
                page = self.page_current_forecasts(
                    CapacityForecastQueryV1(
                        window.subject.account_id,
                        window.subject.resource_id,
                        window.window_id,
                        as_of,
                        1,
                    )
                )
                completed.extend(page.items)
            has_more = len(source_rows) > limit
            return QueryPageV1(
                tuple(completed),
                limit,
                has_more,
                str(selected[-1]["projection_id"]) if has_more and selected else None,
                _availability(
                    "available" if completed else "unavailable",
                    "capacity_current_refresh_available"
                    if completed
                    else "capacity_current_refresh_empty",
                    as_of,
                ),
            )
        except CapacityRepositoryErrorV1:
            raise
        except (
            SqlitePolicyError,
            SQLAlchemyError,
            ValueError,
            TypeError,
            KeyError,
            ForecastSnapshotInvalidV1,
        ):
            raise CapacityRepositoryErrorV1(
                "capacity_current_refresh_unavailable"
            ) from None

    def _write_current(
        self, window: QuotaWindowViewV1, forecast: CapacityForecastV1, as_of: datetime
    ) -> None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    source = (
                        connection.exec_driver_sql(
                            "SELECT record_version,current_observation_id FROM capacity_current_projection "
                            "WHERE projection_id=? AND projection_kind='quota'",
                            (window.window_id.value,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if (
                        source is None
                        or int(source["record_version"]) != window.projection_version
                        or source["current_observation_id"]
                        != window.current_observation_id.value
                    ):
                        connection.rollback()
                        return
                    ids = tuple(item.value for item in forecast.input_observation_ids)
                    if ids:
                        markers = ",".join("?" for _ in ids)
                        present = set(
                            connection.exec_driver_sql(
                                "SELECT observation_id FROM capacity_quota_observation WHERE observation_id IN ("
                                + markers
                                + ")",
                                ids,
                            ).scalars()
                        )
                        if present != set(ids):
                            connection.rollback()
                            return
                    self._write_forecast(connection, window, forecast, as_of)
                    self._write_availability(connection, window, as_of)
                    connection.commit()
        except CapacityRepositoryErrorV1:
            raise
        except (
            SqlitePolicyError,
            SQLAlchemyError,
            ValueError,
            TypeError,
            KeyError,
            ForecastSnapshotInvalidV1,
        ):
            raise CapacityRepositoryErrorV1(
                "capacity_current_write_unavailable"
            ) from None

    def _write_forecast(
        self,
        connection: Connection,
        window: QuotaWindowViewV1,
        forecast: CapacityForecastV1,
        as_of: datetime,
    ) -> None:
        if window.projection_version is None:
            raise CapacityRepositoryErrorV1("capacity_projection_generation_unknown")
        key = _forecast_key(window)
        old = (
            connection.exec_driver_sql(
                "SELECT * FROM capacity_forecast_projection WHERE forecast_key=?",
                (key,),
            )
            .mappings()
            .one_or_none()
        )
        if old is not None and old["snapshot_json"] is not None:
            prior = decode_forecast_snapshot_v1(str(old["snapshot_json"]))
            if old[
                "source_projection_version"
            ] == window.projection_version and _semantic_forecast(
                prior
            ) == _semantic_forecast(forecast):
                return
        generation = int(old["record_version"]) + 1 if old else 1
        stable_id = (
            str(old["forecast_id"]) if old else _stable_identifier("forecast", key)
        )
        current = replace(
            forecast,
            forecast_id=OpaqueIdV1(stable_id),
            generation=generation,
            generated_at=as_of,
        )
        snapshot = encode_forecast_snapshot_v1(current)
        derivation = _forecast_derivation(
            connection, current, window.projection_version, as_of
        )
        burn = current.burn_rate
        connection.exec_driver_sql(
            "INSERT INTO capacity_forecast_projection (forecast_id,forecast_key,provider_key,account_id,"
            "resource_id,window_definition_id,metric_key,forecast_state,exhaustion_at,burn_coefficient,"
            "burn_scale,burn_unit,confidence,reason_code,derivation_id,previous_derivation_id,"
            "projected_at,valid_until,updated_at,record_version,earliest_exhaustion_at,"
            "latest_exhaustion_at,burn_lower_coefficient,burn_lower_scale,burn_upper_coefficient,"
            "burn_upper_scale,window_projection_id,source_projection_version,snapshot_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(forecast_key) DO UPDATE SET forecast_state=excluded.forecast_state,"
            "exhaustion_at=excluded.exhaustion_at,burn_coefficient=excluded.burn_coefficient,"
            "burn_scale=excluded.burn_scale,burn_unit=excluded.burn_unit,confidence=excluded.confidence,"
            "reason_code=excluded.reason_code,previous_derivation_id=capacity_forecast_projection.derivation_id,"
            "derivation_id=excluded.derivation_id,projected_at=excluded.projected_at,"
            "valid_until=excluded.valid_until,updated_at=excluded.updated_at,record_version=excluded.record_version,"
            "earliest_exhaustion_at=excluded.earliest_exhaustion_at,latest_exhaustion_at=excluded.latest_exhaustion_at,"
            "burn_lower_coefficient=excluded.burn_lower_coefficient,burn_lower_scale=excluded.burn_lower_scale,"
            "burn_upper_coefficient=excluded.burn_upper_coefficient,burn_upper_scale=excluded.burn_upper_scale,"
            "window_projection_id=excluded.window_projection_id,source_projection_version=excluded.source_projection_version,"
            "snapshot_json=excluded.snapshot_json",
            (
                stable_id,
                key,
                window.subject.provider_key,
                window.subject.account_id.value,
                window.subject.resource_id.value,
                current.window_definition_id.value,
                "used",
                current.state,
                _utc_text(current.latest_exhaustion_at)
                if current.latest_exhaustion_at
                else None,
                burn.estimate.amount.coefficient if burn else None,
                burn.estimate.amount.scale if burn else None,
                burn.estimate.unit if burn else None,
                current.confidence,
                current.reason_codes[0]
                if current.reason_codes
                else "forecast_available",
                derivation,
                str(old["derivation_id"]) if old and old["derivation_id"] else None,
                _utc_text(as_of),
                _utc_text(current.valid_until) if current.valid_until else None,
                _utc_text(datetime.now(UTC)),
                generation,
                _utc_text(current.earliest_exhaustion_at)
                if current.earliest_exhaustion_at
                else None,
                _utc_text(current.latest_exhaustion_at)
                if current.latest_exhaustion_at
                else None,
                burn.lower_bound.amount.coefficient if burn else None,
                burn.lower_bound.amount.scale if burn else None,
                burn.upper_bound.amount.coefficient if burn else None,
                burn.upper_bound.amount.scale if burn else None,
                window.window_id.value,
                window.projection_version,
                snapshot,
            ),
        )
        transition = (
            "active"
            if current.state == "available" and current.reset_relation == "after"
            else (
                "recovered"
                if old is not None
                and old["forecast_state"] == "available"
                and current.state == "available"
                and current.reset_relation == "before"
                else "invalidated"
                if old is not None and old["forecast_state"] == "available"
                else "not_evaluable"
            )
        )
        payload: dict[str, object] = {
            "window_id": window.window_id.value,
            "previous_state": str(old["forecast_state"]) if old else None,
            "current_state": current.state,
            "transition": transition,
            "generation": generation,
            "source_generation": window.projection_version,
            "input_set_digest": current.input_set_digest,
            "reason_code": current.reason_codes[0]
            if current.reason_codes
            else "forecast_available",
            "latest_observation_id": current.input_observation_ids[-1].value
            if current.input_observation_ids
            else None,
            "occurred_at": _utc_text(as_of),
        }
        _event(
            connection,
            event_type="capacity.forecast.changed.v1",
            stream_key="capacity.forecast/" + key,
            subject_id=window.window_id.value,
            generation=generation,
            correlation_id=window.collection_run_id.value,
            causation_id=window.current_observation_id.value,
            payload=payload,
            as_of=as_of,
        )

    def _write_availability(
        self, connection: Connection, window: QuotaWindowViewV1, as_of: datetime
    ) -> None:
        if window.projection_version is None:
            raise CapacityRepositoryErrorV1("capacity_projection_generation_unknown")
        # No per-observation identity binding proof exists in the public M02/M05 seam.
        metric_state = (
            "available"
            if any(
                field.availability.state == "available"
                for field in (
                    window.used,
                    window.remaining,
                    window.limit,
                    window.remaining_ratio,
                )
            )
            else window.used.availability.state
        )
        state, reason = classify_capability_availability_v1(
            window.freshness,
            window.completeness,
            metric_state,
            identity_bound=False,
        )
        stream_id = _stable_identifier(
            "capacity.availability.capability.v1", window.window_id.value
        )
        input_digest = _stable_identifier(
            "capacity.availability.input.v1",
            window.window_id.value,
            str(window.projection_version),
            window.current_observation_id.value,
            state,
            reason,
            window.provenance.freshness_deadline.isoformat()
            if window.provenance.freshness_deadline
            else "unknown",
        )
        old = (
            connection.exec_driver_sql(
                "SELECT * FROM capacity_availability_current WHERE stream_id=?",
                (stream_id,),
            )
            .mappings()
            .one_or_none()
        )
        if old is not None and old["input_digest"] == input_digest:
            return
        generation = int(old["record_version"]) + 1 if old else 1
        # A bad state may clear only on proved newer healthy evidence from the same stream.
        recovery_of = None
        active_failure = (
            int(old["active_failure_generation"])
            if old and old["active_failure_generation"] is not None
            else None
        )
        if state in {"unavailable", "blocked", "reauthentication_required"}:
            active_failure = generation
        elif (
            state == "available"
            and active_failure is not None
            and old
            and window.projection_version > int(old["source_generation"])
        ):
            recovery_of = active_failure
            active_failure = None
        connection.exec_driver_sql(
            "INSERT INTO capacity_availability_current (stream_id,provider_key,account_id,resource_id,"
            "capability_id,signal_kind,source_subject_id,source_record_id,source_generation,source_contract_id,"
            "state,reason_code,observation_ids_json,input_digest,record_version,source_observed_at,"
            "source_recorded_at,evaluated_at,freshness_deadline,active_failure_generation,recovery_of_generation,updated_at) "
            "VALUES (?,?,?,?,?,'capability',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(stream_id) DO UPDATE SET source_record_id=excluded.source_record_id,"
            "source_generation=excluded.source_generation,state=excluded.state,reason_code=excluded.reason_code,"
            "observation_ids_json=excluded.observation_ids_json,input_digest=excluded.input_digest,"
            "record_version=excluded.record_version,source_observed_at=excluded.source_observed_at,"
            "source_recorded_at=excluded.source_recorded_at,evaluated_at=excluded.evaluated_at,"
            "freshness_deadline=excluded.freshness_deadline,active_failure_generation=excluded.active_failure_generation,"
            "recovery_of_generation=excluded.recovery_of_generation,updated_at=excluded.updated_at",
            (
                stream_id,
                window.subject.provider_key,
                window.subject.account_id.value,
                window.subject.resource_id.value,
                window.provenance.capability_id,
                window.window_id.value,
                window.current_observation_id.value,
                window.projection_version,
                "CTR-CAP-001",
                state,
                reason,
                json.dumps(
                    [window.current_observation_id.value], separators=(",", ":")
                ),
                input_digest,
                generation,
                _utc_text(window.observed_at) if window.observed_at else None,
                _utc_text(window.stored_at),
                _utc_text(as_of),
                _utc_text(window.provenance.freshness_deadline)
                if window.provenance.freshness_deadline
                else None,
                active_failure,
                recovery_of,
                _utc_text(datetime.now(UTC)),
            ),
        )
        payload: dict[str, object] = {
            "stream_id": stream_id,
            "previous_state": str(old["state"]) if old else None,
            "current_state": state,
            "transition": "recovered"
            if recovery_of is not None
            else "active"
            if state in {"unavailable", "blocked", "reauthentication_required"}
            else "not_evaluable",
            "generation": generation,
            "source_generation": window.projection_version,
            "input_set_digest": input_digest,
            "reason_code": reason,
            "latest_observation_id": window.current_observation_id.value,
            "occurred_at": _utc_text(as_of),
        }
        _event(
            connection,
            event_type="capacity.availability.changed.v1",
            stream_key="capacity.availability/" + stream_id,
            subject_id=stream_id,
            generation=generation,
            correlation_id=window.collection_run_id.value,
            causation_id=window.current_observation_id.value,
            payload=payload,
            as_of=as_of,
        )
