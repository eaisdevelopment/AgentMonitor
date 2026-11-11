"""Real billing metadata guards and pure scope-fence checks; no credentials."""

import os
import pty
import secrets
import select
import subprocess
import sys
import termios
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentmonitor.adapters.credential_env.format import CredentialProviderKey
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.adapters.providers.ollama.manifest import build_ollama_manifest
from agentmonitor.composition.ollama_credential_enrollment import (
    EnrollmentError,
    _require_same_billing_target,
    require_billing_credential_target,
)
from agentmonitor.composition.ollama_env_store import update_managed_env
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import (
    AccountBillingConnectionsV1,
    BillingConnectionViewV1,
    CreateBillingConnectionCommandV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    RegisterAccountV1,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationCommandV1,
)


def _assert_real_terminal_rejects_missing_resource(
    reference: DatabaseRefV1, account_id: OpaqueIdV1
) -> None:
    master, slave = pty.openpty()
    try:
        with subprocess.Popen(
            [
                sys.executable,
                "-m",
                "agentmonitor.composition.billing_credential_operator",
                "--data-root",
                str(reference._approved_root),
                "--account-id=" + account_id.value,
                "--resource-id=absent-resource",
            ],
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")},
            stdin=slave,
            stdout=slave,
            stderr=slave,
        ) as process:
            os.close(slave)
            slave = -1
            try:
                result = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                raise
        output = os.read(master, 8192).decode("utf-8")
        assert result == 1
        assert "The billing credential operation could not finish." in output
        assert "API key:" not in output
    finally:
        os.close(master)
        if slave >= 0:
            os.close(slave)


def _assert_real_hidden_terminal_cancellation(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    provider: CredentialProviderKey,
    account_label: str,
    organization_label: str,
) -> None:
    directory = reference._approved_root / "credential-file"
    directory.mkdir(mode=0o700)
    env_path = directory / ".env"
    descriptor = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    # Establish real location/lock metadata through a no-op removal. No key exists.
    update_managed_env(
        env_path,
        "amcb_" + secrets.token_hex(16),
        None,
        provider_key=provider,
        staging_root=reference._approved_root,
    )
    script = """
import sys
from pathlib import Path
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.composition.billing_credential_operator import (
    enroll_selected_billing_credential,
)
from agentmonitor.composition.ollama_env_store import env_location_matches
from agentmonitor.contracts.common_v1 import OpaqueIdV1
root = Path(sys.argv[1])
env = Path(sys.argv[4])
try:
    enroll_selected_billing_credential(
        DatabaseRefV1(root / 'agentmonitor.db', root),
        OpaqueIdV1(sys.argv[2]), OpaqueIdV1(sys.argv[3]), env,
        selection_current=lambda: env_location_matches(root, env),
    )
except EOFError:
    print('owner_cancelled_without_key')
    sys.exit(2)
sys.exit(3)
"""
    master, slave = pty.openpty()
    try:
        with subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                str(reference._approved_root),
                account_id.value,
                resource_id.value,
                str(env_path),
            ],
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")},
            stdin=slave,
            stdout=slave,
            stderr=slave,
        ) as process:
            os.close(slave)
            slave = -1
            try:
                prompt = (
                    b"Anthropic administrative API key: "
                    if provider == "claude"
                    else b"OpenAI administrative API key: "
                )
                output = bytearray()
                deadline = time.monotonic() + 10
                while prompt not in output and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.2)[0]:
                        output.extend(os.read(master, 4096))
                    assert len(output) <= 8192
                assert prompt in output
                assert account_label.encode("utf-8") in output
                assert organization_label.encode("utf-8") in output
                assert not termios.tcgetattr(master)[3] & termios.ECHO
                os.write(master, b"\x04")
                assert process.wait(timeout=10) == 2
                output.extend(os.read(master, 4096))
                assert b"owner_cancelled_without_key" in output
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
    finally:
        os.close(master)
        if slave >= 0:
            os.close(slave)
    assert env_path.stat().st_size == 0
    state = SqliteCredentialBindingsV1(reference).read(account_id)
    assert state.binding_generation == 0
    assert len(state.bindings) == 1 and state.bindings[0].lifecycle == "pending"


def _assert_legacy_helpers_reject_billing(
    reference: DatabaseRefV1, account_id: OpaqueIdV1
) -> None:
    script = """
import sys
from pathlib import Path
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.composition.ollama_credential_enrollment import (
    EnrollmentError, cleanup_ollama_credential, disconnect_ollama_credential,
)
from agentmonitor.composition.ollama_env_store import env_location_matches
from agentmonitor.contracts.common_v1 import OpaqueIdV1
root = Path(sys.argv[1])
env = root / 'credential-file' / '.env'
operation = {
    'cleanup': cleanup_ollama_credential,
    'disconnect': disconnect_ollama_credential,
}[sys.argv[3]]
try:
    operation(
        DatabaseRefV1(root / 'agentmonitor.db', root), OpaqueIdV1(sys.argv[2]), env,
        selection_current=lambda: env_location_matches(root, env),
    )
except EnrollmentError as error:
    sys.exit(0 if str(error) == 'credential_binding_account_unavailable' else 4)
sys.exit(3)
"""
    for action in ("cleanup", "disconnect"):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(reference._approved_root),
                account_id.value,
                action,
            ],
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, (
            "legacy Ollama helper must reject billing provider"
        )


