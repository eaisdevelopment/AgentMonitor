"""Run the bounded real M3 technical test surface.

M2's complete browser routine intentionally includes a 30-minute real idle
expiry scenario. M3's exit gate already performs its own fresh authenticated
visible browser and provider checks, so it runs the M3-owned backend/contract
surface here and leaves the long M2 routine under AUTO-TEST. Exact files keep
later M4 fleet, organization, alert, operations, and LAN scenarios in their
own milestone gates. Historical M0 handoff records remain immutable evidence;
current protocol behavior is checked directly through the production contract,
manifest, persistence, API, capacity, collection, and runtime suites below. A
pytest plugin turns every selected skip or xfail into a failed command.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

M3_PYTEST_TARGETS: tuple[str, ...] = (
    "backend/tests/adapters/providers/claude/test_capacity_mapper.py",
    "backend/tests/adapters/providers/claude/test_manifest.py",
    "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_otlp_success_response_is_gated_by_durable_commit_acknowledgement",
    "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_otlp_collection_schedule_is_bound_to_selected_account_and_profile",
    "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_otlp_collection_persists_the_sanitized_adapter_failure_code",
    "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_launcher_child_reports_only_allowlisted_start_failure_codes",
    "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_collection_uses_preconfirmed_identity_without_mutation",
    "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_owner_binding_command_closes_the_actual_metric_to_exact_source_tuple",
    "backend/tests/capacity/test_quantity_and_health.py",
    "backend/tests/collection_control/test_policy.py",
    "backend/tests/contracts/test_capacity_history_contract.py",
    "backend/tests/provider_system/test_manifest_schema.py",
    "backend/tests/provider_system/test_protocol.py",
    "backend/tests/registry/test_identity_policy.py",
    "backend/tests/registry/test_provider_identity_fingerprint_contract.py",
    "backend/tests/runtime_observation/test_claude_runtime_ports.py",
    "backend/tests/runtime_observation/test_contracts.py",
    "backend/tests/runtime_observation/test_linux_process_policy.py",
    "backend/tests/runtime_observation/test_process_attribution_policy.py",
    "backend/tests/runtime_observation/test_runtime_state_policy.py",
    "backend/tests/runtime_observation/test_session_tree_query.py",
    "backend/tests/runtime_observation/integration/test_runtime_migration_constraints.py",
    "backend/tests/runtime_observation/integration/test_runtime_schema_chain.py",
    "backend/tests/integration/api/test_capacity_history_http.py::test_capacity_history_authenticates_and_get_never_collects",
    "backend/tests/integration/api/test_capacity_history_http.py::test_capacity_history_openapi_has_exact_read_policy",
    "backend/tests/integration/api/test_dashboard_html_routes.py",
    "backend/tests/integration/api/test_docs_browser.py",
    "backend/tests/integration/api/test_observation_http.py",
    "backend/tests/integration/api/test_origin_policy.py",
    "backend/tests/integration/api/test_runtime_tree_http.py",
    "backend/tests/integration/capacity/test_capacity_schema_chain.py",
    "backend/tests/integration/collection_control/test_claude_composition.py",
    "backend/tests/integration/collection_control/test_collection_repository.py",
    "backend/tests/integration/collection_control/test_linux_runtime_recovery.py",
    "backend/tests/integration/provider_system/test_compatibility_repository.py",
    "backend/tests/integration/registry/test_provider_identity_operator.py",
)

COMMANDS: tuple[tuple[str, ...], ...] = (
    (
        "backend/.venv/bin/python",
        "-m",
        "pytest",
        "tools/automation/test_m3_test.py",
        "-q",
        "--tb=short",
        "-p",
        "tools.automation.pytest_no_skip",
    ),
    (
        "backend/.venv/bin/python",
        "-m",
        "pytest",
        *M3_PYTEST_TARGETS,
        "-q",
        "--tb=short",
        "-p",
        "tools.automation.pytest_no_skip",
    ),
)


def main() -> int:
    for command in COMMANDS:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode != 0:
            print("AUTO-M3-TEST: FAILED — required M3 technical test failed")
            return result.returncode
    print("AUTO-M3-TEST: PASSED — M3 contract and technical backend boundaries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
