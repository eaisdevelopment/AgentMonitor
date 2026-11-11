"""M05 immutable budget reports and receipts over the real SQLite boundary."""

import base64
import hashlib
import json
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetReportHistoryQueryV1,
    BudgetReportViewV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionCommitStatusV1,
    BudgetCollectionReceiptV1,
)
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_history_page_count,
    validate_budget_commit,
)
from agentmonitor.modules.capacity.domain.budget_codec import (
    decode_budget_report,
    encode_budget_provenance,
    utc_text,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

BudgetTransactionFence = Callable[[Connection, BudgetCollectionInputV1], None]
_CONSUMER = "capacity.budget"
_VERSION = "1.0.0"


class BudgetRepositoryError(ValueError):
    """Safe repository failures never expose SQL or persisted values."""

    def __init__(self, code: str = "budget_repository_unavailable") -> None:
        self.code = code
        super().__init__(code)


def _identifier() -> str:
    return secrets.token_urlsafe(24)


def _insert(connection: Connection, table: str, values: dict[str, Any]) -> None:
    # Identifiers are exclusively fixed literals at internal call sites.
    connection.exec_driver_sql(
        f"INSERT INTO {table} ({','.join(values)}) "
        f"VALUES ({','.join('?' for _ in values)})",
        tuple(values.values()),
    )


def _selector(query: BudgetReportHistoryQueryV1) -> tuple[str, str, str, str]:
    return (
        query.account_id.value,
        query.resource_id.value,
        utc_text(query.period.start),
        utc_text(query.period.end),
    )


def _cursor(query: BudgetReportHistoryQueryV1, snapshot: int, last: int) -> str:
    data = [1, *_selector(query), snapshot, last]
    return base64.urlsafe_b64encode(
        json.dumps(data, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).decode("ascii")


def _read_cursor(query: BudgetReportHistoryQueryV1) -> tuple[int, int] | None:
    if query.after_key is None:
        return None
    try:
        data = json.loads(
            base64.b64decode(query.after_key, altchars=b"-_", validate=True)
        )
        if (
            type(data) is not list
            or len(data) != 7
            or type(data[0]) is not int
            or data[0] != 1
            or data[1:5] != list(_selector(query))
            or type(data[5]) is not int
            or type(data[6]) is not int
            or not 0 < data[6] <= data[5] <= 9223372036854775807
            or _cursor(query, data[5], data[6]) != query.after_key
        ):
            raise ValueError
        return data[5], data[6]
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise BudgetRepositoryError("budget_history_cursor_invalid") from None


def _view(row: RowMapping) -> BudgetReportViewV1:
    report = decode_budget_report(str(row["canonical_report_json"]))
    if (
        report.subject.account_id.value != row["account_id"]
        or report.subject.resource_id.value != row["resource_id"]
        or utc_text(report.requested_period.start) != row["requested_start"]
        or utc_text(report.requested_period.end) != row["requested_end"]
    ):
        raise BudgetRepositoryError("budget_report_storage_invalid")
    return BudgetReportViewV1(
        OpaqueIdV1(str(row["report_id"])),
        report,
        datetime.fromisoformat(str(row["stored_at"])),
    )


def _receipt(connection: Connection, row: RowMapping) -> BudgetCollectionReceiptV1:
    report_id = connection.exec_driver_sql(
        "SELECT report_id FROM capacity_budget_report WHERE receipt_id=?",
        (row["receipt_id"],),
    ).scalar_one_or_none()
    if report_id is None or row["consumer_key"] != _CONSUMER:
        raise BudgetRepositoryError("budget_commit_conflict")
    ids = tuple(
        OpaqueIdV1(str(value))
        for value in connection.exec_driver_sql(
            "SELECT observation_id FROM capacity_commit_receipt_observation "
            "WHERE receipt_id=? ORDER BY ordinal LIMIT 10001",
            (row["receipt_id"],),
        ).scalars()
    )
    return BudgetCollectionReceiptV1(
        OpaqueIdV1(str(row["collection_run_id"])),
        int(row["target_generation"]),
        str(row["capability_id"]),
        str(row["payload_schema"]),
        str(row["payload_digest"]),
        str(row["consumer_key"]),
        str(row["consumer_version"]),
        OpaqueIdV1(str(report_id)),
        ids,
        datetime.fromisoformat(str(row["stored_at"])),
        int(row["receipt_version"]),
    )


class SqliteBudgetReportRepositoryV1:
    """Missing fence permits reads only; every commit requires the real M02 fence.

    The injected callback must validate active binding, target generation,
    resource and scope epoch on the supplied transaction. It must not commit or
    roll back the transaction. No private M02 tables are accessed here.
    """

    def __init__(
        self,
        database_ref: DatabaseRefV1,
        *,
        transaction_fence: BudgetTransactionFence | None = None,
    ) -> None:
        self._database_ref = database_ref
        self._transaction_fence = transaction_fence

    def commit(self, request: BudgetCollectionInputV1) -> BudgetCollectionReceiptV1:
        if self._transaction_fence is None:
            raise BudgetRepositoryError("budget_transaction_fence_required")
        encoded = validate_budget_commit(request)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    self._transaction_fence(connection, request)
                    if not connection.in_transaction():
                        raise BudgetRepositoryError("budget_transaction_fence_invalid")
                    existing = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_commit_receipt "
                            "WHERE collection_run_id=? AND capability_id=?",
                            (request.run_id.value, request.capability_id),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if existing is not None:
                        if (
                            existing["target_generation"] != request.target_generation
                            or existing["payload_schema"] != request.payload_schema
                            or existing["payload_digest"] != request.payload_digest
                            or existing["conflict_state"]
                        ):
                            raise BudgetRepositoryError("budget_commit_conflict")
                        prior_provenance = connection.exec_driver_sql(
                            "SELECT canonical_provenance_json "
                            "FROM capacity_budget_report WHERE receipt_id=?",
                            (existing["receipt_id"],),
                        ).scalar_one_or_none()
                        if prior_provenance != encode_budget_provenance(
                            request.provenance
                        ):
                            raise BudgetRepositoryError("budget_commit_conflict")
                        receipt = _receipt(connection, existing)
                    else:
                        receipt = _write_report(connection, request, encoded)
                    connection.commit()
                    return receipt
        except (SqlitePolicyError, SQLAlchemyError):
            raise BudgetRepositoryError() from None

    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> BudgetCollectionCommitStatusV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_commit_receipt "
                            "WHERE collection_run_id=? AND capability_id=?",
                            (run_id.value, capability_id),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None:
                        return BudgetCollectionCommitStatusV1("not_committed", None)
                    if row["consumer_key"] != _CONSUMER or row["conflict_state"]:
                        return BudgetCollectionCommitStatusV1("conflict", None)
                    return BudgetCollectionCommitStatusV1(
                        "committed", _receipt(connection, row)
                    )
        except (SqlitePolicyError, SQLAlchemyError):
            raise BudgetRepositoryError() from None

    def get_report(
        self, account_id: OpaqueIdV1, report_id: OpaqueIdV1
    ) -> BudgetReportViewV1 | None:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_budget_report "
                            "WHERE account_id=? AND report_id=?",
                            (account_id.value, report_id.value),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    return _view(row) if row is not None else None
        except (SqlitePolicyError, SQLAlchemyError):
            raise BudgetRepositoryError() from None

    def list_reports(
        self, query: BudgetReportHistoryQueryV1
    ) -> QueryPageV1[BudgetReportViewV1]:
        cursor = _read_cursor(query)
        where = (
            "account_id=? AND resource_id=? AND requested_start=? AND requested_end=?"
        )
        selectors = _selector(query)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_only"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN")
                    snapshot = (
                        cursor[0]
                        if cursor
                        else int(
                            connection.exec_driver_sql(
                                f"SELECT COALESCE(MAX(report_sequence),0) "
                                f"FROM capacity_budget_report WHERE {where}",
                                selectors,
                            ).scalar_one()
                        )
                    )
                    last = cursor[1] if cursor else snapshot + 1
                    metadata = (
                        connection.exec_driver_sql(
                            f"SELECT report_sequence,"
                            "length(CAST(canonical_report_json AS BLOB)) AS size "
                            f"FROM capacity_budget_report WHERE {where} "
                            "AND report_sequence<=? AND report_sequence<? "
                            "ORDER BY report_sequence DESC LIMIT ?",
                            (*selectors, snapshot, last, query.limit + 1),
                        )
                        .mappings()
                        .all()
                    )
                    items: list[BudgetReportViewV1] = []
                    page_count = budget_history_page_count(
                        tuple(int(row["size"]) for row in metadata), query.limit
                    )
                    last_returned = last
                    for row in metadata[:page_count]:
                        stored = (
                            connection.exec_driver_sql(
                                f"SELECT * FROM capacity_budget_report "
                                f"WHERE {where} AND report_sequence=?",
                                (*selectors, row["report_sequence"]),
                            )
                            .mappings()
                            .one()
                        )
                        items.append(_view(stored))
                        last_returned = int(row["report_sequence"])
                    has_more = len(metadata) > len(items)
                    if has_more and not items:
                        raise BudgetRepositoryError("budget_report_storage_invalid")
                    return QueryPageV1(
                        tuple(items),
                        query.limit,
                        has_more,
                        _cursor(query, snapshot, last_returned) if has_more else None,
                        QueryAvailabilityV1(
                            "available", "budget_history_read", datetime.now(UTC)
                        ),
                    )
        except (SqlitePolicyError, SQLAlchemyError):
            raise BudgetRepositoryError() from None


def _write_report(
    connection: Connection, request: BudgetCollectionInputV1, encoded: str
) -> BudgetCollectionReceiptV1:
    report, provenance = request.payload, request.provenance
    now = datetime.now(UTC)
    if now < report.collected_at:
        raise BudgetRepositoryError("budget_collected_time_in_future")
    stored = utc_text(now)
    provenance_id, receipt_id, report_id = _identifier(), _identifier(), _identifier()
    provenance_values: dict[str, Any] = {
        name: getattr(provenance, name)
        for name in (
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
            "value_kind",
            "precision",
            "confidence",
            "confidence_reason_code",
            "freshness_policy_id",
            "decision_reference",
        )
    }
    provenance_values.update(
        provenance_id=provenance_id,
        freshness_deadline=utc_text(provenance.freshness_deadline)
        if provenance.freshness_deadline
        else None,
        experimental=int(provenance.is_experimental),
        operation_id=provenance.operation_id.value,
        correlation_id=provenance.correlation_id.value,
    )
    _insert(connection, "capacity_observation_provenance", provenance_values)
    common: dict[str, Any] = dict(
        account_id=report.subject.account_id.value,
        resource_id=report.subject.resource_id.value,
        collected_at=utc_text(report.collected_at),
        stored_at=stored,
        completeness=report.completeness,
        provenance_id=provenance_id,
        collection_run_id=request.run_id.value,
        payload_digest=request.payload_digest,
        capability_schema_version=provenance.capability_schema_version,
        observed_at=utc_text(provenance.observed_at)
        if provenance.observed_at
        else None,
        data_through_end=utc_text(report.source_data_through)
        if report.source_data_through
        else None,
    )
    facts: list[tuple[str, str]] = []
    if report.cost_buckets:
        # Identity describes reporting spend, never a cash/soft/hard budget.
        identity = json.dumps(
            [
                report.subject.provider_key,
                report.subject.account_id.value,
                report.subject.resource_id.value,
                report.scope_id.value if report.scope_id else None,
                report.scope_generation,
                report.source_id,
                report.source_category,
                report.cost_basis,
                report.currency,
                report.grouping,
            ],
            separators=(",", ":"),
        )
        definition_id = hashlib.sha256(identity.encode()).hexdigest()
        exists = connection.exec_driver_sql(
            "SELECT budget_definition_id FROM capacity_budget_definition "
            "WHERE budget_definition_id=?",
            (definition_id,),
        ).scalar_one_or_none()
        if exists is None:
            _insert(
                connection,
                "capacity_budget_definition",
                dict(
                    budget_definition_id=definition_id,
                    provider_key=report.subject.provider_key,
                    account_id=report.subject.account_id.value,
                    resource_id=report.subject.resource_id.value,
                    budget_key=definition_id,
                    identity_scheme_version=1,
                    resource_semantic="api_spend",
                    currency_state="available",
                    currency=report.currency,
                    billing_interval_semantic="reporting_interval",
                    enforcement_mapping_version="1.0.0",
                    definition_version=1,
                    lifecycle="active",
                    effective_from=utc_text(report.requested_period.start),
                    decision_reference=provenance.decision_reference,
                ),
            )
        for bucket in report.cost_buckets:
            observation_id = _identifier()
            _insert(
                connection,
                "capacity_budget_observation",
                dict(
                    common,
                    observation_id=observation_id,
                    budget_definition_id=definition_id,
                    definition_version=1,
                    observation_kind="cost_bucket",
                    billing_start=utc_text(bucket.period.start),
                    billing_end=utc_text(bucket.period.end),
                    enforcement_state="not_applicable",
                    current_candidate=0,
                ),
            )
            _insert(
                connection,
                "capacity_budget_signed_cost_measure",
                dict(
                    observation_id=observation_id,
                    coefficient=bucket.amount.amount.coefficient,
                    scale=bucket.amount.amount.scale,
                    currency=bucket.amount.currency,
                    cost_kind=bucket.kind,
                ),
            )
            facts.append(("budget", observation_id))
    for bucket_usage in report.usage_buckets:
        bucket_id = _identifier()
        _insert(
            connection,
            "capacity_usage_bucket",
            dict(
                common,
                bucket_id=bucket_id,
                bucket_start=utc_text(bucket_usage.period.start),
                bucket_end=utc_text(bucket_usage.period.end),
            ),
        )
        _insert(
            connection,
            "capacity_usage_measure",
            dict(
                bucket_id=bucket_id,
                metric_kind="quantity",
                field_state="available",
                coefficient=bucket_usage.quantity.amount.coefficient,
                scale=bucket_usage.quantity.amount.scale,
                unit=bucket_usage.quantity.unit,
                precision=provenance.precision,
                confidence=provenance.confidence,
                value_kind=provenance.value_kind,
            ),
        )
        facts.append(("usage", bucket_id))
    ids = tuple(OpaqueIdV1(value) for _, value in facts)
    _insert(
        connection,
        "capacity_commit_receipt",
        dict(
            receipt_id=receipt_id,
            collection_run_id=request.run_id.value,
            target_generation=request.target_generation,
            capability_id=request.capability_id,
            payload_schema=request.payload_schema,
            payload_digest=request.payload_digest,
            consumer_key=_CONSUMER,
            consumer_version=_VERSION,
            observation_set_digest=hashlib.sha256(
                json.dumps(
                    [value.value for value in ids], separators=(",", ":")
                ).encode()
            ).hexdigest(),
            stored_at_start=stored,
            stored_at_end=stored,
            stored_at=stored,
            created_at=stored,
            conflict_state=0,
            affected_projection_ids_json="[]",
            projection_versions_json="[]",
            event_ids_json="[]",
            receipt_version=1,
        ),
    )
    for ordinal, (kind, fact_id) in enumerate(facts):
        _insert(
            connection,
            "capacity_commit_receipt_observation",
            dict(
                receipt_id=receipt_id,
                ordinal=ordinal,
                observation_kind=kind,
                observation_id=fact_id,
            ),
        )
    _insert(
        connection,
        "capacity_budget_report",
        dict(
            report_id=report_id,
            receipt_id=receipt_id,
            provenance_id=provenance_id,
            account_id=report.subject.account_id.value,
            resource_id=report.subject.resource_id.value,
            requested_start=utc_text(report.requested_period.start),
            requested_end=utc_text(report.requested_period.end),
            collected_at=utc_text(report.collected_at),
            stored_at=stored,
            canonical_report_json=encoded,
            canonical_provenance_json=encode_budget_provenance(provenance),
        ),
    )
    return BudgetCollectionReceiptV1(
        request.run_id,
        request.target_generation,
        request.capability_id,
        request.payload_schema,
        request.payload_digest,
        _CONSUMER,
        _VERSION,
        OpaqueIdV1(report_id),
        ids,
        now,
        1,
    )
