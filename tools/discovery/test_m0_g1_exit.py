"""Real-checkout tests for the fail-closed M0 G1 exit gate."""

from __future__ import annotations

import hashlib
import importlib
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPOSITORY_ROOT / "tools/automation/run.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import m0_g1_exit  # noqa: E402

APPROVAL_PATH = (
    REPOSITORY_ROOT
    / "docs/plans/discovery/m0-g1-implementation-approval.toml"
)
CUSTODY_SETUP_PATH = (
    REPOSITORY_ROOT / "tools/discovery/m0_g1_custody.py"
)


class M0G1ExitGateTests(unittest.TestCase):
    def test_owner_approval_binds_exact_contract_without_live_authority(self) -> None:
        self.assertTrue(APPROVAL_PATH.is_file(), "implementation approval is missing")
        with APPROVAL_PATH.open("rb") as stream:
            approval = tomllib.load(stream)

        self.assertEqual("approved_for_implementation", approval["status"])
        self.assertEqual("M0-G1-CONTROLS", approval["contract_id"])
        self.assertEqual("0.3.0-draft", approval["contract_version"])
        for prefix in ("specification", "schema"):
            path = REPOSITORY_ROOT / approval[f"{prefix}_path"]
            content = path.read_bytes()
            self.assertEqual(
                hashlib.sha256(content).hexdigest(),
                approval[f"{prefix}_sha256"],
            )
            self.assertEqual(len(content), approval[f"{prefix}_bytes"])

        for flag in (
            "implementation_authorized",
            "dependency_installation_authorized",
            "scanner_execution_authorized",
        ):
            self.assertIs(True, approval[flag], flag)
        for flag in (
            "evidence_root_access_authorized",
            "provider_operations_authorized",
            "account_access_authorized",
            "g1_complete",
            "g2_authorized",
        ):
            self.assertIs(False, approval[flag], flag)

    def test_canonical_exit_gate_validates_the_approved_real_state(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER), "AUTO-M0-G1-EXIT"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("implementation approval: VERIFIED", result.stdout)
        self.assertIn("schema validator dependency: VERIFIED", result.stdout)
        self.assertIn("schema contract: VERIFIED", result.stdout)
        self.assertIn("local scanner verification: VERIFIED", result.stdout)
        self.assertIn("custody selection metadata: VERIFIED", result.stdout)
        self.assertIn("custody decision and approvals: VERIFIED", result.stdout)
        self.assertIn("scanner admission approvals: VERIFIED", result.stdout)
        self.assertIn("exact G1 bundle approvals: VERIFIED", result.stdout)
        self.assertIn(
            "provider/account/process/profile access: NOT PERFORMED",
            result.stdout,
        )
        self.assertIn(
            "AUTO-M0-G1-EXIT: PASSED",
            result.stdout,
        )

    def test_custody_verifier_uses_real_filesystem_and_fails_closed(self) -> None:
        self.assertTrue(
            hasattr(m0_g1_exit, "verify_custody_root"),
            "custody verifier is not implemented",
        )
        with tempfile.TemporaryDirectory(prefix="agentmonitor-m0-g1-") as raw_root:
            root = Path(raw_root)
            os.chmod(root, 0o700)
            self.assertEqual(
                [],
                m0_g1_exit.verify_custody_root(root, REPOSITORY_ROOT),
            )

            os.chmod(root, 0o750)
            self.assertIn(
                "custody root permissions are not owner-only",
                m0_g1_exit.verify_custody_root(root, REPOSITORY_ROOT),
            )
            os.chmod(root, 0o700)

            link = root.parent / f"{root.name}-link"
            link.symlink_to(root, target_is_directory=True)
            try:
                self.assertIn(
                    "custody root must not be a symbolic link",
                    m0_g1_exit.verify_custody_root(link, REPOSITORY_ROOT),
                )
            finally:
                link.unlink()

        self.assertIn(
            "custody root must be outside the repository",
            m0_g1_exit.verify_custody_root(REPOSITORY_ROOT, REPOSITORY_ROOT),
        )

    def test_timestamp_checker_accepts_only_real_utc_z_instants(self) -> None:
        self.assertTrue(
            hasattr(m0_g1_exit, "is_utc_z_timestamp"),
            "UTC-Z timestamp checker is not implemented",
        )
        for value in (
            "2026-09-19T12:34:56Z",
            "2024-02-29T00:00:00.123456Z",
        ):
            self.assertTrue(m0_g1_exit.is_utc_z_timestamp(value), value)

        for value in (
            "2026-09-19T12:34:56+00:00",
            "2026-09-19 12:34:56Z",
            "2026-02-29T00:00:00Z",
            "2026-09-19T12:34Z",
            "not-a-timestamp",
            123,
        ):
            self.assertFalse(m0_g1_exit.is_utc_z_timestamp(value), value)

    def test_custody_setup_writes_owner_only_local_selection(self) -> None:
        self.assertTrue(CUSTODY_SETUP_PATH.is_file(), "custody setup is missing")
        custody_setup = importlib.import_module("m0_g1_custody")
        with tempfile.TemporaryDirectory(prefix="agentmonitor-custody-root-") as raw_root:
            with tempfile.TemporaryDirectory(
                prefix="agentmonitor-custody-config-"
            ) as raw_config:
                root = Path(raw_root)
                os.chmod(root, 0o700)
                selection_path = Path(raw_config) / "selection.toml"
                violations = custody_setup.write_selection(
                    selection_path=selection_path,
                    external_root=root,
                    repository_root=REPOSITORY_ROOT,
                    retention_until_utc="2027-09-19T00:00:00Z",
                )
                self.assertEqual([], violations)
                self.assertEqual(0o600, selection_path.stat().st_mode & 0o777)
                with selection_path.open("rb") as stream:
                    selection = tomllib.load(stream)
                self.assertEqual(str(root), selection["external_root"])
                self.assertIs(True, selection["owner_selected"])


if __name__ == "__main__":
    unittest.main()
