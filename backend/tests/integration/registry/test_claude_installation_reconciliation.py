"""Real Claude installation reconciliation through the public M02 port."""

import shutil
import subprocess
import sys
from dataclasses import fields, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    RegistryRepositoryErrorV1,
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.adapter import ClaudeAdapterV1
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.installation_discovery import (
    discover_claude_installation_v1,
)
from agentmonitor.adapters.providers.claude.manifest import CLAUDE_PROVIDER_VERSION
from agentmonitor.composition.claude_installation_reconciliation import (
    reconcile_claude_installation_v1,
)
from agentmonitor.composition.iam_operator import exclusive_service_quiescence
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import DiscoveryOutcomeV1
from agentmonitor.modules.registry.application.accounts import (
    ListAccountsV1,
    ListMonitoringProfilesV1,
)
from agentmonitor.modules.registry.application.discovery import (
    ListDiscoveryCandidatesV1,
    ListProviderInstallationsV1,
)
from agentmonitor.modules.registry.application.organizations import (
    RegistryCommandConflictV1,
)
from agentmonitor.modules.registry.application.owner_enrollment import (
    EnrollOwnerConfirmedDiscoveryV1,
)

MODULE = "agentmonitor.composition.claude_installation_reconciliation"


def _database(tmp_path: Path) -> DatabaseRefV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return reference


def _environment() -> dict[str, str]:
    executable = shutil.which("claude")
    assert executable is not None
    return {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": str(Path(executable).parent),
        "PYTHONPATH": str(Path(__file__).parents[3] / "src"),
    }


def _without_revision(value: object) -> tuple[tuple[str, object], ...]:
    return tuple(
        (field.name, getattr(value, field.name))
        for field in fields(value)  # type: ignore[arg-type]
        if field.name != "registry_revision"
    )


def _protected_views(
    repository: SqliteRegistryRepositoryV1,
) -> tuple[tuple[tuple[tuple[str, object], ...], ...], ...]:
    candidates = ListDiscoveryCandidatesV1(repository)("claude")
    accounts = ListAccountsV1(repository)("claude")
    profiles = tuple(
        profile
        for account in accounts
        for profile in ListMonitoringProfilesV1(repository)(account.account_id)
    )
    return tuple(
        tuple(_without_revision(item) for item in values)
        for values in (candidates, accounts, profiles)
    )


def test_real_installation_discovery_emits_no_account_candidate() -> None:
    """FR-DISC-008: selected admitted binary yields installation-only evidence."""
    outcome = discover_claude_installation_v1()

    assert outcome.state == "success"
    assert outcome.value is not None
    assert outcome.provenance is not None
    assert outcome.value.accounts == ()
    assert len(outcome.value.installations) == 1
    installation = outcome.value.installations[0]
    assert installation.provider_key == "claude"
    assert installation.installation_ref.value == "claude-installation-default"
    assert installation.product_version == CLAUDE_PROVIDER_VERSION
    assert installation.platform_id == "linux-x86_64"
    assert outcome.provenance.provider_version == CLAUDE_PROVIDER_VERSION
    assert outcome.provenance.capability_id == "installation.discovery"


def test_real_installation_reconciliation_is_stable_and_idempotent(
    tmp_path: Path,
) -> None:
    """CTR-REG-004/006: real A01 evidence updates one stable M02 installation."""
    reference = _database(tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)

    first = reconcile_claude_installation_v1(reference)
    first_installations = ListProviderInstallationsV1(repository)("claude")
    first_candidates = ListDiscoveryCandidatesV1(repository)()
    first_accounts = ListAccountsV1(repository)()
    first_profiles = tuple(
        profile
        for account in first_accounts
        for profile in ListMonitoringProfilesV1(repository)(account.account_id)
    )
    replay = reconcile_claude_installation_v1(reference)

    assert first.replay_verified is True
    assert replay.replay_verified is True
    assert len(first_installations) == 1
    assert (
        first.provider_installation_id
        == replay.provider_installation_id
        == first_installations[0].provider_installation_id
    )
    assert first.provider_version == replay.provider_version == CLAUDE_PROVIDER_VERSION
    assert first_installations[0].version.masked_value == CLAUDE_PROVIDER_VERSION
    assert first_installations[0].presence_state == "present"
    current_installations = ListProviderInstallationsV1(repository)("claude")
    assert len(current_installations) == 1
    assert (
        current_installations[0].provider_installation_id
        == first_installations[0].provider_installation_id
    )
    assert current_installations[0].record_version == (
        first_installations[0].record_version + 1
    )
    assert ListDiscoveryCandidatesV1(repository)() == first_candidates == ()
    assert ListAccountsV1(repository)() == first_accounts == ()
    assert first_profiles == ()


