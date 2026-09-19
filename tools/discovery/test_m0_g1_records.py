"""Pure contract tests for exact M0 G1 detached approvals."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import m0_g1_records  # noqa: E402


class M0G1RecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = {
            "record_type": "E1ScannerAdmissionV1",
            "schema_version": "1.0",
            "admission_id": "E1-GITLEAKS-8300",
            "scanner_name": "gitleaks",
            "scanner_version": "8.30.0",
            "binary_sha256": "8" * 64,
            "configuration_sha256": "9" * 64,
            "license": "MIT",
            "dependency_review_ref": "REF-DEP-M0-SCANNER-001",
            "telemetry_disabled": True,
            "network_required": False,
            "output_policy": "discard_raw_output",
            "real_verification_status": "Passed",
            "decision": "approved",
            "evidence_ref": "REF-EVID-M0-G1-CONTRACT-002",
            "approvals": [],
        }
        self.required_roles = {
            "owner",
            "security_privacy",
            "test_integrity",
        }

    def _approvals(self) -> list[dict[str, object]]:
        digest = m0_g1_records.subject_sha256(self.subject)
        return [
            {
                "record_type": "ApprovalRecordV1",
                "schema_version": "1.0",
                "approval_id": f"APR-E1-{role.upper().replace('_', '-')}",
                "subject_id": "E1-GITLEAKS-8300",
                "subject_sha256": digest,
                "role": role,
                "decision": "approved",
                "reviewer_ref": f"REF-{role.upper().replace('_', '-')}",
                "decided_at_utc": "2026-09-19T12:00:00Z",
                "expires_at_utc": None,
            }
            for role in sorted(self.required_roles)
        ]

    def test_exact_approval_set_accepts_only_the_canonical_subject(self) -> None:
        approvals = self._approvals()
        self.assertEqual(
            [],
            m0_g1_records.validate_approval_set(
                subject=self.subject,
                subject_id="E1-GITLEAKS-8300",
                approvals=approvals,
                required_roles=self.required_roles,
                as_of=datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
            ),
        )

        changed_subject = dict(self.subject, scanner_version="8.30.1")
        violations = m0_g1_records.validate_approval_set(
            subject=changed_subject,
            subject_id="E1-GITLEAKS-8300",
            approvals=approvals,
            required_roles=self.required_roles,
            as_of=datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
        )
        self.assertIn("approval subject digest does not match", violations)

    def test_approval_set_rejects_missing_duplicate_rejected_and_expired_roles(self) -> None:
        approvals = self._approvals()
        approvals.pop()
        violations = m0_g1_records.validate_approval_set(
            subject=self.subject,
            subject_id="E1-GITLEAKS-8300",
            approvals=approvals,
            required_roles=self.required_roles,
            as_of=datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(any(item.startswith("approval roles must be exactly") for item in violations))

        approvals = self._approvals()
        approvals[0] = dict(approvals[0], decision="rejected")
        approvals.append(dict(approvals[1], approval_id="APR-E1-DUPLICATE"))
        approvals[1] = dict(
            approvals[1],
            expires_at_utc="2026-09-19T12:30:00Z",
        )
        violations = m0_g1_records.validate_approval_set(
            subject=self.subject,
            subject_id="E1-GITLEAKS-8300",
            approvals=approvals,
            required_roles=self.required_roles,
            as_of=datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
        )
        self.assertIn("approval decision is not approved", violations)
        self.assertIn("approval role is duplicated", violations)
        self.assertIn("approval has expired", violations)

    def test_custody_decision_binds_the_owner_selection_and_required_reviews(self) -> None:
        selection = {
            "external_root_ref": "REF-M0-CUSTODY-001",
            "owner_selected": True,
            "sync_backup_disposition": "excluded",
            "retention_until_utc": "2027-09-19T12:00:00Z",
        }
        subject = m0_g1_records.custody_subject(selection)
        digest = m0_g1_records.subject_sha256(subject)
        subject["approvals"] = [
            m0_g1_records.approval_record(
                approval_id=f"APR-CUSTODY-{role.upper().replace('_', '-')}",
                subject_id="CUST-M0-G1-001",
                subject_digest=digest,
                role=role,
                reviewer_ref=f"REF-{role.upper().replace('_', '-')}",
                decided_at_utc="2026-09-19T12:00:00Z",
            )
            for role in sorted(self.required_roles)
        ]
        self.assertEqual(
            [],
            m0_g1_records.validate_custody_decision(
                decision=subject,
                selection=selection,
                as_of=datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
            ),
        )

        changed_selection = dict(
            selection,
            retention_until_utc="2027-10-01T00:00:00Z",
        )
        self.assertIn(
            "custody retention does not match owner selection",
            m0_g1_records.validate_custody_decision(
                decision=subject,
                selection=changed_selection,
                as_of=datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
            ),
        )


if __name__ == "__main__":
    unittest.main()
