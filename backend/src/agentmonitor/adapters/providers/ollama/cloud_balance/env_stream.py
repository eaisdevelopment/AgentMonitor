"""Strict Ollama compatibility wrapper for bounded managed-entry streaming."""

import re
from collections.abc import Iterable

from agentmonitor.adapters.credential_env.stream import (
    read_credential_value_stream as read_managed_stream,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)

ENV_STREAM_CHUNK_BYTES = ENV_AUTHORIZATION_POLICY_V1.stream_chunk_bytes
_NAME = re.compile(ENV_AUTHORIZATION_POLICY_V1.variable_name_pattern.encode("ascii"))


def read_credential_value_stream(
    chunks: Iterable[bytes | bytearray], name: bytes
) -> bytearray:
    """Keep the original namespace restriction and sanitized error vocabulary."""
    if type(name) is not bytes or _NAME.fullmatch(name) is None:
        raise ValueError("ollama_env_binding_invalid") from None
    try:
        return read_managed_stream(chunks, name)
    except ValueError as error:
        raise ValueError(str(error).replace("credential_env_", "ollama_env_")) from None