def test_repository_installation_only_entry_uses_real_outcome(
    tmp_path: Path,
) -> None:
    """CTR-REG-004/006: the strict internal entry admits the real A01 outcome."""
    reference = _database(tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    outcome = discover_claude_installation_v1()

    result = repository.reconcile_installation_only_discovery(
        outcome,
        reconciled_at=datetime.now(UTC),
    )

    assert len(result.installations) == 1
    assert result.installations[0].version.masked_value == CLAUDE_PROVIDER_VERSION
    assert result.candidates == ()


def test_strict_replay_rejects_changed_capability_and_preserves_database(
    tmp_path: Path,
) -> None:
    """CTR-REG-004/006: a receipt cannot bypass the strict capability scope."""
    reference = _database(tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    outcome = discover_claude_installation_v1()
    repository.reconcile_installation_only_discovery(
        outcome,
        reconciled_at=datetime.now(UTC),
    )
    before = reference._path.read_bytes()
    provenance = outcome.provenance
    assert provenance is not None
    changed = replace(
        outcome,
        provenance=replace(
            provenance,
            capability_id="subscription.quota",
        ),
    )

    with pytest.raises(
        RegistryRepositoryErrorV1,
        match="^registry_installation_scope_invalid$",
    ):
        repository.reconcile_installation_only_discovery(
            changed,
            reconciled_at=datetime.now(UTC),
        )

    assert reference._path.read_bytes() == before


def test_strict_replay_rejects_changed_installation_provider_and_preserves_database(
    tmp_path: Path,
) -> None:
    """CTR-REG-004/006: a receipt cannot bypass nested provider scope."""
    reference = _database(tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    outcome = discover_claude_installation_v1()
    repository.reconcile_installation_only_discovery(
        outcome,
        reconciled_at=datetime.now(UTC),
    )
    before = reference._path.read_bytes()
    value = outcome.value
    provenance = outcome.provenance
    assert value is not None
    assert provenance is not None
    changed_installation = replace(
        value.installations[0],
        provider_key="other-provider",
    )
    changed = DiscoveryOutcomeV1.success(
        replace(
            value,
            installations=(changed_installation,),
        ),
        provenance,
    )

    with pytest.raises(
        RegistryRepositoryErrorV1,
        match="^registry_installation_scope_invalid$",
    ):
        repository.reconcile_installation_only_discovery(
            changed,
            reconciled_at=datetime.now(UTC),
        )

    assert reference._path.read_bytes() == before


@pytest.mark.parametrize(
    "field",
    ("decision_reference", "correlation_id"),
)
def test_strict_replay_binds_write_metadata_and_preserves_database(
    tmp_path: Path,
    field: Literal["decision_reference", "correlation_id"],
) -> None:
    """CTR-REG-004/006: replay requires identical stored write metadata."""
    reference = _database(tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    outcome = discover_claude_installation_v1()
    repository.reconcile_installation_only_discovery(
        outcome,
        reconciled_at=datetime.now(UTC),
    )
    before = reference._path.read_bytes()
    provenance = outcome.provenance
    assert provenance is not None
    if field == "decision_reference":
        changed_provenance = replace(
            provenance,
            decision_reference="changed-installation-admission",
        )
    else:
        changed_provenance = replace(
            provenance,
            correlation_id=OpaqueIdV1("changed-installation-correlation"),
        )
    changed = replace(
        outcome,
        provenance=changed_provenance,
    )

    with pytest.raises(
        RegistryCommandConflictV1,
        match="^registry_idempotency_conflict$",
    ):
        repository.reconcile_installation_only_discovery(
            changed,
            reconciled_at=datetime.now(UTC),
        )

    assert reference._path.read_bytes() == before


def test_strict_transaction_rejects_account_discovery_and_preserves_real_graph(
    tmp_path: Path,
) -> None:
    """CTR-REG-004/006: rejection and refresh preserve a populated real graph."""
    reference = _database(tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    installation = discover_default_installation()
    account_outcome = ClaudeAdapterV1(installation).discover_owner_confirmed_default(
        operation_id="installation-atomic-account-discovery",
        correlation_id="installation-atomic-correlation",
        account_ref="installation-atomic-account",
        profile_ref="installation-atomic-profile",
        resource_ref="installation-atomic-resource",
    )
    graph = EnrollOwnerConfirmedDiscoveryV1(repository)(
        account_outcome,
        reconciled_at=datetime.now(UTC),
        command_id="installation-atomic-confirmation",
        principal_id="installation-atomic-owner",
        expected_provider_key="claude",
        friendly_name="Atomic reconciliation account",
        profile_locator="installation-atomic-profile",
        enrollment_command_id="installation-atomic-enrollment",
    )
    before_views = _protected_views(repository)
    before_bytes = reference._path.read_bytes()

    with pytest.raises(
        RegistryRepositoryErrorV1,
        match="^registry_installation_scope_invalid$",
    ):
        repository.reconcile_installation_only_discovery(
            account_outcome,
            reconciled_at=datetime.now(UTC),
        )

    assert reference._path.read_bytes() == before_bytes
    assert _protected_views(repository) == before_views
    installation_outcome = discover_claude_installation_v1()
    reconciled = repository.reconcile_installation_only_discovery(
        installation_outcome,
        reconciled_at=datetime.now(UTC),
    )
    replay = repository.reconcile_installation_only_discovery(
        installation_outcome,
        reconciled_at=datetime.now(UTC),
    )

    assert reconciled == replay
    assert _protected_views(repository) == before_views
    assert len(reconciled.installations) == 1
    assert (
        reconciled.installations[0].provider_installation_id
        == graph.candidate_before_confirmation.provider_installation_id
    )


def test_canonical_command_uses_real_binary_and_real_sqlite(tmp_path: Path) -> None:
    """FR-DISC-008: the operator command is fail closed and replay safe."""
    reference = _database(tmp_path)
    environment = _environment()
    command = [
        sys.executable,
        "-m",
        MODULE,
        "--data-root",
        str(tmp_path),
    ]

    first = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        env=environment,
    )
    repository = SqliteRegistryRepositoryV1(reference)
    installed = ListProviderInstallationsV1(repository)("claude")
    replay = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        env=environment,
    )

    assert first.returncode == replay.returncode == 0
    assert (
        first.stdout
        == replay.stdout
        == (
            "CLAUDE INSTALLATION RECONCILIATION: PASSED — "
            "current admitted installation registered\n"
        )
    )
    assert first.stderr == replay.stderr == ""
    assert len(installed) == 1
    assert installed[0].version.masked_value == CLAUDE_PROVIDER_VERSION
    current = ListProviderInstallationsV1(repository)("claude")
    assert len(current) == 1
    assert current[0].provider_installation_id == installed[0].provider_installation_id
    assert current[0].record_version == installed[0].record_version + 1
    assert ListDiscoveryCandidatesV1(repository)() == ()
    assert ListAccountsV1(repository)() == ()


def test_canonical_command_rejects_invalid_or_relative_targets(tmp_path: Path) -> None:
    """NFR-SEC-001: ambiguous operator targets fail before discovery or writes."""
    reference = _database(tmp_path)
    before = reference._path.read_bytes()
    environment = _environment()
    base = [sys.executable, "-m", MODULE]

    invalid = subprocess.run(
        base,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
        env=environment,
    )
    relative = subprocess.run(
        [*base, "--data-root", "relative-root"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
        env=environment,
    )

    assert invalid.returncode == 2
    assert invalid.stdout == "invalid_operator_arguments\n"
    assert invalid.stderr == ""
    assert relative.returncode == 3
    assert relative.stdout == (
        "CLAUDE INSTALLATION RECONCILIATION: BLOCKED — absolute data root required\n"
    )
    assert relative.stderr == ""
    assert reference._path.read_bytes() == before


def test_canonical_command_refuses_occupied_service_lock_before_write(
    tmp_path: Path,
) -> None:
    """NFR-OPS-001: owner reconciliation requires real service quiescence."""
    reference = _database(tmp_path)
    before = reference._path.read_bytes()
    command = [
        sys.executable,
        "-m",
        MODULE,
        "--data-root",
        str(tmp_path),
    ]

    with exclusive_service_quiescence(tmp_path, reference):
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            env=_environment(),
        )

    assert result.returncode == 3
    assert result.stdout == (
        "CLAUDE INSTALLATION RECONCILIATION: BLOCKED — service quiescence required\n"
    )
    assert result.stderr == ""
    assert reference._path.read_bytes() == before
    assert (
        ListProviderInstallationsV1(SqliteRegistryRepositoryV1(reference))("claude")
        == ()
    )
