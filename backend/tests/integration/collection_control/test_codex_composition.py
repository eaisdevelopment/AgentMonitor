"""M5 Codex collection composition over real SQLite and the installed CLI."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.providers.codex.adapter import CodexAdapterV1
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.codex.manifest import (
    CODEX_ADAPTER_VERSION,
    CODEX_RATE_LIMITS_SOURCE_ID,
    build_codex_manifest,
)
from agentmonitor.composition.codex_dashboard_collection import _scheduled_admission
from agentmonitor.composition.providers import compose_codex_quota_collection
from agentmonitor.contracts.collection_control_v1 import (
    CollectionFailedV1,
    CollectionRunAdmissionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    MaskedRegistryFieldV1,
    MonitoringProfileViewV1,
)
from agentmonitor.modules.capacity.application.commit import (
    CommitCapacityCollectionOutcomeV1,
)
from agentmonitor.modules.capacity.application.queries import (
    GetCollectionCommitStatusV1,
    ListQuotaWindowsV1,
)
from agentmonitor.modules.collection_control.application.runner import (
    RunOneCollectionV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)


def _digest(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()


def _admission(
    installation_id: OpaqueIdV1, *, provider_version: str, requested_at: datetime
) -> CollectionRunAdmissionV1:
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1("codex-composition-run-one"),
        schedule_id=OpaqueIdV1("codex-composition-schedule-one"),
        request_id=OpaqueIdV1("codex-composition-request-one"),
        trigger="scheduled",
        operation_family="collect.subscription.quota",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="internal_scheduler",
        request_principal_id=None,
        correlation_id=OpaqueIdV1("codex-composition-correlation-one"),
        causation_id=None,
        target_key_digest=_digest("codex-target"),
        provider_key="codex",
        installation_id=installation_id,
        account_id=OpaqueIdV1("codex-account-one"),
        profile_id=OpaqueIdV1("codex-profile-one"),
        resource_id=OpaqueIdV1("codex-resource-one"),
        capability_id="subscription.quota",
        source_id=CODEX_RATE_LIMITS_SOURCE_ID,
        adapter_version=CODEX_ADAPTER_VERSION,
        provider_version=provider_version,
        adapter_protocol_version="1.0.0",
        manifest_fingerprint=_digest(
            get_manifest_fingerprint_v1(build_codex_manifest())
        ),
        collection_policy_version="1.0.0",
        registry_revision=1,
        retry_chain_id=OpaqueIdV1("codex-composition-retry-chain-one"),
        attempt_ordinal=1,
        target_generation=1,
        scheduler_instance_id=OpaqueIdV1("codex-composition-scheduler-one"),
        lease_policy_version="1.0.0",
        budget_policy_id="codex-source-minimum-interval-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest=_digest("codex-budget"),
        budget_dimension="provider_requests",
        budget_unit="request",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=requested_at,
        budget_window_end=requested_at + timedelta(minutes=5),
        payload_schema="ProviderQuotaInputV1@1",
        idempotency_key_digest=None,
        request_digest=_digest("codex-request"),
        requested_at=requested_at,
        deadline_at=requested_at + timedelta(seconds=45),
    )


def _private_managed_root(tmp_path: Path) -> Path:
    profiles = tmp_path / "profiles"
    provider = profiles / "codex"
    root = provider / _digest("codex-account-one")
    for directory in (profiles, provider, root):
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
    return root


def test_scheduled_admission_reserves_every_possible_app_server_request() -> None:
    """M5-CDX-COL-004: one admitted run reserves its three bounded CLI reads."""
    requested_at = datetime.now(UTC)
    account_id = OpaqueIdV1("codex-account-one")
    profile_id = OpaqueIdV1("codex-profile-one")
    resource_id = OpaqueIdV1("codex-resource-one")
    installation = discover_default_installation()
    masked = MaskedRegistryFieldV1("withheld", None, "privacy_minimized")
    account = AccountViewV1(
        account_id=account_id,
        provider_key="codex",
        friendly_name="Codex owner account",
        organization_id=None,
        lifecycle="active",
        monitoring_preference="enabled",
        is_effective_monitoring_enabled=True,
        effective_monitoring_reason="eligible",
        identity_state="owner_confirmed",
        masked_identity=masked,
        record_version=1,
        registry_revision=3,
        created_at=requested_at,
        updated_at=requested_at,
        archived_at=None,
    )
    profile = MonitoringProfileViewV1(
        profile_id=profile_id,
        account_id=account_id,
        provider_installation_id=installation.installation_ref,
        purpose="subscription",
        lifecycle="active",
        management_state="managed",
        compatibility_state="compatible",
        is_protected_default=False,
        locator_state="configured",
        identity_state="provider_verified",
        last_verified_at=requested_at,
        resource_ids=(resource_id,),
        record_version=1,
        registry_revision=4,
    )
    resource = AccountResourceViewV1(
        resource_id=resource_id,
        account_id=account_id,
        kind="subscription_pool",
        parent_resource_id=None,
        label=masked,
        lifecycle="active",
        linked_profile_ids=(profile_id,),
        record_version=1,
        registry_revision=5,
        created_at=requested_at,
        updated_at=requested_at,
    )

    admission = _scheduled_admission(
        account=account,
        profile=profile,
        resource=resource,
        installation=installation,
        scheduler_instance=OpaqueIdV1("codex-scheduler-one"),
        schedule_id=OpaqueIdV1("codex-schedule-one"),
        requested_at=requested_at,
    )

    assert admission.budget_dimension == "provider_requests"
    assert admission.budget_unit == "request"
    assert admission.budget_units == 3
    assert admission.budget_limit_units == 3
    assert admission.budget_policy_id == "codex-scheduled-collection-budget-v1"


def test_codex_route_exposes_existing_capacity_sink_and_queries(tmp_path: Path) -> None:
    """M5-CDX-COL-001/CAP-001: Codex reuses the provider-neutral M04/M05 route."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    installation = discover_default_installation()
    managed_root = _private_managed_root(tmp_path)
    route = compose_codex_quota_collection(
        reference,
        installation,
        managed_profiles_root=managed_root.parent,
        managed_profile_root=managed_root,
        expected_identity_fingerprint="a" * 64,
        installation_ref=installation.installation_ref,
        account_ref=OpaqueIdV1("codex-account-one"),
        profile_ref=OpaqueIdV1("codex-profile-one"),
        resource_ref=OpaqueIdV1("codex-resource-one"),
        access_grant_ref=OpaqueIdV1("codex-managed-profile-auth-maintenance"),
    )

    assert isinstance(route.adapter, CodexAdapterV1)
    assert isinstance(route.run_one, RunOneCollectionV1)
    assert isinstance(route.capacity_commit, CommitCapacityCollectionOutcomeV1)
    assert isinstance(route.get_commit_status, GetCollectionCommitStatusV1)
    assert isinstance(route.list_quota_windows, ListQuotaWindowsV1)
    assert (
        route.get_commit_status(
            OpaqueIdV1("codex-run-not-started"), "subscription.quota"
        ).state
        == "not_committed"
    )
    assert (
        route.list_quota_windows(
            OpaqueIdV1("codex-account-one"), as_of=datetime.now(UTC)
        )
        == ()
    )


