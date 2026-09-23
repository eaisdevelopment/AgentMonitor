"""M05 capacity repository over the production file-backed SQLite boundary."""

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
from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV1,
    CapacityCommitReceiptV1,
    CapacityCommitRequestV1,
    CapacityCommitStatusV1,
    CapacityHealthViewV1,
    CapacityObservationProvenanceViewV1,
    CapacitySubjectV1,
    ExactMetricFieldV1,
    QuotaWindowViewV1,
)
from agentmonitor.contracts.common_quantity_v1 import (
    CanonicalDecimalV1,
    ExactQuantityV1,
)
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
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
        provenance=CapacityObservationProvenanceViewV1(
            capability_id=str(row["capability_id"]),
            capability_schema_version=str(row["capability_schema_version"]),
            adapter_id=str(row["adapter_id"]),
            adapter_version=str(row["adapter_version"]),
            provider_protocol_version=str(row["provider_protocol_version"]),
            source_id=str(row["source_id"]),
            source_class=row["source_class"],
            mechanism_version=str(row["mechanism_version"]),
            parser_version=(
                str(row["parser_version"])
                if row["parser_version"] is not None
                else None
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
            precision=row["precision"],
            confidence=row["confidence"],
            confidence_reason_code=str(row["confidence_reason_code"]),
            is_experimental=bool(row["experimental"]),
            decision_reference=str(row["decision_reference"]),
        ),
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
    )


