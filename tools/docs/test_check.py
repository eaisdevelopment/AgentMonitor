"""Real-checkout tests for repository documentation validation."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check import check_repository  # noqa: E402


class DocumentationCheckTests(unittest.TestCase):
    _M3_CRITERIA = (
        "AC-V1-001",
        "AC-V1-002",
        "AC-V1-005",
        "AC-V1-006",
        "AC-V1-007",
        "AC-V1-008",
        "AC-UI-002",
        "AC-UI-003",
        "AC-UI-006",
        "AC-LIVE-001",
        "AC-LIVE-004",
        "AC-LIVE-005",
        "AC-PROC-001",
        "AC-PROC-002",
        "AC-PROC-003",
        "AC-PROC-004",
        "AC-PROC-005",
        "AC-HIST-001",
        "AC-TEST-001",
        "AC-TEST-002",
        "AC-TEST-003",
        "AC-TEST-004",
        "AC-TEST-005",
        "AC-TEST-006",
    )

    def _minimal_repository(self, root: Path, *, with_m3: bool = False) -> None:
        (root / "docs/product").mkdir(parents=True)
        (root / "docs/plans").mkdir()
        (root / "docs/product/requirements.md").write_text(
            "# Requirements\n\nNFR-DOC-001\n", encoding="utf-8"
        )
        (root / "docs/product/v1-acceptance-criteria.md").write_text(
            "# Acceptance criteria\n\n" + "\n".join(self._M3_CRITERIA) + "\n",
            encoding="utf-8",
        )
        (root / "docs/plans/contract-baseline.toml").write_text(
            '[[contracts]]\nid = "CTR-FND-001"\n', encoding="utf-8"
        )
        if with_m3:
            plan = (
                root
                / "docs/superpowers/plans/2026-09-19-agentmonitor-v1-m3-claude-slice.md"
            )
            plan.parent.mkdir(parents=True)
            plan.write_text("# M3 plan\n", encoding="utf-8")
            (root / "docs/evidence").mkdir()

    def _write_m3_record(
        self,
        root: Path,
        *,
        record_id: str,
        status: str = "blocked",
        marker_status: str | None = None,
    ) -> Path:
        evidence_path = root / "docs/evidence/source.md"
        evidence_path.write_text("# Exact evidence\n", encoding="utf-8")
        digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        marker = marker_status or status
        (root / "docs/README.md").write_text(
            "# Index\n\n"
            "<!-- agentmonitor-milestone-status:v1 milestone=V1-M3 "
            f"lifecycle=active status={marker} authority={record_id} -->\n",
            encoding="utf-8",
        )
        record = {
            "schema_version": "1.0.0",
            "record_type": "agentmonitor.milestone_acceptance_status",
            "record_id": record_id,
            "milestone_id": "V1-M3",
            "lifecycle": "active",
            "overall_status": status,
            "assessed_revision": "a" * 40,
            "recorded_at": "2026-09-24T12:00:00Z",
            "status_documents": ["docs/README.md"],
            "evidence": [
                {
                    "evidence_id": "E-M3-001",
                    "path": "docs/evidence/source.md",
                    "sha256": digest,
                }
            ],
            "commands": [
                {
                    "command_id": "AUTO-M3-EXIT",
                    "command": "python3 tools/automation/run.py AUTO-M3-EXIT",
                    "status": "not_run",
                    "exit_code": None,
                    "skips": ["required live boundary unavailable"],
                    "evidence_ids": ["E-M3-001"],
                }
            ],
            "criteria": [
                {
                    "criterion_id": criterion_id,
                    "status": "blocked",
                    "evidence_ids": ["E-M3-001"],
                    "decision": "outstanding acceptance evidence",
                }
                for criterion_id in self._M3_CRITERIA
            ],
            "reviewer_decisions": [
                {
                    "decision_id": "M3-STATUS-001",
                    "status": "blocked",
                    "decision": "milestone remains blocked",
                    "evidence_ids": ["E-M3-001"],
                }
            ],
            "supersedes": [],
        }
        path = root / f"docs/evidence/v1-m3-acceptance-status-{record_id}.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_real_repository_documentation_is_internally_resolvable(self) -> None:
        self.assertEqual([], check_repository(REPOSITORY_ROOT))

    def test_ignores_vendor_markdown_with_broken_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "README.md").write_text("# Project\n", encoding="utf-8")
            (root / "docs/product").mkdir(parents=True)
            (root / "docs/plans").mkdir()
            (root / "docs/product/requirements.md").write_text(
                "# Requirements\n\nNFR-DOC-001\n", encoding="utf-8"
            )
            (root / "docs/product/v1-acceptance-criteria.md").write_text(
                "# Acceptance criteria\n\nAC-TEST-001\n", encoding="utf-8"
            )
            (root / "docs/plans/contract-baseline.toml").write_text(
                '[[contracts]]\nid = "CTR-FND-001"\n', encoding="utf-8"
            )
            (root / "docs/project.md").write_text(
                "# Project documentation\n\n[Repository](../README.md)\n",
                encoding="utf-8",
            )
            vendor_markdown = root / "frontend/node_modules/vendor/README.md"
            vendor_markdown.parent.mkdir(parents=True)
            vendor_markdown.write_text(
                "[Broken vendor link](missing.md)\n", encoding="utf-8"
            )

            self.assertEqual([], check_repository(root))

    def test_m3_plan_requires_one_machine_readable_active_status_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._minimal_repository(root, with_m3=True)

            violations = check_repository(root)

            self.assertTrue(
                any(
                    "V1-M3 requires exactly one active acceptance record" in item
                    for item in violations
                ),
                violations,
            )

    def test_m3_status_rejects_two_contradictory_active_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._minimal_repository(root, with_m3=True)
            self._write_m3_record(root, record_id="M3-ACTIVE-001")
            self._write_m3_record(
                root,
                record_id="M3-ACTIVE-002",
                status="passed",
                marker_status="passed",
            )

            violations = check_repository(root)

            self.assertTrue(
                any(
                    "V1-M3 requires exactly one active acceptance record" in item
                    for item in violations
                ),
                violations,
            )
            self.assertTrue(
                any(
                    "passed milestone contradicts AUTO-M3-EXIT result" in item
                    for item in violations
                ),
                violations,
            )
            self.assertTrue(
                any(
                    "passed milestone contradicts outstanding criterion status" in item
                    for item in violations
                ),
                violations,
            )

    def test_m3_status_rejects_conflicting_active_markdown_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._minimal_repository(root, with_m3=True)
            self._write_m3_record(
                root,
                record_id="M3-ACTIVE-001",
                status="blocked",
                marker_status="passed",
            )

            violations = check_repository(root)

            self.assertTrue(
                any(
                    "active status marker contradicts acceptance record" in item
                    for item in violations
                ),
                violations,
            )

    def test_m3_status_rejects_changed_evidence_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._minimal_repository(root, with_m3=True)
            self._write_m3_record(root, record_id="M3-ACTIVE-001")
            (root / "docs/evidence/source.md").write_text(
                "# Changed evidence\n", encoding="utf-8"
            )

            violations = check_repository(root)

            self.assertTrue(
                any("evidence digest mismatch" in item for item in violations),
                violations,
            )

    def test_m3_status_rejects_passed_command_with_skips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._minimal_repository(root, with_m3=True)
            record_path = self._write_m3_record(root, record_id="M3-ACTIVE-001")
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["commands"][0].update(
                status="passed",
                exit_code=0,
                skips=["live boundary was skipped"],
            )
            record_path.write_text(json.dumps(record), encoding="utf-8")

            violations = check_repository(root)

            self.assertTrue(
                any("passed command reports skips" in item for item in violations),
                violations,
            )

    def test_passed_m3_rejects_any_failed_command_or_reviewer_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._minimal_repository(root, with_m3=True)
            record_path = self._write_m3_record(
                root,
                record_id="M3-ACTIVE-001",
                status="passed",
                marker_status="passed",
            )
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["commands"][0].update(status="passed", exit_code=0, skips=[])
            for criterion in record["criteria"]:
                criterion["status"] = "passed"
            record["commands"].append(
                {
                    "command_id": "AUTO-QUALITY",
                    "command": "python3 tools/automation/run.py AUTO-QUALITY",
                    "status": "failed",
                    "exit_code": 1,
                    "skips": [],
                    "evidence_ids": ["E-M3-001"],
                }
            )
            record_path.write_text(json.dumps(record), encoding="utf-8")

            violations = check_repository(root)

            self.assertTrue(
                any(
                    "passed milestone contradicts command status" in item
                    for item in violations
                ),
                violations,
            )
            self.assertTrue(
                any(
                    "passed milestone contradicts reviewer decision" in item
                    for item in violations
                ),
                violations,
            )


if __name__ == "__main__":
    unittest.main()
