"""Pure approved-path metadata policy; no filesystem or credential access."""

import pytest

from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    EnvCredentialFileError,
    require_safe_env_lock_metadata_v1,
    require_safe_env_parent_metadata_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)


def test_exact_parent_owner_and_process_protection_policy_is_published() -> None:
    assert ENV_AUTHORIZATION_POLICY_V1.allowed_parent_modes == (
        0o700,
        0o750,
        0o755,
        0o770,
        0o775,
    )
    assert ENV_AUTHORIZATION_POLICY_V1.required_owner == "real_uid"
    assert (
        ENV_AUTHORIZATION_POLICY_V1.core_dump_policy
        == "rlimit_core_zero_and_linux_pr_set_dumpable_zero"
    )


def test_unknown_store_failure_is_sanitized_to_closed_unavailable_code() -> None:
    error = EnvCredentialFileError("private path detail")  # type: ignore[arg-type]

    assert error.code == "ollama_cloud_store_unavailable"
    assert str(error) == "ollama_cloud_store_unavailable"


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
