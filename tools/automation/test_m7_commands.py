"""M7 routine evidence: actual checkout execution plus pure completion policy."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tools.automation.implementations.auto_m7 import CheckResult, evaluate_lane

ROOT = Path(__file__).resolve().parents[2]


class M7CanonicalExecutionTests(unittest.TestCase):
    def test_canonical_technical_command_reports_executed_and_missing_boundaries(self):
        """M7-GATE-001: a catalog placeholder cannot substitute for execution."""
        result = subprocess.run(
            [sys.executable, "tools/automation/run.py", "AUTO-M7-TEST"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if "NOT_RUN" in result.stdout:
            self.assertNotEqual(result.returncode, 0)
        self.assertIn("M7 CHECK pure:", result.stdout)
        self.assertIn("M7 CHECK registry_metadata:", result.stdout)
        self.assertNotIn(
            "M7 CHECK registry_metadata: NOT_RUN (m7_boundary_runner_not_implemented)",
            result.stdout,
        )
        self.assertIn("M7 CHECK registry_http:", result.stdout)


class M7CompletionPolicyTests(unittest.TestCase):
    """Constructed execution facts remain within this no-I/O policy boundary."""

    def test_empty_evidence_never_passes(self):
        self.assertEqual(evaluate_lane("pure", ()).status, "blocked")
        self.assertEqual(evaluate_lane("exit", ()).status, "blocked")

    def test_partial_checks_cannot_close_technical_or_exit(self):
        self.assertEqual(
            evaluate_lane("technical", (CheckResult("pure", "passed"),)).status,
            "blocked",
        )
        self.assertEqual(
            evaluate_lane("exit", (CheckResult("technical", "passed"),)).status,
            "blocked",
        )

    def test_metadata_slice_cannot_close_full_registry_flow(self):
        metadata = CheckResult("registry_metadata", "passed")
        self.assertEqual(
            evaluate_lane("registry_metadata", (metadata,)).status, "passed"
        )
        checks = (
            CheckResult("pure", "passed"),
            metadata,
            CheckResult("registry_http", "not_run"),
            CheckResult("persistence", "passed"),
            CheckResult("collection", "passed"),
            CheckResult("budget_http", "passed"),
            CheckResult("compatibility", "passed"),
            CheckResult("mutation", "passed"),
        )
        self.assertEqual(evaluate_lane("technical", checks).status, "blocked")

    def test_missing_or_unexecuted_boundary_is_not_a_pass(self):
        for status in ("blocked", "not_run"):
            with self.subTest(status=status):
                checks = (
                    CheckResult("technical", "passed"),
                    CheckResult("live", status),
                    CheckResult("browser", "passed"),
                    CheckResult("deploy", "passed"),
                )
                self.assertEqual(evaluate_lane("exit", checks).status, "blocked")

    def test_failure_is_preserved_even_when_other_evidence_is_missing(self):
        checks = (CheckResult("technical", "failed"),)
        self.assertEqual(evaluate_lane("exit", checks).status, "failed")

    def test_duplicate_and_foreign_checks_cannot_replace_required_boundaries(self):
        duplicate = (CheckResult("pure", "passed"), CheckResult("pure", "passed"))
        foreign = (CheckResult("subscription_quota", "passed"),)
        self.assertEqual(evaluate_lane("pure", duplicate).status, "failed")
        self.assertEqual(evaluate_lane("pure", foreign).status, "failed")

    def test_all_required_results_close_only_their_declared_scope(self):
        pure = evaluate_lane("pure", (CheckResult("pure", "passed"),))
        self.assertEqual((pure.lane, pure.status), ("pure", "passed"))
        checks = tuple(
            CheckResult(name, "passed")
            for name in ("technical", "live", "browser", "deploy")
        )
        self.assertEqual(evaluate_lane("exit", checks).status, "passed")

    def test_unknown_lane_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "m7_lane_unknown"):
            evaluate_lane("invented", ())


if __name__ == "__main__":
    unittest.main()
