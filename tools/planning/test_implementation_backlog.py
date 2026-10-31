"""Contract test for the Superpowers implementation-planning backlog.

The test reads the real checkout. It prevents a planning handoff from being
reported complete when a milestone plan, Epic, or Story is absent, duplicated,
or detached from its authoritative implementation plan.
"""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKLOG_PATH = REPOSITORY_ROOT / "docs/superpowers/plans/implementation-backlog.toml"
EXPECTED_MILESTONES = {f"V1-M{number}" for number in range(1, 9)}
EXPECTED_EPICS = {
    "EPIC-FND-01",
    "EPIC-CONTRACT-01",
    "EPIC-DATA-01",
    "EPIC-IAM-01",
    "EPIC-API-01",
    "EPIC-UI-01",
    "EPIC-REG-01",
    "EPIC-PROV-01",
    "EPIC-CLA-01",
    "EPIC-OBS-01",
    "EPIC-FLEET-01",
    "EPIC-ALERT-01",
    "EPIC-OPS-01",
    "EPIC-CDX-01",
    "EPIC-OLL-01",
    "EPIC-BUDGET-01",
    "EPIC-DEP-01",
    "EPIC-HARDEN-01",
    "EPIC-RELEASE-01",
}
PLAN_ID_PATTERN = re.compile(r"^PLAN-(?:M0-DISCOVERY|FND|M\d{2}|A\d{2}(?:-(?:LINUX|MAC))?|P\d{2}|DB|DEP|INT)$")
REQUIREMENT_ID_PATTERN = re.compile(r"\b(?:FR|NFR|AC)-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b")
CONTRACT_ID_PATTERN = re.compile(r"\bCTR-[A-Z]+-\d{3}\b")
STORY_HEADING_PATTERN = re.compile(
    r"^### Task \d+:\s+`?(ST-[A-Z0-9]+-\d{3})`?\s+—\s+(.+)$",
    re.MULTILINE,
)


def _unique_ids(records: list[dict], kind: str) -> set[str]:
    identifiers = [record.get("id") for record in records]
    if None in identifiers:
        raise AssertionError(f"{kind} record has no id")
    if len(identifiers) != len(set(identifiers)):
        raise AssertionError(f"duplicate {kind} id")
    return set(identifiers)


def _path_matches(relative_path: str, allocation: str) -> bool:
    """Match the ownership manifest's exact paths and trailing /** roots."""
    if allocation.endswith("/**"):
        root = allocation[:-3].rstrip("/")
        return relative_path == root or relative_path.startswith(f"{root}/")
    return relative_path == allocation


class ImplementationBacklogContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not BACKLOG_PATH.is_file():
            raise AssertionError(
                f"implementation backlog is absent: {BACKLOG_PATH.relative_to(REPOSITORY_ROOT)}"
            )
        cls.backlog = tomllib.loads(BACKLOG_PATH.read_text(encoding="utf-8"))

    def test_backlog_has_exact_traceable_hierarchy(self) -> None:
        planning_catalog = tomllib.loads(
            (REPOSITORY_ROOT / "docs/plans/planning-catalog.toml").read_text(encoding="utf-8")
        )
        known_plan_ids = {plan["id"] for plan in planning_catalog["plans"]}
        self.assertEqual("1.0", self.backlog["schema_version"])
        self.assertEqual("planned_import_ready", self.backlog["status"])
        self.assertFalse(self.backlog["gitlab_objects_created"])
        self.assertFalse(self.backlog["implementation_authorized"])

        milestones = self.backlog["milestones"]
        epics = self.backlog["epics"]
        stories = self.backlog["stories"]
        milestone_ids = _unique_ids(milestones, "milestone")
        epic_ids = _unique_ids(epics, "epic")
        story_ids = _unique_ids(stories, "story")

        self.assertEqual(EXPECTED_MILESTONES, milestone_ids)
        self.assertEqual(EXPECTED_EPICS, epic_ids)
        self.assertTrue(story_ids)
        for milestone in milestones:
            for dependency in milestone["depends_on"]:
                self.assertIn(dependency, milestone_ids)
                self.assertNotEqual(milestone["id"], dependency)
        epic_milestones = {epic["id"]: epic["milestone_id"] for epic in epics}
        for epic in epics:
            self.assertIn(epic["milestone_id"], milestone_ids)
            self.assertTrue(epic["title"])
        for story in stories:
            self.assertIn(story["milestone_id"], milestone_ids)
            self.assertIn(story["epic_id"], epic_ids)
            self.assertEqual(story["milestone_id"], epic_milestones[story["epic_id"]])
            self.assertEqual("Planned", story["status"])
            self.assertTrue(story["title"])
            self.assertTrue(story["plan_ids"])
            self.assertTrue(all(PLAN_ID_PATTERN.fullmatch(value) for value in story["plan_ids"]))
            self.assertTrue(set(story["plan_ids"]).issubset(known_plan_ids))
            for dependency in story["depends_on"]:
                self.assertIn(dependency, story_ids | milestone_ids)
                self.assertNotEqual(story["id"], dependency)

    def test_every_story_matches_one_real_milestone_plan_heading(self) -> None:
        contract_baseline = tomllib.loads(
            (REPOSITORY_ROOT / "docs/plans/contract-baseline.toml").read_text(encoding="utf-8")
        )
        requirement_ownership = tomllib.loads(
            (REPOSITORY_ROOT / "docs/plans/requirement-ownership.toml").read_text(
                encoding="utf-8"
            )
        )
        known_contract_ids = {contract["id"] for contract in contract_baseline["contracts"]}
        known_requirement_ids = {
            requirement["requirement_id"] for requirement in requirement_ownership["requirements"]
        }
        registered = {story["id"]: story for story in self.backlog["stories"]}
        discovered: dict[str, tuple[str, str]] = {}

        for milestone in self.backlog["milestones"]:
            plan_path = REPOSITORY_ROOT / milestone["plan_path"]
            self.assertTrue(plan_path.is_file(), milestone["plan_path"])
            plan_text = plan_path.read_text(encoding="utf-8")
            matches = list(STORY_HEADING_PATTERN.finditer(plan_text))
            for index, match in enumerate(matches):
                story_id, title = match.groups()
                self.assertNotIn(story_id, discovered, f"duplicate plan heading {story_id}")
                discovered[story_id] = (title, milestone["id"])
                block_end = matches[index + 1].start() if index + 1 < len(matches) else len(plan_text)
                story_block = plan_text[match.start():block_end]
                epic_match = re.search(
                    r"^\*\*Epic:\*\*\s+`?(EPIC-[A-Z0-9]+-\d{2})`?",
                    story_block,
                    re.MULTILINE,
                )
                if epic_match is None:
                    section_epics = re.findall(
                        r"^## (EPIC-[A-Z0-9]+-\d{2})\s+—",
                        plan_text[: match.start()],
                        re.MULTILINE,
                    )
                    self.assertTrue(section_epics, f"{story_id} has no Epic declaration")
                    declared_epic = section_epics[-1]
                else:
                    declared_epic = epic_match.group(1)
                self.assertEqual(
                    registered[story_id]["epic_id"],
                    declared_epic,
                    f"{story_id} Epic differs between plan and backlog",
                )
                self.assertIsNotNone(
                    REQUIREMENT_ID_PATTERN.search(story_block),
                    f"{story_id} has no requirement or acceptance ID",
                )
                self.assertIsNotNone(
                    CONTRACT_ID_PATTERN.search(story_block),
                    f"{story_id} has no contract ID",
                )
                self.assertTrue(
                    set(CONTRACT_ID_PATTERN.findall(story_block)).issubset(known_contract_ids),
                    f"{story_id} cites an unknown contract ID",
                )
                self.assertTrue(
                    set(REQUIREMENT_ID_PATTERN.findall(story_block)).issubset(
                        known_requirement_ids
                    ),
                    f"{story_id} cites an unknown requirement or acceptance ID",
                )
                for required_section in ("**Files:**", "**Interfaces:**"):
                    self.assertIn(required_section, story_block, f"{story_id} lacks {required_section}")
                self.assertGreaterEqual(
                    len(re.findall(r"^- \[ \] \*\*Step \d+:", story_block, re.MULTILINE)),
                    4,
                    f"{story_id} is not decomposed into executable steps",
                )
                self.assertRegex(story_block, r"\bRed\b", f"{story_id} has no Red evidence step")
                self.assertRegex(story_block, r"\bGreen\b", f"{story_id} has no Green evidence step")
                self.assertIn("git commit -m", story_block, f"{story_id} has no commit boundary")
                executable_blocks = re.findall(
                    r"```(?:python|typescript|bash)\n(.*?)```",
                    story_block,
                    re.DOTALL,
                )
                self.assertTrue(
                    any(
                        re.search(r"\bdef test|\btest\(|\bpytest\b|\bAUTO-[A-Z0-9-]+\b", block)
                        for block in executable_blocks
                    ),
                    f"{story_id} has no concrete test or gate body",
                )
                self.assertIsNone(
                    re.search(
                        r"(?:def test[^\n]*:|\) -> None:)\s*(?:\.\.\.|pass)\s*$",
                        story_block,
                        re.MULTILINE,
                    ),
                    f"{story_id} presents an empty test body",
                )
                if "backend/src/agentmonitor/composition/" in story_block:
                    self.assertIn(
                        "PLAN-FND",
                        registered[story_id]["plan_ids"],
                        f"{story_id} changes the shared composition root without its steward",
                    )
                if re.search(r"\bregenerat(?:e|es|ed|ing)\b", story_block, re.IGNORECASE):
                    self.assertIn(
                        "contracts/openapi/agentmonitor-v1.json",
                        story_block,
                        f"{story_id} regenerates OpenAPI without declaring its artifact",
                    )
                    self.assertIn(
                        "frontend/src/generated/api/index.ts",
                        story_block,
                        f"{story_id} regenerates the client without declaring its artifact",
                    )

        self.assertEqual(set(discovered), set(registered))
        for story_id, (title, milestone_id) in discovered.items():
            self.assertEqual(title, registered[story_id]["title"])
            self.assertEqual(milestone_id, registered[story_id]["milestone_id"])

    def test_every_referenced_automation_command_is_cataloged(self) -> None:
        routine_catalog = tomllib.loads(
            (REPOSITORY_ROOT / "tools/automation/routines.toml").read_text(encoding="utf-8")
        )
        known_routine_ids = {routine["id"] for routine in routine_catalog["routines"]}
        unknown: dict[str, list[str]] = {}
        for milestone in self.backlog["milestones"]:
            plan_path = REPOSITORY_ROOT / milestone["plan_path"]
            referenced = set(
                re.findall(
                    r"tools/automation/run\.py\s+(AUTO-[A-Z0-9-]+)",
                    plan_path.read_text(encoding="utf-8"),
                )
            )
            missing = sorted(referenced - known_routine_ids)
            if missing:
                unknown[milestone["id"]] = missing
        self.assertEqual({}, unknown)

    def test_planned_file_lifecycle_and_migration_chain_are_consistent(self) -> None:
        planned_files: set[str] = set()
        revisions: list[int] = []
        expected_revisions = {
            0,
            100,
            200,
            201,
            202,
            203,
            204,
            300,
            400,
            500,
            501,
            502,
            503,
            504,
            600,
            601,
            602,
            603,
            700,
            701,
            702,
            800,
            801,
            802,
            803,
            804,
        }
        declaration = re.compile(r"^- (Create|Modify|Generate): `([^`]+)`$", re.MULTILINE)
        migration = re.compile(
            r"^backend/migrations/versions/v1_(\d{4})_[a-z0-9_]+\.py$"
        )

        for milestone in self.backlog["milestones"]:
            plan_path = REPOSITORY_ROOT / milestone["plan_path"]
            for verb, relative_path in declaration.findall(
                plan_path.read_text(encoding="utf-8")
            ):
                if verb == "Create":
                    self.assertFalse(
                        relative_path in planned_files,
                        f"{milestone['id']} re-creates {relative_path}",
                    )
                    planned_files.add(relative_path)
                    if relative_path.startswith("backend/migrations/versions/"):
                        match = migration.fullmatch(relative_path)
                        self.assertIsNotNone(
                            match,
                            f"invalid versioned migration filename: {relative_path}",
                        )
                        revisions.append(int(match.group(1)))
                elif verb == "Generate":
                    planned_files.add(relative_path)
                else:
                    real_path = REPOSITORY_ROOT / relative_path
                    self.assertTrue(
                        real_path.exists() or relative_path in planned_files,
                        f"{milestone['id']} modifies {relative_path} before it exists",
                    )

        self.assertEqual(expected_revisions, set(revisions))
        self.assertEqual(len(revisions), len(set(revisions)), "duplicate migration revision")
        self.assertEqual(sorted(revisions), revisions, "migration chain is planned out of order")

    def test_every_planned_file_has_an_allocated_story_owner(self) -> None:
        ownership = tomllib.loads(
            (REPOSITORY_ROOT / "docs/plans/parallel-ownership.toml").read_text(
                encoding="utf-8"
            )
        )
        unit_paths = {
            unit["id"]: unit["write_paths"] for unit in ownership["units"]
        }
        shared_requirements = {
            "root backend/frontend dependency manifests and lockfiles": {"PLAN-FND"},
            "composition root and module/router registration": {"PLAN-FND"},
            "central contract index and contract baseline": set(),
            "central contract-test registration": set(),
            "provider extension contracts under backend/src/agentmonitor/contracts/providers/**": {
                "PLAN-M03"
            },
            "configuration registry": set(),
            "migration catalog, head, and Alembic environment": {"PLAN-DB"},
            "CTR-EVT registry, dispatcher composition, and event-storage port registration": {
                "PLAN-INT"
            },
            "OpenAPI source and compatibility baseline": {"PLAN-P01"},
            "generated TypeScript client": {"PLAN-P01"},
            "frontend shell, route map, and design tokens": {"PLAN-P02"},
            "build/version manifest, SBOM, and notices": {"PLAN-INT"},
            "canonical command/automation registry": {"PLAN-FND"},
            "root repository and frontend build metadata": {"PLAN-FND"},
            "CI configuration": {"PLAN-FND"},
            "planning registry, traceability, risks, ADR index, and approval records": set(),
        }
        shared_paths = [
            (
                shared["artifact"],
                path,
                shared_requirements[shared["artifact"]],
            )
            for shared in ownership["shared_writers"]
            for path in shared["paths"]
        ]
        stories = {story["id"]: story for story in self.backlog["stories"]}
        declaration = re.compile(
            r"^- (?:Create|Modify|Generate|Regenerate|Test): `([^`]+)`$",
            re.MULTILINE,
        )

        for milestone in self.backlog["milestones"]:
            plan_text = (REPOSITORY_ROOT / milestone["plan_path"]).read_text(
                encoding="utf-8"
            )
            headings = list(STORY_HEADING_PATTERN.finditer(plan_text))
            for index, heading in enumerate(headings):
                story_id = heading.group(1)
                end = headings[index + 1].start() if index + 1 < len(headings) else len(plan_text)
                story_block = plan_text[heading.start():end]
                plan_ids = set(stories[story_id]["plan_ids"])
                files_section = re.search(
                    r"^\*\*Files:\*\*\s*$(.*?)(?=^\*\*Interfaces:\*\*)",
                    story_block,
                    re.MULTILINE | re.DOTALL,
                )
                self.assertIsNotNone(files_section, f"{story_id} has no parseable Files section")
                file_lines = [
                    line
                    for line in files_section.group(1).splitlines()
                    if line.startswith("- ")
                ]
                self.assertTrue(file_lines, f"{story_id} has an empty Files section")
                for line in file_lines:
                    self.assertRegex(
                        line,
                        r"^- (?:Create|Modify|Generate|Regenerate|Test): `[^`]+`$",
                        f"{story_id} has an unrecognized Files directive: {line}",
                    )
                owned = [
                    allocation
                    for plan_id in plan_ids
                    for allocation in unit_paths[plan_id]
                ]
                for relative_path in declaration.findall(story_block):
                    if any(_path_matches(relative_path, path) for path in owned):
                        continue
                    matching_shared = [
                        (artifact, required)
                        for artifact, path, required in shared_paths
                        if _path_matches(relative_path, path)
                    ]
                    self.assertTrue(
                        matching_shared,
                        f"{story_id} declares unallocated path {relative_path}",
                    )
                    self.assertTrue(
                        any(required.issubset(plan_ids) for _, required in matching_shared),
                        f"{story_id} lacks the semantic owner for shared path {relative_path}",
                    )


if __name__ == "__main__":
    unittest.main()
