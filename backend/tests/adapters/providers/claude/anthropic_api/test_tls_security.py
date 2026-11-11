"""Actual unconnected TLS construction; no network, credential or response data."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]


def test_real_tls_context_ignores_environment_key_logging(tmp_path: Path) -> None:
    keylog = tmp_path / "must-not-be-created.log"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            """
import ssl
from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    HOST, REQUEST_SECONDS,
)
from agentmonitor.adapters.providers.claude.anthropic_api.source import _Connection

connection = _Connection(HOST)
try:
    assert connection.sock is None
    assert connection._context.keylog_filename is None
    assert connection._context.protocol == ssl.PROTOCOL_TLS_CLIENT
    assert connection._context.check_hostname
    assert connection._context.verify_mode == ssl.CERT_REQUIRED
    assert connection._context.cert_store_stats()["x509_ca"] > 0
    assert connection.host == HOST
    assert connection.port == 443
    assert connection.timeout == REQUEST_SECONDS
finally:
    connection.close()
""",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "backend/src"), "SSLKEYLOGFILE": str(keylog)},
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not keylog.exists()
