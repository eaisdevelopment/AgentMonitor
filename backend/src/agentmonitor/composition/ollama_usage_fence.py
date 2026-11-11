"""Transaction-bound existing cloud authority and shared rate lease for usage."""

from datetime import UTC, datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    ollama_cloud_admission as cloud_admission,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.budget import (
    require_cloud_budget_commit_authority,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    ensure_access_target_in_transaction,
    ensure_active_binding_in_transaction,
    ensure_cloud_target_graph_in_transaction,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
)
from agentmonitor.contracts.capacity_v1 import BudgetCollectionInputV1
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
    OllamaCloudRequestLeaseV1,
)
from agentmonitor.contracts.registry_v1 import (
    CloudMonitoringTargetV1,
    ProviderAccessTargetV1,
)
from sqlalchemy.engine import Connection


def cloud_usage_fence(
    connection: Connection,
    graph: CloudMonitoringTargetV1,
    service: ProviderAccessTargetV1,
    context: CloudBudgetReportContextV1,
) -> None:
    """Use M02-owned fences; no shadow account, secret or provider verification."""
    if (
        context.scope not in {"self", "team"}
        or graph.access_target_id != service.access_target_id
        or service.authority_id != "ollama.com"
        or service.manifest_fingerprint != ollama_cloud_probe_fingerprint()
        or ensure_access_target_in_transaction(connection, graph.access_target_id)
        != service
    ):
        raise ValueError("ollama_usage_authority_changed")
    ensure_active_binding_in_transaction(connection, graph.binding)
    ensure_cloud_target_graph_in_transaction(
        connection,
        account_id=graph.account_id,
        profile_id=graph.profile_id,
        resource_id=graph.resource_id,
        access_target_id=graph.access_target_id,
        binding=graph.binding,
    )


def usage_capacity_repository(
    reference: DatabaseRefV1,
    *,
    admission: CloudBudgetCollectionRunAdmissionV1,
    lease: OllamaCloudRequestLeaseV1,
    fencing_token: int,
) -> SqliteBudgetReportRepositoryV1:
    """Atomic report commit requires M04 ownership, live M02 graph and rate gate."""

    def fence(connection: Connection, request: BudgetCollectionInputV1) -> None:
        now = datetime.now(UTC)
        authority = require_cloud_budget_commit_authority(
            connection,
            request,
            scheduler_instance_id=admission.scheduler_instance_id,
            fencing_token=fencing_token,
            as_of=now,
        )
        if authority != (
            admission.cloud_target,
            admission.service_target,
            admission.report_context,
        ):
            raise ValueError("ollama_usage_authority_changed")
        cloud_usage_fence(connection, *authority)
        cloud_admission.ensure_ollama_lease_in_transaction(connection, lease, now)
        cloud_admission.ensure_ollama_run_in_transaction(
            connection, lease, admission, request.payload_digest, now
        )

    return SqliteBudgetReportRepositoryV1(reference, transaction_fence=fence)