@pytest.mark.parametrize("provider", ["claude", "codex", "ollama"])
def test_selected_metadata_is_required_and_account_changes_invalidate_capture(
    tmp_path: Path, provider: str
) -> None:
    """M7-ENROLL-003: normal account/billing CRUD supplies exact target evidence."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    registry = SqliteRegistryRepositoryV1(reference)
    manifest = {
        "claude": build_claude_manifest,
        "codex": build_codex_manifest,
        "ollama": build_ollama_manifest,
    }[provider]()
    organization = None
    if provider == "claude":
        organization = registry.create_organization(
            CreateOrganizationCommandV1(
                command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
                principal_id=OpaqueIdV1("isolated-enrollment-owner"),
                name="Billing organization " + secrets.token_urlsafe(8),
                description=None,
                requested_at=datetime.now(UTC),
            )
        )
    account = RegisterAccountV1(registry).pending(
        CreatePendingAccountCommandV1(
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            principal_id=OpaqueIdV1("isolated-enrollment-owner"),
            provider_key=provider,
            manifest_reference=get_manifest_fingerprint_v1(manifest),
            friendly_name="Billing entry " + secrets.token_urlsafe(8),
            organization_id=organization.organization_id
            if organization is not None
            else None,
            requested_at=datetime.now(UTC),
        )
    )
    with pytest.raises(EnrollmentError, match="billing_credential_target_unavailable"):
        require_billing_credential_target(
            reference, account.account_id, OpaqueIdV1("absent-resource")
        )
    _assert_real_terminal_rejects_missing_resource(reference, account.account_id)
    if provider == "ollama":
        assert not SqliteCredentialBindingsV1(reference).has_unfinished_bindings()
        return
    created = SqliteBillingConnectionRepositoryV1(reference).create(
        CreateBillingConnectionCommandV1(
            account_id=account.account_id,
            expected_account_version=account.record_version,
            principal_id=OpaqueIdV1("isolated-enrollment-owner"),
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            scope_id=None,
            requested_at=datetime.now(UTC),
        )
    )
    captured = require_billing_credential_target(
        reference, account.account_id, created.resource_id
    )
    assert captured.connections == (created,)
    assert (
        require_billing_credential_target(
            reference, account.account_id, created.resource_id, expected=captured
        )
        == captured
    )
    with pytest.raises(EnrollmentError, match="billing_credential_target_unavailable"):
        require_billing_credential_target(
            reference, account.account_id, OpaqueIdV1("different-resource")
        )
    _assert_real_hidden_terminal_cancellation(
        reference,
        account.account_id,
        created.resource_id,
        "claude" if provider == "claude" else "codex",
        account.friendly_name,
        organization.name if organization is not None else "Ungrouped",
    )
    _assert_legacy_helpers_reject_billing(reference, account.account_id)
    renamed = registry.edit_account(
        EditAccountCommandV1(
            account_id=account.account_id,
            expected_version=account.record_version,
            principal_id=OpaqueIdV1("isolated-enrollment-owner"),
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            action="rename",
            friendly_name="Updated billing entry " + secrets.token_urlsafe(8),
            requested_at=datetime.now(UTC),
        )
    )
    with pytest.raises(EnrollmentError, match="billing_credential_target_changed"):
        require_billing_credential_target(
            reference, account.account_id, created.resource_id, expected=captured
        )
    registry.edit_account(
        EditAccountCommandV1(
            account_id=account.account_id,
            expected_version=renamed.record_version,
            principal_id=OpaqueIdV1("isolated-enrollment-owner"),
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            action="archive",
            requested_at=datetime.now(UTC),
        )
    )
    with pytest.raises(EnrollmentError, match="billing_credential_target_unavailable"):
        require_billing_credential_target(
            reference, account.account_id, created.resource_id
        )
    retired = SqliteCredentialBindingsV1(reference).read(account.account_id)
    assert len(retired.bindings) == 1
    assert retired.bindings[0].lifecycle == "cleanup_pending"
    assert retired.bindings[0].reason_code == "account_archived"
    assert registry.list_monitoring_profiles(account.account_id) == ()


def _pure_target() -> AccountBillingConnectionsV1:
    now = datetime(2026, 11, 11, tzinfo=UTC)
    connection = BillingConnectionViewV1(
        account_id=OpaqueIdV1("pure-account"),
        resource_id=OpaqueIdV1("pure-resource"),
        provider_key="claude",
        scope_id=None,
        scope_evidence="unresolved",
        scope_generation=1,
        monitoring_preference="disabled",
        lifecycle="pending",
        record_version=1,
        registry_revision=1,
        created_at=now,
        updated_at=now,
    )
    return AccountBillingConnectionsV1(
        account_id=connection.account_id,
        provider_key="claude",
        account_lifecycle="pending",
        account_record_version=1,
        can_add_connection=False,
        reason_code="billing_connection_exists",
        connections=(connection,),
    )


def test_pure_guard_detects_scope_epoch_and_resource_changes() -> None:
    """M7-ENROLL-004: constructed no-I/O context checks fence the selected scope."""
    captured = _pure_target()
    _require_same_billing_target(captured, captured)
    for changed in (
        replace(captured.connections[0], scope_generation=2),
        replace(captured.connections[0], resource_id=OpaqueIdV1("different-resource")),
        replace(captured.connections[0], record_version=2),
        replace(
            captured.connections[0],
            scope_id="different-scope",
            scope_evidence="owner_asserted",
        ),
    ):
        with pytest.raises(EnrollmentError, match="billing_credential_target_changed"):
            _require_same_billing_target(
                captured, replace(captured, connections=(changed,))
            )
