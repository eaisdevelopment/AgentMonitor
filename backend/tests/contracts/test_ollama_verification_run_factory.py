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


def test_source_deadline_reserves_time_for_commit_and_cleanup() -> None:
    from agentmonitor.adapters.providers.ollama.cloud_balance.verification_run import (
        source_budget_seconds,
    )

    assert source_budget_seconds(20.0, 18.0, 30.0) == 10.0
    with pytest.raises(ValueError):
        source_budget_seconds(8.0, 20.0, 30.0)


def test_cloud_polling_target_does_not_alias_installation() -> None:
    from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
        cloud_schedule_storage_target,
    )
    from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

    cloud = ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "2" * 32))
    assert cloud_schedule_storage_target(cloud) == (
        None,
        "cloud_service",
        cloud.target_id.value,
    )
    local = ProviderTargetRefV1("provider_installation", OpaqueIdV1("installation"))
    assert cloud_schedule_storage_target(local) == ("installation", None, None)


def test_cloud_scheduled_run_uses_same_generation_scoped_target() -> None:
    from agentmonitor.adapters.providers.ollama.cloud_balance.verification_run import (
        build_scheduled_cloud_run,
    )

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
    run = build_scheduled_cloud_run(graph, oid("worker"), 7, "b" * 64, now)
    assert run.trigger == "scheduled"
    assert run.provider_target.target_kind == "cloud_service"
    assert run.target_generation == 3
    assert run.account_id == binding.account_id


def test_work_lane_alternates_from_last_durable_request() -> None:
    from agentmonitor.modules.collection_control.domain.ollama_rate_policy import (
        next_cloud_work_lane,
    )

    assert next_cloud_work_lane(None) == "verification"
    assert next_cloud_work_lane(True) == "scheduled"
    assert next_cloud_work_lane(False) == "verification"
