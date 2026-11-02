"""Pure compatibility checks for versioned Ollama verification enqueue ports."""

from typing import get_type_hints

from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudVerificationEnqueueV1,
    OllamaCloudVerificationEnqueueV2,
)
from agentmonitor.modules.collection_control.application import (
    ollama_cloud_admission,
)


def test_v2_enqueue_value_publishes_v2_contract_version() -> None:
    assert OllamaCloudVerificationEnqueueV1.CONTRACT_VERSION == "1.0.0"
    assert OllamaCloudVerificationEnqueueV2.CONTRACT_VERSION == "2.0.0"


def test_v1_port_is_preserved_and_v2_port_is_additive() -> None:
    assert (
        ollama_cloud_admission.OllamaCloudVerificationEnqueueRepositoryV2.CONTRACT_ID
        == "CTR-COL-010"
    )
    assert (
        ollama_cloud_admission.OllamaCloudVerificationEnqueueRepositoryV2.CONTRACT_VERSION
        == "2.0.0"
    )
    v1 = get_type_hints(
        ollama_cloud_admission.OllamaCloudAdmissionRepositoryV1.enqueue_verification
    )
    v2 = get_type_hints(
        ollama_cloud_admission.OllamaCloudVerificationEnqueueRepositoryV2.enqueue_verification_v2
    )

    assert v1["request"] is OllamaCloudVerificationEnqueueV1
    assert v2["request"] is OllamaCloudVerificationEnqueueV2
    assert hasattr(ollama_cloud_admission, "EnqueueOllamaCloudVerificationV1")
    assert hasattr(ollama_cloud_admission, "EnqueueOllamaCloudVerificationV2")
