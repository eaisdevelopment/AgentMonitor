"""A-P02/05: immutable alert contract validation; constructed pure inputs only."""

from datetime import UTC, datetime
from typing import cast

import pytest
from agentmonitor.contracts.alerting_v1 import (
    AlertRuleScopeV1,
    AlertScopeRefV1,
    CapacityRemainingRuleConfigurationV1,
    CreateAlertRuleCommandV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


@pytest.mark.parametrize(
    "warning,critical", [(10001, 1), (2999, 3000), (-1, -2), (True, 1), (3000, False)]
)
def test_invalid_threshold_document_rejected(warning: int, critical: int) -> None:
    with pytest.raises(ValueError):
        CapacityRemainingRuleConfigurationV1(1, warning, critical)


def test_zero_and_equal_thresholds_are_valid() -> None:
    assert (
        CapacityRemainingRuleConfigurationV1(1, 0, 0).critical_remaining_basis_points
        == 0
    )
    assert (
        CapacityRemainingRuleConfigurationV1(
            1, 1500, 1500
        ).warning_remaining_basis_points
        == 1500
    )


@pytest.mark.parametrize(
    "kind,value",
    [
        ("global", "unexpected"),
        ("account", None),
        ("provider", "name@example.invalid"),
        ("organization", "/private/path"),
    ],
)
def test_scope_rejects_wrong_shape_and_identity_text(
    kind: str, value: str | None
) -> None:
    with pytest.raises(ValueError):
        AlertScopeRefV1(cast(AlertRuleScopeV1, kind), value)


def test_rule_command_is_closed_and_requires_aware_time() -> None:
    with pytest.raises(ValueError):
        CreateAlertRuleCommandV1(
            OpaqueIdV1("command"),
            OpaqueIdV1("actor"),
            "capacity_remaining",
            AlertScopeRefV1("global", None),
            True,
            CapacityRemainingRuleConfigurationV1(1, 3000, 1500),
            datetime(2026, 9, 29),
        )
    command = CreateAlertRuleCommandV1(
        OpaqueIdV1("command"),
        OpaqueIdV1("actor"),
        "capacity_remaining",
        AlertScopeRefV1("global", None),
        True,
        CapacityRemainingRuleConfigurationV1(1, 3000, 1500),
        datetime(2026, 9, 29, tzinfo=UTC),
    )
    assert command.enabled
