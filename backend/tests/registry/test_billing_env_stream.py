"""Pure managed-entry stream policy; no credential files or provider I/O."""

from collections.abc import Iterable, Iterator
from typing import cast

import pytest

from agentmonitor.adapters.credential_env.format import (
    CredentialProviderKey,
    credential_variable_name,
    encode_credential_value,
)
from agentmonitor.adapters.credential_env.stream import (
    ENV_STREAM_CHUNK_BYTES,
    read_credential_value_stream,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_stream import (
    read_credential_value_stream as read_ollama_stream,
)


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_ollama_stream_keeps_rejecting_other_managed_names(
    provider: CredentialProviderKey,
) -> None:
    name = credential_variable_name("amcb_" + "a" * 32, provider_key=provider)
    with pytest.raises(ValueError, match="ollama_env_binding_invalid"):
        read_ollama_stream((name + b"=YWJj\n",), name)


def _chunks(content: bytes, width: int = 256) -> tuple[bytes, ...]:
    return tuple(
        content[index : index + width] for index in range(0, len(content), width)
    )


@pytest.mark.parametrize("provider", ["claude", "codex", "ollama"])
@pytest.mark.parametrize("width", [1, 7, 256])
@pytest.mark.parametrize("ending", [b"\n", b"\r\n", b""])
def test_exact_managed_namespace_across_chunk_and_line_boundaries(
    provider: CredentialProviderKey, width: int, ending: bytes
) -> None:
    """M7-STREAM-002: only the selected canonical entry is decoded."""
    name = credential_variable_name("amcb_" + "b" * 32, provider_key=provider)
    line = (
        name + b"=" + encode_credential_value(bytearray(b"pure-stream-input")) + ending
    )
    content = b"UNRELATED=not-base64!\n# comment\n" + line
    assert read_credential_value_stream(_chunks(content, width), name) == bytearray(
        b"pure-stream-input"
    )


def test_other_provider_values_and_long_unrelated_names_are_skipped() -> None:
    """M7-STREAM-003: foreign namespace values are neither decoded nor returned."""
    target = credential_variable_name("amcb_" + "c" * 32, provider_key="claude")
    other = credential_variable_name("amcb_" + "c" * 32, provider_key="codex")
    content = (
        other
        + b"=invalid-base64!\n"
        + target
        + b"X=also-invalid!\n"
        + b"UNRELATED_"
        + b"x" * 2000
        + b"=discarded\n"
        + target
        + b"=YWJj\nOTHER=\x00invalid\n"
    )
    assert read_credential_value_stream(_chunks(content), target) == bytearray(b"abc")


@pytest.mark.parametrize("prefix", [b" ", b"\t", b"export ", b" export "])
def test_noncanonical_target_is_rejected(prefix: bytes) -> None:
    name = credential_variable_name("amcb_" + "d" * 32, provider_key="codex")
    with pytest.raises(ValueError, match="credential_env_entry_invalid"):
        read_credential_value_stream(_chunks(prefix + name + b"=YWJj\n", 7), name)


@pytest.mark.parametrize("suffix", [b"", b" ", b" =YWJj", b"\t=YWJj"])
def test_incomplete_or_spaced_target_is_rejected(suffix: bytes) -> None:
    name = credential_variable_name("amcb_" + "d" * 32, provider_key="claude")
    with pytest.raises(ValueError, match="credential_env_entry_invalid"):
        read_credential_value_stream(_chunks(name + suffix), name)


@pytest.mark.parametrize("encoded", [b"", b"YR==", b"!!", b"YWJj ", b"YQ="])
def test_decode_requires_canonical_nonempty_value(encoded: bytes) -> None:
    name = credential_variable_name("amcb_" + "e" * 32, provider_key="claude")
    with pytest.raises(ValueError, match="credential_env_value_invalid"):
        read_credential_value_stream(_chunks(name + b"=" + encoded), name)


def test_duplicate_after_selected_entry_is_not_ignored() -> None:
    name = credential_variable_name("amcb_" + "f" * 32, provider_key="codex")
    line = name + b"=YWJj\n"
    with pytest.raises(ValueError, match="credential_env_entry_ambiguous"):
        read_credential_value_stream(_chunks(line + b"OTHER=ignored\n" + line, 7), name)


def test_exact_file_limit_and_oversize_file_are_distinct() -> None:
    """M7-STREAM-004: every byte counts even after a selected value was found."""
    name = credential_variable_name("amcb_" + "1" * 32, provider_key="claude")
    line = name + b"=YWJj\n"
    content = line + b"#" + b"x" * (65536 - len(line) - 1)
    assert read_credential_value_stream(_chunks(content), name) == bytearray(b"abc")
    with pytest.raises(ValueError, match="credential_env_stream_invalid"):
        read_credential_value_stream(_chunks(content + b"x"), name)


@pytest.mark.parametrize("bad_chunk", [b"x" * 257, "text", memoryview(b"bytes")])
def test_chunks_are_bounded_and_closed(bad_chunk: object) -> None:
    name = credential_variable_name("amcb_" + "2" * 32, provider_key="codex")
    with pytest.raises(ValueError, match="credential_env_stream_invalid"):
        read_credential_value_stream(
            cast(Iterable[bytes | bytearray], (bad_chunk,)), name
        )
    assert ENV_STREAM_CHUNK_BYTES == 256


def test_maximum_value_passes_and_oversize_encoded_value_is_rejected() -> None:
    name = credential_variable_name("amcb_" + "3" * 32, provider_key="claude")
    value = bytearray(b"!" * 4096)
    encoded = encode_credential_value(value)
    assert (
        read_credential_value_stream(_chunks(name + b"=" + encoded + b"\r\n"), name)
        == value
    )
    with pytest.raises(ValueError, match="credential_env_value_invalid"):
        read_credential_value_stream(_chunks(name + b"=" + b"A" * 5466), name)


@pytest.mark.parametrize(
    "name", [b"OTHER", b"AGENTMONITOR_OPENAI_API_KEY_AMCB_invalid", b""]
)
def test_arbitrary_or_malformed_requested_name_is_rejected(name: bytes) -> None:
    with pytest.raises(ValueError, match="credential_env_binding_invalid"):
        read_credential_value_stream((b"OTHER=YWJj\n",), name)


def test_missing_target_does_not_return_unrelated_value() -> None:
    name = credential_variable_name("amcb_" + "4" * 32, provider_key="codex")
    with pytest.raises(ValueError, match="credential_env_entry_missing"):
        read_credential_value_stream((b"OTHER=YWJj\n",), name)


def test_mutable_chunks_are_consumed_without_modifying_caller_buffers() -> None:
    name = credential_variable_name("amcb_" + "5" * 32, provider_key="claude")
    chunks = [bytearray(part) for part in _chunks(name + b"=YWJj\n", 7)]
    original = [bytes(chunk) for chunk in chunks]
    result = read_credential_value_stream(chunks, name)
    assert result == bytearray(b"abc")
    assert [bytes(chunk) for chunk in chunks] == original
    result[:] = b"\0" * len(result)
    assert result == bytearray(b"\0\0\0")


def test_iterator_failure_after_target_does_not_return_partial_success() -> None:
    name = credential_variable_name("amcb_" + "6" * 32, provider_key="claude")

    def interrupted() -> Iterator[bytes]:
        yield name + b"=YWJj\n"
        raise RuntimeError("pure_iteration_interrupted")

    with pytest.raises(RuntimeError, match="pure_iteration_interrupted"):
        read_credential_value_stream(interrupted(), name)
