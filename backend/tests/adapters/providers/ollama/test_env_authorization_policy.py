"""Pure .env metadata policy; no filesystem or credential access."""

import pytest

from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    require_safe_env_file_metadata_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)


def test_owner_only_regular_bounded_env_file_is_admitted() -> None:
    require_safe_env_file_metadata_v1(
        regular=True,
        owner_uid=1000,
        current_uid=1000,
        mode=0o600,
        link_count=1,
        size=8192,
    )


@pytest.mark.parametrize(
    "override",
    (
        {"regular": False},
        {"owner_uid": 1001},
        {"mode": 0o640},
        {"link_count": 2},
        {"size": ENV_AUTHORIZATION_POLICY_V1.maximum_file_bytes + 1},
    ),
)
def test_unsafe_or_unbounded_env_file_is_rejected(
    override: dict[str, int | bool],
) -> None:
    values: dict[str, int | bool] = {
        "regular": True,
        "owner_uid": 1000,
        "current_uid": 1000,
        "mode": 0o600,
        "link_count": 1,
        "size": 8192,
    }
    values.update(override)
    with pytest.raises(ValueError, match="ollama_env_file_unsafe"):
        require_safe_env_file_metadata_v1(**values)  # type: ignore[arg-type]
