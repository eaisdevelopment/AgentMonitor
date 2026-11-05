"""Actual rotated cloud graph on an owner-only SQLite copy; no provider dispatch."""

import os
import secrets
import shutil
import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
    OllamaCloudAdmissionRepositoryErrorV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_probe_fingerprint,
)
from agentmonitor.composition.ollama_cloud_verification_enqueue_v2 import (
    SqliteAtomicOllamaCloudVerificationEnqueueRepositoryV2,
)
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudVerificationReplayQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1,
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
)
from agentmonitor.modules.registry.domain.credential_binding import (
    resolve_active_credential_binding,
)

RotatedRegistry = tuple[
    DatabaseRefV1, AccountViewV1, CloudMonitoringTargetV1, ActiveCredentialBindingRefV1
]

LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


@pytest.fixture
def rotated_registry(tmp_path: Path) -> Iterator[RotatedRegistry]:
    private = tmp_path / "registry"
    private.mkdir(mode=0o700)
    copied = private / "agentmonitor.db"
    descriptor = os.open(copied, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
            with sqlite3.connect(copied) as target:
                source.backup(target)
        reference = DatabaseRefV1(copied, private)
        registry = SqliteRegistryRepositoryV1(reference)
        cloud = SqliteCloudCredentialRegistryV1(reference)
        bindings = SqliteCredentialBindingsV1(reference)
        for account in registry.list_accounts("ollama", page_size=100):
            graph = cloud.read_monitoring_target(account.account_id)
            active = resolve_active_credential_binding(
                bindings.read(account.account_id)
            )
            if (
                graph is not None
                and active is not None
                and graph.binding != active
                and account.lifecycle == "active"
                and account.is_effective_monitoring_enabled
                and cloud.read_current_verification(graph.binding) is not None
            ):
                yield reference, account, graph, active
                return
        pytest.skip("actual_rotated_cloud_binding_unavailable")
    finally:
        shutil.rmtree(private)


def _query(
    account: AccountViewV1, graph: CloudMonitoringTargetV1
) -> OllamaCloudVerificationReplayQueryV1:
    return OllamaCloudVerificationReplayQueryV1(
        OpaqueIdV1(secrets.token_urlsafe(24)),
        graph.owner_principal_id,
        account.account_id,
        account.record_version,
    )


def test_real_rotation_can_enqueue_current_binding_without_recreating_owner_graph(
    rotated_registry: RotatedRegistry,
) -> None:
    reference, account, graph, active = rotated_registry
    cloud = SqliteCloudCredentialRegistryV1(reference)
    registry = SqliteRegistryRepositoryV1(reference)
    previous_receipt = cloud.read_current_verification(graph.binding)
    query = _query(account, graph)
    initiation = SqliteAtomicOllamaCloudVerificationEnqueueRepositoryV2(reference)
    job = initiation.initiate_verification_atomically_v2(
        query,
        datetime.now(UTC),
        ollama_cloud_probe_fingerprint(),
    )
    assert job.state == "queued"
    assert job.account_id == account.account_id
    assert job.binding_generation == active.generation
    current = cloud.read_monitoring_target(account.account_id)
    assert current is not None
    assert current.binding == active
    assert current.profile_id == graph.profile_id
    assert current.resource_id == graph.resource_id
    assert current.record_version == graph.record_version + 1
    updated = registry.get_account(account.account_id)
    assert updated is not None
    assert updated.record_version == account.record_version + 1
    assert updated.organization_id == account.organization_id
    assert updated.friendly_name == account.friendly_name
    assert updated.monitoring_preference == account.monitoring_preference
    assert updated.identity_state == account.identity_state
    assert cloud.read_current_verification(graph.binding) == previous_receipt
    assert cloud.read_current_verification(active) is None
    replay = initiation.initiate_verification_atomically_v2(
        query,
        datetime.now(UTC),
        ollama_cloud_probe_fingerprint(),
    )
    assert replay == job
    replayed_account = registry.get_account(account.account_id)
    assert replayed_account is not None
    assert replayed_account.record_version == updated.record_version
    assert cloud.read_monitoring_target(account.account_id) == current


def test_real_rotated_graph_stale_account_version_is_rejected_atomically(
    rotated_registry: RotatedRegistry,
) -> None:
    reference, account, graph, active = rotated_registry
    query = replace(
        _query(account, graph),
        expected_account_record_version=account.record_version - 1,
    )
    with pytest.raises(
        OllamaCloudAdmissionRepositoryErrorV1,
        match="ollama_cloud_verification_account_version_conflict",
    ):
        SqliteAtomicOllamaCloudVerificationEnqueueRepositoryV2(
            reference
        ).initiate_verification_atomically_v2(
            query,
            datetime.now(UTC),
            ollama_cloud_probe_fingerprint(),
        )
    assert (
        SqliteCloudCredentialRegistryV1(reference).read_monitoring_target(
            account.account_id
        )
        == graph
    )
    assert (
        SqliteRegistryRepositoryV1(reference).get_account(account.account_id) == account
    )
    assert (
        resolve_active_credential_binding(
            SqliteCredentialBindingsV1(reference).read(account.account_id)
        )
        == active
    )
