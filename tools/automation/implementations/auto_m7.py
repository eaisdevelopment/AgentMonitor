"""Execute bounded M7 checks without treating a partial slice as milestone proof.

Pure calculations, registry/storage HTTP, retained persistence and bounded
compatibility checks execute real tests. Provider collection and other named
boundaries remain Not Run until their real implementation lands.
No ticket flag, owner-entered result or historical receipt can make them pass.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from tools.automation.implementations.auto_m6_exit import (
    M6ExitErrorV1,
    _temporary_tool_environment,
)
from tools.automation.implementations.m7_exit_receipt import (
    ExitContext,
    TimedCheck,
    build_receipt,
)

ROOT = Path(__file__).resolve().parents[3]
Status = Literal["passed", "failed", "blocked", "not_run"]
Lane = Literal[
    "pure",
    "mutation",
    "registry_metadata",
    "persistence_schema",
    "technical",
    "live",
    "browser",
    "deploy",
    "exit",
]

CREDENTIAL_LIFECYCLE_CHECKS = (
    "retired_binding_used",
    "replacement_binding_used",
    "same_scope",
    "history_retained",
    "retired_entry_absent",
    "replacement_entry_present",
    "service_unchanged",
    "account_unchanged",
    "env_selection_unchanged",
)
CREDENTIAL_LIFECYCLE_ABSENCE_REASONS = frozenset(
    {
        "m7_billing_rotation_history_absent",
        "m7_billing_rotation_receipts_absent",
    }
)


PURE_TARGETS = (
    "backend/tests/providers/pure/test_native_cost_diagnostics.py",
    "tools/automation/tests/test_m7_pool_progress.py",
    "tools/automation/tests/test_m7_exit_receipt.py",
    "tools/automation/tests/test_m7_credential_lifecycle.py",
    "backend/tests/providers/pure/test_native_cost_comparison.py",
    "tools/automation/tests/test_m7_provider_report_selection.py",
    "backend/tests/providers/ollama/pure/test_native_usage_comparison.py",
    "tools/automation/tests/test_m7_ollama_selection.py",
    "tools/automation/tests/test_m7_financial_recovery.py::test_financial_observation_respects_actual_retry_time_without_rewriting_it",
    "tools/automation/tests/test_m7_financial_recovery.py::test_financial_recovery_result_requires_exact_actual_witness",
    "tools/automation/tests/test_m7_financial_recovery.py::test_existing_recovery_and_continuity_accept_exact_installed_revision",
    "backend/tests/live/ollama/test_m7_browser_closed_collection.py::test_prospective_gate_rejects_old_queued_and_manual_runs",
    "backend/tests/live/ollama/test_m7_browser_closed_collection.py::test_quota_progress_requires_new_committed_subscription_facts",
    "backend/tests/live/ollama/test_m7_browser_closed_collection.py::test_quota_progress_requires_new_committed_subscription_facts",
    "tools/automation/tests/test_m7_deploy_observation_selection.py",
    "tools/automation/tests/test_m7_retention_selection.py",
    "backend/tests/capacity/pure/test_budget_retention.py",
    "backend/tests/capacity/pure/test_budget_retention_codec.py",
    "backend/tests/contracts/test_budget_retention_contract.py",
    "tools/automation/tests/test_m7_collection_selection.py",
    "backend/tests/capacity/pure/test_cloud_report_views.py",
    "tools/automation/tests/test_m7_aggregate_selection.py",
    "tools/automation/tests/test_m7_accessibility_selection.py",
    "tools/automation/tests/test_m7_budget_http_selection.py",
    "tools/automation/tests/test_m7_backup_selection.py",
    "tools/automation/tests/test_m7_storage_compatibility_selection.py",
    "backend/tests/unit/composition/test_worker_invocation.py",
    "backend/tests/contracts/test_budget_dispatch.py",
    "backend/tests/contracts/test_cloud_usage_actions.py",
    "backend/tests/contracts/test_budget_pool_projection.py",
    "backend/tests/capacity/pure/test_budget_pool_overview.py",
    "backend/tests/capacity/pure/test_budget_exact_arithmetic.py",
    "backend/tests/capacity/pure/test_budget_money.py",
    "backend/tests/capacity/pure/test_budget_aggregation.py",
    "backend/tests/capacity/pure/test_budget_codec.py",
    "backend/tests/capacity/pure/test_budget_remainder.py",
    "backend/tests/api/pure/test_cloud_model_wire.py",
    "backend/tests/adapters/providers/ollama/api/test_ollama_model_groups.py",
    "backend/tests/capacity/pure/test_budget_commit_policy.py",
    "backend/tests/capacity/pure/test_budget_history_cursor.py",
    "backend/tests/capacity/pure/test_budget_history_contract.py",
    "backend/tests/capacity/pure/test_budget_daily_history.py",
    "backend/tests/capacity/pure/test_budget_daily_costs.py",
    "backend/tests/capacity/pure/test_budget_daily_chart.py",
    "backend/tests/capacity/pure/test_budget_forecast.py",
    "backend/tests/adapters/providers/ollama/api/test_budget_source_evidence_policy.py",
    "backend/tests/adapters/providers/ollama/api/test_usage_quantities.py",
    "backend/tests/capacity/pure/test_budget_history_chart.py",
    "backend/tests/contracts/test_budget_report_contract.py",
    "backend/tests/contracts/test_budget_commit_contract.py",
    "backend/tests/contracts/test_budget_run_contract.py",
    "backend/tests/contracts/test_billing_report_context.py",
    "backend/tests/unit/collection_control/test_billing_budget_context.py",
    "backend/tests/unit/composition/test_billing_captured_intervals.py",
    "backend/tests/contracts/test_cloud_budget_run_contract.py",
    "backend/tests/collection_control/pure/test_budget_run_policy.py",
    "backend/tests/collection_control/pure/test_budget_executor_policy.py",
    "backend/tests/registry/test_billing_access_policy.py",
    "backend/tests/capacity/pure/test_budget_report_selection.py",
    "backend/tests/capacity/pure/test_budget_current_selection.py",
    "backend/tests/contracts/test_budget_current_query.py",
    "backend/tests/contracts/test_budget_source_evidence_dispatch.py",
    "backend/tests/adapters/providers/claude/anthropic_api/test_anthropic_budget_source_evidence_policy.py",
    "backend/tests/adapters/providers/codex/openai_api/test_openai_budget_source_evidence_policy.py",
    "backend/tests/contracts/test_budget_account_query.py",
    "backend/tests/contracts/test_budget_funds_query.py",
    "backend/tests/providers/ollama/pure/test_funds_projection.py",
    "backend/tests/contracts/test_billing_actions.py",
    "backend/tests/contracts/test_billing_schedule.py",
    "backend/tests/capacity/pure/test_budget_collection_context.py",
    "backend/tests/collection_control/pure/test_billing_cooldown.py",
    "backend/tests/contracts/test_anthropic_billing_run.py",
    "backend/tests/contracts/test_openai_billing_run.py",
    "backend/tests/contracts/test_openai_analytics_run.py",
    "backend/tests/adapters/providers/codex/openai_api/test_manifest.py",
    "backend/tests/adapters/providers/claude/anthropic_api/test_anthropic_manifest.py",
    "backend/tests/adapters/providers/claude/anthropic_api/test_analytics_manifest.py",
    "backend/tests/adapters/providers/codex/openai_api/test_openai_usage_manifest.py",
    "backend/tests/adapters/providers/codex/openai_api/test_openai_analytics_manifest.py",
    "backend/tests/adapters/providers/codex/openai_api/test_openai_usage_policies.py",
    "backend/tests/adapters/providers/claude/anthropic_api/test_request_policy.py",
    "backend/tests/adapters/providers/claude/anthropic_api/test_usage_policy.py",
    "backend/tests/capacity/pure/test_budget_account_spend.py",
    "backend/tests/capacity/pure/test_budget_funds_lineage.py",
    "backend/tests/capacity/pure/test_budget_overview.py",
    "backend/tests/capacity/pure/test_budget_overview_subscription.py",
    "backend/tests/capacity/pure/test_budget_overview_sort.py",
    "backend/tests/capacity/pure/test_budget_selected.py",
    "backend/tests/contracts/test_budget_overview_query.py",
    "backend/tests/contracts/test_openapi_optional_query.py",
    "backend/tests/collection_control/pure/test_budget_dispatch_policy.py",
    "backend/tests/collection_control/pure/test_cloud_budget_target_codec.py",
    "backend/tests/collection_control/pure/test_cloud_budget_dispatch_policy.py",
    "backend/tests/collection_control/pure/test_ollama_usage_run.py",
    "backend/tests/collection_control/pure/test_ollama_usage_result.py",
    "backend/tests/collection_control/pure/test_ollama_usage_dispatch.py",
    "backend/tests/providers/ollama/pure/test_usage_manifest.py",
    "backend/tests/api/pure/test_budget_cloud_wire.py",
    "backend/tests/capacity/test_quantity_and_health.py",
)
REGISTRY_METADATA_TARGETS = (
    "backend/tests/contracts/test_registry_financial.py",
    "backend/tests/integration/registry/test_financial_pools.py",
    "backend/tests/integration/api/test_financial_pools_http.py",
    "backend/tests/registry/test_billing_credential_status.py",
    "backend/tests/integration/registry/test_billing_access_empty.py",
    "backend/tests/integration/registry/test_billing_account_intent.py",
    "backend/tests/integration/registry/test_billing_connections.py",
    "backend/tests/integration/registry/test_billing_credential_binding.py",
    "backend/tests/integration/registry/test_billing_reconnect.py",
    "backend/tests/integration/registry/test_billing_disconnect.py",
    "backend/tests/integration/registry/test_billing_local_maintenance.py",
    "backend/tests/integration/registry/test_billing_enrollment_guards.py",
    "backend/tests/registry/test_billing_local_command.py",
    "backend/tests/registry/test_billing_credential_operator.py",
    "backend/tests/integration/api/test_billing_reconnect_http.py",
    "backend/tests/integration/api/test_billing_enrollment_http.py",
)
PRESENTATION_TARGETS = (
    "frontend/tests/pure/setup-evidence.mjs",
    "frontend/tests/pure/account-resource-layout.mjs",
    "frontend/tests/pure/cloud-usage-collect-presentation.mjs",
    "frontend/tests/pure/billing-collect-presentation.mjs",
    "frontend/tests/pure/billing-check-presentation.mjs",
    "frontend/tests/pure/financial-pool-presentation.mjs",
    "frontend/tests/pure/budget-account-presentation.mjs",
    "frontend/tests/pure/financial-read-presentation.mjs",
    "frontend/tests/pure/budget-history-pagination.mjs",
    "frontend/tests/pure/budget-funds-history.mjs",
    "frontend/tests/pure/budget-window-navigation.mjs",
    "frontend/tests/pure/budget-selection.mjs",
    "frontend/src/features/overview/overviewSelection.test.mjs",
    "frontend/src/features/overview/budgetOverviewPresentation.test.mjs",
)
SCHEDULED_COLLECTION_TARGETS = (
    "backend/tests/live/ollama/test_m7_scheduled_collection_lifecycle.py",
)
OLLAMA_NATIVE_COMPARISON_TARGETS = (
    "backend/tests/live/ollama/test_m7_native_usage_comparison.py"
    "::test_one_due_real_usage_read_matches_native_completed_usd",
)
OLLAMA_RETAINED_TARGETS = (
    ("ollama_scheduled_ranges", SCHEDULED_COLLECTION_TARGETS),
    (
        "ollama_current_funds",
        ("backend/tests/live/ollama/test_stored_funds_lineage_live.py",),
    ),
    (
        "ollama_monetary_storage",
        ("backend/tests/live/ollama/test_budget_monetary_persistence.py",),
    ),
    (
        "ollama_source_provenance",
        ("backend/tests/live/ollama/test_budget_source_evidence.py",),
    ),
    (
        "ollama_model_storage",
        ("backend/tests/live/ollama/test_model_report_persistence.py",),
    ),
)
BROWSER_ACCESSIBILITY_TARGETS = (
    "backend/tests/live/ollama/test_m7_accessibility_browser.py",
    "backend/tests/live/ollama/test_m7_native_zoom_browser.py",
)
OWNER_SETUP_RECOVERY_TARGETS = (
    "backend/tests/integration/api/test_billing_setup_network_recovery.py",
)
SOURCE_HISTORY_TARGETS = (
    "backend/tests/integration/api/test_budget_report_discovery_http.py",
    "backend/tests/live/ollama/test_budget_history_http_live.py",
    "backend/tests/live/ollama/test_funds_history_http_live.py",
    "backend/tests/live/ollama/test_budget_monetary_persistence.py",
    "backend/tests/live/ollama/test_budget_source_evidence.py",
    "backend/tests/live/ollama/test_source_history_browser.py",
    "backend/tests/live/ollama/test_budget_history_recovery_browser.py",
    "backend/tests/live/ollama/test_m7_accessibility_browser.py",
    "backend/tests/live/ollama/test_model_history_browser.py",
)

PERSISTED_DISPATCH_TARGETS = (
    "backend/tests/integration/collection_control/"
    "test_budget_dispatch_snapshot_real_metadata.py"
    "::test_real_snapshot_selects_exact_later_run_and_updates_only_its_service_age",
    "backend/tests/integration/collection_control/"
    "test_budget_dispatch_snapshot_real_metadata.py"
    "::test_real_dispatch_service_age_survives_reopen_expiry_and_budget_refusal",
)
COLLECTION_GUARD_TARGETS = (
    "backend/tests/live/ollama/test_expired_subscription_recovery.py",
    "backend/tests/contracts/test_collection_recovery_filter.py",
    "backend/tests/live/ollama/test_recovery_query.py",
    "tools/automation/tests/test_m7_exit_context_live.py",
    "backend/tests/live/billing/test_m7_native_cost_comparison.py::test_native_cost_worker_refuses_before_start",
    "backend/tests/live/billing/test_m7_native_cost_comparison.py::test_native_cost_empty_registry_refuses_without_enrollment",
    "backend/tests/live/ollama/test_m7_native_usage_comparison.py::test_native_comparison_worker_refuses_before_start_without_state_access",
    "backend/tests/live/ollama/test_m7_native_usage_comparison.py::test_native_comparison_namespace_runtime_uses_real_module_paths",
    "tools/automation/tests/test_m7_financial_recovery.py",
    "tools/automation/test_m6_controlled_recovery_interval.py",
    "backend/tests/integration/collection_control/test_cloud_usage_eligibility_real_metadata.py",
    *PERSISTED_DISPATCH_TARGETS,
    "backend/tests/integration/collection_control/test_budget_dispatch_snapshot.py",
    "backend/tests/integration/collection_control/test_cloud_usage_actions_empty.py",
    "backend/tests/integration/collection_control/test_ollama_usage_queue_empty.py",
    "backend/tests/integration/collection_control/test_billing_cooldown_empty.py",
    "backend/tests/integration/collection_control/test_billing_budget_context_empty.py",
    "backend/tests/integration/registry/test_billing_monitoring_status.py",
    "backend/tests/contracts/test_billing_schedule.py",
    "backend/tests/collection_control/pure/test_budget_retry_policy.py",
    "backend/tests/collection_control/pure/test_billing_worker_diagnostic.py",
    "backend/tests/integration/collection_control/test_billing_worker_diagnostic_process.py",
    "backend/tests/live/ollama/test_usage_staging_contention.py",
    "backend/tests/integration/collection_control/test_budget_run_repository_empty.py",
    "backend/tests/integration/collection_control/test_budget_dispatch_empty.py",
    "backend/tests/integration/collection_control/test_billing_action_admission.py",
    "backend/tests/integration/collection_control/test_billing_schedule_empty.py",
    "backend/tests/integration/collection_control/test_billing_worker_entrypoint.py",
    "backend/tests/integration/collection_control/test_billing_worker_supervisor.py",
    "backend/tests/integration/collection_control/test_cloud_budget_repository_empty.py",
)
BUDGET_HTTP_GUARD_TARGETS = (
    "backend/tests/integration/api/test_published_openapi_http.py",
    "backend/tests/integration/api/test_cloud_usage_actions_http.py",
    "backend/tests/integration/capacity/test_budget_billing_collection_context.py",
    "backend/tests/integration/capacity/test_budget_overview_empty.py",
    "backend/tests/integration/api/test_budget_http.py",
    "backend/tests/integration/api/test_budget_overview_http.py",
    "backend/tests/integration/api/test_budget_history_http.py",
    "backend/tests/integration/api/test_budget_report_discovery_http.py",
    "backend/tests/integration/api/test_billing_actions_http.py",
    "backend/tests/integration/api/test_billing_monitoring_http.py",
)
CONFIGURED_INVENTORY_TARGETS = ("backend/tests/live/test_m7_configured_inventory.py",)
RETENTION_INVOCATION_TARGETS = ("backend/tests/live/test_m7_retention_invocation.py",)
TECHNICAL_BOUNDARY_TARGETS: dict[str, tuple[str, ...]] = {
    "registry_http": (
        "backend/tests/integration/api/test_financial_pools_http.py",
        "backend/tests/integration/api/test_billing_enrollment_http.py",
        "backend/tests/integration/api/test_billing_reconnect_http.py",
        "backend/tests/integration/api/test_billing_monitoring_http.py",
        "backend/tests/integration/api/test_billing_actions_http.py",
    ),
    "persistence": (
        "backend/tests/integration/capacity/test_budget_retention_boundary.py",
        "backend/tests/integration/collection_control/test_budget_retention_guard.py",
        "backend/tests/integration/operations/test_budget_retention_checkpoint.py",
        "backend/tests/integration/operations/test_budget_retention_task.py",
        "backend/tests/integration/registry/test_billing_retention_scope.py",
        "backend/tests/live/ollama/test_budget_retention_live.py"
        "::test_genuine_retention_preserves_receipt_and_checkpoint",
        "backend/tests/live/ollama/test_budget_retention_live.py"
        "::test_genuine_monetary_bundle_expires_with_original_receipt",
        "backend/tests/live/ollama/test_budget_retention_live.py"
        "::test_changed_checkpoint_cannot_purge_genuine_facts",
        "backend/tests/live/ollama/test_budget_retention_live.py"
        "::test_real_latest_contexts_survive_without_preserving_every_historical_window",
        "backend/tests/live/ollama/test_budget_retention_live.py"
        "::test_unknown_project_metadata_cannot_be_dropped_by_retention",
        "backend/tests/live/ollama/test_budget_retention_live.py"
        "::test_new_genuine_fact_reference_invalidates_preview_before_purge[current]",
        "backend/tests/live/ollama/test_budget_retention_live.py"
        "::test_new_genuine_fact_reference_invalidates_preview_before_purge[derivation]",
        "backend/tests/integration/capacity/test_budget_report_schema.py",
        "backend/tests/integration/collection_control/test_budget_run_schema.py",
        "backend/tests/integration/capacity/test_budget_repository_empty.py",
        "backend/tests/integration/capacity/test_budget_funds_empty.py",
        "backend/tests/integration/capacity/test_budget_current_empty.py",
        "backend/tests/integration/capacity/test_budget_account_empty.py",
        "backend/tests/live/ollama/test_budget_monetary_persistence.py",
        "backend/tests/live/ollama/test_model_report_persistence.py",
        "backend/tests/live/ollama/test_budget_source_evidence.py",
        "backend/tests/live/ollama/test_budget_daily_history_live.py",
        "backend/tests/live/ollama/test_budget_overview_history_snapshot.py",
    ),
    "compatibility": (
        "backend/tests/persistence/sqlite/migrations/test_m05_budget_retention.py",
        "backend/tests/integration/persistence/test_auto_migrate.py"
        "::test_auto_migrate_retention_preserves_genuine_financial_rows",
        "backend/tests/integration/capacity/test_capacity_schema_chain.py",
        "backend/tests/integration/capacity/test_budget_report_schema.py",
        "backend/tests/integration/api/test_billing_actions_http.py",
        "backend/tests/persistence/sqlite/migrations/test_m05_model_remainder.py",
        "backend/tests/live/ollama/test_model_remainder_migration.py",
        "backend/tests/integration/persistence/test_auto_migrate.py"
        "::test_auto_migrate_retention_preserves_schema_and_verified_backup",
        "tools/automation/tests/test_m6_same_schema_update.py"
        "::test_real_same_schema_dashboard_update_and_finalization[False]",
        "tools/automation/tests/test_m6_same_schema_update.py"
        "::test_real_same_schema_dashboard_update_and_finalization[True]",
        "tools/automation/tests/test_m6_same_schema_update.py"
        "::test_real_same_schema_dashboard_update_and_finalization[candidate]",
    ),
}
TECHNICAL_BOUNDARY_SCOPES = {
    "registry_http": (
        "real IAM/HTTP pool, enrollment, reconnect, monitoring and action guards; "
        "no provider credential verification or full owner-setup claim"
    ),
    "persistence": (
        "real schema/repository/funds/current guards and genuine retained "
        "report/receipt/provenance/history reads; fresh atomic commit and "
        "interrupted-receipt recovery remain separate"
    ),
    "compatibility": (
        "real schema chain, semantic marker/retained-data upgrade, legacy/V2 "
        "billing HTTP and three disposable "
        "same-schema update/recovery cases; no installed upgrade, provider "
        "continuity or deployment acceptance claim"
    ),
}
GUARD_SCOPES = {
    "queued_expiry_history": (
        "genuine stored queued-expiry SQLite and authenticated HTTP reads; "
        "real undispatched claim recovery preserves original intent without new facts; "
        "no provider request or committed-receipt recovery acceptance"
    ),
    "collection_guards": (
        "pure scheduling/retry policy and real no-credential SQLite/worker guards; "
        "no successful provider collection or report commit claim"
    ),
    "budget_http_guards": (
        "real IAM/current-read/Check/status/monitoring HTTP guards without reports; "
        "no populated money, summary, history or browser claim"
    ),
}
REQUIRED_CHECKS: dict[str, tuple[str, ...]] = {
    "pure": ("pure",),
    "mutation": ("mutation",),
    "registry_metadata": ("registry_metadata",),
    "persistence_schema": ("persistence_schema",),
    "technical": (
        "pure",
        "registry_metadata",
        "registry_http",
        "persistence",
        "collection",
        "budget_http",
        "compatibility",
        "mutation",
    ),
    "live": (
        "anthropic",
        "openai",
        "ollama",
        "configured_inventory",
        "retention_invocation",
        "recovery",
    ),
    "browser": ("owner_setup", "overview", "detail_history", "accessibility"),
    "deploy": ("candidate", "backup_recovery", "installed_revision", "continuity"),
    "exit": ("technical", "live", "browser", "deploy"),
}


PROVIDER_REPORT_TARGETS = {
    provider: (
        f"backend/tests/live/{provider}/test_{provider}_budget_reports.py"
        f"::test_{provider}_retained_reports_cover_reviewed_mappings_and_ranges",
    )
    for provider in ("anthropic", "openai")
}


BROWSER_CLOSED_TARGETS = (
    "backend/tests/live/ollama/test_m7_browser_closed_collection.py"
    "::test_new_scheduled_financial_receipt_after_controlled_window_closes",
)
DEPLOY_OBSERVATION_CHECKS = ("candidate", "installed_revision")
RECOVERY_PROOFS = (
    "collection_guards",
    "queued_expiry_history",
    "receipt_recovery",
    "backup_recovery",
)


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One execution result; never contains account, credential or provider data."""

    name: str
    status: Status
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class LaneResult:
    """A scope-bearing result, not an owner-acceptance or publication receipt."""

    lane: str
    status: Status
    checks: tuple[CheckResult, ...]


