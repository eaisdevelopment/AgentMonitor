"""Real secret-tool prompt retains a lock; no key or input is provided."""

import fcntl
import os
import pty
import secrets
import subprocess
import time
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_command import (
    build_store_command,
)
from agentmonitor.composition.ollama_credential_enrollment import (
    secret_tool_environment,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.domain.credential_lock import credential_lock_name


def test_secret_tool_holds_inherited_lock_until_exit(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    database = tmp_path / "agentmonitor.db"
    database_fd = os.open(database, os.O_CREAT | os.O_EXCL, 0o600)
    os.close(database_fd)
    account_id = OpaqueIdV1("account-real-secret-tool-lock")
    path = tmp_path / credential_lock_name(account_id.value)
    reference = DatabaseRefV1(database, tmp_path)
    master, slave = pty.openpty()
    process = None
    other = None
    try:
        with account_credential_lock(reference, account_id) as lease:
            inherited = lease.inherited_lock(account_id)
            descriptor = inherited.descriptor_identity(account_id)[0]
            process = subprocess.Popen(
                build_store_command("amcb_" + secrets.token_hex(16)),
                stdin=slave,
                stdout=slave,
                stderr=slave,
                pass_fds=(descriptor,),
                env=secret_tool_environment(os.environ),
            )
            os.close(slave)
            slave = -1
            deadline = time.monotonic() + 3
            while not Path(f"/proc/{process.pid}/fd/{descriptor}").exists():
                assert process.poll() is None
                assert time.monotonic() < deadline
                time.sleep(0.02)
        # The issuing process has closed its copy. The real secret-tool child is
        # now the sole holder of the same locked open-file description.
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
        if slave >= 0:
            os.close(slave)
        os.close(master)
