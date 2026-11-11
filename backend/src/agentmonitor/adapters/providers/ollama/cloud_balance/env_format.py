"""Strict Ollama compatibility surface over shared managed entry formatting."""

import re
from collections.abc import Iterator
from contextlib import contextmanager

from agentmonitor.adapters.credential_env import format as managed
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)

_NAME = re.compile(ENV_AUTHORIZATION_POLICY_V1.variable_name_pattern.encode("ascii"))


@contextmanager
def _legacy_errors() -> Iterator[None]:
    try:
        yield
    except ValueError as error:
        raise ValueError(str(error).replace("credential_env_", "ollama_env_")) from None


def _require_ollama_name(name: bytes) -> None:
    if type(name) is not bytes or _NAME.fullmatch(name) is None:
        raise ValueError("ollama_env_binding_invalid")


def credential_variable_name(binding_id: str) -> bytes:
    with _legacy_errors():
        return managed.credential_variable_name(binding_id, provider_key="ollama")


def encode_credential_value(token: bytearray) -> bytes:
    with _legacy_errors():
        return managed.encode_credential_value(token)


def decode_credential_value(encoded: bytes) -> bytearray:
    with _legacy_errors():
        return managed.decode_credential_value(encoded)


def read_credential_value(content: bytes | bytearray, name: bytes) -> bytearray:
    _require_ollama_name(name)
    with _legacy_errors():
        return managed.read_credential_value(content, name)


def edit_credential_entry(content: bytes, name: bytes, encoded: bytes | None) -> bytes:
    _require_ollama_name(name)
    with _legacy_errors():
        return managed.edit_credential_entry(content, name, encoded)
