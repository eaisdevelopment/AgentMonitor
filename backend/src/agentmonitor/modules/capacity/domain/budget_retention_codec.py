"""Closed, canonical M05 retention records; no I/O or foreign-module internals."""

import json
from dataclasses import fields
from datetime import datetime
from typing import ClassVar

from agentmonitor.contracts.capacity_retention_v1 import BudgetRetentionExportRecordV1
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionReceiptV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_codec import (
    budget_report_digest,
    decode_budget_provenance,
    decode_budget_report,
    encode_budget_provenance,
    encode_budget_report,
    utc_text,
)

MAX_RECORD_BYTES = 24 * 1024 * 1024 - 16384


def _json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


class BudgetRetentionCodecV1:
    CONTRACT_ID: ClassVar[str] = "CTR-CAP-002"
    CONTRACT_VERSION: ClassVar[str] = "2.2.0"
    OWNER: ClassVar[str] = "PLAN-M05"

    def encode(self, record: BudgetRetentionExportRecordV1) -> bytes:
        if not isinstance(record, BudgetRetentionExportRecordV1):
            raise ValueError("budget_checkpoint_record_invalid")
        receipt = record.receipt
        if receipt.payload_digest != budget_report_digest(record.report.report):
            raise ValueError("budget_checkpoint_record_invalid")
        line = {
            "schema": "agentmonitor-budget-retention-record-v1",
            "report_sequence": record.report_sequence,
            "report_id": record.report.report_id.value,
            "stored_at": utc_text(record.report.stored_at),
            "receipt_id": record.receipt_id.value,
            "provenance_id": record.provenance_id.value,
            "report": json.loads(encode_budget_report(record.report.report)),
            "provenance": json.loads(encode_budget_provenance(record.provenance)),
            "receipt": {
                "run_id": receipt.run_id.value,
                "target_generation": receipt.target_generation,
                "capability_id": receipt.capability_id,
                "payload_schema": receipt.payload_schema,
                "payload_digest": receipt.payload_digest,
                "consumer_key": receipt.consumer_key,
                "consumer_version": receipt.consumer_version,
                "report_id": receipt.report_id.value,
                "fact_ids": [fact.value for fact in receipt.fact_ids],
                "stored_at": utc_text(receipt.stored_at),
                "receipt_version": receipt.receipt_version,
            },
        }
        payload = _json(line) + b"\n"
        if len(payload) > MAX_RECORD_BYTES:
            raise ValueError("budget_checkpoint_export_too_large")
        return payload

    def decode(self, payload: bytes) -> BudgetRetentionExportRecordV1:
        try:
            if type(payload) is not bytes or not 1 <= len(payload) <= MAX_RECORD_BYTES:
                raise ValueError
            data = json.loads(payload)
            if (
                type(data) is not dict
                or set(data)
                != {
                    "schema",
                    "report_sequence",
                    "report_id",
                    "stored_at",
                    "receipt_id",
                    "provenance_id",
                    "report",
                    "provenance",
                    "receipt",
                }
                or data["schema"] != "agentmonitor-budget-retention-record-v1"
                or _json(data) + b"\n" != payload
                or type(data["receipt"]) is not dict
                or set(data["receipt"])
                != {field.name for field in fields(BudgetCollectionReceiptV1)}
                or type(data["receipt"]["fact_ids"]) is not list
                or len(data["receipt"]["fact_ids"]) > 10000
            ):
                raise ValueError
            receipt = dict(data["receipt"])
            receipt["run_id"] = OpaqueIdV1(receipt["run_id"])
            receipt["report_id"] = OpaqueIdV1(receipt["report_id"])
            receipt["fact_ids"] = tuple(
                OpaqueIdV1(value) for value in receipt["fact_ids"]
            )
            receipt["stored_at"] = datetime.fromisoformat(receipt["stored_at"])
            record = BudgetRetentionExportRecordV1(
                data["report_sequence"],
                BudgetReportViewV1(
                    OpaqueIdV1(data["report_id"]),
                    decode_budget_report(_json(data["report"]).decode("ascii")),
                    datetime.fromisoformat(data["stored_at"]),
                ),
                decode_budget_provenance(_json(data["provenance"]).decode("ascii")),
                BudgetCollectionReceiptV1(**receipt),
                OpaqueIdV1(data["receipt_id"]),
                OpaqueIdV1(data["provenance_id"]),
            )
            if self.encode(record) != payload:
                raise ValueError
            return record
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            raise ValueError("budget_checkpoint_record_invalid") from None
