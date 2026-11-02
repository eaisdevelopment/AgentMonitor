"""Pure compatibility checks for versioned Ollama verification enqueue ports."""

from inspect import signature
from typing import get_type_hints

from agentmonitor.adapters.persistence.integration.sqlite.ollama_cloud_verification_enqueue_v2 import (  # noqa: E501
    SqliteAtomicOllamaCloudVerificationEnqueueRepositoryV2,
)
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudVerificationEnqueueV1,
    OllamaCloudVerificationEnqueueV2,
    OllamaCloudVerificationReplayQueryV1,
)
from agentmonitor.modules.collection_control.application import (
    ollama_cloud_admission,
)
from agentmonitor.modules.collection_control.domain.ollama_verification import (
    decide_cloud_verification_replay,
)


def test_v2_enqueue_value_publishes_v2_contract_version() -> None:
    assert OllamaCloudVerificationEnqueueV1.CONTRACT_VERSION == "1.0.0"
    assert OllamaCloudVerificationEnqueueV2.CONTRACT_VERSION == "2.0.0"


def test_existing_v2_call_surface_is_preserved_and_atomic_port_is_additive() -> None:
    assert (
        ollama_cloud_admission.OllamaCloudVerificationAtomicEnqueueRepositoryV2.CONTRACT_ID
        == "CTR-COL-010"
    )
    assert (
        ollama_cloud_admission.OllamaCloudVerificationAtomicEnqueueRepositoryV2.CONTRACT_VERSION
        == "2.0.0"
    )
    existing = get_type_hints(
        ollama_cloud_admission.OllamaCloudAdmissionRepositoryV1.enqueue_verification
    )
    atomic = get_type_hints(
        ollama_cloud_admission.OllamaCloudVerificationAtomicEnqueueRepositoryV2.enqueue_verification_atomically_v2
    )

    assert existing["request"] is OllamaCloudVerificationEnqueueV2
    assert atomic["request"] is OllamaCloudVerificationEnqueueV2
    assert tuple(
        signature(
            ollama_cloud_admission.EnqueueOllamaCloudVerificationV2.__call__
        ).parameters
    ) == ("self", "request")
    assert tuple(
        signature(
            ollama_cloud_admission.AtomicallyEnqueueOllamaCloudVerificationV2.__call__
        ).parameters
    ) == (
        "self",
        "request",
        "authority_account_record_version",
        "binding",
        "expected_manifest_fingerprint",
    )


def test_replay_identity_excludes_server_derived_graph_values() -> None:
    """The first call freezes target/binding; replay uses only external identity."""
    hints = get_type_hints(
        ollama_cloud_admission.OllamaCloudAdmissionRepositoryV1.enqueue_verification
    )
    assert hints["request"] is OllamaCloudVerificationEnqueueV2
    assert tuple(signature(decide_cloud_verification_replay).parameters) == (
        "existing_account_id",
        "existing_expected_account_record_version",
        "request_account_id",
        "request_expected_account_record_version",
    )


def test_atomic_initiation_port_checks_replay_before_server_derived_work() -> None:
    """The transaction coordinator starts from external request identity only."""
    assert (
        ollama_cloud_admission.OllamaCloudVerificationAtomicInitiationRepositoryV2.CONTRACT_ID
        == "CTR-COL-010"
    )
    assert (
        ollama_cloud_admission.OllamaCloudVerificationAtomicInitiationRepositoryV2.OWNER
        == "PLAN-M04"
    )
    assert SqliteAtomicOllamaCloudVerificationEnqueueRepositoryV2.OWNER == "PLAN-M04"
    atomic = get_type_hints(
        ollama_cloud_admission.OllamaCloudVerificationAtomicInitiationRepositoryV2.initiate_verification_atomically_v2
    )
    assert atomic["query"] is OllamaCloudVerificationReplayQueryV1
    assert tuple(
        signature(
            ollama_cloud_admission.AtomicallyInitiateOllamaCloudVerificationV2.__call__
        ).parameters
    ) == (
        "self",
        "query",
        "requested_at",
        "expected_manifest_fingerprint",
    )
