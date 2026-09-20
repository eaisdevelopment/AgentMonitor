"""Real-checkout tests for the canonical AgentMonitor routine dispatcher."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPOSITORY_ROOT / "tools/automation/run.py"
sys.path.insert(0, str(RUNNER.parent))

from run import index_routines, load_catalog, validate_catalog  # noqa: E402


class AutomationRoutineTests(unittest.TestCase):
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
        self.assertIn("Red-Green-refactor preflight validator implementation", result.stdout)
        self.assertNotIn("PASSED", result.stdout)

    def test_m0_g1_exit_passes_for_the_approved_real_controls(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M0-G1-EXIT"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
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
