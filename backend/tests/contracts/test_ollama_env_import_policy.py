"""Pure literal .env import policy; no filesystem or credential access."""

import pytest

from agentmonitor.composition import ollama_env_store


def _read(chunks: tuple[bytes, ...], name: str) -> bytearray:
    return ollama_env_store.read_literal_env_value(b"".join(chunks), name)


def test_literal_import_retains_only_exact_target_without_shell_expansion() -> None:
    result = _read(
        (
            b"UNRELATED_ONE=ordinary\nOLLAMA_",
            b"API_KEY=$OTHER_LITERAL\nUNRELATED_TWO=discarded\n",
        ),
        "OLLAMA_API_KEY",
    )

    assert result == bytearray(b"$OTHER_LITERAL")

    quoted = _read((b"OLLAMA_API_KEY='$OTHER_LITERAL'\n",), "OLLAMA_API_KEY")
    assert quoted == bytearray(b"$OTHER_LITERAL")


def test_literal_import_rejects_duplicate_empty_and_noncanonical_target() -> None:
    with pytest.raises(ValueError, match="ollama_env_import_entry_ambiguous"):
        _read((b"OLLAMA_API_KEY=one\nOLLAMA_API_KEY=two\n",), "OLLAMA_API_KEY")
    with pytest.raises(ValueError, match="ollama_env_import_value_invalid"):
        _read((b"OLLAMA_API_KEY=\n",), "OLLAMA_API_KEY")
    with pytest.raises(ValueError, match="ollama_env_import_entry_invalid"):
        _read((b" export OLLAMA_API_KEY=value\n",), "OLLAMA_API_KEY")


@pytest.mark.parametrize(
    "name",
    (
        "",
        "9OLLAMA_API_KEY",
        "OLLAMA API KEY",
        "AGENTMONITOR_OLLAMA_API_KEY_AMCB_" + "A" * 32,
    ),
)
def test_literal_import_rejects_unsafe_or_managed_names(name: str) -> None:
    with pytest.raises(ValueError, match="ollama_env_import_name_invalid"):
        _read((b"OLLAMA_API_KEY=value\n",), name)
