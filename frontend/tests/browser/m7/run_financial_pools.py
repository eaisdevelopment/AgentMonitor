"""Built pool controls against isolated real IAM/registry; no provider access."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)

from backend.tests.integration.api.test_iam_http import _installation, _running
from backend.tests.integration.registry.test_billing_credential_binding import (
    _account,
    _archive,
    _billing_connection,
)

ROOT = Path(__file__).resolve().parents[4]
STAGES = {
    "browser_launch",
    "login",
    "owner_metadata",
    "billing_scope_controls",
    "billing_scope_pool_refresh",
    "billing_scope_status_reconcile",
    "billing_reconnect_lifecycle",
    "billing_reconnect_controls",
    "billing_reconnect_reconcile",
    "billing_reconnect_archived",
    "billing_local_disconnect",
    "billing_local_clipboard_fallback",
    "billing_local_archived_cleanup",
    "billing_status_financial_refresh",
    "billing_focus_financial_refresh",
    "billing_status_failure_retention",
    "billing_status_external_change",
    "billing_status_summary_response",
    "billing_status_scope_render",
    "pool_controls_missing",
    "collection_controls_missing",
    "collection_context_read_only",
    "report_view_options",
    "report_view_options_dom",
    "report_view_initial_window",
    "report_view_select_cost",
    "report_view_select_usage",
    "report_view_reload",
    "report_view_ungrouped",
    "report_view_back",
    "report_view_forward",
    "report_view_restore",
    "report_view_response",
    "report_view_body",
    "report_view_context",
    "report_view_eligibility",
    "report_view_selected_dom",
    "report_view_selected_url",
    "report_view_collect_disabled",
    "report_view_no_response",
    "report_view_wrong_resource",
    "report_view_wrong_range",
    "report_view_wrong_category",
    "report_view_wrong_grouping",
    "create_pool",
    "join_pool",
    "shared_overview",
    "edit_attribution",
    "unlink_pool",
    "stale_revision",
    "pagination",
    "uncertain_outcome",
    "reload_keyboard_narrow",
    "account_create_navigation",
    "account_create_navigation_response",
    "account_create_navigation_settled",
    "account_create_navigation_retained",
    "account_organization_pages",
    "account_organization_assignment",
    "account_organization_placeholder",
    "account_organization_retention",
    "account_organization_save",
    "no_provider_work",
    "overview_sort_source",
    "overview_sort_source_create",
    "overview_sort_source_http",
    "overview_sort_source_availability",
    "budget_overview_registry_changed",
    "budget_overview_query_unavailable",
    "budget_overview_inventory_unavailable",
    "budget_overview_rows_invalid",
    "budget_overview_account_context_invalid",
    "budget_overview_resource_context_invalid",
    "budget_overview_funds_context_invalid",
    "budget_pool_snapshot_invalid",
    "overview_sort_source_page",
    "overview_sort_source_winner",
    "overview_sort_first_page",
    "overview_sort_pagination",
    "overview_sort_reset",
    "overview_sort_reload",
}


def pool_progress_stage(output: str | bytes | None) -> str:
    """Only our fixed step names leave the browser boundary, including timeout."""
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    stage = "browser_boundary"
    for line in (output or "").splitlines():
        if line == "M7 FINANCIAL POOLS BROWSER: PASSED":
            continue
        if not line.startswith("M7 POOL STAGE: "):
            return "browser_output_invalid"
        selected = line.removeprefix("M7 POOL STAGE: ")
        if selected not in STAGES:
            return "browser_output_invalid"
        stage = selected
    return stage


async def run() -> None:
    with tempfile.TemporaryDirectory(prefix="agentmonitor-pool-browser-") as directory:
        app, credential = _installation(Path(directory))
        # This checks owner metadata, not independently scheduled collectors.
        app.state.lifecycle.hooks = replace(app.state.lifecycle.hooks, tasks=())
        # Real interrupted enrollment metadata, then actual archive. No key,
        # provider identity, access proof or telemetry is supplied to this test.
        reference = DatabaseRefV1(Path(directory) / "agentmonitor.db", Path(directory))
        cleanup_account = _account(reference, "claude")
        _billing_connection(reference, cleanup_account)
        SqliteCredentialBindingsV1(reference).transition(
            cleanup_account.account_id, action="prepare", expected_record_version=0
        )
        SqliteRegistryRepositoryV1(reference).edit_account(_archive(cleanup_account))
        async with _running(app) as origin:
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "node",
                    str(Path(__file__).with_name("financial_pools.mjs")),
                    origin,
                    cleanup_account.account_id.value,
                ],
                input=credential,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=420,
            )
        passed = "M7 FINANCIAL POOLS BROWSER: PASSED"
        if (
            result.returncode == 0
            and result.stdout.splitlines()[-1:] == [passed]
            and pool_progress_stage(result.stdout) in STAGES
            and not result.stderr
        ):
            print(passed)
            return
        prefix = "M7 FINANCIAL POOLS BROWSER: FAILED — "
        stage = result.stderr.strip().removeprefix(prefix)
        if pool_progress_stage(result.stdout) not in STAGES or stage not in STAGES:
            stage = "browser_output_invalid"
        raise RuntimeError(stage)


def main() -> int:
    try:
        asyncio.run(run())
    except subprocess.TimeoutExpired as error:
        print(
            "M7 FINANCIAL POOLS BROWSER: FAILED — timeout at "
            + pool_progress_stage(error.output)
        )
        return 1
    except (RuntimeError, TimeoutError) as error:
        stage = str(error) if str(error) in STAGES else "browser_boundary"
        print("M7 FINANCIAL POOLS BROWSER: FAILED — " + stage)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
