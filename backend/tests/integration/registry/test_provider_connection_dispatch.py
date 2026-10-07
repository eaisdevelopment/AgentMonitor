"""Provider-neutral dashboard connection dispatch over real SQLite services."""

import uuid
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
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.composition.claude_dashboard_connection import (
    ClaudeDashboardConnectionV1,
)
from agentmonitor.composition.codex_dashboard_connection import (
    CodexDashboardConnectionV1,
)
from agentmonitor.composition.provider_dashboard_connections import (
    ProviderDashboardConnectionsV1,
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
    GetAccountV1,
    RegisterAccountV1,
)


def _pending_account(reference: DatabaseRefV1, provider_key: str) -> AccountViewV1:
    manifest = (
        build_claude_manifest() if provider_key == "claude" else build_codex_manifest()
    )
    return RegisterAccountV1(SqliteRegistryRepositoryV1(reference)).pending(
        CreatePendingAccountCommandV1(
            OpaqueIdV1(uuid.uuid4().hex),
            OpaqueIdV1("owner-provider-dispatch"),
            provider_key,
            get_manifest_fingerprint_v1(manifest),
            f"Owner selected {provider_key}",
            None,
            datetime.now(UTC),
        )
    )


def _dispatcher(
    reference: DatabaseRefV1, data_root: Path
) -> ProviderDashboardConnectionsV1:
    return ProviderDashboardConnectionsV1(
        GetAccountV1(SqliteRegistryRepositoryV1(reference)),
        {
            "claude": ClaudeDashboardConnectionV1(reference, data_root),
            "codex": CodexDashboardConnectionV1(reference, data_root),
        },
    )


def test_connection_reads_dispatch_by_registered_provider_without_provider_io(
    tmp_path: Path,
) -> None:
    """M5-CDX-CONNECT-006: one API port routes exact account ownership."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    claude = _pending_account(reference, "claude")
    codex = _pending_account(reference, "codex")
    dispatcher = _dispatcher(reference, tmp_path)

    claude_view = dispatcher.read(claude.account_id)
    codex_view = dispatcher.read(codex.account_id)

    assert claude_view.account_id == claude.account_id and claude_view.can_connect
    assert codex_view.account_id == codex.account_id and codex_view.can_connect
    assert not (tmp_path / "profiles").exists()
    assert not (tmp_path / "connection-flows").exists()


@pytest.mark.parametrize("provider_key", ["claude", "codex"])
def test_connection_mutations_dispatch_before_provider_side_effects(
    tmp_path: Path, provider_key: str
) -> None:
    """A stale mutation reaches the exact service and fails before login."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    account = _pending_account(reference, provider_key)
    dispatcher = _dispatcher(reference, tmp_path)

    with pytest.raises(ProviderConnectionErrorV1, match="precondition_failed"):
        dispatcher.start(
            StartProviderConnectionCommandV1(
                account.account_id,
                account.record_version + 1,
                "owner@example.invalid",
                OpaqueIdV1("owner-provider-dispatch"),
                OpaqueIdV1(uuid.uuid4().hex),
                OpaqueIdV1(uuid.uuid4().hex),
            )
        )

    assert not (tmp_path / "profiles").exists()
    assert not (tmp_path / "connection-flows").exists()


def test_connection_dispatch_rejects_unknown_registry_subject(tmp_path: Path) -> None:
    """Missing account IDs cannot be routed to any provider process."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    dispatcher = _dispatcher(reference, tmp_path)

    with pytest.raises(ProviderConnectionErrorV1, match="registry_subject_not_found"):
        dispatcher.read(OpaqueIdV1("missing-account"))

    assert not (tmp_path / "profiles").exists()
    assert not (tmp_path / "connection-flows").exists()