class SqliteCapacityRepositoryV1:
    """Commits immutable quota observations and an idempotent durable receipt."""

    CONSUMER_KEY = "capacity"
    CONSUMER_VERSION = "1.0.0"

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

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
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT p.projection_id, p.account_id, p.resource_id, p.freshness_state, d.provider_key, "
                            "d.installation_id, d.native_window_key, d.safe_label, "
                            "o.observation_id, o.collection_run_id, o.observed_at, "
                            "o.collected_at, o.stored_at, p.freshness_deadline, "
                            "p.capability_id, o.capability_schema_version, "
                            "v.adapter_id, v.adapter_version, v.provider_protocol_version, "
                            "v.source_id, v.source_class, v.mechanism_version, "
                            "v.parser_version, v.provider_version, v.freshness_policy_id, "
                            "v.precision, v.confidence, v.confidence_reason_code, "
                            "v.experimental, v.decision_reference, p.conflict_state FROM "
                            "capacity_current_projection AS p JOIN "
                            "capacity_quota_window_definition AS d ON "
                            "d.window_definition_id=p.window_definition_id JOIN "
                            "capacity_quota_observation AS o ON "
                            "o.observation_id=p.current_observation_id JOIN "
                            "capacity_observation_provenance AS v ON "
                            "v.provenance_id=o.provenance_id WHERE "
                            "p.projection_kind='quota' AND p.account_id=? AND "
                            "p.resource_id=? AND p.capability_id=? AND "
                            "o.collected_at<=? ORDER BY d.native_window_key",
                            (
                                account_id.value,
                                resource_id.value,
                                capability_id,
                                _utc_text(as_of),
                            ),
                        )
                        .mappings()
                        .all()
                    )
                    return tuple(_quota_window(connection, row, as_of) for row in rows)
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
                            "capacity_quota_observation o ON "
                            "o.observation_id=p.current_observation_id WHERE "
                            "p.projection_kind='quota' AND p.account_id=? AND "
                            "o.collected_at<=? ORDER BY p.resource_id, "
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
        if type(page_size) is not int or not 1 <= page_size <= 201:
            raise CapacityRepositoryErrorV1("capacity_query_invalid")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT p.projection_id, p.account_id, p.resource_id, p.freshness_state, "
                            "d.provider_key, d.installation_id, d.native_window_key, d.safe_label, "
                            "o.observation_id, o.collection_run_id, o.observed_at, o.collected_at, "
                            "o.stored_at, p.freshness_deadline, p.capability_id, "
                            "o.capability_schema_version, v.adapter_id, v.adapter_version, "
                            "v.provider_protocol_version, v.source_id, v.source_class, "
                            "v.mechanism_version, v.parser_version, v.provider_version, "
                            "v.freshness_policy_id, v.precision, v.confidence, "
                            "v.confidence_reason_code, v.experimental, v.decision_reference, "
                            "p.conflict_state FROM "
                            "capacity_current_projection AS p JOIN capacity_quota_window_definition AS d "
                            "ON d.window_definition_id=p.window_definition_id JOIN capacity_quota_observation AS o "
                            "ON o.observation_id=p.current_observation_id JOIN "
                            "capacity_observation_provenance AS v ON "
                            "v.provenance_id=o.provenance_id WHERE p.projection_kind='quota' "
                            "AND p.account_id=? AND o.collected_at<=? AND (? IS NULL OR "
                            "(p.resource_id, d.native_window_key, p.projection_id) > ("
                            "SELECT p2.resource_id, d2.native_window_key, p2.projection_id FROM "
                            "capacity_current_projection p2 JOIN capacity_quota_window_definition d2 "
                            "ON d2.window_definition_id=p2.window_definition_id WHERE p2.projection_id=?)) "
                            "ORDER BY p.resource_id, d.native_window_key, p.projection_id LIMIT ?",
                            (
                                account_id.value,
                                _utc_text(as_of),
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
                    explanations = json.loads(str(row["explanation_codes_json"]))
                    if not isinstance(explanations, list) or not all(
                        isinstance(value, str) for value in explanations
                    ):
                        raise CapacityRepositoryErrorV1()
                    return CapacityHealthViewV1(
                        state=row["health_state"],
                        completeness=row["completeness"],
                        freshness=(
                            "stale"
                            if row["valid_until"] is not None
                            and _utc_value(str(row["valid_until"])) <= as_of
                            else row["freshness_state"]
                        ),
                        constraining_window_id=(
                            str(row["constraining_window_definition_id"])
                            if row["constraining_window_definition_id"] is not None
                            else None
                        ),
                        policy_id=str(row["policy_id"]),
                        policy_version=str(row["policy_version"]),
                        explanation_codes=tuple(explanations),
                    )
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
            observed = provenance.observed_at or provenance.collected_at
            observed_text = _utc_text(observed)
            reset_text = (
                _utc_text(window.reset_at) if window.reset_at is not None else None
            )
            safe_label_state = (
                "available" if window.safe_label is not None else "unknown"
            )
            latest_definition = (
                connection.exec_driver_sql(
                    "SELECT * FROM capacity_quota_window_definition WHERE "
                    "provider_key=? AND resource_id=? AND capability_id=? AND "
                    "identity_scheme_version=1 AND native_window_key=? ORDER BY "
                    "definition_version DESC LIMIT 1",
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
                )
            )
            if same_semantics and latest_definition is not None:
                window_definition_id = str(latest_definition["window_definition_id"])
                definition_version = int(latest_definition["definition_version"])
                connection.exec_driver_sql(
                    "UPDATE capacity_quota_window_definition SET "
                    "last_observed_at=?, updated_at=? WHERE window_definition_id=?",
                    (observed_text, stored_text, window_definition_id),
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
                    "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 'active', ?, ?, ?, ?, "
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
                        window.safe_label,
                        safe_label_state,
                        window.semantic_role,
                        native_unit,
                        reset_text,
                        window.reset_precision,
                        observed_text,
                        observed_text,
                        provenance.decision_reference,
                        stored_text,
                        stored_text,
                    ),
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
            projection_ids.append(projection_id)
            freshness_state = (
                "stale"
                if provenance.freshness_availability.state == "stale"
                else "fresh"
                if provenance.freshness_deadline is not None
                else "freshness_unknown"
            )
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
            incoming_semantic = provenance.observed_at or provenance.collected_at
            if current is None or (
                current_semantic is not None and incoming_semantic > current_semantic
            ):
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
            elif (
                current_semantic == incoming_semantic
                and current["payload_digest"] != request.payload_digest
            ):
                connection.exec_driver_sql(
                    "UPDATE capacity_current_projection SET "
                    "conflict_state='conflicted', evaluated_at=?, updated_at=?, "
                    "record_version=record_version+1 WHERE projection_key=?",
                    (stored_text, stored_text, projection_key),
                )
        health_projection_id = _stable_identifier(
            "health",
            payload.subject.provider_key,
            payload.subject.account_id.value,
            payload.subject.resource_id.value,
            request.capability_id,
        )
        connection.exec_driver_sql(
            "INSERT INTO capacity_health_projection "
            "(health_projection_id, provider_key, account_id, resource_id, "
            "capability_id, subject_scope_kind, subject_scope_id, health_state, "
            "completeness, freshness_state, constraining_window_definition_id, "
            "constraining_resource_id, policy_id, policy_version, "
            "constrained_coefficient, constrained_scale, critical_coefficient, "
            "critical_scale, availability_signal_id, "
            "availability_signal_generation, input_set_digest, derivation_id, "
            "explanation_codes_json, evaluated_at, valid_until, updated_at, "
            "projected_at, record_version) VALUES (?, ?, ?, ?, ?, 'resource', ?, "
            "'unknown', ?, ?, NULL, NULL, 'capacity-health-unconfigured', '1.0.0', "
            "NULL, NULL, NULL, NULL, NULL, NULL, ?, NULL, ?, ?, NULL, ?, ?, 1) "
            "ON CONFLICT(provider_key, account_id, resource_id, capability_id) "
            "DO UPDATE SET completeness=excluded.completeness, "
            "freshness_state=excluded.freshness_state, "
            "input_set_digest=excluded.input_set_digest, "
            "explanation_codes_json=excluded.explanation_codes_json, "
            "evaluated_at=excluded.evaluated_at, updated_at=excluded.updated_at, "
            "projected_at=excluded.projected_at, "
            "record_version=capacity_health_projection.record_version+1",
            (
                health_projection_id,
                payload.subject.provider_key,
                payload.subject.account_id.value,
                payload.subject.resource_id.value,
                request.capability_id,
                payload.subject.resource_id.value,
                ("complete" if payload.completeness == "complete_scope" else "partial"),
                (
                    "stale"
                    if provenance.freshness_availability.state == "stale"
                    else "fresh"
                    if provenance.freshness_deadline is not None
                    else "freshness_unknown"
                ),
                request.payload_digest,
                '["no_configured_health_policy"]',
                stored_text,
                stored_text,
                stored_text,
            ),
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
