"""Actual local operator/SQLite/empty protected store, without manufactured keys."""

import os
import pty
import secrets
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition import billing_credential_operator
from agentmonitor.composition.ollama_credential_enrollment import EnrollmentError
from agentmonitor.composition.ollama_env_store import (
    env_location_matches,
    update_managed_env,
)

from backend.tests.integration.registry.test_billing_credential_binding import (
    _account,
    _archive,
    _billing_connection,
    _database,
)

_OPERATOR = """
import sys
from pathlib import Path
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.composition.billing_credential_operator import (
    maintain_selected_billing_credential,
)
from agentmonitor.composition.ollama_env_store import read_env_location
from agentmonitor.contracts.common_v1 import OpaqueIdV1
root, env = Path(sys.argv[1]), Path(sys.argv[4])
def selected():
    try:
        return read_env_location(root) == env
    except FileNotFoundError:
        return True
try:
    maintain_selected_billing_credential(
        DatabaseRefV1(root / 'agentmonitor.db', root),
        OpaqueIdV1(sys.argv[2]), OpaqueIdV1(sys.argv[3]), env,
        action=sys.argv[5], selection_current=selected,
    )
except (ValueError, OSError):
    print('maintenance_incomplete')
    sys.exit(4)
print('maintenance_complete')
"""


def _run(
    root: Path, account: str, resource: str, env: Path, action: str
) -> tuple[int, str]:
    master, slave = pty.openpty()
    try:
        with subprocess.Popen(
            [
                sys.executable,
                "-c",
                _OPERATOR,
                str(root),
                account,
                resource,
                str(env),
                action,
            ],
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")},
            stdin=slave,
            stdout=slave,
            stderr=slave,
        ) as process:
            os.close(slave)
            slave = -1
            try:
                status = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                raise
        output = os.read(master, 8192).decode("utf-8")
        return status, output
    finally:
        os.close(master)
        if slave >= 0:
            os.close(slave)


@pytest.mark.parametrize("provider", ["claude", "codex"])
@pytest.mark.parametrize("archived", [False, True])
def test_disconnect_revokes_before_failed_cleanup_and_retry_only_cleans(
    tmp_path: Path, provider: str, archived: bool
) -> None:
    """M7-LOCAL-MAINT-001: real permission failure never restores old authority."""
    reference = _database(tmp_path)
    account = _account(reference, provider)
    _billing_connection(reference, account)
    billing = SqliteBillingConnectionRepositoryV1(reference)
    status = billing.get(account.account_id)
    assert status is not None
    original = status.connections[0]
    bindings = SqliteCredentialBindingsV1(reference)
    pending = bindings.transition(
        account.account_id, action="prepare", expected_record_version=0
    )
    directory = tmp_path / "credential-file"
    directory.mkdir(mode=0o700)
    env = directory / ".env"
    descriptor = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    update_managed_env(
        env,
        "amcb_" + secrets.token_hex(16),
        None,
        provider_key="claude" if provider == "claude" else "codex",
        staging_root=tmp_path,
    )
    # Real unsafe permissions: the production writer must refuse this file.
    env.chmod(0o644)
    code, output = _run(
        tmp_path,
        account.account_id.value,
        original.resource_id.value,
        env,
        "disconnect",
    )
    assert code == 4 and "maintenance_incomplete" in output, (
        "billing_disconnect_runtime_missing"
    )
    retired = bindings.read(account.account_id)
    assert retired.bindings[0].binding_id == pending.bindings[0].binding_id
    assert retired.bindings[0].lifecycle == "cleanup_pending"
    assert retired.bindings[0].reason_code == "owner_disconnected"
    current = billing.get(account.account_id)
    assert current is not None and current.credential_status is not None
    disconnected = current.connections[0]
    assert disconnected.lifecycle == "disconnected"
    assert disconnected.monitoring_preference == "disabled"
    assert disconnected.scope_generation == original.scope_generation
    assert current.credential_status.cleanup_required
    assert env.stat().st_size == 0
    if archived:
        SqliteRegistryRepositoryV1(reference).edit_account(_archive(account))
    env.chmod(0o600)
    code, output = _run(
        tmp_path, account.account_id.value, original.resource_id.value, env, "cleanup"
    )
    assert code == 0 and "maintenance_complete" in output
    assert account.friendly_name in output
    assert "API key:" not in output
    cleaned = bindings.read(account.account_id)
    assert cleaned.binding_generation == retired.binding_generation
    assert cleaned.bindings[0].lifecycle == "cleanup_complete"
    refreshed = billing.get(account.account_id)
    assert refreshed is not None and refreshed.credential_status is not None
    assert refreshed.connections[0] == disconnected
    assert refreshed.credential_status.state == "missing"
    assert env.stat().st_size == 0
    code, output = _run(
        tmp_path,
        account.account_id.value,
        original.resource_id.value,
        env,
        "disconnect",
    )
    assert code == (4 if archived else 0)
    assert ("maintenance_incomplete" if archived else "maintenance_complete") in output
    assert bindings.read(account.account_id) == cleaned
    again = billing.get(account.account_id)
    assert again is not None and again.connections[0] == disconnected


def test_maintenance_selection_rejects_replaced_database_with_identical_metadata(
    tmp_path: Path,
) -> None:
    """M7-LOCAL-MAINT-002: actual SQLite backup replacement cannot inherit selection."""
    reference = _database(tmp_path)
    account = _account(reference, "claude")
    _billing_connection(reference, account)
    directory = tmp_path / "credential-file"
    directory.mkdir(mode=0o700)
    env = directory / ".env"
    descriptor = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    update_managed_env(
        env,
        "amcb_" + secrets.token_hex(16),
        None,
        provider_key="claude",
        staging_root=tmp_path,
    )
    selected = billing_credential_operator._pin_billing_database(
        reference, lambda: env_location_matches(tmp_path, env)
    )
    assert selected()
    before = SqliteBillingConnectionRepositoryV1(reference).get(account.account_id)
    replacement = tmp_path / "replacement.db"
    with (
        closing(sqlite3.connect(reference._path)) as source,
        closing(sqlite3.connect(replacement)) as target,
    ):
        source.backup(target)
    replacement.chmod(0o600)
    os.replace(replacement, reference._path)
    assert (
        SqliteBillingConnectionRepositoryV1(reference).get(account.account_id) == before
    )
    with pytest.raises(EnrollmentError, match="billing_credential_database_changed"):
        selected()