def evaluate_lane(lane: str, checks: tuple[CheckResult, ...]) -> LaneResult:
    """Require each named boundary once; absent/unexecuted evidence cannot pass."""
    if lane not in REQUIRED_CHECKS:
        raise ValueError("m7_lane_unknown")
    names = tuple(check.name for check in checks)
    required = set(REQUIRED_CHECKS[lane])
    if len(set(names)) != len(names) or set(names) - required:
        return LaneResult(lane, "failed", checks)
    if any(check.status == "failed" for check in checks):
        return LaneResult(lane, "failed", checks)
    if set(names) != required or any(check.status != "passed" for check in checks):
        return LaneResult(lane, "blocked", checks)
    return LaneResult(lane, "passed", checks)


def _run_pytest(
    name: str,
    targets: tuple[str, ...],
    *,
    build: bool = False,
    expected_revision: str | None = None,
) -> CheckResult:
    # Repository-owned pytest node IDs select required real examples separately
    # from naturally absent optional examples in the same source file.
    missing = tuple(
        target for target in targets if not (ROOT / target.partition("::")[0]).is_file()
    )
    if missing:
        # Paths are fixed repository-owned selections, not external input.
        for target in missing:
            print(f"M7 REQUIRED SUITE NOT RUN: {target}", flush=True)
        return CheckResult(name, "not_run", "m7_required_suite_missing")
    command = [
        str(ROOT / "backend/.venv/bin/python"),
        "-m",
        "pytest",
        "-c",
        "backend/pyproject.toml",
        *targets,
        "-q",
        "--tb=short",
        "-p",
        "tools.automation.pytest_no_skip",
    ]
    try:
        with (
            _temporary_tool_environment(),
            TemporaryDirectory(prefix="agentmonitor-m7-pytest-") as run_temp,
        ):
            # Real retained snapshots can be large. Remove passed test copies
            # immediately and this run's remaining copies on every exit path.
            # A private base avoids touching other agents' pytest retention.
            command.extend(
                ["--basetemp", run_temp, "-o", "tmp_path_retention_policy=failed"]
            )
            if build:
                built = subprocess.run(
                    [
                        str(ROOT / "backend/.venv/bin/python"),
                        "tools/automation/implementations/auto_build.py",
                    ],
                    cwd=ROOT,
                    timeout=180,
                    check=False,
                )
                if built.returncode != 0:
                    return CheckResult(name, "failed", "m7_build_failed")
            # Receipt capture permits 1000s readiness, a final 125s owned
            # worker, 121s natural expiry and two 30s reconciliation attempts.
            # Native usage comparison permits 1000s readiness and a 125s worker.
            # These enclosing bounds do not change any collection deadline.
            timeout = (
                # Overview runs multiple real browser cases serially. Its
                # enclosing deadline must cover their existing child deadlines.
                600
                if name == "overview"
                else 300
                if name == "overview_metadata"
                else 1200
                if name
                in {
                    "anthropic_native_comparison",
                    "openai_native_comparison",
                    "ollama_native_comparison",
                }
                else 1500
                if name == "continuity"
                else 1500
                if name == "receipt_recovery"
                # Actual balance eligibility (up to 310s) plus the existing
                # 120s stale-owner proof and ordinary SQLite/HTTP work.
                else 600
                if name == "queued_expiry_history"
                else 180
            )
            environment = os.environ.copy()
            # Pytest's pythonpath setting does not reach its real child processes.
            environment["PYTHONPATH"] = (
                str(ROOT / "backend/src") + os.pathsep + str(ROOT)
            )
            environment.pop("AGENTMONITOR_M7_NATIVE_COMPARISON", None)
            environment.pop("AGENTMONITOR_M7_NATIVE_COST_COMPARISON", None)
            if name == "ollama_native_comparison":
                if (
                    expected_revision is None
                    or re.fullmatch(r"[a-f0-9]{40}", expected_revision) is None
                ):
                    return CheckResult(
                        name, "not_run", "m7_expected_installed_revision_required"
                    )
                environment["AGENTMONITOR_M7_NATIVE_COMPARISON"] = "authorized"
            if name in {"anthropic_native_comparison", "openai_native_comparison"}:
                if (
                    expected_revision is None
                    or re.fullmatch(r"[a-f0-9]{40}", expected_revision) is None
                ):
                    return CheckResult(
                        name, "not_run", "m7_expected_installed_revision_required"
                    )
                environment["AGENTMONITOR_M7_NATIVE_COST_COMPARISON"] = "authorized"
            if expected_revision is not None:
                environment["AGENTMONITOR_M7_EXPECTED_REVISION"] = expected_revision
            result = subprocess.run(
                command, cwd=ROOT, timeout=timeout, check=False, env=environment
            )
    except subprocess.TimeoutExpired:
        return CheckResult(name, "failed", "m7_test_timeout")
    except (OSError, M6ExitErrorV1):
        return CheckResult(name, "blocked", "m7_test_toolchain_unavailable")
    if result.returncode != 0:
        return CheckResult(name, "failed", "m7_tests_failed_or_empty")
    return CheckResult(name, "passed")


