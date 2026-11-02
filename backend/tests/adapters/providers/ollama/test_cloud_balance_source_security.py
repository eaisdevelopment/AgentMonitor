"""Pure adversarial checks for sanitized Ollama cloud source boundaries."""

import subprocess
import sys
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CloudBalanceAuthorizationUnavailable,
    _retry_after,
)


def test_authorization_failure_code_is_runtime_closed() -> None:
    with pytest.raises(
        ValueError,
        match="^ollama_cloud_authorization_failure_code_invalid$",
    ) as captured:
        CloudBalanceAuthorizationUnavailable("provider-secret-marker")  # type: ignore[arg-type]

    assert captured.value.__cause__ is None
    assert "provider-secret-marker" not in repr(captured.value)


def test_valid_long_retry_after_is_not_discarded_or_truncated() -> None:
    seconds = 365 * 24 * 60 * 60 + 1

    assert _retry_after({"retry-after": (str(seconds),)}) == seconds
    assert _retry_after({"retry-after": (str(2**63 - 1),)}) == 2**63 - 1


def test_unrepresentable_retry_after_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="^ollama_cloud_retry_after_unrepresentable$",
    ):
        _retry_after({"retry-after": (str(2**63),)})


def test_malformed_retry_after_remains_fallback_eligible() -> None:
    assert _retry_after({}) is None
    assert _retry_after({"retry-after": ("not-seconds",)}) is None


def test_tls_context_ignores_environment_keylog_request(tmp_path: Path) -> None:
    backend = Path(__file__).resolve().parents[4]
    keylog = tmp_path / "must-not-exist.log"
    script = """
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    _secure_tls_context,
)
context = _secure_tls_context()
raise SystemExit(0 if context.keylog_filename is None else 7)
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend.parent,
        env={
            "PYTHONPATH": str(backend / "src"),
            "SSLKEYLOGFILE": str(keylog),
        },
        check=False,
        capture_output=True,
        timeout=5,
    )

    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr == b""
    assert not keylog.exists()
