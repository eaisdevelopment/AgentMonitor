"""Validate M6 planning traceability, without claiming delivery readiness."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/plans/integration/m6-ticket-catalog-v1.json"
REQUIREMENTS = ROOT / "docs/product/requirements.md"
ACCEPTANCE = ROOT / "docs/product/v1-acceptance-criteria.md"
STORIES = ROOT / "docs/superpowers/plans/implementation-backlog.toml"
PLAN = ROOT / "docs/plans/integration/m6-execution-plan-2026-10-31.md"
ID = re.compile(r"M6-T\d{3}\Z")


def validate_status_dependencies(tickets: dict[str, dict]) -> list[str]:
    """Do not let a completed ticket conceal unfinished prerequisites."""
    errors: list[str] = []
    for key, ticket in tickets.items():
        if ticket.get("status") != "done":
            continue
        if any(
            dep in tickets and tickets[dep].get("status") != "done"
            for dep in ticket.get("depends_on", [])
        ):
            errors.append(f"{key}: completed_dependency_not_done")
    return errors


def complete_stage_reasons(tickets: list[dict]) -> tuple[str, ...]:
    """Report whether the ticket ledger is complete without claiming M6 passed."""

    if any(
        not isinstance(ticket, dict)
        or ticket.get("status") != "done"
        or not ticket.get("evidence")
        for ticket in tickets
    ):
        return ("m6_tickets_not_complete",)
    return ()


def validate(catalog: object) -> list[str]:
    """Check identity, links, coverage and dependency graph of the fixed catalog."""
    errors: list[str] = []
    if (
        not isinstance(catalog, dict)
        or catalog.get("schema_version") != "1.0"
        or catalog.get("milestone") != "V1-M6"
    ):
        return ["catalog_header_invalid"]
    tickets = catalog.get("tickets")
    if not isinstance(tickets, list) or not tickets:
        return ["tickets_missing"]
    stories = set(re.findall(r"ST-OLL-\d{3}", STORIES.read_text()))
    requirements = set(
        re.findall(r"\b(?:FR|NFR)-[A-Z]+-\d{3}\b", REQUIREMENTS.read_text())
    )
    criteria = set(re.findall(r"\bAC-[A-Z0-9]+-\d{3}\b", ACCEPTANCE.read_text()))
    local_criteria = set(re.findall(r"\bM6-A\d{2}\b", PLAN.read_text()))
    by_id: dict[str, dict] = {}
    covered_stories: set[str] = set()
    covered_m6: set[str] = set()
    for ticket in tickets:
        if not isinstance(ticket, dict):
            errors.append("ticket_invalid")
            continue
        key = ticket.get("id")
        if not isinstance(key, str) or ID.fullmatch(key) is None or key in by_id:
            errors.append("ticket_id_invalid_or_duplicate")
            continue
        by_id[key] = ticket
        story = ticket.get("story")
        if story not in stories:
            errors.append(f"{key}: unknown_story")
        else:
            covered_stories.add(story)
        if ticket.get("status") not in {"planned", "in_progress", "blocked", "done"}:
            errors.append(f"{key}: invalid_status")
        for field, allowed in (
            ("requirements", requirements),
            ("acceptance_criteria", criteria),
            ("m6_acceptance", local_criteria),
        ):
            values = ticket.get(field)
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(x, str) and x in allowed for x in values)
            ):
                errors.append(f"{key}: invalid_{field}")
            elif field == "m6_acceptance":
                covered_m6.update(values)
        for field in ("title", "owner", "work", "done_when"):
            if not isinstance(ticket.get(field), str) or not ticket[field].strip():
                errors.append(f"{key}: missing_{field}")
        for field in ("depends_on", "verification", "evidence"):
            value = ticket.get(field)
            if not isinstance(value, list) or not all(
                isinstance(x, str) and x for x in value
            ):
                errors.append(f"{key}: invalid_{field}")
        estimate = ticket.get("estimate_hours")
        if (
            not isinstance(estimate, dict)
            or type(estimate.get("min")) is not int
            or type(estimate.get("max")) is not int
            or not 0 < estimate["min"] <= estimate["max"]
        ):
            errors.append(f"{key}: invalid_estimate")
        if ticket.get("status") == "done" and not ticket.get("evidence"):
            errors.append(f"{key}: done_without_evidence")
    for key, ticket in by_id.items():
        for dep in ticket.get("depends_on", []):
            if dep not in by_id or dep == key:
                errors.append(f"{key}: invalid_dependency")
    errors.extend(validate_status_dependencies(by_id))
    active: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in active:
            errors.append(f"{key}: dependency_cycle")
            return
        if key in visited:
            return
        active.add(key)
        for dep in by_id[key].get("depends_on", []):
            if dep in by_id:
                visit(dep)
        active.remove(key)
        visited.add(key)

    for key in by_id:
        visit(key)
    if covered_stories != set(catalog.get("story_ids", [])) or covered_stories != {
        f"ST-OLL-{i:03}" for i in range(1, 6)
    }:
        errors.append("story_coverage_incomplete")
    if covered_m6 != set(catalog.get("acceptance_ids", [])) or covered_m6 != {
        f"M6-A{i:02}" for i in range(1, 11)
    }:
        errors.append("m6_acceptance_coverage_incomplete")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("plan", "complete"), default="plan")
    args = parser.parse_args()
    try:
        catalog = json.loads(CATALOG.read_text())
        errors = validate(catalog)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"M6 TICKETS: FAILED — {type(exc).__name__}")
        return 1
    if errors:
        print("M6 TICKETS: FAILED — " + ", ".join(errors))
        return 1
    tickets = catalog["tickets"]
    if args.stage == "complete":
        reasons = complete_stage_reasons(tickets)
        if reasons:
            print(
                "M6 TICKETS: BLOCKED — ticket ledger is not complete; "
                "planning validation is not completion evidence"
            )
            return 3
        print(
            f"M6 TICKETS: PASSED — {len(tickets)} completed tickets have evidence; "
            "AUTO-M6-EXIT remains the milestone authority"
        )
        return 0
    print(
        f"M6 TICKETS: PASSED — {len(tickets)} proposed tickets; "
        "five stories and ten M6 acceptance items traced; "
        "not implementation approval or M6 completion"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
