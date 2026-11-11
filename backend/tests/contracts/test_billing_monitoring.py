"""Pure monitoring intent validation; no credential or provider I/O."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_enable_requires_current_generation_and_verified_run_intent() -> None:
    from agentmonitor.contracts.registry_billing_v1 import SetBillingMonitoringCommandV1

    disabled = SetBillingMonitoringCommandV1(
        account_id=OpaqueIdV1("account"),
        resource_id=OpaqueIdV1("resource"),
        expected_account_version=1,
        expected_connection_version=1,
        expected_scope_generation=1,
        expected_binding_generation=None,
        monitoring_preference="disabled",
        verified_run_id=None,
        principal_id=OpaqueIdV1("owner"),
        command_id=OpaqueIdV1("command"),
        requested_at=datetime(2026, 11, 11, tzinfo=UTC),
    )
    assert disabled.expected_binding_generation is None
    with pytest.raises(ValueError, match="billing_monitoring_command_invalid"):
        replace(disabled, monitoring_preference="enabled")
    enabled = replace(
        disabled,
        monitoring_preference="enabled",
        expected_binding_generation=1,
        verified_run_id=OpaqueIdV1("verified-run"),
    )
    for field in (
        "expected_account_version",
        "expected_connection_version",
        "expected_scope_generation",
        "expected_binding_generation",
    ):
        for invalid in (0, -1, True):
            with pytest.raises(ValueError, match="billing_monitoring_command_invalid"):
                if field == "expected_account_version":
                    replace(enabled, expected_account_version=invalid)
                elif field == "expected_connection_version":
                    replace(enabled, expected_connection_version=invalid)
                elif field == "expected_scope_generation":
                    replace(enabled, expected_scope_generation=invalid)
                else:
                    replace(enabled, expected_binding_generation=invalid)
    with pytest.raises(ValueError, match="billing_monitoring_command_invalid"):
        replace(disabled, verified_run_id=OpaqueIdV1("unneeded-proof"))
