"""Pure construction of the approved, secret-free enrollment command."""

import pytest

from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_command import (
    build_store_command,
)


def test_store_command_uses_a_scoped_binding_without_a_secret_argument():
    binding = "amcb_" + "a" * 32
    assert build_store_command(binding) == (
        "/usr/bin/secret-tool",
        "store",
        "--label=AgentMonitor Ollama balance",
        "application",
        "agentmonitor",
        "provider",
        "ollama",
        "purpose",
        "balance",
        "binding",
        binding,
    )


def test_store_command_rejects_untrusted_binding_text():
    with pytest.raises(ValueError, match="ollama_binding_invalid"):
        build_store_command("owner-supplied-key")
