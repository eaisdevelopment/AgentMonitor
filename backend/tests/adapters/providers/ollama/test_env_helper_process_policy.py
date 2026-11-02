"""Real provider-free process policy for the credential-bearing helper."""

import subprocess
import sys
from pathlib import Path


def test_real_helper_process_disables_core_dumps() -> None:
    source = Path(__file__).resolve().parents[4] / "src"
    program = (
        "import resource; "
        "from agentmonitor.adapters.providers.ollama.cloud_balance.deadline_helper "
        "import _disable_core_dumps_v1; "
        "_disable_core_dumps_v1(); "
        "print(*resource.getrlimit(resource.RLIMIT_CORE))"
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
        env={"LC_ALL": "C.UTF-8", "PYTHONPATH": str(source)},
    )

    assert result.returncode == 0
    assert result.stdout == "0 0\n"
    assert result.stderr == ""
