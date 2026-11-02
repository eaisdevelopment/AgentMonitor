"""Real kernel flock survives owner death while its child retains the fd."""

import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.domain.credential_lock import credential_lock_name


def _reference(root: Path) -> DatabaseRefV1:
    root.chmod(0o700)
    descriptor = os.open(root / "agentmonitor.db", os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    return DatabaseRefV1(root / "agentmonitor.db", root)


def test_account_lock_rejects_replaced_directory_entry_after_flock(
    tmp_path: Path,
) -> None:
    reference = _reference(tmp_path)
    account_id = OpaqueIdV1("account-lock-replacement")

    with account_credential_lock(reference, account_id) as lease:
        path = tmp_path / credential_lock_name(account_id.value)
        path.rename(tmp_path / "displaced-account-lock")
        replacement = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(replacement)

        with pytest.raises(ValueError, match="credential_lock_replaced"):
            lease.inherited_lock(account_id)


def test_account_lock_capability_is_account_bound_and_invalidated_on_exit(
    tmp_path: Path,
) -> None:
    reference = _reference(tmp_path)
    account_id = OpaqueIdV1("account-bound-lock")
    other_account_id = OpaqueIdV1("other-account-bound-lock")

    with account_credential_lock(reference, account_id) as lease:
        inherited = lease.inherited_lock(account_id)
        with pytest.raises(ValueError, match="credential_lock_invalid"):
            lease.inherited_lock(other_account_id)
        with pytest.raises(ValueError, match="credential_lock_invalid"):
            inherited.descriptor_identity(other_account_id)

    with pytest.raises(ValueError, match="credential_lock_invalid"):
        inherited.descriptor_identity(account_id)


def test_child_holds_lock_after_parent_death(tmp_path: Path) -> None:
    account_id = OpaqueIdV1("account-parent-death")
    lock = tmp_path / credential_lock_name(account_id.value)
    script = """
import os, subprocess, sys
from pathlib import Path
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
root = Path(sys.argv[1])
root.chmod(0o700)
db_fd = os.open(root / 'agentmonitor.db', os.O_CREAT | os.O_EXCL, 0o600)
os.close(db_fd)
account = OpaqueIdV1('account-parent-death')
reference = DatabaseRefV1(root / 'agentmonitor.db', root)
with account_credential_lock(reference, account) as lease:
    fd = lease.inherited_lock(account).descriptor_identity(account)[0]
    subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.buffer.read(1)"],
                     stdin=sys.stdin, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL,
                     pass_fds=(fd,))
    print("ready", flush=True)
    os._exit(0)
"""
    parent = subprocess.Popen(
        [sys.executable, "-c", script, str(tmp_path)],
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
