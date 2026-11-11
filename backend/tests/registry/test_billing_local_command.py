"""Pure shell-argument formatting; no command, provider or filesystem is invoked."""

import shlex

import pytest
from agentmonitor.composition.billing_local_setup import billing_local_command
from agentmonitor.contracts.common_v1 import OpaqueIdV1


@pytest.mark.parametrize(
    "root",
    ["/srv/agentmonitor", "/srv/space and 'quote'", "/srv/$(never-run)`text`"],
)
def test_local_command_preserves_selected_root_and_leading_dash_ids(root: str) -> None:
    command = billing_local_command(
        root, OpaqueIdV1("-account"), OpaqueIdV1("-resource")
    )
    prefix, arguments = command.split(
        "agentmonitor.composition.billing_credential_operator ", 1
    )
    assert "agentmonitor-dashboard.service" in prefix
    assert shlex.split(arguments) == [
        "--data-root=" + root,
        "--account-id=-account",
        "--resource-id=-resource",
    ]


@pytest.mark.parametrize("root", ["relative", "/srv/line\nbreak", "/srv/\x00"])
def test_local_command_rejects_unusable_directory_text(root: str) -> None:
    with pytest.raises(ValueError, match="billing_setup_data_root_invalid"):
        billing_local_command(root, OpaqueIdV1("account"), OpaqueIdV1("resource"))
