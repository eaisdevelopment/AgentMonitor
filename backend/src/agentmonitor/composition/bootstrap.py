"""Explicit local compositions with loopback and opt-in trusted LAN listeners.

Startup consumes an already migrated, quiescent SQLite file without implicit
DDL or migrations. The authenticated lifespan polls an eligible enrolled Claude
profile through the approved read-only adapter; the schema factory does no I/O.
The CLI selects either the M1 schema seam or the authenticated dashboard.
Native DEP installation policy remains pending.
"""

import argparse
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import signal
import socket
import stat
import subprocess
import tomllib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from functools import partial
from pathlib import Path

import uvicorn
from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqliteDatabaseHandleV1,
    checkpoint_sqlite_database,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    RequireWritableSchemaV1,
    application_schema_range,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.live_health import (
    InspectStartupDatabaseHealthV1,
    LiveDatabaseHealthReaderV1,
)
from agentmonitor.adapters.persistence.alerting.sqlite.actions import (
    SqliteAlertActionRepositoryV1,
)
from agentmonitor.adapters.persistence.alerting.sqlite.repository import (
    SqliteAlertingRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.health import (
    GetCollectorComponentHealthV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.api_tokens import (
    SqliteIdentityAccessApiTokenRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.health import (
    GetIamComponentHealthV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.sessions import (
    SqliteIdentityAccessSessionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
    SqliteOrganizationProviderCoverageRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.health import (
    GetRegistryComponentHealthV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.persistence.runtime_observation.settings.repository import (
    OwnerAssociationSettingsRepositoryV1,
)
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
    SqliteRuntimeObservationRepositoryV1,
)
from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.adapters.providers.ollama.manifest import build_ollama_manifest
from agentmonitor.api.app import create_application
from agentmonitor.api.v1.dependencies import (
    AlertApiPortsV1,
    IamApiPortsV1,
    ObservationApiPortsV1,
)
from agentmonitor.composition.alert_delivery import CapacityAlertDeliveryV1
from agentmonitor.composition.billing_actions import BillingCheckActionsV1
from agentmonitor.composition.billing_local_setup import InstalledBillingLocalSetupV1
from agentmonitor.composition.billing_worker_supervisor import BillingWorkerSupervisorV1
from agentmonitor.composition.claude_dashboard_collection import (
    ClaudeDashboardCollectorV1,
)
from agentmonitor.composition.claude_dashboard_connection import (
    ClaudeDashboardConnectionV1,
)
from agentmonitor.composition.codex_dashboard_collection import (
    CodexDashboardCollectorV1,
)
from agentmonitor.composition.codex_dashboard_connection import (
    CodexDashboardConnectionV1,
)
from agentmonitor.composition.linux_process_locations import (
    read_live_process_locations_v1,
)
from agentmonitor.composition.ollama_cloud_collection import cloud_connection_ready
from agentmonitor.composition.ollama_cloud_connection import (
    OllamaCloudConnectionServiceV1,
)
from agentmonitor.composition.ollama_cloud_worker import OllamaCloudWorkerSupervisorV1
from agentmonitor.composition.ollama_env_store import env_location_matches
from agentmonitor.composition.ollama_local_catalog import read_ollama_local_catalog_v1
from agentmonitor.composition.ollama_runtime_collection import (
    OllamaRuntimeCollectorV1,
)
from agentmonitor.composition.operations_health import (
    CodexProviderHealthLeafV1,
    ConfigurationHealthLeafV1,
    DatabaseHealthLeafV1,
    DatabaseSchemaVersionQueryV1,
    FoundationHealthLeafV1,
)
from agentmonitor.composition.provider_dashboard_connections import (
    ProviderDashboardConnectionsV1,
    ProviderVerifiedQuotaIdentitiesV1,
)
from agentmonitor.contracts.configuration_v1 import (
    BootstrapConfigurationV1,
    ConfigurationRegistryV1,
)
from agentmonitor.contracts.foundation_v1 import BuildMetadataV1
from agentmonitor.contracts.operations_v1 import ComponentRegistrationV1
from agentmonitor.foundation.application import (
    ApplicationLifecycleError,
    ComponentFactorySetV1,
    LifecycleHooksV1,
)
from agentmonitor.foundation.configuration import (
    BootstrapCliOptionsV1,
    BootstrapConfigurationError,
    load_bootstrap_configuration,
)
from agentmonitor.modules.alerting.application.commands import (
    AcknowledgeAlertV1,
    MarkAlertReadV1,
    SnoozeAlertV1,
    UnsnoozeAlertV1,
)
from agentmonitor.modules.alerting.application.queries import (
    GetAlertV1,
    GetDashboardNotificationCountsV1,
    ListAlertHistoryV1,
    ListAlertsV1,
    ListDashboardNotificationsV1,
)
from agentmonitor.modules.alerting.application.rules import (
    ArchiveAlertRuleOverrideV1,
    CreateAlertRuleV1,
    GetAlertRuleV1,
    ListAlertRulesV1,
    UpdateAlertRuleV1,
)
from agentmonitor.modules.capacity.application.budget_queries import (
    GetAccountBudgetCurrentV1,
)
from agentmonitor.modules.capacity.application.ports import ClassifyCapacityProjectionV1
from agentmonitor.modules.capacity.application.queries import (
    GetAccountCapacityV1,
    GetCapacityAggregateV1,
    GetCapacityAggregateV2,
    ListCapacityForecastsV1,
    ListCapacityHistoryV1,
    ListQuotaWindowsV1,
)
from agentmonitor.modules.collection_control.application.queries import (
    ListCollectionRunsV1,
)
from agentmonitor.modules.identity_access.application.api_tokens import (
    CreateApiTokenV1,
    ListApiTokensV1,
    ListIamSecurityEventsV1,
    ResolveBearerTokenV1,
    RevokeApiTokenV1,
    RotateApiTokenV1,
)
from agentmonitor.modules.identity_access.application.authorization import (
    AuthorizePrincipalV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    GetIamInitializationStateV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
    ChangeAdministratorPasswordV1,
    ListSessionsV1,
    LogoutSessionV1,
    ResolveBrowserSessionV1,
    RevokeAllSessionsV1,
    RevokeSessionV1,
    VerifyCsrfV1,
)
from agentmonitor.modules.operations.application.service import OperationsServiceV1
from agentmonitor.modules.provider_system.application.queries import (
    GetProviderCapabilitiesV1,
    GetVerifiedQuotaIdentityV1,
)
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
    CapacityScopeMembershipQueryV2,
    EditAccountV1,
    GetAccountV1,
    ListAccountResourcesV1,
    ListAccountsV1,
    RegisterAccountV1,
)
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationV1,
    EditOrganizationV1,
    GetOrganizationV1,
    ListOrganizationsV1,
    ReorderOrganizationsV1,
)
from agentmonitor.modules.runtime_observation.application.owner_associations import (
    OwnerProcessAccountAssociationsV1,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    GetAgentSessionV1,
    GetSessionTreeV1,
    ListAgentProcessesV1,
    ListAgentSessionsV1,
    ListLiveProcessLocationsV1,
)
from fastapi import FastAPI


class LoopbackServerError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_GIT_EXECUTABLE_V1 = Path("/usr/bin/git")
_GIT_REVISION_V1 = re.compile(r"[a-f0-9]{40}")
_GIT_ENVIRONMENT_V1 = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "XDG_CONFIG_HOME": "/nonexistent",
}


def _git_revision_command_v1(root: Path) -> str | None:
    result = subprocess.run(
        [
            str(_GIT_EXECUTABLE_V1),
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        ],
        cwd=root,
        env=_GIT_ENVIRONMENT_V1,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )
    if result.returncode != 0 or len(result.stdout) > 41:
        return None
    revision = result.stdout.decode("ascii", errors="strict").strip()
    return revision if _GIT_REVISION_V1.fullmatch(revision) is not None else None


def _git_exit_v1(root: Path, *arguments: str) -> int:
    return subprocess.run(
        [
            str(_GIT_EXECUTABLE_V1),
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            *arguments,
        ],
        cwd=root,
        env=_GIT_ENVIRONMENT_V1,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    ).returncode


def read_clean_source_revision_v1(root: Path) -> str | None:
    """Read exact clean HEAD through the fixed local Git boundary.

    Only a revision is returned. Repository paths, status rows and Git errors
    remain internal, and any unavailable or dirty state becomes unknown.
    """

    try:
        executable = os.lstat(_GIT_EXECUTABLE_V1)
        if (
            not stat.S_ISREG(executable.st_mode)
            or executable.st_uid != 0
            or executable.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or executable.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) == 0
        ):
            return None
        before = _git_revision_command_v1(root)
        if before is None or _git_exit_v1(
            root,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--quiet",
            "--ignore-submodules=none",
            "HEAD",
            "--",
        ):
            return None
        untracked = _git_exit_v1(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "--error-unmatch",
            "--",
            "*",
        )
        if untracked != 1:
            return None
        after = _git_revision_command_v1(root)
        return before if before == after else None
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None


def build_metadata() -> BuildMetadataV1:
    """Read only repository build inputs, with no timestamps or local-path output."""
    manifest = Path(__file__).resolve().parents[3] / "pyproject.toml"
    with manifest.open("rb") as stream:
        version = tomllib.load(stream)["project"]["version"]
    if not isinstance(version, str):
        raise ApplicationLifecycleError("build_version_invalid")
    root = manifest.parent.parent
    source_revision = read_clean_source_revision_v1(root)
    openapi_path = root / "contracts/openapi/agentmonitor-v1.json"
    client_path = root / "frontend/src/generated/api/index.ts"
    frontend_manifest = root / "frontend/package.json"
    frontend_build = root / "frontend/dist"
    openapi_hash = None
    client_hash = None
    frontend_hash = None
    versions: list[tuple[str, str]] = []
    if openapi_path.is_file() and not openapi_path.is_symlink():
        source = openapi_path.read_bytes()
        document = json.loads(source)
        openapi_hash = hashlib.sha256(source).hexdigest()
        versions.extend(
            (
                ("api", document["info"]["version"]),
                ("openapi", document["openapi"]),
            )
        )
        if client_path.is_file() and not client_path.is_symlink():
            client_hash = hashlib.sha256(client_path.read_bytes()).hexdigest()
            versions.append(
                ("client", document["x-agentmonitor-generation"]["generator_version"])
            )
    if (
        frontend_build / "dashboard.html"
    ).is_file() and not frontend_build.is_symlink():
        digest = hashlib.sha256()
        artifacts = tuple(
            sorted(path for path in frontend_build.rglob("*") if path.is_file())
        )
        if len(artifacts) <= 128 and all(
            not path.is_symlink() and path.stat().st_size <= 20_000_000
            for path in artifacts
        ):
            for path in artifacts:
                digest.update(
                    path.relative_to(frontend_build).as_posix().encode("utf-8")
                )
                digest.update(b"\0")
                digest.update(hashlib.sha256(path.read_bytes()).digest())
            frontend_hash = digest.hexdigest()
            versions.append(
                ("frontend", json.loads(frontend_manifest.read_bytes())["version"])
            )
    return BuildMetadataV1(
        version,
        source_revision,
        None,
        "omitted_for_reproducibility",
        application_schema_range(),
        frontend_hash,
        openapi_hash,
        client_hash,
        tuple(versions),
    )


def _open_database(
    ref: DatabaseRefV1,
    build: BuildMetadataV1,
    *,
    checkpoint_wal: bool = False,
    database_health: LiveDatabaseHealthReaderV1 | None = None,
) -> SqliteDatabaseHandleV1:
    receipt = None
    if database_health is None:
        view = InspectSchemaCompatibilityV1(
            ref, build.schema_range, "runtime_read_write"
        )
    else:
        view, receipt = InspectStartupDatabaseHealthV1(
            ref, build.schema_range, "runtime_read_write"
        )
    if view.state == "locked" and checkpoint_wal:
        # IAM lifespan holds the service lock here. Recover retained SQLite WAL
        # before the immutable schema check; this applies no DDL or migration.
        checkpoint_sqlite_database(ref)
        if database_health is None:
            view = InspectSchemaCompatibilityV1(
                ref, build.schema_range, "runtime_read_write"
            )
        else:
            view, receipt = InspectStartupDatabaseHealthV1(
                ref, build.schema_range, "runtime_read_write"
            )
    if view.state != "compatible":
        raise ApplicationLifecycleError("database_" + view.state)
    RequireWritableSchemaV1(view)
    if database_health is not None:
        if receipt is None:
            raise ApplicationLifecycleError("database_health_unverified")
        database_health.bind_startup_receipt(receipt)
    return open_sqlite_database(ref, "runtime_read_write")


def create_foundation_application(
    config_path: Path, data_root: Path, *, lifecycle: LifecycleHooksV1
) -> FastAPI:
    settings = load_bootstrap_configuration(
        config_path, {}, BootstrapCliOptionsV1(ConfigurationRegistryV1(()))
    )
    build = build_metadata()
    ref = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    return create_application(
        settings,
        ComponentFactorySetV1(partial(_open_database, ref, build)),
        build,
        lifecycle,
    )


def _iam_ports(reference: DatabaseRefV1) -> IamApiPortsV1:
    bootstrap_repository = SqliteIdentityAccessRepositoryV1(reference)
    sessions_repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    token_repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    hasher = Argon2PasswordV1()
    return IamApiPortsV1(
        GetIamInitializationStateV1(bootstrap_repository),
        AuthenticateAdministratorV1(sessions_repository, hasher),
        ResolveBrowserSessionV1(sessions_repository),
        VerifyCsrfV1(sessions_repository),
        AuthorizePrincipalV1(),
        LogoutSessionV1(sessions_repository),
        ChangeAdministratorPasswordV1(sessions_repository, hasher),
        ListSessionsV1(sessions_repository),
        RevokeSessionV1(sessions_repository),
        RevokeAllSessionsV1(sessions_repository),
        ResolveBearerTokenV1(token_repository),
        ListApiTokensV1(token_repository),
        CreateApiTokenV1(token_repository),
        RotateApiTokenV1(token_repository),
        RevokeApiTokenV1(token_repository),
        ListIamSecurityEventsV1(token_repository),
    )


def _observation_ports(
    reference: DatabaseRefV1,
    claude_collector: ClaudeDashboardCollectorV1,
    codex_collector: CodexDashboardCollectorV1,
    claude_connections: ClaudeDashboardConnectionV1,
    codex_connections: CodexDashboardConnectionV1,
    data_root: Path,
    ollama_cloud_worker: OllamaCloudWorkerSupervisorV1,
    billing_worker: BillingWorkerSupervisorV1,
) -> ObservationApiPortsV1:
    def current_ollama_env_location() -> bool:
        selected = ollama_cloud_worker.credential_env_file()
        if selected is None:
            return False
        try:
            return env_location_matches(data_root, selected)
        except (OSError, ValueError):
            return False

    registry = SqliteRegistryRepositoryV1(reference)
    coverage = SqliteOrganizationProviderCoverageRepositoryV1(reference)
    collection = SqliteCollectionRepositoryV1(reference)
    capacity = SqliteCapacityRepositoryV1(reference)
    runtime = SqliteRuntimeObservationRepositoryV1(reference)
    get_account = GetAccountV1(registry)
    associations = OwnerProcessAccountAssociationsV1(
        read_live_process_locations_v1,
        OwnerAssociationSettingsRepositoryV1(data_root),
        get_account,
    )
    connections = ProviderDashboardConnectionsV1(
        get_account,
        {"claude": claude_connections, "codex": codex_connections},
    )
    verified_identities = ProviderVerifiedQuotaIdentitiesV1(
        get_account,
        {
            "claude": claude_collector.read_verified_identity,
            "codex": codex_collector.read_verified_identity,
        },
    )
    return ObservationApiPortsV1(
        CreateOrganizationV1(registry),
        EditOrganizationV1(registry),
        GetOrganizationV1(registry),
        ListOrganizationsV1(registry),
        ReorderOrganizationsV1(registry),
        RegisterAccountV1(registry),
        EditAccountV1(registry),
        GetAccountV1(registry),
        ListAccountsV1(registry),
        ListProviderInstallationsV1(registry),
        GetProviderCapabilitiesV1(
            (
                build_claude_manifest(),
                build_codex_manifest(),
                build_ollama_manifest(),
            )
        ),
        ListCollectionRunsV1(collection),
        GetAccountCapacityV1(capacity),
        ListQuotaWindowsV1(capacity),
        ListCapacityHistoryV1(capacity),
        ListAgentProcessesV1(runtime),
        ListAgentSessionsV1(runtime),
        GetAgentSessionV1(runtime),
        GetSessionTreeV1(runtime),
        GetVerifiedQuotaIdentityV1(verified_identities),
        ListLiveProcessLocationsV1(associations.read),
        connections,
        associations,
        get_capacity_aggregate=GetCapacityAggregateV1(
            capacity, AlertScopeAndSubjectQueryV1(registry)
        ),
        get_capacity_aggregate_v2=GetCapacityAggregateV2(
            capacity, CapacityScopeMembershipQueryV2(registry)
        ),
        list_capacity_forecasts=ListCapacityForecastsV1(capacity),
        registry_scope=AlertScopeAndSubjectQueryV1(registry),
        registry_scope_v2=CapacityScopeMembershipQueryV2(registry),
        list_account_resources=ListAccountResourcesV1(registry),
        capacity_health_policy=ClassifyCapacityProjectionV1().policy,
        organization_coverage_read=coverage,
        organization_coverage_write=coverage,
        billing_connections=SqliteBillingConnectionRepositoryV1(reference),
        billing_checks=BillingCheckActionsV1(
            reference,
            on_queued=billing_worker.wake,
            can_dispatch=billing_worker.is_monitoring_available,
        ),
        get_account_budget_current=GetAccountBudgetCurrentV1(
            SqliteBillingConnectionRepositoryV1(reference),
            SqliteBudgetReportRepositoryV1(reference),
            collection,
        ),
        billing_local_setup=InstalledBillingLocalSetupV1(
            data_root, socket.gethostname()
        ),
        ollama_local_catalog=read_ollama_local_catalog_v1,
        ollama_cloud_connection=OllamaCloudConnectionServiceV1(
            reference,
            ready=lambda: (
                cloud_connection_ready(ollama_cloud_worker.credential_env_file())
                and ollama_cloud_worker.is_available()
                and ollama_cloud_worker.is_configured()
            ),
            monitoring_ready=ollama_cloud_worker.is_monitoring_available,
            location_current=current_ollama_env_location,
        ),
    )


def create_iam_application(
    config_path: Path,
    data_root: Path,
    *,
    lifecycle: LifecycleHooksV1,
    credential_env_file: Path | None = None,
) -> FastAPI:
    """M2 production IAM mode over a pre-migrated real installation."""
    settings = load_bootstrap_configuration(
        config_path, {}, BootstrapCliOptionsV1(ConfigurationRegistryV1(()))
    )
    build = build_metadata()
    reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    database_health = LiveDatabaseHealthReaderV1(reference, build.schema_range)
    claude_collector = ClaudeDashboardCollectorV1(
        reference, managed_profiles_root=data_root / "profiles" / "claude"
    )
    codex_collector = CodexDashboardCollectorV1(
        reference, managed_profiles_root=data_root / "profiles" / "codex"
    )
    ollama_runtime_collector = OllamaRuntimeCollectorV1(reference, data_root=data_root)
    ollama_cloud_worker = OllamaCloudWorkerSupervisorV1(
        data_root, credential_env_file=credential_env_file
    )
    billing_worker = BillingWorkerSupervisorV1(
        data_root, credential_env_file=credential_env_file
    )
    claude_connections = ClaudeDashboardConnectionV1(reference, data_root)
    codex_connections = CodexDashboardConnectionV1(reference, data_root)
    alert_delivery = CapacityAlertDeliveryV1(reference)
    lifecycle = replace(
        lifecycle,
        tasks=lifecycle.tasks
        + (
            claude_collector.run,
            codex_collector.run,
            ollama_runtime_collector.run,
            ollama_cloud_worker.run,
            billing_worker.run,
            claude_connections.run,
            codex_connections.run,
            alert_delivery.run,
        ),
        # A Codex request is bounded at 30 seconds and owned-child TERM/KILL
        # cleanup can consume four more. Leave bounded scheduling/SQLite margin
        # so lifecycle cancellation drains the worker before closing resources.
        shutdown_timeout_seconds=45,
    )
    app = create_application(
        settings,
        ComponentFactorySetV1(
            partial(
                _open_database,
                reference,
                build,
                checkpoint_wal=True,
                database_health=database_health,
            )
        ),
        build,
        lifecycle,
        iam_mode=True,
        iam_ports=_iam_ports(reference),
        observation_ports=_observation_ports(
            reference,
            claude_collector,
            codex_collector,
            claude_connections,
            codex_connections,
            data_root,
            ollama_cloud_worker,
            billing_worker,
        ),
        service_lock_path=data_root / ".agentmonitor-service.lock",
    )
    alerting = SqliteAlertingRepositoryV1(reference)
    alert_actions = SqliteAlertActionRepositoryV1(reference)
    alert_scope = AlertScopeAndSubjectQueryV1(SqliteRegistryRepositoryV1(reference))
    app.state.alert_ports = AlertApiPortsV1(
        CreateAlertRuleV1(alerting, alert_scope),
        UpdateAlertRuleV1(alerting, alert_scope),
        ArchiveAlertRuleOverrideV1(alerting, alert_scope),
        GetAlertRuleV1(alerting),
        ListAlertRulesV1(alerting),
        GetAlertV1(alert_actions),
        ListAlertsV1(alert_actions),
        ListAlertHistoryV1(alert_actions),
        ListDashboardNotificationsV1(alert_actions),
        GetDashboardNotificationCountsV1(alert_actions),
        AcknowledgeAlertV1(alert_actions),
        SnoozeAlertV1(alert_actions),
        UnsnoozeAlertV1(alert_actions),
        MarkAlertReadV1(alert_actions),
    )
    required = (
        "foundation",
        "configuration",
        "database",
        "identity_access",
        "registry",
    )
    optional = (
        "provider_system",
        "collection_control",
        "capacity",
        "runtime_observation",
        "alerting",
        "provider.claude",
        "provider.codex",
    )
    manifest = tuple(
        ComponentRegistrationV1(key, "required_for_normal_readiness", ())
        for key in required
    )
    manifest += tuple(
        ComponentRegistrationV1(
            key,
            "optional_degraded",
            ("due_count", "running_count", "blocked_count")
            if key == "collection_control"
            else (),
        )
        for key in optional
    )
    lifecycle_query = app.state.lifecycle.get_lifecycle_state
    app.state.operations_ports = OperationsServiceV1(
        manifest,
        (
            ("foundation", FoundationHealthLeafV1(lifecycle_query)),
            ("configuration", ConfigurationHealthLeafV1(settings)),
            ("database", DatabaseHealthLeafV1(database_health)),
            ("identity_access", GetIamComponentHealthV1(reference)),
            ("registry", GetRegistryComponentHealthV1(reference)),
            ("collection_control", GetCollectorComponentHealthV1(reference)),
            ("provider.codex", CodexProviderHealthLeafV1()),
        ),
        lifecycle_query,
        build,
        settings,
        ConfigurationRegistryV1(()),
        DatabaseSchemaVersionQueryV1(database_health),
    )
    return app


def create_iam_schema_application() -> FastAPI:
    """Same M2 route declarations, no runnable state or database side effects."""
    return create_application(
        BootstrapConfigurationV1("1.0.0", (), (), ()),
        ComponentFactorySetV1(None),
        build_metadata(),
        LifecycleHooksV1(),
        iam_mode=True,
    )


def create_schema_application() -> FastAPI:
    """Fixed build factory: same route source, no lifespan, DB or background work.

    Deliberately cannot run as a service: its absent runtime component fails
    lifespan closed. The declaration has no external config keys to load in M1.
    """
    return create_application(
        BootstrapConfigurationV1("1.0.0", (), (), ()),
        ComponentFactorySetV1(None),
        build_metadata(),
        LifecycleHooksV1(),
    )


class _OwnedServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        # The runner owns signal installation/restoration and returns safe exit
        # codes; Uvicorn must not re-raise SIGTERM after successful cleanup.
        yield


async def _serve_loopback(
    app: FastAPI,
    *,
    host: str,
    port: int,
    ready: Callable[[str], None] | None,
    stop: asyncio.Event,
    lan_host: str | None = None,
    lan_network: str | None = None,
) -> None:
    """Serve actual Uvicorn on a prebound IPv4 loopback socket, including port 0."""
    if host != "127.0.0.1":
        raise LoopbackServerError("bind_not_loopback")
    if type(port) is not int or not 0 <= port <= 65535:
        raise LoopbackServerError("bind_port_invalid")
    network: ipaddress.IPv4Network | None = None
    if lan_host is not None or lan_network is not None:
        try:
            if lan_host is None or lan_network is None or app.state.iam_ports is None:
                raise ValueError
            host_address = ipaddress.IPv4Address(lan_host)
            parsed_network = ipaddress.IPv4Network(lan_network, strict=True)
            private_ranges = (
                ipaddress.IPv4Network("10.0.0.0/8"),
                ipaddress.IPv4Network("172.16.0.0/12"),
                ipaddress.IPv4Network("192.168.0.0/16"),
            )
            if (
                not any(parsed_network.subnet_of(item) for item in private_ranges)
                or host_address not in parsed_network
                or host_address
                in {parsed_network.network_address, parsed_network.broadcast_address}
                or str(host_address) != lan_host
                or str(parsed_network) != lan_network
            ):
                raise ValueError
            network = parsed_network
        except (ValueError, AttributeError):
            raise LoopbackServerError("lan_binding_invalid") from None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lan_sock: socket.socket | None = None
    failed = False
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.setblocking(False)
        if lan_host is not None:
            lan_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            lan_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            lan_sock.bind((lan_host, sock.getsockname()[1]))
            lan_sock.setblocking(False)
    except OSError:
        failed = True
        sock.close()
        if lan_sock is not None:
            lan_sock.close()
    if failed:
        raise LoopbackServerError("bind_unavailable") from None
    try:
        app.state.loopback_schema_binding.address = (host, sock.getsockname()[1])
        app.state.loopback_schema_binding.lan_address = (
            lan_sock.getsockname() if lan_sock is not None else None
        )
        app.state.loopback_schema_binding.lan_network = network
        await _run_server(
            app,
            sock=sock,
            ready=ready,
            stop=stop,
            additional_sockets=(lan_sock,) if lan_sock is not None else (),
        )
    finally:
        app.state.loopback_schema_binding.address = None
        app.state.loopback_schema_binding.lan_address = None
        app.state.loopback_schema_binding.lan_network = None
        sock.close()
        if lan_sock is not None:
            lan_sock.close()


async def _run_server(
    app: FastAPI,
    *,
    sock: socket.socket,
    ready: Callable[[str], None] | None,
    stop: asyncio.Event,
    additional_sockets: tuple[socket.socket, ...] = (),
) -> None:
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=sock.getsockname()[1],
        loop="asyncio",
        http="h11",
        ws="none",
        lifespan="on",
        proxy_headers=False,
        forwarded_allow_ips=[],
        workers=1,
        reload=False,
        env_file=None,
        server_header=False,
        access_log=False,
        timeout_graceful_shutdown=app.state.lifecycle.hooks.shutdown_timeout_seconds,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {"discard": {"class": "logging.NullHandler"}},
            "loggers": {
                "uvicorn": {"handlers": ["discard"], "propagate": False},
                "uvicorn.error": {"handlers": ["discard"], "propagate": False},
            },
        },
    )
    server = _OwnedServer(config)

    async def drive() -> None:
        failure: str | None = None
        try:
            await server.serve(sockets=[sock, *additional_sockets])
        except SystemExit:
            failure = "startup_failed"
        except Exception:
            failure = "server_failed"
        if failure is not None:
            raise LoopbackServerError(failure) from None
        if app.state.lifecycle.failure_code:
            raise LoopbackServerError("shutdown_failed")

    task = asyncio.create_task(drive())
    cancelled = False
    try:
        while not server.started:
            if task.done():
                await task
                raise LoopbackServerError("startup_failed")
            await asyncio.sleep(0.01)
        if ready is not None:
            ready(f"http://127.0.0.1:{sock.getsockname()[1]}")
        while not stop.is_set() and not task.done():
            await asyncio.sleep(0.02)
        server.should_exit = True
        await asyncio.shield(task)
    except asyncio.CancelledError:
        cancelled = True
    finally:
        server.should_exit = True
        while not task.done():
            try:
                # Uvicorn's bounded HTTP drain and application cleanup must finish
                # before caller cancellation is propagated or the socket is closed.
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
    # A shutdown failure takes precedence over cancellation and remains typed.
    task.result()
    if cancelled:
        raise asyncio.CancelledError


