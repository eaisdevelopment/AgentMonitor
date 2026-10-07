"""Scheduled Codex polling uses only enrolled managed registry targets."""

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.composition.codex_dashboard_collection import (
    CodexDashboardCollectorV1,
)
from agentmonitor.composition.codex_installation_reconciliation import (
    reconcile_codex_installation_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ConfirmProviderIdentityFingerprintCommandV1,
    PrivateProfileLocatorRefV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    ConfirmProviderIdentityFingerprintV1,
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    EditAccountV1,
    EnrollMonitoringGraphCommandV1,
    EnrollMonitoringGraphV1,
    RegisterAccountV1,
)


def test_codex_poller_does_not_infer_or_read_an_unenrolled_profile(
    tmp_path: Path,
) -> None:
    """M5-CDX-COL-002/003: an empty registry performs no provider operation."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    profiles_root = tmp_path / "profiles" / "codex"
    profiles_root.mkdir(parents=True, mode=0o700)
    profiles_root.chmod(0o700)
    collector = CodexDashboardCollectorV1(
        reference, managed_profiles_root=profiles_root
    )

    assert collector.tick() == "codex_poll_no_enabled_target"
    assert (
        SqliteCollectionRepositoryV1(reference).list_runs(
            "codex", None, datetime.now(UTC), 10
        )
        == ()
    )


def test_codex_poller_paginates_to_enrolled_account_after_first_200(
    tmp_path: Path,
) -> None:
    """NFR-PERF-001/M5-CDX-COL-012: every Codex registry page is considered."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    installation = reconcile_codex_installation_v1(reference)
    repository = SqliteRegistryRepositoryV1(reference)
    register = RegisterAccountV1(repository)
    manifest = get_manifest_fingerprint_v1(build_codex_manifest())
    accounts = tuple(
        register.pending(
            CreatePendingAccountCommandV1(
                OpaqueIdV1(uuid.uuid4().hex),
                OpaqueIdV1("pagination-owner"),
                "codex",
                manifest,
                f"Pagination account {index:03d}",
                None,
                datetime.now(UTC),
            )
        )
        for index in range(201)
    )
    target = max(accounts, key=lambda account: account.account_id.value)
    fingerprint = hashlib.sha256(b"pagination-owner-identity").hexdigest()
    ConfirmProviderIdentityFingerprintV1(repository)(
        ConfirmProviderIdentityFingerprintCommandV1(
            idempotency_key=OpaqueIdV1(uuid.uuid4().hex),
            principal_id=OpaqueIdV1("pagination-owner"),
            account_id=target.account_id,
            expected_account_record_version=target.record_version,
            provider_key="codex",
            identity_scheme="codex.app_server.account.sha256",
            identity_scope="provider_account",
            identity_scheme_version=1,
            subject_fingerprint=fingerprint,
            source_id="codex.app-server.account-read.v2",
            source_version="2",
            parser_version="1.0.0",
            evidence_reference=OpaqueIdV1("pagination-evidence"),
            expected_evidence_digest=fingerprint,
            requested_at=datetime.now(UTC),
            activate_pending_account=True,
        )
    )
    locator = "codex-pagination-managed-profile"
    EnrollMonitoringGraphV1(repository)(
        EnrollMonitoringGraphCommandV1(
            command_id=OpaqueIdV1("pagination-enrollment"),
            principal_id=OpaqueIdV1("pagination-owner"),
            account_id=target.account_id,
            provider_installation_id=installation.provider_installation_id,
            purpose="subscription",
            profile_locator_ref=PrivateProfileLocatorRefV1(locator),
            locator_fingerprint=hashlib.sha256(locator.encode()).hexdigest(),
            management_state="managed",
            compatibility_state="compatible",
            is_protected_default=False,
            resource_kind="subscription_pool",
            parent_resource_id=None,
            requested_at=datetime.now(UTC),
        )
    )
    active = repository.get_account(target.account_id)
    assert active is not None
    EditAccountV1(repository)(
        EditAccountCommandV1(
            account_id=target.account_id,
            expected_version=active.record_version,
            principal_id=OpaqueIdV1("pagination-owner"),
            command_id=OpaqueIdV1("pagination-enable"),
            action="monitoring",
            monitoring_preference="enabled",
            requested_at=datetime.now(UTC),
        )
    )
    profiles_root = tmp_path / "profiles" / "codex"
    collector = CodexDashboardCollectorV1(
        reference, managed_profiles_root=profiles_root
    )

    targets = collector._targets()

    assert len(targets) == 1
    assert targets[0][0].account_id == target.account_id
