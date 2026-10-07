"""Read-only owner-installation guards for the V1-M5 Codex fleet selection."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.registry.application.accounts import (
    GetAccountV1,
)

from tools.automation.implementations.m5_owner_outcomes import (
    OWNER_OUTCOMES_BASENAME,
    read_owner_outcomes_file_v2,
)


def _selected_owner_installation() -> tuple[DatabaseRefV1, Path]:
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    selected_outcomes = os.environ.get("AGENTMONITOR_TEST_M5_OWNER_OUTCOMES")
    if not selected or not selected_outcomes:
        pytest.fail("BLOCKED: m5_owner_installation_required")
    assert selected is not None and selected_outcomes is not None
    root = Path(selected)
    outcomes = Path(selected_outcomes)
    try:
        reference = DatabaseRefV1(root / "agentmonitor.db", root)
        reference.validate()
        if outcomes != root / OWNER_OUTCOMES_BASENAME:
            raise ValueError
    except (OSError, ValueError):
        pytest.fail("BLOCKED: m5_owner_installation_invalid")
    return reference, outcomes


def test_four_codex_outcomes_bind_to_exact_registry_identity_graphs() -> None:
    """M5-CDX-GATE-003..006: private outcomes resolve without guessing."""

    reference, path = _selected_owner_installation()
    selected, _digest = read_owner_outcomes_file_v2(path, now=datetime.now(UTC))
    repository = SqliteRegistryRepositoryV1(reference)
    get_account = GetAccountV1(repository)

    for account_id in selected.unavailable_account_ids:
        account = get_account(OpaqueIdV1(account_id))
        assert account is not None
        assert account.provider_key == "codex"
        assert account.lifecycle != "archived"

    for outcome in selected.outcomes:
        if outcome.disposition != "verified":
            continue
        account = get_account(OpaqueIdV1(outcome.account_id))
        assert account is not None
        assert account.provider_key == "codex"
        assert account.lifecycle == "active"
        assert account.identity_state in {"matched", "owner_confirmed"}
        assert account.is_effective_monitoring_enabled
        profiles = repository.list_monitoring_profiles(account.account_id)
        resources = repository.list_account_resources(account.account_id)
        assert len(profiles) == 1
        assert profiles[0].lifecycle == "active"
        assert profiles[0].management_state == "managed"
        assert not profiles[0].is_protected_default
        assert profiles[0].compatibility_state == "compatible"
        assert profiles[0].identity_state in {"owner_confirmed", "provider_verified"}
        assert len(resources) == 1
        assert resources[0].lifecycle == "active"
        assert resources[0].kind == "subscription_pool"
        assert profiles[0].profile_id in resources[0].linked_profile_ids
        assert resources[0].resource_id in profiles[0].resource_ids