def provider_reports_result(
    provider: str,
    retained: CheckResult,
    comparison: CheckResult | None = None,
) -> LaneResult:
    """Require both complete retained coverage and an independent real comparison."""
    if (
        provider not in PROVIDER_REPORT_TARGETS
        or retained.name != provider
        or (
            comparison is not None
            and comparison.name != provider + "_native_comparison"
        )
    ):
        raise ValueError("m7_provider_proof_mismatch")
    comparison = comparison or CheckResult(
        provider + "_native_comparison",
        "not_run",
        "m7_fresh_provider_access_and_source_comparison_required",
    )
    failure = next(
        (
            item
            for state in ("failed", "blocked", "not_run")
            for item in (retained, comparison)
            if item.status == state
        ),
        None,
    )
    summary = CheckResult(
        provider,
        "passed" if failure is None else failure.status,
        None if failure is None else failure.reason_code,
    )
    return LaneResult(
        f"live/{provider}", summary.status, (summary, retained, comparison)
    )


def execute_provider_reports(provider: str, expected: str | None = None) -> LaneResult:
    """One real comparison plus all retained mappings; no credential configuration."""
    retained = _run_pytest(provider, PROVIDER_REPORT_TARGETS[provider])
    print(f"M7 RETAINED REPORTS {provider}: {retained.status.upper()}", flush=True)
    if expected is None:
        return provider_reports_result(provider, retained)
    native = _run_pytest(
        provider + "_native_comparison",
        (
            "backend/tests/live/billing/test_m7_native_cost_comparison.py"
            + "::test_real_native_cost_comparison["
            + provider
            + "]",
        ),
        expected_revision=expected,
    )
    return provider_reports_result(provider, retained, native)


def ollama_retained_result(
    proofs: tuple[CheckResult, ...],
    manual: CheckResult | None = None,
    comparison: CheckResult | None = None,
) -> LaneResult:
    """Retained source integrity is not an independent value or browser comparison."""
    failed = next((proof for proof in proofs if proof.status != "passed"), None)
    if failed is not None:
        summary = CheckResult("ollama", failed.status, failed.reason_code)
        return LaneResult("live/ollama", summary.status, (summary, *proofs))
    if tuple(proof.name for proof in proofs) != tuple(
        name for name, _ in OLLAMA_RETAINED_TARGETS
    ):
        summary = CheckResult(
            "ollama", "not_run", "m7_ollama_retained_checks_incomplete"
        )
        return LaneResult("live/ollama", summary.status, (summary, *proofs))
    comparison = comparison or CheckResult(
        "independent_native_monetary_comparison",
        "not_run",
        "m7_ollama_independent_monetary_comparison_required",
    )
    manual = manual or CheckResult(
        "installed_manual_usage_action",
        "not_run",
        "m7_ollama_manual_browser_evidence_required",
    )
    incomplete = next(
        (
            proof
            for state in ("failed", "blocked", "not_run")
            for proof in (comparison, manual)
            if proof.status == state
        ),
        None,
    )
    summary = (
        CheckResult("ollama", "passed")
        if incomplete is None
        else CheckResult("ollama", incomplete.status, incomplete.reason_code)
    )
    return LaneResult(
        "live/ollama", summary.status, (summary, *proofs, comparison, manual)
    )


def execute_ollama_retained(expected: str | None = None) -> LaneResult:
    """Execute real retained read/copy proofs; never request a provider collection."""
    print(
        "M7 SCOPE: current scheduled self 7/30-day lineage, existing funds lineage, "
        "genuine monetary storage/provenance and retained model-context isolation; "
        "not independent native money comparison or a manual browser action",
        flush=True,
    )
    if expected is not None:
        selected = execute_deploy_observation("candidate", expected)
        if selected.status != "passed":
            summary = CheckResult(
                "ollama", selected.status, selected.checks[0].reason_code
            )
            return LaneResult(
                "live/ollama", summary.status, (summary, *selected.checks)
            )
    proofs: list[CheckResult] = []
    for name, targets in OLLAMA_RETAINED_TARGETS:
        proof = _run_pytest(name, targets)
        proofs.append(proof)
        detail = f" ({proof.reason_code})" if proof.reason_code else ""
        print(f"M7 OLLAMA RETAINED {name}: {proof.status.upper()}{detail}", flush=True)
        if proof.status != "passed":
            return ollama_retained_result(tuple(proofs))
    if expected is not None:
        selected = execute_deploy_observation("candidate", expected)
        if selected.status != "passed":
            summary = CheckResult(
                "ollama", selected.status, selected.checks[0].reason_code
            )
            return LaneResult(
                "live/ollama", summary.status, (summary, *proofs, *selected.checks)
            )
    return ollama_retained_result(tuple(proofs))


def ollama_manual_result(
    returncode: int, payload: object, expected: str
) -> CheckResult:
    """A real single click must finish with the same complete self seven-day report."""
    name = "installed_manual_usage_action"
    failed = CheckResult(name, "failed", "m7_ollama_manual_witness_invalid")
    if re.fullmatch(r"[a-f0-9]{40}", expected) is None:
        return failed
    if not isinstance(payload, dict) or (
        payload.get("record_type") != "agentmonitor.m7_cloud_collect_probe.v1"
        or payload.get("scope") != "one_real_cloud_usage_action"
        or payload.get("range") != "7d"
        or payload.get("usage_scope") != "self"
        or payload.get("grouping") != []
        or type(payload.get("unsafe")) is not int
        or payload["unsafe"] != 0
        or type(payload.get("posts")) is not int
        or payload["posts"] not in (0, 1)
    ):
        return failed
    if returncode == 3 and payload.get("status") == "blocked":
        if payload.get("revision") != expected and not (
            payload.get("revision") is None and payload["posts"] == 0
        ):
            return failed
        reason = payload.get("reason")
        allowed = {
            "authentication_required",
            "browser_unavailable",
            "browser_context_unavailable",
            "active_cloud_resource_required",
            "balance_comparison_unavailable",
            "concurrent_provider_cooldown",
            "cloud_usage_rate_limited",
            "cloud_usage_request_unresolved",
            "cloud_usage_service_unavailable",
            "cloud_usage_credential_required",
            "cloud_usage_monitoring_disabled",
            "cloud_usage_authority_unavailable",
            "cloud_usage_target_unavailable",
            "cloud_usage_interval_unavailable",
        }
        return CheckResult(
            name,
            "blocked",
            reason
            if isinstance(reason, str) and reason in allowed
            else "m7_ollama_manual_unavailable",
        )
    if payload.get("revision") != expected:
        return failed
    if returncode == 1 and payload.get("status") == "failed":
        reason = payload.get("reason")
        allowed_failures = {
            "cloud_collection_partial",
            "cloud_collection_failed",
            "cloud_collection_blocked",
            "cloud_collection_cancelled",
            "cloud_collection_unsupported",
            "cloud_collection_queued",
            "cloud_collection_running",
            "cloud_collection_committing",
            "collected_report_incomplete",
            "cloud_terminal_context_mismatch",
            "cloud_run_context_mismatch",
            "collected_report_context_mismatch",
            "collected_report_not_readable",
            "cloud_collection_not_accepted",
            "cloud_success_report_missing",
            "cloud_action_replayed_or_configured",
            "balance_disappeared_after_usage",
            "balance_not_rendered_after_usage",
            "rendered_summary_unavailable",
            "financial_panel_not_settled",
            "cloud_collect_control_missing",
            "probe_execution_failed",
            "installed_revision_changed",
        }
        return CheckResult(
            name,
            "failed",
            reason
            if isinstance(reason, str) and reason in allowed_failures
            else "m7_ollama_manual_probe_failed",
        )
    checks, run, report = (
        payload.get("checks"),
        payload.get("run"),
        payload.get("report"),
    )
    required = (
        "authentication",
        "controls",
        "eligibility",
        "reload",
        "collection",
        "report",
        "balance_continuity",
    )
    if (
        returncode != 0
        or payload.get("status") != "passed"
        or payload.get("reason") is not None
        or payload["posts"] != 1
        or not isinstance(checks, dict)
        or any(checks.get(key) is not True for key in required)
        or not isinstance(run, dict)
        or not isinstance(report, dict)
        or run.get("state") != "succeeded"
        or report.get("completeness") != "complete"
        or report.get("provider_key") != "ollama"
        or report.get("source_id") != "ollama.cloud.usage.v1"
        or report.get("source_category") != "self_requests_and_cost"
        or report.get("grouping") != []
    ):
        return failed
    for key in ("run_id", "report_id", "account_id", "resource_id"):
        if (
            not isinstance(run.get(key), str)
            or re.fullmatch(r"[A-Za-z0-9_.:@-]{1,128}", run[key]) is None
        ):
            return failed
        if key != "run_id" and report.get(key) != run[key]:
            return failed
    context = run.get("report_context")
    requested, covered = report.get("requested_period"), report.get("covered_period")
    if (
        not isinstance(context, dict)
        or context.get("scope") != "self"
        or context.get("range_key") != "7d"
        or context.get("grouping") != []
        or not isinstance(requested, dict)
        or not isinstance(covered, dict)
    ):
        return failed
    try:
        start, end = (
            datetime.fromisoformat(context[key].replace("Z", "+00:00"))
            for key in ("interval_start", "interval_end")
        )
        if (
            start.utcoffset() != timedelta(0)
            or end.utcoffset() != timedelta(0)
            or end - start != timedelta(days=7)
            or any(
                datetime.fromisoformat(period[edge].replace("Z", "+00:00")) != target
                for period in (requested, covered)
                for edge, target in (("start", start), ("end", end))
            )
        ):
            return failed
    except (KeyError, TypeError, ValueError, AttributeError):
        return failed
    return CheckResult(name, "passed")


