"""Validate AgentMonitor documentation against the real repository indexes."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REQUIREMENT_ID = re.compile(r"\b(?:FR|NFR|AC)-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b")
CONTRACT_ID = re.compile(r"\bCTR-[A-Z]+-\d{3}\b")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "app://", "data:")
M3_PLAN = Path("docs/superpowers/plans/2026-09-19-agentmonitor-v1-m3-claude-slice.md")
M3_RECORD_GLOB = "v1-m3-acceptance-status-*.json"
M3_REQUIRED_CRITERIA_V1 = frozenset(
    {
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
    }
)
M3_REQUIRED_CRITERIA_V2 = frozenset(
    {
        "AC-M3-001",
        "AC-M3-002",
        "AC-M3-003",
        "AC-M3-004",
        "AC-M3-005",
        "AC-M3-006",
        "AC-M3-007",
    }
)
M3_STATUSES = frozenset(
    {"passed", "failed", "blocked", "not_run", "deviation_accepted"}
)
M3_COMMAND_STATUSES = frozenset({"passed", "failed", "blocked", "not_run"})
M3_RECORD_KEYS_V1 = frozenset(
    {
        "schema_version",
        "record_type",
        "record_id",
        "milestone_id",
        "lifecycle",
        "overall_status",
        "assessed_revision",
        "recorded_at",
        "status_documents",
        "evidence",
        "commands",
        "criteria",
        "reviewer_decisions",
        "supersedes",
    }
)
M3_RECORD_KEYS_V2 = M3_RECORD_KEYS_V1 | {
    "scope_decision",
    "supersedes_record",
}
M3_RECORD_KEYS_V3 = M3_RECORD_KEYS_V2 | {"current_gate_receipt"}
M3_SCOPE_DECISION_PATH = "docs/evidence/m3-scope-correction-2026-10-02.md"
M3_SCOPE_KIND = "m3_one_account_claude_vertical"
M3_SCOPE_DECISION_SHA256 = (
    "7b4c0fcd46a47e0827c03da3973f08243b23c1c398dca4fe42e3388795f0067b"
)
M3_PREDECESSOR_PATH = "docs/evidence/v1-m3-acceptance-status-v1.json"
M3_PREDECESSOR_RECORD_ID = "M3-ACCEPTANCE-2026-09-24-01"
M3_PREDECESSOR_SHA256 = (
    "ff40162231e1af00798828fb4694d64748fc1d125a40b0baa80d70596aa7248a"
)
M3_V2_PREDECESSOR_PATH = "docs/evidence/v1-m3-acceptance-status-v2.json"
M3_V2_PREDECESSOR_RECORD_ID = "M3-ACCEPTANCE-2026-10-02-01"
M3_V2_PREDECESSOR_SHA256: str | None = (
    "3fd735a90aaee5be32e60880add1a316814400e5d3233bf0d8dbe006820605f8"
)
M3_CURRENT_GATE_RECEIPT_PATH = "docs/evidence/m3-current-gate-receipt-2026-10-03.json"
M3_CURRENT_GATE_RECEIPT_SHA256: str | None = (
    "043d4d51ff201bf14c3b50708e9391fd2c9c25c488d7e387fd0b1545028bc121"
)
M3_HISTORICAL_TDD_OWNER_ARTIFACT_PATH = (
    "docs/evidence/m3-historical-tdd-owner-disposition-2026-10-03.md"
)
M3_OWNER_LIVE_ARTIFACT_PATH = (
    "docs/evidence/m3-owner-live-countersignature-2026-10-03.md"
)
# These decisions are separate owner evidence, never inferred from gate output.
M3_HISTORICAL_TDD_OWNER_ARTIFACT_SHA256: str | None = (
    "8a514b7736a39b2dc29d06a8d09a3aee701e20beae86017419f9f012d57b5a3e"
)
M3_OWNER_LIVE_ARTIFACT_SHA256: str | None = (
    "85ab4fcee6291cef04c6334588d5118de2838b41587929a00ca231b964c135d2"
)
M3_CURRENT_GATE_LANES = frozenset(
    {
        "selected_account_preflight",
        "fresh_quota_lineage",
        "registry_unchanged",
        "revision_bound_service",
        "current_browser",
        "runtime_regression",
        "technical_suite",
        "quality",
        "build",
        "mutation",
        "documentation",
        "git_preflight",
    }
)
M3_CURRENT_GATE_EXACT_EVIDENCE = {
    "selected_account_preflight": "browser_api_account_verified",
    "registry_unchanged": "browser_get_only_registry_unchanged",
    "revision_bound_service": "service_restarted_from_clean_head",
    "current_browser": "visible_shared_chrome_passed",
    "technical_suite": "auto-m3-test_passed",
    "quality": "auto-quality_passed",
    "build": "auto-build_passed",
    "mutation": "auto-mutation_passed",
    "documentation": "auto-docs-check_passed",
    "git_preflight": "auto-git-preflight_passed",
}
M3_CURRENT_GATE_COMMAND = "python3 tools/automation/run.py AUTO-M3-EXIT"
M3_STATUS_MARKER = re.compile(
    r"<!-- agentmonitor-milestone-status:v1 "
    r"milestone=(?P<milestone>\S+) "
    r"lifecycle=(?P<lifecycle>active|superseded) "
    r"status=(?P<status>passed|failed|blocked|not_run|deviation_accepted) "
    r"authority=(?P<authority>[A-Za-z0-9._-]+) -->"
)
V1_IMPLEMENTATION_BACKLOG = Path("docs/superpowers/plans/implementation-backlog.toml")
V1_IMPLEMENTATION_STATUS = Path("docs/evidence/v1-implementation-status-v1.json")
V1_STATUS_TOP_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "record_id",
        "implementation_revision",
        "recorded_at",
        "planning_backlog",
        "planning_backlog_sha256",
        "roadmap",
        "milestones",
        "stories",
    }
)
V1_STATUS_MILESTONE_KEYS = frozenset(
    {
        "milestone_id",
        "title",
        "depends_on",
        "delivery_state",
        "canonical_gate_state",
        "gate_binding",
        "gate_revision",
        "acceptance_state",
        "acceptance_scope",
        "acceptance_decision_path",
        "dependency_state",
        "unresolved_dependency_ids",
        "evidence_paths",
        "decision",
    }
)
V1_STATUS_STORY_KEYS = frozenset(
    {
        "story_id",
        "milestone_id",
        "title",
        "delivery_state",
        "evidence_paths",
        "decision",
    }
)
V1_DELIVERY_STATES = frozenset({"planned", "in_progress", "implemented"})
V1_GATE_STATES = frozenset({"not_run", "blocked", "failed", "passed"})
V1_GATE_BINDINGS = frozenset(
    {"none", "historical_run", "current_implementation_revision"}
)
V1_ACCEPTANCE_STATES = frozenset({"not_recorded", "blocked", "accepted"})
V1_ACCEPTANCE_SCOPES = frozenset(
    {"none", "local_foundation", "local_authenticated_shell", "full_milestone"}
)
V1_DEPENDENCY_STATES = frozenset({"not_applicable", "satisfied", "unresolved"})
V1_ROADMAP_HEADING = re.compile(r"^## (V1-M\d+) — (.+)$", re.MULTILINE)
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_REVISION = re.compile(r"[0-9a-f]{40}")
UTC_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
EXCLUDED_MARKDOWN_DIRECTORY_NAMES = frozenset(
    {
        ".ci-tools",
        ".git",
        ".superpowers",
        ".venv",
        "__pycache__",
        "node_modules",
    }
)


def _safe_repository_path(repository_root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value or value.startswith("/"):
        return None
    candidate = (repository_root / value).resolve()
    try:
        candidate.relative_to(repository_root.resolve())
    except ValueError:
        return None
    return candidate


def _m3_markers(repository_root: Path) -> list[tuple[Path, dict[str, str]]]:
    markers: list[tuple[Path, dict[str, str]]] = []
    for document in enumerate_repository_markdown(repository_root):
        text = document.read_text(encoding="utf-8")
        for match in M3_STATUS_MARKER.finditer(text):
            if match.group("milestone") == "V1-M3":
                markers.append((document, match.groupdict()))
    return markers


def _m3_lane_evidence_is_canonical(lane_id: str, evidence: object) -> bool:
    if not isinstance(evidence, str):
        return False
    if lane_id == "fresh_quota_lineage":
        return re.fullmatch(r"run_sha256:[0-9a-f]{64}", evidence) is not None
    if lane_id == "runtime_regression":
        return evidence in {"runtime_query:available", "runtime_query:partial"}
    return evidence == M3_CURRENT_GATE_EXACT_EVIDENCE.get(lane_id)


def _validate_m3_v3_decision_bindings(
    reviewer_decisions: object,
    *,
    receipt_evidence_id: str | None,
    historical_evidence_id: str | None,
    owner_live_evidence_id: str | None,
) -> list[str]:
    """Validate V3 decision references without reading files or trusting labels."""
    decisions_by_id = (
        {
            item["decision_id"]: item
            for item in reviewer_decisions
            if isinstance(item, dict) and isinstance(item.get("decision_id"), str)
        }
        if isinstance(reviewer_decisions, list)
        else {}
    )
    required = (
        ("M3-SCOPE-2026-10-02", "passed", "M3 scope decision", None),
        (
            "M3-CURRENT-GATE-2026-10-02",
            "passed",
            "M3 current-gate review",
            receipt_evidence_id,
        ),
        (
            "M3-HISTORICAL-TDD-2026-10-03",
            "deviation_accepted",
            "M3 historical TDD owner disposition",
            historical_evidence_id,
        ),
        (
            "M3-OWNER-LIVE-2026-10-03",
            "passed",
            "M3 owner live countersignature",
            owner_live_evidence_id,
        ),
    )
    violations: list[str] = []
    for decision_id, status, label, required_evidence_id in required:
        decision = decisions_by_id.get(decision_id)
        if decision is None or decision.get("status") != status:
            violations.append(f"{label} is missing")
            continue
        references = decision.get("evidence_ids")
        if not isinstance(references, list) or not references:
            violations.append(f"{label} lacks evidence")
            continue
        if decision_id == "M3-SCOPE-2026-10-02":
            continue
        if required_evidence_id is None or required_evidence_id not in references:
            if decision_id == "M3-CURRENT-GATE-2026-10-02":
                violations.append("M3 current-gate review lacks receipt evidence")
            else:
                violations.append(f"{label} lacks dedicated evidence")
    return violations


def _m3_pinned_evidence_id(
    evidence: object, *, path: str, pinned_sha: str | None
) -> str | None:
    """Find an artifact only by its independent exact path and pinned digest."""
    if pinned_sha is None or not isinstance(evidence, list):
        return None
    return next(
        (
            item["evidence_id"]
            for item in evidence
            if isinstance(item, dict)
            and item.get("path") == path
            and item.get("sha256") == pinned_sha
            and isinstance(item.get("evidence_id"), str)
        ),
        None,
    )


def _validate_m3_receipt_payload(
    receipt: object, record: dict[str, object]
) -> list[str]:
    """Check typed gate metadata without crossing a file or provider boundary."""
    violations: list[str] = []
    if not isinstance(receipt, dict):
        return ["M3 current-gate receipt is not valid JSON object"]
    expected_keys = {
        "schema_version",
        "record_type",
        "receipt_id",
        "milestone_id",
        "command_id",
        "command",
        "implementation_revision",
        "started_at",
        "completed_at",
        "status",
        "exit_code",
        "skips",
        "selected_account_digest",
        "required_lanes",
    }
    if set(receipt) != expected_keys:
        violations.append("M3 current-gate receipt fields are not closed")
    receipt_id = receipt.get("receipt_id")
    if (
        receipt.get("schema_version") != "1.0.0"
        or receipt.get("record_type") != "agentmonitor.m3_current_gate_receipt"
        or not isinstance(receipt_id, str)
        or not receipt_id
        or receipt.get("milestone_id") != "V1-M3"
    ):
        violations.append("M3 current-gate receipt identity is invalid")
    if receipt.get("implementation_revision") != record.get("assessed_revision"):
        violations.append("M3 current-gate receipt revision differs")
    started_at = receipt.get("started_at")
    completed_at = receipt.get("completed_at")
    recorded_at = record.get("recorded_at")
    if (
        not isinstance(started_at, str)
        or UTC_INSTANT.fullmatch(started_at) is None
        or not isinstance(completed_at, str)
        or UTC_INSTANT.fullmatch(completed_at) is None
        or completed_at < started_at
        or not isinstance(recorded_at, str)
        or UTC_INSTANT.fullmatch(recorded_at) is None
        or recorded_at < completed_at
    ):
        violations.append("M3 current-gate receipt time is invalid")
    if (
        receipt.get("command_id") != "AUTO-M3-EXIT"
        or receipt.get("command") != M3_CURRENT_GATE_COMMAND
        or receipt.get("status") != "passed"
        or type(receipt.get("exit_code")) is not int
        or receipt.get("exit_code") != 0
        or receipt.get("skips") != []
    ):
        violations.append("M3 current-gate receipt result is not Passed")
    account_digest = receipt.get("selected_account_digest")
    if not isinstance(account_digest, str) or SHA256.fullmatch(account_digest) is None:
        violations.append("M3 current-gate selected-account digest is invalid")
    lanes = receipt.get("required_lanes")
    if not isinstance(lanes, list) or len(lanes) != len(M3_CURRENT_GATE_LANES):
        violations.append("M3 current-gate receipt lanes are incomplete")
    else:
        lane_ids: list[str] = []
        for lane in lanes:
            if not isinstance(lane, dict) or set(lane) != {
                "lane_id",
                "status",
                "evidence",
            }:
                violations.append("M3 current-gate receipt lane is not closed")
                continue
            lane_id = lane.get("lane_id")
            if not isinstance(lane_id, str):
                violations.append("M3 current-gate receipt lane ID is invalid")
                continue
            lane_ids.append(lane_id)
            evidence = lane.get("evidence")
            if lane.get("status") != "passed":
                violations.append("M3 current-gate receipt lane did not pass")
            if not _m3_lane_evidence_is_canonical(lane_id, evidence):
                violations.append("M3 current-gate receipt lane evidence is invalid")
        if set(lane_ids) != M3_CURRENT_GATE_LANES or len(lane_ids) != len(
            set(lane_ids)
        ):
            violations.append("M3 current-gate receipt lanes are incomplete")
    return violations


def _validate_m3_current_gate_receipt(
    repository_root: Path, record: dict[str, object]
) -> list[str]:
    violations: list[str] = []
    reference = record.get("current_gate_receipt")
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        return ["M3 current-gate receipt reference is not closed"]

    path_value = reference.get("path")
    path = _safe_repository_path(repository_root, path_value)
    if path_value != M3_CURRENT_GATE_RECEIPT_PATH or path is None:
        violations.append("M3 current-gate receipt path is invalid")
    if path is None or not path.is_file():
        violations.append("M3 current-gate receipt file is missing")

    digest = reference.get("sha256")
    if M3_CURRENT_GATE_RECEIPT_SHA256 is None:
        violations.append("M3 current-gate receipt SHA is not pinned")
    elif digest != M3_CURRENT_GATE_RECEIPT_SHA256:
        violations.append("M3 current-gate receipt digest is not canonical")
    if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
        violations.append("M3 current-gate receipt digest is invalid")
    elif path is not None and path.is_file():
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            violations.append("M3 current-gate receipt digest does not match file")
        try:
            receipt = json.loads(content)
        except (UnicodeError, json.JSONDecodeError):
            receipt = None
        violations.extend(_validate_m3_receipt_payload(receipt, record))
    return violations


def _validate_m3_record(
    repository_root: Path, relative: Path, record: dict[str, object]
) -> list[str]:
    violations: list[str] = []

    def reject(code: str) -> None:
        violations.append(f"{relative}: {code}")

    schema_version = record.get("schema_version")
    expected_keys = {
        "1.0.0": M3_RECORD_KEYS_V1,
        "2.0.0": M3_RECORD_KEYS_V2,
        "3.0.0": M3_RECORD_KEYS_V3,
    }.get(schema_version, M3_RECORD_KEYS_V1)
    if set(record) != expected_keys:
        reject("acceptance record keys do not match V1 schema")
    if schema_version not in {"1.0.0", "2.0.0", "3.0.0"}:
        reject("acceptance record schema_version is unsupported")
    if record.get("record_type") != "agentmonitor.milestone_acceptance_status":
        reject("acceptance record type is invalid")
    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not re.fullmatch(
        r"[A-Z0-9][A-Z0-9._-]{2,127}", record_id
    ):
        reject("acceptance record_id is invalid")
    if record.get("milestone_id") != "V1-M3":
        reject("acceptance record milestone_id must be V1-M3")
    if record.get("lifecycle") not in {"active", "superseded"}:
        reject("acceptance record lifecycle is invalid")
    overall_status = record.get("overall_status")
    if overall_status not in M3_COMMAND_STATUSES:
        reject("acceptance record overall_status is invalid")
    if schema_version == "2.0.0" and overall_status == "passed":
        reject("M3 schema 2.0.0 cannot claim Passed without a current-gate receipt")
    if schema_version == "3.0.0" and overall_status != "passed":
        reject("M3 schema 3.0.0 requires a Passed current gate")
    revision = record.get("assessed_revision")
    if not isinstance(revision, str) or GIT_REVISION.fullmatch(revision) is None:
        reject("acceptance record assessed_revision is not an exact revision")
    recorded_at = record.get("recorded_at")
    if not isinstance(recorded_at, str) or UTC_INSTANT.fullmatch(recorded_at) is None:
        reject("acceptance record recorded_at is not exact UTC")

    evidence_ids: set[str] = set()
    evidence = record.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        reject("acceptance record evidence must be non-empty")
    else:
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {
                "evidence_id",
                "path",
                "sha256",
            }:
                reject("acceptance evidence entry is not closed")
                continue
            evidence_id = item.get("evidence_id")
            if not isinstance(evidence_id, str) or not evidence_id:
                reject("acceptance evidence_id is invalid")
                continue
            if evidence_id in evidence_ids:
                reject(f"duplicate acceptance evidence_id {evidence_id}")
            evidence_ids.add(evidence_id)
            path_value = item.get("path")
            path = _safe_repository_path(repository_root, path_value)
            if (
                path is None
                or not isinstance(path_value, str)
                or not path_value.startswith("docs/evidence/")
                or not path.is_file()
            ):
                reject(f"acceptance evidence path is invalid for {evidence_id}")
                continue
            digest = item.get("sha256")
            if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
                reject(f"acceptance evidence digest is invalid for {evidence_id}")
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                reject(f"evidence digest mismatch for {evidence_id}")

    def evidence_references(value: object, owner: str) -> None:
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            reject(f"{owner} evidence_ids are invalid")
            return
        unknown = set(value) - evidence_ids
        if unknown:
            reject(f"{owner} references unknown evidence_ids")

    commands = record.get("commands")
    command_ids: set[str] = set()
    command_statuses: dict[str, str] = {}
    if not isinstance(commands, list) or not commands:
        reject("acceptance commands must be non-empty")
    else:
        for item in commands:
            if not isinstance(item, dict) or set(item) != {
                "command_id",
                "command",
                "status",
                "exit_code",
                "skips",
                "evidence_ids",
            }:
                reject("acceptance command entry is not closed")
                continue
            command_id = item.get("command_id")
            if not isinstance(command_id, str) or not command_id:
                reject("acceptance command_id is invalid")
                continue
            if command_id in command_ids:
                reject(f"duplicate acceptance command_id {command_id}")
            command_ids.add(command_id)
            status = item.get("status")
            if status not in M3_COMMAND_STATUSES:
                reject(f"acceptance command status is invalid for {command_id}")
                continue
            command_statuses[command_id] = status
            if not isinstance(item.get("command"), str) or not item["command"]:
                reject(f"acceptance command text is invalid for {command_id}")
            exit_code = item.get("exit_code")
            if (status == "passed" and exit_code != 0) or (
                status == "failed" and (type(exit_code) is not int or exit_code == 0)
            ):
                reject(f"acceptance command exit_code contradicts {command_id}")
            if status in {"blocked", "not_run"} and exit_code is not None:
                reject(f"unexecuted acceptance command has exit_code for {command_id}")
            skips = item.get("skips")
            if not isinstance(skips, list) or not all(
                isinstance(value, str) and value for value in skips
            ):
                reject(f"acceptance command skips are invalid for {command_id}")
            elif status == "passed" and skips:
                reject(f"passed command reports skips for {command_id}")
            references = item.get("evidence_ids")
            evidence_references(references, f"command {command_id}")
            if status == "passed" and not references:
                reject(f"passed command lacks evidence for {command_id}")
    if "AUTO-M3-EXIT" not in command_ids:
        reject("acceptance record omits AUTO-M3-EXIT")
    if overall_status == "passed" and command_statuses.get("AUTO-M3-EXIT") != "passed":
        reject("passed milestone contradicts AUTO-M3-EXIT result")
    if overall_status == "passed" and any(
        status != "passed" for status in command_statuses.values()
    ):
        reject("passed milestone contradicts command status")

    criteria = record.get("criteria")
    criterion_ids: list[str] = []
    criterion_statuses: list[str] = []
    if not isinstance(criteria, list):
        reject("acceptance criteria must be a list")
    else:
        for item in criteria:
            if not isinstance(item, dict) or set(item) != {
                "criterion_id",
                "status",
                "evidence_ids",
                "decision",
            }:
                reject("acceptance criterion entry is not closed")
                continue
            criterion_id = item.get("criterion_id")
            status = item.get("status")
            if not isinstance(criterion_id, str):
                reject("acceptance criterion_id is invalid")
                continue
            criterion_ids.append(criterion_id)
            if status not in M3_STATUSES:
                reject(f"acceptance criterion status is invalid for {criterion_id}")
                continue
            criterion_statuses.append(status)
            references = item.get("evidence_ids")
            evidence_references(references, f"criterion {criterion_id}")
            if status in {"passed", "deviation_accepted"} and not references:
                reject(f"accepted criterion lacks evidence for {criterion_id}")
            if not isinstance(item.get("decision"), str) or not item["decision"]:
                reject(f"acceptance criterion decision is invalid for {criterion_id}")
    if len(criterion_ids) != len(set(criterion_ids)):
        reject("acceptance criteria contain duplicates")
    expected_criteria = (
        M3_REQUIRED_CRITERIA_V2
        if schema_version in {"2.0.0", "3.0.0"}
        else M3_REQUIRED_CRITERIA_V1
    )
    if set(criterion_ids) != expected_criteria:
        reject("acceptance criteria do not match approved M3 Task 6")
    if overall_status == "passed" and any(
        status not in {"passed", "deviation_accepted"} for status in criterion_statuses
    ):
        reject("passed milestone contradicts outstanding criterion status")

    reviewer_decisions = record.get("reviewer_decisions")
    decision_ids: set[str] = set()
    reviewer_statuses: list[str] = []
    if not isinstance(reviewer_decisions, list) or not reviewer_decisions:
        reject("acceptance reviewer_decisions must be non-empty")
    else:
        for item in reviewer_decisions:
            if not isinstance(item, dict) or set(item) != {
                "decision_id",
                "status",
                "decision",
                "evidence_ids",
            }:
                reject("acceptance reviewer decision is not closed")
                continue
            decision_id = item.get("decision_id")
            if not isinstance(decision_id, str) or not decision_id:
                reject("acceptance reviewer decision_id is invalid")
                continue
            if decision_id in decision_ids:
                reject(f"duplicate acceptance reviewer decision {decision_id}")
            decision_ids.add(decision_id)
            reviewer_status = item.get("status")
            if reviewer_status not in M3_STATUSES:
                reject(f"acceptance reviewer status is invalid for {decision_id}")
            else:
                reviewer_statuses.append(reviewer_status)
            if not isinstance(item.get("decision"), str) or not item["decision"]:
                reject(f"acceptance reviewer decision is invalid for {decision_id}")
            evidence_references(
                item.get("evidence_ids"), f"reviewer decision {decision_id}"
            )
    if "deviation_accepted" in criterion_statuses and not any(
        isinstance(item, dict) and item.get("status") == "deviation_accepted"
        for item in reviewer_decisions
        if isinstance(reviewer_decisions, list)
    ):
        reject("deviation_accepted criterion lacks reviewer disposition")
    if overall_status == "passed" and any(
        status not in {"passed", "deviation_accepted"} for status in reviewer_statuses
    ):
        reject("passed milestone contradicts reviewer decision")
    supersedes = record.get("supersedes")
    if not isinstance(supersedes, list):
        reject("acceptance supersedes must be a list")
    else:
        for item in supersedes:
            if not isinstance(item, dict) or set(item) != {
                "path",
                "prior_status",
                "scope",
            }:
                reject("acceptance supersession entry is not closed")
                continue
            path = _safe_repository_path(repository_root, item.get("path"))
            if path is None or not path.is_file():
                reject("acceptance supersession path is invalid")
            if item.get("prior_status") not in M3_STATUSES:
                reject("acceptance supersession prior_status is invalid")
            if not isinstance(item.get("scope"), str) or not item["scope"]:
                reject("acceptance supersession scope is invalid")

    status_documents = record.get("status_documents")
    if not isinstance(status_documents, list) or not status_documents:
        reject("acceptance status_documents must be non-empty")
    else:
        for value in status_documents:
            path = _safe_repository_path(repository_root, value)
            if path is None or path.suffix != ".md" or not path.is_file():
                reject("acceptance status document path is invalid")

    if schema_version in {"2.0.0", "3.0.0"}:
        scope_decision = record.get("scope_decision")
        if not isinstance(scope_decision, dict) or set(scope_decision) != {
            "path",
            "sha256",
            "scope_kind",
        }:
            reject("M3 scope decision is not closed")
        else:
            scope_path_value = scope_decision.get("path")
            scope_path = _safe_repository_path(repository_root, scope_path_value)
            if (
                scope_path_value != M3_SCOPE_DECISION_PATH
                or scope_path is None
                or not scope_path.is_file()
            ):
                reject("M3 scope decision path is invalid")
            digest = scope_decision.get("sha256")
            if digest != M3_SCOPE_DECISION_SHA256:
                reject("M3 scope decision digest is not approved")
            elif (
                not isinstance(digest, str)
                or SHA256.fullmatch(digest) is None
                or scope_path is None
                or not scope_path.is_file()
                or hashlib.sha256(scope_path.read_bytes()).hexdigest() != digest
            ):
                reject("M3 scope decision digest is invalid")
            if scope_decision.get("scope_kind") != M3_SCOPE_KIND:
                reject("M3 scope decision kind is invalid")

        predecessor = record.get("supersedes_record")
        expected_predecessor_path = (
            M3_V2_PREDECESSOR_PATH if schema_version == "3.0.0" else M3_PREDECESSOR_PATH
        )
        expected_predecessor_id = (
            M3_V2_PREDECESSOR_RECORD_ID
            if schema_version == "3.0.0"
            else M3_PREDECESSOR_RECORD_ID
        )
        expected_predecessor_sha = (
            M3_V2_PREDECESSOR_SHA256
            if schema_version == "3.0.0"
            else M3_PREDECESSOR_SHA256
        )
        predecessor_label = (
            "M3 v2 predecessor" if schema_version == "3.0.0" else "M3 predecessor"
        )
        if not isinstance(predecessor, dict) or set(predecessor) != {
            "path",
            "record_id",
            "sha256",
            "prior_status",
        }:
            reject(f"{predecessor_label} record is not closed")
        else:
            predecessor_path_value = predecessor.get("path")
            predecessor_path = _safe_repository_path(
                repository_root, predecessor_path_value
            )
            if (
                predecessor_path is None
                or predecessor_path_value != expected_predecessor_path
                or not predecessor_path.is_file()
            ):
                record_word = "" if schema_version == "3.0.0" else " record"
                reject(f"{predecessor_label}{record_word} path is invalid")
            predecessor_digest = predecessor.get("sha256")
            if expected_predecessor_sha is None:
                reject("M3 v2 predecessor SHA is not pinned")
            elif predecessor_digest != expected_predecessor_sha:
                record_word = "" if schema_version == "3.0.0" else " record"
                reject(f"{predecessor_label}{record_word} digest is not canonical")
            elif (
                not isinstance(predecessor_digest, str)
                or SHA256.fullmatch(predecessor_digest) is None
                or predecessor_path is None
                or not predecessor_path.is_file()
                or hashlib.sha256(predecessor_path.read_bytes()).hexdigest()
                != predecessor_digest
            ):
                record_word = "" if schema_version == "3.0.0" else " record"
                reject(f"{predecessor_label}{record_word} digest is invalid")
            if predecessor.get("record_id") != expected_predecessor_id:
                reject(f"{predecessor_label} record_id is invalid")
            if predecessor.get("prior_status") != "blocked":
                reject(f"{predecessor_label} prior_status is invalid")
    if schema_version == "3.0.0":
        for code in _validate_m3_current_gate_receipt(repository_root, record):
            reject(code)
        receipt_reference = record.get("current_gate_receipt")
        receipt_path = (
            receipt_reference.get("path")
            if isinstance(receipt_reference, dict)
            else None
        )
        receipt_digest = (
            receipt_reference.get("sha256")
            if isinstance(receipt_reference, dict)
            else None
        )
        receipt_evidence_id = None
        if isinstance(evidence, list):
            for entry in evidence:
                if (
                    isinstance(entry, dict)
                    and entry.get("path") == receipt_path
                    and entry.get("sha256") == receipt_digest
                ):
                    receipt_evidence_id = entry.get("evidence_id")
                    break
        if not isinstance(receipt_evidence_id, str):
            reject("M3 current-gate receipt is absent from evidence")
        owner_artifacts = (
            (
                "M3 historical TDD owner disposition",
                M3_HISTORICAL_TDD_OWNER_ARTIFACT_PATH,
                M3_HISTORICAL_TDD_OWNER_ARTIFACT_SHA256,
            ),
            (
                "M3 owner live countersignature",
                M3_OWNER_LIVE_ARTIFACT_PATH,
                M3_OWNER_LIVE_ARTIFACT_SHA256,
            ),
        )
        owner_evidence_ids: list[str | None] = []
        for label, artifact_path, pinned_sha in owner_artifacts:
            if pinned_sha is None:
                reject(f"{label} artifact SHA is not pinned")
            artifact_evidence_id = _m3_pinned_evidence_id(
                evidence, path=artifact_path, pinned_sha=pinned_sha
            )
            if artifact_evidence_id is None:
                reject(f"{label} artifact is absent from evidence")
            owner_evidence_ids.append(artifact_evidence_id)
        for code in _validate_m3_v3_decision_bindings(
            reviewer_decisions,
            receipt_evidence_id=receipt_evidence_id,
            historical_evidence_id=owner_evidence_ids[0],
            owner_live_evidence_id=owner_evidence_ids[1],
        ):
            reject(code)
        gate_command = None
        if isinstance(commands, list):
            gate_command = next(
                (
                    entry
                    for entry in commands
                    if isinstance(entry, dict)
                    and entry.get("command_id") == "AUTO-M3-EXIT"
                ),
                None,
            )
        if (
            not isinstance(gate_command, dict)
            or gate_command.get("command") != M3_CURRENT_GATE_COMMAND
            or gate_command.get("status") != "passed"
            or gate_command.get("exit_code") != 0
            or gate_command.get("skips") != []
            or not isinstance(gate_command.get("evidence_ids"), list)
            or receipt_evidence_id not in gate_command["evidence_ids"]
        ):
            reject("M3 AUTO-M3-EXIT is not bound to current-gate receipt")
        closure_criterion = None
        if isinstance(criteria, list):
            closure_criterion = next(
                (
                    entry
                    for entry in criteria
                    if isinstance(entry, dict)
                    and entry.get("criterion_id") == "AC-M3-007"
                ),
                None,
            )
        if (
            not isinstance(closure_criterion, dict)
            or closure_criterion.get("status") != "passed"
            or not isinstance(closure_criterion.get("evidence_ids"), list)
            or receipt_evidence_id not in closure_criterion["evidence_ids"]
        ):
            reject("M3 closure criterion lacks current-gate receipt")
    return violations


def check_m3_acceptance_status(repository_root: Path) -> list[str]:
    """Fail closed when active V1-M3 custody is missing or contradictory."""

    if not (repository_root / M3_PLAN).is_file():
        return []
    violations: list[str] = []
    records: list[tuple[Path, dict[str, object]]] = []
    evidence_root = repository_root / "docs/evidence"
    for path in sorted(evidence_root.glob(M3_RECORD_GLOB)):
        relative = path.relative_to(repository_root)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            violations.append(f"{relative}: acceptance record is not valid JSON")
            continue
        if not isinstance(raw, dict):
            violations.append(f"{relative}: acceptance record root must be an object")
            continue
        records.append((relative, raw))
        violations.extend(_validate_m3_record(repository_root, relative, raw))

    active = [item for item in records if item[1].get("lifecycle") == "active"]
    if len(active) != 1:
        violations.append(
            f"V1-M3 requires exactly one active acceptance record; found {len(active)}"
        )

    markers = _m3_markers(repository_root)
    active_markers = [item for item in markers if item[1]["lifecycle"] == "active"]
    if len(active_markers) != 1:
        violations.append(
            "V1-M3 requires exactly one active Markdown status marker; "
            f"found {len(active_markers)}"
        )
    if len(active) == 1 and len(active_markers) == 1:
        _record_path, record = active[0]
        marker_path, marker = active_markers[0]
        if marker["status"] != record.get("overall_status") or marker[
            "authority"
        ] != record.get("record_id"):
            violations.append(
                f"{marker_path.relative_to(repository_root)}: active status marker "
                "contradicts acceptance record"
            )
        documents = record.get("status_documents")
        if isinstance(documents, list):
            marker_documents = {
                path.relative_to(repository_root).as_posix(): marker
                for path, marker in markers
            }
            missing = set(documents) - marker_documents.keys()
            if missing:
                violations.append(
                    "V1-M3 status_documents lack machine status markers: "
                    + ", ".join(sorted(missing))
                )
            for document in set(documents) & marker_documents.keys():
                if marker_documents[document]["authority"] != record.get("record_id"):
                    violations.append(
                        f"{document}: milestone status marker names another authority"
                    )
        supersedes = record.get("supersedes")
        if isinstance(supersedes, list):
            markers_by_path = {
                path.relative_to(repository_root).as_posix(): marker
                for path, marker in markers
            }
            for item in supersedes:
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    continue
                marker = markers_by_path.get(item["path"])
                if (
                    marker is None
                    or marker["lifecycle"] != "superseded"
                    or marker["status"] != item.get("prior_status")
                    or marker["authority"] != record.get("record_id")
                ):
                    violations.append(
                        f"{item['path']}: superseded status lacks matching marker"
                    )
        schema_version = record.get("schema_version")
        if schema_version in {"2.0.0", "3.0.0"}:
            predecessor = record.get("supersedes_record")
            records_by_path = {
                relative.as_posix(): candidate for relative, candidate in records
            }
            if isinstance(predecessor, dict) and isinstance(
                predecessor.get("path"), str
            ):
                prior = records_by_path.get(predecessor["path"])
                expected_schema = "2.0.0" if schema_version == "3.0.0" else "1.0.0"
                if (
                    prior is None
                    or prior.get("schema_version") != expected_schema
                    or prior.get("lifecycle") != "superseded"
                    or prior.get("record_id") != predecessor.get("record_id")
                    or prior.get("overall_status") != predecessor.get("prior_status")
                ):
                    label = (
                        "M3 v2 predecessor"
                        if schema_version == "3.0.0"
                        else "M3 predecessor"
                    )
                    violations.append(
                        f"{predecessor['path']}: {label} authority is invalid"
                    )
    return violations


def check_v1_implementation_status(repository_root: Path) -> list[str]:
    """Validate the current delivery overlay against the frozen import backlog."""

    backlog_path = repository_root / V1_IMPLEMENTATION_BACKLOG
    if not backlog_path.is_file():
        return []
    if not (repository_root / V1_IMPLEMENTATION_STATUS).is_file():
        return [
            f"{V1_IMPLEMENTATION_STATUS}: V1 implementation status overlay is missing"
        ]

    violations: list[str] = []

    def reject(code: str) -> None:
        violations.append(f"{V1_IMPLEMENTATION_STATUS}: {code}")

    try:
        with backlog_path.open("rb") as stream:
            backlog = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        return [f"{V1_IMPLEMENTATION_BACKLOG}: import backlog is not valid TOML"]
    try:
        status = json.loads(
            (repository_root / V1_IMPLEMENTATION_STATUS).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return [f"{V1_IMPLEMENTATION_STATUS}: status overlay is not valid JSON"]
    if not isinstance(status, dict):
        return [f"{V1_IMPLEMENTATION_STATUS}: status overlay root must be an object"]
    if set(status) != V1_STATUS_TOP_KEYS:
        reject("status overlay keys do not match V1 schema")
    if status.get("schema_version") != "1.0.0":
        reject("schema_version must be 1.0.0")
    if status.get("record_type") != "agentmonitor.v1_implementation_status":
        reject("record_type is invalid")
    record_id = status.get("record_id")
    if (
        not isinstance(record_id, str)
        or re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{2,127}", record_id) is None
    ):
        reject("record_id is invalid")
    revision = status.get("implementation_revision")
    if not isinstance(revision, str) or GIT_REVISION.fullmatch(revision) is None:
        reject("implementation_revision is not an exact revision")
    recorded_at = status.get("recorded_at")
    if not isinstance(recorded_at, str) or UTC_INSTANT.fullmatch(recorded_at) is None:
        reject("recorded_at is not exact UTC")
    if status.get("planning_backlog") != V1_IMPLEMENTATION_BACKLOG.as_posix():
        reject("planning_backlog does not name the canonical import backlog")
    backlog_digest = status.get("planning_backlog_sha256")
    if (
        not isinstance(backlog_digest, str)
        or SHA256.fullmatch(backlog_digest) is None
        or backlog_digest != hashlib.sha256(backlog_path.read_bytes()).hexdigest()
    ):
        reject("planning_backlog_sha256 does not match the import backlog")

    backlog_milestones_raw = backlog.get("milestones")
    backlog_stories_raw = backlog.get("stories")
    if not isinstance(backlog_milestones_raw, list) or not all(
        isinstance(item, dict) for item in backlog_milestones_raw
    ):
        reject("canonical backlog milestones are invalid")
        backlog_milestones_raw = []
    if not isinstance(backlog_stories_raw, list) or not all(
        isinstance(item, dict) for item in backlog_stories_raw
    ):
        reject("canonical backlog stories are invalid")
        backlog_stories_raw = []
    backlog_milestones = {
        item.get("id"): item
        for item in backlog_milestones_raw
        if isinstance(item.get("id"), str)
    }
    backlog_stories = {
        item.get("id"): item
        for item in backlog_stories_raw
        if isinstance(item.get("id"), str)
    }

    def evidence_paths(value: object, *, owner: str, required: bool) -> list[str]:
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item for item in value
        ):
            reject(f"{owner} evidence_paths are invalid")
            return []
        if required and not value:
            reject(f"{owner} requires implementation evidence")
        for item in value:
            path = _safe_repository_path(repository_root, item)
            if (
                path is None
                or not item.startswith("docs/evidence/")
                or not path.is_file()
            ):
                reject(f"{owner} evidence path is invalid: {item}")
        return value

    milestones_raw = status.get("milestones")
    milestone_entries: dict[str, dict[str, object]] = {}
    if not isinstance(milestones_raw, list):
        reject("milestones must be a list")
    else:
        for item in milestones_raw:
            if not isinstance(item, dict) or set(item) != V1_STATUS_MILESTONE_KEYS:
                reject("milestone entry is not closed")
                continue
            milestone_id = item.get("milestone_id")
            if not isinstance(milestone_id, str):
                reject("milestone_id is invalid")
                continue
            if milestone_id in milestone_entries:
                reject(f"duplicate milestone {milestone_id}")
                continue
            milestone_entries[milestone_id] = item
            expected = backlog_milestones.get(milestone_id)
            if expected is None:
                reject(f"unknown milestone {milestone_id}")
                continue
            if item.get("title") != expected.get("title"):
                reject(f"milestone title differs from backlog for {milestone_id}")
            if item.get("depends_on") != expected.get("depends_on"):
                reject(f"milestone dependencies differ from backlog for {milestone_id}")
            delivery = item.get("delivery_state")
            gate = item.get("canonical_gate_state")
            binding = item.get("gate_binding")
            gate_revision = item.get("gate_revision")
            acceptance = item.get("acceptance_state")
            scope = item.get("acceptance_scope")
            dependency = item.get("dependency_state")
            if delivery not in V1_DELIVERY_STATES:
                reject(f"delivery_state is invalid for {milestone_id}")
            if gate not in V1_GATE_STATES:
                reject(f"canonical_gate_state is invalid for {milestone_id}")
            if binding not in V1_GATE_BINDINGS:
                reject(f"gate_binding is invalid for {milestone_id}")
            if gate_revision is not None and (
                not isinstance(gate_revision, str)
                or GIT_REVISION.fullmatch(gate_revision) is None
            ):
                reject(f"gate_revision is invalid for {milestone_id}")
            if acceptance not in V1_ACCEPTANCE_STATES:
                reject(f"acceptance_state is invalid for {milestone_id}")
            if scope not in V1_ACCEPTANCE_SCOPES:
                reject(f"acceptance_scope is invalid for {milestone_id}")
            if dependency not in V1_DEPENDENCY_STATES:
                reject(f"dependency_state is invalid for {milestone_id}")
            unresolved = item.get("unresolved_dependency_ids")
            expected_dependencies = expected.get("depends_on")
            if not isinstance(unresolved, list) or not all(
                isinstance(value, str) for value in unresolved
            ):
                reject(f"unresolved_dependency_ids are invalid for {milestone_id}")
                unresolved = []
            elif len(unresolved) != len(set(unresolved)) or not set(
                unresolved
            ).issubset(set(expected_dependencies or [])):
                reject(f"unresolved dependencies are inconsistent for {milestone_id}")
            if not expected_dependencies and (
                dependency != "not_applicable" or unresolved
            ):
                reject(f"dependency state must be not_applicable for {milestone_id}")
            if expected_dependencies and dependency == "satisfied" and unresolved:
                reject(
                    f"satisfied milestone lists unresolved dependencies: {milestone_id}"
                )
            if dependency == "unresolved" and not unresolved:
                reject(f"unresolved milestone lacks dependency IDs: {milestone_id}")
            if gate == "passed" and binding == "none":
                reject(f"passed gate lacks a revision binding for {milestone_id}")
            if gate != "passed" and binding != "none":
                reject(f"unpassed gate has a positive binding for {milestone_id}")
            if binding == "none" and gate_revision is not None:
                reject(f"unbound gate has a revision for {milestone_id}")
            if (
                binding == "current_implementation_revision"
                and gate_revision != revision
            ):
                reject(
                    "current gate revision differs from implementation revision "
                    f"for {milestone_id}"
                )
            if acceptance == "accepted" and (
                delivery != "implemented"
                or gate != "passed"
                or dependency == "unresolved"
                or scope == "none"
            ):
                reject(
                    f"accepted milestone is internally contradictory: {milestone_id}"
                )
            if acceptance == "not_recorded" and scope != "none":
                reject(f"unrecorded acceptance has a scope for {milestone_id}")
            if delivery == "planned" and (
                gate != "not_run" or acceptance != "not_recorded"
            ):
                reject(f"planned milestone claims execution for {milestone_id}")
            milestone_evidence = evidence_paths(
                item.get("evidence_paths"),
                owner=f"milestone {milestone_id}",
                required=delivery != "planned" or gate == "passed",
            )
            acceptance_path_value = item.get("acceptance_decision_path")
            acceptance_path = _safe_repository_path(
                repository_root, acceptance_path_value
            )
            if acceptance in {"accepted", "blocked"}:
                if (
                    acceptance_path is None
                    or not isinstance(acceptance_path_value, str)
                    or not acceptance_path_value.startswith("docs/evidence/")
                    or not acceptance_path.is_file()
                    or acceptance_path_value not in milestone_evidence
                ):
                    state_name = (
                        "accepted milestone lacks acceptance decision evidence"
                        if acceptance == "accepted"
                        else "blocked milestone lacks acceptance decision evidence"
                    )
                    reject(f"{state_name}: {milestone_id}")
            elif acceptance_path_value is not None:
                reject(f"unrecorded acceptance has decision evidence: {milestone_id}")
            if not isinstance(item.get("decision"), str) or not item["decision"]:
                reject(f"decision is invalid for milestone {milestone_id}")
    if set(milestone_entries) != set(backlog_milestones):
        reject("milestone IDs do not exactly match the import backlog")
    for milestone_id, item in milestone_entries.items():
        expected = backlog_milestones.get(milestone_id)
        if expected is None:
            continue
        dependencies = expected.get("depends_on")
        if not isinstance(dependencies, list):
            continue
        unresolved_expected = {
            dependency_id
            for dependency_id in dependencies
            if milestone_entries.get(dependency_id, {}).get("acceptance_state")
            != "accepted"
        }
        unresolved_recorded = item.get("unresolved_dependency_ids")
        dependency_state = item.get("dependency_state")
        expected_state = (
            "not_applicable"
            if not dependencies
            else "unresolved"
            if unresolved_expected
            else "satisfied"
        )
        if (
            dependency_state != expected_state
            or not isinstance(unresolved_recorded, list)
            or set(unresolved_recorded) != unresolved_expected
        ):
            reject(f"dependency acceptance is inconsistent for {milestone_id}")

    m3_entry = milestone_entries.get("V1-M3")
    if m3_entry is not None:
        active_m3_records: list[tuple[str, dict[str, object]]] = []
        evidence_root = repository_root / "docs/evidence"
        for path in sorted(evidence_root.glob(M3_RECORD_GLOB)):
            try:
                candidate = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(candidate, dict) and candidate.get("lifecycle") == "active":
                active_m3_records.append(
                    (path.relative_to(repository_root).as_posix(), candidate)
                )
        if len(active_m3_records) == 1:
            active_path, active_record = active_m3_records[0]
            active_status = active_record.get("overall_status")
            expected_acceptance = {
                "passed": "accepted",
                "blocked": "blocked",
                "failed": "blocked",
                "not_run": "not_recorded",
            }.get(active_status)
            if m3_entry.get("acceptance_state") != expected_acceptance:
                reject(
                    "V1-M3 acceptance state contradicts the active acceptance record"
                )
            if m3_entry.get("acceptance_decision_path") != active_path:
                reject("V1-M3 acceptance decision does not name the active record")

    stories_raw = status.get("stories")
    story_entries: dict[str, dict[str, object]] = {}
    if not isinstance(stories_raw, list):
        reject("stories must be a list")
    else:
        for item in stories_raw:
            if not isinstance(item, dict) or set(item) != V1_STATUS_STORY_KEYS:
                reject("story entry is not closed")
                continue
            story_id = item.get("story_id")
            if not isinstance(story_id, str):
                reject("story_id is invalid")
                continue
            if story_id in story_entries:
                reject(f"duplicate story {story_id}")
                continue
            story_entries[story_id] = item
            expected = backlog_stories.get(story_id)
            if expected is None:
                reject(f"unknown story {story_id}")
                continue
            if item.get("milestone_id") != expected.get("milestone_id"):
                reject(f"story milestone differs from backlog for {story_id}")
            if item.get("title") != expected.get("title"):
                reject(f"story title differs from backlog for {story_id}")
            delivery = item.get("delivery_state")
            if delivery not in V1_DELIVERY_STATES:
                reject(f"delivery_state is invalid for story {story_id}")
            evidence_paths(
                item.get("evidence_paths"),
                owner=f"story {story_id}",
                required=delivery != "planned",
            )
            if not isinstance(item.get("decision"), str) or not item["decision"]:
                reject(f"decision is invalid for story {story_id}")
    if set(story_entries) != set(backlog_stories):
        reject("story IDs do not exactly match the import backlog")
    for milestone_id, milestone in milestone_entries.items():
        if milestone.get("delivery_state") != "implemented":
            continue
        milestone_stories = [
            item
            for item in story_entries.values()
            if item.get("milestone_id") == milestone_id
        ]
        if any(
            item.get("delivery_state") != "implemented" for item in milestone_stories
        ):
            reject(f"implemented milestone has an incomplete Story: {milestone_id}")

    roadmap_value = status.get("roadmap")
    roadmap_path = _safe_repository_path(repository_root, roadmap_value)
    if (
        roadmap_path is None
        or not isinstance(roadmap_value, str)
        or roadmap_path.suffix != ".md"
        or not roadmap_path.is_file()
    ):
        reject("roadmap path is invalid")
    else:
        headings = V1_ROADMAP_HEADING.findall(roadmap_path.read_text(encoding="utf-8"))
        heading_ids = [item[0] for item in headings]
        expected_ids = [item["id"] for item in backlog_milestones_raw]
        if heading_ids != expected_ids:
            reject("roadmap milestone IDs differ from the import backlog")
    return violations


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    return unquote(target).split("#", maxsplit=1)[0]


def enumerate_repository_markdown(repository_root: Path) -> list[Path]:
    return sorted(
        path
        for path in repository_root.rglob("*.md")
        if path.is_file()
        and EXCLUDED_MARKDOWN_DIRECTORY_NAMES.isdisjoint(
            path.relative_to(repository_root).parts
        )
    )


def check_repository(repository_root: Path) -> list[str]:
    violations: list[str] = []
    requirement_text = "\n".join(
        (repository_root / path).read_text(encoding="utf-8")
        for path in (
            "docs/product/requirements.md",
            "docs/product/v1-acceptance-criteria.md",
        )
    )
    known_requirements = set(REQUIREMENT_ID.findall(requirement_text))
    with (repository_root / "docs/plans/contract-baseline.toml").open("rb") as stream:
        contract_raw = tomllib.load(stream)
    known_contracts = {item["id"] for item in contract_raw["contracts"]}

    for document in enumerate_repository_markdown(repository_root):
        relative = document.relative_to(repository_root)
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = _link_target(raw_target)
            if not target or target.startswith(EXTERNAL_SCHEMES):
                continue
            if target.startswith("/"):
                violations.append(
                    f"{relative}: repository document uses absolute link {target}"
                )
                continue
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(repository_root.resolve())
            except ValueError:
                violations.append(f"{relative}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                violations.append(f"{relative}: broken local link: {target}")
        unknown_requirements = sorted(
            set(REQUIREMENT_ID.findall(text)) - known_requirements
        )
        if unknown_requirements:
            violations.append(
                f"{relative}: unknown requirement IDs: "
                f"{', '.join(unknown_requirements)}"
            )
        unknown_contracts = sorted(set(CONTRACT_ID.findall(text)) - known_contracts)
        if unknown_contracts:
            violations.append(
                f"{relative}: unknown contract IDs: {', '.join(unknown_contracts)}"
            )
    violations.extend(check_m3_acceptance_status(repository_root))
    violations.extend(check_v1_implementation_status(repository_root))
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    violations = check_repository(root)
    if violations:
        print(f"DOCUMENTATION CHECK: FAILED ({len(violations)} violation(s))")
        for violation in violations:
            print(f"- {violation}")
        return 1
    markdown_count = len(enumerate_repository_markdown(root))
    print(f"DOCUMENTATION CHECK: PASSED ({markdown_count} Markdown files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
