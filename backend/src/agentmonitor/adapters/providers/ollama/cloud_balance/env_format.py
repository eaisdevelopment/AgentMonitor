"""Pure formatting for owner-managed, binding-scoped Ollama .env entries."""

import base64
import binascii
import re
from typing import cast

_BINDING = re.compile(r"amcb_[0-9a-f]{32}\Z")
_NAME = re.compile(rb"OLLAMA_API_KEY_AMCB_[0-9A-F]{32}\Z")
_MAX_TOKEN_BYTES = 4096


def credential_variable_name(binding_id: str) -> bytes:
    if not isinstance(binding_id, str) or _BINDING.fullmatch(binding_id) is None:
        raise ValueError("ollama_env_binding_invalid")
    return b"OLLAMA_API_KEY_AMCB_" + binding_id[5:].upper().encode("ascii")


def encode_credential_value(token: bytearray) -> bytes:
    if not isinstance(token, bytearray) or not 1 <= len(token) <= _MAX_TOKEN_BYTES:
        raise ValueError("ollama_env_value_invalid")
    if any(value < 0x21 or value > 0x7E for value in token):
        raise ValueError("ollama_env_value_invalid")
    return base64.b64encode(token)


def decode_credential_value(encoded: bytes) -> bytearray:
    token: bytearray | None = None
    try:
        if not isinstance(encoded, bytes) or len(encoded) > 5464:
            raise ValueError("ollama_env_value_invalid")
        token = bytearray(base64.b64decode(encoded, validate=True))
        if encode_credential_value(token) != encoded:
            raise ValueError("ollama_env_value_invalid")
        return token
    except (ValueError, TypeError, binascii.Error):
        if token is not None:
            token[:] = b"\0" * len(token)
        raise ValueError("ollama_env_value_invalid") from None


def _target_lines(content: bytes | bytearray, name: bytes) -> list[int]:
    if _NAME.fullmatch(name) is None:
        raise ValueError("ollama_env_binding_invalid")
    matches = []
    lines = cast(list[bytes | bytearray], content.splitlines(keepends=True))
    for index, line in enumerate(lines):
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
    line = content.splitlines(keepends=True)[matches[0]]
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
