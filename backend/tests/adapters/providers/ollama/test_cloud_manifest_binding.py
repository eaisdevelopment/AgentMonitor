"""A pending provider manifest cannot be used as proof of cloud support."""

import pytest
from agentmonitor.composition.ollama_cloud_collection import require_cloud_manifest


def test_current_manifest_does_not_authorize_cloud_quota() -> None:
    with pytest.raises(ValueError, match="ollama_cloud_manifest_not_admitted"):
        require_cloud_manifest()