def execute_ollama_manual(expected: str | None) -> CheckResult:
    """One invocation and one explicit click; never retry a submitted collection."""
    name = "installed_manual_usage_action"
    if expected is None:
        return CheckResult(name, "not_run", "m7_expected_installed_revision_required")
    try:
        with _temporary_tool_environment():
            # Readiness uses the existing 1000s native-comparison envelope:
            # the real fifteen-minute report allowance plus worker cadence.
            # After its only POST, terminal polling remains bounded at 140s.
            process = subprocess.Popen(
                [
                    "node",
                    "frontend/tests/browser/m7/verify_cloud_collect.mjs",
                    "--collect",
                    "--range=7d",
                    "--expected-revision=" + expected,
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            try:
                output, _ = process.communicate(timeout=1240)
            except subprocess.TimeoutExpired:
                # Close only this probe's tab through its bounded SIGTERM handler.
                # The admitted backend collection and owner processes are untouched.
                process.terminate()
                try:
                    process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=5)
                raise
        payload = json.loads(output) if len(output) <= 65536 else None
        # This probe emits only its closed, credential-free verification schema.
        # Retain its stage and checks so a failed browser action is diagnosable;
        # never print arbitrary browser response bodies or exception messages.
        if (
            isinstance(payload, dict)
            and payload.get("record_type") == "agentmonitor.m7_cloud_collect_probe.v1"
        ):
            print(
                "M7 OLLAMA MANUAL WITNESS: " + json.dumps(payload, sort_keys=True),
                flush=True,
            )
        return ollama_manual_result(process.returncode, payload, expected)
    except subprocess.TimeoutExpired:
        return CheckResult(name, "failed", "m7_ollama_manual_probe_timeout")
    except (OSError, ValueError, M6ExitErrorV1):
        return CheckResult(name, "blocked", "m7_ollama_manual_unavailable")


def execute_ollama(expected: str | None = None) -> LaneResult:
    retained = execute_ollama_retained(expected)
    if (
        retained.checks[0].reason_code
        != "m7_ollama_independent_monetary_comparison_required"
    ):
        return retained
    proofs = retained.checks[1 : 1 + len(OLLAMA_RETAINED_TARGETS)]
    if expected is None:
        native = CheckResult(
            "ollama_native_comparison",
            "not_run",
            "m7_expected_installed_revision_required",
        )
    else:
        print(
            "M7 OLLAMA NATIVE COMPARISON: one actual official usage read; "
            "no retry or budget override",
            flush=True,
        )
        native = _run_pytest(
            "ollama_native_comparison",
            OLLAMA_NATIVE_COMPARISON_TARGETS,
            expected_revision=expected,
        )
    comparison = CheckResult(
        "independent_native_monetary_comparison", native.status, native.reason_code
    )
    # Authentication absence in the UI must not suppress the independent native
    # comparison. Each subcheck runs once and keeps its own nonpass result.
    manual = execute_ollama_manual(expected)
    return ollama_retained_result(proofs, manual, comparison)


def execute_receipt_recovery() -> LaneResult:
    """Recover a genuine commit snapshot without accepting the full recovery lane."""
    result = _run_pytest(
        "receipt_recovery",
        ("backend/tests/live/ollama/test_budget_interrupted_receipt.py",),
    )
    return LaneResult("live/receipt_recovery", result.status, (result,))


def execute_backup_recovery() -> LaneResult:
    """Prove isolated genuine financial restore without changing installed state."""
    result = _run_pytest(
        "backup_recovery",
        ("backend/tests/live/ollama/test_budget_backup_restore.py",),
    )
    return LaneResult("deploy/backup_recovery", result.status, (result,))


def execute_budget_http() -> LaneResult:
    """Verify actual IAM/HTTP reads of retained money, without provider requests."""
    # Keep the existing 180-second boundary for each independent HTTP file.
    # Genuine populated snapshots grow; the combined retained group already
    # needed 172 seconds after being separated from authorization checks.
    groups = (
        ("guards", BUDGET_HTTP_GUARD_TARGETS),
        *(
            ("retained_" + str(index), (target,))
            for index, target in enumerate(
                (
                    "backend/tests/live/ollama/test_budget_history_http_live.py",
                    "backend/tests/live/ollama/test_usage_breakdowns_http_live.py",
                    "backend/tests/live/ollama/test_funds_history_http_live.py",
                    "backend/tests/live/ollama/test_budget_pool_totals_live.py"
                    "::test_genuine_filtered_pool_totals_over_real_iam_http",
                )
            )
        ),
    )
    for label, targets in groups:
        result = _run_pytest("budget_http", targets)
        print(f"M7 HTTP PROOF {label}: {result.status.upper()}", flush=True)
        if result.status != "passed":
            break
    return LaneResult("technical/budget_http", result.status, (result,))


def execute_accessibility() -> LaneResult:
    """Exercise real built keyboard navigation and native Chrome 200% zoom."""
    result = _run_pytest("accessibility", BROWSER_ACCESSIBILITY_TARGETS, build=True)
    return LaneResult("browser/accessibility", result.status, (result,))


def retention_invocation_result() -> LaneResult:
    """Observe installed invocation metadata without running retention manually."""
    result = _run_pytest("retention_invocation", RETENTION_INVOCATION_TARGETS)
    return LaneResult("live/retention_invocation", result.status, (result,))


def configured_inventory_result() -> LaneResult:
    """Read real configured financial resources without collecting from providers."""
    result = _run_pytest("configured_inventory", CONFIGURED_INVENTORY_TARGETS)
    return LaneResult("live/configured_inventory", result.status, (result,))


def technical_target_batches(check: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Keep expensive genuine cases separately bounded without dropping targets."""
    if check not in TECHNICAL_BOUNDARY_TARGETS:
        raise ValueError("m7_selection_invalid")
    targets = TECHNICAL_BOUNDARY_TARGETS[check]
    separate = tuple(
        target
        for target in targets
        if target.startswith(
            "backend/tests/live/ollama/test_budget_retention_live.py::"
        )
        or target.endswith(
            "::test_auto_migrate_retention_preserves_genuine_financial_rows"
        )
    )
    return (
        (
            check + "_mechanics",
            tuple(target for target in targets if target not in separate),
        ),
        *(
            (check + "_retained_" + str(index), (target,))
            for index, target in enumerate(separate)
        ),
    )


def execute_technical_boundary(check: str) -> LaneResult:
    """Run all fixed required cases, each within its existing bounded process."""
    batches = technical_target_batches(check)
    print(f"M7 SCOPE: {TECHNICAL_BOUNDARY_SCOPES[check]}", flush=True)
    proofs: list[CheckResult] = []
    for name, targets in batches:
        result = _run_pytest(name, targets)
        proofs.append(result)
        print(f"M7 PROOF {name}: {result.status.upper()}", flush=True)
        if result.status != "passed":
            summary = CheckResult(check, result.status, result.reason_code)
            return LaneResult(f"technical/{check}", summary.status, (summary, *proofs))
    summary = CheckResult(check, "passed")
    return LaneResult(f"technical/{check}", summary.status, (summary, *proofs))


def execute_guard(check: str) -> LaneResult:
    """Execute one explicit partial boundary without accepting its parent check."""
    targets = {
        "queued_expiry_history": (
            "backend/tests/contracts/test_budget_run_contract.py",
            "backend/tests/live/ollama/test_budget_queued_expiry_history.py",
            "backend/tests/integration/collection_control/test_ollama_usage_queue_real_metadata.py",
        ),
        "collection_guards": COLLECTION_GUARD_TARGETS,
        "budget_http_guards": BUDGET_HTTP_GUARD_TARGETS,
    }
    if check not in targets:
        raise ValueError("m7_selection_invalid")
    print(f"M7 SLICE: {GUARD_SCOPES[check]}", flush=True)
    if check == "collection_guards":
        # The natural-expiry case has its own 175-second internal deadline.
        # Give each real case the existing 180-second enclosing bound instead
        # of adding an independent metadata case to that same timed process.
        regular = tuple(
            target
            for target in targets[check]
            if target not in PERSISTED_DISPATCH_TARGETS
        )
        result = _run_pytest(check, regular)
        for target in PERSISTED_DISPATCH_TARGETS:
            if result.status != "passed":
                break
            result = _run_pytest(check, (target,))
    else:
        result = _run_pytest(check, targets[check])
    reason = f" ({result.reason_code})" if result.reason_code else ""
    print(f"M7 CHECK {check}: {result.status.upper()}{reason}", flush=True)
    return LaneResult(f"technical/{check}", result.status, (result,))


def _presentation_checks() -> CheckResult:
    """Execute actual pure presentation suites, without simulated browser I/O."""
    for target in PRESENTATION_TARGETS:
        if not (ROOT / target).is_file():
            return CheckResult("pure", "not_run", "m7_required_suite_missing")
        try:
            result = subprocess.run(
                ["node", "--experimental-strip-types", target],
                cwd=ROOT,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return CheckResult("pure", "failed", "m7_test_timeout")
        except OSError:
            return CheckResult("pure", "blocked", "m7_test_toolchain_unavailable")
        if result.returncode != 0:
            return CheckResult("pure", "failed", "m7_presentation_test_failed")
    return CheckResult("pure", "passed")


def execute_pool_browser(name: str = "owner_pool_controls") -> LaneResult:
    """Build actual sources and exercise owner metadata with real IAM/SQLite."""
    if name not in {"owner_pool_controls", "source_history"}:
        raise ValueError("m7_selection_invalid")
    status: Status = "passed"
    reason = None
    try:
        with (
            _temporary_tool_environment(),
            TemporaryDirectory(prefix="agentmonitor-m7-browser-") as run_temp,
        ):
            commands = (
                [
                    str(ROOT / "backend/.venv/bin/python"),
                    "tools/automation/implementations/auto_build.py",
                ],
                [
                    str(ROOT / "backend/.venv/bin/python"),
                    *(
                        ["frontend/tests/browser/m7/run_financial_pools.py"]
                        if name == "owner_pool_controls"
                        else [
                            "-m",
                            "pytest",
                            "-c",
                            "backend/pyproject.toml",
                            "-q",
                            "--tb=short",
                            "-p",
                            "tools.automation.pytest_no_skip",
                            "--basetemp",
                            run_temp,
                            "-o",
                            "tmp_path_retention_policy=failed",
                            *SOURCE_HISTORY_TARGETS,
                        ]
                    ),
                ],
            )
            for command in commands:
                result = subprocess.run(command, cwd=ROOT, timeout=480, check=False)
                if result.returncode:
                    status, reason = "failed", "m7_built_browser_failed"
                    break
    except subprocess.TimeoutExpired:
        status, reason = "failed", "m7_test_timeout"
    except (OSError, M6ExitErrorV1):
        status, reason = "blocked", "m7_test_toolchain_unavailable"
    check = CheckResult(name, status, reason)
    print(f"M7 CHECK {name}: {status.upper()}", flush=True)
    return LaneResult(f"browser/{name}", status, (check,))


def required_boundary_check(
    name: str, proof: LaneResult, unmet_reason: str | None = None
) -> CheckResult:
    """Retain the full executor result when mapping it to a required boundary."""
    if proof.status == "passed":
        return CheckResult(
            name, "passed" if unmet_reason is None else "not_run", unmet_reason
        )
    reason = next(
        (check.reason_code for check in proof.checks if check.status == proof.status),
        None,
    )
    return CheckResult(name, proof.status, reason)


def execute_collection_boundary(
    completed: dict[str, LaneResult] | None = None,
) -> CheckResult:
    """Run existing lifecycle proofs without accepting missing current scheduling."""
    completed = {} if completed is None else completed
    for name in ("collection_guards", "queued_expiry_history", "receipt_recovery"):
        proof = completed.get(name) or (
            execute_receipt_recovery()
            if name == "receipt_recovery"
            else execute_guard(name)
        )
        completed[name] = proof
        print(f"M7 COLLECTION PROOF {name}: {proof.status.upper()}", flush=True)
        if proof.status != "passed":
            return required_boundary_check("collection", proof)
    scheduled = _run_pytest("current_scheduling", SCHEDULED_COLLECTION_TARGETS)
    if scheduled.status != "passed":
        return CheckResult("collection", scheduled.status, scheduled.reason_code)
    print(
        "M7 SCOPE: technical collection guards, natural expiry, genuine receipt "
        "recovery and retained scheduled lineage; prospective browser-closed "
        "and cross-provider progress are required separately by deploy/continuity",
        flush=True,
    )
    return CheckResult("collection", "passed")


def financial_recovery_result(
    returncode: int, payload: object, expected: str, attempt: str
) -> CheckResult:
    """Admit only this real worker's closed, exact-revision recovery witness."""
    failed = CheckResult(
        "source_failure_isolation", "failed", "m7_financial_witness_invalid"
    )
    if not isinstance(payload, dict) or (
        payload.get("record_type") != "agentmonitor.m7_financial_recovery.v1"
        or payload.get("source_revision") != expected
        or payload.get("attempt_id") != attempt
        or payload.get("isolation_scope") != "owned_billing_worker_network"
    ):
        return failed
    if returncode == 3 and payload.get("status") in {"blocked", "not_run"}:
        reason = payload.get("reason_code")
        # Codes are from our fixed producer, never provider text or exception data.
        from tools.automation.implementations.m6_controlled_recovery_interval import (
            FINANCIAL_REASONS,
        )

        if not isinstance(reason, str) or reason not in FINANCIAL_REASONS:
            reason = "m7_financial_boundary_unavailable"
        return CheckResult("source_failure_isolation", payload["status"], reason)
    if (
        returncode != 0
        or payload.get("status") != "passed"
        or payload.get("reason_code")
        not in {
            "m7_financial_source_recovered",
            "m7_financial_uncertain_source_recovered",
        }
    ):
        return failed
    if (
        payload.get("namespace_cleanup_confirmed") is not True
        or any(
            type(payload.get(name)) is not int or payload[name] <= 0
            for name in (
                "namespace_pid",
                "namespace_start_ticks",
                "parent_namespace_inode",
                "isolated_namespace_inode",
            )
        )
        or payload["parent_namespace_inode"] == payload["isolated_namespace_inode"]
        or payload.get("failure_run_id") == payload.get("recovery_run_id")
        or payload.get("old_report_id") == payload.get("recovery_report_id")
    ):
        return failed
    for name, pattern in (
        ("service_invocation_id", r"[a-f0-9]{32}"),
        ("old_payload_digest", r"[a-f0-9]{64}"),
        ("recovery_payload_digest", r"[a-f0-9]{64}"),
        *(
            (key, r"[A-Za-z0-9_.:@-]{1,128}")
            for key in (
                "failure_run_id",
                "old_report_id",
                "recovery_run_id",
                "recovery_report_id",
            )
        ),
    ):
        if (
            not isinstance(payload.get(name), str)
            or re.fullmatch(pattern, payload[name]) is None
        ):
            return failed
    others, samples = (
        payload.get("continuity_run_ids"),
        payload.get("dashboard_observed_at"),
    )
    if (
        not isinstance(others, list)
        or not others
        or any(
            not isinstance(item, str)
            or re.fullmatch(r"[A-Za-z0-9_.:@-]{1,128}", item) is None
            for item in others
        )
        or not isinstance(samples, list)
        or len(samples) < 2
    ):
        return failed
    try:
        began, isolated, ended, completed = (
            datetime.fromisoformat(payload[name])
            for name in (
                "started_at",
                "isolation_started_at",
                "isolation_ended_at",
                "completed_at",
            )
        )
        observations = tuple(datetime.fromisoformat(value) for value in samples)
        if payload.get("reason_code") == "m7_financial_uncertain_source_recovered":
            released = datetime.fromisoformat(payload["uncertainty_released_at"])
            retry = datetime.fromisoformat(payload["uncertainty_next_allowed_at"])
            if (
                payload.get("failure_kind") != "outcome_unknown"
                or released.utcoffset() != timedelta(0)
                or retry.utcoffset() != timedelta(0)
                or not ended <= released < retry <= completed
                or retry < released + timedelta(seconds=300)
            ):
                return failed
        if (
            any(
                value.utcoffset() != timedelta(0)
                for value in (began, isolated, ended, completed, *observations)
            )
            or not began <= isolated < ended <= completed
            or not began <= min(observations) <= isolated
            or not ended <= max(observations) <= completed
        ):
            return failed
    except (KeyError, TypeError, ValueError):
        return failed
    return CheckResult(
        "source_failure_isolation",
        "passed",
        "m7_financial_uncertain_source_recovered"
        if payload.get("reason_code") == "m7_financial_uncertain_source_recovered"
        else None,
    )


def execute_financial_recovery(expected: str | None) -> CheckResult:
    if expected is None:
        return CheckResult(
            "source_failure_isolation",
            "not_run",
            "m7_expected_installed_revision_required",
        )
    from tools.automation.implementations.m6_controlled_recovery_interval import (
        FINANCIAL_MAX_SECONDS,
    )

    attempt = uuid.uuid4().hex
    try:
        with _temporary_tool_environment():
            result = subprocess.run(
                [
                    str(ROOT / "backend/.venv/bin/python"),
                    "-m",
                    "tools.automation.implementations.m6_controlled_recovery_interval",
                    "--financial",
                    "--revision",
                    expected,
                    "--attempt-id",
                    attempt,
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                timeout=FINANCIAL_MAX_SECONDS,
                check=False,
            )
        payload = json.loads(result.stdout) if len(result.stdout) <= 32768 else None
        return financial_recovery_result(result.returncode, payload, expected, attempt)
    except subprocess.TimeoutExpired:
        return CheckResult(
            "source_failure_isolation", "failed", "m7_financial_observation_timeout"
        )
    except (OSError, ValueError, M6ExitErrorV1):
        return CheckResult(
            "source_failure_isolation",
            "blocked",
            "m7_financial_observation_unavailable",
        )


def execute_continuity(expected: str | None) -> LaneResult:
    """Observe a real new scheduled receipt after closing our own dashboard window."""
    if expected is None:
        proof = CheckResult(
            "continuity", "not_run", "m7_expected_installed_revision_required"
        )
    else:
        proof = _run_pytest(
            "continuity", BROWSER_CLOSED_TARGETS, expected_revision=expected
        )
    return LaneResult("deploy/continuity", proof.status, (proof,))


def recovery_result(
    proofs: tuple[CheckResult, ...], isolation: CheckResult | None = None
) -> LaneResult:
    """Keep executed proof outcomes and the remaining recovery scope explicit."""
    failed = next((proof for proof in proofs if proof.status != "passed"), None)
    if failed is not None:
        summary = CheckResult("recovery", failed.status, failed.reason_code)
        return LaneResult("live/recovery", summary.status, (summary, *proofs))
    if tuple(proof.name for proof in proofs) != RECOVERY_PROOFS:
        summary = CheckResult("recovery", "not_run", "m7_recovery_proofs_incomplete")
        return LaneResult("live/recovery", summary.status, (summary, *proofs))
    isolation = isolation or CheckResult(
        "source_failure_isolation",
        "not_run",
        "m7_source_failure_isolation_evidence_required",
    )
    summary = CheckResult("recovery", isolation.status, isolation.reason_code)
    unknown_recovered = (
        isolation.status == "passed"
        and isolation.reason_code == "m7_financial_uncertain_source_recovered"
    )
    conditional = CheckResult(
        "uncertain_financial_dispatch",
        "passed" if unknown_recovered else "not_run",
        "m7_genuine_abandoned_financial_dispatch_recovered"
        if unknown_recovered
        else "m7_genuine_abandoned_financial_dispatch_not_observed",
    )
    return LaneResult(
        "live/recovery", summary.status, (summary, *proofs, isolation, conditional)
    )


def execute_recovery(
    expected: str | None = None, completed: dict[str, LaneResult] | None = None
) -> LaneResult:
    """Reuse the finite real recovery proofs; do not infer source failure evidence."""
    proofs: list[CheckResult] = []
    completed = {} if completed is None else completed
    for name in RECOVERY_PROOFS:
        result = completed.get(name) or (
            execute_receipt_recovery()
            if name == "receipt_recovery"
            else execute_backup_recovery()
            if name == "backup_recovery"
            else execute_guard(name)
        )
        completed[name] = result
        proof = required_boundary_check(name, result)
        proofs.append(proof)
        print(f"M7 RECOVERY PROOF {name}: {proof.status.upper()}", flush=True)
        if proof.status != "passed":
            break
    isolation = (
        execute_financial_recovery(expected)
        if all(proof.status == "passed" for proof in proofs)
        else None
    )
    return recovery_result(tuple(proofs), isolation)


def execute_deploy_observation(check: str, expected: str) -> LaneResult:
    """Inspect the sealed selected binary and existing service; never activate it."""
    if (
        check not in DEPLOY_OBSERVATION_CHECKS
        or re.fullmatch(r"[a-f0-9]{40}", expected) is None
    ):
        raise ValueError("m7_selection_invalid")
    from tools.automation.implementations.m6_cutover import (
        _FIXED_DATA,
        _FIXED_EXECUTABLE,
        _FIXED_UNIT,
        _candidate_override,
        _cwd,
        _verify_candidate_runtime,
        _verify_retained_baseline,
    )
    from tools.automation.implementations.m6_cutover_diagnostics import REASONS

    try:
        candidate = Path(_cwd(_FIXED_UNIT))
        revision, build = _verify_retained_baseline(candidate)
        if revision != expected:
            result = CheckResult(check, "failed", "m7_installed_revision_mismatch")
            return LaneResult(f"deploy/{check}", result.status, (result,))
        if check == "installed_revision":
            _verify_candidate_runtime(
                root=_FIXED_DATA,
                unit=_FIXED_UNIT,
                checkout=candidate,
                origin="http://127.0.0.1:43110",
                executable=_FIXED_EXECUTABLE,
                expected_command=_candidate_override(candidate)
                .split("ExecStart=\nExecStart=", 1)[1]
                .strip()
                .split(),
            )
        if _verify_retained_baseline(candidate) != (revision, build) or _cwd(
            _FIXED_UNIT
        ) != str(candidate):
            result = CheckResult(check, "failed", "m7_candidate_changed")
        else:
            result = CheckResult(check, "passed")
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        reason = (
            "m7_" + str(error)
            if str(error) in REASONS
            else "m7_deploy_observation_unavailable"
        )
        result = CheckResult(check, "blocked", reason)
    return LaneResult(f"deploy/{check}", result.status, (result,))


def owner_setup_probe_result(
    returncode: int, payload: object, expected: str
) -> CheckResult:
    """Read-only verified current state cannot certify rotation/removal actions."""
    failed = CheckResult("owner_setup_current", "failed", "m7_owner_setup_probe_failed")
    if not isinstance(payload, dict) or (
        payload.get("record_type") != "agentmonitor.m7_installed_setup_probe.v1"
        or payload.get("expected_revision") != expected
        or type(payload.get("unsafe_requests")) is not int
        or payload["unsafe_requests"] != 0
    ):
        return failed
    if returncode == 3 and payload.get("status") == "blocked":
        reason = payload.get("reason_code")
        allowed = {
            "authentication_required",
            "browser_unavailable",
            "browser_context_unavailable",
            "dashboard_unavailable",
            "revision_unavailable",
            "owner_setup_permission_required",
            "owner_setup_current_evidence_unavailable",
        }
        if payload.get("source_revision") not in {None, expected}:
            return failed
        return CheckResult(
            "owner_setup_current",
            "blocked",
            reason
            if isinstance(reason, str) and reason in allowed
            else "m7_owner_setup_unavailable",
        )
    required = (
        "authentication",
        "revision",
        "overview",
        "setup_form",
        "account_layout",
        "scope_contract",
        "continuity",
        "read_only",
        "credential_stored",
        "connection_verified",
        "monitoring_enabled",
        "retained_report",
    )
    checks = payload.get("checks")
    if (
        returncode != 0
        or payload.get("status") != "passed"
        or payload.get("source_revision") != expected
        or payload.get("reason_code") != "installed_owner_setup_verified"
        or payload.get("evidence_scope") != "current_verified_billing_state"
        or type(payload.get("resources_verified")) is not int
        or payload["resources_verified"] < 1
        or not isinstance(checks, dict)
        or any(checks.get(name) != "passed" for name in required)
    ):
        return failed
    return CheckResult("owner_setup_current", "passed")


def execute_owner_setup_current(expected: str | None) -> CheckResult:
    if expected is None:
        return CheckResult(
            "owner_setup_current", "not_run", "m7_expected_installed_revision_required"
        )
    try:
        with _temporary_tool_environment():
            result = subprocess.run(
                [
                    "node",
                    "frontend/tests/browser/m7/verify_setup.mjs",
                    expected,
                    "--require-connected-billing",
                ],
                cwd=ROOT,
                capture_output=True,
                timeout=180,
                check=False,
            )
        payload = json.loads(result.stdout) if len(result.stdout) <= 32768 else None
        return owner_setup_probe_result(result.returncode, payload, expected)
    except subprocess.TimeoutExpired:
        return CheckResult(
            "owner_setup_current", "failed", "m7_owner_setup_probe_timeout"
        )
    except (OSError, ValueError, M6ExitErrorV1):
        return CheckResult(
            "owner_setup_current", "blocked", "m7_owner_setup_unavailable"
        )


def credential_lifecycle_result(
    returncode: int, payload: object, expected: str
) -> CheckResult:
    """Admit a real passive lifecycle witness, never logical status alone."""

    name = "credential_rotation_removal"
    failed = CheckResult(name, "failed", "m7_credential_lifecycle_proof_invalid")
    if (
        re.fullmatch("[a-f0-9]{40}", expected) is None
        or not isinstance(payload, dict)
        or payload.get("record_type") != "agentmonitor.m7_credential_lifecycle.v1"
        or payload.get("evidence_scope")
        != "one_real_billing_rotation_and_local_removal"
        or payload.get("source_revision") != expected
        or payload.get("provider_key_revocation_claimed") is not False
        or payload.get("distinct_key_content_claimed") is not False
        or payload.get("command_provenance_claimed") is not False
    ):
        return failed
    reason = payload.get("reason_code")
    if returncode == 3 and payload.get("status") == "not_run":
        if isinstance(reason, str) and reason in CREDENTIAL_LIFECYCLE_ABSENCE_REASONS:
            return CheckResult(name, "not_run", reason)
        return failed
    if returncode == 3 and payload.get("status") == "blocked":
        allowed = {
            "m7_lifecycle_account_changed",
            "m7_lifecycle_cursor_invalid",
            "m7_lifecycle_env_selection_changed",
            "m7_lifecycle_installed_revision_mismatch",
            "m7_lifecycle_inventory_unavailable",
            "m7_lifecycle_lineage_changed",
            "m7_lifecycle_lineage_invalid",
            "m7_lifecycle_observation_unavailable",
            "m7_lifecycle_replacement_entry_absent",
            "m7_lifecycle_retired_entry_present",
            "m7_lifecycle_revision_invalid",
            "m7_lifecycle_scan_limit",
            "m7_lifecycle_seal_invalid",
            "m7_lifecycle_service_changed",
            "m7_lifecycle_service_unavailable",
        }
        if isinstance(reason, str) and reason in allowed:
            return CheckResult(name, "blocked", reason)
        return failed
    checks = payload.get("checks")
    digest = payload.get("proof_digest")
    if (
        returncode != 0
        or payload.get("status") != "passed"
        or reason is not None
        or payload.get("provider") not in {"claude", "codex"}
        or not isinstance(digest, str)
        or re.fullmatch("[a-f0-9]{64}", digest) is None
        or not isinstance(checks, dict)
        or set(checks) != set(CREDENTIAL_LIFECYCLE_CHECKS)
        or any(checks.get(key) is not True for key in CREDENTIAL_LIFECYCLE_CHECKS)
    ):
        return failed
    return CheckResult(name, "passed")


def execute_credential_lifecycle(expected: str | None) -> CheckResult:
    """Inspect genuine history and managed entry names without owner mutations."""
    if expected is None:
        return CheckResult(
            "credential_rotation_removal",
            "not_run",
            "m7_expected_installed_revision_required",
        )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "backend/src") + os.pathsep + str(ROOT)
    try:
        with _temporary_tool_environment():
            result = subprocess.run(
                [
                    str(ROOT / "backend/.venv/bin/python"),
                    "-m",
                    "tools.automation.implementations.m7_credential_lifecycle",
                    "--expected-revision",
                    expected,
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                timeout=120,
                check=False,
            )
        if result.stderr or len(result.stdout) > 16384:
            return CheckResult(
                "credential_rotation_removal",
                "failed",
                "m7_credential_lifecycle_proof_invalid",
            )
        return credential_lifecycle_result(
            result.returncode, json.loads(result.stdout), expected
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            "credential_rotation_removal", "blocked", "m7_lifecycle_scan_limit"
        )
    except (OSError, ValueError, M6ExitErrorV1):
        return CheckResult(
            "credential_rotation_removal",
            "blocked",
            "m7_lifecycle_observation_unavailable",
        )


def execute_lane(
    lane: str,
    expected_revision: str | None = None,
    *,
    completed_proofs: dict[str, LaneResult] | None = None,
    observations: list[TimedCheck] | None = None,
) -> LaneResult:
    """Run implemented boundaries; report the rest without inventing evidence."""
    if lane not in REQUIRED_CHECKS:
        raise ValueError("m7_lane_unknown")
    completed_proofs = {} if completed_proofs is None else completed_proofs
    checks: list[CheckResult] = []
    for name in REQUIRED_CHECKS[lane]:
        started_at = datetime.now(UTC)
        if name == "pure":
            check = _run_pytest("pure", PURE_TARGETS)
            if check.status == "passed":
                check = _presentation_checks()
        elif name == "mutation":
            check = _run_pytest(
                "mutation", ("tools/automation/test_m7_budget_mutation_policies.py",)
            )
        elif name == "registry_metadata":
            print(
                "M7 SLICE: account intent, connection metadata and nonsecret binding "
                "lifecycle over real SQLite/HTTP; secret entry, "
                "credential verification "
                "and full registry flow remain separate",
                flush=True,
            )
            check = _run_pytest("registry_metadata", REGISTRY_METADATA_TARGETS)
        elif name == "persistence_schema":
            check = _run_pytest(
                name,
                (
                    "backend/tests/integration/capacity/test_budget_report_schema.py",
                    "backend/tests/integration/collection_control/test_budget_run_schema.py",
                    "backend/tests/integration/collection_control/test_budget_run_repository_empty.py",
                    "backend/tests/integration/capacity/test_capacity_schema_chain.py",
                    "backend/tests/integration/capacity/test_budget_repository_empty.py",
                    "backend/tests/integration/capacity/test_budget_current_empty.py",
                    "backend/tests/integration/capacity/test_budget_account_empty.py",
                ),
            )
        elif lane == "deploy" and name in DEPLOY_OBSERVATION_CHECKS:
            check = (
                CheckResult(name, "not_run", "m7_expected_installed_revision_required")
                if expected_revision is None
                else execute_deploy_observation(name, expected_revision).checks[0]
            )
        elif lane == "deploy" and name == "continuity":
            check = execute_continuity(expected_revision).checks[0]
        elif lane == "live" and name == "recovery":
            check = execute_recovery(expected_revision, completed_proofs).checks[0]
        elif lane == "live" and name == "ollama":
            retained = execute_ollama(expected_revision)
            check = retained.checks[0]
            for boundary in retained.checks[1:]:
                detail = f" ({boundary.reason_code})" if boundary.reason_code else ""
                print(
                    f"M7 OLLAMA BOUNDARY {boundary.name}: "
                    f"{boundary.status.upper()}{detail}",
                    flush=True,
                )
        elif lane == "deploy" and name == "backup_recovery":
            backup = (
                completed_proofs.get("backup_recovery") or execute_backup_recovery()
            )
            completed_proofs["backup_recovery"] = backup
            check = backup.checks[0]
        elif lane == "technical" and name == "budget_http":
            check = execute_budget_http().checks[0]
        elif lane == "technical" and name in TECHNICAL_BOUNDARY_TARGETS:
            check = execute_technical_boundary(name).checks[0]
        elif lane == "technical" and name == "collection":
            check = execute_collection_boundary(completed_proofs)
        elif lane == "live" and name == "configured_inventory":
            check = _run_pytest(name, CONFIGURED_INVENTORY_TARGETS)
        elif lane == "live" and name == "retention_invocation":
            check = retention_invocation_result().checks[0]
        elif lane == "live" and name in PROVIDER_REPORT_TARGETS:
            check = execute_provider_reports(name, expected_revision).checks[0]
        elif lane == "browser" and name == "overview":
            check = (
                CheckResult(name, "not_run", "m7_expected_installed_revision_required")
                if expected_revision is None
                else required_boundary_check(
                    name, execute_overview_browser(expected_revision)
                )
            )
        elif lane == "browser" and name == "detail_history":
            check = required_boundary_check(
                name,
                execute_pool_browser("source_history"),
            )
        elif lane == "browser" and name == "accessibility":
            check = execute_accessibility().checks[0]
        elif lane == "browser" and name == "owner_setup":
            proof = execute_pool_browser()
            if proof.status == "passed":
                transport = _run_pytest(
                    "owner_setup_recovery", OWNER_SETUP_RECOVERY_TARGETS, build=True
                )
                proof = LaneResult(
                    "browser/owner_setup_recovery", transport.status, (transport,)
                )
            if proof.status == "passed":
                current = execute_owner_setup_current(expected_revision)
                proof = LaneResult(
                    "browser/owner_setup_current", current.status, (current,)
                )
            if proof.status == "passed":
                lifecycle = execute_credential_lifecycle(expected_revision)
                proof = LaneResult(
                    "browser/credential_rotation_removal",
                    lifecycle.status,
                    (lifecycle,),
                )
            check = required_boundary_check(name, proof)
        elif lane == "exit":
            child = execute_lane(
                name,
                expected_revision=expected_revision,
                completed_proofs=completed_proofs,
                observations=observations,
            )
            check = CheckResult(name, child.status)
        else:
            check = CheckResult(name, "not_run", "m7_boundary_runner_not_implemented")
        checks.append(check)
        if observations is not None:
            observations.append(
                TimedCheck(
                    lane,
                    name,
                    check.status,
                    check.reason_code,
                    started_at,
                    datetime.now(UTC),
                )
            )
        reason = f" ({check.reason_code})" if check.reason_code else ""
        print(f"M7 CHECK {name}: {check.status.upper()}{reason}", flush=True)
    return evaluate_lane(lane, tuple(checks))


def monetary_probe_result(
    returncode: int, payload: object, expected: str
) -> CheckResult:
    """Admit the exact monetary journey, not a generic funds/counts-only pass."""
    failed = CheckResult("monetary_journey", "failed", "m7_monetary_probe_failed")
    if (
        not isinstance(payload, dict)
        or payload.get("record_type") != "agentmonitor.m7_overview_probe.v1"
        or type(payload.get("unsafe_requests")) is not int
        or payload["unsafe_requests"] != 0
    ):
        return failed
    if (
        returncode == 3
        and payload.get("status") == "blocked"
        and payload.get("reason_code") == "authentication_required"
        and payload.get("source_revision") is None
    ):
        return CheckResult("monetary_journey", "blocked", "authentication_required")
    if payload.get("source_revision") != expected:
        return failed
    if returncode == 3 and payload.get("status") == "blocked":
        reason = payload.get("reason_code")
        return CheckResult(
            "monetary_journey",
            "blocked",
            reason
            if reason
            in {
                "genuine_complete_monetary_report_required",
                "monetary_selection_unavailable",
                "authentication_required",
                "comparison_source_unavailable",
            }
            else "m7_monetary_probe_unavailable",
        )
    checks = payload.get("checks")
    required = (
        "monetary",
        "authentication",
        "overview",
        "filters",
        "navigation",
        "financial_entry",
        "source_history",
        "history_windows",
        "responsive",
        "pool_controls",
        "read_only",
    )
    if (
        returncode != 0
        or payload.get("status") != "passed"
        or payload.get("reason_code")
        != "real_monetary_overview_detail_history_verified"
        or not isinstance(checks, dict)
        or any(checks.get(name) != "passed" for name in required)
    ):
        return failed
    return CheckResult("monetary_journey", "passed")


def execute_monetary_browser(expected: str) -> CheckResult:
    """Read actual installed money; retain failure without emitting raw output."""
    try:
        result = subprocess.run(
            [
                "node",
                "frontend/tests/browser/m7/verify_overview.mjs",
                "--require-money",
            ],
            cwd=ROOT,
            timeout=200,
            capture_output=True,
            check=False,
        )
        if result.stderr or len(result.stdout) > 16384:
            return CheckResult("monetary_journey", "failed", "m7_probe_output_invalid")
        payload = json.loads(result.stdout)
        if (
            isinstance(payload, dict)
            and payload.get("record_type") == "agentmonitor.m7_overview_probe.v1"
        ):
            # The probe supplies closed stage/status diagnostics, not financial
            # values, page text, credentials or raw exception messages.
            print(
                "M7 MONETARY BROWSER WITNESS: " + json.dumps(payload, sort_keys=True),
                flush=True,
            )
        return monetary_probe_result(result.returncode, payload, expected)
    except (ValueError, UnicodeError):
        return CheckResult("monetary_journey", "failed", "m7_probe_output_invalid")
    except subprocess.TimeoutExpired:
        return CheckResult("monetary_journey", "failed", "m7_browser_timeout")
    except OSError:
        return CheckResult(
            "monetary_journey", "blocked", "m7_browser_toolchain_unavailable"
        )


def execute_overview_browser(expected: str) -> LaneResult:
    """Verify retained money, available pool totals and installed concurrent reads."""
    metadata = _run_pytest(
        "overview_metadata",
        (
            "backend/tests/integration/capacity/test_budget_overview_real_metadata.py",
            "backend/tests/live/ollama/test_budget_read_efficiency.py",
            "backend/tests/live/billing/test_latest_source_read_efficiency.py",
            "backend/tests/live/ollama/test_budget_overview_live.py",
            "backend/tests/live/ollama/test_budget_overview_history_snapshot.py",
            "backend/tests/live/ollama/test_budget_history_http_live.py",
            "backend/tests/live/ollama/test_funds_history_http_live.py",
            "backend/tests/live/ollama/test_budget_monetary_persistence.py",
        ),
    )
    print(
        f"M7 CHECK overview_metadata: {metadata.status.upper()}"
        + (f" ({metadata.reason_code})" if metadata.reason_code else ""),
        flush=True,
    )
    if metadata.status != "passed":
        return LaneResult("browser/overview", metadata.status, (metadata,))
    status: Status = "blocked"
    reason = "m7_browser_toolchain_unavailable"
    try:
        result = subprocess.run(
            [
                "node",
                "frontend/tests/browser/m7/verify_overview_concurrency.mjs",
                expected,
            ],
            cwd=ROOT,
            timeout=200,
            check=False,
        )
        statuses: dict[int, Status] = {0: "passed", 3: "blocked"}
        status = statuses.get(result.returncode, "failed")
        reason = "m7_concurrent_overview_reads"
    except subprocess.TimeoutExpired:
        status, reason = "failed", "m7_browser_timeout"
    except OSError:
        pass
    concurrent = CheckResult("overview_concurrency", status, reason)
    monetary = execute_monetary_browser(expected)
    # Verify all available genuine contexts, including money beyond page one,
    # isolated shared-pool attribution and exact API/DOM sums. Extra populated
    # examples are separate conditional evidence, not an owner-spend requirement.
    full = _run_pytest(
        "overview",
        (
            "backend/tests/live/ollama/test_budget_pool_totals_live.py"
            "::test_genuine_available_filtered_pool_totals",
            "backend/tests/live/ollama/test_budget_pool_totals_live.py"
            "::test_genuine_pool_totals_built_browser[all_phases]",
            "backend/tests/live/ollama/test_session_hierarchy_browser.py",
            "backend/tests/live/ollama/test_quota_progress_browser.py",
            "backend/tests/live/ollama/test_budget_overview_registry_race_browser.py",
        ),
        build=True,
    )
    print(f"M7 CHECK overview_concurrency: {status.upper()}", flush=True)
    print(
        f"M7 CHECK monetary_journey: {monetary.status.upper()}"
        + (f" ({monetary.reason_code})" if monetary.reason_code else ""),
        flush=True,
    )
    print(
        f"M7 CHECK overview: {full.status.upper()}"
        + (f" ({full.reason_code})" if full.reason_code else ""),
        flush=True,
    )
    outcomes = (status, monetary.status, full.status)
    return LaneResult(
        "browser/overview",
        "failed"
        if "failed" in outcomes
        else "blocked"
        if "blocked" in outcomes
        else "passed"
        if all(outcome == "passed" for outcome in outcomes)
        else "not_run",
        (metadata, concurrent, monetary, full),
    )


def validate_selection(lane: str, check: str | None, expected: str | None) -> None:
    """Keep partial technical guards separate from exact-revision activation."""
    if check is None and expected is None:
        return
    if (
        check is None
        and lane in {"browser", "deploy", "exit", "live"}
        and expected is not None
        and re.fullmatch(r"[a-f0-9]{40}", expected) is not None
    ):
        return
    if (
        lane == "browser"
        and check in {"owner_pool_controls", "source_history", "accessibility"}
        and expected is None
    ):
        return
    if (
        lane == "browser"
        and check == "overview"
        and expected is not None
        and re.fullmatch(r"[a-f0-9]{40}", expected) is not None
    ):
        return
    if (
        lane == "deploy"
        and check in DEPLOY_OBSERVATION_CHECKS
        and expected is not None
        and re.fullmatch(r"[a-f0-9]{40}", expected) is not None
    ):
        return
    if (
        (lane == "live" and check in {"recovery", "ollama"})
        or (lane == "deploy" and check == "continuity")
    ) and (expected is None or re.fullmatch(r"[a-f0-9]{40}", expected) is not None):
        return
    if lane == "deploy" and check == "backup_recovery" and expected is None:
        return
    if (
        lane == "live"
        and check in PROVIDER_REPORT_TARGETS
        and (expected is None or re.fullmatch(r"[a-f0-9]{40}", expected) is not None)
    ):
        return
    if (
        lane == "live"
        and check in {"configured_inventory", "retention_invocation"}
        and expected is None
    ):
        return
    if lane == "live" and check == "receipt_recovery" and expected is None:
        return
    if lane == "technical" and check == "budget_http" and expected is None:
        return
    if lane == "technical" and check in TECHNICAL_BOUNDARY_TARGETS and expected is None:
        return
    if lane == "technical" and check in GUARD_SCOPES and expected is None:
        return
    if (
        lane != "deploy"
        or check
        not in {
            "setup_activation",
            "financial_activation",
            "model_activation",
            "retention_activation",
        }
        or expected is None
        or re.fullmatch(r"[a-f0-9]{40}", expected) is None
    ):
        raise ValueError("m7_selection_invalid")


def selected_setup_revision(controller: Path, expected: str) -> str:
    """Observe the selected revision from real Git, without installed actions."""
    from tools.automation.implementations.m6_frontend_build import _clean_revision

    if (
        re.fullmatch(r"[a-f0-9]{40}", expected) is None
        or not controller.is_absolute()
        or controller.resolve() != controller
    ):
        raise RuntimeError("m7_setup_controller_invalid")
    revision = _clean_revision(controller)
    if revision != expected:
        raise RuntimeError("m7_setup_revision_mismatch")
    return revision


def verify_setup_controller(controller: Path, expected: str) -> None:
    """Require the existing fixed retained-release seal before service access."""
    from tools.automation.implementations.m6_cutover import (
        _FIXED_RELEASES,
        _verify_retained_baseline,
    )

    selected_setup_revision(controller, expected)
    if controller.parent != _FIXED_RELEASES:
        raise RuntimeError("m7_setup_controller_not_retained")
    revision, _ = _verify_retained_baseline(controller)
    if revision != expected:
        raise RuntimeError("m7_setup_revision_mismatch")


def setup_activation_result(
    checks: tuple[CheckResult, ...],
    *,
    financial: bool = False,
    model: bool = False,
    retention: bool = False,
) -> LaneResult:
    """Operational readiness alone cannot accept installed product workflows."""
    remaining = tuple(
        CheckResult(name, "not_run", "m7_separate_real_evidence_required")
        for name in (
            "authenticated_financial"
            if financial or model or retention
            else "authenticated_setup",
            "collector_continuity",
            "backup_recovery",
        )
    )
    return LaneResult(
        "deploy/retention_activation"
        if retention
        else "deploy/model_activation"
        if model
        else "deploy/financial_activation"
        if financial
        else "deploy/setup_activation",
        "failed" if any(check.status == "failed" for check in checks) else "blocked",
        checks + remaining,
    )


def closed_setup_command_reason(output: bytes) -> str:
    """Expose only exact known wrapper messages as fixed codes, never raw output."""
    from tools.automation.implementations.m6_cutover_diagnostics import (
        parse_cutover_failure_message,
    )

    detail = parse_cutover_failure_message(output)
    if detail is not None:
        phase, reason = detail
        return "m7_cutover_" + phase + "_" + reason
    messages = {
        "M6 CUTOVER: BLOCKED — review the transition journal and service state": (
            "m7_setup_cutover_journal_review"
        ),
        (
            "M6 CANDIDATE FINALIZE: BLOCKED — "
            "review the transition journal and service state"
        ): ("m7_setup_finalize_journal_review"),
        "M6 CUTOVER: BLOCKED — expected checkout revision does not match": (
            "m7_setup_revision_mismatch"
        ),
        "M6 CUTOVER: BLOCKED — operator checkout or runtime unavailable": (
            "m7_setup_runtime_unavailable"
        ),
        "M6 CANDIDATE FINALIZE: BLOCKED — operator checkout or runtime unavailable": (
            "m7_setup_runtime_unavailable"
        ),
        "M6 CUTOVER: BLOCKED — private runtime unavailable": (
            "m7_setup_runtime_unavailable"
        ),
        "M6 CANDIDATE FINALIZE: BLOCKED — private runtime unavailable": (
            "m7_setup_runtime_unavailable"
        ),
    }
    return {key.encode(): value for key, value in messages.items()}.get(
        output.strip(), "m7_setup_command_failed"
    )


def _setup_process(arguments: list[str], *, timeout: int) -> None:
    """Run fixed owned code with no inherited credentials or captured output leaks."""
    from tools.automation.implementations.m6_cutover import _FIXED_VENV

    completed = subprocess.run(
        [str(_FIXED_VENV / "bin/python"), "-B", *arguments],
        cwd=ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/dev",
            "LANG": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT / "backend/src") + os.pathsep + str(ROOT),
        },
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if len(completed.stdout) > 16384:
        raise RuntimeError("m7_setup_command_failed")
    if completed.returncode:
        raise RuntimeError(closed_setup_command_reason(completed.stdout))
    if "agentmonitor.composition.billing_credential_operator" in arguments and not all(
        flag in completed.stdout
        for flag in (b"--account-id", b"--resource-id", b"--data-root")
    ):
        raise RuntimeError("m7_setup_operator_unavailable")
    if "agentmonitor.composition.billing_worker" in arguments and not all(
        flag in completed.stdout
        for flag in (b"--data-root", b"--start-authority", b"--recovery-only")
    ):
        raise RuntimeError("m7_setup_operator_unavailable")


def execute_setup_activation(
    expected: str,
    *,
    financial: bool = False,
    model: bool = False,
    retention: bool = False,
) -> LaneResult:
    """One fixed setup/financial/model transition, never full M7 deployment."""
    checks: list[CheckResult] = []
    stage = "controller_preflight"
    started = False
    try:
        verify_setup_controller(ROOT, expected)
        from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
            DatabaseRefV1,
        )
        from agentmonitor.adapters.persistence._shared.sqlite.schema import (
            compatibility,
        )

        from tools.automation.implementations.auto_m6_local_activate import request
        from tools.automation.implementations.m6_cutover import (
            _FIXED_DATA,
            _FIXED_EXECUTABLE,
            _FIXED_UNIT,
            _candidate_override,
            _verify_active_source_schema,
            _verify_candidate_runtime,
        )

        source_revision = (
            "v1_0735"
            if retention
            else "v1_0734"
            if model
            else "v1_0733"
            if financial
            else "v1_0720"
        )
        target_revision = (
            "v1_0736"
            if retention
            else "v1_0735"
            if model
            else "v1_0734"
            if financial
            else "v1_0731"
        )
        if compatibility.load_migration_catalog().head != target_revision:
            raise RuntimeError("m7_setup_schema_selection_invalid")
        _verify_active_source_schema(
            DatabaseRefV1(_FIXED_DATA / "agentmonitor.db", _FIXED_DATA), source_revision
        )
        checks.append(CheckResult(stage, "passed"))
        stage = "candidate_started"
        print(
            "M7 RETENTION OPERATION: retention schema activation only"
            if retention
            else "M7 MODEL OPERATION: model grouping semantic marker activation only"
            if model
            else "M7 FINANCIAL OPERATION: financial schema activation only"
            if financial
            else "M7 SETUP OPERATION: initial setup activation only",
            flush=True,
        )
        started = True
        _setup_process(
            [
                "tools/automation/implementations/auto_m6_cutover.py",
                "--expected-revision=" + expected,
            ],
            timeout=600,
        )
        checks.append(CheckResult(stage, "passed"))

        def installed_ready() -> None:
            verify_setup_controller(ROOT, expected)
            _verify_candidate_runtime(
                root=_FIXED_DATA,
                unit=_FIXED_UNIT,
                checkout=ROOT,
                origin="http://127.0.0.1:43110",
                executable=_FIXED_EXECUTABLE,
                expected_command=_candidate_override(ROOT)
                .split("ExecStart=\nExecStart=", 1)[1]
                .strip()
                .split(),
            )

        stage = "installed_revision_loopback"
        deadline = time.monotonic() + 20
        while True:
            try:
                installed_ready()
                break
            except (OSError, RuntimeError, ValueError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)
        checks.append(CheckResult(stage, "passed"))
        stage = "restart_finalized"
        verify_setup_controller(ROOT, expected)
        _setup_process(
            ["tools/automation/implementations/auto_m6_finalize_candidate.py"],
            timeout=90,
        )
        installed_ready()
        checks.append(CheckResult(stage, "passed"))
        stage = "operator_command"
        _setup_process(
            ["-m", "agentmonitor.composition.billing_credential_operator", "--help"],
            timeout=30,
        )
        checks.append(CheckResult(stage, "passed"))
        if financial or model or retention:
            stage = "billing_worker_command"
            _setup_process(
                ["-m", "agentmonitor.composition.billing_worker", "--help"],
                timeout=30,
            )
            checks.append(CheckResult(stage, "passed"))
        stage = "lan_readiness"
        status, body = request("http://192.168.1.18:43110", "/login")
        if status != 200 or b"agentmonitor-dashboard-root" not in body:
            raise RuntimeError("m7_setup_lan_unavailable")
        checks.append(CheckResult(stage, "passed"))
        stage = "installed_postcheck"
        installed_ready()
        checks.append(CheckResult(stage, "passed"))
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        from tools.automation.implementations.m6_cutover_diagnostics import (
            PHASES,
            REASONS,
        )

        known = {
            "m7_setup_cutover_journal_review",
            "m7_setup_finalize_journal_review",
            "m7_setup_revision_mismatch",
            "m7_setup_runtime_unavailable",
            "m7_setup_command_failed",
            "m7_setup_operator_unavailable",
            "m7_setup_lan_unavailable",
            "m7_setup_schema_selection_invalid",
            "m7_setup_controller_not_retained",
        }
        known.update(
            "m7_cutover_" + phase + "_" + reason
            for phase in PHASES
            for reason in REASONS
        )
        reason = (
            str(error)
            if str(error) in known
            else (
                "m7_setup_operation_requires_review"
                if started
                else "m7_setup_preflight_refused"
            )
        )
        checks.append(CheckResult(stage, "failed" if started else "blocked", reason))
    result = setup_activation_result(
        tuple(checks), financial=financial, model=model, retention=retention
    )
    for check in result.checks:
        reason = f" ({check.reason_code})" if check.reason_code else ""
        print(f"M7 CHECK {check.name}: {check.status.upper()}{reason}", flush=True)
    return result


def observe_exit_context(expected: str) -> ExitContext:
    """Read existing clean checkout, sealed runtime and compatible schema only."""
    from tools.automation.implementations.m6_frontend_build import _clean_revision

    source = _clean_revision(ROOT)
    if source != expected:
        raise ValueError("m7_exit_source_revision_mismatch")

    import hashlib

    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
        InspectActiveSchemaCompatibilityV1,
        load_migration_catalog,
    )

    from tools.automation.implementations.m6_cutover import (
        _FIXED_DATA,
        _FIXED_UNIT,
        _cwd,
        _verify_retained_baseline,
    )
    from tools.automation.implementations.m6_recovery_interval import _identity

    identity = _identity()
    candidate = Path(_cwd(_FIXED_UNIT))
    installed, build = _verify_retained_baseline(candidate)
    if installed != source:
        raise ValueError("m7_exit_installed_revision_mismatch")
    state, schema = InspectActiveSchemaCompatibilityV1(
        DatabaseRefV1(_FIXED_DATA / "agentmonitor.db", _FIXED_DATA)
    )
    if state != "compatible" or schema != load_migration_catalog().head:
        raise ValueError("m7_exit_schema_unverified")
    if (
        _identity() != identity
        or _cwd(_FIXED_UNIT) != str(candidate)
        or _verify_retained_baseline(candidate) != (installed, build)
        or _clean_revision(ROOT) != source
    ):
        raise ValueError("m7_exit_context_changed")
    digest = hashlib.sha256(
        f"{identity.pid}:{identity.invocation_id}:{identity.started_at.isoformat()}:{build}".encode()
    ).hexdigest()
    return ExitContext(source, installed, schema, digest)