def test_codex_route_persists_real_managed_profile_auth_failure_once(
    tmp_path: Path,
) -> None:
    """M5-CDX-COL-004/007: admission precedes one real, failed-closed CLI read."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    installation = discover_default_installation()
    managed_root = _private_managed_root(tmp_path)
    route = compose_codex_quota_collection(
        reference,
        installation,
        managed_profiles_root=managed_root.parent,
        managed_profile_root=managed_root,
        expected_identity_fingerprint="a" * 64,
        installation_ref=installation.installation_ref,
        account_ref=OpaqueIdV1("codex-account-one"),
        profile_ref=OpaqueIdV1("codex-profile-one"),
        resource_ref=OpaqueIdV1("codex-resource-one"),
        access_grant_ref=OpaqueIdV1("codex-managed-profile-auth-maintenance"),
    )
    requested_at = datetime.now(UTC)
    admission = _admission(
        installation.installation_ref,
        provider_version=installation.provider_version,
        requested_at=requested_at,
    )
    assert admission.account_id is not None
    assert admission.profile_id is not None
    assert admission.resource_id is not None
    request = route.adapter.subscription_request(
        operation_id=admission.run_id.value,
        correlation_id=admission.correlation_id.value,
        requested_at=requested_at,
    )

    result = route.collect_once(
        admission,
        request,
        started_at=datetime.now(UTC),
        completed_at=lambda: datetime.now(UTC),
    )

    assert isinstance(result, CollectionFailedV1)
    assert result.terminal_state == "blocked"
    assert result.error_code == "codex_managed_authentication_required"
    assert (
        route.adapter.take_verified_identity(
            operation_id=admission.run_id,
            correlation_id=admission.correlation_id,
        )
        is None
    )
    persisted = SqliteCollectionRepositoryV1(reference).get_run(admission.run_id)
    assert persisted.state == "blocked"
    assert persisted.fencing_token == 1
    assert persisted.target_generation == admission.target_generation
    assert persisted.observation_ids == ()
    runs = SqliteCollectionRepositoryV1(reference).list_runs(
        "codex", admission.account_id, datetime.now(UTC), 10
    )
    assert tuple(run.run_id for run in runs) == (admission.run_id,)
    assert route.list_quota_windows(admission.account_id, as_of=datetime.now(UTC)) == ()
