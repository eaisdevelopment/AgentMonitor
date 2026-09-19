"""Repository-level tests for the AgentMonitor planning completion gate.

These tests intentionally inspect the real checkout. They do not construct a fake
repository or replace filesystem behavior.
"""

from __future__ import annotations

import sys
import hashlib
import re
import tomllib
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_plans import (  # noqa: E402  # imported after real-root discovery
    load_catalog,
    validate_event_topology,
    validate_plan_snapshot,
    validate_requirement_ownership,
    validate_scenario_references,
    validate_repository,
)
from render_snapshot import render_snapshot  # noqa: E402


class PlanningCompletionGateTests(unittest.TestCase):
    def test_catalog_declares_every_required_v1_planning_workstream(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)

        self.assertEqual(20, len(catalog.plans))
        self.assertEqual(
            "tools/automation/routines.toml", catalog.automation_catalog_path
        )
        self.assertEqual(
            "docs/plans/configuration-baseline.toml",
            catalog.configuration_baseline_path,
        )
        self.assertEqual(
            "docs/plans/integration/cs1-final-readiness-audit.md",
            catalog.readiness_audit_path,
        )
        self.assertEqual(
            "docs/plans/discovery/m0-g0-approval.toml",
            catalog.m0_g0_approval_path,
        )
        self.assertEqual(
            {
                "PLAN-M0-DISCOVERY",
                "PLAN-FND",
                "PLAN-M01",
                "PLAN-M02",
                "PLAN-M03",
                "PLAN-M04",
                "PLAN-M05",
                "PLAN-M06",
                "PLAN-M07",
                "PLAN-M08",
                "PLAN-A01",
                "PLAN-A02",
                "PLAN-A03",
                "PLAN-A04-LINUX",
                "PLAN-A04-MAC",
                "PLAN-P01",
                "PLAN-P02",
                "PLAN-DB",
                "PLAN-DEP",
                "PLAN-INT",
            },
            {plan.plan_id for plan in catalog.plans},
        )

    def test_real_repository_has_a_complete_synchronized_plan_set(self) -> None:
        violations = validate_repository(REPOSITORY_ROOT, stage="synchronized")

        self.assertEqual([], violations, "\n".join(violations))

    def test_real_requirement_manifest_has_exact_resolvable_ownership(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)

        violations = validate_requirement_ownership(REPOSITORY_ROOT, catalog)

        self.assertEqual([], violations, "\n".join(violations))

    def test_event_delivery_topology_is_exact_and_module_owned(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)

        violations = validate_event_topology(REPOSITORY_ROOT, catalog)

        self.assertEqual([], violations, "\n".join(violations))

    def test_real_plan_snapshot_matches_every_catalog_artifact(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)

        violations = validate_plan_snapshot(REPOSITORY_ROOT, catalog)

        self.assertEqual([], violations, "\n".join(violations))

    def test_all_exact_plan_scenario_references_resolve(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)

        violations = validate_scenario_references(REPOSITORY_ROOT, catalog)

        self.assertEqual([], violations, "\n".join(violations))

    def test_snapshot_renderer_uses_the_real_catalog_and_controls(self) -> None:
        rendered = tomllib.loads(render_snapshot(REPOSITORY_ROOT))

        self.assertEqual(20, rendered["plan_count"])
        self.assertEqual(9, rendered["control_count"])
        self.assertEqual(
            {plan.plan_id for plan in load_catalog(REPOSITORY_ROOT).plans},
            {plan["id"] for plan in rendered["plans"]},
        )

    def test_exact_contract_adoption_is_bound_for_all_twenty_plans(self) -> None:
        adoption_path = REPOSITORY_ROOT / "docs/plans/contract-adoption.toml"

        self.assertTrue(adoption_path.is_file(), "contract adoption manifest is absent")
        adoption = tomllib.loads(adoption_path.read_text(encoding="utf-8"))
        baseline_path = REPOSITORY_ROOT / "docs/plans/contract-baseline.toml"
        baseline = tomllib.loads(baseline_path.read_text(encoding="utf-8"))
        expected_digest = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
        catalog = load_catalog(REPOSITORY_ROOT)

        self.assertEqual(expected_digest, adoption["contract_baseline_sha256"])
        self.assertEqual(20, adoption["plan_count"])
        self.assertEqual(
            {plan.plan_id for plan in catalog.plans},
            {record["id"] for record in adoption["plans"]},
        )
        for record in adoption["plans"]:
            catalog_plan = next(
                plan for plan in catalog.plans if plan.plan_id == record["id"]
            )
            self.assertEqual(catalog_plan.path, record["plan_path"])
            self.assertEqual(
                hashlib.sha256(
                    (REPOSITORY_ROOT / catalog_plan.path).read_bytes()
                ).hexdigest(),
                record["plan_sha256"],
            )
            expected_publishes = {
                contract["id"]
                for contract in baseline["contracts"]
                if contract["producer"] == record["id"]
            }
            expected_consumes = {
                contract["id"]
                for contract in baseline["contracts"]
                if record["id"] in contract["consumers"]
            }
            self.assertEqual(expected_publishes, set(record["publishes"]))
            self.assertEqual(expected_consumes, set(record["consumes"]))

    def test_parallel_units_have_complete_collision_checked_write_sets(self) -> None:
        ownership = tomllib.loads(
            (REPOSITORY_ROOT / "docs/plans/parallel-ownership.toml").read_text(
                encoding="utf-8"
            )
        )
        catalog = load_catalog(REPOSITORY_ROOT)
        plan_by_id = {plan.plan_id: plan for plan in catalog.plans}
        seen: dict[str, str] = {}
        for unit in ownership["units"]:
            plan = plan_by_id[unit["id"]]
            plan_path = REPOSITORY_ROOT / plan.path
            self.assertEqual(
                hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                unit.get("plan_sha256"),
                f"{unit['id']} write set is not bound to its current plan",
            )
            paths = unit.get("write_paths", [])
            self.assertTrue(paths, f"{unit['id']} has no canonical write set")
            self.assertTrue(
                any(path.startswith("docs/") for path in paths),
                f"{unit['id']} write set omits documentation",
            )
            if plan.kind != "discovery":
                self.assertTrue(
                    any("/tests/" in path or path.startswith("backend/tests/") for path in paths),
                    f"{unit['id']} write set omits tests",
                )
            for root in paths:
                normalized = root.removesuffix("/**").rstrip("/")
                self.assertNotIn(" ", normalized)
                for previous, owner in seen.items():
                    if owner == unit["id"]:
                        continue
                    self.assertFalse(
                        normalized == previous
                        or normalized.startswith(previous + "/")
                        or previous.startswith(normalized + "/"),
                        f"write-set collision: {owner} and {unit['id']}",
                    )
                seen[normalized] = unit["id"]

        shared_seen: dict[str, str] = {}
        for writer in ownership["shared_writers"]:
            paths = writer.get("paths", [])
            self.assertTrue(paths, f"{writer['artifact']} has no exact paths")
            for path in paths:
                normalized = path.removesuffix("/**").rstrip("/")
                self.assertNotIn(" ", normalized)
                for unit_root, owner in seen.items():
                    self.assertFalse(
                        normalized == unit_root
                        or normalized.startswith(unit_root + "/")
                        or unit_root.startswith(normalized + "/"),
                        f"shared/unit root collision: {writer['artifact']} and {owner}",
                    )
                for previous, artifact in shared_seen.items():
                    self.assertFalse(
                        normalized == previous
                        or normalized.startswith(previous + "/")
                        or previous.startswith(normalized + "/"),
                        f"shared root collision: {artifact} and {writer['artifact']}",
                    )
                shared_seen[normalized] = writer["artifact"]

        allocated_paths = tuple(seen) + tuple(shared_seen)
        literal_contract_paths: set[str] = set()
        for plan in catalog.plans:
            text = (REPOSITORY_ROOT / plan.path).read_text(encoding="utf-8")
            literal_contract_paths.update(
                path
                for path in re.findall(
                    r"backend/src/agentmonitor/contracts/[a-z0-9_/]+\.py", text
                )
                if "<" not in path
            )
        uncovered = sorted(
            path
            for path in literal_contract_paths
            if not any(
                path == root or path.startswith(root + "/")
                for root in allocated_paths
            )
        )
        self.assertEqual([], uncovered, "public contract files lack a writer")

    def test_draft_plans_do_not_claim_contract_approval_or_synchronization(self) -> None:
        catalog = load_catalog(REPOSITORY_ROOT)
        stale_claim = re.compile(
            r"^\|[^\n|]+\|[^\n|]*(?:approved|synchronized) v1(?:\s+query)?\s*\|",
            re.IGNORECASE | re.MULTILINE,
        )

        violations = []
        for plan in catalog.plans:
            text = (REPOSITORY_ROOT / plan.path).read_text(encoding="utf-8")
            if stale_claim.search(text):
                violations.append(plan.plan_id)

        self.assertEqual([], violations)

    def test_planning_entry_points_describe_the_current_twenty_plan_state(self) -> None:
        program = (
            REPOSITORY_ROOT / "docs/plans/integration/v1-planning-program.md"
        ).read_text(encoding="utf-8")
        registry = (REPOSITORY_ROOT / "docs/plans/README.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("20 synchronized Draft planning artifacts", program)
        self.assertNotIn("The immediate planning wave contains", program)
        self.assertNotIn("Detailed P0 plan drafts: in preparation", program)
        self.assertNotIn("every remaining module/adapter/boundary plan", registry)

    def test_review_records_bind_the_exact_plan_snapshot(self) -> None:
        snapshot_path = REPOSITORY_ROOT / "docs/plans/plan-baseline.toml"
        digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        binding = f"Plan snapshot SHA-256: `{digest}`"

        for relative_path in (
            "docs/plans/integration/cs1-final-readiness-audit.md",
            "docs/plans/integration/cs1-full-plan-synchronization.md",
        ):
            with self.subTest(path=relative_path):
                text = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn(binding, text)


if __name__ == "__main__":
    unittest.main()
