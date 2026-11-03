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
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_coverage_v1 import (
    OrganizationProviderCoverageSelectionV1,
    RevokeOrganizationProviderCoverageCommandV1,
    SetOrganizationProviderCoverageCommandV1,
)
from agentmonitor.modules.registry.application.accounts import EditAccountCommandV1
from agentmonitor.modules.registry.application.organizations import (
    EditOrganizationCommandV1,
    RegistryCommandConflictV1,
)

ROOT = Path(__file__).resolve().parents[4]
LIVE = Path("/home/dev/.local/share/agentmonitor/agentmonitor.db")


def _id() -> OpaqueIdV1:
    return OpaqueIdV1(secrets.token_urlsafe(24))


@pytest.fixture(scope="module")
def coverage_source(tmp_path_factory):
    """The published SQLite backup API copies real state without table inspection."""
    tmp_path = tmp_path_factory.mktemp("coverage-source")
    tmp_path.chmod(0o700)
    copied = tmp_path / "agentmonitor.db"
    with sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True) as source:
        with sqlite3.connect(copied) as target:
            source.backup(target)
    copied.chmod(0o600)
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


@pytest.fixture
def actual_registry(tmp_path: Path, coverage_source: Path):
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
    for account in registry.list_accounts(provider_key="ollama", page_size=100):
        graph = cloud.read_monitoring_target(account.account_id)
        if (
            graph is not None
            and graph.identity_state == "owner_confirmed"
            and account.organization_id
        ):
            selected.append((account, graph))
    assert len(selected) == 1, "actual_owner_confirmed_account_selection_ambiguous"
    account, graph = selected[0]
    return reference, registry, account, graph


def _command(account, graph, version=0):
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


def test_real_own_account_set_replay_revoke_and_history(actual_registry) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    command = _command(account, graph)
    selected = OrganizationProviderCoverageSelectionV1(
        (account.organization_id,), "ollama"
    )
    assert repository.read_coverage(selected).items == ()
    first = repository.set_coverage(command)
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
    assert again.coverage_id == first.coverage_id and again.record_version == 3
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            versions = (
                connection.exec_driver_sql(
                    "SELECT record_version "
                    "FROM reg_organization_provider_coverage_revision "
                    "WHERE coverage_id=? ORDER BY record_version",
                    (first.coverage_id.value,),
                )
                .scalars()
                .all()
            )
    assert versions == [1, 2, 3]
    current_account = registry.get_account(account.account_id)
    assert current_account is not None
    assert current_account.record_version == account.record_version


def test_real_account_version_and_replay_conflicts_do_not_write(
    actual_registry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    command = _command(account, graph)
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


def test_real_reassignment_and_return_never_revive_coverage(actual_registry) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    first = repository.set_coverage(_command(account, graph))
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


def test_real_account_archive_restore_keeps_invalidation(actual_registry) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    first = repository.set_coverage(_command(account, graph))
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
    actual_registry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    first = repository.set_coverage(_command(account, graph))
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
    actual_registry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, registry, account, graph = actual_registry
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    first = repository.set_coverage(_command(account, graph))
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
    actual_registry,
) -> None:
    from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
        SqliteOrganizationProviderCoverageRepositoryV1,
    )

    reference, _registry, account, graph = actual_registry
    repository = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    command = _command(account, graph)
    with ThreadPoolExecutor(max_workers=2) as executor:
        writes = tuple(
            executor.submit(repository.set_coverage, command) for _ in range(2)
        )
        results = tuple(write.result() for write in writes)
    assert results[0] == results[1]
    assert results[0].record_version == 1
