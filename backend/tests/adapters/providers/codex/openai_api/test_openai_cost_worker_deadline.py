"""Actual isolated Linux process/alarm boundary; no HTTP substitutes or keys."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]


def run_child(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", body],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "backend/src"), "LC_ALL": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
        start_new_session=True,
    )


def test_request_alarm_interrupts_actual_blocking_work_and_restores_handler() -> None:
    result = run_child("""
import signal, time
from agentmonitor.adapters.providers.codex.openai_api.source import request_deadline
before = signal.getsignal(signal.SIGALRM)
try:
    with request_deadline(time.monotonic() + 0.03):
        time.sleep(0.15)
except TimeoutError:
    assert signal.getsignal(signal.SIGALRM) == before
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    print("deadline_enforced")
""")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "deadline_enforced"


def test_request_alarm_refuses_preexisting_alarm_without_changing_it() -> None:
    result = run_child("""
import signal, time
from agentmonitor.adapters.providers.codex.openai_api.source import request_deadline
signal.setitimer(signal.ITIMER_REAL, 2)
try:
    with request_deadline(time.monotonic() + 0.1):
        print("unexpected_admission")
except ValueError:
    assert signal.getitimer(signal.ITIMER_REAL)[0] > 1
    print("existing_alarm_preserved")
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
""")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "existing_alarm_preserved"


def test_request_alarm_refuses_non_main_thread() -> None:
    result = run_child("""
import threading, time
from agentmonitor.adapters.providers.codex.openai_api.source import request_deadline
outcome = []
def run():
    try:
        with request_deadline(time.monotonic() + 0.1):
            outcome.append("unexpected_admission")
    except ValueError:
        outcome.append("refused")
thread = threading.Thread(target=run)
thread.start()
thread.join()
assert outcome == ["refused"]
""")
    assert result.returncode == 0, result.stderr


def test_request_rejects_nonfinite_deadlines_without_arming_an_alarm() -> None:
    result = run_child("""
import signal
from agentmonitor.adapters.providers.codex.openai_api.source import request_deadline
for deadline in (float("nan"), float("inf"), float("-inf")):
    try:
        with request_deadline(deadline):
            raise AssertionError("nonfinite_deadline_admitted")
    except TimeoutError:
        pass
    assert signal.getsignal(signal.SIGALRM) == signal.SIG_DFL
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
""")
    assert result.returncode == 0, result.stderr
