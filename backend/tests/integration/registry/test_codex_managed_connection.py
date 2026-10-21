"""Codex initial managed-profile connection over real SQLite and filesystem."""

from __future__ import annotations

import asyncio
import os
import sqlite3
import stat
import time
import uuid
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.codex.authentication.identity import (
    read_managed_profile_identity_v1,
)
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.composition.codex_dashboard_connection import (
    CodexDashboardConnectionV1,
)
from agentmonitor.composition.codex_installation_reconciliation import (
    reconcile_codex_installation_v1,
)
from agentmonitor.composition.codex_managed_connection import (
    enroll_verified_managed_codex_v1,
    managed_codex_root_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    ProviderConnectionErrorV1,
    StartProviderConnectionCommandV1,
)
from agentmonitor.contracts.registry_v1 import AccountViewV1
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    RegisterAccountV1,
)


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def _without_registry_revision(value: object) -> tuple[tuple[str, object], ...]:
    return tuple(
        (field.name, getattr(value, field.name))
        for field in fields(value)  # type: ignore[arg-type]
        if field.name != "registry_revision"
    )


def _pending_codex(
    reference: DatabaseRefV1, *, friendly_name: str = "Owner selected Codex"
) -> AccountViewV1:
    repository = SqliteRegistryRepositoryV1(reference)
    return RegisterAccountV1(repository).pending(
        CreatePendingAccountCommandV1(
            OpaqueIdV1(uuid.uuid4().hex),
            OpaqueIdV1("owner-codex-connection"),
            "codex",
            get_manifest_fingerprint_v1(build_codex_manifest()),
            friendly_name,
            None,
            datetime.now(UTC),
        )
    )


def test_real_codex_installation_reconciles_before_connection(
    tmp_path: Path,
) -> None:
    """M5-CDX-REG-001: installed exact CLI becomes one current M02 installation."""
    reference = _database(tmp_path)

    first = reconcile_codex_installation_v1(reference)
    second = reconcile_codex_installation_v1(reference)
    rows = SqliteRegistryRepositoryV1(reference).list_provider_installations("codex")

    assert first.replay_verified and second.replay_verified
    assert first.provider_installation_id == second.provider_installation_id
    assert len(rows) == 1
    assert rows[0].provider_key == "codex"
    assert (
        rows[0].version.masked_value == discover_default_installation().provider_version
    )
    assert rows[0].presence_state == "present"


def test_status_read_is_side_effect_free_for_pending_codex_account(
    tmp_path: Path,
) -> None:
    """M5-CDX-CONNECT-004: GET/startup does not create roots or start login."""
    reference = _database(tmp_path)
    account = _pending_codex(reference)
    connection = CodexDashboardConnectionV1(reference, tmp_path)

    view = connection.read(account.account_id)

    async def start_and_stop_lifecycle() -> None:
        task = asyncio.create_task(connection.run())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(start_and_stop_lifecycle())

    assert view.account_id == account.account_id
    assert view.flow_id is None
    assert view.state == "idle"
    assert view.can_connect
    assert view.reason_code == "pending_profile"
    assert not (tmp_path / "profiles").exists()
    assert not (tmp_path / "connection-flows").exists()
    assert (
        SqliteRegistryRepositoryV1(reference).get_account(account.account_id) == account
    )


def test_managed_root_is_deterministic_provider_specific_and_uncreated(
    tmp_path: Path,
) -> None:
    """M5-CDX-REG-002: opaque account IDs derive no public or cross-provider path."""
    account_id = OpaqueIdV1("private-owner-account")

    first = managed_codex_root_v1(tmp_path, account_id)
    second = managed_codex_root_v1(tmp_path, account_id)

    assert first == second
    assert first.parent == tmp_path / "profiles" / "codex"
    assert first.name != account_id.value
    assert len(first.name) == 64
    assert not first.exists()


