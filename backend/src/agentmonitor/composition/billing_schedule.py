"""Bounded 7/30-day API cost scheduling over public M02/M04 ports."""

import hashlib
import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    CollectionRepositoryErrorV1,
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingAccessRepositoryV1,
    SqliteBillingConnectionRepositoryV1,
    ensure_billing_access_in_transaction,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.billing_context import completed_billing_cost_context
from agentmonitor.composition.billing_run import (
    ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
    anthropic_cost_manifest_fingerprint,
    build_anthropic_billing_run,
)
from agentmonitor.composition.openai_billing_run import (
    OPENAI_COST_AUTHORITY_ID_V1,
    OPENAI_COST_COLLECTION_POLICY_VERSION_V1,
    build_openai_billing_run,
    openai_cost_manifest_fingerprint,
)
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetReportContextV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import BillingAccessTargetV1
from agentmonitor.contracts.registry_v1 import ProviderAccessTargetV1
from agentmonitor.modules.registry.application.accounts import ListAccountsV1


@dataclass(frozen=True, slots=True)
class BillingScheduleIntentV1:
    target: BillingAccessTargetV1
    window_start: datetime
    due_at: datetime
    run_id: OpaqueIdV1
    schedule_id: OpaqueIdV1
    request_id: OpaqueIdV1
    retry_chain_id: OpaqueIdV1
    producer_id: OpaqueIdV1
    correlation_id: OpaqueIdV1
    report_context: BillingBudgetReportContextV1


def _digest(*values: str) -> str:
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


