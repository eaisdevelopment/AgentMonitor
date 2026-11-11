"""Real isolated process/alarm and unconnected sink checks; no provider traffic."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]


def _child(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-c", body],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "backend/src"), "LC_ALL": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
        start_new_session=True,
    )


def test_real_worker_alarm_interrupts_and_restores() -> None:
    result = _child("""
import signal,time
from agentmonitor.adapters.providers.ollama.api.source import request_deadline
try:
    with request_deadline(time.monotonic()+0.03):
        time.sleep(0.2)
except TimeoutError:
    assert signal.getsignal(signal.SIGALRM) == signal.SIG_DFL
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0,0.0)
    print("deadline_enforced")
""")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "deadline_enforced"


def test_existing_alarm_and_non_main_thread_are_refused() -> None:
    result = _child("""
import signal,time,threading
from agentmonitor.adapters.providers.ollama.api.source import request_deadline
signal.setitimer(signal.ITIMER_REAL,2)
try:
    with request_deadline(time.monotonic()+0.1):
        raise AssertionError("existing_alarm_admitted")
except ValueError:
    assert signal.getitimer(signal.ITIMER_REAL)[0] > 1
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
outcome=[]
def run():
    try:
        with request_deadline(time.monotonic()+0.1):
            outcome.append("admitted")
    except ValueError:
        outcome.append("refused")
thread=threading.Thread(target=run)
thread.start();thread.join()
assert outcome == ["refused"]
""")
    assert result.returncode == 0, result.stderr


def test_nonfinite_deadlines_do_not_arm_an_alarm() -> None:
    result = _child("""
import signal
from agentmonitor.adapters.providers.ollama.api.source import request_deadline
for value in (float("nan"),float("inf"),-float("inf")):
    try:
        with request_deadline(value):
            raise AssertionError("nonfinite_admitted")
    except TimeoutError:
        pass
    assert signal.getsignal(signal.SIGALRM) == signal.SIG_DFL
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0,0.0)
""")
    assert result.returncode == 0, result.stderr


def test_usage_sink_refuses_empty_input_and_is_not_balance_sink() -> None:
    result = _child("""
from http.client import HTTPSConnection
from agentmonitor.adapters.providers.ollama.api.source import (
    OllamaUsageAuthorizationSinkV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CloudBalanceAuthorizationSinkV1,
)
connection=HTTPSConnection("ollama.com")
sink=OllamaUsageAuthorizationSinkV1(connection)
assert not isinstance(sink,CloudBalanceAuthorizationSinkV1)
try:
    sink.put_bearer_token(bytearray())
    raise AssertionError("empty_key_admitted")
except ValueError:
    pass
assert connection.sock is None
assert connection.__dict__.get("_buffer") == []
try:
    sink.finish()
    raise AssertionError("authorization_claimed")
except ValueError:
    pass
finally:
    sink.cancel();connection.close()
""")
    assert result.returncode == 0, result.stderr


def test_real_tls_constructor_ignores_environment_key_logging(tmp_path: Path) -> None:
    keylog = tmp_path / "must-not-be-created.log"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            """
import ssl
from agentmonitor.adapters.providers.ollama.api.source import _Connection
from agentmonitor.adapters.providers.ollama.api.policy import HOST
connection = _Connection(HOST)
try:
    assert connection.sock is None
    assert connection._context.keylog_filename is None
    assert connection._context.check_hostname
    assert connection._context.verify_mode == ssl.CERT_REQUIRED
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
