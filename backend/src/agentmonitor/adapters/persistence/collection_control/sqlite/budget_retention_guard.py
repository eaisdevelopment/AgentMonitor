"""M04-owned immutable receipt linkage check in the caller's retention transaction."""

import sqlite3

from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    BudgetCollectionError,
    _utc,
)
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionReceiptV1
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError


def ensure_budget_retention_safe_in_transaction(
    connection: Connection, receipts: tuple[BudgetCollectionReceiptV1, ...]
) -> None:
    """Require finalized M04 linkage without reading or modifying another module.

    The caller must hold BEGIN IMMEDIATE until its retention transaction ends;
    this check neither starts nor commits a transaction. SQLite's Python driver
    exposes active transaction state, but not whether BEGIN was IMMEDIATE.
    The guarded M04 records cannot change while that caller-held write lock lasts.
    """
    if (
        type(receipts) is not tuple
        or not 1 <= len(receipts) <= 200
        or any(not isinstance(item, BudgetCollectionReceiptV1) for item in receipts)
        or len({item.run_id for item in receipts}) != len(receipts)
        or len({item.report_id for item in receipts}) != len(receipts)
    ):
        raise BudgetCollectionError("budget_retention_request_invalid")
    if (
        not isinstance(connection, Connection)
        or connection.closed
        or not connection.in_transaction()
    ):
        raise BudgetCollectionError("budget_retention_transaction_required")
    try:
        driver = connection.connection.driver_connection
        if not isinstance(driver, sqlite3.Connection) or not driver.in_transaction:
            raise BudgetCollectionError("budget_retention_transaction_required")
        for receipt in receipts:
            row = (
                connection.exec_driver_sql(
                    "SELECT r.run_id,r.state,r.outcome_code,r.error_code,"
                    "r.target_generation,r.capability_id,r.payload_schema,"
                    "r.payload_digest,r.requested_at,r.completed_at,"
                    "b.report_id,b.consumer_key,b.consumer_version,b.receipt_version "
                    "FROM collection_run r JOIN collection_budget_run b "
                    "ON b.run_id=r.run_id WHERE r.run_id=?",
                    (receipt.run_id.value,),
                )
                .mappings()
                .one_or_none()
            )
            if (
                row is None
                or row["state"] not in {"succeeded", "partial"}
                or row["outcome_code"] != row["state"]
                or row["error_code"] is not None
                or row["run_id"] != receipt.run_id.value
                or row["target_generation"] != receipt.target_generation
                or row["capability_id"] != receipt.capability_id
                or receipt.payload_schema != "budget.report.v1"
                or row["payload_schema"] != receipt.payload_schema
                or row["payload_digest"] != receipt.payload_digest
                or row["report_id"] != receipt.report_id.value
                or row["consumer_key"] != receipt.consumer_key
                or row["consumer_version"] != receipt.consumer_version
                or receipt.receipt_version != 1
                or row["receipt_version"] != receipt.receipt_version
                or row["completed_at"] is None
                or not row["requested_at"]
                <= _utc(receipt.stored_at)
                <= row["completed_at"]
            ):
                raise BudgetCollectionError("budget_retention_run_unsafe")
            references = connection.exec_driver_sql(
                "SELECT observation_id,consumer_key,consumer_version,receipt_version "
                "FROM collection_run_observation_ref WHERE run_id=? LIMIT 10001",
                (receipt.run_id.value,),
            ).all()
            expected = {
                (
                    fact.value,
                    receipt.consumer_key,
                    receipt.consumer_version,
                    receipt.receipt_version,
                )
                for fact in receipt.fact_ids
            }
            if (
                len(references) != len(expected)
                or {tuple(reference) for reference in references} != expected
            ):
                raise BudgetCollectionError("budget_retention_references_unsafe")
    except (SQLAlchemyError, sqlite3.Error):
        raise BudgetCollectionError("budget_retention_query_unavailable") from None
