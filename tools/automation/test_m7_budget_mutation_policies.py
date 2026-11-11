"""Kill seven critical M7 regressions in isolated copies of actual source.

The subprocesses run only existing pure-domain tests with constructed no-I/O
values. This is mutation evidence, not a provider, storage or browser test.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from shutil import copy2, copytree, ignore_patterns

from tools.automation.implementations.auto_mutation import _run

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
PURE_TESTS = (
    Path("tests/capacity/pure/test_budget_exact_arithmetic.py"),
    Path("tests/capacity/pure/test_budget_money.py"),
    Path("tests/capacity/pure/test_budget_report_selection.py"),
)
QUANTITY = Path("src/agentmonitor/contracts/common_quantity_v1.py")
MONEY = Path("src/agentmonitor/modules/capacity/domain/budget_money.py")
REPORTS = Path("src/agentmonitor/modules/capacity/domain/budget_reports.py")
MUTATIONS = (
    (
        "decimal_context_rounding",
        QUANTITY,
        'return Decimal(f"{self.coefficient}e-{self.scale}")',
        "return Decimal(self.coefficient).scaleb(-self.scale)",
    ),
    (
        "signed_adjustment_clamped",
        MONEY,
        "total = sum(_aligned(value.amount, scale) for value in values)",
        "total = sum(max(0, _aligned(value.amount, scale)) for value in values)",
    ),
    (
        "currency_guard_bypassed",
        MONEY,
        "if left.currency != right.currency:",
        "if False:",
    ),
    (
        "ties_round_up_instead_of_even",
        MONEY,
        "remainder * 2 == denominator and quotient % 2 == 1",
        "remainder * 2 == denominator",
    ),
    ("oldest_report_selected", REPORTS, "reverse=True,", "reverse=False,"),
    (
        "partial_report_admitted",
        REPORTS,
        'if item.report.completeness == "complete"',
        'if item.report.completeness in {"complete", "partial"}',
    ),
    (
        "empty_revision_resurrects_old_charge",
        REPORTS,
        'if item.report.completeness == "complete"',
        'if item.report.completeness == "complete" and item.report.cost_buckets',
    ),
)


class M7BudgetMutationTests(unittest.TestCase):
    def test_existing_pure_tests_kill_critical_budget_regressions(self) -> None:
        """M7-CAP-MUT-001; M7-MATH-04/05/09/10/12/13/14."""
        with tempfile.TemporaryDirectory(prefix="agentmonitor-m7-mutation-") as raw:
            workspace = Path(raw)
            copy2(BACKEND / "pyproject.toml", workspace / "pyproject.toml")
            copytree(
                BACKEND / "src",
                workspace / "src",
                ignore=ignore_patterns("__pycache__", "*.pyc"),
            )
            for relative in PURE_TESTS:
                target = workspace / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                copy2(BACKEND / relative, target)
            copy2(
                ROOT / "tools/automation/pytest_no_skip.py",
                workspace / "pytest_no_skip.py",
            )
            environment = {
                "PATH": os.defpath,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
            }
            report = workspace / "result.xml"
            command = [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--tb=short",
                "-p",
                "no:cacheprovider",
                "-p",
                "pytest_no_skip",
                f"--junitxml={report}",
                *(str(path) for path in PURE_TESTS),
            ]
            baseline = _run(command, cwd=workspace, environment=environment)
            self.assertEqual(
                baseline.returncode,
                0,
                "Clean pure baseline failed: "
                + (baseline.stdout + baseline.stderr)[-4000:],
            )
            baseline_cases = tuple(ET.parse(report).getroot().iter("testcase"))
            self.assertGreater(len(baseline_cases), 0)
            self.assertFalse(
                any(
                    case.find(tag) is not None
                    for case in baseline_cases
                    for tag in ("failure", "error", "skipped")
                )
            )
            print(
                f"M7 MUTATION BASELINE: {len(baseline_cases)} pure cases passed",
                flush=True,
            )
            for name, relative, original, replacement in MUTATIONS:
                with self.subTest(mutation=name):
                    target = workspace / relative
                    content = target.read_text()
                    self.assertEqual(
                        content.count(original), 1, "Mutation target drifted"
                    )
                    try:
                        target.write_text(content.replace(original, replacement, 1))
                        mutant = _run(command, cwd=workspace, environment=environment)
                        self.assertEqual(
                            mutant.returncode,
                            1,
                            f"{name}: survived or failed outside assertion execution",
                        )
                        cases = tuple(ET.parse(report).getroot().iter("testcase"))
                        self.assertEqual(len(cases), len(baseline_cases))
                        self.assertFalse(
                            any(
                                case.find(tag) is not None
                                for case in cases
                                for tag in ("error", "skipped")
                            )
                        )
                        failures = tuple(
                            failure
                            for case in cases
                            for failure in case.findall("failure")
                        )
                        self.assertTrue(
                            any(
                                failure.get("message", "").startswith(
                                    ("assert ", "AssertionError", "Failed:")
                                )
                                for failure in failures
                            ),
                            f"{name}: no behavioral assertion killed the mutant",
                        )
                        print(f"M7 MUTATION {name}: KILLED", flush=True)
                    finally:
                        target.write_text(content)


if __name__ == "__main__":
    unittest.main()
