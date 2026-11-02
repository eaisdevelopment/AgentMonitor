"""Private binding-scoped authorization from the protected AgentMonitor .env."""

from __future__ import annotations

import os
from collections.abc import Generator

from agentmonitor.adapters.providers.ollama.cloud_balance.credential_lock import (
    validated_credential_lock_descriptor,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    InheritedEnvCredentialFileV1,
    validated_inherited_env_file_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_format import (
    credential_variable_name,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_stream import (
    ENV_STREAM_CHUNK_BYTES,
    read_credential_value_stream,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CloudBalanceAuthorizationSinkV1,
    CloudBalanceAuthorizationUnavailable,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import InheritedAccountCredentialLockV1


def _bounded_chunks(
    descriptor: int, count: list[int]
) -> Generator[bytearray, None, None]:
    while True:
        chunk = bytearray(ENV_STREAM_CHUNK_BYTES)
        try:
            used = os.readv(descriptor, [chunk])
            if used == 0:
                return
            del chunk[used:]
            count[0] += used
            yield chunk
        finally:
            chunk[:] = b"\0" * len(chunk)


class EnvFileAuthorizationV1:
    """Stream one binding key from an inherited approved-file capability."""

    __slots__ = (
        "_account_id",
        "_credential_file",
        "_credential_lock",
        "_variable_name",
    )

    def __init__(
        self,
        binding_id: str,
        account_id: OpaqueIdV1,
        credential_lock: InheritedAccountCredentialLockV1,
        credential_file: InheritedEnvCredentialFileV1,
    ) -> None:
        variable_name = credential_variable_name(binding_id)
        if (
            not isinstance(account_id, OpaqueIdV1)
            or type(credential_lock) is not InheritedAccountCredentialLockV1
            or type(credential_file) is not InheritedEnvCredentialFileV1
        ):
            raise ValueError("credential_lock_invalid") from None
        validated_credential_lock_descriptor(credential_lock, account_id)
        validated_inherited_env_file_v1(credential_file)
        self._variable_name = variable_name
        self._account_id = account_id
        self._credential_lock = credential_lock
        self._credential_file = credential_file

    def apply_authorization_v1(self, sink: CloudBalanceAuthorizationSinkV1) -> None:
        """Apply one freshly read key without exposing it outside this process."""
        if type(sink) is not CloudBalanceAuthorizationSinkV1:
            raise ValueError("ollama_env_authorization_sink_invalid") from None
        token: bytearray | None = None
        read_count = [0]
        try:
            validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            descriptor = validated_inherited_env_file_v1(self._credential_file)
            expected_size = self._credential_file.descriptor_identity()[3]
            os.lseek(descriptor, 0, os.SEEK_SET)
            chunks = _bounded_chunks(descriptor, read_count)
            try:
                token = read_credential_value_stream(chunks, self._variable_name)
            finally:
                chunks.close()
            if read_count[0] != expected_size:
                raise ValueError("ollama_env_file_replaced")
            validated_inherited_env_file_v1(self._credential_file)
            validated_credential_lock_descriptor(
                self._credential_lock, self._account_id
            )
            sink.put_bearer_token_v1(token)
        except TimeoutError:
            raise
        except (OSError, ValueError):
            raise CloudBalanceAuthorizationUnavailable(
                "ollama_cloud_store_unavailable"
            ) from None
        finally:
            if token is not None:
                token[:] = b"\0" * len(token)
