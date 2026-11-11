"""Compose M04 lease/run and M02 credential/scope fences for billing commits."""

from datetime import UTC, datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    require_budget_commit_authority,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    ensure_billing_access_in_transaction,
)
from agentmonitor.contracts.capacity_v1 import BudgetCollectionInputV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from sqlalchemy.engine import Connection


def billing_capacity_repository(
    reference: DatabaseRefV1,
    *,
    scheduler_instance_id: OpaqueIdV1,
    fencing_token: int,
) -> SqliteBudgetReportRepositoryV1:
    """No report can bypass either owner's current transaction-bound authority.

    This connects independent Anthropic/OpenAI billing targets. Ollama usage must
    use its existing cloud graph fence before it is wired into this factory.
    """
    if not isinstance(scheduler_instance_id, OpaqueIdV1) or (
        type(fencing_token) is not int or fencing_token < 1
    ):
        raise ValueError("budget_commit_owner_invalid")

    def fence(connection: Connection, request: BudgetCollectionInputV1) -> None:
        target = require_budget_commit_authority(
            connection,
            request,
            scheduler_instance_id=scheduler_instance_id,
            fencing_token=fencing_token,
            as_of=datetime.now(UTC),
        )
        ensure_billing_access_in_transaction(connection, target)

    return SqliteBudgetReportRepositoryV1(reference, transaction_fence=fence)
