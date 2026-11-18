"""One-report financial purge with real checkpoint and transaction-bound guards."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    _insert,
    _receipt,
    _view,
)
from agentmonitor.contracts.capacity_retention_v1 import (
    BudgetRetentionExportRecordV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetCollectionInputV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionReceiptV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import (
    BudgetRetentionCheckpointPortV1,
    OperationsParticipantReceiptV1,
    OperationsParticipantRequestV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    validate_budget_commit,
)
from agentmonitor.modules.capacity.domain.budget_codec import (
    decode_budget_provenance,
    utc_text,
)
from agentmonitor.modules.capacity.domain.budget_retention import (
    POLICY_ID,
    POLICY_VERSION,
    original_fact_values,
    referenced_report,
    request_identity,
    retention_cursor,
    retention_position,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

Guard = Callable[[Connection, tuple[BudgetCollectionReceiptV1, ...]], None]
LiveContext = Callable[[Connection, BudgetRetentionExportRecordV1], bool]

# Match the existing report context, replacing exact dates with range duration.
# Resolved credential rotations retain scope; unresolved lineages never merge.
_CONTEXT = """json_array(
 json_extract(canonical_report_json,'$.subject'),
 json_extract(canonical_report_json,'$.scope_id'),
 json_extract(canonical_report_json,'$.scope_generation'),
 CASE WHEN json_extract(canonical_report_json,'$.scope_evidence')='unresolved'
      THEN json_extract(canonical_report_json,'$.binding_id') END,
 CASE WHEN json_extract(canonical_report_json,'$.scope_evidence')='unresolved'
      THEN json_extract(canonical_report_json,'$.binding_generation') END,
 json_extract(canonical_report_json,'$.source_id'),
 json_extract(canonical_report_json,'$.source_category'),
 json_extract(canonical_report_json,'$.cost_basis'),
 json_extract(canonical_report_json,'$.grouping'),
 json_extract(canonical_report_json,'$.currency'),
 CAST(strftime('%s',requested_end) AS INTEGER)
 -CAST(strftime('%s',requested_start) AS INTEGER)
)"""
_COMPLETE = """json_extract(canonical_report_json,'$.completeness')='complete'
 AND json_extract(canonical_report_json,'$.covered_period.start')=requested_start
 AND json_extract(canonical_report_json,'$.covered_period.end')=requested_end"""


class BudgetRetentionError(ValueError):
    def __init__(self, code: str = "budget_retention_unavailable") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class _Batch:
    records: tuple[BudgetRetentionExportRecordV1, ...]
    digest: str
    generation: int
    next_cursor: str | None
    preserved: int


def _deadline(deadline: datetime) -> None:
    if datetime.now(UTC) >= deadline:
        raise BudgetRetentionError("budget_retention_deadline")


def _record(
    connection: Connection, row: RowMapping, deadline: datetime
) -> BudgetRetentionExportRecordV1:
    receipt_row = (
        connection.exec_driver_sql(
            "SELECT * FROM capacity_commit_receipt WHERE receipt_id=?",
            (row["receipt_id"],),
        )
        .mappings()
        .one()
    )
    view, receipt = _view(row), _receipt(connection, receipt_row)
    provenance = decode_budget_provenance(str(row["canonical_provenance_json"]))
    report = view.report
    if receipt_row["conflict_state"] or provenance.operation_id != receipt.run_id:
        raise BudgetRetentionError("budget_retention_report_invalid")
    validate_budget_commit(
        BudgetCollectionInputV1(
            receipt.run_id,
            receipt.target_generation,
            receipt.capability_id,
            receipt.payload_schema,
            receipt.payload_digest,
            "succeeded"
            if report.completeness == "complete"
            and report.covered_period == report.requested_period
            else "partial",
            report,
            provenance,
        )
    )
    ids_digest = hashlib.sha256(
        json.dumps(
            [fact.value for fact in receipt.fact_ids], separators=(",", ":")
        ).encode()
    ).hexdigest()
    if ids_digest != receipt_row["observation_set_digest"]:
        raise BudgetRetentionError("budget_retention_references_invalid")
    record = BudgetRetentionExportRecordV1(
        int(row["report_sequence"]),
        view,
        provenance,
        receipt,
        OpaqueIdV1(str(row["receipt_id"])),
        OpaqueIdV1(str(row["provenance_id"])),
    )
    refs = connection.exec_driver_sql(
        "SELECT ordinal,observation_kind,observation_id "
        "FROM capacity_commit_receipt_observation "
        "WHERE receipt_id=? ORDER BY ordinal",
        (record.receipt_id.value,),
    ).all()
    expected = [
        (i, "budget" if i < len(report.cost_buckets) else "usage", fact.value)
        for i, fact in enumerate(receipt.fact_ids)
    ]
    if [tuple(ref) for ref in refs] != expected:
        raise BudgetRetentionError("budget_retention_references_invalid")
    for i, fact in enumerate(receipt.fact_ids):
        _deadline(deadline)
        table, column = (
            ("capacity_budget_observation", "observation_id")
            if i < len(report.cost_buckets)
            else ("capacity_usage_bucket", "bucket_id")
        )
        match = (
            connection.exec_driver_sql(
                f"SELECT * FROM {table} WHERE {column}=?", (fact.value,)
            )
            .mappings()
            .one_or_none()
        )
        if match is None or dict(match) != original_fact_values(record, i):
            raise BudgetRetentionError("budget_retention_fact_shape_unknown")
        shared = connection.exec_driver_sql(
            "SELECT 1 FROM capacity_commit_receipt_observation "
            "WHERE observation_id=? AND receipt_id<>? LIMIT 1",
            (fact.value, record.receipt_id.value),
        ).first()
        if match is None or shared is not None:
            raise BudgetRetentionError("budget_retention_references_invalid")
        # Only the physical shape written by the budget report producer is
        # reconstructible from this export. Never delete unexported extensions.
        if i < len(report.cost_buckets):
            bucket = report.cost_buckets[i]
            measure = connection.exec_driver_sql(
                "SELECT coefficient,scale,currency,cost_kind "
                "FROM capacity_budget_signed_cost_measure WHERE observation_id=?",
                (fact.value,),
            ).all()
            unknown = connection.exec_driver_sql(
                "SELECT 1 FROM capacity_budget_measure WHERE observation_id=? LIMIT 1",
                (fact.value,),
            ).first()
            expected_measure = (
                bucket.amount.amount.coefficient,
                bucket.amount.amount.scale,
                bucket.amount.currency,
                bucket.kind,
            )
            if [tuple(value) for value in measure] != [
                expected_measure
            ] or unknown is not None:
                raise BudgetRetentionError("budget_retention_fact_shape_unknown")
        else:
            usage = report.usage_buckets[i - len(report.cost_buckets)]
            measure = connection.exec_driver_sql(
                "SELECT metric_kind,field_state,coefficient,scale,unit,precision,"
                "confidence,value_kind,reason_code,derivation_id "
                "FROM capacity_usage_measure WHERE bucket_id=?",
                (fact.value,),
            ).all()
            unknown = connection.exec_driver_sql(
                "SELECT 1 FROM capacity_usage_dimension WHERE bucket_id=? LIMIT 1",
                (fact.value,),
            ).first()
            expected_usage = (
                "quantity",
                "available",
                usage.quantity.amount.coefficient,
                usage.quantity.amount.scale,
                usage.quantity.unit,
                provenance.precision,
                provenance.confidence,
                provenance.value_kind,
                None,
                None,
            )
            if [tuple(value) for value in measure] != [
                expected_usage
            ] or unknown is not None:
                raise BudgetRetentionError("budget_retention_fact_shape_unknown")
    return record


def _protected_facts(
    connection: Connection, record: BudgetRetentionExportRecordV1, deadline: datetime
) -> bool:
    for fact in record.receipt.fact_ids:
        _deadline(deadline)
        if (
            connection.exec_driver_sql(
                "SELECT 1 FROM capacity_current_projection "
                "WHERE current_observation_id=? UNION ALL SELECT 1 "
                "FROM capacity_derivation_input WHERE input_id=? LIMIT 1",
                (fact.value, fact.value),
            ).first()
            is not None
        ):
            return referenced_report(record.receipt.fact_ids, (fact,))
        if (
            connection.exec_driver_sql(
                "SELECT 1 FROM capacity_budget_observation "
                "WHERE observation_id=? AND current_candidate=1 LIMIT 1",
                (fact.value,),
            ).first()
            is not None
        ):
            return True
    return False


def _latest(connection: Connection, record: BudgetRetentionExportRecordV1) -> bool:
    for extra in ("", " AND " + _COMPLETE):
        winner = connection.exec_driver_sql(
            f"SELECT report_id FROM capacity_budget_report WHERE {_CONTEXT}="
            f"(SELECT {_CONTEXT} FROM capacity_budget_report WHERE report_id=?)"
            f"{extra} ORDER BY collected_at DESC,stored_at DESC,report_id DESC LIMIT 1",
            (record.report.report_id.value,),
        ).scalar_one_or_none()
        if winner == record.report.report_id.value:
            return True
    return False


class SqliteBudgetRetentionV1:
    CONTRACT_ID: ClassVar[str] = "CTR-OPS-007"
    CONTRACT_VERSION: ClassVar[str] = "1.1.0"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __init__(
        self,
        database_ref: DatabaseRefV1,
        *,
        transaction_guard: Guard | None,
        live_context: LiveContext | None,
        checkpoints: BudgetRetentionCheckpointPortV1 | None,
    ) -> None:
        if (
            not callable(transaction_guard)
            or not callable(live_context)
            or checkpoints is None
        ):
            raise BudgetRetentionError("budget_retention_dependencies_required")
        self._reference = database_ref
        self._guard = transaction_guard
        self._live = live_context
        self._checkpoints = checkpoints

    def _validate(self, request: OperationsParticipantRequestV1) -> None:
        if not isinstance(request, OperationsParticipantRequestV1):
            raise BudgetRetentionError("budget_retention_request_invalid")
        request_identity(request)
        retention_position(request)
        if request.deadline <= datetime.now(UTC):
            raise BudgetRetentionError("budget_retention_deadline")
        if request.prepared_database_ref is not None or request.limit != 1:
            raise BudgetRetentionError("budget_retention_request_invalid")

    def _scan(
        self, connection: Connection, request: OperationsParticipantRequestV1
    ) -> _Batch:
        assert request.cutoff is not None
        position = retention_position(request)
        snapshot, last = (
            position
            if position is not None
            else (
                int(
                    connection.exec_driver_sql(
                        "SELECT COALESCE(MAX(report_sequence),0) "
                        "FROM capacity_budget_report"
                    ).scalar_one()
                ),
                0,
            )
        )
        rows = (
            connection.exec_driver_sql(
                "SELECT report_sequence,report_id,"
                "length(CAST(canonical_report_json AS BLOB)) AS size "
                "FROM capacity_budget_report WHERE report_sequence>? "
                "AND report_sequence<=? AND stored_at<? AND requested_end<? "
                "ORDER BY report_sequence LIMIT 100",
                (last, snapshot, utc_text(request.cutoff), utc_text(request.cutoff)),
            )
            .mappings()
            .all()
        )
        evidence: list[object] = [request_identity(request), snapshot, last]
        records: tuple[BudgetRetentionExportRecordV1, ...] = ()
        preserved = 0
        for metadata in rows:
            if datetime.now(UTC) >= request.deadline:
                raise BudgetRetentionError("budget_retention_deadline")
            last = int(metadata["report_sequence"])
            if not 2 <= int(metadata["size"]) <= 16777216:
                raise BudgetRetentionError("budget_retention_report_invalid")
            row = (
                connection.exec_driver_sql(
                    "SELECT * FROM capacity_budget_report WHERE report_sequence=?",
                    (last,),
                )
                .mappings()
                .one()
            )
            record = _record(connection, row, request.deadline)
            live = self._live(connection, record)
            if type(live) is not bool:
                raise BudgetRetentionError("budget_retention_authority_unknown")
            protected = (
                _protected_facts(connection, record, request.deadline)
                or live
                and _latest(connection, record)
            )
            safe = True
            try:
                self._guard(connection, (record.receipt,))
            except ValueError as error:
                if str(error) not in {
                    "budget_retention_run_unsafe",
                    "budget_retention_references_unsafe",
                }:
                    raise
                safe = False
            if not connection.in_transaction():
                raise BudgetRetentionError("budget_retention_transaction_invalid")
            evidence.append(
                [
                    last,
                    hashlib.sha256(
                        str(row["canonical_report_json"]).encode()
                    ).hexdigest(),
                    hashlib.sha256(
                        str(row["canonical_provenance_json"]).encode()
                    ).hexdigest(),
                    record.receipt.payload_digest,
                    [fact.value for fact in record.receipt.fact_ids],
                    live,
                    protected,
                    safe,
                ]
            )
            if not protected and safe:
                records = (record,)
                break
            preserved += 1
        more = (
            connection.exec_driver_sql(
                "SELECT 1 FROM capacity_budget_report "
                "WHERE report_sequence>? AND report_sequence<=? "
                "AND stored_at<? AND requested_end<? LIMIT 1",
                (last, snapshot, utc_text(request.cutoff), utc_text(request.cutoff)),
            ).first()
            is not None
        )
        cursor = retention_cursor(request, snapshot, last) if more else None
        digest = hashlib.sha256(
            json.dumps(evidence, separators=(",", ":")).encode()
        ).hexdigest()
        # This is the bounded scan generation, not a global database revision.
        # Exact preview/reference equality is fenced separately by the digest.
        return _Batch(records, digest, snapshot + 1, cursor, preserved)

    def _read(self, request: OperationsParticipantRequestV1) -> _Batch:
        self._validate(request)
        try:
            with open_sqlite_database(self._reference, "runtime_read_write") as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    batch = self._scan(connection, request)
                    connection.rollback()
                    return batch
        except (SQLAlchemyError, SqlitePolicyError):
            raise BudgetRetentionError() from None

    def preview_expired(
        self, request: OperationsParticipantRequestV1
    ) -> OperationsParticipantReceiptV1:
        batch = self._read(request)
        return self._receipt(request, batch, datetime.now(UTC))

    def query_export_records(
        self, request: OperationsParticipantRequestV1
    ) -> tuple[BudgetRetentionExportRecordV1, ...]:
        batch = self._read(request)
        if request.preview_digest != batch.digest:
            raise BudgetRetentionError("budget_retention_preview_changed")
        return batch.records

    @staticmethod
    def _receipt(
        request: OperationsParticipantRequestV1, batch: _Batch, checked: datetime
    ) -> OperationsParticipantReceiptV1:
        return OperationsParticipantReceiptV1(
            "capacity",
            request.operation_id,
            "partial" if batch.next_cursor else "complete",
            batch.generation,
            batch.digest,
            len(batch.records),
            batch.next_cursor,
            checked,
            "operations_retention_batch_partial"
            if batch.next_cursor
            else "operations_retention_batch_complete",
        )

    def purge_expired(
        self, request: OperationsParticipantRequestV1
    ) -> OperationsParticipantReceiptV1:
        self._validate(request)
        assert request.cutoff is not None
        if request.preview_digest is None:
            raise BudgetRetentionError("budget_retention_checkpoint_required")
        checkpoint_id = request.checkpoint_id.value if request.checkpoint_id else None
        identity = hashlib.sha256(
            json.dumps(
                [request.operation_id.value, request.cursor], separators=(",", ":")
            ).encode()
        ).hexdigest()
        try:
            with open_sqlite_database(self._reference, "runtime_read_write") as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    prior = (
                        connection.exec_driver_sql(
                            "SELECT * FROM capacity_retention_run "
                            "WHERE idempotency_key_digest=?",
                            (identity,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if prior is not None:
                        if (
                            prior["preview_digest"] != request.preview_digest
                            or prior["export_checkpoint_ref"] != checkpoint_id
                            or prior["cutoff_at"] != utc_text(request.cutoff)
                            or prior["state"] not in {"completed", "partial"}
                        ):
                            raise BudgetRetentionError(
                                "budget_retention_idempotency_conflict"
                            )
                        return OperationsParticipantReceiptV1(
                            "capacity",
                            request.operation_id,
                            "partial" if prior["state"] == "partial" else "complete",
                            int(prior["actual_generation"]),
                            str(prior["preview_digest"]),
                            int(prior["batch_count"]),
                            prior["cursor_value"],
                            datetime.fromisoformat(str(prior["completed_at"])),
                            "operations_retention_batch_partial"
                            if prior["state"] == "partial"
                            else "operations_retention_batch_complete",
                        )
                    batch = self._scan(connection, request)
                    if request.preview_digest != batch.digest:
                        raise BudgetRetentionError("budget_retention_preview_changed")
                    if batch.records and checkpoint_id is None:
                        raise BudgetRetentionError(
                            "budget_retention_checkpoint_required"
                        )
                    if batch.records and not self._checkpoints.verify(
                        request, batch.records
                    ):
                        raise BudgetRetentionError(
                            "budget_retention_checkpoint_invalid"
                        )
                    if datetime.now(UTC) >= request.deadline:
                        raise BudgetRetentionError("budget_retention_deadline")
                    checked = datetime.now(UTC)
                    costs = usage = 0
                    for record in batch.records:
                        self._guard(connection, (record.receipt,))
                        if not connection.in_transaction():
                            raise BudgetRetentionError(
                                "budget_retention_transaction_invalid"
                            )
                        _insert(
                            connection,
                            "capacity_budget_expired_report",
                            dict(
                                receipt_id=record.receipt_id.value,
                                report_id=record.report.report_id.value,
                                canonical_provenance_json=connection.exec_driver_sql(
                                    "SELECT canonical_provenance_json "
                                    "FROM capacity_budget_report WHERE report_id=?",
                                    (record.report.report_id.value,),
                                ).scalar_one(),
                                expired_at=utc_text(checked),
                            ),
                        )
                        costs += len(record.report.report.cost_buckets)
                        usage += len(record.report.report.usage_buckets)
                        for i, fact in enumerate(record.receipt.fact_ids):
                            _deadline(request.deadline)
                            tables = (
                                (
                                    (
                                        "capacity_budget_signed_cost_measure",
                                        "observation_id",
                                    ),
                                    ("capacity_budget_measure", "observation_id"),
                                    ("capacity_budget_observation", "observation_id"),
                                )
                                if i < len(record.report.report.cost_buckets)
                                else (
                                    ("capacity_usage_dimension", "bucket_id"),
                                    ("capacity_usage_measure", "bucket_id"),
                                    ("capacity_usage_bucket", "bucket_id"),
                                )
                            )
                            for table, column in tables:
                                connection.exec_driver_sql(
                                    f"DELETE FROM {table} WHERE {column}=?",
                                    (fact.value,),
                                )
                        connection.exec_driver_sql(
                            "DELETE FROM capacity_budget_report WHERE report_id=?",
                            (record.report.report_id.value,),
                        )
                    assert request.cutoff is not None
                    _insert(
                        connection,
                        "capacity_retention_run",
                        dict(
                            retention_run_id=identity,
                            policy_id=POLICY_ID,
                            policy_version=POLICY_VERSION,
                            cutoff_at=utc_text(request.cutoff),
                            as_of=utc_text(request.cutoff + timedelta(days=365)),
                            preview_digest=batch.digest,
                            idempotency_key_digest=identity,
                            export_checkpoint_ref=checkpoint_id,
                            expected_generation=batch.generation,
                            actual_generation=batch.generation,
                            batch_limit=1,
                            batch_count=len(batch.records),
                            state="partial" if batch.next_cursor else "completed",
                            deleted_quota_count=0,
                            deleted_budget_count=costs,
                            deleted_usage_count=usage,
                            preserved_current_count=batch.preserved,
                            cursor_kind="budget_report_sequence"
                            if batch.next_cursor
                            else None,
                            cursor_value=batch.next_cursor,
                            correlation_id=request.correlation_id.value,
                            started_at=utc_text(checked),
                            completed_at=utc_text(checked),
                            error_code=None,
                        ),
                    )
                    connection.commit()
                    return self._receipt(request, batch, checked)
        except (SQLAlchemyError, SqlitePolicyError):
            raise BudgetRetentionError() from None
