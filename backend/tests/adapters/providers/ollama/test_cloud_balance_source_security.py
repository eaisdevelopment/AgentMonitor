"""Pure adversarial checks for sanitized Ollama cloud source boundaries."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CloudBalanceAuthorizationUnavailable,
    _retry_after,
    probe_cloud_balance_for_binding_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ActiveCredentialBindingRefV1,
    InheritedAccountCredentialLockV1,
)


def test_authorization_failure_code_is_runtime_closed() -> None:
    with pytest.raises(
        ValueError,
        match="^ollama_cloud_authorization_failure_code_invalid$",
    ) as captured:
        CloudBalanceAuthorizationUnavailable("provider-secret-marker")  # type: ignore[arg-type]

    assert captured.value.__cause__ is None
    assert "provider-secret-marker" not in repr(captured.value)


def test_valid_long_retry_after_is_not_discarded_or_truncated() -> None:
    seconds = 365 * 24 * 60 * 60 + 1

    assert _retry_after({"retry-after": (str(seconds),)}) == seconds
    assert _retry_after({"retry-after": (str(2**63 - 1),)}) == 2**63 - 1


def test_unrepresentable_retry_after_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="^ollama_cloud_retry_after_unrepresentable$",
    ):
        _retry_after({"retry-after": (str(2**63),)})


def test_malformed_retry_after_remains_fallback_eligible() -> None:
    assert _retry_after({}) is None
    assert _retry_after({"retry-after": ("not-seconds",)}) is None


def test_tls_context_ignores_environment_keylog_request(tmp_path: Path) -> None:
    backend = Path(__file__).resolve().parents[4]
    keylog = tmp_path / "must-not-exist.log"
    script = """
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    _secure_tls_context,
)
context = _secure_tls_context()
raise SystemExit(0 if context.keylog_filename is None else 7)
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend.parent,
        env={
            "PYTHONPATH": str(backend / "src"),
            "SSLKEYLOGFILE": str(keylog),
        },
        check=False,
        capture_output=True,
        timeout=5,
    )

    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr == b""
    assert not keylog.exists()


def test_raw_descriptor_cannot_be_used_as_a_credential_lock() -> None:
    result = probe_cloud_balance_for_binding_v1(
        binding=ActiveCredentialBindingRefV1(
            OpaqueIdV1("account-lock-policy"),
            OpaqueIdV1("amcb_" + "a" * 32),
            1,
        ),
        credential_lock=7,  # type: ignore[arg-type]
        deadline_monotonic=0.0,
    )

    assert result.state == "internal_adapter_error"
    assert result.reason_code == "ollama_cloud_credential_lock_invalid"
    assert result.dispatch_certainty == "not_started"
    assert result.http_status is None
    assert result.balance is None


def test_inherited_lock_rejects_an_arbitrary_locked_file(tmp_path: Path) -> None:
    import fcntl
    import os

    from agentmonitor.adapters.providers.ollama.cloud_balance.credential_lock import (
        validated_credential_lock_descriptor,
    )

    tmp_path.chmod(0o700)
    descriptor = os.open(
        tmp_path / "arbitrary-file", os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600
    )
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_metadata = os.fstat(descriptor)
        root_metadata = os.fstat(directory)
        account_id = OpaqueIdV1("account-arbitrary-file")
        credential_lock = InheritedAccountCredentialLockV1.from_inherited_identity(
            account_id=account_id,
            descriptor=descriptor,
            device=lock_metadata.st_dev,
            inode=lock_metadata.st_ino,
            directory_descriptor=directory,
            root_device=root_metadata.st_dev,
            root_inode=root_metadata.st_ino,
        )

        with pytest.raises(ValueError, match="credential_lock_invalid"):
            validated_credential_lock_descriptor(credential_lock, account_id)
    finally:
        os.close(descriptor)
        os.close(directory)


def test_nested_lookup_child_dies_with_its_isolated_helper() -> None:
    backend = Path(__file__).resolve().parents[4]
    script = """
import os, subprocess, sys
from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_authorization import (
    _parent_death_signal_v1,
)
parent = os.getpid()
child = subprocess.Popen(
    [sys.executable, '-c', 'import time; time.sleep(30)'],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    preexec_fn=_parent_death_signal_v1(parent),
)
print(child.pid, flush=True)
os._exit(0)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=backend.parent,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(backend / "src")},
    )
    child_pid = 0
    try:
        assert process.stdout is not None
        child_pid = int(process.stdout.readline())
        assert process.wait(timeout=5) == 0
        deadline = time.monotonic() + 2
        while Path(f"/proc/{child_pid}").exists():
            assert time.monotonic() < deadline
            time.sleep(0.01)
    finally:
        if child_pid and Path(f"/proc/{child_pid}").exists():
            try:
                import signal

                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.stdout is not None:
            process.stdout.close()
