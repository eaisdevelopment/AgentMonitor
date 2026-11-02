"""Real secret-tool prompt retains a lock; no key or input is provided."""

import fcntl
import os
import pty
import secrets
import subprocess
import time
from pathlib import Path

from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_command import (
    build_store_command,
)
from agentmonitor.composition.ollama_credential_enrollment import (
    secret_tool_environment,
)


def test_secret_tool_holds_inherited_lock_until_exit(tmp_path: Path) -> None:
    path = tmp_path / "lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    master, slave = pty.openpty()
    process = None
    other = None
    try:
        process = subprocess.Popen(
            build_store_command("amcb_" + secrets.token_hex(16)),
            stdin=slave,
            stdout=slave,
            stderr=slave,
            pass_fds=(fd,),
            env=secret_tool_environment(os.environ),
        )
        os.close(slave)
        slave = -1
        deadline = time.monotonic() + 3
        while not Path(f"/proc/{process.pid}/fd/{fd}").exists():
            assert process.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.02)
        os.close(fd)
        fd = -1
        other = os.open(path, os.O_RDWR)
        try:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            raise AssertionError("secret-tool did not retain the account lock")
        process.terminate()
        process.wait(timeout=5)
        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if other is not None:
            os.close(other)
        if fd >= 0:
            os.close(fd)
        if slave >= 0:
            os.close(slave)
        os.close(master)
