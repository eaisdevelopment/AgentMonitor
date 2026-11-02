"""A credential-required writer must receive a credential fence."""

import pytest
from agentmonitor.modules.capacity.domain.credential_fence import require_capacity_fence


def test_writer_policy_rejects_missing_required_fence() -> None:
    with pytest.raises(ValueError, match="capacity_credential_fence_required"):
        require_capacity_fence(True, False)
    require_capacity_fence(True, True)
    require_capacity_fence(False, False)
