"""Credential fencing is required only for Ollama capacity commits."""

import pytest

from agentmonitor.modules.capacity.domain.ollama_fence import require_capacity_fence


def test_ollama_capacity_requires_a_binding_fence() -> None:
    with pytest.raises(ValueError, match="ollama_credential_fence_required"):
        require_capacity_fence("ollama", False)
    require_capacity_fence("ollama", True)
    require_capacity_fence("claude", False)
    require_capacity_fence("codex", False)