def test_unauthenticated_managed_root_cannot_mutate_registry(
    tmp_path: Path,
) -> None:
    """M5-CDX-REG-003: enrollment requires a current real managed identity."""
    reference = _database(tmp_path)
    reconcile_codex_installation_v1(reference)
    account = _pending_codex(reference)
    installation = discover_default_installation()
    root = managed_codex_root_v1(tmp_path, account.account_id)
    root.mkdir(mode=0o700, parents=True)
    root.parent.chmod(0o700)
    root.parent.parent.chmod(0o700)
    assert (
        read_managed_profile_identity_v1(
            installation,
            managed_profiles_root=root.parent,
            managed_profile_root=root,
        )
        is None
    )
    repository = SqliteRegistryRepositoryV1(reference)
    before = repository.get_account(account.account_id)

    with pytest.raises(ValueError, match="codex_managed_identity_changed"):
        enroll_verified_managed_codex_v1(
            reference,
            data_root=tmp_path,
            account_id=account.account_id,
            installation=installation,
            expected_identity=None,
            principal_id=OpaqueIdV1("owner-codex-connection"),
            expected_account_record_version=account.record_version,
        )

    assert repository.get_account(account.account_id) == before
    assert repository.list_monitoring_profiles(account.account_id) == ()
    assert repository.list_account_resources(account.account_id) == ()


