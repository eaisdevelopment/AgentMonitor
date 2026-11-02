"""Pure construction of the owner-local Ollama keyring enrollment command."""

import re

_BINDING = re.compile(r"amcb_[0-9a-f]{32}\Z")


def build_store_command(binding_id: str) -> tuple[str, ...]:
    """Build a fixed command; the credential is entered directly in its TTY."""
    if type(binding_id) is not str or _BINDING.fullmatch(binding_id) is None:
        raise ValueError("ollama_binding_invalid")
    return (
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
        binding_id,
    )
