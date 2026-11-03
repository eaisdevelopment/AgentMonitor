"""Upgrade a private real 0718 copy without inventing coverage declarations."""

import os
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectActiveSchemaCompatibilityV1,
    InspectSchemaCompatibilityV1,
    application_schema_range,
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
from agentmonitor.contracts.capacity_v1 import CapacityHistoryQueryV1
from agentmonitor.modules.capacity.application.queries import (
    ListCapacityHistoryV1,
    ListQuotaWindowsV1,
)
from agentmonitor.modules.collection_control.application.queries import (
    ListCollectionRunsV1,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)
from agentmonitor.modules.registry.application.organizations import ListOrganizationsV1

from backend.tests.integration.persistence.test_auto_migrate import _run


def _public_snapshot(reference: DatabaseRefV1, now: datetime) -> tuple[object, ...]:
    """Read only published module projections, never another module's tables."""
    registry = SqliteRegistryRepositoryV1(reference)
    accounts = ListAccountsV1(registry).page(None, as_of=now, limit=200)
    organizations = ListOrganizationsV1(registry).page(as_of=now, limit=200)
    if accounts.has_more or organizations.has_more or not accounts.items:
        pytest.fail("coverage_migration_real_registry_selection_incomplete")
    capacity = SqliteCapacityRepositoryV1(reference)
    windows = tuple(
        ListQuotaWindowsV1(capacity)(account.account_id, as_of=now)
        for account in accounts.items
    )
    histories = tuple(
        ListCapacityHistoryV1(capacity)(
            CapacityHistoryQueryV1(
                subject_id=account.account_id,
                resource_id=None,
                window_id=None,
                metric=metric,
                series_kind="poll_snapshot",
                range_start=now - timedelta(days=90),
                range_before=now,
                as_of=now,
                limit=200,
                after_key=None,
                bucket_method=None,
                bucket_seconds=None,
            )
        )
        for account in accounts.items
        for metric in ("remaining", "remaining_ratio")
    )
    runs = ListCollectionRunsV1(SqliteCollectionRepositoryV1(reference))(
        as_of=now, page_size=200
    )
    if not any(windows) or not runs or not any(page.items for page in histories):
        pytest.fail("coverage_migration_real_quota_history_absent")
    return (
        accounts,
        organizations,
        ListProviderInstallationsV1(registry)(),
        windows,
        histories,
        runs,
    )


def test_actual_private_0718_upgrade_preserves_registry_quota_and_history(
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> None:
    """M6-COV-DB-03: migration alone cannot create assertions or change facts."""
    tmp_path.chmod(0o700)
    request.addfinalizer(lambda: shutil.rmtree(tmp_path) if tmp_path.exists() else None)
    target = tmp_path / "agentmonitor.db"
    source = sqlite3.connect(
        "file:/home/dev/.local/share/agentmonitor/agentmonitor.db?mode=ro", uri=True
    )
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    os.chmod(target, 0o600)
    reference = DatabaseRefV1(target, tmp_path)
    view = InspectSchemaCompatibilityV1(
        reference, application_schema_range(), "runtime_read_write"
    )
    assert view.current_revision == "v1_0718"
    assert view.state == "upgrade_required"
    now = datetime.now(UTC)
    before = _public_snapshot(reference, now)
    result = _run(tmp_path, expected="v1_0718")
    if result.returncode:
        pytest.fail("coverage_migration_actual_copy_upgrade_failed")
    after = _public_snapshot(reference, now)
    if before != after:
        pytest.fail("coverage_migration_existing_public_facts_changed")
    # Published readers may leave WAL sidecars. This is an active read-only
    # inspection, not a request for new offline migration authority.
    state, revision = InspectActiveSchemaCompatibilityV1(reference)
    assert revision == "v1_0719"
    assert state == "compatible"
