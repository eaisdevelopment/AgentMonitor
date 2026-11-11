"""Actual empty custody and concrete sinks; no keys, HTTP or substitute grants."""

import http.client
import os
from contextlib import ExitStack
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.providers.claude.anthropic_api.source import (
    AnthropicCostAuthorizationSinkV1,
)
from agentmonitor.adapters.providers.codex.openai_api.source import (
    OpenAICostAuthorizationSinkV1,
)
from agentmonitor.adapters.providers.ollama.api.source import (
    OllamaUsageAuthorizationSinkV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    approve_env_credential_file_v1,
    env_credential_file_lease_v1,
)
from agentmonitor.composition import billing_env_authorization as grants

from backend.tests.registry.test_billing_env_authorization import _empty_pending_store


@pytest.mark.parametrize("provider", ["codex", "ollama"])
@pytest.mark.parametrize(
    "boundary",
    [
        "empty",
        "replaced_file",
        "replaced_lock",
        "expired_file",
        "expired_lock",
        "wrong_sink",
    ],
)
def test_provider_grant_refuses_actual_custody_failure_without_header(
    tmp_path: Path, provider: str, boundary: str
) -> None:
    reference, account_id, binding_id, selected = _empty_pending_store(
        tmp_path, provider
    )
    before = SqliteCredentialBindingsV1(reference).read(account_id)
    authority = approve_env_credential_file_v1(selected)
    connection = http.client.HTTPSConnection(
        "api.openai.com" if provider == "codex" else "ollama.com", timeout=1
    )
    sink_type = (
        OpenAICostAuthorizationSinkV1
        if provider == "codex"
        else OllamaUsageAuthorizationSinkV1
    )
    sink = (
        AnthropicCostAuthorizationSinkV1(connection)
        if boundary == "wrong_sink"
        else sink_type(connection)
    )
    error_type = getattr(
        grants,
        "OpenAIEnvAuthorizationUnavailable"
        if provider == "codex"
        else "OllamaUsageEnvAuthorizationUnavailable",
    )
    grant_type = getattr(
        grants,
        "OpenAIEnvAuthorizationV1"
        if provider == "codex"
        else "OllamaUsageEnvAuthorizationV1",
    )
    reason = (
        "openai_cost_authorization_unavailable"
        if provider == "codex"
        else "ollama_usage_authorization_unavailable"
    )
    try:
        with ExitStack() as account_scope, ExitStack() as file_scope:
            account_lease = account_scope.enter_context(
                account_credential_lock(reference, account_id)
            )
            file_lease = file_scope.enter_context(
                env_credential_file_lease_v1(authority)
            )
            inherited_lock = account_lease.inherited_lock(account_id)
            grant = grant_type(
                binding_id, account_id, inherited_lock, file_lease.inherited_file()
            )
            if boundary in {"replaced_file", "replaced_lock"}:
                target = (
                    selected
                    if boundary == "replaced_file"
                    else tmp_path / inherited_lock.lock_name(account_id)
                )
                target.rename(target.with_name("displaced-empty-entry"))
                descriptor = os.open(
                    target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                os.close(descriptor)
            elif boundary == "expired_file":
                file_scope.close()
            elif boundary == "expired_lock":
                account_scope.close()
            with pytest.raises(error_type) as failed:
                grant.authorize(sink)
            assert str(failed.value) == reason
            assert connection.sock is None
            assert connection.__dict__.get("_buffer") == []
            with pytest.raises(ValueError, match="authorization_missing"):
                sink.finish()
    finally:
        sink.cancel()
        connection.close()
    assert selected.stat().st_size == 0
    assert SqliteCredentialBindingsV1(reference).read(account_id) == before
