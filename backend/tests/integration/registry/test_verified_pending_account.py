"""Pending activation with real provider identity and real SQLite commands."""

import uuid
from dataclasses import replace
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
from agentmonitor.adapters.providers.claude.authentication.identity import (
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ConfirmProviderIdentityFingerprintCommandV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    ConfirmProviderIdentityFingerprintV1,
    CreatePendingAccountCommandV1,
    RegisterAccountV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)


def test_real_identity_activates_only_explicit_current_pending_account(
    tmp_path: Path,
) -> None:
    """M02-MANAGED-001: version, defaults, stable ID, replay, duplicate rejection."""
    identity = read_default_profile_identity_v1(discover_default_installation())
    assert identity is not None, "real owner Claude identity required"
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteRegistryRepositoryV1(reference)
    pending = RegisterAccountV1(repository).pending(
        CreatePendingAccountCommandV1(
            OpaqueIdV1(uuid.uuid4().hex),
            OpaqueIdV1("owner-managed-connection"),
            "claude",
            get_manifest_fingerprint_v1(build_claude_manifest()),
            identity.email,
            None,
            datetime.now(UTC),
        )
    )
    command = ConfirmProviderIdentityFingerprintCommandV1(
        idempotency_key=OpaqueIdV1(uuid.uuid4().hex),
        principal_id=OpaqueIdV1("owner-managed-connection"),
        account_id=pending.account_id,
        expected_account_record_version=pending.record_version,
        provider_key="claude",
        identity_scheme="claude.cli.auth.status.sha256",
        identity_scope="provider_account",
        identity_scheme_version=1,
        subject_fingerprint=identity.fingerprint,
        source_id="claude.auth.status",
        source_version="1",
        parser_version="1",
        evidence_reference=OpaqueIdV1("auth-status-" + uuid.uuid4().hex),
        expected_evidence_digest=identity.fingerprint,
        requested_at=datetime.now(UTC),
    )
    confirm = ConfirmProviderIdentityFingerprintV1(repository)
    with pytest.raises(RegistryCommandConflictV1, match="registry_identity_conflict"):
        confirm(command)
    assert repository.get_account(pending.account_id) == pending
    explicit = replace(command, activate_pending_account=True)
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_account_version_conflict"
    ):
        confirm(replace(explicit, expected_account_record_version=2))
    resolved = confirm(explicit)
    current = repository.get_account(pending.account_id)
    assert current is not None
    assert current.account_id == pending.account_id == resolved.account_id
    assert current.lifecycle == "active" and current.identity_state == "owner_confirmed"
    assert current.friendly_name == pending.friendly_name
    assert current.organization_id == pending.organization_id
    assert current.record_version == pending.record_version + 1
    assert current.monitoring_preference == "disabled"
    assert confirm(explicit) == resolved
    other = RegisterAccountV1(repository).pending(
        CreatePendingAccountCommandV1(
            OpaqueIdV1(uuid.uuid4().hex),
            command.principal_id,
            "claude",
            get_manifest_fingerprint_v1(build_claude_manifest()),
            identity.email + " (second record)",
            None,
            datetime.now(UTC),
        )
    )
    with pytest.raises(RegistryCommandConflictV1, match="registry_identity_conflict"):
        confirm(
            replace(
                explicit,
                idempotency_key=OpaqueIdV1(uuid.uuid4().hex),
                account_id=other.account_id,
            )
        )
    assert repository.get_account(other.account_id) == other
