"""Fail-closed acceptance of all six canonical V1-M4 stories."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STORY_ARTIFACTS = {
    "ST-FLEET-001": ("backend/tests/integration/registry/test_claude_fleet.py",),
    "ST-FLEET-002": (
        "backend/src/agentmonitor/modules/capacity/domain/forecast.py",
        "backend/src/agentmonitor/modules/collection_control/domain/identity_attestation.py",
        "backend/src/agentmonitor/adapters/persistence/capacity/sqlite/current_repository.py",
        "backend/migrations/versions/v1_0703_m05_capacity_projection_metadata.py",
        "backend/migrations/versions/v1_0704_m05_event_delivery_proof.py",
        "backend/migrations/versions/v1_0707_m05_current_capacity_projections.py",
        "backend/tests/integration/collection_control/test_claude_fleet_collection.py",
        "backend/tests/integration/capacity/test_claude_organization_aggregates.py",
    ),
    "ST-FLEET-003": (
        "backend/tests/runtime_observation/integration/test_claude_process_tree.py",
        "backend/tests/integration/api/test_fleet_routes.py",
        "tools/ui/verify_m4_fleet.mjs",
    ),
    "ST-ALERT-001": (
        "backend/src/agentmonitor/contracts/alerting_v1.py",
        "backend/src/agentmonitor/modules/alerting/application/consume.py",
        "backend/migrations/versions/v1_0700_m07_alert_rules.py",
        "backend/migrations/versions/v1_0701_m07_alert_lifecycle.py",
        "backend/migrations/versions/v1_0702_m07_alert_deadlines_outbox.py",
        "backend/migrations/versions/v1_0705_m07_rule_configuration_guards.py",
        "backend/migrations/versions/v1_0706_m04_collector_alerts.py",
        "backend/src/agentmonitor/composition/alert_delivery.py",
        "backend/tests/integration/alerting/test_signal_lifecycle.py",
    ),
    "ST-ALERT-002": (
        "backend/src/agentmonitor/api/v1/routers/alerts.py",
        "frontend/src/features/alerts/AlertsPage.tsx",
        "frontend/src/features/alerts/AlertRulesPage.tsx",
        "backend/tests/integration/api/test_alert_routes.py",
        "tools/ui/verify_m4_alerts.mjs",
    ),
    "ST-OPS-001": (
        "backend/src/agentmonitor/contracts/operations_v1.py",
        "backend/src/agentmonitor/modules/operations/application/health.py",
        "backend/src/agentmonitor/modules/operations/application/diagnostics.py",
        "backend/src/agentmonitor/modules/operations/application/service.py",
        "backend/src/agentmonitor/api/v1/routers/operations.py",
        "frontend/src/features/operations/OperationsPage.tsx",
        "backend/tests/integration/operations/test_health_and_diagnostics.py",
        "backend/tests/integration/api/test_operations_routes.py",
        "backend/tests/integration/release/test_v1_m4_claude_fleet_alerts.py",
        "tools/automation/implementations/auto_migrate.py",
        "backend/tests/integration/persistence/test_auto_migrate.py",
        "tools/ui/verify_m4_operations.mjs",
    ),
}
TEST_PATHS = (
    "backend/tests/integration/registry/test_claude_fleet.py",
    "backend/tests/integration/registry/test_m4_alert_subject_scope.py",
    "backend/tests/foundation/test_build_inventory.py",
    "backend/tests/foundation/test_durable_event_contract.py",
    "backend/tests/foundation/test_lifecycle_snapshot.py",
    "backend/tests/identity_access/test_alert_authorization.py",
    "backend/tests/capacity/pure",
    "backend/tests/capacity/test_quantity_and_health.py",
    "backend/tests/collection_control/test_polling.py",
    "backend/tests/collection_control/test_collector_alert_conditions.py",
    "backend/tests/collection_control/test_identity_reattest_policy.py",
    "backend/tests/integration/collection_control/test_alert_condition_queries.py",
    "backend/tests/integration/collection_control/test_claude_fleet_collection.py",
    "backend/tests/integration/capacity/test_claude_organization_aggregates.py",
    "backend/tests/integration/capacity/test_m4_current_forecast.py",
    "backend/tests/integration/capacity/test_m4_current_metadata.py",
    "backend/tests/integration/capacity/test_capacity_schema_chain.py",
    "backend/tests/runtime_observation/integration/test_claude_process_tree.py",
    "backend/tests/runtime_observation/integration/test_runtime_schema_chain.py",
    "backend/tests/persistence/sqlite/core/test_bounded_read.py",
    "backend/tests/persistence/sqlite/schema/test_live_health.py",
    "backend/tests/integration/persistence/test_auto_migrate.py",
    "backend/tests/alerting",
    "backend/tests/integration/alerting",
    "backend/tests/operations",
    "backend/tests/integration/operations",
    "backend/tests/integration/api/test_fleet_routes.py",
    "backend/tests/integration/api/test_capacity_scope_routes.py",
    "backend/tests/integration/api/test_alert_routes.py",
    "backend/tests/integration/api/test_operations_routes.py",
    "backend/tests/integration/release/test_v1_m4_claude_fleet_alerts.py",
)
LIVE_SELECTORS = (
    "AGENTMONITOR_TEST_OWNER_DATA_ROOT",
    "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT",
    "AGENTMONITOR_TEST_DASHBOARD_ORIGIN",
    "AGENTMONITOR_TEST_M4_OWNER_OUTCOMES",
)
LOCAL_ROUTINES = (
    "AUTO-PLAN-CHECK",
    "AUTO-QUALITY",
    "AUTO-BUILD",
    "AUTO-MUTATION",
    "AUTO-DOCS-CHECK",
    "AUTO-GIT-PREFLIGHT",
)


def main() -> int:
    missing = tuple(
        (story, path)
        for story, paths in STORY_ARTIFACTS.items()
        for path in paths
        if not (ROOT / path).is_file()
    )
    if missing:
        print("M4 EXIT: FAILED — required_m4_artifacts_missing")
        for story, path in missing:
            print(f"{story}: {path}")
        return 1
    if not all(os.environ.get(key) for key in LIVE_SELECTORS):
        print("M4 EXIT: BLOCKED — genuine_fleet_and_owner_outcomes_required")
        return 3
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "backend/src"))
    try:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-m4-acceptance-") as raw:
            report = Path(raw) / "results.xml"
            command = [
                str(ROOT / "backend/.venv/bin/python"),
                "-m",
                "pytest",
                *TEST_PATHS,
                "-q",
                "--tb=short",
                f"--junitxml={report}",
            ]
            result = subprocess.run(
                command, cwd=ROOT, env=environment, check=False, timeout=1800
            )
            if result.returncode:
                print("M4 EXIT: FAILED — required_story_suite_failed")
                return 1
            suites = tuple(ET.parse(report).getroot().iter("testsuite"))
            if not suites or sum(int(s.get("tests", "0")) for s in suites) == 0:
                print("M4 EXIT: FAILED — required_story_suite_empty")
                return 1
            if any(int(s.get("skipped", "0")) for s in suites):
                print("M4 EXIT: BLOCKED — required_real_scenario_unexecuted")
                return 3
        commands = (
            *(
                ("node", path)
                for path in (
                    "tools/ui/verify_m4_fleet.mjs",
                    "tools/ui/verify_m4_alerts.mjs",
                    "tools/ui/verify_m4_operations.mjs",
                )
            ),
            *(
                (sys.executable, "tools/automation/run.py", routine)
                for routine in LOCAL_ROUTINES
            ),
        )
        for command in commands:
            result = subprocess.run(
                command, cwd=ROOT, env=environment, check=False, timeout=1800
            )
            if result.returncode:
                state = "BLOCKED" if result.returncode == 3 else "FAILED"
                print(f"M4 EXIT: {state} — required_boundary_rejected")
                return 3 if result.returncode == 3 else 1
    except (OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired):
        print("M4 EXIT: FAILED — completion_execution_unavailable")
        return 1
    print("M4 EXIT: PASSED — six stories, real fleet/alerts/operations and local gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
