"""Pure streaming parser policy; no filesystem or credential access."""

import pytest
from agentmonitor.adapters.providers.ollama.cloud_balance.env_format import (
    credential_variable_name,
    encode_credential_value,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_stream import (
    ENV_STREAM_CHUNK_BYTES,
    read_credential_value_stream,
)


def test_stream_retains_only_the_exact_target_value_across_chunks() -> None:
    name = credential_variable_name("amcb_" + "a" * 32)
    token = bytearray(b"ordinary-pure-input")
    encoded = encode_credential_value(token)
    content = (
        b"#"
        + b"comment" * 30
        + b"\nUNRELATED_ONE=alpha\n"
        + name
        + b"="
        + encoded
        + b"\nOTHER=beta\n"
    )
    chunks = tuple(content[offset : offset + 7] for offset in range(0, len(content), 7))

    assert read_credential_value_stream(chunks, name) == token


def test_stream_rejects_duplicate_or_noncanonical_target() -> None:
    name = credential_variable_name("amcb_" + "b" * 32)
    line = name + b"=YWJj\n"
    with pytest.raises(ValueError, match="ollama_env_entry_ambiguous"):
        read_credential_value_stream((line, line), name)
    with pytest.raises(ValueError, match="ollama_env_entry_invalid"):
        read_credential_value_stream((b" export " + line,), name)


def test_stream_bounds_every_transient_chunk_and_skips_unrelated_long_name() -> None:
    name = credential_variable_name("amcb_" + "c" * 32)
    with pytest.raises(ValueError, match="ollama_env_stream_invalid"):
        read_credential_value_stream((b"x" * (ENV_STREAM_CHUNK_BYTES + 1),), name)
    content = b"X" * 1024 + b"=value\n" + name + b"=YWJj\n"
    chunks = tuple(
        content[offset : offset + ENV_STREAM_CHUNK_BYTES]
        for offset in range(0, len(content), ENV_STREAM_CHUNK_BYTES)
    )
    assert read_credential_value_stream(chunks, name) == bytearray(b"abc")


def test_stream_rejects_missing_target() -> None:
    name = credential_variable_name("amcb_" + "d" * 32)
    with pytest.raises(ValueError, match="ollama_env_entry_missing"):
        read_credential_value_stream((b"OTHER=value\n",), name)
