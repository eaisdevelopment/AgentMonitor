"""Closed scope checks for the current one-account M3 technical suite."""

import subprocess
import sys
from pathlib import Path

from tools.automation.implementations.auto_m3_test import COMMANDS, M3_PYTEST_TARGETS

ROOT = Path(__file__).resolve().parents[2]


def test_m3_suite_names_exact_files_and_excludes_later_milestones() -> None:
    required = {
        "backend/tests/adapters/providers/claude/test_capacity_mapper.py",
        "backend/tests/adapters/providers/claude/test_manifest.py",
        "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_otlp_success_response_is_gated_by_durable_commit_acknowledgement",
        "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_otlp_collection_schedule_is_bound_to_selected_account_and_profile",
        "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_otlp_collection_persists_the_sanitized_adapter_failure_code",
        "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_launcher_child_reports_only_allowlisted_start_failure_codes",
        "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_collection_uses_preconfirmed_identity_without_mutation",
        "backend/tests/adapters/providers/claude/test_otel_runtime_static.py::test_owner_binding_command_closes_the_actual_metric_to_exact_source_tuple",
        "backend/tests/provider_system/test_protocol.py",
        "backend/tests/provider_system/test_manifest_schema.py",
        "backend/tests/integration/collection_control/test_claude_composition.py",
        "backend/tests/integration/capacity/test_capacity_schema_chain.py",
        "backend/tests/runtime_observation/integration/test_runtime_schema_chain.py",
        "backend/tests/integration/api/test_capacity_history_http.py::test_capacity_history_authenticates_and_get_never_collects",
        "backend/tests/integration/api/test_observation_http.py",
    }
    prohibited_fragments = (
        "fleet",
        "organization_aggregates",
        "alert",
        "m4_",
        "lan_http",
        "iam_http",
        "openapi_policy",
    )

    assert required <= set(M3_PYTEST_TARGETS)
    assert (
        "backend/tests/adapters/providers/claude/test_otel_runtime_static.py"
        not in M3_PYTEST_TARGETS
    )
    assert len(M3_PYTEST_TARGETS) == len(set(M3_PYTEST_TARGETS))
    assert all(
        (ROOT / target.partition("::")[0]).is_file() for target in M3_PYTEST_TARGETS
    )
    assert all(
        not any(token in target for token in prohibited_fragments)
        for target in M3_PYTEST_TARGETS
    )
    assert COMMANDS[0][3] == "tools/automation/test_m3_test.py"
    assert COMMANDS[0][-2:] == ("-p", "tools.automation.pytest_no_skip")
    assert tuple(COMMANDS[1][3:-4]) == M3_PYTEST_TARGETS
    assert COMMANDS[1][-2:] == ("-p", "tools.automation.pytest_no_skip")


def test_m3_suite_fails_closed_when_pytest_skips_a_selected_test(
    tmp_path: Path,
) -> None:
    probe = tmp_path / "test_skip_probe.py"
    probe.write_text(
        "import pytest\n\n@pytest.mark.skip(reason='probe')\ndef test_probe():\n"
        "    raise AssertionError('must not execute')\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        (
            sys.executable,
            "-m",
            "pytest",
            str(probe),
            "-q",
            "-p",
            "tools.automation.pytest_no_skip",
        ),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert "AUTO-M3-TEST skip policy: 1 skipped test is prohibited" in (
        result.stdout + result.stderr
    )
