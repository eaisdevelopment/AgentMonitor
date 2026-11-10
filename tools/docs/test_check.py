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

import check as docs_check
from check import (
    _validate_m3_receipt_payload,
    check_m3_acceptance_status,
    check_repository,
    check_v1_implementation_status,
)


class DocumentationCheckTests(unittest.TestCase):
    def test_only_documented_m6_local_deferral_excludes_incomplete_story(self) -> None:
        decision = "docs/evidence/m6-local-ollama-deferral-2026-11-04.md"
        local = {
            "story_id": "ST-OLL-002",
            "delivery_state": "in_progress",
            "evidence_paths": [decision],
        }
        self.assertFalse(docs_check.story_blocks_completion("V1-M6", local))
        self.assertTrue(docs_check.story_blocks_completion("V1-M7", local))
        self.assertTrue(
            docs_check.story_blocks_completion(
                "V1-M6", {**local, "evidence_paths": []}
            )
        )
        self.assertTrue(
            docs_check.story_blocks_completion(
                "V1-M6", {**local, "story_id": "ST-OLL-003"}
            )
        )
        self.assertFalse(
            docs_check.story_blocks_completion(
                "V1-M6", {**local, "delivery_state": "implemented"}
            )
        )

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
    _M3_SCOPED_CRITERIA = (
        "AC-M3-001",
        "AC-M3-002",
        "AC-M3-003",
        "AC-M3-004",
        "AC-M3-005",
        "AC-M3-006",
        "AC-M3-007",
    )

    def _minimal_repository(self, root: Path, *, with_m3: bool = False) -> None:
        (root / "docs/product").mkdir(parents=True)
        (root / "docs/plans").mkdir()
        (root / "docs/product/requirements.md").write_text(
            "# Requirements\n\nNFR-DOC-001\n", encoding="utf-8"
        )
        (root / "docs/product/v1-acceptance-criteria.md").write_text(
            "# Acceptance criteria\n\n"
            + "\n".join(self._M3_CRITERIA + self._M3_SCOPED_CRITERIA)
            + "\n",
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

    def _copy_real_m3_status_repository(self, root: Path) -> tuple[Path, Path]:
        relative_paths = [
            "docs/README.md",
            "docs/superpowers/plans/2026-09-19-agentmonitor-v1-m3-claude-slice.md",
            "docs/evidence/v1-m3-acceptance-status-v1.json",
            "docs/evidence/v1-m3-acceptance-status-v2.json",
        ]
        v3_relative = "docs/evidence/v1-m3-acceptance-status-v3.json"
        if (REPOSITORY_ROOT / v3_relative).is_file():
            relative_paths.append(v3_relative)
        for relative in relative_paths:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPOSITORY_ROOT / relative).read_bytes())
        predecessor = root / relative_paths[2]
        active = root / relative_paths[3]
        for record_path in (root / relative for relative in relative_paths[2:]):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            related_paths = {
                *(item["path"] for item in record["evidence"]),
                *record["status_documents"],
                *(item["path"] for item in record["supersedes"]),
            }
            for relative in related_paths:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((REPOSITORY_ROOT / relative).read_bytes())
        return predecessor, active

    def _check_m3_v2_repository(self, root: Path) -> list[str]:
        return check_m3_acceptance_status(root)

    def _pure_m3_v3_receipt(self) -> tuple[dict[str, object], dict[str, object]]:
        record = {
            "assessed_revision": "a" * 40,
            "recorded_at": "2026-10-03T10:02:00Z",
        }
        evidence_by_lane = {
            "selected_account_preflight": "browser_api_account_verified",
            "fresh_quota_lineage": "run_sha256:" + "b" * 64,
            "registry_unchanged": "browser_get_only_registry_unchanged",
            "revision_bound_service": "service_restarted_from_clean_head",
            "current_browser": "visible_shared_chrome_passed",
            "runtime_regression": "runtime_query:available",
            "technical_suite": "auto-m3-test_passed",
            "quality": "auto-quality_passed",
            "build": "auto-build_passed",
            "mutation": "auto-mutation_passed",
            "documentation": "auto-docs-check_passed",
            "git_preflight": "auto-git-preflight_passed",
        }
        receipt: dict[str, object] = {
            "schema_version": "1.0.0",
            "record_type": "agentmonitor.m3_current_gate_receipt",
            "receipt_id": "M3-CURRENT-GATE-20261003T100100Z",
            "milestone_id": "V1-M3",
            "command_id": "AUTO-M3-EXIT",
            "command": "python3 tools/automation/run.py AUTO-M3-EXIT",
            "implementation_revision": record["assessed_revision"],
            "started_at": "2026-10-03T10:00:00Z",
            "completed_at": "2026-10-03T10:01:00Z",
            "status": "passed",
            "exit_code": 0,
            "skips": [],
            "selected_account_digest": "c" * 64,
            "required_lanes": [
                {"lane_id": key, "status": "passed", "evidence": value}
                for key, value in evidence_by_lane.items()
            ],
        }
        return record, receipt

    def test_m3_v3_pure_receipt_requires_exact_canonical_lanes(self) -> None:
        record, receipt = self._pure_m3_v3_receipt()
        self.assertEqual([], _validate_m3_receipt_payload(receipt, record))

        receipt["required_lanes"][0]["evidence"] = "test metadata"
        self.assertIn(
            "M3 current-gate receipt lane evidence is invalid",
            _validate_m3_receipt_payload(receipt, record),
        )

    def test_m3_v3_pure_owner_decisions_require_distinct_evidence(self) -> None:
        decisions = [
            {
                "decision_id": "M3-SCOPE-2026-10-02",
                "status": "passed",
                "evidence_ids": ["E-SCOPE"],
            },
            {
                "decision_id": "M3-CURRENT-GATE-2026-10-02",
                "status": "passed",
                "evidence_ids": ["E-SCOPE"],
            },
            {
                "decision_id": "M3-HISTORICAL-TDD-2026-10-03",
                "status": "deviation_accepted",
                "evidence_ids": ["E-SCOPE"],
            },
            {
                "decision_id": "M3-OWNER-LIVE-2026-10-03",
                "status": "passed",
                "evidence_ids": ["E-SCOPE"],
            },
        ]
        violations = docs_check._validate_m3_v3_decision_bindings(
            decisions,
            receipt_evidence_id="E-GATE",
            historical_evidence_id="E-TDD",
            owner_live_evidence_id="E-LIVE",
        )
        self.assertIn("M3 current-gate review lacks receipt evidence", violations)
        self.assertIn(
            "M3 historical TDD owner disposition lacks dedicated evidence", violations
        )
        self.assertIn(
            "M3 owner live countersignature lacks dedicated evidence", violations
        )

    def _copy_status_repository(self, root: Path) -> tuple[Path, dict[str, object]]:
        backlog = root / "docs/superpowers/plans/implementation-backlog.toml"
        backlog.parent.mkdir(parents=True)
        backlog.write_bytes(
            (
                REPOSITORY_ROOT / "docs/superpowers/plans/implementation-backlog.toml"
            ).read_bytes()
        )
        status_path = root / "docs/evidence/v1-implementation-status-v1.json"
        status_path.parent.mkdir(parents=True)
        status = json.loads(
            (
                REPOSITORY_ROOT / "docs/evidence/v1-implementation-status-v1.json"
            ).read_text(encoding="utf-8")
        )
        for collection in (status["milestones"], status["stories"]):
            for item in collection:
                for evidence_path in item["evidence_paths"]:
                    path = root / evidence_path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("# Evidence\n", encoding="utf-8")
        roadmap = root / status["roadmap"]
        roadmap.parent.mkdir(parents=True, exist_ok=True)
        roadmap.write_text(
            "# Roadmap\n\n"
            + "\n".join(
                f"## {item['milestone_id']} — {item['title']}"
                for item in status["milestones"]
            )
            + "\n",
            encoding="utf-8",
        )
        return status_path, status

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

    def test_import_backlog_requires_current_implementation_status_overlay(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._minimal_repository(root)
            backlog = root / "docs/superpowers/plans/implementation-backlog.toml"
            backlog.parent.mkdir(parents=True)
            backlog.write_bytes(
                (
                    REPOSITORY_ROOT
                    / "docs/superpowers/plans/implementation-backlog.toml"
                ).read_bytes()
            )

            violations = check_repository(root)

            self.assertTrue(
                any(
                    "V1 implementation status overlay is missing" in item
                    for item in violations
                ),
                violations,
            )

    def test_implementation_status_rejects_story_milestone_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            status_path, status = self._copy_status_repository(root)
            status["stories"][0]["milestone_id"] = "V1-M8"
            status_path.write_text(json.dumps(status), encoding="utf-8")

            violations = check_v1_implementation_status(root)

            self.assertTrue(
                any(
                    "story milestone differs from backlog" in item
                    for item in violations
                ),
                violations,
            )

    def test_implementation_status_rejects_unresolved_accepted_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            status_path, status = self._copy_status_repository(root)
            m4 = next(
                item for item in status["milestones"] if item["milestone_id"] == "V1-M4"
            )
            m4["dependency_state"] = "unresolved"
            m4["unresolved_dependency_ids"] = ["V1-M3"]
            status_path.write_text(json.dumps(status), encoding="utf-8")

            violations = check_v1_implementation_status(root)

            self.assertTrue(
                any(
                    "dependency acceptance is inconsistent for V1-M4" in item
                    for item in violations
                ),
                violations,
            )

    def test_implementation_status_requires_distinct_acceptance_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            status_path, status = self._copy_status_repository(root)
            m1 = next(
                item for item in status["milestones"] if item["milestone_id"] == "V1-M1"
            )
            m1["acceptance_decision_path"] = None
            status_path.write_text(json.dumps(status), encoding="utf-8")

            violations = check_v1_implementation_status(root)

            self.assertTrue(
                any(
                    "accepted milestone lacks acceptance decision evidence" in item
                    for item in violations
                ),
                violations,
            )

    def test_current_gate_binding_requires_exact_implementation_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            status_path, status = self._copy_status_repository(root)
            m4 = next(
                item for item in status["milestones"] if item["milestone_id"] == "V1-M4"
            )
            m4["gate_binding"] = "current_implementation_revision"
            m4["gate_revision"] = "b" * 40
            status_path.write_text(json.dumps(status), encoding="utf-8")

            violations = check_v1_implementation_status(root)

            self.assertTrue(
                any(
                    "current gate revision differs from implementation revision" in item
                    for item in violations
                ),
                violations,
            )

    def test_implementation_status_m3_decision_must_name_active_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            status_path, status = self._copy_status_repository(root)
            historical = root / "docs/evidence/v1-m3-acceptance-status-v1.json"
            historical.write_bytes(
                (REPOSITORY_ROOT / historical.relative_to(root)).read_bytes()
            )
            active = root / "docs/evidence/v1-m3-acceptance-status-v3.json"
            active.write_bytes(
                (REPOSITORY_ROOT / active.relative_to(root)).read_bytes()
            )
            m3 = next(
                item for item in status["milestones"] if item["milestone_id"] == "V1-M3"
            )
            m3["acceptance_decision_path"] = historical.relative_to(root).as_posix()
            status_path.write_text(json.dumps(status), encoding="utf-8")

            violations = check_v1_implementation_status(root)

            self.assertTrue(
                any(
                    "V1-M3 acceptance decision does not name the active record" in item
                    for item in violations
                ),
                violations,
            )

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

    def test_m3_v2_scoped_record_supersedes_legacy_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._copy_real_m3_status_repository(root)

            violations = self._check_m3_v2_repository(root)

            self.assertEqual([], violations)

    def test_m3_v2_rejects_later_provider_criterion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _predecessor, active_path = self._copy_real_m3_status_repository(root)
            active = json.loads(active_path.read_text(encoding="utf-8"))
            active["criteria"][-1]["criterion_id"] = "AC-LIVE-002"
            active_path.write_text(json.dumps(active), encoding="utf-8")

            violations = self._check_m3_v2_repository(root)

            self.assertTrue(
                any(
                    "criteria do not match approved M3 Task 6" in item
                    for item in violations
                ),
                violations,
            )

    def test_m3_v2_rejects_changed_predecessor_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            predecessor, _active_path = self._copy_real_m3_status_repository(root)
            predecessor.write_text(
                predecessor.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )

            violations = self._check_m3_v2_repository(root)

            self.assertTrue(
                any("M3 predecessor record digest" in item for item in violations),
                violations,
            )

    def test_m3_v2_rejects_coedited_scope_and_self_reported_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _predecessor, active_path = self._copy_real_m3_status_repository(root)
            active = json.loads(active_path.read_text(encoding="utf-8"))
            scope = root / active["scope_decision"]["path"]
            scope.write_text("# Changed M3 scope\n", encoding="utf-8")
            changed_digest = hashlib.sha256(scope.read_bytes()).hexdigest()
            active["scope_decision"]["sha256"] = changed_digest
            scope_evidence = next(
                item
                for item in active["evidence"]
                if item["evidence_id"] == "E-M3-SCOPE"
            )
            scope_evidence["sha256"] = changed_digest
            active_path.write_text(json.dumps(active), encoding="utf-8")

            violations = self._check_m3_v2_repository(root)

            self.assertTrue(
                any(
                    "M3 scope decision digest is not approved" in item
                    for item in violations
                ),
                violations,
            )

    def test_m3_v2_rejects_coedited_predecessor_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            predecessor, active_path = self._copy_real_m3_status_repository(root)
            active = json.loads(active_path.read_text(encoding="utf-8"))
            predecessor_record = json.loads(predecessor.read_text(encoding="utf-8"))
            predecessor_record["recorded_at"] = "2026-09-24T12:00:01Z"
            predecessor.write_text(json.dumps(predecessor_record), encoding="utf-8")
            active["supersedes_record"]["sha256"] = hashlib.sha256(
                predecessor.read_bytes()
            ).hexdigest()
            active_path.write_text(json.dumps(active), encoding="utf-8")

            violations = self._check_m3_v2_repository(root)

            self.assertTrue(
                any(
                    "M3 predecessor record digest is not canonical" in item
                    for item in violations
                ),
                violations,
            )

    def test_m3_v2_rejects_substitute_predecessor_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            predecessor, active_path = self._copy_real_m3_status_repository(root)
            active = json.loads(active_path.read_text(encoding="utf-8"))
            substitute = root / "docs/evidence/v1-m3-acceptance-status-substitute.json"
            substitute.write_bytes(predecessor.read_bytes())
            active["supersedes_record"]["path"] = substitute.relative_to(
                root
            ).as_posix()
            active_path.write_text(json.dumps(active), encoding="utf-8")

            violations = self._check_m3_v2_repository(root)

            self.assertTrue(
                any(
                    "M3 predecessor record path is invalid" in item
                    for item in violations
                ),
                violations,
            )

    def test_m3_v2_rejects_self_reported_predecessor_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _predecessor, active_path = self._copy_real_m3_status_repository(root)
            active = json.loads(active_path.read_text(encoding="utf-8"))
            active["supersedes_record"]["record_id"] = "M3-SUBSTITUTE-001"
            active_path.write_text(json.dumps(active), encoding="utf-8")

            violations = self._check_m3_v2_repository(root)

            self.assertTrue(
                any(
                    "M3 predecessor record_id is invalid" in item for item in violations
                ),
                violations,
            )

    def test_m3_v2_cannot_claim_passed_without_current_gate_receipt_schema(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _predecessor, active_path = self._copy_real_m3_status_repository(root)
            active = json.loads(active_path.read_text(encoding="utf-8"))
            active["overall_status"] = "passed"
            active["commands"][0].update(status="passed", exit_code=0, skips=[])
            for criterion in active["criteria"]:
                criterion["status"] = "passed"
            for decision in active["reviewer_decisions"]:
                decision["status"] = "passed"
            active_path.write_text(json.dumps(active), encoding="utf-8")
            (root / "docs/README.md").write_text(
                "# Index\n\n"
                "<!-- agentmonitor-milestone-status:v1 milestone=V1-M3 "
                "lifecycle=active status=passed "
                "authority=M3-ACCEPTANCE-2026-10-02-01 -->\n",
                encoding="utf-8",
            )

            violations = self._check_m3_v2_repository(root)

            self.assertTrue(
                any(
                    "cannot claim Passed without a current-gate receipt" in item
                    for item in violations
                ),
                violations,
            )

    def test_m3_v3_pure_receipt_rejects_skips_revision_and_missing_lane(self) -> None:
        record, receipt = self._pure_m3_v3_receipt()
        receipt["skips"] = ["runtime_regression"]
        self.assertIn(
            "M3 current-gate receipt result is not Passed",
            _validate_m3_receipt_payload(receipt, record),
        )
        receipt["skips"] = []
        receipt["implementation_revision"] = "f" * 40
        self.assertIn(
            "M3 current-gate receipt revision differs",
            _validate_m3_receipt_payload(receipt, record),
        )
        receipt["implementation_revision"] = record["assessed_revision"]
        receipt["required_lanes"].pop()
        self.assertIn(
            "M3 current-gate receipt lanes are incomplete",
            _validate_m3_receipt_payload(receipt, record),
        )

    def test_m3_v3_pure_receipt_rejects_unproven_run_and_runtime(self) -> None:
        record, receipt = self._pure_m3_v3_receipt()
        lanes = {item["lane_id"]: item for item in receipt["required_lanes"]}
        lanes["fresh_quota_lineage"]["evidence"] = "run_sha256:unknown"
        lanes["runtime_regression"]["evidence"] = "runtime_query:unavailable"
        violations = _validate_m3_receipt_payload(receipt, record)
        self.assertEqual(
            2,
            violations.count("M3 current-gate receipt lane evidence is invalid"),
        )

    def test_m3_v3_pure_owner_decision_binding_accepts_only_exact_refs(self) -> None:
        decisions = [
            {
                "decision_id": "M3-SCOPE-2026-10-02",
                "status": "passed",
                "evidence_ids": ["E-SCOPE"],
            },
            {
                "decision_id": "M3-CURRENT-GATE-2026-10-02",
                "status": "passed",
                "evidence_ids": ["E-GATE"],
            },
            {
                "decision_id": "M3-HISTORICAL-TDD-2026-10-03",
                "status": "deviation_accepted",
                "evidence_ids": ["E-TDD"],
            },
            {
                "decision_id": "M3-OWNER-LIVE-2026-10-03",
                "status": "passed",
                "evidence_ids": ["E-LIVE"],
            },
        ]
        self.assertEqual(
            [],
            docs_check._validate_m3_v3_decision_bindings(
                decisions,
                receipt_evidence_id="E-GATE",
                historical_evidence_id="E-TDD",
                owner_live_evidence_id="E-LIVE",
            ),
        )
        decisions[-1]["status"] = "blocked"
        self.assertIn(
            "M3 owner live countersignature is missing",
            docs_check._validate_m3_v3_decision_bindings(
                decisions,
                receipt_evidence_id="E-GATE",
                historical_evidence_id="E-TDD",
                owner_live_evidence_id="E-LIVE",
            ),
        )

    def test_m3_real_checkout_transition_remains_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _v1_path, v2_path = self._copy_real_m3_status_repository(root)
            v3_path = root / "docs/evidence/v1-m3-acceptance-status-v3.json"
            if v3_path.is_file():
                v3 = json.loads(v3_path.read_text(encoding="utf-8"))
                self.assertEqual("3.0.0", v3["schema_version"])
                self.assertEqual("passed", v3["overall_status"])
            else:
                v2 = json.loads(v2_path.read_text(encoding="utf-8"))
                self.assertEqual("2.0.0", v2["schema_version"])
                self.assertEqual("active", v2["lifecycle"])
                self.assertEqual("blocked", v2["overall_status"])
            self.assertEqual([], check_m3_acceptance_status(root))

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
