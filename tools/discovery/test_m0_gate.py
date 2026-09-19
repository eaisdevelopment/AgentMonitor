"""Real-checkout tests for the restricted Milestone 0 G0 approval gate."""

from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from m0_gate import APPROVAL_PATH, PROHIBITED_AUTHORITY_FLAGS, validate_g0  # noqa: E402


class MilestoneZeroGateTests(unittest.TestCase):
    def test_exact_real_m0_plan_has_complete_g0_approval(self) -> None:
        violations = validate_g0(REPOSITORY_ROOT)

        self.assertEqual([], violations, "\n".join(violations))

    def test_real_g0_approval_grants_no_execution_or_access_authority(self) -> None:
        with (REPOSITORY_ROOT / APPROVAL_PATH).open("rb") as stream:
            approval = tomllib.load(stream)

        for flag in PROHIBITED_AUTHORITY_FLAGS:
            self.assertIs(
                False,
                approval[flag],
                f"G0 must leave {flag} false",
            )


if __name__ == "__main__":
    unittest.main()
