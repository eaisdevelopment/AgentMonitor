"""Production Claude quota composition over an empty real SQLite database."""

import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.providers.claude.adapter import ClaudeAdapterV1
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.contracts.collection_control_v1 import CollectionRunAdmissionV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
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

NOW = datetime(2026, 9, 22, 14, 0, tzinfo=UTC)


def _admission() -> CollectionRunAdmissionV1:
    return CollectionRunAdmissionV1(
        run_id=OpaqueIdV1("composition-run-one"),
        schedule_id=OpaqueIdV1("composition-schedule-one"),
        request_id=OpaqueIdV1("composition-request-one"),
        trigger="manual",
        operation_family="collect.subscription.quota",
        requested_capability_ids=("subscription.quota",),
        capability_set_version="1.0.0",
        request_auth_method="owner_session",
        request_principal_id=OpaqueIdV1("owner-one"),
        correlation_id=OpaqueIdV1("correlation-one"),
        causation_id=None,
        target_key_digest="b" * 64,
        provider_key="claude",
        installation_id=OpaqueIdV1("claude-installation-default"),
        account_id=OpaqueIdV1("account-one"),
        profile_id=OpaqueIdV1("profile-one"),
        resource_id=OpaqueIdV1("resource-one"),
        capability_id="subscription.quota",
        source_id="claude.subscription.usage.screen_reader",
        adapter_version="1.0.0",
        provider_version="2.1.278",
        adapter_protocol_version="1.0.0",
        manifest_fingerprint="e" * 64,
        collection_policy_version="1.0.0",
        registry_revision=1,
        retry_chain_id=OpaqueIdV1("retry-chain-one"),
        attempt_ordinal=1,
        target_generation=1,
        scheduler_instance_id=OpaqueIdV1("scheduler-instance-one"),
        lease_policy_version="1.0.0",
        budget_policy_id="provider-request-budget-v1",
        budget_policy_version="1.0.0",
        budget_scope_digest="d" * 64,
        budget_dimension="provider_requests",
        budget_unit="request",
        budget_units=1,
        budget_limit_units=1,
        budget_window_start=NOW,
        budget_window_end=NOW + timedelta(minutes=1),
        payload_schema="ProviderQuotaInputV1@1",
        idempotency_key_digest="f" * 64,
        request_digest="a" * 64,
        requested_at=NOW,
        deadline_at=NOW + timedelta(seconds=30),
    )


def test_production_claude_route_exposes_one_sink_recovery_and_queries(
    tmp_path: Path,
) -> None:
    """ST-OBS-001: composition is usable before provider I/O or telemetry."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    installation = discover_default_installation()

    providers = importlib.import_module("agentmonitor.composition.providers")
    route = providers.compose_claude_quota_collection(reference, installation)

    assert isinstance(route.adapter, ClaudeAdapterV1)
    assert isinstance(route.run_one, RunOneCollectionV1)
    assert isinstance(route.capacity_commit, CommitCapacityCollectionOutcomeV1)
    assert isinstance(route.get_commit_status, GetCollectionCommitStatusV1)
    assert isinstance(route.list_quota_windows, ListQuotaWindowsV1)
    status = route.get_commit_status(
        OpaqueIdV1("collection-run-not-started"), "subscription.quota"
    )
    assert status.state == "not_committed"
    assert status.receipt is None
    assert (
        route.list_quota_windows.for_scope(
            OpaqueIdV1("account-with-no-observation"),
            OpaqueIdV1("resource-with-no-observation"),
            "subscription.quota",
            as_of=datetime(2026, 9, 22, tzinfo=UTC),
        )
        == ()
    )


def test_production_route_recovers_absent_commit_without_provider_invocation(
    tmp_path: Path,
) -> None:
    """M04-DB-019: recovery closes a definite no-receipt commit interruption."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    installation = discover_default_installation()
    providers = importlib.import_module("agentmonitor.composition.providers")
    route = providers.compose_claude_quota_collection(reference, installation)
    repository = SqliteCollectionRepositoryV1(reference)
    admission = _admission()
    run = repository.admit_run(admission)
    repository.mark_running(run.run_id, NOW, fencing_token=run.fencing_token)
    repository.mark_committing(
        run.run_id,
        fencing_token=run.fencing_token,
        payload_digest="9" * 64,
        committing_at=NOW,
        terminal_state="succeeded",
    )

    result = route.recover_commit(admission, completed_at=NOW)

    assert result.terminal_state == "failed"
    assert result.error_code == "collection_commit_interrupted"
    assert repository.get_run(run.run_id).state == "failed"
