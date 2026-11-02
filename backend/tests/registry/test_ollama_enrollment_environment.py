"""Only the desktop session values required by Secret Service are forwarded."""

from agentmonitor.composition.ollama_credential_enrollment import (
    secret_tool_environment,
)


def test_environment_does_not_forward_unrelated_values():
    assert secret_tool_environment(
        {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/session", "UNRELATED": "private"}
    ) == {"PATH": "/usr/bin:/bin", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/session"}
