"""Private Secret Service lookup that can only fill one bearer-token sink."""

from __future__ import annotations

import ctypes
import os
import signal
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

from agentmonitor.adapters.providers.ollama.cloud_balance.credential_lock import (
    validated_credential_lock_descriptor,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_command import (
    build_lookup_command,
    secret_tool_environment,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CloudBalanceAuthorizationSinkV1,
    CloudBalanceAuthorizationUnavailable,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import InheritedAccountCredentialLockV1

_SECRET_TOOL = Path("/usr/bin/secret-tool")
_MAX_BEARER_BYTES = 4096
_PR_SET_PDEATHSIG = 1
_LIBC = ctypes.CDLL(None, use_errno=True)
# One accepted trailing LF plus one extra byte that proves oversize output.
_MAX_LOOKUP_OUTPUT_BYTES = _MAX_BEARER_BYTES + 2


def _safe_secret_tool() -> bool:
    try:
        metadata = _SECRET_TOOL.stat(follow_symlinks=False)
    except OSError:
        return False
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == 0
        and metadata.st_gid == 0
        and stat.S_IMODE(metadata.st_mode) & 0o022 == 0
        and stat.S_IMODE(metadata.st_mode) & 0o100 != 0
    )


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait()
    except OSError:
        pass


def _parent_death_signal_v1(expected_parent: int) -> Callable[[], None]:
    """Kill the nested lookup if its isolated helper dies unexpectedly."""
    if type(expected_parent) is not int or expected_parent <= 1:
        raise ValueError("credential_worker_parent_invalid") from None

    def configure() -> None:
        if _LIBC.prctl(_PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0) != 0:
            os._exit(127)
        # Close the fork-before-prctl race without emitting diagnostics.
        if os.getppid() != expected_parent:
            os._exit(127)

    return configure


class SecretToolAuthorizationV1:
    """Resolve one exact binding inside the isolated network worker only."""

    __slots__ = ("_account_id", "_binding_id", "_credential_lock")

    def __init__(
        self,
        binding_id: str,
        account_id: OpaqueIdV1,
        credential_lock: InheritedAccountCredentialLockV1,
    ) -> None:
        # The pure builder owns the closed generated-binding grammar.
        build_lookup_command(binding_id)
        if (
            not isinstance(account_id, OpaqueIdV1)
            or type(credential_lock) is not InheritedAccountCredentialLockV1
        ):
            raise ValueError("credential_lock_invalid") from None
        validated_credential_lock_descriptor(credential_lock, account_id)
        self._binding_id = binding_id
        self._account_id = account_id
        self._credential_lock = credential_lock

    def apply_authorization_v1(self, sink: CloudBalanceAuthorizationSinkV1) -> None:
        """Consume bounded lookup stdout without returning or logging key bytes."""
        if not _safe_secret_tool():
            raise CloudBalanceAuthorizationUnavailable("ollama_cloud_store_unavailable")
        process: subprocess.Popen[bytes] | None = None
        output = bytearray(_MAX_LOOKUP_OUTPUT_BYTES)
        token: bytearray | None = None
        try:
            lock_descriptor, _ = validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            parent_pid = os.getpid()
            process = subprocess.Popen(
                build_lookup_command(self._binding_id),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=secret_tool_environment(os.environ),
                close_fds=True,
                pass_fds=(lock_descriptor,),
                preexec_fn=_parent_death_signal_v1(parent_pid),
            )
            if process.stdout is None:
                raise OSError("secret_tool_stdout_unavailable")
            used = 0
            while used < len(output):
                count = os.readv(
                    process.stdout.fileno(),
                    [memoryview(output)[used:]],
                )
                if count == 0:
                    break
                used += count
            if used == len(output):
                raise OSError("secret_tool_output_invalid")
            if process.wait() != 0:
                raise OSError("secret_tool_lookup_failed")
            if used and output[used - 1] == 0x0A:
                used -= 1
            if not 1 <= used <= _MAX_BEARER_BYTES or any(
                value < 0x21 or value > 0x7E for value in memoryview(output)[:used]
            ):
                raise OSError("secret_tool_output_invalid")
            token = bytearray(memoryview(output)[:used])
            sink.put_bearer_token_v1(token)
        except TimeoutError:
            raise
        except (OSError, subprocess.SubprocessError, ValueError):
            raise CloudBalanceAuthorizationUnavailable(
                "ollama_cloud_store_unavailable"
            ) from None
        finally:
            if token is not None:
                token[:] = b"\x00" * len(token)
            output[:] = b"\x00" * len(output)
            if process is not None:
                _stop(process)
                if process.stdout is not None:
                    process.stdout.close()
