"""Pure names for account-scoped credential synchronization."""

from agentmonitor.modules.registry.domain.credential_lock import credential_lock_name


def test_lock_name_is_stable_account_scoped_and_hides_identifier() -> None:
    one = credential_lock_name("account-one")
    assert one == credential_lock_name("account-one")
    assert one != credential_lock_name("account-two")
    assert one.startswith("credential-")
    assert "account" not in one
