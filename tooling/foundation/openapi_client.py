"""CTR-FND-005 repository-owned V1 OpenAPI/strict TypeScript generation.

Canonical command: backend/.venv/bin/python tooling/foundation/openapi_client.py
Use --check for read-only drift verification. Only the fixed production schema
factory and the two allocated outputs are permitted. No third-party generator,
provider startup, dynamic plugin import, timestamps or host paths are emitted.

The compiler admits only the frozen IAM and dashboard HTTP surface. It never
invents an operation or response schema to fill the client.
Validation combines FastAPI's OpenAPI 3.1 model with the exact policy catalog.
Replacements are atomic per file, staged together, with rollback on write errors;
cross-directory crash atomicity is not claimed. --check detects interrupted pairs.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi.openapi.models import OpenAPI
from pydantic import ValidationError

FACTORY_REF = "agentmonitor.composition.bootstrap:create_iam_schema_application"
GENERATOR_VERSION = "2.0.8"
OPENAPI_RELATIVE = Path("contracts/openapi/agentmonitor-v1.json")
CLIENT_RELATIVE = Path("frontend/src/generated/api/index.ts")
METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
)
SOURCE_FILES = (
    "backend/pyproject.toml",
    "backend/src/agentmonitor/api/app.py",
    "backend/src/agentmonitor/api/v1/router.py",
    "backend/src/agentmonitor/api/problem.py",
    "backend/src/agentmonitor/api/transport.py",
    "backend/src/agentmonitor/api/v1/dependencies.py",
    "backend/src/agentmonitor/api/v1/ollama_cloud_port.py",
    "backend/src/agentmonitor/api/v1/pagination.py",
    "backend/src/agentmonitor/api/v1/routers/iam.py",
    "backend/src/agentmonitor/api/v1/routers/_observation.py",
    "backend/src/agentmonitor/api/v1/routers/registry.py",
    "backend/src/agentmonitor/api/v1/routers/coverage.py",
    "backend/src/agentmonitor/api/v1/routers/providers.py",
    "backend/src/agentmonitor/api/v1/routers/provider_connections.py",
    "backend/src/agentmonitor/api/v1/routers/collection.py",
    "backend/src/agentmonitor/api/v1/routers/capacity.py",
    "backend/src/agentmonitor/api/v1/routers/budgets.py",
    "backend/src/agentmonitor/api/v1/routers/budget_overview.py",
    "backend/src/agentmonitor/api/v1/routers/billing_actions.py",
    "backend/src/agentmonitor/api/v1/routers/runtime.py",
    "backend/src/agentmonitor/api/v1/routers/operations.py",
    "backend/src/agentmonitor/api/v1/routers/alerts.py",
    "backend/src/agentmonitor/api/v1/serialization.py",
    "backend/src/agentmonitor/api/v1/schemas/iam.py",
    "backend/src/agentmonitor/api/v1/schemas/registry.py",
    "backend/src/agentmonitor/api/v1/schemas/coverage.py",
    "backend/src/agentmonitor/api/v1/schemas/providers.py",
    "backend/src/agentmonitor/api/v1/schemas/collection.py",
    "backend/src/agentmonitor/api/v1/schemas/capacity.py",
    "backend/src/agentmonitor/api/v1/schemas/budgets.py",
    "backend/src/agentmonitor/api/v1/schemas/budget_overview.py",
    "backend/src/agentmonitor/api/v1/schemas/billing_actions.py",
    "backend/src/agentmonitor/api/v1/schemas/runtime.py",
    "backend/src/agentmonitor/api/v1/schemas/operations.py",
    "backend/src/agentmonitor/api/v1/schemas/alerts.py",
    "backend/src/agentmonitor/foundation/application.py",
    "backend/src/agentmonitor/foundation/configuration.py",
    "backend/src/agentmonitor/foundation/observability.py",
    "backend/src/agentmonitor/composition/bootstrap.py",
    "backend/src/agentmonitor/composition/claude_dashboard_connection.py",
    "backend/src/agentmonitor/composition/claude_managed_connection.py",
    "backend/src/agentmonitor/adapters/providers/claude/authentication/browser.py",
    "backend/src/agentmonitor/adapters/providers/claude/subscription/source.py",
    "backend/src/agentmonitor/adapters/providers/claude/subscription/terminal_screen.py",
    "backend/src/agentmonitor/adapters/providers/claude/authentication/owned_process.py",
    "backend/src/agentmonitor/adapters/providers/claude/authentication/reauthentication.py",
    "backend/src/agentmonitor/modules/identity_access/application/authorization.py",
    "backend/src/agentmonitor/contracts/common_v1.py",
    "backend/src/agentmonitor/contracts/configuration_v1.py",
    "backend/src/agentmonitor/contracts/foundation_v1.py",
    "backend/src/agentmonitor/contracts/database_v1.py",
    "backend/src/agentmonitor/contracts/identity_access_v1.py",
    "backend/src/agentmonitor/contracts/registry_v1.py",
    "backend/src/agentmonitor/contracts/registry_billing_v1.py",
    "backend/src/agentmonitor/contracts/registry_coverage_v1.py",
    "backend/src/agentmonitor/contracts/provider_system_v1.py",
    "backend/src/agentmonitor/contracts/collection_control_v1.py",
    "backend/src/agentmonitor/contracts/capacity_v1.py",
    "backend/src/agentmonitor/contracts/budget_query_v1.py",
    "backend/src/agentmonitor/contracts/billing_actions_v1.py",
    "backend/src/agentmonitor/contracts/runtime_observation_v1.py",
    "backend/src/agentmonitor/contracts/operations_v1.py",
    "backend/src/agentmonitor/contracts/alerting_v1.py",
    "backend/src/agentmonitor/modules/registry/application/accounts.py",
    "backend/src/agentmonitor/modules/registry/application/discovery.py",
    "backend/src/agentmonitor/modules/registry/application/organizations.py",
    "backend/src/agentmonitor/modules/registry/domain/names.py",
    "backend/src/agentmonitor/modules/provider_system/application/queries.py",
    "backend/src/agentmonitor/modules/collection_control/application/queries.py",
    "backend/src/agentmonitor/modules/capacity/application/queries.py",
    "backend/src/agentmonitor/modules/runtime_observation/application/queries.py",
    "backend/src/agentmonitor/modules/runtime_observation/application/owner_associations.py",
    "backend/src/agentmonitor/modules/runtime_observation/application/ports.py",
    "backend/src/agentmonitor/adapters/persistence/runtime_observation/settings/repository.py",
    "backend/src/agentmonitor/composition/linux_process_locations.py",
    "backend/src/agentmonitor/adapters/providers/claude/installation.py",
    "backend/src/agentmonitor/adapters/providers/claude/manifest.py",
    "backend/src/agentmonitor/adapters/persistence/registry/sqlite/repository.py",
    "backend/src/agentmonitor/adapters/persistence/registry/sqlite/billing_connections.py",
    "backend/src/agentmonitor/modules/registry/domain/billing_connection.py",
    "backend/src/agentmonitor/composition/billing_local_setup.py",
    "backend/src/agentmonitor/adapters/persistence/registry/sqlite/coverage.py",
    "backend/src/agentmonitor/adapters/persistence/registry/sqlite/coverage_records.py",
    "backend/src/agentmonitor/adapters/persistence/registry/sqlite/registry_transaction.py",
    "backend/src/agentmonitor/adapters/persistence/collection_control/sqlite/repository.py",
    "backend/src/agentmonitor/adapters/persistence/capacity/sqlite/repository.py",
    "backend/src/agentmonitor/adapters/persistence/runtime_observation/sqlite/repository.py",
    "backend/src/agentmonitor/adapters/persistence/_shared/sqlite/core/policy.py",
    "backend/src/agentmonitor/adapters/persistence/_shared/sqlite/schema/compatibility.py",
    "backend/migrations/catalog.toml",
    "backend/migrations/env.py",
    "backend/migrations/versions/v1_0000_fnd_anchor.py",
    "backend/migrations/versions/v1_0100_m01_identity_access.py",
)

IAM_OPERATIONS = {
    (
        "/api/v1/accounts/{account_id}/billing-connections/{resource_id}/monitoring",
        "get",
    ): "billing_get_monitoring_v1",
    (
        "/api/v1/accounts/{account_id}/billing-connections/{resource_id}/monitoring",
        "put",
    ): "billing_set_monitoring_v1",
    ("/api/v1/collection-runs/{run_id}/budget", "get"): "billing_get_run_status_v1",
    (
        "/api/v1/accounts/{account_id}/billing-connections/{resource_id}/checks",
        "post",
    ): "billing_check_connection_v1",
    (
        "/api/v1/provider-coverage/{provider_key}",
        "get",
    ): "registry_list_organization_coverage_v1",
    ("/api/v1/operations/liveness", "get"): "operations_get_liveness_v1",
    ("/api/v1/operations/readiness", "get"): "operations_get_readiness_v1",
    ("/api/v1/operations/health", "get"): "operations_get_health_v1",
    ("/api/v1/operations/versions", "get"): "operations_get_versions_v1",
    ("/api/v1/operations/diagnostics", "get"): "operations_get_diagnostics_v1",
    ("/api/v1/alert-rules", "get"): "alert_list_rules_v1",
    ("/api/v1/alert-rules", "post"): "alert_create_rule_v1",
    ("/api/v1/alert-rules/{rule_id}", "get"): "alert_get_rule_v1",
    ("/api/v1/alert-rules/{rule_id}", "put"): "alert_update_rule_v1",
    ("/api/v1/alert-rules/{rule_id}/archivals", "post"): "alert_archive_rule_v1",
    ("/api/v1/alerts", "get"): "alert_list_alerts_v1",
    ("/api/v1/alert-notifications", "get"): "alert_list_notifications_v1",
    ("/api/v1/alert-notifications/counts", "get"): "alert_get_notification_counts_v1",
    ("/api/v1/alerts/{alert_id}", "get"): "alert_get_alert_v1",
    ("/api/v1/alerts/{alert_id}/history", "get"): "alert_list_history_v1",
    ("/api/v1/alerts/{alert_id}/acknowledgements", "post"): "alert_acknowledge_v1",
    ("/api/v1/alerts/{alert_id}/snoozes", "post"): "alert_snooze_v1",
    ("/api/v1/alerts/{alert_id}/unsnoozes", "post"): "alert_unsnooze_v1",
    ("/api/v1/alerts/{alert_id}/read-receipts", "post"): "alert_mark_read_v1",
    ("/api/v1/iam/initialization", "get"): "iam_get_initialization_v1",
    ("/api/v1/session", "post"): "iam_login_v1",
    ("/api/v1/session", "get"): "iam_get_current_session_v1",
    ("/api/v1/session", "delete"): "iam_logout_v1",
    ("/api/v1/session/password", "patch"): "iam_change_password_v1",
    ("/api/v1/iam/sessions", "get"): "iam_list_sessions_v1",
    ("/api/v1/iam/sessions/{session_id}", "delete"): "iam_revoke_session_v1",
    ("/api/v1/iam/session-revocations", "post"): "iam_revoke_other_sessions_v1",
    ("/api/v1/api-tokens", "get"): "iam_list_api_tokens_v1",
    ("/api/v1/api-tokens", "post"): "iam_create_api_token_v1",
    ("/api/v1/api-tokens/{token_id}/rotations", "post"): "iam_rotate_api_token_v1",
    ("/api/v1/api-tokens/{token_id}", "delete"): "iam_revoke_api_token_v1",
    ("/api/v1/iam/security-events", "get"): "iam_list_security_events_v1",
    (
        "/api/v1/accounts/{account_id}/billing-connections",
        "get",
    ): "registry_get_billing_connections_v1",
    (
        "/api/v1/accounts/{account_id}/billing-connections",
        "post",
    ): "registry_create_billing_connection_v1",
    ("/api/v1/accounts", "get"): "registry_list_accounts_v1",
    ("/api/v1/accounts", "post"): "registry_register_account_v1",
    ("/api/v1/accounts/{account_id}", "get"): "registry_get_account_v1",
    ("/api/v1/accounts/{account_id}", "patch"): "registry_rename_account_v1",
    (
        "/api/v1/accounts/{account_id}/organization",
        "put",
    ): "registry_assign_account_organization_v1",
    (
        "/api/v1/accounts/{account_id}/monitoring",
        "put",
    ): "registry_set_account_monitoring_v1",
    ("/api/v1/accounts/{account_id}/archivals", "post"): "registry_archive_account_v1",
    ("/api/v1/accounts/{account_id}/archival", "delete"): "registry_restore_account_v1",
    ("/api/v1/organizations", "get"): "registry_list_organizations_v1",
    ("/api/v1/organizations", "post"): "registry_create_organization_v1",
    ("/api/v1/organization-orderings", "post"): "registry_reorder_organizations_v1",
    (
        "/api/v1/organizations/{organization_id}/provider-coverage/{provider_key}",
        "get",
    ): "registry_get_organization_coverage_v1",
    (
        "/api/v1/organizations/{organization_id}/provider-coverage/{provider_key}",
        "put",
    ): "registry_set_organization_coverage_v1",
    (
        "/api/v1/organizations/{organization_id}/provider-coverage/{provider_key}",
        "delete",
    ): "registry_revoke_organization_coverage_v1",
    ("/api/v1/organizations/{organization_id}", "get"): "registry_get_organization_v1",
    (
        "/api/v1/organizations/{organization_id}",
        "patch",
    ): "registry_rename_organization_v1",
    (
        "/api/v1/organizations/{organization_id}/archivals",
        "post",
    ): "registry_archive_organization_v1",
    (
        "/api/v1/organizations/{organization_id}/archival",
        "delete",
    ): "registry_restore_organization_v1",
    (
        "/api/v1/provider-installations",
        "get",
    ): "registry_list_provider_installations_v1",
    (
        "/api/v1/providers/{provider_key}/capabilities",
        "get",
    ): "provider_get_capabilities_v1",
    (
        "/api/v1/providers/ollama/local-catalog",
        "get",
    ): "provider_get_ollama_local_catalog_v1",
    (
        "/api/v1/accounts/{account_id}/observed-identity",
        "get",
    ): "provider_get_observed_account_identity_v1",
    (
        "/api/v1/accounts/{account_id}/provider-identity",
        "get",
    ): "provider_get_account_identity_v1",
    (
        "/api/v1/accounts/{account_id}/ollama-cloud-connection",
        "get",
    ): "ollama_cloud_get_connection_v1",
    (
        "/api/v1/accounts/{account_id}/ollama-cloud-connection",
        "post",
    ): "ollama_cloud_initiate_connection_v1",
    ("/api/v1/accounts/{account_id}/connection", "get"): "provider_get_connection_v1",
    (
        "/api/v1/accounts/{account_id}/connection",
        "post",
    ): "provider_start_connection_v1",
    (
        "/api/v1/accounts/{account_id}/connection",
        "delete",
    ): "provider_cancel_connection_v1",
    ("/api/v1/collection-runs", "get"): "collection_list_runs_v1",
    ("/api/v1/accounts/{account_id}/capacity/v2", "get"): "capacity_get_account_v2",
    (
        "/api/v1/accounts/{account_id}/api-capacity",
        "get",
    ): "capacity_get_account_api_budget_v1",
    ("/api/v1/budgets", "get"): "capacity_list_budget_overview_v1",
    ("/api/v1/budgets/{budget_id}", "get"): "capacity_get_budget_v1",
    (
        "/api/v1/accounts/{account_id}/quotas/v2",
        "get",
    ): "capacity_list_quota_windows_v2",
    ("/api/v1/capacity/history/v2", "get"): "capacity_list_history_v2",
    ("/api/v1/accounts/{account_id}/capacity", "get"): "capacity_get_account_v1",
    ("/api/v1/accounts/{account_id}/quotas", "get"): "capacity_list_quota_windows_v1",
    ("/api/v1/capacity/history", "get"): "capacity_list_history_v1",
    ("/api/v1/capacity/scope", "get"): "capacity_get_scope_v1",
    ("/api/v1/capacity/scope/v2", "get"): "capacity_get_scope_v2",
    ("/api/v1/accounts/{account_id}/forecasts", "get"): "capacity_list_forecasts_v1",
    ("/api/v1/processes", "get"): "runtime_list_processes_v1",
    ("/api/v1/process-locations", "get"): "runtime_list_process_locations_v1",
    (
        "/api/v1/process-locations/{association_key}/account",
        "put",
    ): "runtime_set_process_account_association_v1",
    ("/api/v1/process-metrics", "get"): "runtime_list_process_metrics_v1",
    ("/api/v1/sessions", "get"): "runtime_list_sessions_v1",
    ("/api/v1/sessions/{session_id}/tree", "get"): "runtime_get_session_tree_v1",
    ("/api/v1/sessions/{session_id}", "get"): "runtime_get_session_v1",
}

_PREAUTH: tuple[tuple[str, ...], ...] = ()
_COOKIE = (("BrowserSessionCookieV1",),)
_COOKIE_CSRF = (("BrowserSessionCookieV1", "BrowserCsrfHeaderV1"),)
_COOKIE_BEARER = (("BrowserSessionCookieV1",), ("BearerTokenV1",))
_COOKIE_CSRF_BEARER = (
    ("BrowserSessionCookieV1", "BrowserCsrfHeaderV1"),
    ("BearerTokenV1",),
)
_M2_REQUIRED_ERROR_STATUSES = frozenset(
    {
        "400",
        "401",
        "403",
        "404",
        "405",
        "409",
        "412",
        "413",
        "415",
        "422",
        "428",
        "429",
        "500",
        "503",
        "504",
    }
)
# Frozen independent P01 oracle: exactly one record per operation covers
# auth, permission, port, replay, security, success status/model, and problem.
IamPolicyRow = tuple[
    str,
    str,
    str,
    str,
    tuple[tuple[str, ...], ...],
    str,
    str | None,
    str,
    frozenset[str],
    str | None,
]
IAM_POLICY: dict[str, IamPolicyRow] = {
    "alert_list_alerts_v1": (
        "cookie_or_bearer",
        "read:alerts",
        "ListAlertsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AlertPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_list_notifications_v1": (
        "cookie_or_bearer",
        "read:alerts",
        "ListDashboardNotificationsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AlertNotificationPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_get_notification_counts_v1": (
        "cookie_or_bearer",
        "read:alerts",
        "GetDashboardNotificationCountsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AlertNotificationCountsWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_get_alert_v1": (
        "cookie_or_bearer",
        "read:alerts",
        "GetAlertV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AlertWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_list_history_v1": (
        "cookie_or_bearer",
        "read:alerts",
        "ListAlertHistoryV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AlertHistoryPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_acknowledge_v1": (
        "cookie_or_bearer",
        "write:alerts",
        "AcknowledgeAlertV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AlertCommandWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_snooze_v1": (
        "cookie_or_bearer",
        "write:alerts",
        "SnoozeAlertV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AlertCommandWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "SnoozeAlertInputV1",
    ),
    "alert_unsnooze_v1": (
        "cookie_or_bearer",
        "write:alerts",
        "UnsnoozeAlertV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AlertCommandWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_mark_read_v1": (
        "cookie_or_bearer",
        "write:alerts",
        "MarkAlertReadV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AlertCommandWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_list_rules_v1": (
        "cookie_or_bearer",
        "read:alerts",
        "ListAlertRulesV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AlertRulePageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_get_rule_v1": (
        "cookie_or_bearer",
        "read:alerts",
        "GetAlertRuleV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AlertRuleWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "alert_create_rule_v1": (
        "cookie_or_bearer",
        "write:alerts",
        "CreateAlertRuleV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "201",
        "AlertRuleCommandWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "AlertRuleInputV1",
    ),
    "alert_update_rule_v1": (
        "cookie_or_bearer",
        "write:alerts",
        "UpdateAlertRuleV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AlertRuleCommandWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "AlertRuleInputV1",
    ),
    "alert_archive_rule_v1": (
        "cookie_or_bearer",
        "write:alerts",
        "ArchiveAlertRuleOverrideV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AlertRuleCommandWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "operations_get_liveness_v1": (
        "cookie_or_bearer",
        "read:status",
        "GetLivenessV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OperationsLivenessWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "operations_get_readiness_v1": (
        "cookie_or_bearer",
        "read:status",
        "GetReadinessV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OperationsReadinessWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "operations_get_health_v1": (
        "cookie_or_bearer",
        "read:status",
        "GetOperationsHealthV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OperationsHealthWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "operations_get_versions_v1": (
        "cookie_or_bearer",
        "read:status",
        "GetVersionInventoryV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OperationsVersionsWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "operations_get_diagnostics_v1": (
        "cookie_or_bearer",
        "read:status",
        "GetDiagnosticSummaryV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OperationsDiagnosticsWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "runtime_set_process_account_association_v1": (
        "browser_cookie_only",
        "write:accounts",
        "OwnerProcessAccountAssociationsV1.set",
        "replay_safe_representation",
        _COOKIE_CSRF,
        "200",
        "LiveProcessLocationViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "SetProcessAccountAssociationInputV1",
    ),
    "ollama_cloud_get_connection_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "OllamaCloudConnectionPortV1.read",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OllamaCloudConnectionStatusV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "ollama_cloud_initiate_connection_v1": (
        "browser_cookie_only",
        "write:reauth",
        "OllamaCloudConnectionPortV1.initiate",
        "replay_safe_connection_receipt",
        _COOKIE_CSRF,
        "202",
        "OllamaCloudConnectionStatusV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "provider_get_connection_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "ProviderConnectionPortV1.read",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "ProviderConnectionViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "provider_start_connection_v1": (
        "browser_cookie_only",
        "write:reauth",
        "StartProviderConnectionCommandV1",
        "replay_safe_connection_receipt",
        _COOKIE_CSRF,
        "202",
        "ProviderConnectionViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "StartProviderConnectionInputV1",
    ),
    "provider_cancel_connection_v1": (
        "browser_cookie_only",
        "write:reauth",
        "ProviderConnectionPortV1.cancel",
        "cancel_owned_connection",
        _COOKIE_CSRF,
        "200",
        "ProviderConnectionViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "CancelProviderConnectionInputV1",
    ),
    "iam_get_initialization_v1": (
        "preauth_loopback",
        "none",
        "GetIamInitializationStateV1",
        "safe_query_repeat",
        _PREAUTH,
        "200",
        "IamInitializationStateV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "iam_login_v1": (
        "preauth_loopback",
        "none",
        "AuthenticateAdministratorV1",
        "fresh_credential_issue",
        _PREAUTH,
        "204",
        None,
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "LoginInputV1",
    ),
    "iam_get_current_session_v1": (
        "browser_cookie_only",
        "read:self",
        "ResolveBrowserSessionV1",
        "safe_query_repeat",
        _COOKIE,
        "200",
        "CurrentSessionViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "iam_logout_v1": (
        "browser_cookie_only",
        "write:self",
        "LogoutSessionV1",
        "terminal_idempotent_transition",
        _COOKIE_CSRF,
        "204",
        None,
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "iam_change_password_v1": (
        "browser_cookie_only",
        "write:self",
        "ChangeAdministratorPasswordV1",
        "one_time_secret_non_replayable",
        _COOKIE_CSRF,
        "204",
        None,
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "ChangeAdministratorPasswordInputV1",
    ),
    "iam_list_sessions_v1": (
        "browser_cookie_only",
        "write:sessions",
        "ListSessionsV1",
        "safe_query_repeat",
        _COOKIE,
        "200",
        "BrowserSessionPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "iam_revoke_session_v1": (
        "browser_cookie_only",
        "write:sessions",
        "RevokeSessionV1",
        "terminal_idempotent_transition",
        _COOKIE_CSRF,
        "204",
        None,
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "iam_revoke_other_sessions_v1": (
        "browser_cookie_only",
        "write:sessions",
        "RevokeAllSessionsV1",
        "replay_safe_representation",
        _COOKIE_CSRF,
        "200",
        "SessionRevocationSummaryV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "iam_list_api_tokens_v1": (
        "cookie_or_bearer",
        "write:tokens",
        "ListApiTokensV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "ApiTokenPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "iam_create_api_token_v1": (
        "cookie_or_bearer",
        "write:tokens",
        "CreateApiTokenV1",
        "one_time_secret_non_replayable",
        _COOKIE_CSRF_BEARER,
        "201",
        "ApiTokenCredentialIssueV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "CreateApiTokenInputV1",
    ),
    "iam_rotate_api_token_v1": (
        "cookie_or_bearer",
        "write:tokens",
        "RotateApiTokenV1",
        "one_time_secret_non_replayable",
        _COOKIE_CSRF_BEARER,
        "201",
        "ApiTokenCredentialIssueV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "RotateApiTokenInputV1",
    ),
    "iam_revoke_api_token_v1": (
        "cookie_or_bearer",
        "write:tokens",
        "RevokeApiTokenV1",
        "terminal_idempotent_transition",
        _COOKIE_CSRF_BEARER,
        "204",
        None,
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "iam_list_security_events_v1": (
        "cookie_or_bearer",
        "read:diagnostics",
        "ListIamSecurityEventsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "IamSecurityEventPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_list_accounts_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "ListAccountsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AccountPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_list_organizations_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "ListOrganizationsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OrganizationPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_create_organization_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "CreateOrganizationV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "201",
        "OrganizationViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "CreateOrganizationInputV1",
    ),
    "registry_list_organization_coverage_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "OrganizationProviderCoverageReadPortV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OrganizationCoverageSnapshotWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_get_organization_coverage_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "OrganizationProviderCoverageReadPortV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OrganizationCoverageResourceV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_set_organization_coverage_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "OrganizationProviderCoverageWritePortV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "OrganizationCoverageWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "SetOrganizationCoverageInputV1",
    ),
    "registry_revoke_organization_coverage_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "OrganizationProviderCoverageWritePortV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "OrganizationCoverageWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_get_organization_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "GetOrganizationV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OrganizationViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_reorder_organizations_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "ReorderOrganizationsV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "OrganizationOrderingViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "ReorderOrganizationsInputV1",
    ),
    "registry_rename_organization_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "RenameOrganizationV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "OrganizationViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "RenameOrganizationInputV1",
    ),
    "registry_archive_organization_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "ArchiveOrganizationV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "OrganizationViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "ArchiveOrganizationInputV1",
    ),
    "registry_restore_organization_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "RestoreOrganizationV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "OrganizationViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_register_account_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "RegisterAccountV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "201",
        "AccountViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "RegisterAccountInputV1",
    ),
    "registry_get_billing_connections_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "BillingConnectionPortV1.get",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AccountBillingConnectionsV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_create_billing_connection_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "BillingConnectionPortV1.create",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "201",
        "BillingConnectionViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "CreateBillingConnectionInputV1",
    ),
    "registry_get_account_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "GetAccountV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AccountViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_rename_account_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "RenameAccountV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AccountViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "RenameAccountInputV1",
    ),
    "registry_assign_account_organization_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "AssignAccountOrganizationV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AccountViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "AssignAccountOrganizationInputV1",
    ),
    "registry_set_account_monitoring_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "SetAccountMonitoringV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AccountViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "SetAccountMonitoringInputV1",
    ),
    "registry_archive_account_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "ArchiveAccountV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AccountViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "ArchiveAccountInputV1",
    ),
    "registry_restore_account_v1": (
        "cookie_or_bearer",
        "write:accounts",
        "RestoreAccountV1",
        "replay_safe_representation",
        _COOKIE_CSRF_BEARER,
        "200",
        "AccountViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "registry_list_provider_installations_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "ListProviderInstallationsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "ProviderInstallationPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "provider_get_capabilities_v1": (
        "cookie_or_bearer",
        "read:status",
        "GetProviderCapabilitiesV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "ProviderCapabilityDeclarationPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "provider_get_ollama_local_catalog_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "LocalCatalogPortV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "OllamaLocalCatalogViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "provider_get_observed_account_identity_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "GetVerifiedQuotaIdentityV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "ObservedAccountIdentityViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "provider_get_account_identity_v1": (
        "cookie_or_bearer",
        "read:accounts",
        "GetVerifiedQuotaIdentityV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "ProviderAccountIdentityViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "collection_list_runs_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListCollectionRunsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "CollectionRunPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "billing_get_monitoring_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "BillingMonitoringPortV1.get_status",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "BillingMonitoringStatusV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "billing_set_monitoring_v1": (
        "browser_cookie_only",
        "write:accounts",
        "BillingMonitoringPortV1.set_monitoring",
        "replay_safe_representation",
        _COOKIE_CSRF,
        "200",
        "BillingMonitoringResultV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "SetBillingMonitoringInputV1",
    ),
    "billing_get_run_status_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "BillingCheckPortV1.get_status",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "BudgetRunStatusV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "billing_check_connection_v1": (
        "browser_cookie_only",
        "write:accounts",
        "BillingCheckPortV1.check",
        "replay_safe_representation",
        _COOKIE_CSRF,
        "202",
        "BillingCheckRunV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        "BillingCheckInputV1",
    ),
    "capacity_get_budget_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "BudgetSelectedReportPortV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "BudgetSelectedReportWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_list_budget_overview_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "BudgetOverviewPortV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "BudgetOverviewWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_get_account_api_budget_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "AccountBudgetCurrentPortV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AccountBudgetCurrentWireV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_get_account_v2": (
        "cookie_or_bearer",
        "read:telemetry",
        "GetAccountCapacityV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AccountCapacityViewV2",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_list_quota_windows_v2": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListQuotaWindowsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "QuotaWindowPageV2",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_list_history_v2": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListCapacityHistoryV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "CapacityHistoryPageV2",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_get_account_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "GetAccountCapacityV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AccountCapacityViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_list_quota_windows_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListQuotaWindowsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "QuotaWindowPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_get_scope_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "GetCapacityAggregateV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "CapacityScopeViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_get_scope_v2": (
        "cookie_or_bearer",
        "read:telemetry",
        "GetCapacityAggregateV2",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "CapacityScopeViewV2",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_list_forecasts_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListCapacityForecastsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "CapacityForecastPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "capacity_list_history_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListCapacityHistoryV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "CapacityHistoryPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "runtime_list_processes_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListAgentProcessesV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AgentProcessPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "runtime_list_process_locations_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListLiveProcessLocationsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "LiveProcessLocationPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "runtime_list_process_metrics_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListAgentProcessesV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AgentProcessMetricPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "runtime_list_sessions_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "ListAgentSessionsV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AgentSessionPageV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "runtime_get_session_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "GetAgentSessionV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "AgentSessionViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
    "runtime_get_session_tree_v1": (
        "cookie_or_bearer",
        "read:telemetry",
        "GetSessionTreeV1",
        "safe_query_repeat",
        _COOKIE_BEARER,
        "200",
        "SessionTreeViewV1",
        "SafeProblemV1",
        _M2_REQUIRED_ERROR_STATUSES,
        None,
    ),
}


class OpenApiGenerationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class OpenApiGenerationReceiptV1:
    source_hash: str
    openapi_hash: str
    client_hash: str
    generator_hash: str
    generator_name: str
    generator_version: str
    api_major: int
    compatibility: Literal["compatible", "breaking", "not_checked"]
    operation_count: int


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise OpenApiGenerationError("schema_invalid")
    return {key: item for key, item in value.items()}


def validate_openapi(document: object) -> tuple[str, ...]:
    """Validate version, versioned paths, unique operation IDs and responses."""
    schema = _object(document)
    if schema.get("openapi") != "3.1.0":
        raise OpenApiGenerationError("openapi_version_unsupported")
    info = _object(schema.get("info"))
    version = info.get("version")
    if (
        info.get("title") != "AgentMonitor"
        or not isinstance(version, str)
        or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None
    ):
        raise OpenApiGenerationError("api_version_invalid")
    ids: list[str] = []
    for path, item in _object(schema.get("paths")).items():
        if not path.startswith("/api/v1/") or any(char in path for char in "?#\\"):
            raise OpenApiGenerationError("unversioned_path")
        for method, raw_operation in _object(item).items():
            if method not in METHODS:
                raise OpenApiGenerationError("path_item_unsupported")
            operation = _object(raw_operation)
            identifier = operation.get("operationId")
            if (
                not isinstance(identifier, str)
                or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,95}", identifier) is None
            ):
                raise OpenApiGenerationError("operation_id_invalid")
            if identifier in ids:
                raise OpenApiGenerationError("operation_id_duplicate")
            ids.append(identifier)
            responses = _object(operation.get("responses"))
            if not responses or any(
                not _object(value).get("description") for value in responses.values()
            ):
                raise OpenApiGenerationError("responses_invalid")
    return tuple(sorted(ids))


def validate_iam_openapi(document: object) -> tuple[str, ...]:
    """Fail closed if the real M2 route/schema/security graph drifts."""
    identifiers = validate_openapi(document)
    schema = _object(document)
    try:
        OpenAPI.model_validate(schema)
    except ValidationError:
        raise OpenApiGenerationError("openapi_schema_invalid") from None
    components = _object(schema.get("components"))
    models = _object(components.get("schemas"))
    schemes = _object(components.get("securitySchemes"))
    if (
        set(schemes)
        != {
            "BearerTokenV1",
            "BrowserSessionCookieV1",
            "BrowserCsrfHeaderV1",
        }
        or "SafeProblemV1" not in models
    ):
        raise OpenApiGenerationError("security_schema_invalid")
    actual: dict[tuple[str, str], str] = {}
    for path, methods in _object(schema["paths"]).items():
        for method, raw in _object(methods).items():
            operation = _object(raw)
            actual[(path, method)] = str(operation["operationId"])
            if any(
                key not in operation
                for key in (
                    "x-agentmonitor-auth-profile",
                    "x-agentmonitor-required-permission",
                    "x-agentmonitor-application-port",
                    "x-agentmonitor-replay-policy",
                    "x-agentmonitor-error-schema",
                    "security",
                )
            ):
                raise OpenApiGenerationError("operation_policy_missing")
            security = operation["security"]
            if not isinstance(security, list) or any(
                not isinstance(requirement, dict)
                or not set(requirement) <= set(schemes)
                for requirement in security
            ):
                raise OpenApiGenerationError("security_reference_invalid")
            identifier = operation["operationId"]
            policy = IAM_POLICY.get(identifier) if isinstance(identifier, str) else None
            if (
                policy is None
                or (
                    operation["x-agentmonitor-auth-profile"],
                    operation["x-agentmonitor-required-permission"],
                    operation["x-agentmonitor-application-port"],
                    operation["x-agentmonitor-replay-policy"],
                )
                != policy[:4]
            ):
                raise OpenApiGenerationError("operation_policy_mismatch")
            expected_security: list[dict[str, list[str]]] = [
                {name: [] for name in names} for names in policy[4]
            ]
            if (
                security != expected_security
                or operation["x-agentmonitor-error-schema"] != policy[7]
            ):
                raise OpenApiGenerationError("operation_policy_mismatch")
            expected_success = policy[5:7]
            successes = {
                status: response
                for status, response in _object(operation["responses"]).items()
                if status.startswith("2")
            }
            if set(successes) != {expected_success[0]}:
                raise OpenApiGenerationError("success_schema_mismatch")
            error_statuses = {
                status
                for status in _object(operation["responses"])
                if not status.startswith("2")
            }
            if not policy[8] <= error_statuses:
                raise OpenApiGenerationError("error_status_missing")
            request_body = operation.get("requestBody")
            expected_request = policy[9]
            if expected_request is None:
                if request_body is not None:
                    raise OpenApiGenerationError("request_schema_mismatch")
            elif request_body != {
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{expected_request}"}
                    }
                },
                "required": True,
            }:
                raise OpenApiGenerationError("request_schema_mismatch")
            success_response = _object(successes[expected_success[0]])
            model_name = expected_success[1]
            if model_name is None:
                if "content" in success_response:
                    raise OpenApiGenerationError("success_schema_mismatch")
            elif _object(success_response.get("content")) != {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{model_name}"}
                }
            }:
                raise OpenApiGenerationError("success_schema_mismatch")
            for status, response in _object(operation["responses"]).items():
                if not status.startswith("2"):
                    content = _object(_object(response).get("content"))
                    if set(content) != {"application/problem+json"} or _object(
                        content["application/problem+json"]
                    ).get("schema") != {"$ref": f"#/components/schemas/{policy[7]}"}:
                        raise OpenApiGenerationError("problem_media_invalid")
    if (
        actual != IAM_OPERATIONS
        or set(IAM_POLICY) != set(IAM_OPERATIONS.values())
        or len(identifiers) != 87
    ):
        raise OpenApiGenerationError("operation_surface_invalid")

    def visit(value: object) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if reference is not None and (
                not isinstance(reference, str)
                or not reference.startswith("#/components/schemas/")
                or reference.removeprefix("#/components/schemas/") not in models
            ):
                raise OpenApiGenerationError("schema_reference_invalid")
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(schema)
    return identifiers


def classify_compatibility(
    previous: object, current: object
) -> Literal["compatible", "breaking"]:
    """Conservative V1 diff: removals/changes to any old operation are breaking.

    Additions are compatible only at the comparison layer; the bounded compiler
    still refuses unadmitted operations. Source/tool provenance is not API meaning.
    """
    validate_openapi(previous)
    validate_openapi(current)
    old, new = _object(previous), _object(current)

    def compatible_component(old_value: object, new_value: object) -> bool:
        """Permit only additive optional fields on an existing object schema."""
        if old_value == new_value:
            return True
        if not isinstance(old_value, dict) or not isinstance(new_value, dict):
            return False
        old_schema, new_schema = _object(old_value), _object(new_value)
        old_properties = old_schema.get("properties")
        new_properties = new_schema.get("properties")
        if not isinstance(old_properties, dict) or not isinstance(new_properties, dict):
            return False
        if any(
            name not in new_properties or new_properties[name] != definition
            for name, definition in old_properties.items()
        ):
            return False
        if old_schema.get("required", []) != new_schema.get("required", []):
            return False
        return all(
            new_schema.get(key) == value
            for key, value in old_schema.items()
            if key not in {"properties", "required"}
        )

    old_paths, new_paths = _object(old["paths"]), _object(new["paths"])
    for path, item in old_paths.items():
        if path not in new_paths:
            return "breaking"
        for method, operation in _object(item).items():
            if _object(new_paths[path]).get(method) != operation:
                return "breaking"
    first_public_version = not old_paths and "components" not in old
    if not first_public_version:
        old_components = _object(old.get("components", {}))
        new_components = _object(new.get("components", {}))
        for category, old_entries_value in old_components.items():
            new_entries_value = new_components.get(category)
            if isinstance(old_entries_value, dict) and isinstance(
                new_entries_value, dict
            ):
                if any(
                    name not in new_entries_value
                    or (category != "schemas" and new_entries_value[name] != definition)
                    or (
                        category == "schemas"
                        and not compatible_component(
                            definition, new_entries_value[name]
                        )
                    )
                    for name, definition in old_entries_value.items()
                ):
                    return "breaking"
            elif new_entries_value != old_entries_value:
                return "breaking"
        if old.get("security") != new.get("security"):
            return "breaking"
    if (
        str(_object(old["info"])["version"]).split(".")[0]
        != str(_object(new["info"])["version"]).split(".")[0]
    ):
        return "breaking"
    return "compatible"


def _canonical(document: object) -> bytes:
    return (
        json.dumps(
            document, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
        )
        + "\n"
    ).encode("ascii")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_path(path: Path) -> None:
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise OpenApiGenerationError("artifact_path_unsafe")
    if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
        raise OpenApiGenerationError("artifact_path_unsafe")


def _read(path: Path) -> bytes:
    _safe_path(path)
    if path.stat().st_size > 1024 * 1024:
        raise OpenApiGenerationError("artifact_too_large")
    return path.read_bytes()


def _committed_blob(root: Path, relative: Path) -> bytes:
    """Read the approved local HEAD blob, never a mutable working artifact."""
    try:
        repository = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if (
            repository.returncode != 0
            or Path(repository.stdout.strip()).resolve() != root.resolve()
        ):
            raise OpenApiGenerationError("approved_baseline_unavailable")
        blob = subprocess.run(
            ["git", "show", f"HEAD:{relative.as_posix()}"],
            cwd=root,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise OpenApiGenerationError("approved_baseline_unavailable") from None
    if blob.returncode != 0 or not blob.stdout or len(blob.stdout) > 1024 * 1024:
        raise OpenApiGenerationError("approved_baseline_unavailable")
    return blob.stdout


def _verify_existing_generated_pair(
    root: Path, openapi_path: Path, client_path: Path, baseline: bytes
) -> None:
    """Refuse --write if an owner-edited/non-generated draft would be lost."""
    if not openapi_path.exists():
        if client_path.exists():
            raise OpenApiGenerationError("generated_pair_incomplete")
        return
    previous_bytes = _read(openapi_path)
    if previous_bytes == baseline:
        if client_path.exists() and _read(client_path) != _committed_blob(
            root, CLIENT_RELATIVE
        ):
            raise OpenApiGenerationError("generated_artifact_modified")
        return
    try:
        previous = _object(json.loads(previous_bytes))
        provenance = _object(previous.pop("x-agentmonitor-generation"))
    except (ValueError, KeyError, TypeError, OpenApiGenerationError):
        raise OpenApiGenerationError("generation_input_invalid") from None
    if (
        provenance.get("generator") != "agentmonitor-openapi-client"
        or provenance.get("schema_sha256") != _digest(_canonical(previous))
        or not client_path.exists()
    ):
        raise OpenApiGenerationError("generated_artifact_modified")
    client = _read(client_path)
    artifact_hash = _digest(previous_bytes).encode("ascii")
    if (
        not client.startswith(b"// Generated by tooling/foundation/openapi_client.py;")
        or not client.endswith(b"export type ApiClient = typeof apiClient;\n")
        or artifact_hash not in client[:512]
    ):
        raise OpenApiGenerationError("generated_artifact_modified")


def _source_hash(root: Path) -> str:
    return _digest(
        _canonical({name: _digest(_read(root / name)) for name in SOURCE_FILES})
    )


def _typescript(schema: dict[str, object], artifact: bytes) -> bytes:
    validate_iam_openapi(schema)
    provenance = _object(schema["x-agentmonitor-generation"])
    lines = [
        "// Generated by tooling/foundation/openapi_client.py; do not edit.",
        "// AgentMonitor V1 IAM contract. No credential is retained by this client.",
    ]
    exports = {
        "openapiArtifactSha256": _digest(artifact),
        "schemaSha256": provenance["schema_sha256"],
        "sourceSha256": provenance["source_sha256"],
        "generatorSha256": provenance["generator_sha256"],
        "generatorVersion": GENERATOR_VERSION,
        "apiVersion": _object(schema["info"])["version"],
    }
    lines.extend(
        f"export const {name} = {json.dumps(value)} as const;"
        for name, value in exports.items()
    )
    models = _object(_object(schema["components"])["schemas"])
    for name, definition in sorted(models.items()):
        lines.append(f"export type {name} = {_ts_type(definition)};")
    lines += [
        "export type OperationId =",
        *[
            f"  | {json.dumps(identifier)}"
            for identifier in validate_iam_openapi(schema)
        ],
        ";",
        "export type ApiPaths = Readonly<Record<OperationId, string>>;",
        "export type RequestOptionsV1 = Readonly<{",
        "  baseUrl?: string;",
        "  headers?: Readonly<Record<string, string>>;",
        "  credentials?: RequestCredentials;",
        "  signal?: AbortSignal;",
        "}>;",
        "export type ApiResultV1<T> =",
        "  | Readonly<{ ok: true; status: number; data: T; headers: Headers }>",
        (
            "  | Readonly<{ ok: false; status: number; "
            "problem: SafeProblemV1; headers: Headers }>;"
        ),
        "export type OperationRequestMap = Readonly<{",
    ]
    routes: list[tuple[str, str, str, str]] = []
    for (path, method), identifier in sorted(IAM_OPERATIONS.items()):
        operation = _object(_object(_object(schema["paths"])[path])[method])
        request_body = operation.get("requestBody")
        parts: list[str] = []
        if request_body is not None:
            content = _object(_object(request_body)["content"])
            parts.append(
                "body: " + _ts_type(_object(content["application/json"])["schema"])
            )
        placeholders = re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", path)
        if placeholders:
            fields = " ".join(f"{field}: string;" for field in placeholders)
            parts.append("path: Readonly<{ " + fields + " }>")
        parameters = operation.get("parameters", [])
        if not isinstance(parameters, list):
            raise OpenApiGenerationError("parameters_invalid")
        queries: list[str] = []
        for raw_parameter in parameters:
            parameter = _object(raw_parameter)
            if parameter.get("in") == "query":
                parameter_name = parameter.get("name")
                if not isinstance(parameter_name, str) or not re.fullmatch(
                    r"[a-z_]+", parameter_name
                ):
                    raise OpenApiGenerationError("parameters_invalid")
                optional = "" if parameter.get("required") else "?"
                queries.append(
                    f"{parameter_name}{optional}: {_ts_type(parameter['schema'])};"
                )
        if queries:
            parts.append("query?: Readonly<{ " + " ".join(queries) + " }>")
        request_type = (
            "Readonly<{ " + "; ".join(parts) + " }> & RequestOptionsV1"
            if parts
            else "RequestOptionsV1"
        )
        lines.append(f"  {identifier}: {request_type};")
        responses = _object(operation["responses"])
        success = [code for code in responses if code.startswith("2")]
        if len(success) != 1:
            raise OpenApiGenerationError("success_schema_invalid")
        content = _object(_object(responses[success[0]]).get("content", {}))
        if not content:
            response_type = "undefined"
        else:
            response_type = _ts_type(_object(content["application/json"])["schema"])
        routes.append((identifier, method.upper(), path, response_type))
    lines += ["}>;", "export type OperationResponseMap = Readonly<{"]
    for identifier, _method, _path, response_type in routes:
        lines.append(f"  {identifier}: {response_type};")
    lines += [
        "}>;",
        "function isProblem(value: unknown): value is SafeProblemV1 {",
        "  if (typeof value !== 'object' || value === null) return false;",
        "  const record = value as Record<string, unknown>;",
        "  return typeof record.code === 'string' && typeof record.status === 'number'",
        (
            "    && typeof record.correlation_id === 'string' "
            "&& typeof record.title === 'string';"
        ),
        "}",
        (
            "async function send<T>(method: string, template: string, "
            "input: RequestOptionsV1 & {"
        ),
        "  body?: unknown; path?: Readonly<Record<string, string>>;",
        (
            "  query?: Readonly<Record<string, string | number | boolean "
            "| null | undefined>>;"
        ),
        "}): Promise<ApiResultV1<T>> {",
        (
            "  const route = template.replace(/\\{([A-Za-z_][A-Za-z0-9_]*)\\}/g, "
            "(_match, key: string) => {"
        ),
        "    const value = input.path?.[key];",
        "    if (value === undefined) throw new Error('missing_path_parameter');",
        "    return encodeURIComponent(value);",
        "  });",
        "  const query = new URLSearchParams();",
        "  for (const [key, value] of Object.entries(input.query ?? {})) {",
        (
            "    if (value !== undefined && value !== null) "
            "query.append(key, String(value));"
        ),
        "  }",
        "  const suffix = query.size ? `?${query.toString()}` : '';",
        "  const headers: Record<string, string> = { ...(input.headers ?? {}) };",
        "  if (input.body !== undefined) headers['Content-Type'] = 'application/json';",
        "  const bearer = Object.entries(headers).some(([key, value]) =>",
        "    key.toLowerCase() === 'authorization' && value.startsWith('Bearer '));",
        "  if (bearer) for (const key of Object.keys(headers)) {",
        (
            "    if (key.toLowerCase() === 'cookie' || "
            "key.toLowerCase() === 'x-csrf-token') delete headers[key];"
        ),
        "  }",
        "  const response = await fetch(`${input.baseUrl ?? ''}${route}${suffix}`, {",
        (
            "    method, headers, credentials: bearer ? 'omit' : "
            "(input.credentials ?? 'same-origin'),"
        ),
        "    body: input.body === undefined ? undefined : JSON.stringify(input.body),",
        "    signal: input.signal,",
        "  });",
        (
            "  const raw: unknown = response.status === 204 "
            "? undefined : await response.json();"
        ),
        (
            "  if (response.ok) return { ok: true, status: response.status, "
            "data: raw as T, headers: response.headers };"
        ),
        "  if (!isProblem(raw)) throw new Error('invalid_problem_response');",
        (
            "  return { ok: false, status: response.status, "
            "problem: raw, headers: response.headers };"
        ),
        "}",
        "export const operationIds = Object.freeze([",
        *[
            f"  {json.dumps(identifier)},"
            for identifier in validate_iam_openapi(schema)
        ],
        "] as const);",
        "export const apiPaths: ApiPaths = Object.freeze({",
        *[f"  {identifier}: {json.dumps(path)}," for identifier, _, path, _ in routes],
        "});",
        "export const apiClient = Object.freeze({",
    ]
    for identifier, method, path, _ in routes:
        lines.append(
            f"  {identifier}: (input: OperationRequestMap["
            f"{json.dumps(identifier)}]) => "
            f"send<OperationResponseMap[{json.dumps(identifier)}]>("
            f"{json.dumps(method)}, {json.dumps(path)}, input),"
        )
    lines += ["});", "export type ApiClient = typeof apiClient;", ""]
    return "\n".join(lines).encode("ascii")


def _ts_type(value: object) -> str:
    schema = _object(value)
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
        name = reference.removeprefix("#/components/schemas/")
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            return name
    alternatives = schema.get("anyOf")
    if isinstance(alternatives, list) and alternatives:
        return " | ".join(_ts_type(option) for option in alternatives)
    enumeration = schema.get("enum")
    if isinstance(enumeration, list) and enumeration:
        return " | ".join(json.dumps(item) for item in enumeration)
    kind = schema.get("type")
    if kind == "string":
        return "string"
    if kind in {"integer", "number"}:
        return "number"
    if kind == "boolean":
        return "boolean"
    if kind == "null":
        return "null"
    if kind == "array":
        if schema.get("maxItems") == 0:
            return "readonly []"
        return "readonly (" + _ts_type(schema["items"]) + ")[]"
    if kind == "object":
        properties = _object(schema.get("properties", {}))
        required = schema.get("required", [])
        if not isinstance(required, list):
            raise OpenApiGenerationError("typescript_schema_invalid")
        fields = [
            f"{json.dumps(name)}{'?' if name not in required else ''}"
            f": {_ts_type(field)};"
            for name, field in sorted(properties.items())
        ]
        return "Readonly<{ " + " ".join(fields) + " }>"
    raise OpenApiGenerationError("typescript_schema_invalid")


def _atomic(path: Path, contents: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=".agentmonitor-generation-", dir=path.parent
    )
    pending = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        pending.unlink(missing_ok=True)
        raise
    return pending


def _write_pair(outputs: tuple[tuple[Path, bytes], ...]) -> None:
    originals = {path: _read(path) if path.exists() else None for path, _ in outputs}
    pending: list[tuple[Path, Path]] = []
    replaced: list[Path] = []
    try:
        for path, contents in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            pending.append((path, _atomic(path, contents)))
        for path, staged in pending:
            _safe_path(path)
            os.replace(staged, path)
            replaced.append(path)
    except (OSError, OpenApiGenerationError):
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink()
            else:
                os.replace(_atomic(path, original), path)
        raise OpenApiGenerationError("artifact_write_failed") from None
    finally:
        for _, staged in pending:
            staged.unlink(missing_ok=True)


def _generate_openapi_client(
    app_factory_ref: str, openapi_path: Path, client_dir: Path, *, check: bool = False
) -> OpenApiGenerationReceiptV1:
    """Generate only the allocated outputs; --check never creates or writes files."""
    if app_factory_ref != FACTORY_REF:
        raise OpenApiGenerationError("factory_not_approved")
    root = Path(__file__).resolve().parents[2]
    if (
        openapi_path != root / OPENAPI_RELATIVE
        or client_dir != (root / CLIENT_RELATIVE).parent
    ):
        raise OpenApiGenerationError("output_not_allocated")
    client_path = client_dir / "index.ts"
    for path in (openapi_path, client_path):
        _safe_path(path)
    # Fixed static import after validation: never import caller-supplied strings.
    from agentmonitor.composition.bootstrap import create_iam_schema_application

    source_hash = _source_hash(root)
    tool_hash = _digest(_read(Path(__file__)))
    schema = _object(create_iam_schema_application().openapi())
    operations = validate_iam_openapi(schema)
    schema["x-agentmonitor-generation"] = {
        "generator": "agentmonitor-openapi-client",
        "generator_version": GENERATOR_VERSION,
        "generator_sha256": tool_hash,
        "source_sha256": source_hash,
        # Hash excludes this provenance extension to avoid a self-reference.
        "schema_sha256": _digest(_canonical(schema)),
        "api_major": 1,
        "openapi_version": "3.1.0",
        "components": {
            name: importlib.metadata.version(name)
            for name in ("fastapi", "pydantic", "starlette")
        },
    }
    artifact = _canonical(schema)
    # Client source is the canonical artifact, round-tripped through its bytes.
    client = _typescript(_object(json.loads(artifact)), artifact)
    baseline = _committed_blob(root, OPENAPI_RELATIVE)
    compatibility = classify_compatibility(json.loads(baseline), schema)
    if compatibility == "breaking":
        raise OpenApiGenerationError("breaking_drift")
    if not check:
        _verify_existing_generated_pair(root, openapi_path, client_path, baseline)
    if source_hash != _source_hash(root) or tool_hash != _digest(_read(Path(__file__))):
        raise OpenApiGenerationError("generation_source_changed")
    outputs = ((openapi_path, artifact), (client_path, client))
    if check:
        if any(
            not path.exists() or _read(path) != contents for path, contents in outputs
        ):
            raise OpenApiGenerationError("generated_drift")
    else:
        _write_pair(outputs)
    return OpenApiGenerationReceiptV1(
        source_hash,
        _digest(artifact),
        _digest(client),
        tool_hash,
        "agentmonitor-openapi-client",
        GENERATOR_VERSION,
        1,
        compatibility,
        len(operations),
    )


def generate_openapi_client(
    app_factory_ref: str, openapi_path: Path, client_dir: Path, *, check: bool = False
) -> OpenApiGenerationReceiptV1:
    """Typed failure boundary, retaining neither raw paths nor exception chains."""
    code = "generation_failed"
    try:
        return _generate_openapi_client(
            app_factory_ref, openapi_path, client_dir, check=check
        )
    except OpenApiGenerationError as error:
        code = error.code
    except (ValueError, KeyError, TypeError):
        code = "generation_input_invalid"
    except OSError:
        code = "artifact_unavailable"
    except Exception:  # noqa: BLE001 - public boundary returns only a safe code
        code = "generation_failed"
    raise OpenApiGenerationError(code) from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "backend/src"))
    code = "generation_failed"
    try:
        receipt = generate_openapi_client(
            FACTORY_REF,
            root / OPENAPI_RELATIVE,
            (root / CLIENT_RELATIVE).parent,
            check=args.check,
        )
        print(
            json.dumps(
                {
                    "status": "passed",
                    "compatibility": receipt.compatibility,
                    "operations": receipt.operation_count,
                    "openapi_sha256": receipt.openapi_hash,
                },
                sort_keys=True,
            )
        )
        return 0
    except OpenApiGenerationError as error:
        code = error.code
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        pass
    print(json.dumps({"status": "failed", "code": code}, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
