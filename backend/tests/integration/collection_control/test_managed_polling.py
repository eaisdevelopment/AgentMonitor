"""Live owner registry and collection cadence across isolated Claude accounts."""

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.authentication.identity import (
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.manifest import CLAUDE_USAGE_SOURCE_ID
from agentmonitor.composition.claude_dashboard_collection import (
    ClaudeDashboardCollectorV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.queries import (
    GetLatestSourceRunV1,
)


def test_latest_source_cadence_is_account_scoped() -> None:
    """M04-MANAGED-001: another real account's run cannot delay this account."""
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    account_id = os.environ.get("AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID")
    if selected is None or account_id is None:
        pytest.skip("NOT RUN: explicit owner data root and managed account required")
    root = Path(selected)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    repository = SqliteCollectionRepositoryV1(reference)
    accounts = SqliteRegistryRepositoryV1(reference).list_accounts("claude")
    targets = tuple(
        account for account in accounts if account.is_effective_monitoring_enabled
    )
    assert targets, "real existing monitored account required"
    query = GetLatestSourceRunV1(repository)
    instant = datetime.now(UTC)
    for target in targets:
        latest = query(
            "claude",
            "subscription.quota",
            CLAUDE_USAGE_SOURCE_ID,
            instant,
            account_id=target.account_id,
        )
        assert latest is not None and latest.account_id == target.account_id
    managed = query(
        "claude",
        "subscription.quota",
        CLAUDE_USAGE_SOURCE_ID,
        instant,
        account_id=OpaqueIdV1(account_id),
    )
    assert managed is None or (
        managed.account_id is not None and managed.account_id.value == account_id
    )


def test_collector_attests_managed_account_quota_independently() -> None:
    """M04-MANAGED-002: real scheduled run and isolated identity receipt."""
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    account_id = os.environ.get("AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID")
    if selected is None or account_id is None:
        pytest.skip("NOT RUN: explicit owner data root and managed account required")
    root = Path(selected)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    collector = ClaudeDashboardCollectorV1(
        reference, managed_profiles_root=root / "profiles" / "claude"
    )
    for _ in range(3):
        collector.tick()
        receipt = collector.read_verified_identity(OpaqueIdV1(account_id))
        if receipt is not None:
            break
    assert receipt is not None, "no attested managed quota collected"
    native = read_default_profile_identity_v1(
        discover_default_installation(),
        managed_profile_root=root
        / "profiles"
        / "claude"
        / hashlib.sha256(account_id.encode()).hexdigest(),
    )
    assert native is not None and receipt.identity.fingerprint == native.fingerprint
    runs = SqliteCollectionRepositoryV1(reference).list_runs(
        "claude", OpaqueIdV1(account_id), datetime.now(UTC), 100
    )
    matching = tuple(run for run in runs if run.run_id == receipt.collection_run_id)
    assert len(matching) == 1 and matching[0].state in {"succeeded", "partial"}
    assert (
        matching[0].account_id is not None
        and matching[0].account_id.value == account_id
    )
