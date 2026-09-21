"""Real-checkout tests for the canonical AgentMonitor routine dispatcher."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from shutil import copy2, copytree, which

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPOSITORY_ROOT / "tools/automation/run.py"
sys.path.insert(0, str(RUNNER.parent))

from run import index_routines, load_catalog, validate_catalog  # noqa: E402


class AutomationRoutineTests(unittest.TestCase):
    def test_m2_local_suite_selection_covers_real_backend_and_browser_boundaries(
        self,
    ) -> None:
        """The canonical runner must select the complete installed M2 boundary."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_test import m2_local_suite_commands

        commands = m2_local_suite_commands()
        self.assertEqual(
            {"backend", "p02_all", "p02_security", "p02_hostile_resource"},
            set(commands),
        )
        backend = commands["backend"]
        self.assertIn("backend/tests", backend)
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

    def test_m2_local_evidence_does_not_claim_universal_historical_tdd(self) -> None:
        """A passing current gate cannot invent Reds for prior UI corrections."""
        sys.path.insert(0, str(REPOSITORY_ROOT / "tools/automation/implementations"))
        from auto_test import m2_local_acceptance_ids

        accepted = m2_local_acceptance_ids()
        self.assertNotIn("AC-TEST-001", accepted)
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
        if direct.returncode:
            self.assertIn("AUTO-M0-G1-EXIT: FAILED", result.stdout)
            self.assertNotIn("AUTO-M0-G1-EXIT: PASSED", result.stdout)
        else:
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
