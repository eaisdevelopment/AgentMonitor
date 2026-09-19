"""Real-filesystem tests for owner-controlled M0 G1 finalization."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import m0_g1_approve  # noqa: E402
import m0_g1_exit  # noqa: E402
import m0_g1_records  # noqa: E402


class M0G1ApprovalTests(unittest.TestCase):
    def test_owner_confirmation_is_exact(self) -> None:
        self.assertTrue(m0_g1_approve.is_owner_confirmation("APPROVE M0 G1"))
        for value in ("", "approve m0 g1", "APPROVE", " APPROVE M0 G1"):
            self.assertFalse(m0_g1_approve.is_owner_confirmation(value), value)

    def test_finalizer_writes_owner_only_records_without_exposing_root_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-g1-external-") as external:
            with tempfile.TemporaryDirectory(prefix="agentmonitor-g1-local-") as local:
                external_root = Path(external)
                os.chmod(external_root, 0o700)
                local_record = Path(local) / "m0-g1-exit.json"
                selection = {
                    "external_root_ref": "REF-M0-CUSTODY-001",
                    "external_root": str(external_root),
                    "owner_selected": True,
                    "sync_backup_disposition": "excluded",
                    "retention_until_utc": "2027-09-19T12:00:00Z",
                }
                violations = m0_g1_approve.write_final_records(
                    repository_root=REPOSITORY_ROOT,
                    selection=selection,
                    local_record_path=local_record,
                    decided_at=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
                )
                self.assertEqual([], violations)

                custody_path = external_root / m0_g1_approve.CUSTODY_FILENAME
                self.assertTrue(custody_path.is_file())
                self.assertEqual(0o600, custody_path.stat().st_mode & 0o777)
                self.assertEqual(0o600, local_record.stat().st_mode & 0o777)

                custody = json.loads(custody_path.read_text(encoding="utf-8"))
                local_exit = json.loads(local_record.read_text(encoding="utf-8"))
                self.assertNotIn(str(external_root), local_record.read_text(encoding="utf-8"))
                self.assertEqual(
                    [],
                    m0_g1_records.validate_custody_decision(
                        decision=custody,
                        selection=selection,
                        as_of=datetime(2026, 9, 19, 12, 1, tzinfo=timezone.utc),
                    ),
                )
                self.assertTrue(
                    local_exit["external_custody_record_access_authorized"]
                )
                self.assertEqual(
                    m0_g1_approve.file_sha256(custody_path),
                    local_exit["custody_decision_sha256"],
                )
                self.assertEqual(
                    [],
                    m0_g1_exit.validate_final_approval_state(
                        repository_root=REPOSITORY_ROOT,
                        selection=selection,
                        local_record_path=local_record,
                        as_of=datetime(2026, 9, 19, 12, 1, tzinfo=timezone.utc),
                    ),
                )

                custody_path.write_bytes(custody_path.read_bytes() + b" ")
                self.assertIn(
                    "custody decision digest does not match approval state",
                    m0_g1_exit.validate_final_approval_state(
                        repository_root=REPOSITORY_ROOT,
                        selection=selection,
                        local_record_path=local_record,
                        as_of=datetime(2026, 9, 19, 12, 1, tzinfo=timezone.utc),
                    ),
                )


if __name__ == "__main__":
    unittest.main()
