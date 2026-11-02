"""Private Secret Service lookup that can only fill one bearer-token sink."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_command import (
    build_lookup_command,
    secret_tool_environment,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CloudBalanceAuthorizationSinkV1,
    CloudBalanceAuthorizationUnavailable,
)

_SECRET_TOOL = Path("/usr/bin/secret-tool")
_MAX_BEARER_BYTES = 4096
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


class SecretToolAuthorizationV1:
    """Resolve one exact binding inside the isolated network worker only."""

    __slots__ = ("_binding_id",)

    def __init__(self, binding_id: str) -> None:
        # The pure builder owns the closed generated-binding grammar.
        build_lookup_command(binding_id)
        self._binding_id = binding_id

    def apply_authorization_v1(self, sink: CloudBalanceAuthorizationSinkV1) -> None:
        """Consume bounded lookup stdout without returning or logging key bytes."""
        if not _safe_secret_tool():
            raise CloudBalanceAuthorizationUnavailable("ollama_cloud_store_unavailable")
        process: subprocess.Popen[bytes] | None = None
        output = bytearray(_MAX_LOOKUP_OUTPUT_BYTES)
        token: bytearray | None = None
        try:
            process = subprocess.Popen(
                build_lookup_command(self._binding_id),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=secret_tool_environment(os.environ),
                close_fds=True,
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
