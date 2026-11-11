"""Pure constructed byte-policy inputs only: no file, credentials or provider I/O."""

from typing import cast

import pytest
from agentmonitor.adapters.credential_env.format import (
    CredentialProviderKey,
    credential_variable_name,
    decode_credential_value,
    edit_credential_entry,
    encode_credential_value,
    parse_managed_entry_name,
    read_credential_value,
)
from agentmonitor.adapters.providers.ollama.cloud_balance import env_format as ollama
from agentmonitor.composition.ollama_env_store import (
    validate_ollama_env_import_variable,
)


@pytest.mark.parametrize("provider", ["ANTHROPIC", "OPENAI", "OLLAMA"])
def test_all_managed_names_are_reserved_from_literal_import(provider: str) -> None:
    """M7-ENV-001: never import another managed entry as a literal key."""
    name = "AGENTMONITOR_" + provider + "_API_KEY_AMCB_" + "A" * 32
    with pytest.raises(ValueError, match="ollama_env_import_name_invalid"):
        validate_ollama_env_import_variable(name)


@pytest.mark.parametrize(
    ("provider", "prefix"),
    [
        ("claude", b"AGENTMONITOR_ANTHROPIC_API_KEY_AMCB_"),
        ("codex", b"AGENTMONITOR_OPENAI_API_KEY_AMCB_"),
        ("ollama", b"AGENTMONITOR_OLLAMA_API_KEY_AMCB_"),
    ],
)
def test_provider_namespace_roundtrip_and_exact_entry_edit(
    provider: CredentialProviderKey, prefix: bytes
) -> None:
    """M7-ENV-003: namespaces are exact and unrelated bytes survive edits."""
    binding = "amcb_" + "a" * 32
    name = credential_variable_name(binding, provider_key=provider)
    assert name == prefix + b"A" * 32
    assert parse_managed_entry_name(name) == (provider, binding)
    before = b"# Pure constructed inputs\r\nOTHER=literal\r\n"
    encoded = encode_credential_value(bytearray(b"pure-format-input"))
    added = edit_credential_entry(before, name, encoded)
    assert added == before + name + b"=" + encoded + b"\n"
    assert read_credential_value(added, name) == bytearray(b"pure-format-input")
    assert edit_credential_entry(added, name, None) == before
    with pytest.raises(ValueError, match="credential_env_entry_ambiguous"):
        edit_credential_entry(added + name + b"=" + encoded + b"\n", name, None)
    with pytest.raises(ValueError, match="credential_env_entry_invalid"):
        edit_credential_entry(b"export " + name + b"=" + encoded, name, None)


def test_editing_one_namespace_preserves_other_managed_entries() -> None:
    """M7-ENV-004: replacement/removal is scoped to one exact managed name."""
    names = tuple(
        credential_variable_name("amcb_" + "b" * 32, provider_key=provider)
        for provider in ("claude", "codex", "ollama")
    )
    lines = tuple(name + b"=YWJj\n" for name in names)
    content = b"".join(lines)
    assert edit_credential_entry(content, names[1], None) == lines[0] + lines[2]
    assert edit_credential_entry(content, names[1], b"ZGVm") == (
        lines[0] + lines[2] + names[1] + b"=ZGVm\n"
    )


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_ollama_compatibility_rejects_other_names(
    provider: CredentialProviderKey,
) -> None:
    """M7-ENV-005: widening shared policy never widens the Ollama reader/writer."""
    name = credential_variable_name("amcb_" + "c" * 32, provider_key=provider)
    with pytest.raises(ValueError, match="ollama_env_binding_invalid"):
        ollama.read_credential_value(name + b"=YWJj\n", name)
    with pytest.raises(ValueError, match="ollama_env_binding_invalid"):
        ollama.edit_credential_entry(b"", name, b"YWJj")
    assert ollama.credential_variable_name("amcb_" + "c" * 32) == (
        credential_variable_name("amcb_" + "c" * 32, provider_key="ollama")
    )


@pytest.mark.parametrize("provider", ["", "anthropic", "openai", "other", True])
def test_unknown_provider_cannot_select_a_namespace(provider: object) -> None:
    with pytest.raises(ValueError, match="credential_env_provider_invalid"):
        credential_variable_name(
            "amcb_" + "a" * 32, provider_key=cast(CredentialProviderKey, provider)
        )


@pytest.mark.parametrize(
    "binding", ["", "a" * 32, "amcb_" + "A" * 32, "amcb_" + "a" * 33]
)
def test_binding_shape_remains_closed(binding: str) -> None:
    with pytest.raises(ValueError, match="credential_env_binding_invalid"):
        credential_variable_name(binding, provider_key="claude")


@pytest.mark.parametrize(
    "prefix",
    [
        b"AGENTMONITOR_ANTHROPIC_API_KEY_AMCB_",
        b"AGENTMONITOR_OPENAI_API_KEY_AMCB_",
        b"AGENTMONITOR_OLLAMA_API_KEY_AMCB_",
    ],
)
def test_cleanup_name_policy_rejects_malformed_reserved_names(prefix: bytes) -> None:
    """M7-ENV-006: orphan scan must fail closed on malformed managed entries."""
    with pytest.raises(ValueError, match="credential_env_binding_invalid"):
        parse_managed_entry_name(prefix + b"invalid")
    assert parse_managed_entry_name(b"UNRELATED_OWNER_VARIABLE") is None


@pytest.mark.parametrize("value", [b"", b"two words", b"line\n", b"\x00", b"x" * 4097])
def test_value_encoding_keeps_existing_bounds(value: bytes) -> None:
    with pytest.raises(ValueError, match="credential_env_value_invalid"):
        encode_credential_value(bytearray(value))


@pytest.mark.parametrize("encoded", [b"!!", b"YR==", b"YWJj\n", b"", b"YQ="])
def test_decoder_rejects_noncanonical_or_empty_values(encoded: bytes) -> None:
    with pytest.raises(ValueError, match="credential_env_value_invalid"):
        decode_credential_value(encoded)


def test_maximum_visible_ascii_encoding_matches_ollama_compatibility() -> None:
    value = bytearray(b"!" * 4096)
    encoded = encode_credential_value(value)
    assert len(encoded) == 5464
    assert decode_credential_value(encoded) == value
    assert ollama.encode_credential_value(value) == encoded
    assert ollama.decode_credential_value(encoded) == value
