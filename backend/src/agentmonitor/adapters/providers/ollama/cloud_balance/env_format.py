"""Pure formatting for owner-managed, binding-scoped Ollama .env entries."""

import base64
import binascii
import re
from typing import cast

from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)

_BINDING = re.compile(ENV_AUTHORIZATION_POLICY_V1.binding_id_pattern)
_NAME = re.compile(ENV_AUTHORIZATION_POLICY_V1.variable_name_pattern.encode("ascii"))


def credential_variable_name(binding_id: str) -> bytes:
    if not isinstance(binding_id, str) or _BINDING.fullmatch(binding_id) is None:
        raise ValueError("ollama_env_binding_invalid")
    return ENV_AUTHORIZATION_POLICY_V1.variable_prefix.encode("ascii") + binding_id[
        5:
    ].upper().encode("ascii")


def encode_credential_value(token: bytearray) -> bytes:
    if (
        not isinstance(token, bytearray)
        or not 1 <= len(token) <= ENV_AUTHORIZATION_POLICY_V1.maximum_token_bytes
    ):
        raise ValueError("ollama_env_value_invalid")
    if any(value < 0x21 or value > 0x7E for value in token):
        raise ValueError("ollama_env_value_invalid")
    return base64.b64encode(token)


def decode_credential_value(encoded: bytes) -> bytearray:
    token: bytearray | None = None
    try:
        if (
            not isinstance(encoded, bytes)
            or len(encoded) > ENV_AUTHORIZATION_POLICY_V1.maximum_encoded_bytes
        ):
            raise ValueError("ollama_env_value_invalid")
        token = bytearray(base64.b64decode(encoded, validate=True))
        if encode_credential_value(token) != encoded:
            raise ValueError("ollama_env_value_invalid")
        return token
    except (ValueError, TypeError, binascii.Error):
        if token is not None:
            token[:] = b"\0" * len(token)
        raise ValueError("ollama_env_value_invalid") from None


def _lines(content: bytes | bytearray) -> list[bytes | bytearray]:
    return cast(list[bytes | bytearray], content.splitlines(keepends=True))


def _target_lines(content: bytes | bytearray, name: bytes) -> list[int]:
    if _NAME.fullmatch(name) is None:
        raise ValueError("ollama_env_binding_invalid")
    matches = []
    for index, line in enumerate(_lines(content)):
        stripped = line.lstrip()
        if stripped.startswith(b"export "):
            stripped = stripped[7:].lstrip()
        if stripped.split(b"=", 1)[0].strip() == name:
            matches.append(index)
    if len(matches) > 1:
        raise ValueError("ollama_env_entry_ambiguous")
    return matches


def read_credential_value(content: bytes | bytearray, name: bytes) -> bytearray:
    matches = _target_lines(content, name)
    if not matches:
        raise ValueError("ollama_env_entry_missing")
    line = _lines(content)[matches[0]]
    if not line.startswith(name + b"="):
        raise ValueError("ollama_env_entry_invalid")
    return decode_credential_value(bytes(line[len(name) + 1 :].rstrip(b"\r\n")))


def edit_credential_entry(content: bytes, name: bytes, encoded: bytes | None) -> bytes:
    matches = _target_lines(content, name)
    if encoded is not None:
        token = decode_credential_value(encoded)
        token[:] = b"\0" * len(token)
    lines = content.splitlines(keepends=True)
    if matches:
        line = lines[matches[0]]
        if not line.startswith(name + b"="):
            raise ValueError("ollama_env_entry_invalid")
        lines.pop(matches[0])
    if encoded is not None:
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            lines.append(b"\n")
        lines.append(name + b"=" + encoded + b"\n")
    return b"".join(lines)
