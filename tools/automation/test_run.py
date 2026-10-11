"""Real-checkout tests for the canonical AgentMonitor routine dispatcher."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from datetime import UTC, datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from inspect import getsource
from pathlib import Path
from shutil import copy2, copytree, which

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPOSITORY_ROOT / "tools/automation/run.py"
CATALOG = REPOSITORY_ROOT / "tools/automation/routines.toml"
sys.path.insert(0, str(RUNNER.parent))

from run import index_routines, load_catalog, validate_catalog


class AutomationRoutineTests(unittest.TestCase):
    def test_m5_prerequisite_archive_without_selection_never_moves_files(
        self,
    ) -> None:
        """The recovery command blocks before selecting an owner data root."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-M5-ARCHIVE-PREREQUISITES"]
        self.assertEqual("operational", routine["status"])
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M5-ARCHIVE-PREREQUISITES"],
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath},
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(3, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("PASSED", result.stdout)
        self.assertIn("M5 PREREQUISITE ARCHIVE: BLOCKED", result.stdout)

    def test_m5_owner_outcomes_without_real_selectors_never_writes_file(
        self,
    ) -> None:
        """The interactive producer fails closed before owner registry access."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-M5-OWNER-OUTCOMES"]
        self.assertEqual("operational", routine["status"])
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M5-OWNER-OUTCOMES"],
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath},
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(3, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("PASSED", result.stdout)
        self.assertIn("M5 OWNER OUTCOMES: BLOCKED", result.stdout)

    def test_m5_alert_witness_without_real_selectors_never_writes_receipt(
        self,
    ) -> None:
        """The application-owned witness command fails closed before live input."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-M5-ALERT-WITNESS"]
        self.assertEqual("operational", routine["status"])
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M5-ALERT-WITNESS"],
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath},
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(3, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("PASSED", result.stdout)
        self.assertIn("M5 CODEX ALERT WITNESS: BLOCKED", result.stdout)

    def test_m5_quota_witness_without_real_selectors_never_writes_receipt(
        self,
    ) -> None:
        """The quota witness fails closed before browser or owner interaction."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-M5-QUOTA-WITNESS"]
        self.assertEqual("operational", routine["status"])
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M5-QUOTA-WITNESS"],
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath},
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(3, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("PASSED", result.stdout)
        self.assertIn("M5 CODEX QUOTA WITNESS: BLOCKED", result.stdout)

    def test_m5_exit_without_real_selectors_never_claims_completion(self) -> None:
        """The Codex milestone gate rejects absent live owner prerequisites."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-M5-EXIT"]
        self.assertEqual("operational", routine["status"])
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M5-EXIT"],
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath},
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertIn(result.returncode, (1, 3), result.stdout + result.stderr)
        self.assertNotIn("PASSED", result.stdout)
        self.assertRegex(result.stdout, r"M5 CURRENT EXIT: (?:BLOCKED|FAILED)")

    def test_m4_exit_without_real_selectors_never_claims_completion(self) -> None:
        """The actual milestone gate must reject absent genuine live resources."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-M4-EXIT"]
        self.assertEqual("operational", routine["status"])
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M4-EXIT"],
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath},
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertIn(result.returncode, (1, 3), result.stdout + result.stderr)
        self.assertNotIn("PASSED", result.stdout)
        self.assertIn("M4 CURRENT EXIT:", result.stdout)

    def test_mutation_baseline_runs_without_caller_pythonpath(self) -> None:
        """The actual selected policy suite must run in a clean caller context."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_mutation import baseline_policy_command

        result = subprocess.run(
            baseline_policy_command(),
            cwd=REPOSITORY_ROOT,
            env={"PATH": os.defpath, "PYTHONHASHSEED": "0"},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("passed", result.stdout)

    def test_m2_local_suite_selection_covers_real_backend_and_browser_boundaries(
        self,
    ) -> None:
        """The canonical runner must select the complete installed M2 boundary."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_test import POST_M2_OWNER_BOUNDARIES, m2_local_suite_commands

        commands = m2_local_suite_commands()
        self.assertEqual(
            {
                "argon2_budget",
                "backend",
                "p02_all",
                "p02_security",
                "p02_hostile_resource",
            },
            set(commands),
        )
        argon2_budget = commands["argon2_budget"]
        self.assertIn(
            "backend/tests/integration/identity_access/test_argon2_workload.py",
            argon2_budget,
        )
        backend = commands["backend"]
        self.assertIn("backend/tests", backend)
        self.assertIn("--import-mode=importlib", backend)
        self.assertIn("--ignore=backend/tests/live", backend)
        self.assertIn(
            "--ignore=backend/tests/integration/identity_access/test_argon2_workload.py",
            backend,
        )
        self.assertIn(
            "--ignore=backend/tests/runtime_observation/integration/test_real_linux_commit.py",
            backend,
        )
        for path in POST_M2_OWNER_BOUNDARIES:
            self.assertIn(f"--ignore={path}", backend)
        self.assertNotIn("-k", backend)
        self.assertFalse(any(value.startswith("--deselect") for value in backend))
        for key, scenario in (
            ("p02_all", "all"),
            ("p02_security", "security_boundary"),
            ("p02_hostile_resource", "hostile_resource"),
        ):
            command = commands[key]
            self.assertEqual(scenario, command[-2])
            self.assertEqual("--no-build", command[-1])
            self.assertTrue((REPOSITORY_ROOT / command[1]).is_file())
        browser_test = (
            REPOSITORY_ROOT / "frontend/tests/browser/p02/security_boundary.mjs"
        )
        self.assertTrue(browser_test.is_file())

    def test_tool_suites_use_the_admitted_dependency_complete_python(self) -> None:
        """M5 tool imports must not be launched with dependency-empty system Python."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_test import BACKEND_PYTHON, tool_test_command

        command = tool_test_command("tools.automation.test_run")
        self.assertEqual(str(BACKEND_PYTHON), command[0])
        self.assertEqual(
            ["-m", "unittest", "tools.automation.test_run"], command[1:]
        )

    def test_m2_local_evidence_does_not_claim_universal_historical_tdd(self) -> None:
        """A passing current gate cannot invent Reds for prior UI corrections."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_test import m2_local_acceptance_ids

        accepted = m2_local_acceptance_ids()
        self.assertNotIn("AC-TEST-001", accepted)
        self.assertNotIn("AC-UI-001", accepted)
        self.assertIn("AC-TEST-003", accepted)

    def test_clean_clone_blocks_missing_owner_local_m0_executable(self) -> None:
        """A fresh real checkout must classify absent M0 custody tooling as Blocked."""
        with tempfile.TemporaryDirectory(prefix="agentmonitor-clean-gate-") as raw:
            checkout = Path(raw) / "checkout"
            clone = subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-hardlinks",
                    str(REPOSITORY_ROOT),
                    str(checkout),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, clone.returncode, "fresh local Git clone failed")
            self.assertFalse((checkout / ".venv-m0-g1/bin/python").exists())
            copy2(RUNNER, checkout / "tools/automation/run.py")
            copy2(CATALOG, checkout / "tools/automation/routines.toml")
            copy2(
                REPOSITORY_ROOT
                / "tools/automation/implementations/auto_claude_poll.py",
                checkout / "tools/automation/implementations/auto_claude_poll.py",
            )
            copy2(
                REPOSITORY_ROOT
                / "tools/automation/implementations/auto_claude_managed.py",
                checkout / "tools/automation/implementations/auto_claude_managed.py",
            )
            copy2(
                REPOSITORY_ROOT
                / "tools/automation/implementations/auto_claude_connect.py",
                checkout / "tools/automation/implementations/auto_claude_connect.py",
            )
            copy2(
                REPOSITORY_ROOT
                / "tools/automation/implementations/auto_dashboard_provider_filter.py",
                checkout
                / "tools/automation/implementations/auto_dashboard_provider_filter.py",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(checkout / "tools/automation/run.py"),
                    "AUTO-M0-G1-EXIT",
                    "--root",
                    str(checkout),
                ],
                cwd=checkout,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(3, result.returncode, "missing M0 tool was not Blocked")
            self.assertIn("AUTO-M0-G1-EXIT: BLOCKED", result.stdout)
            self.assertNotIn("PASSED", result.stdout)

    def test_evidence_rows_validate_v1_contract_and_unrun_provenance(self) -> None:
        """Pure evidence policy rejects a claimed pass without runtime context."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from evidence import evidence_row

        when = datetime(2026, 9, 20, tzinfo=UTC)
        with self.assertRaises(ValueError):
            evidence_row(
                test_id="FND-QUALITY-001",
                command_id="AUTO-QUALITY",
                boundary="local static quality",
                status="Passed",
                versions=(),
                recorded_at=when,
            )
        not_run = evidence_row(
            test_id="FND-CI-001",
            command_id="AUTO-TEST",
            boundary="hosted GitLab pipeline",
            status="Not Run",
            versions=(),
            recorded_at=when,
        )
        self.assertEqual("CTR-FND-008", not_run["contract_id"])
        self.assertEqual([], not_run["environment_versions"])
        self.assertIsNone(not_run["red_reference"])
        self.assertIsNone(not_run["green_reference"])
        self.assertIsNone(not_run["refactor_reference"])
        self.assertEqual("pending_independent_review", not_run["reviewer"])

    def test_local_evidence_cannot_claim_owner_countersigned_live_acceptance(
        self,
    ) -> None:
        """A local-only helper has no owner signature and cannot certify AC-TEST-004."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from evidence import evidence_row

        with self.assertRaisesRegex(
            ValueError, "owner_live_acceptance_requires_countersign"
        ):
            evidence_row(
                test_id="M2-LOCAL-EVIDENCE",
                command_id="AUTO-TEST",
                boundary="local SQLite, HTTP, and browser only",
                status="Passed",
                versions=(("python", "3.12.3"),),
                acceptance_ids=("AC-TEST-004",),
            )

    def test_evidence_versions_match_the_real_node_command(self) -> None:
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from evidence import actual_tool_versions

        result = subprocess.run(
            ["node", "--version"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual(
            (("node", result.stdout.strip().removeprefix("v")),),
            actual_tool_versions(("node",)),
        )

    def test_governance_policy_checks_leave_tracked_checkout_untouched(self) -> None:
        """Two concurrent real test processes must not rewrite shared source."""
        paths = (
            REPOSITORY_ROOT / "frontend/src/main.tsx",
            REPOSITORY_ROOT / "backend/pyproject.toml",
        )
        before = tuple(path.stat().st_mtime_ns for path in paths)
        selection = (
            "tools.automation.test_run.AutomationRoutineTests.test_source_policy_rejects_prohibited_double_import",
            "tools.automation.test_run.AutomationRoutineTests.test_manifest_policy_rejects_unapproved_backend_section",
            "tools.automation.test_run.AutomationRoutineTests.test_source_policy_rejects_prefixed_secret_value",
        )
        children = [
            subprocess.Popen(
                [sys.executable, "-m", "unittest", *selection],
                cwd=REPOSITORY_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        for child in children:
            output, error = child.communicate(timeout=15)
            self.assertEqual(0, child.returncode, output + error)
        self.assertEqual(before, tuple(path.stat().st_mtime_ns for path in paths))

    def test_frontend_typecheck_covers_application_and_tooling(self) -> None:
        """The published command must typecheck the built React source too."""
        import json

        manifest = json.loads((REPOSITORY_ROOT / "frontend/package.json").read_text())
        command = manifest["scripts"]["typecheck"]
        self.assertIn("tsconfig.app.json", command)
        self.assertIn("tsconfig.node.json", command)
        compiler = str(REPOSITORY_ROOT / "frontend/node_modules/.bin/tsc")
        application_files = subprocess.run(
            [compiler, "--project", "frontend/tsconfig.app.json", "--listFilesOnly"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            0,
            application_files.returncode,
            application_files.stdout + application_files.stderr,
        )
        self.assertIn("frontend/src/app/App.tsx", application_files.stdout)
        self.assertIn("frontend/src/main.tsx", application_files.stdout)
        result = subprocess.run(
            ["npm", "--prefix", "frontend", "run", "typecheck"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_real_app_type_fault_fails_the_published_command(self) -> None:
        """Real pre-fix config and current app compile in an isolated copy."""
        frontend = REPOSITORY_ROOT / "frontend"
        with tempfile.TemporaryDirectory(prefix="agentmonitor-type-fault-") as root:
            isolated = Path(root)
            for name in (
                "package.json",
                "tsconfig.json",
                "tsconfig.node.json",
                "vite.config.ts",
            ):
                copy2(frontend / name, isolated / name)
            copy2(
                frontend / "tests/typecheck/tsconfig.app.pre-fix.json",
                isolated / "tsconfig.app.json",
            )
            copytree(frontend / "src", isolated / "src")
            (isolated / "node_modules").symlink_to(
                frontend / "node_modules", target_is_directory=True
            )
            result = subprocess.run(
                ["npm", "run", "typecheck"],
                cwd=isolated,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("TS2882", result.stdout + result.stderr)

    def test_source_policy_rejects_prohibited_double_import(self) -> None:
        """Pure policy regression; the real checkout is scanned by AUTO-QUALITY."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_quality import source_is_allowed

        prohibited = "from unittest import "
        prohibited += "mock\n"
        self.assertFalse(source_is_allowed(prohibited))
        self.assertTrue(source_is_allowed("export const appVersion = '1.0.0';\n"))

    def test_browser_scenarios_are_in_the_real_source_control_set(self) -> None:
        """The canonical local scan must include the installed browser scenarios."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_quality import checked_source_paths

        browser = REPOSITORY_ROOT / "frontend/tests/browser/p02/security_boundary.mjs"
        self.assertTrue(browser.is_file())
        self.assertIn(browser, checked_source_paths())

    def test_source_policy_rejects_browser_response_interception(self) -> None:
        """A browser test must not substitute a response for real HTTP."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_quality import source_is_allowed

        intercepted = "await page." + "route('**/api/v1/**', handler);"
        context_intercepted = "await context." + "route('**/api/v1/**', handler);"
        fabricated = "route." + "fulfill({status: 200});"
        self.assertFalse(source_is_allowed(intercepted))
        self.assertFalse(source_is_allowed(context_intercepted))
        self.assertFalse(source_is_allowed(fabricated))

    def test_manifest_policy_rejects_unapproved_backend_section(
        self,
    ) -> None:
        """Pure section policy; production checks the real manifest and lock."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_quality import approved_manifest_sections

        project: dict[str, object] = {
            "name": "agentmonitor",
            "version": "0.0.0",
            "requires-python": ">=3.12",
            "dependencies": [],
        }
        self.assertTrue(
            approved_manifest_sections(
                {"project": project, "dependency-groups": {"dev": []}}
            )
        )
        self.assertFalse(
            approved_manifest_sections(
                {
                    "project": {**project, "optional-dependencies": {}},
                    "dependency-groups": {"dev": []},
                }
            )
        )

    def test_source_policy_rejects_prefixed_secret_value(self) -> None:
        """A test-setting prefix never exempts a value assigned to a secret field."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_quality import source_is_allowed

        prohibited = "pass" + "word = 'AGENTMONITOR_TEST_SENSITIVE_VALUE'\n"
        self.assertFalse(source_is_allowed(prohibited))

    def test_source_policy_allows_prompt_labels_but_rejects_secret_literals(
        self,
    ) -> None:
        """TTY prompt copy is not a credential assignment or object value."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_quality import source_is_allowed

        self.assertTrue(source_is_allowed('prompt = b"Enter dashboard password: "\n'))
        self.assertTrue(
            source_is_allowed(
                'prompt_seen = read_until(terminal, b"Enter dashboard password:", '
                "captured)\n"
            )
        )
        self.assertFalse(source_is_allowed('password = "constructed-policy-value"\n'))
        object_field = '"' + "password" + '": "constructed-policy-value"\n'
        self.assertFalse(source_is_allowed(object_field))

    def test_frontend_inventory_policy_rejects_extraneous_installed_package(
        self,
    ) -> None:
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_build import installed_inventory_approved

        expected = {"node_modules/react"}
        self.assertTrue(installed_inventory_approved(expected, expected))
        self.assertFalse(
            installed_inventory_approved(
                expected, expected | {"node_modules/unreviewed-package"}
            )
        )

    def test_frontend_package_policy_rejects_stale_installed_optional_package(
        self,
    ) -> None:
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_build import installed_package_approved

        record: dict[str, object] = {
            "version": "1.0.0",
            "license": "MIT",
            "optional": True,
        }
        self.assertTrue(installed_package_approved(record, None))
        self.assertTrue(installed_package_approved(record, "1.0.0"))
        self.assertFalse(installed_package_approved(record, "0.0.0-stale"))

    def test_browser_environment_resolves_the_actual_playwright_node_shebang(
        self,
    ) -> None:
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        implementation = (
            REPOSITORY_ROOT / "tools/automation/implementations/auto_test.py"
        )
        spec = spec_from_file_location("real_auto_test", implementation)
        assert spec is not None and spec.loader is not None
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        node = which("node")
        self.assertIsNotNone(node)
        environment = module.browser_environment("http://127.0.0.1:1")
        self.assertIn(str(Path(node).parent), environment["PATH"])
        result = subprocess.run(
            [
                str(REPOSITORY_ROOT / "frontend/node_modules/.bin/playwright"),
                "--version",
            ],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_frontend_input_validation_rejects_disallowed_direct_license(self) -> None:
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_build import direct_package_approved

        self.assertTrue(direct_package_approved("react", "19.3.0", "19.3.0", "MIT"))
        self.assertTrue(
            direct_package_approved("swagger-ui-dist", "5.33.0", "5.33.0", "Apache-2.0")
        )
        self.assertFalse(
            direct_package_approved("swagger-ui-dist", "5.33.0", "5.34.0", "Apache-2.0")
        )
        self.assertFalse(
            direct_package_approved("react", "19.3.0", "19.3.0", "GPL-3.0-only")
        )

    def test_m2_admitted_argon2_graph_matches_real_locked_install(self) -> None:
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_quality import verify_backend_inputs

        self.assertTrue(verify_backend_inputs())

    def test_m1_quality_and_build_report_required_local_controls(self) -> None:
        for script, marker in (
            ("auto_quality.py", "M1 LOCAL CONTROLS: PASSED"),
            ("auto_build.py", "FRONTEND INPUTS: PASSED"),
        ):
            with self.subTest(script=script):
                result = subprocess.run(
                    [
                        sys.executable,
                        "tools/automation/implementations/" + script,
                    ],
                    cwd=REPOSITORY_ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertIn(marker, result.stdout)

    def test_m1_routines_resolve_from_canonical_catalog(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)

        self.assertEqual(
            ["python3", "tools/automation/implementations/auto_test.py"],
            catalog["AUTO-TEST"]["implementation_command"],
        )
        self.assertEqual(
            ["python3", "tools/automation/implementations/auto_quality.py"],
            catalog["AUTO-QUALITY"]["implementation_command"],
        )
        self.assertEqual(
            ["python3", "tools/automation/implementations/auto_build.py"],
            catalog["AUTO-BUILD"]["implementation_command"],
        )
        self.assertEqual([], validate_catalog(REPOSITORY_ROOT, catalog))

    def test_m3_live_browser_gate_is_cataloged_fail_closed(self) -> None:
        """The owner-data browser slice has one executable canonical gate."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-M3-LIVE"]

        self.assertEqual("operational", routine["status"])
        self.assertEqual(
            [
                "backend/.venv/bin/python",
                "tools/automation/implementations/auto_m3_live.py",
            ],
            routine["implementation_command"],
        )
        self.assertIn("real owner", routine["scope"])
        self.assertEqual([], routine["blockers"])

    def test_m3_mutation_gate_is_cataloged_fail_closed(self) -> None:
        """Critical M3 pure policies have one executable mutation gate."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-MUTATION"]

        self.assertEqual("operational", routine["status"])
        self.assertEqual(
            [
                "backend/.venv/bin/python",
                "tools/automation/implementations/auto_mutation.py",
            ],
            routine["implementation_command"],
        )
        self.assertIn("M3", routine["scope"])
        self.assertIn("critical pure", routine["scope"])
        self.assertEqual([], routine["blockers"])

    def test_mutation_summary_policy_rejects_every_non_killed_result(self) -> None:
        """A score alone cannot conceal a survivor or unavailable mutant."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_mutation import mutation_summary_passes

        killed = {
            "total": 4,
            "killed": 4,
            "survived": 0,
            "no_tests": 0,
            "skipped": 0,
            "suspicious": 0,
            "timeout": 0,
            "check_was_interrupted_by_user": 0,
            "segfault": 0,
        }
        self.assertTrue(mutation_summary_passes(killed))
        for status in (
            "survived",
            "no_tests",
            "skipped",
            "suspicious",
            "timeout",
            "check_was_interrupted_by_user",
            "segfault",
        ):
            with self.subTest(status=status):
                result = {**killed, "killed": 3, status: 1}
                self.assertFalse(mutation_summary_passes(result))
        equivalent = {**killed, "killed": 3, "survived": 1}
        self.assertTrue(
            mutation_summary_passes(equivalent, accepted_equivalent_count=1)
        )
        self.assertFalse(
            mutation_summary_passes(equivalent, accepted_equivalent_count=0)
        )
        self.assertFalse(mutation_summary_passes({**killed, "total": 0, "killed": 0}))

    def test_mutation_equivalence_is_bound_to_contract_invariants(self) -> None:
        """Equivalent survivors cannot outlive the invariants proving equivalence."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_mutation import equivalence_invariants_match

        contract = (
            REPOSITORY_ROOT
            / "backend/src/agentmonitor/contracts/runtime_observation_v1.py"
        ).read_bytes()
        self.assertTrue(equivalence_invariants_match(contract))
        self.assertFalse(
            equivalence_invariants_match(contract + b"\n# invariant drift\n")
        )

    def test_mutation_config_exactly_matches_runner_targets_and_tests(self) -> None:
        """The executed mutation surface cannot drift from its declared surface."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_mutation import mutation_config_matches

        manifest = tomllib.loads(
            (REPOSITORY_ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
        )
        config = manifest["tool"]["mutmut"]
        self.assertTrue(mutation_config_matches(config))

        extra_target = {**config, "only_mutate": [*config["only_mutate"], "extra.py"]}
        self.assertFalse(mutation_config_matches(extra_target))
        missing_test = {
            **config,
            "pytest_add_cli_args_test_selection": config[
                "pytest_add_cli_args_test_selection"
            ][:-1],
        }
        self.assertFalse(mutation_config_matches(missing_test))

    def test_m3_exit_actively_runs_the_mutation_gate(self) -> None:
        """M3 completion cannot bypass the admitted critical-policy gate."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_m3_current_exit import LOCAL_ROUTINES, PRE_BROWSER_ROUTINES, main

        self.assertEqual(
            ("AUTO-BUILD",),
            tuple(routine for _lane, routine in PRE_BROWSER_ROUTINES),
        )
        self.assertEqual(
            (
                "AUTO-M3-TEST",
                "AUTO-QUALITY",
                "AUTO-MUTATION",
                "AUTO-DOCS-CHECK",
                "AUTO-GIT-PREFLIGHT",
            ),
            tuple(routine for _lane, routine in LOCAL_ROUTINES),
        )
        self.assertIn("for lane, routine in PRE_BROWSER_ROUTINES", getsource(main))
        self.assertIn("for lane, routine in LOCAL_ROUTINES", getsource(main))

    def test_m3_mutmut_dependency_graph_names_the_full_locked_closure(self) -> None:
        """Dependency verification includes every package in the selected closure."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_quality import M3_MUTMUT_GRAPH

        self.assertEqual(
            {
                "click": "8.5.0",
                "coverage": "7.16.1",
                "iniconfig": "2.3.0",
                "libcst": "1.9.0",
                "linkify-it-py": "2.2.0",
                "markdown-it-py": "4.2.0",
                "mdit-py-plugins": "0.6.1",
                "mdurl": "0.1.2",
                "mutmut": "3.8.0",
                "packaging": "26.3",
                "platformdirs": "4.11.12",
                "pluggy": "1.6.0",
                "pygments": "2.21.0",
                "pytest": "9.1.1",
                "pyyaml": "6.0.3",
                "rich": "15.0.0",
                "setproctitle": "1.3.7",
                "textual": "8.2.8",
                "typing-extensions": "4.16.0",
            },
            M3_MUTMUT_GRAPH,
        )

    def test_m3_exit_gate_is_distinct_and_cataloged_fail_closed(self) -> None:
        """M3 completion uses the safe current read-only successor gate."""
        catalog = load_catalog(REPOSITORY_ROOT)
        routine = catalog["AUTO-M3-EXIT"]

        self.assertEqual("operational", routine["status"])
        self.assertEqual(
            [
                "backend/.venv/bin/python",
                "tools/automation/implementations/auto_m3_current_exit.py",
            ],
            routine["implementation_command"],
        )
        self.assertIn("clean-revision build", routine["scope"])
        self.assertIn("fresh scheduled", routine["scope"])
        self.assertIn("account-scoped runtime", routine["scope"])
        self.assertEqual([], routine["blockers"])

    def test_m3_exit_lineage_rejects_non_utc_gate_time(self) -> None:
        """Freshness comparisons use one exact UTC timeline."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_m3_exit import (
            M3ExitErrorV1,
            M3FreshLineageV1,
            verify_fresh_same_account_v1,
        )

        non_utc = datetime(2026, 9, 24, 13, tzinfo=timezone(timedelta(hours=1)))
        later = datetime(2026, 9, 24, 13, 1, tzinfo=timezone(timedelta(hours=1)))
        lineage = M3FreshLineageV1(
            gate_started_at=non_utc,
            quota_account_id="account-one",
            quota_run_id="quota-run",
            quota_requested_at=later,
            quota_completed_at=later,
            quota_observation_ids=("quota-observation",),
            runtime_account_id="account-one",
            runtime_run_id="runtime-run",
            runtime_requested_at=later,
            runtime_completed_at=later,
            runtime_observed_at=later,
            runtime_source_id="claude.otel.metrics.http-json.v1",
            runtime_state="succeeded",
            runtime_observation_ids=("runtime-observation",),
        )

        with self.assertRaisesRegex(M3ExitErrorV1, "m3_exit_fresh_observation_missing"):
            verify_fresh_same_account_v1(lineage)

    def test_m3_exit_child_commands_preserve_the_owner_terminal_environment(
        self,
    ) -> None:
        """The real Claude and Git tools retain their normal inherited environment."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_m3_exit import _run_checkout_command

        variable = "AGENTMONITOR_M3_INHERITED_ENVIRONMENT_TEST"
        previous = os.environ.get(variable)
        os.environ[variable] = "present"
        try:
            _run_checkout_command(
                [
                    sys.executable,
                    "-c",
                    (
                        "import os,sys; "
                        "sys.exit(0 if os.environ.get("
                        f"'{variable}') == 'present' else 7)"
                    ),
                ],
                timeout=5,
            )
        finally:
            if previous is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = previous

    def test_m3_exit_uses_the_approved_schema_validation_runtime(self) -> None:
        """M0 authorization cannot silently use an unreviewed jsonschema build."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_m3_exit import M0_SCHEMA_PYTHON

        self.assertEqual(REPOSITORY_ROOT / ".venv-m0-g1/bin/python", M0_SCHEMA_PYTHON)
        result = subprocess.run(
            [
                str(M0_SCHEMA_PYTHON),
                "-c",
                "from importlib.metadata import version; print(version('jsonschema'))",
            ],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("4.26.0", result.stdout.strip())

    def test_m3_exit_runs_the_real_identity_evidence_check_after_runtime(self) -> None:
        """The live exit cannot accept a stale or detached provider binding."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_m3_exit import identity_evidence_check

        data_root = Path("/owner-selected/agentmonitor-data")
        command, environment = identity_evidence_check(data_root, "account-one")

        self.assertEqual(
            [
                str(REPOSITORY_ROOT / "backend/.venv/bin/python"),
                "-m",
                "pytest",
                "backend/tests/live/claude/test_provider_identity_evidence.py",
                "-q",
                "--tb=short",
            ],
            command,
        )
        self.assertEqual(str(data_root), environment["AGENTMONITOR_TEST_DATA_ROOT"])
        self.assertEqual("account-one", environment["AGENTMONITOR_TEST_ACCOUNT_ID"])
        self.assertEqual(
            str(REPOSITORY_ROOT / "backend/src"), environment["PYTHONPATH"]
        )
        self.assertNotIn("CLAUDE", " ".join(environment))
        from auto_m3_exit import main

        main_source = getsource(main)
        self.assertIn("identity_evidence_check(", main_source)
        self.assertIn("data_root, account_id.value", main_source)

    def test_git_preflight_catalog_does_not_claim_remote_readiness(self) -> None:
        routine = load_catalog(REPOSITORY_ROOT)["AUTO-GIT-PREFLIGHT"]
        self.assertEqual("operational_limited", routine["status"])
        self.assertIn("local commit", routine["scope"])
        self.assertTrue(
            any("push/release" in blocker for blocker in routine["blockers"])
        )

    def test_catalog_index_rejects_duplicate_routine_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate routine ID"):
            index_routines(
                [
                    {"id": "AUTO-EXAMPLE", "status": "blocked"},
                    {"id": "AUTO-EXAMPLE", "status": "operational"},
                ]
            )

    def test_operational_limited_routine_requires_named_limitations(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)
        catalog["AUTO-TEST"] = {
            **catalog["AUTO-TEST"],
            "status": "operational_limited",
            "blockers": [],
        }

        self.assertIn(
            "AUTO-TEST: operational_limited routine must name blockers",
            validate_catalog(REPOSITORY_ROOT, catalog),
        )

    def test_real_catalog_defines_every_mandatory_routine(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)

        self.assertEqual(
            {
                "AUTO-PLAN-CHECK",
                "AUTO-M0-G0",
                "AUTO-M0-G1-CONTRACT",
                "AUTO-M0-G1-FINALIZE",
                "AUTO-M0-G1-EXIT",
                "AUTO-M0-PREFLIGHT",
                "AUTO-M0-POSTFLIGHT",
                "AUTO-M0-LEDGER",
                "AUTO-DOCS-CHECK",
                "AUTO-M3-LIVE",
                "AUTO-M3-EXIT",
                "AUTO-M4-EXIT",
                "AUTO-M5-ARCHIVE-PREREQUISITES",
                "AUTO-M5-OWNER-OUTCOMES",
                "AUTO-M5-QUOTA-WITNESS",
                "AUTO-M5-ALERT-WITNESS",
                "AUTO-M5-EXIT",
                "AUTO-CLAUDE-POLL",
                "AUTO-CLAUDE-MANAGED",
                "AUTO-CLAUDE-CONNECT",
                "AUTO-DASHBOARD-PROVIDER-FILTER",
                "AUTO-LAN-DASHBOARD",
                "AUTO-ACCOUNT-AGENTS",
                "AUTO-M3-TEST",
                "AUTO-MUTATION",
                "AUTO-TEST",
                "AUTO-QUALITY",
                "AUTO-GIT-PREFLIGHT",
                "AUTO-BUILD",
                "AUTO-MIGRATE",
                "AUTO-DEPLOY",
                "AUTO-BACKUP",
                "AUTO-RESTORE",
                "AUTO-RELEASE",
            },
            set(catalog),
        )
        self.assertEqual([], validate_catalog(REPOSITORY_ROOT, catalog))

    def test_m0_g0_approval_gate_passes_for_the_exact_real_plan(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M0-G0"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("M0 G0 APPROVAL: PASSED", result.stdout)

    def test_m0_g1_contract_gate_checks_the_real_checkout_bundle(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M0-G1-CONTRACT"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("AUTO-M0-G1-CONTRACT: PASSED", result.stdout)

    def test_m0_scenario_preflight_fails_closed_until_g1_is_implemented(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M0-PREFLIGHT"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(3, result.returncode, result.stdout + result.stderr)
        self.assertIn("BLOCKED", result.stdout)
        self.assertIn(
            "Red-Green-refactor preflight validator implementation", result.stdout
        )
        self.assertNotIn("PASSED", result.stdout)

    def test_m0_g1_dispatch_preserves_the_real_exit_status(self) -> None:
        direct_command = load_catalog(REPOSITORY_ROOT)["AUTO-M0-G1-EXIT"][
            "implementation_command"
        ]
        if not (REPOSITORY_ROOT / direct_command[0]).is_file():
            result = subprocess.run(
                [sys.executable, str(RUNNER), "AUTO-M0-G1-EXIT"],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            self.assertIn("AUTO-M0-G1-EXIT: BLOCKED", result.stdout)
            self.assertNotIn("PASSED", result.stdout)
            return
        direct = subprocess.run(
            direct_command,
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M0-G1-EXIT"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            direct.returncode, result.returncode, result.stdout + result.stderr
        )
        self.assertIn(direct.stdout, result.stdout)
        if direct.returncode == 2:
            self.assertIn("AUTO-M0-G1-EXIT: FAILED", result.stdout)
            self.assertNotIn("AUTO-M0-G1-EXIT: PASSED", result.stdout)
        elif direct.returncode == 3:
            self.assertIn("AUTO-M0-G1-EXIT: BLOCKED", result.stdout)
            self.assertNotIn("AUTO-M0-G1-EXIT: PASSED", result.stdout)
        else:
            self.assertEqual(0, direct.returncode)
            self.assertIn("M0 G1 FINISHED", result.stdout)
            self.assertIn("AUTO-M0-G1-EXIT: PASSED", result.stdout)

    def test_m0_result_gates_fail_closed_until_g1_is_implemented(self) -> None:
        for routine_id in ("AUTO-M0-POSTFLIGHT", "AUTO-M0-LEDGER"):
            with self.subTest(routine_id=routine_id):
                result = subprocess.run(
                    [sys.executable, str(RUNNER), routine_id],
                    cwd=REPOSITORY_ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )

                self.assertEqual(3, result.returncode, result.stdout + result.stderr)
                self.assertIn("BLOCKED", result.stdout)
                if routine_id == "AUTO-M0-LEDGER":
                    self.assertIn(
                        "Red-Green-refactor ledger validator implementation",
                        result.stdout,
                    )
                self.assertNotIn("PASSED", result.stdout)

    def test_blocked_routine_fails_closed_in_the_real_checkout(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-DEPLOY"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(3, result.returncode)
        self.assertIn("BLOCKED", result.stdout)
        self.assertNotIn("PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
