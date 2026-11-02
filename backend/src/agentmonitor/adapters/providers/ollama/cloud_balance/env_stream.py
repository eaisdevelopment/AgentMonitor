"""Bounded pure streaming selection for one managed Ollama .env entry."""

import re
from collections.abc import Iterable

from agentmonitor.adapters.providers.ollama.cloud_balance.env_format import (
    decode_credential_value,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)

ENV_STREAM_CHUNK_BYTES = ENV_AUTHORIZATION_POLICY_V1.stream_chunk_bytes
_NAME = re.compile(ENV_AUTHORIZATION_POLICY_V1.variable_name_pattern.encode("ascii"))
_EXPORT = b"export "
_WHITESPACE = b" \t\r"


def read_credential_value_stream(
    chunks: Iterable[bytes | bytearray], name: bytes
) -> bytearray:
    """Select one exact line while retaining no unrelated line values."""
    if type(name) is not bytes or _NAME.fullmatch(name) is None:
        raise ValueError("ollama_env_binding_invalid") from None

    encoded = bytearray()
    selected: bytearray | None = None
    state = "leading"
    canonical = True
    export_index = 0
    name_index = 0
    target_count = 0
    total = 0
    line_started = False

    def finish_line() -> None:
        nonlocal canonical, encoded, export_index, line_started, name_index
        nonlocal selected, state
        if state in {"after_name", "trailing"}:
            raise ValueError("ollama_env_entry_invalid") from None
        if state == "target":
            if encoded.endswith(b"\r"):
                del encoded[-1:]
            if len(encoded) > ENV_AUTHORIZATION_POLICY_V1.maximum_encoded_bytes:
                raise ValueError("ollama_env_value_invalid") from None
            selected = encoded
            encoded = bytearray()
        state = "leading"
        canonical = True
        export_index = 0
        name_index = 0
        line_started = False

    try:
        for chunk in chunks:
            if (
                type(chunk) not in {bytes, bytearray}
                or len(chunk) > ENV_STREAM_CHUNK_BYTES
            ):
                raise ValueError("ollama_env_stream_invalid") from None
            total += len(chunk)
            if total > ENV_AUTHORIZATION_POLICY_V1.maximum_file_bytes:
                raise ValueError("ollama_env_stream_invalid") from None
            for value in chunk:
                if value == 0x0A:
                    finish_line()
                    continue
                line_started = True
                if state == "skip":
                    continue
                if state == "target":
                    if (
                        len(encoded)
                        >= ENV_AUTHORIZATION_POLICY_V1.maximum_encoded_bytes + 1
                    ):
                        raise ValueError("ollama_env_value_invalid") from None
                    encoded.append(value)
                    continue
                if state in {"leading", "post_export"}:
                    if value in _WHITESPACE:
                        canonical = False
                        continue
                    if state == "leading" and value == 0x23:
                        state = "skip"
                        continue
                    if value == name[0]:
                        name_index = 1
                        state = "after_name" if len(name) == 1 else "name"
                        continue
                    if state == "leading" and value == _EXPORT[0]:
                        canonical = False
                        export_index = 1
                        state = "export"
                        continue
                    state = "skip"
                    continue
                if state == "export":
                    if value != _EXPORT[export_index]:
                        state = "skip"
                        continue
                    export_index += 1
                    if export_index == len(_EXPORT):
                        state = "post_export"
                    continue
                if state == "name":
                    if value != name[name_index]:
                        state = "skip"
                        continue
                    name_index += 1
                    if name_index == len(name):
                        state = "after_name"
                    continue
                if state == "after_name":
                    if value == 0x3D:
                        if not canonical:
                            raise ValueError("ollama_env_entry_invalid") from None
                        target_count += 1
                        if target_count > 1:
                            raise ValueError("ollama_env_entry_ambiguous") from None
                        state = "target"
                    elif value in _WHITESPACE:
                        canonical = False
                        state = "trailing"
                    else:
                        state = "skip"
                    continue
                if state == "trailing":
                    if value == 0x3D:
                        raise ValueError("ollama_env_entry_invalid") from None
                    if value not in _WHITESPACE:
                        state = "skip"
        if line_started:
            finish_line()
        if target_count == 0 or selected is None:
            raise ValueError("ollama_env_entry_missing") from None
        return decode_credential_value(bytes(selected))
    finally:
        encoded[:] = b"\0" * len(encoded)
        if selected is not None:
            selected[:] = b"\0" * len(selected)
