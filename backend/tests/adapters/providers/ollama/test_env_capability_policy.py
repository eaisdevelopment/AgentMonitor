"""Pure approved-path metadata policy; no filesystem or credential access."""

import pytest

from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    require_safe_env_lock_metadata_v1,
    require_safe_env_parent_metadata_v1,
)


def test_owner_parent_allows_documented_same_group_write_residual() -> None:
    assert require_safe_env_parent_metadata_v1(
        directory=True,
        owner_uid=1000,
        current_uid=1000,
        mode=0o775,
    )
    assert not require_safe_env_parent_metadata_v1(
        directory=True,
        owner_uid=1000,
        current_uid=1000,
        mode=0o700,
    )


@pytest.mark.parametrize(
    "override",
    (
        {"directory": False},
        {"owner_uid": 1001},
        {"mode": 0o777},
    ),
)
def test_unsafe_parent_is_rejected(override: dict[str, int | bool]) -> None:
    values: dict[str, int | bool] = {
        "directory": True,
        "owner_uid": 1000,
        "current_uid": 1000,
        "mode": 0o755,
    }
    values.update(override)
    with pytest.raises(ValueError, match="ollama_env_parent_unsafe"):
        require_safe_env_parent_metadata_v1(**values)  # type: ignore[arg-type]


def test_global_lock_requires_one_owner_only_regular_inode() -> None:
    require_safe_env_lock_metadata_v1(
        regular=True,
        owner_uid=1000,
        current_uid=1000,
        mode=0o600,
        link_count=1,
    )
    with pytest.raises(ValueError, match="ollama_env_lock_unsafe"):
        require_safe_env_lock_metadata_v1(
            regular=True,
            owner_uid=1000,
            current_uid=1000,
            mode=0o640,
            link_count=1,
        )
