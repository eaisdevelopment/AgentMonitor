"""Real operator connection binds the selected owner profile and admin record."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_managed_connection_preserves_account_and_enables_monitoring() -> None:
    """M02-MANAGED-002: real official identity, preserved admin metadata, graph."""
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    account_id = os.environ.get("AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID")
    if selected is None or account_id is None:
        pytest.skip("NOT RUN: explicit owner account and data root required")
    root = Path(selected)
    repository = SqliteRegistryRepositoryV1(
        DatabaseRefV1(root / "agentmonitor.db", root)
    )
    target = OpaqueIdV1(account_id)
    before = repository.get_account(target)
    assert before is not None
    result = subprocess.run(
        [
            sys.executable,
            "tools/providers/connect_claude_profile.py",
            "--data-root",
            str(root),
            "--account-id",
            account_id,
            "--enroll",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, "managed connection did not enroll"
    assert "MONITORING ENABLED" in result.stdout
    after = repository.get_account(target)
    assert after is not None and after.is_effective_monitoring_enabled
    assert (after.account_id, after.friendly_name, after.organization_id) == (
        before.account_id,
        before.friendly_name,
        before.organization_id,
    )
    profiles = repository.list_monitoring_profiles(target)
    resources = repository.list_account_resources(target)
    assert len(profiles) == len(resources) == 1
    assert profiles[0].management_state == "managed"
    assert not profiles[0].is_protected_default
    assert profiles[0].resource_ids == (resources[0].resource_id,)


def test_official_setup_requires_an_owner_terminal() -> None:
    """CLA-MANAGED-008: redirected provider setup never starts or captures UI."""
    result = subprocess.run(
        [
            sys.executable,
            "tools/providers/connect_claude_profile.py",
            "--data-root",
            "/tmp",
            "--account-id",
            "owner-selected",
            "--setup",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 3
    assert (
        result.stdout
        == "CLAUDE CONNECTION: BLOCKED — owner terminal required for setup\n"
    )
