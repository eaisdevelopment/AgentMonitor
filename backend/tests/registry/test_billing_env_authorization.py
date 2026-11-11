"""Real empty-file authorization boundaries; no key, active grant or network."""

import http.client
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

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
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.anthropic_api.policy import HOST
from agentmonitor.adapters.providers.claude.anthropic_api.source import (
    AnthropicCostAuthorizationSinkV1,
    AnthropicCostAuthorizationV1,
)
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    approve_env_credential_file_v1,
    env_credential_file_lease_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CloudBalanceAuthorizationSinkV1,
)
from agentmonitor.composition.billing_env_authorization import (
    AnthropicEnvAuthorizationUnavailable,
    AnthropicEnvAuthorizationV1,
)
from agentmonitor.composition.ollama_env_store import update_managed_env
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import CreateBillingConnectionCommandV1
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    RegisterAccountV1,
)


def _empty_pending_store(tmp_path: Path) -> tuple[DatabaseRefV1, OpaqueIdV1, str, Path]:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    account = RegisterAccountV1(SqliteRegistryRepositoryV1(reference)).pending(
        CreatePendingAccountCommandV1(
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            principal_id=OpaqueIdV1("isolated-authorization-owner"),
            provider_key="claude",
            manifest_reference=get_manifest_fingerprint_v1(build_claude_manifest()),
            friendly_name="Empty authorization " + secrets.token_urlsafe(8),
            organization_id=None,
            requested_at=datetime.now(UTC),
        )
    )
    SqliteBillingConnectionRepositoryV1(reference).create(
        CreateBillingConnectionCommandV1(
            account_id=account.account_id,
            expected_account_version=account.record_version,
            principal_id=OpaqueIdV1("isolated-authorization-owner"),
            command_id=OpaqueIdV1(secrets.token_urlsafe(24)),
            scope_id=None,
            requested_at=datetime.now(UTC),
        )
    )
    prepared = SqliteCredentialBindingsV1(reference).transition(
        account.account_id, action="prepare", expected_record_version=0
    )
    assert prepared.binding_generation == 0
    assert prepared.bindings[0].lifecycle == "pending"
    binding_id = prepared.bindings[0].binding_id.value
    parent = tmp_path / "owner-private"
    parent.mkdir(mode=0o700)
    selected = parent / ".env"
    descriptor = os.open(selected, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    update_managed_env(
        selected, binding_id, None, provider_key="claude", staging_root=tmp_path
    )
    return reference, account.account_id, binding_id, selected


def _assert_denied_without_header(
    authorization: AnthropicCostAuthorizationV1,
    connection: http.client.HTTPSConnection,
    sink: AnthropicCostAuthorizationSinkV1,
) -> None:
    with pytest.raises(AnthropicEnvAuthorizationUnavailable) as failed:
        authorization.authorize(sink)
    assert str(failed.value) == "anthropic_cost_authorization_unavailable"
    assert connection.sock is None
    assert connection.__dict__.get("_buffer") == []
    with pytest.raises(ValueError, match="anthropic_cost_authorization_missing"):
        sink.finish()


def test_real_empty_file_denies_before_header_or_network(tmp_path: Path) -> None:
    """M7-AUTH-001: persisted pending ID is not an active-access assertion."""
    reference, account_id, binding_id, selected = _empty_pending_store(tmp_path)
    before = SqliteCredentialBindingsV1(reference).read(account_id)
    authority = approve_env_credential_file_v1(selected)
    connection = http.client.HTTPSConnection(HOST, timeout=1)
    sink = AnthropicCostAuthorizationSinkV1(connection)
    try:
        with account_credential_lock(reference, account_id) as account_lease:
            with env_credential_file_lease_v1(authority) as file_lease:
                authorization = AnthropicEnvAuthorizationV1(
                    binding_id,
                    account_id,
                    account_lease.inherited_lock(account_id),
                    file_lease.inherited_file(),
                )
                _assert_denied_without_header(authorization, connection, sink)
    finally:
        sink.cancel()
        connection.close()
    assert selected.stat().st_size == 0
    assert SqliteCredentialBindingsV1(reference).read(account_id) == before


@pytest.mark.parametrize("replaced", ["file", "account_lock"])
def test_real_replaced_entry_is_rejected_before_authorization(
    tmp_path: Path, replaced: str
) -> None:
    """M7-AUTH-002: actual pinned file/lock replacement invalidates the reader."""
    reference, account_id, binding_id, selected = _empty_pending_store(tmp_path)
    authority = approve_env_credential_file_v1(selected)
    connection = http.client.HTTPSConnection(HOST, timeout=1)
    sink = AnthropicCostAuthorizationSinkV1(connection)
    try:
        with account_credential_lock(reference, account_id) as account_lease:
            with env_credential_file_lease_v1(authority) as file_lease:
                inherited_lock = account_lease.inherited_lock(account_id)
                authorization = AnthropicEnvAuthorizationV1(
                    binding_id,
                    account_id,
                    inherited_lock,
                    file_lease.inherited_file(),
                )
                target = (
                    selected
                    if replaced == "file"
                    else tmp_path / inherited_lock.lock_name(account_id)
                )
                target.rename(target.with_name("displaced-empty-entry"))
                descriptor = os.open(
                    target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                os.close(descriptor)
                _assert_denied_without_header(authorization, connection, sink)
    finally:
        sink.cancel()
        connection.close()


@pytest.mark.parametrize("expired", ["file", "account_lock"])
def test_expired_actual_lease_is_rejected(tmp_path: Path, expired: str) -> None:
    """M7-AUTH-003: exiting the real lease scope revokes the inherited capability."""
    reference, account_id, binding_id, selected = _empty_pending_store(tmp_path)
    authority = approve_env_credential_file_v1(selected)
    connection = http.client.HTTPSConnection(HOST, timeout=1)
    sink = AnthropicCostAuthorizationSinkV1(connection)
    try:
        if expired == "file":
            with account_credential_lock(reference, account_id) as account_lease:
                with env_credential_file_lease_v1(authority) as file_lease:
                    authorization = AnthropicEnvAuthorizationV1(
                        binding_id,
                        account_id,
                        account_lease.inherited_lock(account_id),
                        file_lease.inherited_file(),
                    )
                _assert_denied_without_header(authorization, connection, sink)
        else:
            with env_credential_file_lease_v1(authority) as file_lease:
                with account_credential_lock(reference, account_id) as account_lease:
                    authorization = AnthropicEnvAuthorizationV1(
                        binding_id,
                        account_id,
                        account_lease.inherited_lock(account_id),
                        file_lease.inherited_file(),
                    )
                _assert_denied_without_header(authorization, connection, sink)
    finally:
        sink.cancel()
        connection.close()


def test_actual_other_provider_sink_is_rejected(tmp_path: Path) -> None:
    """M7-AUTH-004: a real bearer sink is not the A01 x-api-key capability."""
    reference, account_id, binding_id, selected = _empty_pending_store(tmp_path)
    authority = approve_env_credential_file_v1(selected)
    connection = http.client.HTTPSConnection(HOST, timeout=1)
    other_sink = CloudBalanceAuthorizationSinkV1(connection)
    try:
        with account_credential_lock(reference, account_id) as account_lease:
            with env_credential_file_lease_v1(authority) as file_lease:
                authorization = AnthropicEnvAuthorizationV1(
                    binding_id,
                    account_id,
                    account_lease.inherited_lock(account_id),
                    file_lease.inherited_file(),
                )
                with pytest.raises(AnthropicEnvAuthorizationUnavailable):
                    authorization.authorize(
                        cast(AnthropicCostAuthorizationSinkV1, other_sink)
                    )
                assert connection.sock is None
                assert connection.__dict__.get("_buffer") == []
    finally:
        other_sink._cancel_v1()
        connection.close()
