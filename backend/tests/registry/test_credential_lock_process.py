"""Real kernel flock survives owner death while its child retains the fd."""

import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path


def test_child_holds_lock_after_parent_death(tmp_path: Path) -> None:
    lock = tmp_path / "lock"
    script = """
import os, subprocess, sys
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    exclusive_descriptor,
)
fd = os.open(sys.argv[1], os.O_CREAT | os.O_RDWR, 0o600)
with exclusive_descriptor(fd):
    subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.buffer.read(1)"],
                     stdin=sys.stdin, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL,
                     pass_fds=(fd,))
    print("ready", flush=True)
    os._exit(0)
"""
    parent = subprocess.Popen(
        [sys.executable, "-c", script, str(lock)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
    )
    try:
        assert parent.stdout is not None and parent.stdin is not None
        assert parent.stdout.readline().strip() == "ready"
        assert parent.wait(timeout=5) == 0
        fd = os.open(lock, os.O_RDWR)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise AssertionError("lock released while child still alive")
            parent.stdin.write("x")
            parent.stdin.flush()
            deadline = time.monotonic() + 5
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    assert time.monotonic() < deadline
                    time.sleep(0.02)
        finally:
            os.close(fd)
    finally:
        if parent.stdin is not None:
            parent.stdin.close()
        if parent.stdout is not None:
            parent.stdout.close()
        if parent.poll() is None:
            parent.kill()
            parent.wait()
