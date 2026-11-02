"""Pure service-argument policy without reading deployment files."""

from pathlib import Path

import pytest

from agentmonitor.composition.ollama_credential_operator import selected_env_from_argv


def test_service_selection_requires_one_exact_env_path() -> None:
    selected = selected_env_from_argv(
        ("python", "--credential-env-file", "/opt/agentmonitor/.env")
    )
    assert selected == Path("/opt/agentmonitor/.env")
    with pytest.raises(ValueError):
        selected_env_from_argv(("python",))
    with pytest.raises(ValueError):
        selected_env_from_argv(
            (
                "python",
                "--credential-env-file",
                "/a/.env",
                "--credential-env-file",
                "/b/.env",
            )
        )
