"""Copyable local setup using the selected installed service, never a dev path."""

import shlex
from pathlib import Path

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    AccountBillingConnectionsV1,
    BillingLocalSetupV1,
)

# Same installed-service discovery as the existing Ollama local-entry flow.
# Only fixed executable/service names participate in these substitutions.
_INSTALLED_ENTRY = (
    'PYTHONPATH="$(/usr/bin/systemctl --user show agentmonitor-dashboard.service '
    '-p WorkingDirectory --value)/backend/src" '
    '"$(/usr/bin/systemctl --user show agentmonitor-dashboard.service '
    r"-p ExecStart --value | /usr/bin/sed -n 's/^{ path=\([^ ]*\) ;.*/\1/p')"
    '" -B -m agentmonitor.composition.billing_credential_operator'
)


def billing_local_command(
    data_root: str, account_id: OpaqueIdV1, resource_id: OpaqueIdV1
) -> str:
    """Quote complete arguments; leading '-' IDs cannot become CLI flags."""
    if not Path(data_root).is_absolute() or any(
        ord(character) < 32 or ord(character) == 127 for character in data_root
    ):
        raise ValueError("billing_setup_data_root_invalid")
    arguments = (
        "--data-root=" + data_root,
        "--account-id=" + account_id.value,
        "--resource-id=" + resource_id.value,
    )
    return _INSTALLED_ENTRY + " " + shlex.join(arguments)


class InstalledBillingLocalSetupV1:
    """Publish a command; execution still validates the real selected service."""

    def __init__(self, data_root: Path, host_label: str) -> None:
        self._data_root = str(data_root)
        safe = "".join(c for c in host_label if c.isprintable())[:128].strip()
        self._host_label = safe or "AgentMonitor computer"

    def describe(
        self, status: AccountBillingConnectionsV1
    ) -> BillingLocalSetupV1 | None:
        if (
            status.provider_key not in {"claude", "codex"}
            or status.account_lifecycle not in {"pending", "active"}
            or len(status.connections) != 1
            or status.connections[0].lifecycle not in {"pending", "active"}
        ):
            return None
        return BillingLocalSetupV1(
            host_label=self._host_label,
            command=billing_local_command(
                self._data_root, status.account_id, status.connections[0].resource_id
            ),
        )
