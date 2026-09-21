"""Real-filesystem tests for owner-controlled M0 G1 finalization."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import m0_g1_approve
import m0_g1_custody
import m0_g1_exit
import m0_g1_records


class M0G1ApprovalTests(unittest.TestCase):
    def test_sync_backup_confirmation_policy_matches_approved_dispositions(self) -> None:
        self.assertEqual(
            "excluded",
            m0_g1_custody.disposition_for_confirmation(
                "I CONFIRM THIS ROOT IS EXCLUDED FROM SYNC AND BACKUP"
            ),
        )
        self.assertEqual(
            "owner_accepted_encrypted",
            m0_g1_custody.disposition_for_confirmation(
                "I CONFIRM ENCRYPTED SYNC AND BACKUP FOR THIS ROOT AND ACCEPT THE RISK"
            ),
        )
        for confirmation in ("", "I ACCEPT SYNC", "blocked"):
            self.assertIsNone(
                m0_g1_custody.disposition_for_confirmation(confirmation)
            )

    def test_owner_accepted_encrypted_selection_is_valid_but_blocked_is_not(self) -> None:
        selection = {
            "schema_version": "1.1",
            "external_root_ref": "REF-M0-CUSTODY-001",
            "external_root": "/not-a-real-root-for-pure-policy",
            "owner_selected": True,
            "sync_backup_disposition": "owner_accepted_encrypted",
            "sync_backup_owner_attested": True,
            "sync_backup_attested_at_utc": "2026-09-19T11:00:00Z",
            "retention_until_utc": "2027-09-19T12:00:00Z",
        }
        as_of = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(
            [], m0_g1_exit.review_selection_violations(selection, as_of=as_of)
        )
        selection["sync_backup_disposition"] = "blocked"
        self.assertIn(
            "owner custody sync/backup disposition is invalid",
            m0_g1_exit.review_selection_violations(selection, as_of=as_of),
        )

    def test_local_review_selection_validation_is_pure_and_root_agnostic(self) -> None:
        selection = {
            "schema_version": "1.1",
            "external_root_ref": "REF-M0-CUSTODY-001",
            "external_root": "/not-a-real-root-for-pure-policy",
            "owner_selected": True,
            "sync_backup_disposition": "excluded",
            "sync_backup_owner_attested": True,
            "sync_backup_attested_at_utc": "2026-09-19T11:00:00Z",
            "retention_until_utc": "2027-09-19T12:00:00Z",
        }
        self.assertEqual(
            [],
            m0_g1_exit.review_selection_violations(
                selection, as_of=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
            ),
        )
        selection["owner_selected"] = False
        self.assertIn(
            "owner custody selection is not confirmed",
            m0_g1_exit.review_selection_violations(
                selection, as_of=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
            ),
        )
        selection["owner_selected"] = True
        selection["sync_backup_owner_attested"] = False
        self.assertIn(
            "sync/backup disposition lacks owner attestation",
            m0_g1_exit.review_selection_violations(
                selection, as_of=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
            ),
        )
        selection["sync_backup_owner_attested"] = True
        selection["schema_version"] = "1.0"
        self.assertIn(
            "owner custody selection version is invalid",
            m0_g1_exit.review_selection_violations(
                selection, as_of=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
            ),
        )

    def test_owner_approval_assembly_is_pure_and_policy_valid(self) -> None:
        subject = {"subject_id": "CUST-M0-G1-001", "approvals": []}
        reviewers = [
            m0_g1_records.approval_record(
                approval_id=f"APR-CUST-{role.upper().replace('_', '-')}",
                subject_id="CUST-M0-G1-001",
                subject_digest=m0_g1_records.subject_sha256(subject),
                role=role,
                reviewer_ref=f"REF-REVIEWER-{role.upper().replace('_', '-')}",
                decided_at_utc="2026-09-19T12:00:00Z",
            )
            for role in ("security_privacy", "test_integrity")
        ]
        approvals = m0_g1_approve.owner_completed_approvals(
            subject,
            reviewers,
            subject_id="CUST-M0-G1-001",
            approval_prefix="CUST-M0-G1",
            decided_at_utc="2026-09-19T12:01:00Z",
        )
        self.assertEqual([], subject["approvals"])
        self.assertEqual(
            [],
            m0_g1_records.validate_approval_set(
                subject=subject,
                subject_id="CUST-M0-G1-001",
                approvals=approvals,
                required_roles=m0_g1_approve.CUSTODY_ROLES,
                as_of=datetime(2026, 9, 19, 12, 2, tzinfo=timezone.utc),
            ),
        )

    def test_review_subject_rows_expose_ids_and_digests_only(self) -> None:
        rows = m0_g1_approve.review_subject_rows(
            {"decision_id": "CUST-M0-G1-001", "private": "not-for-output"},
            {"admission_id": "E1-GITLEAKS-8300", "private": "not-for-output"},
            {"subject_id": "M0-G1-BUNDLE-001", "private": "not-for-output"},
        )
        self.assertEqual(3, len(rows))
        self.assertEqual(
            ["CUST-M0-G1-001", "E1-GITLEAKS-8300", "M0-G1-BUNDLE-001"],
            [row[0] for row in rows],
        )
        self.assertTrue(all(len(row[1]) == 64 for row in rows))
        self.assertNotIn("not-for-output", repr(rows))

    def test_owner_confirmation_is_exact(self) -> None:
        self.assertTrue(m0_g1_approve.is_owner_confirmation("APPROVE M0 G1"))
        for value in ("", "approve m0 g1", "APPROVE", " APPROVE M0 G1"):
            self.assertFalse(m0_g1_approve.is_owner_confirmation(value), value)

    def test_owner_confirmation_does_not_forge_independent_reviewer_decisions(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-g1-review-") as root:
            external_root = Path(root) / "external"
            external_root.mkdir(mode=0o700)
            local_record = Path(root) / "m0-g1-exit.json"
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
                owner_confirmation="APPROVE M0 G1",
            )
            custody_path = external_root / m0_g1_approve.CUSTODY_FILENAME
            self.assertIn("independent reviewer decisions are missing", violations)
            self.assertFalse(custody_path.exists())
            self.assertFalse(local_record.exists())

    def test_finalizer_requires_exact_owner_confirmation_before_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-g1-review-") as root:
            external_root = Path(root) / "external"
            external_root.mkdir(mode=0o700)
            selection = {
                "external_root_ref": "REF-M0-CUSTODY-001",
                "external_root": str(external_root),
                "owner_selected": True,
                "sync_backup_disposition": "excluded",
                "retention_until_utc": "2027-09-19T12:00:00Z",
            }
            local_record = Path(root) / "m0-g1-exit.json"
            violations = m0_g1_approve.write_final_records(
                repository_root=REPOSITORY_ROOT,
                selection=selection,
                local_record_path=local_record,
                decided_at=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
                owner_confirmation="approve m0 g1",
            )
            self.assertIn("exact owner confirmation is missing", violations)
            self.assertFalse((external_root / m0_g1_approve.CUSTODY_FILENAME).exists())
            self.assertFalse(local_record.exists())

    def test_finalizer_rejects_repository_as_custody_root(self) -> None:
        selection = {
            "external_root_ref": "REF-M0-CUSTODY-001",
            "external_root": str(REPOSITORY_ROOT),
            "owner_selected": True,
            "sync_backup_disposition": "excluded",
            "retention_until_utc": "2027-09-19T12:00:00Z",
        }
        violations = m0_g1_approve.write_final_records(
            repository_root=REPOSITORY_ROOT,
            selection=selection,
            local_record_path=REPOSITORY_ROOT / ".agentmonitor-local/m0-g1-exit.json",
            decided_at=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
            owner_confirmation="APPROVE M0 G1",
        )
        self.assertIn("custody root must be outside the repository", violations)

    def test_reviewer_decision_policy_rejects_owner_only_or_wrong_subject(self) -> None:
        as_of = datetime(2026, 9, 19, 12, 1, tzinfo=timezone.utc)
        subjects = {
            "custody": {"subject_id": "CUST-M0-G1-001", "approvals": []},
            "scanner": {"subject_id": "E1-GITLEAKS-8300", "approvals": []},
            "bundle": {"subject_id": "M0-G1-BUNDLE-001", "approvals": []},
        }

        def approved(role: str, group: str) -> dict[str, object]:
            return m0_g1_records.approval_record(
                approval_id=f"APR-{group.upper()}-{role.upper().replace('_', '-')}",
                subject_id=str(subjects[group]["subject_id"]),
                subject_digest=m0_g1_records.subject_sha256(subjects[group]),
                role=role,
                reviewer_ref=f"REF-REVIEWER-{role.upper().replace('_', '-')}",
                decided_at_utc="2026-09-19T12:00:00Z",
            )

        reviews = {
            "record_version": "1.0",
            "custody_approvals": [
                approved(role, "custody")
                for role in ("security_privacy", "test_integrity")
            ],
            "scanner_approvals": [
                approved(role, "scanner")
                for role in ("security_privacy", "test_integrity")
            ],
            "bundle_approvals": [
                approved(role, "bundle")
                for role in (
                    "security_privacy",
                    "test_integrity",
                    "provider_system",
                    "root_integration",
                )
            ],
        }
        self.assertEqual(
            [],
            m0_g1_approve.validate_reviewer_decisions(
                reviews,
                custody_subject=subjects["custody"],
                scanner_subject=subjects["scanner"],
                bundle_subject=subjects["bundle"],
                as_of=as_of,
            ),
        )

        reviews["bundle_approvals"] = [approved("owner", "bundle")]
        self.assertIn(
            "bundle_approvals: approval roles must be exactly provider_system,root_integration,security_privacy,test_integrity",
            m0_g1_approve.validate_reviewer_decisions(
                reviews,
                custody_subject=subjects["custody"],
                scanner_subject=subjects["scanner"],
                bundle_subject=subjects["bundle"],
                as_of=as_of,
            ),
        )

        reviews["bundle_approvals"] = [
            approved(role, "bundle")
            for role in (
                "security_privacy",
                "test_integrity",
                "provider_system",
                "root_integration",
            )
        ]
        reviews["bundle_approvals"][0]["subject_sha256"] = "0" * 64
        self.assertIn(
            "bundle_approvals: approval subject digest does not match",
            m0_g1_approve.validate_reviewer_decisions(
                reviews,
                custody_subject=subjects["custody"],
                scanner_subject=subjects["scanner"],
                bundle_subject=subjects["bundle"],
                as_of=as_of,
            ),
        )

        reviews["bundle_approvals"][0]["subject_sha256"] = m0_g1_records.subject_sha256(
            subjects["bundle"]
        )
        reviews["bundle_approvals"][1]["reviewer_ref"] = reviews["bundle_approvals"][0][
            "reviewer_ref"
        ]
        self.assertIn(
            "independent reviewer references are not role-distinct",
            m0_g1_approve.validate_reviewer_decisions(
                reviews,
                custody_subject=subjects["custody"],
                scanner_subject=subjects["scanner"],
                bundle_subject=subjects["bundle"],
                as_of=as_of,
            ),
        )

        reviews["bundle_approvals"][1]["reviewer_ref"] = "REF-REVIEWER-TEST-INTEGRITY"
        reviews["bundle_approvals"][0]["reviewer_ref"] = "REF-OWNER-PAVLO"
        self.assertIn(
            "owner reference cannot attest a non-owner review",
            m0_g1_approve.validate_reviewer_decisions(
                reviews,
                custody_subject=subjects["custody"],
                scanner_subject=subjects["scanner"],
                bundle_subject=subjects["bundle"],
                as_of=as_of,
            ),
        )

    def test_independent_review_file_is_owner_only_and_duplicate_key_free(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agentmonitor-g1-review-") as root:
            base = Path(root)
            os.chmod(base, 0o700)
            review_path = base / m0_g1_approve.REVIEW_DECISION_PATH
            review_path.parent.mkdir(mode=0o700)
            review_path.write_text('{"record_version":"1.0"}', encoding="utf-8")
            os.chmod(review_path, 0o600)
            self.assertEqual(
                ({"record_version": "1.0"}, []),
                m0_g1_approve.load_reviewer_decisions(base),
            )

            review_path.write_text(
                '{"record_version":"1.0","record_version":"1.0"}', encoding="utf-8"
            )
            self.assertEqual(
                (None, ["independent reviewer decision file is invalid"]),
                m0_g1_approve.load_reviewer_decisions(base),
            )
            os.chmod(review_path, 0o644)
            self.assertEqual(
                (None, ["independent reviewer decision file is not owner-only"]),
                m0_g1_approve.load_reviewer_decisions(base),
            )


if __name__ == "__main__":
    unittest.main()
