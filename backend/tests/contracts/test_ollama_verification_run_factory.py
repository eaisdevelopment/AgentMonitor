from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from agentmonitor.adapters.providers.ollama.cloud_balance.verification_run import (
    build_verification_run,
)
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudRequestLeaseV1,
    OllamaCloudVerificationJobClaimV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
)


def test_run_binds_exact_claim_graph_and_owner() -> None:
    now = datetime(2026, 11, 2, tzinfo=UTC)
    oid = OpaqueIdV1
    binding = ActiveCredentialBindingRefV1(oid("account"), oid("amcb_" + "1" * 32), 3)
    graph = CloudMonitoringTargetV1(
        oid("profile"),
        oid("resource"),
        oid("account"),
        oid("amat_" + "2" * 32),
        binding,
        "active",
        "owner_confirmed",
        oid("owner"),
        now,
        1,
    )
    claim = OllamaCloudVerificationJobClaimV1(
        oid("amvj_" + "3" * 32),
        oid("worker"),
        oid("principal"),
        "a" * 64,
        oid("schedule"),
        oid("account"),
        graph.access_target_id,
        3,
        1,
        now,
        now + timedelta(seconds=45),
        1,
    )
    lease = OllamaCloudRequestLeaseV1(
        oid("admission"),
        oid("worker"),
        oid("schedule"),
        oid("account"),
        1,
        now,
        now + timedelta(seconds=40),
        now + timedelta(seconds=70),
        1,
    )
    run = build_verification_run(claim, graph, lease, 1, "b" * 64, now)
    assert run.request_principal_id == claim.request_principal_id
    assert run.idempotency_key_digest == claim.idempotency_key_digest
    assert run.provider_target.target_id == graph.access_target_id
    with pytest.raises(ValueError):
        build_verification_run(
            claim,
            replace(graph, resource_id=oid("other")),
            replace(lease, account_id=oid("other")),
            1,
            "b" * 64,
            now,
        )