def billing_schedule_intent(
    target: BillingAccessTargetV1, as_of: datetime, *, range_key: str = "7d"
) -> BillingScheduleIntentV1:
    """Stable window identity does not replace the actual admission timestamp."""
    if (
        target.purpose != "monitoring"
        or target.connection.provider_key not in {"claude", "codex"}
        or as_of.utcoffset() != timedelta(0)
    ):
        raise ValueError("billing_schedule_target_invalid")
    if range_key not in {"7d", "30d"}:
        raise ValueError("billing_schedule_range_invalid")
    connection = target.connection
    window = as_of.replace(minute=(as_of.minute // 15) * 15, second=0, microsecond=0)
    identity = _digest(
        f"anthropic-scheduled-cost-{range_key}-v1"
        if connection.provider_key == "claude"
        else f"openai-scheduled-cost-{range_key}-v1",
        ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1
        if connection.provider_key == "claude"
        else OPENAI_COST_COLLECTION_POLICY_VERSION_V1,
        connection.account_id.value,
        connection.resource_id.value,
        str(connection.record_version),
        str(connection.scope_generation),
        target.binding.binding_id.value,
        str(target.binding.generation),
        anthropic_cost_manifest_fingerprint()
        if connection.provider_key == "claude"
        else openai_cost_manifest_fingerprint(),
    )
    tick = _digest(identity, window.isoformat())
    return BillingScheduleIntentV1(
        target,
        window,
        window + timedelta(seconds=int(identity[:8], 16) % 60),
        OpaqueIdV1("billing-periodic-run-" + tick[:40]),
        OpaqueIdV1("billing-periodic-schedule-" + identity[:40]),
        OpaqueIdV1("billing-periodic-request-" + tick[:40]),
        OpaqueIdV1("billing-periodic-retry-" + tick[:40]),
        OpaqueIdV1("billing-periodic-producer-" + tick[:40]),
        OpaqueIdV1("billing-periodic-correlation-" + tick[:40]),
        completed_billing_cost_context(as_of, range_key=range_key),
    )


def due_billing_targets(
    candidates: tuple[tuple[BillingAccessTargetV1, str, datetime | None], ...],
    as_of: datetime,
) -> tuple[BillingScheduleIntentV1, ...]:
    """Oldest attempt first; a Check also consumes this window's refresh."""
    selected: list[tuple[datetime, str, BillingScheduleIntentV1]] = []
    for target, range_key, latest in candidates:
        intent = billing_schedule_intent(target, as_of, range_key=range_key)
        if latest is not None and (
            latest.utcoffset() != timedelta(0) or latest > as_of
        ):
            raise ValueError("billing_schedule_time_invalid")
        if as_of >= intent.due_at and (latest is None or latest < intent.window_start):
            selected.append(
                (
                    latest or datetime.min.replace(tzinfo=UTC),
                    intent.schedule_id.value,
                    intent,
                )
            )
    return tuple(item[2] for item in sorted(selected, key=lambda item: item[:2]))


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if not math.isfinite(remaining) or remaining <= 5:
        raise ValueError("billing_schedule_deadline_exceeded")
    return remaining


class BillingScheduleV1:
    """Read current billing authority and admit one selected due resource."""

    def __init__(self, reference: DatabaseRefV1) -> None:
        self._accounts = ListAccountsV1(SqliteRegistryRepositoryV1(reference))
        self._connections = SqliteBillingConnectionRepositoryV1(reference)
        self._access = SqliteBillingAccessRepositoryV1(reference)
        self._targets = SqliteCloudCredentialRegistryV1(reference)
        self._runs = SqliteCollectionRepositoryV1(
            reference, billing_admission_fence=ensure_billing_access_in_transaction
        )

    def read_targets(
        self, *, deadline_monotonic: float
    ) -> tuple[BillingAccessTargetV1, ...]:
        """Current authority for queued checks as well as monitored resources."""
        _remaining(deadline_monotonic)
        as_of = datetime.now(UTC)
        targets: list[BillingAccessTargetV1] = []
        seen: set[OpaqueIdV1] = set()
        cursor: str | None = None
        while True:
            _remaining(deadline_monotonic)
            page = self._accounts.page(None, as_of=as_of, limit=200, after_key=cursor)
            if page.availability.state != "available":
                raise ValueError("billing_schedule_inventory_unavailable")
            for account in page.items:
                _remaining(deadline_monotonic)
                if account.account_id in seen:
                    raise ValueError("billing_schedule_inventory_changed")
                seen.add(account.account_id)
                if account.provider_key not in {
                    "claude",
                    "codex",
                } or account.lifecycle not in {"pending", "active"}:
                    continue
                metadata = self._connections.get(account.account_id)
                if metadata is None or not metadata.connections:
                    continue
                connection = metadata.connections[0]
                target = self._access.resolve(
                    account.account_id, connection.resource_id, "monitoring"
                ) or self._access.resolve(
                    account.account_id, connection.resource_id, "verification"
                )
                if target is not None:
                    targets.append(target)
            if not page.has_more:
                break
            if len(seen) >= 2000:
                raise ValueError("billing_schedule_inventory_overflow")
            if page.next_key is None or page.next_key == cursor:
                raise ValueError("billing_schedule_inventory_changed")
            cursor = page.next_key
        return tuple(targets)

    def service_target(self, target: BillingAccessTargetV1) -> ProviderAccessTargetV1:
        is_openai = target.connection.provider_key == "codex"
        return self._targets.reconcile_access_target(
            provider_key=target.connection.provider_key,
            authority_id=OPENAI_COST_AUTHORITY_ID_V1
            if is_openai
            else "anthropic.analytics",
            manifest_fingerprint=openai_cost_manifest_fingerprint()
            if is_openai
            else anthropic_cost_manifest_fingerprint(),
            as_of=datetime.now(UTC),
        )

    def due_intents(
        self, targets: tuple[BillingAccessTargetV1, ...], *, as_of: datetime
    ) -> tuple[BillingScheduleIntentV1, ...]:
        candidates: list[tuple[BillingAccessTargetV1, str, datetime | None]] = []
        for target in targets:
            if target.purpose != "monitoring":
                continue
            connection = target.connection
            for range_key in ("7d", "30d"):
                context = completed_billing_cost_context(as_of, range_key=range_key)
                latest = self._runs.get_latest_budget_run(
                    connection.account_id,
                    connection.resource_id,
                    connection.scope_generation,
                    as_of,
                    report_context=context,
                )
                candidates.append(
                    (target, range_key, None if latest is None else latest.requested_at)
                )
        return due_billing_targets(tuple(candidates), as_of)

    def enqueue_due(
        self, *, deadline_monotonic: float
    ) -> BudgetCollectionRunViewV1 | None:
        targets = self.read_targets(deadline_monotonic=deadline_monotonic)
        for intent in self.due_intents(targets, as_of=datetime.now(UTC)):
            result = self.enqueue_intent(intent, deadline_monotonic=deadline_monotonic)
            if result is not None:
                return result
        return None

    def enqueue_intent(
        self, intent: BillingScheduleIntentV1, *, deadline_monotonic: float
    ) -> BudgetCollectionRunViewV1 | None:
        """Admit the selected due context after rechecking current authority."""
        _remaining(deadline_monotonic)
        # Existing identity is durable even after failure; never recreate its
        # requested_at or collect repeatedly within the same report window.
        try:
            existing = self._runs.get_run(intent.run_id)
        except CollectionRepositoryErrorV1 as error:
            if error.code != "collection_run_not_found":
                raise
        else:
            if not isinstance(existing, BudgetCollectionRunViewV1):
                raise ValueError("billing_schedule_run_conflict")
            return None
        current = self._access.resolve(
            intent.target.connection.account_id,
            intent.target.connection.resource_id,
            "monitoring",
        )
        if current != intent.target:
            return None
        is_openai = current.connection.provider_key == "codex"
        service_target = self.service_target(current)
        requested_at = datetime.now(UTC)
        if (
            billing_schedule_intent(
                current, requested_at, range_key=intent.report_context.range_key
            )
            != intent
        ):
            # UTC window changed during inventory; next wake gets a fresh
            # intent rather than assigning an old cutoff to a new request.
            return None
        remaining = min(120.0, _remaining(deadline_monotonic))
        build = build_openai_billing_run if is_openai else build_anthropic_billing_run
        admission = build(
            target=current,
            access_target=service_target,
            registry_revision=current.connection.registry_revision,
            scheduler_instance_id=intent.producer_id,
            run_id=intent.run_id,
            schedule_id=intent.schedule_id,
            request_id=intent.request_id,
            retry_chain_id=intent.retry_chain_id,
            correlation_id=intent.correlation_id,
            causation_id=None,
            trigger="scheduled",
            request_principal_id=None,
            idempotency_key_digest=None,
            report_context=intent.report_context,
            requested_at=requested_at,
            deadline_at=requested_at + timedelta(seconds=remaining),
        )
        try:
            result = self._runs.admit_run(admission)
        except CollectionRepositoryErrorV1 as error:
            if error.code in {
                "collection_budget_exhausted",
                "collection_retry_deferred",
                "collection_schedule_conflict",
                "collection_generation_conflict",
                "collection_idempotency_conflict",
            }:
                return None  # One busy/throttled scope does not block others.
            raise
        if not isinstance(result, BudgetCollectionRunViewV1):
            raise ValueError("billing_schedule_run_conflict")
        return result
