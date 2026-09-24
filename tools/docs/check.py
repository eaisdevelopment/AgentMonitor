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
M3_REQUIRED_CRITERIA = frozenset(
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
M3_STATUSES = frozenset(
    {"passed", "failed", "blocked", "not_run", "deviation_accepted"}
)
M3_COMMAND_STATUSES = frozenset({"passed", "failed", "blocked", "not_run"})
M3_RECORD_KEYS = frozenset(
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
M3_STATUS_MARKER = re.compile(
    r"<!-- agentmonitor-milestone-status:v1 "
    r"milestone=(?P<milestone>\S+) "
    r"lifecycle=(?P<lifecycle>active|superseded) "
    r"status=(?P<status>passed|failed|blocked|not_run|deviation_accepted) "
    r"authority=(?P<authority>[A-Za-z0-9._-]+) -->"
)
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


def _validate_m3_record(
    repository_root: Path, relative: Path, record: dict[str, object]
) -> list[str]:
    violations: list[str] = []

    def reject(code: str) -> None:
        violations.append(f"{relative}: {code}")

    if set(record) != M3_RECORD_KEYS:
        reject("acceptance record keys do not match V1 schema")
    if record.get("schema_version") != "1.0.0":
        reject("acceptance record schema_version must be 1.0.0")
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
    if set(criterion_ids) != M3_REQUIRED_CRITERIA:
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
