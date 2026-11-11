"""Pure bounded formatting for three binding-scoped managed credential namespaces."""

import base64
import binascii
import re
from typing import Literal, cast

CredentialProviderKey = Literal["claude", "codex", "ollama"]
_PREFIXES: tuple[tuple[CredentialProviderKey, bytes], ...] = (
    ("claude", b"AGENTMONITOR_ANTHROPIC_API_KEY_AMCB_"),
    ("codex", b"AGENTMONITOR_OPENAI_API_KEY_AMCB_"),
    ("ollama", b"AGENTMONITOR_OLLAMA_API_KEY_AMCB_"),
)
MANAGED_VARIABLE_PREFIXES = tuple(prefix for _, prefix in _PREFIXES)
_BINDING = re.compile(r"amcb_[0-9a-f]{32}\Z")
_SUFFIX = re.compile(rb"[0-9A-F]{32}\Z")
_MAXIMUM_TOKEN_BYTES = 4096
_MAXIMUM_ENCODED_BYTES = 5464


def credential_variable_name(
    binding_id: str, *, provider_key: CredentialProviderKey
) -> bytes:
    if type(provider_key) is not str or provider_key not in dict(_PREFIXES):
        raise ValueError("credential_env_provider_invalid")
    if type(binding_id) is not str or _BINDING.fullmatch(binding_id) is None:
        raise ValueError("credential_env_binding_invalid")
    return dict(_PREFIXES)[provider_key] + binding_id[5:].upper().encode("ascii")


def parse_managed_entry_name(name: bytes) -> tuple[CredentialProviderKey, str] | None:
    """Classify a canonical name only; malformed reserved names fail closed."""
    if type(name) is not bytes:
        raise ValueError("credential_env_binding_invalid")
    for provider, prefix in _PREFIXES:
        if name.startswith(prefix):
            suffix = name[len(prefix) :]
            if _SUFFIX.fullmatch(suffix) is None:
                raise ValueError("credential_env_binding_invalid")
            return provider, "amcb_" + suffix.decode("ascii").lower()
    return None


def encode_credential_value(token: bytearray) -> bytes:
    if not isinstance(token, bytearray) or not 1 <= len(token) <= _MAXIMUM_TOKEN_BYTES:
        raise ValueError("credential_env_value_invalid")
    if any(value < 0x21 or value > 0x7E for value in token):
        raise ValueError("credential_env_value_invalid")
    return base64.b64encode(token)


def decode_credential_value(encoded: bytes) -> bytearray:
    token: bytearray | None = None
    try:
        if not isinstance(encoded, bytes) or len(encoded) > _MAXIMUM_ENCODED_BYTES:
            raise ValueError("credential_env_value_invalid")
        token = bytearray(base64.b64decode(encoded, validate=True))
        if encode_credential_value(token) != encoded:
            raise ValueError("credential_env_value_invalid")
        return token
    except (ValueError, TypeError, binascii.Error):
        if token is not None:
            token[:] = b"\0" * len(token)
        raise ValueError("credential_env_value_invalid") from None


def _lines(content: bytes | bytearray) -> list[bytes | bytearray]:
    return cast(list[bytes | bytearray], content.splitlines(keepends=True))


def _target_lines(content: bytes | bytearray, name: bytes) -> list[int]:
    if parse_managed_entry_name(name) is None:
        raise ValueError("credential_env_binding_invalid")
    matches = []
    for index, line in enumerate(_lines(content)):
        stripped = line.lstrip()
        if stripped.startswith(b"export "):
            stripped = stripped[7:].lstrip()
        if stripped.split(b"=", 1)[0].strip() == name:
            matches.append(index)
    if len(matches) > 1:
        raise ValueError("credential_env_entry_ambiguous")
    return matches


def read_credential_value(content: bytes | bytearray, name: bytes) -> bytearray:
    matches = _target_lines(content, name)
    if not matches:
        raise ValueError("credential_env_entry_missing")
    line = _lines(content)[matches[0]]
    if not line.startswith(name + b"="):
        raise ValueError("credential_env_entry_invalid")
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
            raise ValueError("credential_env_entry_invalid")
        lines.pop(matches[0])
    if encoded is not None:
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            lines.append(b"\n")
        lines.append(name + b"=" + encoded + b"\n")
    return b"".join(lines)
