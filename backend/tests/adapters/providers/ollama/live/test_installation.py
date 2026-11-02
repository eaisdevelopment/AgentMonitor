"""Installation discovery uses the actual local Ollama executable."""

from datetime import UTC, datetime

from agentmonitor.adapters.providers.ollama.installation import discover_installation


def test_real_local_cli_version_is_independent_of_daemon() -> None:
    started = datetime.now(UTC)
    result = discover_installation()
    completed = datetime.now(UTC)
    assert result.outcome == "success"
    assert result.cli_version == "0.24.0"
    assert result.platform_id == "linux-x86_64"
    assert started <= result.observed_at <= completed


def test_real_local_cli_is_found_with_service_search_path() -> None:
    import os
    import subprocess
    import sys
    from pathlib import Path

    checkout = Path(__file__).resolve().parents[6]
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "from agentmonitor.adapters.providers.ollama.installation import "
            "discover_installation; result=discover_installation(); "
            "print(result.outcome, result.cli_version)",
        ],
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(checkout / "backend/src"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "LANG": "C.UTF-8",
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        cwd=checkout,
    )
    assert os.path.isfile("/usr/local/bin/ollama")
    assert result.returncode == 0
    assert result.stdout.strip() == "success 0.24.0"
