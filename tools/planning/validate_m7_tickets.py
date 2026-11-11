"""Check the real M7 planning ledger; never certify implementation or acceptance."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/plans/integration/m7-ticket-catalog-v1.json"


def validate() -> list[str]:
    """Resolve traceability and dependencies against this actual checkout."""
    data = json.loads(CATALOG.read_text())
    errors: list[str] = []
    if data.get("schema_version") != "1.0" or data.get("milestone") != "V1-M7":
        return ["invalid_catalog"]
    stories = {f"ST-BUDGET-{i:03}" for i in range(1, 6)}
    acceptance = {f"M7-A{i:02}" for i in range(1, 11)}
    if set(data["story_ids"]) != stories or set(data["acceptance_ids"]) != acceptance:
        errors.append("scope_changed")
    plan = (ROOT / data["plan"]).read_text()
    requirements = (ROOT / "docs/product/requirements.md").read_text()
    criteria = (ROOT / "docs/product/v1-acceptance-criteria.md").read_text()
    backlog = (ROOT / "docs/superpowers/plans/implementation-backlog.toml").read_text()
    tickets = data["tickets"]
    by_id = {item["id"]: item for item in tickets}
    if len(by_id) != len(tickets) or set(by_id) != {
        f"M7-T{i:03}" for i in range(1, 17)
    }:
        errors.append("ticket_inventory_changed")
    covered_stories: set[str] = set()
    covered_acceptance: set[str] = set()
    for key, item in by_id.items():
        if item["story"] not in stories or item["story"] not in backlog:
            errors.append(f"{key}: unknown_story")
        covered_stories.add(item["story"])
        for field in (
            "title",
            "owner",
            "test_ids",
            "deliverable",
            "expected_red",
            "done_when",
            "verification",
        ):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{key}: missing_{field}")
        for field, source in (
            ("requirements", requirements),
            ("acceptance_criteria", criteria),
            ("m7_acceptance", plan),
        ):
            values = item.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"{key}: missing_{field}")
                continue
            for value in values:
                if not isinstance(value, str) or not re.search(
                    r"\b" + re.escape(value) + r"\b", source
                ):
                    errors.append(f"{key}: unknown_{field}")
        covered_acceptance.update(item["m7_acceptance"])
        if item["status"] not in {"planned", "in_progress", "blocked", "done"}:
            errors.append(f"{key}: invalid_status")
        if not isinstance(item["depends_on"], list) or not isinstance(
            item["evidence"], list
        ):
            errors.append(f"{key}: invalid_links")
            continue
        for dependency in item["depends_on"]:
            if dependency not in by_id or dependency == key:
                errors.append(f"{key}: invalid_dependency")
            elif item["status"] == "done" and by_id[dependency]["status"] != "done":
                errors.append(f"{key}: unfinished_dependency")
        if item["status"] == "done" and not item["evidence"]:
            errors.append(f"{key}: missing_completion_evidence")
        for evidence in item["evidence"]:
            path = (ROOT / evidence).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                errors.append(f"{key}: invalid_evidence_path")
    if covered_stories != stories or covered_acceptance != acceptance:
        errors.append("incomplete_coverage")
    active: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in active:
            errors.append(f"{key}: dependency_cycle")
            return
        if key in visited:
            return
        active.add(key)
        for dependency in by_id[key]["depends_on"]:
            if dependency in by_id:
                visit(dependency)
        active.remove(key)
        visited.add(key)

    for key in by_id:
        visit(key)
    if data["owner_approved"]:
        approval = data.get("approval_evidence")
        if not isinstance(approval, str) or not (ROOT / approval).is_file():
            errors.append("approval_evidence_missing")
    return errors


def main() -> int:
    try:
        errors = validate()
    except (OSError, ValueError, TypeError, KeyError):
        print("M7 PLAN: FAILED — malformed or missing planning artifact")
        return 1
    if errors:
        print("M7 PLAN: FAILED — " + ", ".join(errors))
        return 1
    print(
        "M7 PLAN: PASSED — 16 tickets, 5 stories, 10 acceptance items traced; "
        "not implementation approval or M7 completion"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
