"""Pure fixed Secret Service commands and their bounded process environment."""

import re
from collections.abc import Mapping

_BINDING = re.compile(r"amcb_[0-9a-f]{32}\Z")


def _binding(binding_id: str) -> str:
    if type(binding_id) is not str or _BINDING.fullmatch(binding_id) is None:
        raise ValueError("ollama_binding_invalid")
    return binding_id


def secret_tool_environment(source: Mapping[str, str]) -> dict[str, str]:
    """Forward only settings needed to reach the owner's Secret Service."""
    allowed = (
        "DBUS_SESSION_BUS_ADDRESS",
        "XDG_RUNTIME_DIR",
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "LANG",
        "LC_CTYPE",
    )
    return {
        "PATH": "/usr/bin:/bin",
        **{key: source[key] for key in allowed if key in source},
    }


def build_store_command(binding_id: str) -> tuple[str, ...]:
    """Build a fixed command; the credential is entered directly in its TTY."""
    binding_id = _binding(binding_id)
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


def build_lookup_command(binding_id: str) -> tuple[str, ...]:
    """Build the exact noninteractive lookup for one registry-owned binding."""
    binding_id = _binding(binding_id)
    return (
        "/usr/bin/secret-tool",
        "lookup",
        "application",
        "agentmonitor",
        "provider",
        "ollama",
        "purpose",
        "balance",
        "binding",
        binding_id,
    )
