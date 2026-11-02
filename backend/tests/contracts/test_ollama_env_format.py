"""Pure format policy; no real credential or filesystem access."""

import pytest

from agentmonitor.adapters.providers.ollama.cloud_balance.env_format import (
    credential_variable_name,
    decode_credential_value,
    edit_credential_entry,
    encode_credential_value,
)


def test_binding_name_and_codec_are_closed() -> None:
    name = credential_variable_name("amcb_" + "a" * 32)
    assert name == b"OLLAMA_API_KEY_AMCB_" + b"A" * 32
    token = bytearray(b"ordinary-test-input")
    assert decode_credential_value(encode_credential_value(token)) == token
    with pytest.raises(ValueError):
        credential_variable_name("wrong")
    with pytest.raises(ValueError):
        decode_credential_value(b"!!")


def test_edit_preserves_unrelated_lines_and_rejects_ambiguous_target() -> None:
    name = credential_variable_name("amcb_" + "a" * 32)
    before = b"OTHER=value\n# comment\n"
    added = edit_credential_entry(before, name, b"YWJj")
    assert added == before + name + b"=YWJj\n"
    assert edit_credential_entry(added, name, None) == before
    with pytest.raises(ValueError):
        edit_credential_entry(added + name + b"=YWJj\n", name, None)
