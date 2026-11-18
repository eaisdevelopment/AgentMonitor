"""Read current cloud usage inventory without registering or recovering work."""

import time
import uuid
from datetime import datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.api.policy import completed_period
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
)
from agentmonitor.composition.ollama_usage_run import build_ollama_usage_run
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.cloud_connection import (
    resolve_active_credential_binding,
)


def read_usage_inventory(
    reference: DatabaseRefV1,
    *,
    as_of: datetime,
    deadline_monotonic: float,
    scheduler_instance_id: OpaqueIdV1,
) -> tuple[CloudBudgetCollectionRunAdmissionV1, ...]:
    """Draft intents from owner metadata; no provider reads or database writes."""
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    bindings = SqliteCredentialBindingsV1(reference)
    cursor = None
    scanned = 0
    prepared: list[CloudBudgetCollectionRunAdmissionV1] = []
    while scanned < 1000:
        if time.monotonic() >= deadline_monotonic:
            raise ValueError("ollama_usage_inventory_deadline")
        accounts = registry.list_accounts(
            provider_key="ollama", page_size=100, after_key=cursor
        )
        scanned += len(accounts)
        for account in accounts:
            if (
                not account.is_effective_monitoring_enabled
                or account.lifecycle != "active"
            ):
                continue
            graph = cloud.read_monitoring_target(account.account_id)
            if graph is None or graph.lifecycle != "active":
                continue
            service = cloud.read_active_access_target(graph.access_target_id)
            if (
                service is None
                or service.authority_id != "ollama.com"
                or service.manifest_fingerprint != ollama_cloud_probe_fingerprint()
                or resolve_active_credential_binding(bindings.read(account.account_id))
                != graph.binding
            ):
                continue
            for scope in ("self", "team"):
                for range_key in ("7d", "30d"):
                    now = as_of
                    period = completed_period(now, range_key)
                    run = build_ollama_usage_run(
                        graph=graph,
                        service=service,
                        context=CloudBudgetReportContextV1(
                            scope, range_key, period.start, period.end
                        ),
                        registry_revision=account.registry_revision,
                        scheduler_instance_id=scheduler_instance_id,
                        run_id=OpaqueIdV1("usage-run-" + uuid.uuid4().hex),
                        request_id=OpaqueIdV1("usage-request-" + uuid.uuid4().hex),
                        requested_at=now,
                    )
                    prepared.append(run)
        if len(accounts) < 100:
            return tuple(prepared)
        cursor = accounts[-1].account_id.value
    raise ValueError("ollama_usage_target_limit")
