"""Pure source-target decision; no database or provider I/O."""

from dataclasses import replace

import pytest
from agentmonitor.composition.ollama_capacity_commit import validate_cloud_target_fence
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderAccessTargetV1


def test_cloud_target_fence_rejects_changed_authority_and_fingerprint() -> None:
    target = ProviderAccessTargetV1(
        OpaqueIdV1("amat_" + "a" * 32),
        "ollama",
        "cloud_service",
        "ollama.com",
        "b" * 64,
        "active",
        1,
    )
    validate_cloud_target_fence(target, "b" * 64)
    with pytest.raises(ValueError):
        validate_cloud_target_fence(
            replace(target, manifest_fingerprint="c" * 64), "b" * 64
        )
    with pytest.raises(ValueError):
        validate_cloud_target_fence(
            replace(target, authority_id="other.example"), "b" * 64
        )
