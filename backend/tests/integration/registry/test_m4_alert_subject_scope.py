"""Actual owner registry correlation through M02 ports, with no invented accounts."""

import os
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1


def test_current_alert_subject_scope_preserves_genuine_membership() -> None:
    root_value = os.environ.get("AGENTMONITOR_TEST_DATA_ROOT")
    if root_value is None:
        pytest.skip("NOT RUN: select actual owner AgentMonitor data root")
    root = Path(root_value)
    repository = SqliteRegistryRepositoryV1(
        DatabaseRefV1(root / "agentmonitor.db", root)
    )
    accounts = ListAccountsV1(repository)("claude")
    if not accounts:
        pytest.skip("BLOCKED: no actual enrolled Claude accounts")
    import agentmonitor.modules.registry.application.accounts as queries

    resolve = getattr(queries, "ResolveAlertSubjectScopeV1", None)
    assert resolve is not None, "M4 M02 current alert subject query is missing"
    for account in accounts:
        scope = resolve(repository)(account.account_id)
        assert scope.account_id == account.account_id
        assert scope.organization_id == account.organization_id
        assert scope.provider_key == account.provider_key
        assert scope.eligible == account.is_effective_monitoring_enabled
        assert scope.registry_revision > 0