async def serve_loopback(
    app: FastAPI,
    *,
    host: str,
    port: int,
    ready: Callable[[str], None] | None,
    stop: asyncio.Event,
    lan_host: str | None = None,
    lan_network: str | None = None,
) -> None:
    """Typed sanitized server boundary; callbacks never expose raw failures."""
    code = "server_failed"
    try:
        await _serve_loopback(
            app,
            host=host,
            port=port,
            ready=ready,
            stop=stop,
            lan_host=lan_host,
            lan_network=lan_network,
        )
        return
    except LoopbackServerError as error:
        code = error.code
    except Exception:
        pass
    raise LoopbackServerError(code) from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--credential-env-file", type=Path)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--lan-host", help="Opt-in private IPv4 dashboard interface")
    parser.add_argument(
        "--lan-network",
        help="Canonical private IPv4 subnet allowed on the LAN listener",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--foundation-contract", action="store_true")
    mode.add_argument("--authenticated-dashboard", action="store_true")
    args = parser.parse_args()

    async def run() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signum, stop.set)
        try:
            if args.authenticated_dashboard:
                app = create_iam_application(
                    args.config,
                    args.data_root,
                    lifecycle=LifecycleHooksV1(),
                    credential_env_file=args.credential_env_file,
                )
            else:
                app = create_foundation_application(
                    args.config,
                    args.data_root,
                    lifecycle=LifecycleHooksV1(foundation_contract_mode=True),
                )

            def ready(origin: str) -> None:
                print(json.dumps({"event": "ready", "origin": origin}), flush=True)
                if args.lan_host is not None:
                    lan_port = origin.rsplit(":", 1)[1]
                    print(
                        json.dumps(
                            {
                                "event": "lan_ready",
                                "origin": f"http://{args.lan_host}:{lan_port}",
                                "network": args.lan_network,
                            }
                        ),
                        flush=True,
                    )

            await serve_loopback(
                app,
                host=args.host,
                port=args.port,
                ready=ready,
                stop=stop,
                lan_host=args.lan_host,
                lan_network=args.lan_network,
            )
        finally:
            for signum in (signal.SIGTERM, signal.SIGINT):
                loop.remove_signal_handler(signum)

    code = "bootstrap_failed"
    try:
        asyncio.run(run(), debug=False)
        return 0
    except (
        LoopbackServerError,
        ApplicationLifecycleError,
        BootstrapConfigurationError,
    ) as error:
        code = error.code
    except Exception:
        pass
    print(json.dumps({"event": "failed", "code": code}), flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
