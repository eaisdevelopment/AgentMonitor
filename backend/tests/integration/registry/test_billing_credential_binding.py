"""Real registry metadata and locks, without credential values or store claims."""

import secrets
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    CredentialBindingRepositoryErrorV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.adapters.providers.ollama.manifest import build_ollama_manifest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import CreateBillingConnectionCommandV1
from agentmonitor.contracts.registry_v1 import AccountViewV1
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    RegisterAccountV1,
)


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def _account(reference: DatabaseRefV1, provider: str) -> AccountViewV1:
    manifest = {
        "claude": build_claude_manifest,
        "codex": build_codex_manifest,
        "ollama": build_ollama_manifest,
    }[provider]()
    return RegisterAccountV1(SqliteRegistryRepositoryV1(reference)).pending(
        CreatePendingAccountCommandV1(
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            principal_id=OpaqueIdV1("isolated-binding-owner"),
            provider_key=provider,
            manifest_reference=get_manifest_fingerprint_v1(manifest),
            friendly_name="Credential metadata " + secrets.token_urlsafe(8),
            organization_id=None,
            requested_at=datetime.now(UTC),
        )
    )


def _billing_connection(reference: DatabaseRefV1, account: AccountViewV1) -> None:
    SqliteBillingConnectionRepositoryV1(reference).create(
        CreateBillingConnectionCommandV1(
            account_id=account.account_id,
            expected_account_version=account.record_version,
            principal_id=OpaqueIdV1("isolated-binding-owner"),
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            scope_id=None,
            requested_at=datetime.now(UTC),
        )
    )


def _archive(account: AccountViewV1) -> EditAccountCommandV1:
    return EditAccountCommandV1(
        account_id=account.account_id,
        expected_version=account.record_version,
        principal_id=OpaqueIdV1("isolated-binding-owner"),
        command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
        action="archive",
        requested_at=datetime.now(UTC),
    )


@pytest.mark.parametrize("provider", ["claude", "codex", "ollama"])
def test_prepare_and_archive_retire_only_pending_binding_metadata(
    tmp_path: Path, provider: str
) -> None:
    """M7-REG-CRED-001: real enrollment metadata, no stored or activated key."""
    reference = _database(tmp_path)
    account = _account(reference, provider)
    if provider != "ollama":
        _billing_connection(reference, account)
    registry = SqliteRegistryRepositoryV1(reference)
    original = registry.get_account(account.account_id)
    resources = registry.list_account_resources(account.account_id)
    profiles = registry.list_monitoring_profiles(account.account_id)
    assert profiles == ()
    bindings = SqliteCredentialBindingsV1(reference)
    initial = bindings.read(account.account_id)
    assert initial.bindings == ()
    assert initial.record_version == initial.binding_generation == 0
    if provider != "ollama":
        billing = SqliteBillingConnectionRepositoryV1(reference).get(account.account_id)
        assert billing is not None
        assert billing.credential_status is not None
        assert billing.credential_status.state == "missing"
        assert billing.credential_status.active_generation is None
        assert billing.credential_status.pending_generation is None
        assert not billing.credential_status.cleanup_required
    prepared = bindings.transition(
        account.account_id,
        action="prepare",
        expected_record_version=initial.record_version,
    )
    assert prepared.record_version == 1 and prepared.binding_generation == 0
    assert len(prepared.bindings) == 1
    pending = prepared.bindings[0]
    assert pending.lifecycle == "pending" and pending.generation == 1
    assert pending.association_provenance == "owner_asserted"
    if provider != "ollama":
        billing = SqliteBillingConnectionRepositoryV1(reference).get(account.account_id)
        assert billing is not None and billing.credential_status is not None
        assert billing.credential_status.state == "pending"
        assert billing.credential_status.pending_generation == pending.generation
        assert billing.credential_status.active_generation is None
    assert SqliteCredentialBindingsV1(reference).read(account.account_id) == prepared
    assert registry.get_account(account.account_id) == original
    assert registry.list_account_resources(account.account_id) == resources
    assert registry.list_monitoring_profiles(account.account_id) == profiles
    archived = registry.edit_account(_archive(account))
    assert archived.lifecycle == "archived"
    assert archived.identity_state == account.identity_state == "unresolved"
    assert archived.monitoring_preference == account.monitoring_preference == "disabled"
    assert registry.list_monitoring_profiles(account.account_id) == profiles
    retired = SqliteCredentialBindingsV1(reference).read(account.account_id)
    assert retired.record_version == prepared.record_version + 1
    assert retired.binding_generation == prepared.binding_generation + 1
    assert len(retired.bindings) == 1
    assert retired.bindings[0].binding_id == pending.binding_id
    assert retired.bindings[0].lifecycle == "cleanup_pending"
    assert retired.bindings[0].reason_code == "account_archived"
    if provider != "ollama":
        billing = SqliteBillingConnectionRepositoryV1(reference).get(account.account_id)
        assert billing is not None and billing.credential_status is not None
        assert billing.credential_status.state == "cleanup_required"
        assert billing.credential_status.cleanup_required
        assert billing.credential_status.active_generation is None
        assert billing.credential_status.pending_generation is None
    assert bindings.has_unfinished_bindings()
    with pytest.raises(
        CredentialBindingRepositoryErrorV1,
        match="credential_binding_account_unavailable",
    ):
        bindings.transition(
            account.account_id,
            action="prepare",
            expected_record_version=retired.record_version,
        )
    assert bindings.read(account.account_id) == retired
    # No cleanup-complete or active transition: neither store nor deletion occurred.


@pytest.mark.parametrize("provider", ["claude", "codex", "ollama"])
def test_archive_uses_existing_account_credential_lock(
    tmp_path: Path, provider: str
) -> None:
    """M7-REG-CRED-002: archive cannot race the owner credential operation."""
    reference = _database(tmp_path)
    account = _account(reference, provider)
    if provider != "ollama":
        _billing_connection(reference, account)
    registry = SqliteRegistryRepositoryV1(reference)
    before = registry.get_account(account.account_id)
    command = _archive(account)
    with account_credential_lock(reference, account.account_id):
        with pytest.raises(ValueError, match="credential_account_busy"):
            registry.edit_account(command)
        assert registry.get_account(account.account_id) == before
    assert registry.edit_account(command).lifecycle == "archived"


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_nonbilling_account_cannot_prepare_binding_but_can_archive(
    tmp_path: Path, provider: str
) -> None:
    """M7-REG-CRED-003: subscription-only accounts gain no credential authority."""
    reference = _database(tmp_path)
    account = _account(reference, provider)
    bindings = SqliteCredentialBindingsV1(reference)
    with pytest.raises(
        CredentialBindingRepositoryErrorV1,
        match="credential_binding_account_unavailable",
    ):
        bindings.read(account.account_id)
    with pytest.raises(
        CredentialBindingRepositoryErrorV1,
        match="credential_binding_account_unavailable",
    ):
        bindings.transition(
            account.account_id, action="prepare", expected_record_version=0
        )
    assert not bindings.has_unfinished_bindings()
    registry = SqliteRegistryRepositoryV1(reference)
    assert registry.get_account(account.account_id) == account
    assert registry.edit_account(_archive(account)).lifecycle == "archived"
    assert not bindings.has_unfinished_bindings()
