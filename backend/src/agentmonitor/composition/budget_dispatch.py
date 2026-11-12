"""Pure ordering of currently eligible financial work; no queue or clock state."""

from dataclasses import dataclass
from datetime import UTC, datetime

from agentmonitor.contracts.common_v1 import OpaqueIdV1


@dataclass(frozen=True, slots=True)
class BudgetWorkV1:
    # Provider, shared request scope, operation. Manual and automatic use one key.
    key: tuple[str, str, str]
    last_started_at: datetime | None
    ready_since: datetime
    queued_run_id: OpaqueIdV1 | None
    scheduled_due: bool


def ordered_budget_work(work: tuple[BudgetWorkV1, ...]) -> tuple[BudgetWorkV1, ...]:
    """Least recently served first, then ready age and a deterministic tie."""
    if len({item.key for item in work}) != len(work):
        raise ValueError("budget_dispatch_duplicate_work")
    return tuple(
        sorted(
            work,
            key=lambda item: (
                item.last_started_at or datetime.min.replace(tzinfo=UTC),
                item.ready_since,
                item.key,
            ),
        )
    )
