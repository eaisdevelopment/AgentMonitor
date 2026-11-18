"""Compose financial retention using module-owned transaction-bound metadata."""

import asyncio
import logging
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.operations import budget_retention_checkpoint
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_retention import (
    SqliteBudgetRetentionV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    budget_retention_guard,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    read_budget_target,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    read_billing_retention_scope_in_transaction,
    resolve_billing_access_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    ensure_cloud_target_graph_in_transaction,
)
from agentmonitor.contracts.capacity_retention_v1 import BudgetRetentionExportRecordV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import (
    OperationsParticipantReceiptV1,
    OperationsParticipantRequestV1,
)
from agentmonitor.modules.capacity.application.budget_retention import (
    build_budget_retention_codec,
)
from agentmonitor.modules.operations.application.budget_retention import (
    run_budget_retention_batch,
)
from sqlalchemy.engine import Connection


def is_live_budget_context(
    connection: Connection, record: BudgetRetentionExportRecordV1
) -> bool:
    """Preserve latest readings only within the current owner-selected lineage.

    Monitoring can be disabled while its current retained reading remains valid.
    Known scopes survive credential rotation; unresolved identities do not.
    Unknown metadata errors refuse the batch rather than permitting deletion.
    """
    report = record.report.report
    if report.subject.provider_key in {"claude", "codex"}:
        current = read_billing_retention_scope_in_transaction(
            connection, report.subject.account_id, report.subject.resource_id
        )
        scope_id = report.scope_id.value if report.scope_id else None
        if (
            current is None
            or current.scope_generation != report.scope_generation
            or current.scope_id != scope_id
        ):
            return False
        if report.scope_evidence != "unresolved":
            return True
        target = resolve_billing_access_in_transaction(
            connection,
            report.subject.account_id,
            report.subject.resource_id,
            "verification",
        )
        if target is None:
            return False
        return (
            target.binding.binding_id == report.binding_id
            and target.binding.generation == report.binding_generation
        )
    if report.subject.provider_key != "ollama":
        raise ValueError("budget_retention_provider_unsupported")
    captured = read_budget_target(connection, record.receipt.run_id)
    if not isinstance(captured, tuple):
        raise ValueError("budget_retention_cloud_authority_invalid")
    graph, _, _ = captured
    if (
        graph.account_id != report.subject.account_id
        or graph.resource_id != report.subject.resource_id
        or graph.binding.binding_id != report.binding_id
        or graph.binding.generation != report.binding_generation
        or report.scope_generation != 1
        or report.scope_evidence != "unresolved"
    ):
        raise ValueError("budget_retention_cloud_authority_invalid")
    try:
        ensure_cloud_target_graph_in_transaction(
            connection,
            account_id=graph.account_id,
            profile_id=graph.profile_id,
            resource_id=graph.resource_id,
            access_target_id=graph.access_target_id,
            binding=graph.binding,
        )
    except ValueError as error:
        if getattr(error, "code", None) not in {
            "credential_binding_account_unavailable",
            "credential_binding_target_unavailable",
            "registry_credential_binding_stale",
            "registry_credential_binding_archived",
        }:
            raise
        return False
    return True


def build_budget_retention_checkpoints(
    checkpoint_root: Path,
) -> budget_retention_checkpoint.FilesystemBudgetRetentionCheckpointV1:
    return budget_retention_checkpoint.FilesystemBudgetRetentionCheckpointV1(
        checkpoint_root, codec=build_budget_retention_codec()
    )


def build_budget_retention(
    reference: DatabaseRefV1, checkpoint_root: Path
) -> SqliteBudgetRetentionV1:
    return SqliteBudgetRetentionV1(
        reference,
        transaction_guard=budget_retention_guard.ensure_budget_retention_safe_in_transaction,
        live_context=is_live_budget_context,
        checkpoints=build_budget_retention_checkpoints(checkpoint_root),
    )


class BudgetRetentionTaskV1:
    """One bounded local batch per minute; completed cycles wait one day.

    The task never calls providers or changes registry configuration. A failed
    batch starts a fresh scan next time; durable M05 audits and expiration
    markers prevent deleted facts from being processed again after restart.
    """

    def __init__(self, reference: DatabaseRefV1, checkpoint_root: Path) -> None:
        self._reference = reference
        self._checkpoint_root = checkpoint_root
        self._operation: OpaqueIdV1 | None = None
        self._cutoff: datetime | None = None
        self._cursor: str | None = None
        self._next_delay = 60
        self.last_receipt: OperationsParticipantReceiptV1 | None = None
        self.last_error: str | None = None

    def run_once(self) -> OperationsParticipantReceiptV1:
        now = datetime.now(UTC)
        if self._operation is None:
            self._operation = OpaqueIdV1("budget-retention-" + secrets.token_hex(12))
            self._cutoff = now - timedelta(days=365)
            self._cursor = None
        request = OperationsParticipantRequestV1(
            self._operation,
            self._operation,
            now + timedelta(seconds=20),
            1,
            self._cutoff,
            1,
            self._cursor,
            None,
            None,
            None,
        )
        try:
            checkpoints = build_budget_retention_checkpoints(self._checkpoint_root)
            participant = build_budget_retention(self._reference, self._checkpoint_root)
            checkpoints.cleanup_expired(as_of=now, limit=32)
            result = run_budget_retention_batch(request, participant, checkpoints)
            if result.outcome not in {"complete", "partial"}:
                raise ValueError("budget_retention_batch_incomplete")
        except Exception:
            self.last_error = "budget_retention_batch_failed"
            self._operation = None
            self._next_delay = 60
            raise
        self.last_receipt, self.last_error = result, None
        self._cursor = result.next_cursor
        self._next_delay = 60 if result.next_cursor is not None else 86400
        if result.next_cursor is None:
            self._operation = None
        return result

    async def run(self) -> None:
        await asyncio.sleep(1)
        while True:
            job = asyncio.create_task(asyncio.to_thread(self.run_once))
            try:
                await asyncio.shield(job)
            except asyncio.CancelledError:
                # Drain the bounded local transaction before lifecycle resources
                # close; cancelling a Python thread cannot roll back SQLite.
                try:
                    await asyncio.shield(job)
                except Exception:
                    pass
                raise
            except Exception:
                logging.getLogger(__name__).warning("budget_retention_batch_failed")
            await asyncio.sleep(self._next_delay)
