"""Real managed Codex quota lineage through scheduled collection and capacity."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.codex.manifest import CODEX_RATE_LIMITS_SOURCE_ID
from agentmonitor.composition.providers import compose_codex_quota_collection
from agentmonitor.contracts.capacity_v1 import (
    CapacityHistoryPointV1,
    CapacityHistoryQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.queries import (
    ListCapacityHistoryV1,
    ListQuotaWindowsV1,
)


def _selected_real_target() -> tuple[Path, OpaqueIdV1]:
    root_value = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    account_value = os.environ.get("AGENTMONITOR_TEST_CODEX_ACCOUNT_ID")
    if root_value is None or account_value is None:
        pytest.skip("NOT RUN: explicit owner data root and Codex account required")
    root = Path(root_value)
    if not root.is_absolute():
        pytest.fail("AGENTMONITOR_TEST_OWNER_DATA_ROOT must be absolute")
    return root, OpaqueIdV1(account_value)


def test_codex_capacity_queries_never_invent_unobserved_windows(tmp_path: Path) -> None:
    """M5-CDX-CAP-001: real SQLite remains empty before a genuine quota read."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    profiles = tmp_path / "profiles"
    provider = profiles / "codex"
    managed_root = provider / ("a" * 64)
    for directory in (profiles, provider, managed_root):
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
    route = compose_codex_quota_collection(
        reference,
        discover_default_installation(),
        managed_profiles_root=managed_root.parent,
        managed_profile_root=managed_root,
        expected_identity_fingerprint="a" * 64,
        installation_ref=OpaqueIdV1("codex-installation-primary"),
        account_ref=OpaqueIdV1("codex-account-without-observation"),
        profile_ref=OpaqueIdV1("codex-profile-without-observation"),
        resource_ref=OpaqueIdV1("codex-resource-without-observation"),
        access_grant_ref=OpaqueIdV1("codex-managed-profile-auth-maintenance"),
    )
    account_id = OpaqueIdV1("codex-account-without-observation")
    as_of = datetime.now(UTC)

    assert route.list_quota_windows(account_id, as_of=as_of) == ()
    history = ListCapacityHistoryV1(SqliteCapacityRepositoryV1(reference))(
        CapacityHistoryQueryV1(
            subject_id=account_id,
            resource_id=None,
            window_id=None,
            metric="remaining_ratio",
            series_kind="poll_snapshot",
            range_start=as_of - timedelta(days=1),
            range_before=as_of,
            as_of=as_of,
            limit=10,
            after_key=None,
            bucket_method=None,
            bucket_seconds=None,
        )
    )
    assert history.items == ()
    assert history.availability.state == "unavailable"


def test_running_service_persisted_native_codex_windows_and_history() -> None:
    """M5-CDX-COL-005/CAP-002..008: service-owned quota has durable lineage."""
    root, account_id = _selected_real_target()
    started_value = os.environ.get("AGENTMONITOR_M5_SERVICE_STARTED_AT")
    if started_value is None:
        pytest.fail("BLOCKED: selected M5 service start time required")
    service_started_at = datetime.fromisoformat(started_value)
    assert service_started_at.utcoffset() == timedelta(0)
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    registry = SqliteRegistryRepositoryV1(reference)
    account = registry.get_account(account_id)
    assert account is not None and account.provider_key == "codex"
    profiles = registry.list_monitoring_profiles(account_id)
    assert len(profiles) == 1
    assert profiles[0].management_state == "managed"
    assert profiles[0].compatibility_state == "compatible"
    assert profiles[0].identity_state in {"owner_confirmed", "provider_verified"}
    runs = SqliteCollectionRepositoryV1(reference).list_runs(
        "codex", account_id, datetime.now(UTC), 100
    )
    matching = tuple(
        run
        for run in runs
        if run.capability_id == "subscription.quota"
        and run.source_id == CODEX_RATE_LIMITS_SOURCE_ID
        and run.requested_at >= service_started_at
        and run.state in {"succeeded", "partial"}
    )
    assert matching, "no post-restart service-owned Codex quota lineage"
    run = matching[0]
    assert run.provider_version == "0.160.0"
    assert run.adapter_version == "1.0.2"
    assert run.observation_ids
    windows = ListQuotaWindowsV1(SqliteCapacityRepositoryV1(reference))(
        account_id, as_of=datetime.now(UTC)
    )
    assert windows
    assert {window.collection_run_id for window in windows} == {run.run_id}
    assert {window.current_observation_id for window in windows} == set(
        run.observation_ids
    )
    assert all(window.subject.provider_key == "codex" for window in windows)
    assert all(window.semantic_role in {"primary", "secondary"} for window in windows)
    assert all(":" in window.window_key for window in windows)
    assert len({window.window_key for window in windows}) == len(windows)
    assert all(
        window.provenance.source_id == CODEX_RATE_LIMITS_SOURCE_ID
        and window.provenance.is_experimental
        for window in windows
    )

    resource_ids = {window.subject.resource_id for window in windows}
    assert None not in resource_ids and len(resource_ids) == 1
    resource_kinds = {
        resource.resource_id: resource.kind
        for resource in registry.list_account_resources(account_id)
    }
    assert {resource_kinds.get(resource_id) for resource_id in resource_ids} == {
        "subscription_pool"
    }
    as_of = datetime.now(UTC)
    history_query = CapacityHistoryQueryV1(
        subject_id=account_id,
        resource_id=None,
        window_id=None,
        metric="remaining_ratio",
        series_kind="poll_snapshot",
        range_start=as_of - timedelta(days=30),
        range_before=as_of + timedelta(seconds=1),
        as_of=as_of,
        limit=200,
        after_key=None,
        bucket_method=None,
        bucket_seconds=None,
    )
    list_history = ListCapacityHistoryV1(SqliteCapacityRepositoryV1(reference))
    history_points: list[CapacityHistoryPointV1] = []
    seen_cursors: set[str] = set()
    next_key = None
    for _ in range(128):
        history = list_history(history_query.with_cursor(next_key))
        for point in history.items:
            assert isinstance(point, CapacityHistoryPointV1)
            history_points.append(point)
        if not history.has_more:
            assert history.next_key is None
            break
        assert history.next_key is not None
        assert history.next_key not in seen_cursors
        seen_cursors.add(history.next_key)
        next_key = history.next_key
    else:
        pytest.fail("capacity history exceeded the bounded cursor traversal")

    assert history_points
    assert tuple(
        (point.observed_at, point.observation_id.value) for point in history_points
    ) == tuple(
        sorted(
            (point.observed_at, point.observation_id.value) for point in history_points
        )
    )
    assert len({point.observation_id for point in history_points}) == len(
        history_points
    )
    current_lineage = tuple(
        point for point in history_points if point.collection_run_id == run.run_id
    )
    assert current_lineage
    assert {point.window_id for point in current_lineage} == {
        window.window_id for window in windows
    }
    assert any(point.collection_run_id != run.run_id for point in history_points)
