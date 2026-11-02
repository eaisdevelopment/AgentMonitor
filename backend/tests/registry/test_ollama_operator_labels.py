"""Owner-facing text does not emit terminal control sequences."""

from agentmonitor.composition.ollama_credential_operator import safe_label


def test_account_label_removes_terminal_controls() -> None:
    assert safe_label("SDK\x1b[31m") == "SDK?[31m"
    assert safe_label("") == "Unnamed"
