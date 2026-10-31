"""Real-checkout tests for the exact M0 G1 review bundle."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import m0_g1_bundle  # noqa: E402


class M0G1BundleTests(unittest.TestCase):
    def test_bundle_binds_every_declared_real_checkout_artifact(self) -> None:
        subject = m0_g1_bundle.bundle_subject(REPOSITORY_ROOT)
        self.assertEqual("M0-G1-BUNDLE-001", subject["subject_id"])
        artifacts = subject["artifacts"]
        self.assertEqual(
            list(m0_g1_bundle.BUNDLE_ARTIFACT_PATHS),
            [item["path"] for item in artifacts],
        )
        for item in artifacts:
            content = (REPOSITORY_ROOT / item["path"]).read_bytes()
            self.assertEqual(len(content), item["bytes"])
            self.assertEqual(hashlib.sha256(content).hexdigest(), item["sha256"])

    def test_scanner_admission_binds_the_installed_binary_and_wrapper(self) -> None:
        subject = m0_g1_bundle.scanner_subject(REPOSITORY_ROOT)
        self.assertEqual("E1-GITLEAKS-8300", subject["admission_id"])
        self.assertEqual(
            hashlib.sha256(
                (REPOSITORY_ROOT / ".venv-m0-g1/bin/gitleaks").read_bytes()
            ).hexdigest(),
            subject["binary_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(
                (REPOSITORY_ROOT / "tools/discovery/m0_g1_scanner.py").read_bytes()
            ).hexdigest(),
            subject["configuration_sha256"],
        )
        self.assertEqual([], subject["approvals"])


if __name__ == "__main__":
    unittest.main()