def test_codex_connection_port_rejects_another_provider_without_io(
    tmp_path: Path,
) -> None:
    """M5-CDX-CONNECT-005: provider dispatch cannot launch Codex for Claude."""
    reference = _database(tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    account = RegisterAccountV1(repository).pending(
        CreatePendingAccountCommandV1(
            OpaqueIdV1(uuid.uuid4().hex),
            OpaqueIdV1("owner-codex-connection"),
            "claude",
            "a" * 32,
            "Different provider",
            None,
            datetime.now(UTC),
        )
    )
    connection = CodexDashboardConnectionV1(reference, tmp_path)

    view = connection.read(account.account_id)

    assert not view.can_connect
    assert view.reason_code == "account_not_connectable"
    assert not (tmp_path / "profiles").exists()
    assert not (tmp_path / "connection-flows").exists()


def test_explicit_start_reconciles_installation_then_fails_unsafe_root_closed(
    tmp_path: Path,
) -> None:
    """M5-CDX-CONNECT-007: POST alone starts work and profile links stay closed."""
    reference = _database(tmp_path)
    account = _pending_codex(reference)
    root = managed_codex_root_v1(tmp_path, account.account_id)
    root.parent.mkdir(mode=0o700, parents=True)
    root.parent.parent.chmod(0o700)
    root.parent.chmod(0o700)
    target = tmp_path / "unsafe-profile-target"
    target.mkdir(mode=0o700)
    root.symlink_to(target, target_is_directory=True)
    connection = CodexDashboardConnectionV1(reference, tmp_path)

    started = connection.start(
        StartProviderConnectionCommandV1(
            account.account_id,
            account.record_version,
            "owner@example.invalid",
            OpaqueIdV1("owner-codex-connection"),
            OpaqueIdV1(uuid.uuid4().hex),
            OpaqueIdV1(uuid.uuid4().hex),
        )
    )
    assert started.state == "requested"
    deadline = time.monotonic() + 8
    while True:
        view = connection.read(account.account_id)
        if view.state == "failed":
            break
        assert time.monotonic() < deadline, "unsafe managed root did not fail closed"
        time.sleep(0.02)

    assert view.reason_code == "connection_failed"
    assert tuple(target.iterdir()) == ()
    rows = SqliteRegistryRepositoryV1(reference).list_provider_installations("codex")
    assert len(rows) == 1 and rows[0].presence_state == "present"
    receipts = tuple((tmp_path / "connection-flows" / "codex").glob("*.json"))
    assert len(receipts) == 1
    assert stat.S_IMODE(receipts[0].stat().st_mode) == 0o600
    assert b"owner@example.invalid" not in receipts[0].read_bytes()


def test_live_connected_profile_enrollment_is_idempotent_when_selected(
    tmp_path: Path,
) -> None:
    """M5-CDX-REG-004..006: owner-selected real profile enrollment witness."""
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    account_id = os.environ.get("AGENTMONITOR_TEST_CODEX_MANAGED_ACCOUNT_ID")
    if selected is None or account_id is None:
        pytest.skip("NOT RUN: explicit owner Codex account and data root required")
    data_root = Path(selected)
    owner_reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    owner_repository = SqliteRegistryRepositoryV1(owner_reference)
    target = OpaqueIdV1(account_id)
    account = owner_repository.get_account(target)
    assert account is not None and account.provider_key == "codex"
    owner_registry_before = (
        owner_repository.get_account(target),
        owner_repository.list_monitoring_profiles(target),
        owner_repository.list_account_resources(target),
        owner_repository.list_provider_installations("codex"),
    )
    copied_path = tmp_path / "agentmonitor.db"
    with sqlite3.connect(
        f"file:{data_root / 'agentmonitor.db'}?mode=ro", uri=True
    ) as source:
        with sqlite3.connect(copied_path) as copied:
            source.backup(copied)
    reference = DatabaseRefV1(copied_path, tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    installation = discover_default_installation()
    identity = read_managed_profile_identity_v1(
        installation,
        managed_profiles_root=managed_codex_root_v1(data_root, target).parent,
        managed_profile_root=managed_codex_root_v1(data_root, target),
    )
    assert identity is not None, "selected managed Codex identity required"

    enroll_verified_managed_codex_v1(
        reference,
        data_root=data_root,
        account_id=target,
        installation=installation,
        expected_identity=identity,
        principal_id=OpaqueIdV1("agentmonitor-owner"),
        expected_account_record_version=account.record_version,
    )

    after_first = repository.get_account(target)
    assert after_first is not None and after_first.is_effective_monitoring_enabled
    first_profiles = repository.list_monitoring_profiles(target)
    first_resources = repository.list_account_resources(target)

    enroll_verified_managed_codex_v1(
        reference,
        data_root=data_root,
        account_id=target,
        installation=installation,
        expected_identity=identity,
        principal_id=OpaqueIdV1("agentmonitor-owner"),
        expected_account_record_version=after_first.record_version,
    )

    after_second = repository.get_account(target)
    profiles = repository.list_monitoring_profiles(target)
    resources = repository.list_account_resources(target)
    assert after_second is not None
    assert after_second.registry_revision == after_first.registry_revision + 1
    assert _without_registry_revision(after_second) == _without_registry_revision(
        after_first
    )
    assert tuple(_without_registry_revision(item) for item in profiles) == tuple(
        _without_registry_revision(item) for item in first_profiles
    )
    assert tuple(_without_registry_revision(item) for item in resources) == tuple(
        _without_registry_revision(item) for item in first_resources
    )
    assert all(
        item.registry_revision == after_second.registry_revision for item in profiles
    )
    assert all(
        item.registry_revision == after_second.registry_revision for item in resources
    )
    assert len(profiles) == len(resources) == 1
    assert profiles[0].management_state == "managed"
    assert not profiles[0].is_protected_default
    assert profiles[0].resource_ids == (resources[0].resource_id,)
    assert (
        owner_repository.get_account(target),
        owner_repository.list_monitoring_profiles(target),
        owner_repository.list_account_resources(target),
        owner_repository.list_provider_installations("codex"),
    ) == owner_registry_before


def test_corrupt_connection_receipt_directory_fails_closed(
    tmp_path: Path,
) -> None:
    """M5-CDX-CONNECT-006: status never follows an unsafe receipt directory."""
    reference = _database(tmp_path)
    account = _pending_codex(reference)
    target = tmp_path / "unsafe-receipts"
    target.mkdir(mode=0o700)
    parent = tmp_path / "connection-flows"
    parent.mkdir(mode=0o700)
    (parent / "codex").symlink_to(target, target_is_directory=True)

    with pytest.raises(
        ProviderConnectionErrorV1, match="provider_connection_unavailable"
    ):
        CodexDashboardConnectionV1(reference, tmp_path).read(account.account_id)

    assert tuple(target.iterdir()) == ()
