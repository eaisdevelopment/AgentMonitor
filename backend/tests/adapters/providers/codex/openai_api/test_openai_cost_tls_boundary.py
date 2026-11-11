"""Actual TLS context with a keylog environment request; no handshake or key."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]


def test_environment_cannot_enable_tls_key_logging(tmp_path: Path) -> None:
    target = tmp_path / "must-not-exist.log"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            """
import ssl
from agentmonitor.adapters.providers.codex.openai_api.source import _Connection
connection = _Connection("api.openai.com")
context = connection._context
assert context.keylog_filename is None
assert context.check_hostname is True
assert context.verify_mode == ssl.CERT_REQUIRED
assert context.cert_store_stats()["x509_ca"] > 0
connection.close()
try:
    _Connection("unapproved.invalid")
    raise AssertionError("unapproved_destination_admitted")
except ValueError:
    pass
""",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "backend/src"), "SSLKEYLOGFILE": str(target)},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not target.exists()
