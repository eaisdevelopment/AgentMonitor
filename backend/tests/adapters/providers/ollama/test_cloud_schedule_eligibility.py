"""Pure enrollment checks for real cloud schedule candidates."""

from agentmonitor.adapters.providers.ollama.cloud_balance.collection import (
    eligible_cloud_account,
)


def test_only_active_monitored_owner_associated_accounts_are_eligible() -> None:
    assert eligible_cloud_account("ollama", "active", True, "owner_confirmed")
    assert not eligible_cloud_account("claude", "active", True, "owner_confirmed")
    assert not eligible_cloud_account("ollama", "archived", True, "owner_confirmed")
    assert not eligible_cloud_account("ollama", "active", False, "owner_confirmed")
    assert not eligible_cloud_account("ollama", "active", True, "unknown")
