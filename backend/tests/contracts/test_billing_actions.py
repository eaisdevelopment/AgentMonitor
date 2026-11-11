"""Pure billing action intent validation, no credentials or provider fixtures."""

from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_check_connection_requires_current_owner_versions() -> None:
    from agentmonitor.contracts.billing_actions_v1 import BillingCheckCommandV1

    for version in (0, -1, True):
        with pytest.raises(ValueError, match="billing_check_command_invalid"):
            BillingCheckCommandV1(
                OpaqueIdV1("account"),
                OpaqueIdV1("resource"),
                version,
                1,
                OpaqueIdV1("principal"),
                OpaqueIdV1("request"),
                datetime(2026, 11, 11, tzinfo=UTC),
            )
