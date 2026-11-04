"""M6-COV real private-copy SQLite evidence; never invent provider outcomes."""

import os
import secrets
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
)
from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
    SqliteOrganizationProviderCoverageRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_coverage_v1 import (
    OrganizationProviderCoverageSelectionV1,
    OrganizationProviderCoverageV1,
    RevokeOrganizationProviderCoverageCommandV1,
    SetOrganizationProviderCoverageCommandV1,
)
from agentmonitor.contracts.registry_v1 import AccountViewV1, CloudMonitoringTargetV1
from agentmonitor.modules.registry.application.accounts import EditAccountCommandV1
from agentmonitor.modules.registry.application.organizations import (
    EditOrganizationCommandV1,
    RegistryCommandConflictV1,
)

ActualCoverageRegistry = tuple[
    DatabaseRefV1, SqliteRegistryRepositoryV1, AccountViewV1, CloudMonitoringTargetV1
]

ROOT = Path(__file__).resolve().parents[4]
LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


def _id() -> OpaqueIdV1:
    return OpaqueIdV1(secrets.token_urlsafe(24))


@pytest.fixture(scope="module")
def coverage_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The published SQLite backup API copies real state without table inspection."""
    tmp_path = tmp_path_factory.mktemp("coverage-source")
    tmp_path.chmod(0o700)
    copied = tmp_path / "agentmonitor.db"
    with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
        with sqlite3.connect(copied) as target:
            source.backup(target)
    copied.chmod(0o600)
    state = InspectSchemaCompatibilityV1(
        DatabaseRefV1(copied, tmp_path),
        application_schema_range(),
        "runtime_read_write",
    )
    if state.current_revision == "v1_0719":
        assert state.state == "compatible", "actual_private_copy_schema_incompatible"
        return copied
    assert state.current_revision == "v1_0718", "actual_private_copy_source_unsupported"
    environment = os.environ.copy()
    environment["AGENTMONITOR_MIGRATE_DATA_ROOT"] = str(tmp_path)
    environment["AGENTMONITOR_MIGRATE_EXPECTED_HEAD"] = "v1_0718"
    migrated = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; import sys; "
            "from tools.automation.implementations.auto_migrate import run_upgrade; "
            "run_upgrade(Path(sys.argv[1]), 'v1_0718')",
            str(tmp_path),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert migrated.returncode == 0, "actual_private_copy_migration_failed"
    return copied


def _select_eligible_coverage_account(candidates: tuple[tuple[str, bool], ...]) -> str:
    """Select an actual account from prevalidated declaration eligibility."""
    ids = [account_id for account_id, _ in candidates]
    assert len(ids) == len(set(ids)), "actual_coverage_account_selection_duplicate"
    selected = sorted(account_id for account_id, eligible in candidates if eligible)
    assert selected, "actual_eligible_coverage_account_unavailable"
    return selected[0]


@pytest.fixture
def actual_registry(tmp_path: Path, coverage_source: Path) -> ActualCoverageRegistry:
    tmp_path.chmod(0o700)
    copied = tmp_path / "agentmonitor.db"
    with sqlite3.connect(f"file:{coverage_source}?mode=ro", uri=True) as source:
        with sqlite3.connect(copied) as target:
            source.backup(target)
    copied.chmod(0o600)
    reference = DatabaseRefV1(copied, tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    selected = []
    coverage = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    accounts = registry.list_accounts(provider_key="ollama", page_size=100)
    assert len(accounts) < 100, "actual_account_selection_incomplete"
    for account in accounts:
        graph = cloud.read_monitoring_target(account.account_id)
        if (
            graph is not None
            and graph.identity_state == "owner_confirmed"
            and account.organization_id
            and account.lifecycle == "active"
        ):
            organization = registry.get_organization(account.organization_id)
            if organization is None or organization.lifecycle != "active":
                continue
            snapshot = coverage.read_coverage(
                OrganizationProviderCoverageSelectionV1(
                    (account.organization_id,), account.provider_key
                )
            )
            assert snapshot.completeness == "complete", "coverage_baseline_unavailable"
            eligible = not snapshot.items or _coverage_matches_account(
                snapshot.items[0], account
            )
            selected.append((account, graph, eligible))
    selected_id = _select_eligible_coverage_account(
        tuple((account.account_id.value, eligible) for account, _, eligible in selected)
    )
    account, graph, _ = next(
        item for item in selected if item[0].account_id.value == selected_id
    )
    assert account.organization_id is not None
    return reference, registry, account, graph


def _command(
    account: AccountViewV1, graph: CloudMonitoringTargetV1, version: int = 0
) -> SetOrganizationProviderCoverageCommandV1:
    assert account.organization_id is not None
    return SetOrganizationProviderCoverageCommandV1(
        organization_id=account.organization_id,
        provider_key=account.provider_key,
        outcome="account",
        account_id=account.account_id,
        expected_account_record_version=account.record_version,
        unavailable_reason=None,
        expected_version=version,
        command_id=_id(),
        principal_id=graph.owner_principal_id,
        requested_at=datetime.now(UTC),
    )


def _coverage_matches_account(
    existing: OrganizationProviderCoverageV1, account: AccountViewV1
) -> bool:
    """Never replace another owner declaration, even in a private test copy."""
    return (
        existing.outcome == "account"
        and existing.account_id == account.account_id
        and existing.organization_id == account.organization_id
        and existing.account_organization_id == account.organization_id
        and existing.provider_key == account.provider_key
        and existing.provenance == "owner_asserted"
    )


def _initial_version(
    repository: SqliteOrganizationProviderCoverageRepositoryV1,
    account: AccountViewV1,
) -> int:
    """Preserve actual owner outcomes; never replace a different declaration."""
    assert account.organization_id is not None
    snapshot = repository.read_coverage(
        OrganizationProviderCoverageSelectionV1(
            (account.organization_id,), account.provider_key
        )
    )
    assert snapshot.completeness == "complete", "coverage_baseline_unavailable"
    if not snapshot.items:
        return 0
    existing = snapshot.items[0]
    assert _coverage_matches_account(existing, account), (
        "existing_owner_outcome_differs"
    )
    return existing.record_version


def _history(
    reference: DatabaseRefV1, account: AccountViewV1
) -> tuple[tuple[object, ...], ...]:
    assert account.organization_id is not None
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            return tuple(
                tuple(row)
                for row in connection.exec_driver_sql(
                    "SELECT * FROM reg_organization_provider_coverage_revision "
                    "WHERE organization_id=? AND provider_key=? "
                    "ORDER BY record_version",
                    (account.organization_id.value, account.provider_key),
                ).all()
            )


def test_real_own_account_set_replay_revoke_and_history(
    actual_registry: ActualCoverageRegistry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    assert account.organization_id is not None
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    baseline_version = _initial_version(repository, account)
    command = _command(account, graph, baseline_version)
    selected = OrganizationProviderCoverageSelectionV1(
        (account.organization_id,), "ollama"
    )
    baseline_history = _history(reference, account)
    baseline = repository.read_coverage(selected).items
    first = repository.set_coverage(command)
    assert first.record_version == baseline_version + 1
    assert not baseline or first.coverage_id == baseline[0].coverage_id
    assert first.provenance == "owner_asserted"
    assert repository.set_coverage(command) == first
    assert repository.read_coverage(selected).items == (first,)
    revoked = repository.revoke_coverage(
        RevokeOrganizationProviderCoverageCommandV1(
            account.organization_id,
            "ollama",
            first.record_version,
            _id(),
            graph.owner_principal_id,
            datetime.now(UTC),
        )
    )
    assert revoked.invalidation_reason == "owner_revoked"
    assert revoked.record_version == first.record_version + 1
    with pytest.raises(RegistryCommandConflictV1, match="registry_replay_stale"):
        repository.set_coverage(command)
    again = repository.set_coverage(_command(account, graph, revoked.record_version))
    assert again.coverage_id == first.coverage_id
    assert again.record_version == baseline_version + 3
    history = _history(reference, account)
    assert history[: len(baseline_history)] == baseline_history
    assert len(history) == len(baseline_history) + 3
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            versions = (
                connection.exec_driver_sql(
                    "SELECT record_version "
                    "FROM reg_organization_provider_coverage_revision "
                    "WHERE coverage_id=? AND record_version>? ORDER BY record_version",
                    (first.coverage_id.value, baseline_version),
                )
                .scalars()
                .all()
            )
    assert versions == [baseline_version + offset for offset in (1, 2, 3)]
    current_account = registry.get_account(account.account_id)
    assert current_account is not None
    assert current_account.record_version == account.record_version


def test_real_account_version_and_replay_conflicts_do_not_write(
    actual_registry: ActualCoverageRegistry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    assert account.organization_id is not None
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    baseline_version = _initial_version(repository, account)
    command = _command(account, graph, baseline_version)
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_account_version_conflict"
    ):
        repository.set_coverage(
            replace(command, expected_account_record_version=account.record_version + 1)
        )
    first = repository.set_coverage(command)
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_idempotency_conflict"
    ):
        repository.set_coverage(replace(command, expected_version=first.record_version))
    current_account = registry.get_account(account.account_id)
    assert current_account is not None
    assert current_account.record_version == account.record_version


def test_real_reassignment_and_return_never_revive_coverage(
    actual_registry: ActualCoverageRegistry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    assert account.organization_id is not None
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    first = repository.set_coverage(
        _command(account, graph, _initial_version(repository, account))
    )
    moved = registry.edit_account(
        EditAccountCommandV1(
            account.account_id,
            account.record_version,
            graph.owner_principal_id,
            _id(),
            "assign",
            datetime.now(UTC),
            organization_id=None,
        )
    )
    registry.edit_account(
        EditAccountCommandV1(
            account.account_id,
            moved.record_version,
            graph.owner_principal_id,
            _id(),
            "assign",
            datetime.now(UTC),
            organization_id=account.organization_id,
        )
    )
    snapshot = repository.read_coverage(
        OrganizationProviderCoverageSelectionV1((account.organization_id,), "ollama")
    )
    assert snapshot.items[0].invalidation_reason == "account_reassigned"
    assert snapshot.items[0].record_version == first.record_version + 1


def test_real_account_archive_restore_keeps_invalidation(
    actual_registry: ActualCoverageRegistry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    assert account.organization_id is not None
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    first = repository.set_coverage(
        _command(account, graph, _initial_version(repository, account))
    )
    archived = registry.edit_account(
        EditAccountCommandV1(
            account.account_id,
            account.record_version,
            graph.owner_principal_id,
            _id(),
            "archive",
            datetime.now(UTC),
        )
    )
    registry.edit_account(
        EditAccountCommandV1(
            account.account_id,
            archived.record_version,
            graph.owner_principal_id,
            _id(),
            "restore",
            datetime.now(UTC),
        )
    )
    snapshot = repository.read_coverage(
        OrganizationProviderCoverageSelectionV1((account.organization_id,), "ollama")
    )
    assert snapshot.items[0].invalidation_reason == "account_archived"
    assert snapshot.items[0].record_version == first.record_version + 1


def test_real_rename_and_monitoring_edits_preserve_owner_assertion(
    actual_registry: ActualCoverageRegistry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    assert account.organization_id is not None
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    first = repository.set_coverage(
        _command(account, graph, _initial_version(repository, account))
    )
    renamed = registry.edit_account(
        EditAccountCommandV1(
            account.account_id,
            account.record_version,
            graph.owner_principal_id,
            _id(),
            "rename",
            datetime.now(UTC),
            friendly_name=account.friendly_name + " review",
        )
    )
    registry.edit_account(
        EditAccountCommandV1(
            account.account_id,
            renamed.record_version,
            graph.owner_principal_id,
            _id(),
            "monitoring",
            datetime.now(UTC),
            monitoring_preference="disabled",
        )
    )
    organization = registry.get_organization(account.organization_id)
    assert organization is not None
    registry.edit_organization(
        EditOrganizationCommandV1(
            organization.organization_id,
            organization.record_version,
            graph.owner_principal_id,
            _id(),
            "rename",
            datetime.now(UTC),
            name=organization.name + " review",
        )
    )
    selection = OrganizationProviderCoverageSelectionV1(
        (account.organization_id,), "ollama"
    )
    assert repository.read_coverage(selection).items == (first,)


def test_real_invalidating_transaction_rolls_back_account_and_history(
    actual_registry: ActualCoverageRegistry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    assert account.organization_id is not None
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    first = repository.set_coverage(
        _command(account, graph, _initial_version(repository, account))
    )
    with pytest.raises(
        RegistryCommandConflictV1, match="registry_coverage_timestamp_conflict"
    ):
        registry.edit_account(
            EditAccountCommandV1(
                account.account_id,
                account.record_version,
                graph.owner_principal_id,
                _id(),
                "archive",
                first.confirmed_at - timedelta(seconds=1),
            )
        )
    after = registry.get_account(account.account_id)
    assert after is not None
    assert after.record_version == account.record_version
    assert after.lifecycle == account.lifecycle
    assert (
        SqliteCloudCredentialRegistryV1(reference).read_monitoring_target(
            account.account_id
        )
        == graph
    )
    selection = OrganizationProviderCoverageSelectionV1(
        (account.organization_id,), "ollama"
    )
    assert repository.read_coverage(selection).items == (first,)


def test_real_same_request_concurrent_writers_produce_one_revision(
    actual_registry: ActualCoverageRegistry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, _registry, account, graph = actual_registry
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    baseline_version = _initial_version(repository, account)
    command = _command(account, graph, baseline_version)
    with ThreadPoolExecutor(max_workers=2) as executor:
        writes = tuple(
            executor.submit(repository.set_coverage, command) for _ in range(2)
        )
        results = tuple(write.result() for write in writes)
    assert results[0] == results[1]
    assert results[0].record_version == baseline_version + 1