def execute_exit(expected: str | None) -> LaneResult:
    """Extend the existing aggregate with observed identity and a typed receipt."""
    if expected is None:
        print(
            "M7 EXIT ADMISSION: BLOCKED (m7_expected_installed_revision_required)",
            flush=True,
        )
        return LaneResult(
            "exit",
            "blocked",
            (
                CheckResult(
                    "technical", "not_run", "m7_expected_installed_revision_required"
                ),
            ),
        )
    try:
        before = observe_exit_context(expected)
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.SubprocessError,
        ImportError,
    ) as error:
        reason = (
            str(error)
            if str(error)
            in {
                "frontend_source_not_clean",
                "m7_exit_source_revision_mismatch",
                "m7_exit_installed_revision_mismatch",
                "m7_exit_schema_unverified",
                "m7_exit_context_changed",
            }
            else "m7_exit_context_unavailable"
        )
        print(f"M7 EXIT ADMISSION: BLOCKED ({reason})", flush=True)
        return LaneResult(
            "exit", "blocked", (CheckResult("technical", "not_run", reason),)
        )
    observations: list[TimedCheck] = []
    result = execute_lane("exit", expected_revision=expected, observations=observations)
    try:
        after = observe_exit_context(expected)
        receipt = build_receipt(before, after, tuple(observations), REQUIRED_CHECKS)
        if receipt["status"] != result.status:
            raise ValueError("m7_exit_result_mismatch")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, ImportError):
        print("M7 EXIT RECEIPT: FAILED (m7_exit_context_or_result_changed)", flush=True)
        return LaneResult("exit", "failed", result.checks)
    # Closed metadata only. The command's captured output is its receipt artifact;
    # no imported/owner-entered outcome can enter this execution path.
    print("M7 EXIT RECEIPT: " + json.dumps(receipt, sort_keys=True), flush=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, choices=tuple(REQUIRED_CHECKS))
    parser.add_argument(
        "--check",
        choices=(
            "candidate",
            "installed_revision",
            "continuity",
            "recovery",
            "ollama",
            "setup_activation",
            "financial_activation",
            "model_activation",
            "retention_activation",
            "owner_pool_controls",
            "source_history",
            "accessibility",
            "overview",
            "receipt_recovery",
            "configured_inventory",
            "retention_invocation",
            "backup_recovery",
            "budget_http",
            *TECHNICAL_BOUNDARY_TARGETS,
            *PROVIDER_REPORT_TARGETS,
            *GUARD_SCOPES,
        ),
    )
    parser.add_argument("--expected-revision")
    args = parser.parse_args(argv)
    if args.lane == "exit" and args.expected_revision is None:
        args.expected_revision = os.environ.get("AGENTMONITOR_M7_EXPECTED_REVISION")
    try:
        validate_selection(args.lane, args.check, args.expected_revision)
    except ValueError:
        parser.error(
            "activation requires --lane deploy and --expected-revision=<40SHA>; "
            "browser/deploy/live/exit aggregates accept --expected-revision=<40SHA>; "
            "guard checks require --lane technical without --expected-revision"
        )
    result = (
        execute_exit(args.expected_revision)
        if args.lane == "exit" and args.check is None
        else execute_deploy_observation(args.check, args.expected_revision)
        if args.check in DEPLOY_OBSERVATION_CHECKS
        else execute_ollama(args.expected_revision)
        if args.check == "ollama"
        else execute_continuity(args.expected_revision)
        if args.check == "continuity"
        else execute_recovery(args.expected_revision)
        if args.check == "recovery"
        else execute_setup_activation(
            args.expected_revision,
            financial=args.check == "financial_activation",
            model=args.check == "model_activation",
            retention=args.check == "retention_activation",
        )
        if args.check
        in {
            "setup_activation",
            "financial_activation",
            "model_activation",
            "retention_activation",
        }
        else execute_pool_browser(args.check)
        if args.check in {"owner_pool_controls", "source_history"}
        else execute_accessibility()
        if args.check == "accessibility"
        else execute_overview_browser(args.expected_revision)
        if args.check == "overview"
        else execute_budget_http()
        if args.check == "budget_http"
        else execute_technical_boundary(args.check)
        if args.check in TECHNICAL_BOUNDARY_TARGETS
        else execute_backup_recovery()
        if args.check == "backup_recovery"
        else execute_receipt_recovery()
        if args.check == "receipt_recovery"
        else retention_invocation_result()
        if args.check == "retention_invocation"
        else configured_inventory_result()
        if args.check == "configured_inventory"
        else execute_provider_reports(args.check, args.expected_revision)
        if args.check in PROVIDER_REPORT_TARGETS
        else execute_guard(args.check)
        if args.check in GUARD_SCOPES
        else execute_lane(args.lane, expected_revision=args.expected_revision)
    )
    if args.check in {
        *DEPLOY_OBSERVATION_CHECKS,
        *PROVIDER_REPORT_TARGETS,
        "recovery",
        "continuity",
        "ollama",
    }:
        for check in result.checks:
            detail = f" ({check.reason_code})" if check.reason_code else ""
            print(f"M7 CHECK {check.name}: {check.status.upper()}{detail}", flush=True)
    if args.check in DEPLOY_OBSERVATION_CHECKS:
        scope = (
            "read-only selected sealed release/runtime identity; authenticated "
            "workflow and provider continuity remain separate"
        )
    elif args.check == "recovery":
        scope = (
            "real guards, expiry, receipt, backup and owned-worker financial network "
            "isolation/recovery; genuine abandoned dispatch remains "
            "separately conditional"
        )
    elif args.check == "ollama":
        scope = (
            "real retained Ollama scheduling/funds/monetary/provenance/model-context "
            "checks plus one complete installed manual usage action when an exact "
            "revision is supplied, plus one actual native monetary comparison; "
            "all executed outcomes remain explicit"
        )
    elif args.check == "continuity":
        scope = (
            "prospective scheduled financial receipt after closing our own dashboard "
            "window, with genuine Claude/Codex quota progress in the same interval; "
            "no claim that owner browser windows were closed"
        )
    elif result.lane == "deploy/retention_activation":
        scope = (
            "retention schema operational slice; authenticated financial, "
            "collector continuity and backup/recovery proof remain separate; "
            "not full deployment or M7 acceptance"
        )
    elif result.lane == "deploy/model_activation":
        scope = (
            "model grouping semantic marker operational slice; authenticated "
            "financial, collector continuity and backup/recovery proof remain "
            "separate; not full deployment or M7 acceptance"
        )
    elif result.lane == "deploy/financial_activation":
        scope = (
            "financial schema operational slice; authenticated first report, "
            "collector continuity and backup/recovery proof remain separate; "
            "not full deployment or M7 acceptance"
        )
    elif result.lane == "deploy/setup_activation":
        scope = (
            "setup operational slice; authenticated setup, collector continuity and "
            "backup/recovery proof remain separate; "
            "not full deployment or M7 acceptance"
        )
    elif args.check == "owner_pool_controls":
        scope = (
            "isolated built-browser owner pool metadata; "
            "no provider, money or full M7 acceptance claim"
        )
    elif args.check == "source_history":
        scope = (
            "genuine retained monetary persistence/HTTP, report metadata, "
            "built-browser keyboard navigation, source-entry and daily-total charts; "
            "no fresh commit, provider-display comparison "
            "native 200-percent zoom or full detail_history acceptance"
        )
    elif args.check == "accessibility":
        scope = (
            "built-browser keyboard navigation and native Chrome 200-percent zoom "
            "over genuine financial data; no installed revision, provider access "
            "or full M7 acceptance claim"
        )
    elif args.check == "overview":
        scope = (
            "real stored money, installed monetary journey "
            "concurrent Overview/setup/cloud reads and genuine private-copy "
            "full-filter totals for available contexts; extra populated examples "
            "and broader accessibility/M7 acceptance remain separate"
        )
    elif args.check == "budget_http":
        scope = (
            "real IAM/HTTP guards and genuine monetary history, funds "
            "and filtered totals; "
            "no fresh provider collection or full M7 acceptance claim"
        )
    elif args.check in TECHNICAL_BOUNDARY_SCOPES:
        scope = TECHNICAL_BOUNDARY_SCOPES[args.check]
    elif args.check == "backup_recovery":
        scope = (
            "isolated genuine financial backup/restore and missing-credential guard; "
            "no installed restore, full disaster recovery or M7 acceptance claim"
        )
    elif args.check == "receipt_recovery":
        scope = (
            "genuine pre-finalization snapshot recovery only; "
            "no process-kill, supervisor recovery or full M7 acceptance claim"
        )
    elif args.check in PROVIDER_REPORT_TARGETS:
        scope = (
            "retained provider coverage plus independent native cost comparison when "
            "an installed revision is selected; actual missing access/coverage "
            "and naturally absent populated mappings remain explicit"
        )
    elif args.check in GUARD_SCOPES:
        scope = GUARD_SCOPES[args.check]
    elif result.lane in {"pure", "mutation"}:
        scope = (
            "pure policy verification only; "
            "no database, HTTP, browser or provider claim"
        )
    elif result.lane == "registry_metadata":
        scope = (
            "registry metadata and nonsecret binding lifecycle only; "
            "no secret entry, activation or provider access claim"
        )
    elif result.lane == "persistence_schema":
        scope = (
            "fresh and upgraded empty SQLite schema only; "
            "no provider report commit, installed migration or M7 acceptance claim"
        )
    else:
        scope = f"{result.lane}; no milestone acceptance or publication claim"
    print(f"M7 RESULT: {result.status.upper()} — {scope}", flush=True)
    return {"passed": 0, "failed": 1, "blocked": 3, "not_run": 3}[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
