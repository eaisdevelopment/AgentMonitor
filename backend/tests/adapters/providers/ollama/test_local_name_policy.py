"""Pure safe-name policy for Ollama's model identifiers."""

import pytest
from agentmonitor.adapters.providers.ollama.local_catalog.source import safe_model_name


@pytest.mark.parametrize("name", ["qwen3.5:4b", "team/model:v1", "model-1.2_q4"])
def test_valid_names_are_preserved(name: str) -> None:
    assert safe_model_name(name) == name


@pytest.mark.parametrize("name", ["", "../private", "a\nInjected", "a b", "a" * 129])
def test_unsafe_names_are_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="model_name_invalid"):
        safe_model_name(name)
