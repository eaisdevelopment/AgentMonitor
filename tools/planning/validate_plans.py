"""Executable completion gate for AgentMonitor planning artifacts.

The gate reads the real repository and deliberately has no dependency outside the
Python standard library. It validates documentation completeness; it does not
claim that unexecuted implementation or live-provider behavior has passed.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

MODULE_SECTIONS = tuple(f"## {number}." for number in range(1, 17))
REQUIRED_IMPLEMENTATION_PLAN_TERMS = (
    "Status:",
    "Plan version:",
    "Requirements",
    "contract",
    "Test",
    "Red",
    "Green",
    "security",
    "privacy",
    "rollback",
    "Definition of ready",
    "Approval",
)
REQUIRED_DISCOVERY_PLAN_TERMS = (
    "Status:",
    "Plan version:",
    "Requirements",
    "scenario",
    "evidence",
    "security",
    "privacy",
    "stop",
    "Approval",
)
REQUIRED_AUTOMATION_ROUTINES = (
    "AUTO-PLAN-CHECK",
    "AUTO-M0-G0",
    "AUTO-M0-G1-CONTRACT",
    "AUTO-M0-G1-FINALIZE",
    "AUTO-M0-G1-EXIT",
    "AUTO-M0-PREFLIGHT",
    "AUTO-M0-POSTFLIGHT",
    "AUTO-M0-LEDGER",
    "AUTO-DOCS-CHECK",
    "AUTO-M3-TEST",
    "AUTO-M3-LIVE",
    "AUTO-M3-EXIT",
    "AUTO-M4-EXIT",
    "AUTO-M5-SERVICE-ACTIVATE",
    "AUTO-M5-ARCHIVE-PREREQUISITES",
    "AUTO-M5-OWNER-OUTCOMES",
    "AUTO-M5-QUOTA-WITNESS",
    "AUTO-M5-ALERT-WITNESS",
    "AUTO-M5-EXIT",
    "AUTO-M6-LOCAL-ACTIVATE",
    "AUTO-M6-LOCAL-ADMIT",
    "AUTO-M6-LOCAL-INVENTORY",
    "AUTO-M6-CUTOVER",
    "AUTO-M6-CURRENT-UPDATE",
    "AUTO-M6-RECOVER-CURRENT-UPDATE",
    "AUTO-M6-RECOVER-MIGRATION",
    "AUTO-M6-RESTORE-PRESTART",
    "AUTO-M6-START-RESTORED",
    "AUTO-M6-FINALIZE-CANDIDATE",
    "AUTO-M6-EXIT",
    "AUTO-M7-PLAN-CHECK",
    "AUTO-M7-TEST",
    "AUTO-M7-LIVE",
    "AUTO-M7-BROWSER",
    "AUTO-M7-DEPLOY",
    "AUTO-M7-EXIT",
    "AUTO-CLAUDE-POLL",
    "AUTO-CLAUDE-MANAGED",
    "AUTO-CLAUDE-CONNECT",
    "AUTO-DASHBOARD-PROVIDER-FILTER",
    "AUTO-LAN-DASHBOARD",
    "AUTO-ACCOUNT-AGENTS",
    "AUTO-MUTATION",
    "AUTO-TEST",
    "AUTO-QUALITY",
    "AUTO-GIT-PREFLIGHT",
    "AUTO-BUILD",
    "AUTO-MIGRATE",
    "AUTO-DEPLOY",
    "AUTO-BACKUP",
    "AUTO-RESTORE",
    "AUTO-RELEASE",
)
REQUIREMENT_ID_PATTERN = re.compile(r"\b(?:FR|NFR|AC)-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b")
SCENARIO_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9-]*-\d{3}$")
CONFIGURATION_KEY_PATTERN = re.compile(r"\bAGENTMONITOR_[A-Z0-9_]+\b")
EVIDENCE_BOUNDARIES = {"T1", "T2", "T3", "T4", "T5", "T6", "T7", "docs"}
STALE_DRAFT_CONTRACT_CLAIM = re.compile(
    r"^\|[^\n|]+\|[^\n|]*(?:approved|synchronized) v1(?:\s+query)?\s*\|",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class PlanSpec:
    plan_id: str
    path: str
    kind: str
    scenario_prefix: str
    minimum_lines: int
    minimum_scenarios: int


@dataclass(frozen=True)
class PlanningCatalog:
    schema_version: str
    required_plan_count: int
    registry_path: str
    synchronization_review_path: str
    readiness_audit_path: str
    automation_standard_path: str
    automation_catalog_path: str
    contract_baseline_path: str
    contract_adoption_path: str
    configuration_baseline_path: str
    requirement_ownership_path: str
    parallel_ownership_path: str
    plan_snapshot_path: str
    m0_g0_approval_path: str
    plans: tuple[PlanSpec, ...]


def load_catalog(repository_root: Path) -> PlanningCatalog:
    catalog_path = repository_root / "docs/plans/planning-catalog.toml"
    with catalog_path.open("rb") as stream:
        raw = tomllib.load(stream)
    plans = tuple(
        PlanSpec(
            plan_id=item["id"],
            path=item["path"],
            kind=item["kind"],
            scenario_prefix=item["scenario_prefix"],
            minimum_lines=item["minimum_lines"],
            minimum_scenarios=item["minimum_scenarios"],
        )
        for item in raw["plans"]
    )
    return PlanningCatalog(
        schema_version=raw["schema_version"],
        required_plan_count=raw["required_plan_count"],
        registry_path=raw["registry_path"],
        synchronization_review_path=raw["synchronization_review_path"],
        readiness_audit_path=raw["readiness_audit_path"],
        automation_standard_path=raw["automation_standard_path"],
        automation_catalog_path=raw["automation_catalog_path"],
        contract_baseline_path=raw["contract_baseline_path"],
        contract_adoption_path=raw["contract_adoption_path"],
        configuration_baseline_path=raw["configuration_baseline_path"],
        requirement_ownership_path=raw["requirement_ownership_path"],
        parallel_ownership_path=raw["parallel_ownership_path"],
        plan_snapshot_path=raw["plan_snapshot_path"],
        m0_g0_approval_path=raw["m0_g0_approval_path"],
        plans=plans,
    )


def _scenario_definitions(text: str, prefix: str) -> tuple[str, ...]:
    identifier = rf"{re.escape(prefix)}[A-Z][A-Z0-9-]*-\d{{3}}"
    table_rows = re.findall(rf"^\|\s*({identifier})\s*\|", text, re.MULTILINE)
    list_rows = re.findall(rf"^-\s+({identifier}):", text, re.MULTILINE)
    dash_rows = re.findall(rf"^-\s+({identifier})\s+[—–-]\s+", text, re.MULTILINE)
    numbered_bold_rows = re.findall(
        rf"^\d+\.\s+\*\*({identifier}):\*\*", text, re.MULTILINE
    )
    return tuple(table_rows + list_rows + dash_rows + numbered_bold_rows)


def _load_toml(path: Path, label: str, violations: list[str]) -> dict:
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except (FileNotFoundError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        violations.append(f"{label} cannot be loaded: {error}")
        return {}


def _validate_contract_baseline(
    repository_root: Path,
    catalog: PlanningCatalog,
    plan_ids: set[str],
    violations: list[str],
) -> None:
    path = repository_root / catalog.contract_baseline_path
    raw = _load_toml(path, "contract baseline", violations)
    if not raw:
        return
    contracts = raw.get("contracts", [])
    contract_ids = [item.get("id") for item in contracts]
    expected_count = raw.get("contract_count")
    if expected_count != 106 or len(contracts) != expected_count:
        violations.append(
            f"contract baseline count mismatch: metadata={expected_count}, "
            f"records={len(contracts)}, expected=106"
        )
    if len(contract_ids) != len(set(contract_ids)):
        violations.append("contract baseline contains duplicate IDs")
    if raw.get("status") != "draft_aligned":
        violations.append("contract baseline status is not draft_aligned")
    if raw.get("owner_approved") is not False:
        violations.append("Draft contract baseline must not claim owner approval")
    if raw.get("implementation_authorized") is not False:
        violations.append("Draft contract baseline must not authorize implementation")

    required_checklist = {
        "field_state_null",
        "units_time",
        "auth",
        "side_effects",
        "idempotency",
        "events",
        "retention",
        "errors",
        "compatibility",
    }
    allowed_maturities = {"proposed_aligned", "evidence_blocked"}
    for item in contracts:
        contract_id = item.get("id", "<missing>")
        if not re.fullmatch(r"CTR-[A-Z]+-\d{3}", str(contract_id)):
            violations.append(f"contract baseline has invalid ID {contract_id!r}")
        expected_version = {
            "CTR-COL-008": "1.2.0",
            "CTR-COL-009": "1.1.0",
            "CTR-COL-010": "2.0.0",
            "CTR-PROV-003": "1.3.0",
            "CTR-REG-012": "1.1.0",
            "CTR-REG-014": "1.2.0",
        }.get(contract_id, "1.0.0")
        if item.get("version") != expected_version:
            violations.append(
                f"{contract_id}: expected proposed version {expected_version}"
            )
        if item.get("producer") not in plan_ids:
            violations.append(f"{contract_id}: invalid semantic producer")
        consumers = item.get("consumers", [])
        if not consumers or any(consumer not in plan_ids for consumer in consumers):
            violations.append(f"{contract_id}: missing or invalid consumers")
        if item.get("maturity") not in allowed_maturities:
            violations.append(f"{contract_id}: invalid Draft maturity")
        if not item.get("decision_reference"):
            violations.append(f"{contract_id}: missing decision reference")
        checklist = item.get("checklist", {})
        if set(checklist) != required_checklist or not all(checklist.values()):
            violations.append(f"{contract_id}: incomplete semantic checklist")

    resolutions = raw.get("resolutions", [])
    resolution_ids = {item.get("id") for item in resolutions}
    required_resolutions = {f"CAA-C{number:02d}" for number in range(1, 18)}
    if resolution_ids != required_resolutions:
        violations.append("contract baseline does not resolve exactly CAA-C01..CAA-C17")
    for item in resolutions:
        if (
            item.get("owner_approved") is not False
            or item.get("implementation_authorized") is not False
        ):
            violations.append(f"{item.get('id')}: resolution overclaims authority")

    referenced_contracts: set[str] = set()
    for plan in catalog.plans:
        plan_path = repository_root / plan.path
        if plan_path.is_file():
            referenced_contracts.update(
                re.findall(
                    r"\bCTR-[A-Z]+-\d{3}\b", plan_path.read_text(encoding="utf-8")
                )
            )
    missing = sorted(referenced_contracts - set(contract_ids))
    if missing:
        violations.append(
            "plan contract references absent from baseline: " + ", ".join(missing)
        )


def validate_contract_adoption(
    repository_root: Path, catalog: PlanningCatalog
) -> list[str]:
    """Bind every plan to its exact producer/consumer set in the baseline."""

    violations: list[str] = []
    baseline_path = repository_root / catalog.contract_baseline_path
    baseline = _load_toml(baseline_path, "contract baseline for adoption", violations)
    adoption = _load_toml(
        repository_root / catalog.contract_adoption_path,
        "contract adoption manifest",
        violations,
    )
    if not baseline or not adoption:
        return violations
    if adoption.get("schema_version") != "1.0":
        violations.append("contract adoption schema is not 1.0")
    if adoption.get("status") != "draft_exact":
        violations.append("contract adoption status is not draft_exact")
    if adoption.get("contract_baseline_version") != baseline.get("baseline_version"):
        violations.append("contract adoption baseline version mismatch")
    if (
        adoption.get("contract_baseline_sha256")
        != hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    ):
        violations.append("contract adoption baseline SHA-256 mismatch")
    if adoption.get("owner_approved") is not False:
        violations.append("contract adoption must not claim owner approval")
    if adoption.get("implementation_authorized") is not False:
        violations.append("contract adoption must not authorize implementation")

    plan_ids = {plan.plan_id for plan in catalog.plans}
    records = adoption.get("plans", [])
    record_ids = [record.get("id") for record in records]
    if adoption.get("plan_count") != len(plan_ids) or set(record_ids) != plan_ids:
        violations.append("contract adoption plans do not match the catalog")
    if len(record_ids) != len(set(record_ids)):
        violations.append("contract adoption contains duplicate plans")
    contracts = baseline.get("contracts", [])
    for record in records:
        plan_id = record.get("id")
        catalog_plan = next(
            (plan for plan in catalog.plans if plan.plan_id == plan_id), None
        )
        if catalog_plan is None:
            continue
        if record.get("plan_path") != catalog_plan.path:
            violations.append(f"{plan_id}: contract adoption plan path mismatch")
        else:
            plan_digest = hashlib.sha256(
                (repository_root / catalog_plan.path).read_bytes()
            ).hexdigest()
            if record.get("plan_sha256") != plan_digest:
                violations.append(f"{plan_id}: contract adoption plan SHA-256 mismatch")
        expected_publishes = sorted(
            contract["id"]
            for contract in contracts
            if contract.get("producer") == plan_id
        )
        expected_consumes = sorted(
            contract["id"]
            for contract in contracts
            if plan_id in contract.get("consumers", [])
        )
        publishes = record.get("publishes", [])
        consumes = record.get("consumes", [])
        if publishes != expected_publishes or len(publishes) != len(set(publishes)):
            violations.append(f"{plan_id}: published contract adoption is not exact")
        if consumes != expected_consumes or len(consumes) != len(set(consumes)):
            violations.append(f"{plan_id}: consumed contract adoption is not exact")
    return violations


def validate_event_topology(
    repository_root: Path, catalog: PlanningCatalog
) -> list[str]:
    """Validate the one CS-1 physical event-delivery topology.

    This is deliberately narrower than contract approval.  It prevents parallel
    implementation lanes from privately choosing a central journal versus
    module-owned transactional tables while the Draft still awaits approval.
    """

    violations: list[str] = []
    raw = _load_toml(
        repository_root / catalog.contract_baseline_path,
        "contract baseline for event topology",
        violations,
    )
    if not raw:
        return violations
    topology = raw.get("event_topology")
    if not isinstance(topology, dict):
        return ["contract baseline lacks [event_topology]"]

    expected_scalars = {
        "id": "CTR-EVT-TOPOLOGY-001",
        "status": "draft_aligned",
        "model": "module_owned_transactional_outboxes",
        "semantic_governor": "PLAN-INT",
        "persistence_mechanism_owner": "PLAN-DB",
        "producer_row_owner": "producing_module",
        "consumer_receipt_owner": "consuming_module",
        "dispatcher_access": "published_module_event_storage_ports_only",
        "central_event_table": False,
        "cross_module_table_access": False,
        "owner_approved": False,
        "implementation_authorized": False,
    }
    expected_fields = {
        *expected_scalars,
        "producer_outbox_tables",
        "producer_delivery_table_rule",
        "consumer_receipt_table_rule",
        "dispatcher_rule",
        "transaction_rule",
        "retention_rule",
    }
    if set(topology) != expected_fields:
        violations.append(
            "event topology fields are not the exact versioned CS-1 schema: "
            f"missing={sorted(expected_fields - set(topology))}, "
            f"extra={sorted(set(topology) - expected_fields)}"
        )
    for field, expected in expected_scalars.items():
        if topology.get(field) != expected:
            violations.append(
                f"event topology {field}={topology.get(field)!r}; expected {expected!r}"
            )

    expected_tables = {
        "PLAN-M02": "reg_event_outbox",
        "PLAN-M03": "provider_system_event_outbox",
        "PLAN-M04": "collection_event_outbox",
        "PLAN-M05": "capacity_event_outbox",
        "PLAN-M06": "runtime_event_outbox",
        "PLAN-M07": "alert_event_outbox",
        "PLAN-M08": "ops_event_outbox",
    }
    table_records = topology.get("producer_outbox_tables", [])
    try:
        actual_tables = {item["plan"]: item["table"] for item in table_records}
    except (KeyError, TypeError):
        actual_tables = {}
        violations.append("event topology producer_outbox_tables are malformed")
    if actual_tables != expected_tables or len(table_records) != len(expected_tables):
        violations.append(
            "event topology does not allocate exactly one producer-owned outbox "
            "table to PLAN-M02..PLAN-M08"
        )

    catalog_by_id = {plan.plan_id: plan for plan in catalog.plans}
    for plan_id, table in expected_tables.items():
        spec = catalog_by_id.get(plan_id)
        if spec is None:
            violations.append(f"event topology references unknown plan {plan_id}")
            continue
        text = (repository_root / spec.path).read_text(encoding="utf-8")
        if "CTR-EVT-TOPOLOGY-001" not in text or table not in text:
            violations.append(
                f"{plan_id}: plan does not adopt CTR-EVT-TOPOLOGY-001 and {table}"
            )

    forbidden_ambiguities = (
        "centrally owned outbox table",
        "shared event journal is selected",
        "conditional m03 event outbox",
        "conditional m02 outbox",
        "conditional `provider_system_outbox_events`",
        "conditional `collection_event_outbox`",
        "conditional `capacity_event_outbox`",
        "conditional `runtime_event_outbox`",
        "conditional `alert_event_outbox`",
        "conditional `ops_outbox_event`",
        "according to the shared outbox decision",
        "exact table ownership may move to common infrastructure",
        "outbox is m08-owned only if",
        "if foundation selects a shared outbox",
    )
    for spec in catalog.plans:
        text = (repository_root / spec.path).read_text(encoding="utf-8").casefold()
        for phrase in forbidden_ambiguities:
            if phrase in text:
                violations.append(
                    f"{spec.plan_id}: event topology remains conditional: {phrase!r}"
                )

    for plan_id in ("PLAN-DB", "PLAN-INT"):
        spec = catalog_by_id[plan_id]
        text = (repository_root / spec.path).read_text(encoding="utf-8")
        if "CTR-EVT-TOPOLOGY-001" not in text:
            violations.append(f"{plan_id}: plan does not adopt CTR-EVT-TOPOLOGY-001")
        missing_tables = sorted(
            table for table in expected_tables.values() if table not in text
        )
        if missing_tables:
            violations.append(
                f"{plan_id}: event topology table allocation is incomplete: "
                + ", ".join(missing_tables)
            )
    return violations


def _validate_parallel_ownership(
    repository_root: Path,
    catalog: PlanningCatalog,
    plan_ids: set[str],
    violations: list[str],
) -> None:
    path = repository_root / catalog.parallel_ownership_path
    raw = _load_toml(path, "parallel ownership manifest", violations)
    if not raw:
        return
    units = raw.get("units", [])
    unit_ids = [item.get("id") for item in units]
    if set(unit_ids) != plan_ids or len(unit_ids) != len(set(unit_ids)):
        violations.append("parallel ownership units do not match the 20-plan catalog")
    catalog_paths = {plan.plan_id: plan.path for plan in catalog.plans}
    dependency_graph: dict[str, list[str]] = {}
    table_prefix_owners: dict[str, str] = {}
    write_roots: dict[str, str] = {}
    catalog_by_id = {plan.plan_id: plan for plan in catalog.plans}
    if raw.get("schema_version") != "1.1":
        violations.append("parallel ownership schema is not 1.1")
    rules = raw.get("rules", {})
    expected_write_rules = {
        "write_paths": "complete nonshared repository write surface for code, tests, documentation, and sanitized evidence",
        "plan_sha256_binding": "any plan-byte change invalidates that unit allocation until reviewed and rebound",
        "unlisted_repository_paths": "locked until added to one exclusive write set or one shared-writer allocation",
    }
    for key, expected in expected_write_rules.items():
        if rules.get(key) != expected:
            violations.append(f"parallel ownership rule {key} is not fail-closed")
    for unit in units:
        unit_id = unit.get("id")
        if catalog_paths.get(unit_id) != unit.get("plan"):
            violations.append(f"{unit_id}: ownership manifest plan path mismatch")
        for field in (
            "plan_sha256",
            "write_paths",
            "contract_families",
            "table_prefixes",
            "migration_slots",
            "configuration_namespace",
            "depends_on",
            "parallel_after_approval",
            "live_boundary",
        ):
            if field not in unit:
                violations.append(f"{unit_id}: ownership manifest missing {field}")
        spec = catalog_by_id.get(str(unit_id))
        if spec is not None:
            plan_path = repository_root / spec.path
            if (
                plan_path.is_file()
                and unit.get("plan_sha256")
                != hashlib.sha256(plan_path.read_bytes()).hexdigest()
            ):
                violations.append(
                    f"{unit_id}: ownership write set is not bound to current plan SHA-256"
                )
        write_paths = unit.get("write_paths", [])
        if not write_paths:
            violations.append(
                f"{unit_id}: ownership manifest has no canonical write set"
            )
        if len(write_paths) != len(set(write_paths)):
            violations.append(f"{unit_id}: canonical write set contains duplicates")
        if not any(str(item).startswith("docs/") for item in write_paths):
            violations.append(f"{unit_id}: canonical write set omits documentation")
        if (
            spec is not None
            and spec.kind != "discovery"
            and not any(
                "/tests/" in str(item) or str(item).startswith("backend/tests/")
                for item in write_paths
            )
        ):
            violations.append(f"{unit_id}: canonical write set omits tests")
        for root in write_paths:
            normalized = str(root).removesuffix("/**").rstrip("/")
            if not normalized or " " in normalized or normalized.startswith("/"):
                violations.append(f"{unit_id}: invalid write path {root!r}")
                continue
            for previous, owner in write_roots.items():
                if owner == unit_id:
                    continue
                if (
                    normalized == previous
                    or normalized.startswith(previous + "/")
                    or previous.startswith(normalized + "/")
                ):
                    violations.append(f"write-set collision: {owner} and {unit_id}")
            write_roots[normalized] = str(unit_id)
        namespace = unit.get("configuration_namespace")
        if namespace != "none" and not str(namespace).startswith("AGENTMONITOR_"):
            violations.append(
                f"{unit_id}: configuration namespace violates AGENTMONITOR_* convention"
            )
        dependencies = unit.get("depends_on", [])
        parallel_units = unit.get("parallel_after_approval", [])
        if any(dependency not in plan_ids for dependency in dependencies):
            violations.append(f"{unit_id}: depends_on contains a non-catalog ID")
        if any(parallel not in plan_ids for parallel in parallel_units):
            violations.append(
                f"{unit_id}: parallel_after_approval contains a non-catalog ID"
            )
        if unit_id in dependencies or unit_id in parallel_units:
            violations.append(f"{unit_id}: ownership graph contains a self-reference")
        dependency_graph[str(unit_id)] = list(dependencies)
        for prefix in unit.get("table_prefixes", []):
            if prefix.startswith("physical policy"):
                continue
            previous = table_prefix_owners.setdefault(prefix, str(unit_id))
            if previous != unit_id:
                violations.append(
                    f"table prefix {prefix!r} is owned by both {previous} and {unit_id}"
                )
        for semantic_path in unit.get("contract_semantic_paths", []):
            if not semantic_path.startswith(
                "backend/src/agentmonitor/contracts/providers/"
            ):
                violations.append(
                    f"{unit_id}: provider extension path violates frozen namespace"
                )
    visit_state: dict[str, int] = {}

    def visit(unit_id: str) -> None:
        visit_state[unit_id] = 1
        for dependency in dependency_graph.get(unit_id, []):
            if visit_state.get(dependency) == 1:
                violations.append(
                    f"parallel ownership dependency graph has a cycle at {unit_id}->{dependency}"
                )
            elif visit_state.get(dependency, 0) == 0:
                visit(dependency)
        visit_state[unit_id] = 2

    for unit_id in plan_ids:
        if visit_state.get(unit_id, 0) == 0:
            visit(unit_id)
    shared = raw.get("shared_writers", [])
    artifacts = [item.get("artifact") for item in shared]
    if len(shared) < 10 or len(artifacts) != len(set(artifacts)):
        violations.append("shared-writer allocation is missing or duplicated")
    shared_roots: dict[str, str] = {}
    for item in shared:
        if not item.get("semantic_owner") or not item.get("wave_writer"):
            violations.append(
                f"shared artifact {item.get('artifact')!r} lacks ownership"
            )
        paths = item.get("paths", [])
        if not paths:
            violations.append(
                f"shared artifact {item.get('artifact')!r} lacks exact paths"
            )
        for path in paths:
            normalized = str(path).removesuffix("/**").rstrip("/")
            if not normalized or " " in normalized or normalized.startswith("/"):
                violations.append(
                    f"shared artifact {item.get('artifact')!r} has invalid path {path!r}"
                )
                continue
            for unit_root, owner in write_roots.items():
                if (
                    normalized == unit_root
                    or normalized.startswith(unit_root + "/")
                    or unit_root.startswith(normalized + "/")
                ):
                    violations.append(
                        f"shared/unit root collision: {item.get('artifact')} and {owner}"
                    )
            for previous, artifact in shared_roots.items():
                if (
                    normalized == previous
                    or normalized.startswith(previous + "/")
                    or previous.startswith(normalized + "/")
                ):
                    violations.append(
                        f"shared root collision: {artifact} and {item.get('artifact')}"
                    )
            shared_roots[normalized] = str(item.get("artifact"))

    allocated_roots = tuple(write_roots) + tuple(shared_roots)
    literal_contract_paths: set[str] = set()
    for spec in catalog.plans:
        plan_path = repository_root / spec.path
        if plan_path.is_file():
            literal_contract_paths.update(
                re.findall(
                    r"backend/src/agentmonitor/contracts/[a-z0-9_/]+\.py",
                    plan_path.read_text(encoding="utf-8"),
                )
            )
    uncovered = sorted(
        contract_path
        for contract_path in literal_contract_paths
        if not any(
            contract_path == root or contract_path.startswith(root + "/")
            for root in allocated_roots
        )
    )
    if uncovered:
        violations.append(
            "public contract files lack a shared or exclusive writer: "
            + ", ".join(uncovered)
        )


def _validate_configuration_baseline(
    repository_root: Path,
    catalog: PlanningCatalog,
    plan_ids: set[str],
    violations: list[str],
) -> None:
    raw = _load_toml(
        repository_root / catalog.configuration_baseline_path,
        "configuration baseline",
        violations,
    )
    if not raw:
        return
    keys = raw.get("keys", [])
    names = [item.get("name") for item in keys]
    mentions: dict[str, set[str]] = {}
    for plan in catalog.plans:
        path = repository_root / plan.path
        if not path.is_file():
            continue
        for name in CONFIGURATION_KEY_PATTERN.findall(path.read_text(encoding="utf-8")):
            if name.endswith("_"):
                continue
            mentions.setdefault(name, set()).add(plan.plan_id)
    if raw.get("schema_version") != "1.0":
        violations.append("configuration baseline schema is not 1.0")
    if raw.get("status") != "draft_exact_allocation":
        violations.append("configuration baseline status is not draft_exact_allocation")
    if raw.get("owner_approved") is not False:
        violations.append("configuration baseline must not claim owner approval")
    if raw.get("implementation_authorized") is not False:
        violations.append("configuration baseline must not authorize implementation")
    if len(names) != len(set(names)):
        violations.append("configuration baseline contains duplicate keys")
    if set(names) != set(mentions):
        violations.append(
            "configuration baseline does not exactly match plan key allocations: "
            f"missing={sorted(set(mentions) - set(names))}, "
            f"extra={sorted(set(names) - set(mentions))}"
        )
    if raw.get("key_count") != len(keys) or len(keys) != 57:
        violations.append(
            "configuration key count mismatch: "
            f"metadata={raw.get('key_count')}, records={len(keys)}, expected=57"
        )
    required_fields = {
        "name",
        "owner",
        "referenced_by",
        "value_type",
        "unit",
        "default_or_derivation",
        "constraints",
        "secret",
        "sensitivity",
        "reload",
        "status",
        "first_version",
    }
    for item in keys:
        name = item.get("name", "<missing>")
        if not re.fullmatch(r"AGENTMONITOR_[A-Z0-9]+(?:_[A-Z0-9]+)*", str(name)):
            violations.append(f"configuration baseline has invalid key {name!r}")
        if item.get("owner") not in plan_ids:
            violations.append(f"{name}: invalid configuration owner")
        if set(item) != required_fields:
            violations.append(f"{name}: configuration record fields are incomplete")
        if set(item.get("referenced_by", [])) != mentions.get(name, set()):
            violations.append(f"{name}: referenced_by does not match plan corpus")
        for field in (
            "value_type",
            "unit",
            "default_or_derivation",
            "constraints",
            "sensitivity",
            "reload",
            "first_version",
        ):
            if not isinstance(item.get(field), str) or not item.get(field):
                violations.append(f"{name}: missing configuration field {field}")
        if not isinstance(item.get("secret"), bool):
            violations.append(f"{name}: secret classification must be boolean")
        if item.get("status") not in {"proposed_exact", "decision_required"}:
            violations.append(f"{name}: invalid configuration status")


def _validate_automation_catalog(
    repository_root: Path, catalog: PlanningCatalog, violations: list[str]
) -> None:
    raw = _load_toml(
        repository_root / catalog.automation_catalog_path,
        "automation routine catalog",
        violations,
    )
    if not raw:
        return
    routines = raw.get("routines", [])
    routine_ids = [item.get("id") for item in routines]
    if set(routine_ids) != set(REQUIRED_AUTOMATION_ROUTINES) or len(routine_ids) != len(
        set(routine_ids)
    ):
        violations.append(
            "automation catalog does not define exactly the mandatory routines"
        )
    allowed_statuses = {"operational", "operational_limited", "blocked"}
    for routine in routines:
        routine_id = routine.get("id", "<missing>")
        status = routine.get("status")
        command = routine.get("implementation_command")
        blockers = routine.get("blockers")
        if status not in allowed_statuses:
            violations.append(f"{routine_id}: invalid automation status")
        if not routine.get("owner") or not routine.get("scope"):
            violations.append(f"{routine_id}: missing automation owner or scope")
        if not isinstance(command, list) or not isinstance(blockers, list):
            violations.append(f"{routine_id}: command/blockers must be arrays")
            continue
        if status in {"operational", "operational_limited"} and not command:
            violations.append(f"{routine_id}: executable routine lacks command")
        if (
            command
            and len(command) > 1
            and command[0].startswith("python")
            and command[1].endswith(".py")
            and not (repository_root / command[1]).is_file()
        ):
            violations.append(f"{routine_id}: automation command script is missing")
        if status == "operational" and blockers:
            violations.append(f"{routine_id}: operational routine still has blockers")
        if status == "blocked" and (command or not blockers):
            violations.append(f"{routine_id}: blocked routine does not fail closed")


def _source_requirement_statuses(repository_root: Path) -> dict[str, str]:
    requirements_path = repository_root / "docs/product/requirements.md"
    acceptance_path = repository_root / "docs/product/v1-acceptance-criteria.md"
    statuses: dict[str, str] = {}
    deferred_section = False
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            deferred_section = line.strip() == "## Deferred requirements"
        for requirement_id in REQUIREMENT_ID_PATTERN.findall(line):
            if "(Discovery)" in line:
                status = "discovery"
            elif "(Deferred)" in line or deferred_section:
                status = "deferred"
            else:
                status = "approved"
            prior = statuses.setdefault(requirement_id, status)
            if prior != status:
                raise ValueError(
                    f"source requirement {requirement_id} has conflicting statuses"
                )
    for requirement_id in REQUIREMENT_ID_PATTERN.findall(
        acceptance_path.read_text(encoding="utf-8")
    ):
        prior = statuses.setdefault(requirement_id, "approved")
        if prior != "approved":
            raise ValueError(
                f"acceptance criterion {requirement_id} conflicts with {prior}"
            )
    return statuses


def validate_requirement_ownership(
    repository_root: Path, catalog: PlanningCatalog
) -> list[str]:
    """Validate exact requirement ownership against the real plan corpus."""

    violations: list[str] = []
    path = repository_root / catalog.requirement_ownership_path
    raw = _load_toml(path, "requirement ownership manifest", violations)
    if not raw:
        return violations
    try:
        source_statuses = _source_requirement_statuses(repository_root)
    except (FileNotFoundError, ValueError) as error:
        violations.append(f"requirement sources cannot be resolved: {error}")
        return violations

    entries = raw.get("requirements", [])
    entry_ids = [item.get("requirement_id") for item in entries]
    plan_ids = {plan.plan_id for plan in catalog.plans}
    if raw.get("schema_version") != "1.0":
        violations.append("requirement ownership schema is not 1.0")
    if raw.get("owner_approved") is not False:
        violations.append("requirement ownership must not claim owner approval")
    if raw.get("implementation_authorized") is not False:
        violations.append("requirement ownership must not authorize implementation")
    if len(entry_ids) != len(set(entry_ids)):
        violations.append("requirement ownership contains duplicate requirement IDs")
    if set(entry_ids) != set(source_statuses):
        missing = sorted(set(source_statuses) - set(entry_ids))
        extra = sorted(set(entry_ids) - set(source_statuses))
        violations.append(
            "requirement ownership does not exactly match product sources: "
            f"missing={missing}, extra={extra}"
        )
    if raw.get("entry_count") != len(entries) or len(entries) != 154:
        violations.append(
            "requirement ownership entry count mismatch: "
            f"metadata={raw.get('entry_count')}, records={len(entries)}, expected=154"
        )

    contract_raw = _load_toml(
        repository_root / catalog.contract_baseline_path,
        "contract baseline for requirement ownership",
        violations,
    )
    contract_records = contract_raw.get("contracts", [])
    contract_ids = {item.get("id") for item in contract_records}
    contract_producers = {
        item.get("id"): item.get("producer") for item in contract_records
    }
    scenario_ids: set[str] = set()
    for plan in catalog.plans:
        plan_path = repository_root / plan.path
        if plan_path.is_file():
            scenario_ids.update(
                _scenario_definitions(
                    plan_path.read_text(encoding="utf-8"), plan.scenario_prefix
                )
            )

    status_counts = {"approved": 0, "discovery": 0, "deferred": 0}
    for item in entries:
        requirement_id = item.get("requirement_id", "<missing>")
        status = item.get("status")
        if status in status_counts:
            status_counts[status] += 1
        expected_status = source_statuses.get(requirement_id)
        if expected_status is not None and status != expected_status:
            violations.append(
                f"{requirement_id}: manifest status {status!r} != source {expected_status!r}"
            )
        primary = item.get("primary_plan")
        supports = item.get("supporting_plans", [])
        contracts = item.get("contract_ids", [])
        scenarios = item.get("scenario_ids", [])
        boundaries = item.get("evidence_boundaries", [])
        for field_name, values in (
            ("supporting_plans", supports),
            ("contract_ids", contracts),
            ("scenario_ids", scenarios),
            ("evidence_boundaries", boundaries),
        ):
            if not isinstance(values, list) or len(values) != len(set(values)):
                violations.append(
                    f"{requirement_id}: {field_name} must be a duplicate-free list"
                )
        if status == "deferred":
            if primary != "POST-V1":
                violations.append(f"{requirement_id}: deferred primary must be POST-V1")
            if supports or contracts or scenarios or boundaries:
                violations.append(
                    f"{requirement_id}: deferred item has a V1 ownership/evidence assignment"
                )
            if not item.get("v1_guard"):
                violations.append(f"{requirement_id}: deferred item lacks a V1 guard")
            continue
        if primary not in plan_ids:
            violations.append(
                f"{requirement_id}: invalid exact primary plan {primary!r}"
            )
        if any(plan_id not in plan_ids for plan_id in supports):
            violations.append(f"{requirement_id}: invalid supporting plan")
        if primary in supports:
            violations.append(
                f"{requirement_id}: primary is duplicated as supporting plan"
            )
        if not contracts or any(
            contract_id not in contract_ids for contract_id in contracts
        ):
            violations.append(
                f"{requirement_id}: missing or invalid contract reference"
            )
        parties = {primary, *supports}
        missing_producers = sorted(
            {
                contract_producers.get(contract_id)
                for contract_id in contracts
                if contract_producers.get(contract_id) not in parties
            }
        )
        if missing_producers:
            violations.append(
                f"{requirement_id}: contract producers absent from ownership parties: "
                + ", ".join(str(producer) for producer in missing_producers)
            )
        if not scenarios:
            violations.append(f"{requirement_id}: has no exact planned scenario")
        primary_spec = next(
            (plan for plan in catalog.plans if plan.plan_id == primary), None
        )
        if primary_spec is not None and not any(
            scenario_id.startswith(primary_spec.scenario_prefix)
            for scenario_id in scenarios
        ):
            violations.append(
                f"{requirement_id}: primary plan has no owned evidence scenario"
            )
        for scenario_id in scenarios:
            if not isinstance(scenario_id, str) or not SCENARIO_ID_PATTERN.fullmatch(
                scenario_id
            ):
                violations.append(
                    f"{requirement_id}: non-exact scenario reference {scenario_id!r}"
                )
            elif scenario_id not in scenario_ids:
                violations.append(
                    f"{requirement_id}: undefined scenario reference {scenario_id}"
                )
        if not boundaries or any(
            boundary not in EVIDENCE_BOUNDARIES for boundary in boundaries
        ):
            violations.append(f"{requirement_id}: missing or invalid evidence boundary")

    if status_counts != {"approved": 144, "discovery": 3, "deferred": 7}:
        violations.append(
            f"requirement ownership status counts are wrong: {status_counts}"
        )
    if raw.get("non_deferred_count") != 147 or raw.get("deferred_count") != 7:
        violations.append("requirement ownership summary counts are wrong")
    return violations


def validate_plan_snapshot(
    repository_root: Path, catalog: PlanningCatalog
) -> list[str]:
    """Verify the immutable digest manifest for the exact synchronized drafts."""

    violations: list[str] = []
    path = repository_root / catalog.plan_snapshot_path
    raw = _load_toml(path, "plan snapshot", violations)
    if not raw:
        return violations
    if raw.get("schema_version") != "1.0":
        violations.append("plan snapshot schema is not 1.0")
    if raw.get("status") != "draft_synchronized":
        violations.append("plan snapshot status is not draft_synchronized")
    if raw.get("owner_approved") is not False:
        violations.append("plan snapshot must not claim owner approval")
    if raw.get("implementation_authorized") is not False:
        violations.append("plan snapshot must not authorize implementation")

    records = raw.get("plans", [])
    record_ids = [item.get("id") for item in records]
    catalog_by_id = {plan.plan_id: plan for plan in catalog.plans}
    if raw.get("plan_count") != len(catalog.plans) or len(records) != len(
        catalog.plans
    ):
        violations.append("plan snapshot does not contain exactly 20 records")
    if len(record_ids) != len(set(record_ids)) or set(record_ids) != set(catalog_by_id):
        violations.append("plan snapshot IDs do not exactly match the catalog")
    for item in records:
        plan_id = item.get("id")
        plan = catalog_by_id.get(plan_id)
        if plan is None:
            continue
        if item.get("path") != plan.path:
            violations.append(f"{plan_id}: snapshot path does not match catalog")
            continue
        plan_path = repository_root / plan.path
        try:
            content = plan_path.read_bytes()
        except FileNotFoundError:
            violations.append(f"{plan_id}: snapshotted plan is missing")
            continue
        digest = hashlib.sha256(content).hexdigest()
        if item.get("sha256") != digest:
            violations.append(f"{plan_id}: snapshot SHA-256 does not match")
        if item.get("bytes") != len(content):
            violations.append(f"{plan_id}: snapshot byte count does not match")
        version_match = re.search(
            r"Plan version:\s*`?([^`\n]+)", content.decode("utf-8")
        )
        current_version = version_match.group(1).strip() if version_match else None
        if not item.get("plan_version"):
            violations.append(f"{plan_id}: snapshot lacks a plan version")
        elif item.get("plan_version") != current_version:
            violations.append(f"{plan_id}: snapshot plan version does not match")
    expected_controls = {
        "planning-catalog": "docs/plans/planning-catalog.toml",
        "contract-baseline": catalog.contract_baseline_path,
        "contract-adoption": catalog.contract_adoption_path,
        "configuration-baseline": catalog.configuration_baseline_path,
        "requirement-ownership": catalog.requirement_ownership_path,
        "parallel-ownership": catalog.parallel_ownership_path,
        "automation-routines": catalog.automation_catalog_path,
        "automation-standard": catalog.automation_standard_path,
        "m0-g0-approval": catalog.m0_g0_approval_path,
    }
    controls = raw.get("controls", [])
    control_ids = [item.get("id") for item in controls]
    if raw.get("control_count") != len(expected_controls) or len(controls) != len(
        expected_controls
    ):
        violations.append("plan snapshot control count is wrong")
    if len(control_ids) != len(set(control_ids)) or set(control_ids) != set(
        expected_controls
    ):
        violations.append("plan snapshot controls do not match required baselines")
    for item in controls:
        control_id = item.get("id")
        expected_path = expected_controls.get(control_id)
        if expected_path is None:
            continue
        if item.get("path") != expected_path:
            violations.append(f"{control_id}: snapshot control path mismatch")
            continue
        control_path = repository_root / expected_path
        try:
            content = control_path.read_bytes()
        except FileNotFoundError:
            violations.append(f"{control_id}: snapshotted control is missing")
            continue
        if item.get("sha256") != hashlib.sha256(content).hexdigest():
            violations.append(f"{control_id}: snapshot control SHA-256 mismatch")
        if item.get("bytes") != len(content):
            violations.append(f"{control_id}: snapshot control byte count mismatch")
    return violations


def validate_scenario_references(
    repository_root: Path, catalog: PlanningCatalog
) -> list[str]:
    """Resolve every exact scenario identifier mentioned anywhere in the plans."""

    violations: list[str] = []
    definitions: set[str] = set()
    texts: list[tuple[str, str]] = []
    prefix_roots = sorted(
        {plan.scenario_prefix.removesuffix("-") for plan in catalog.plans},
        key=len,
        reverse=True,
    )
    reference_pattern = re.compile(
        rf"\b(?:{'|'.join(re.escape(prefix) for prefix in prefix_roots)})"
        r"-[A-Z][A-Z0-9-]*-\d{3}\b"
    )
    for plan in catalog.plans:
        path = repository_root / plan.path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        texts.append((plan.plan_id, text))
        definitions.update(_scenario_definitions(text, plan.scenario_prefix))
    for plan_id, text in texts:
        unresolved = sorted(set(reference_pattern.findall(text)) - definitions)
        if unresolved:
            violations.append(
                f"{plan_id}: undefined exact scenario references: {', '.join(unresolved)}"
            )
    return violations


def _validate_current_planning_entry_points(
    repository_root: Path, catalog: PlanningCatalog, violations: list[str]
) -> None:
    program_path = repository_root / "docs/plans/integration/v1-planning-program.md"
    program = program_path.read_text(encoding="utf-8") if program_path.is_file() else ""
    registry_path = repository_root / catalog.registry_path
    registry = (
        registry_path.read_text(encoding="utf-8") if registry_path.is_file() else ""
    )
    if "20 synchronized Draft planning artifacts" not in program:
        violations.append("planning program does not expose the current 20-plan state")
    for stale in (
        "The immediate planning wave contains",
        "Detailed P0 plan drafts: in preparation",
    ):
        if stale in program:
            violations.append(f"planning program retains stale state: {stale!r}")
    if "every remaining module/adapter/boundary plan" in registry:
        violations.append(
            "planning registry incorrectly describes existing plans as remaining"
        )
    for plan in catalog.plans:
        plan_path = repository_root / plan.path
        if not plan_path.is_file():
            continue
        if STALE_DRAFT_CONTRACT_CLAIM.search(plan_path.read_text(encoding="utf-8")):
            violations.append(
                f"{plan.plan_id}: Draft table claims a contract is Approved/Synchronized"
            )


def validate_repository(repository_root: Path, stage: str) -> list[str]:
    violations: list[str] = []
    try:
        catalog = load_catalog(repository_root)
    except (FileNotFoundError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        return [f"catalog cannot be loaded: {error}"]

    if catalog.schema_version != "1.0":
        violations.append(f"unsupported catalog schema {catalog.schema_version!r}")
    if len(catalog.plans) != catalog.required_plan_count:
        violations.append(
            f"catalog contains {len(catalog.plans)} plans; "
            f"expected {catalog.required_plan_count}"
        )

    ids = [plan.plan_id for plan in catalog.plans]
    plan_ids = set(ids)
    paths = [plan.path for plan in catalog.plans]
    if len(ids) != len(set(ids)):
        violations.append("catalog contains duplicate plan IDs")
    if len(paths) != len(set(paths)):
        violations.append("catalog contains duplicate plan paths")

    registry_file = repository_root / catalog.registry_path
    registry_text = (
        registry_file.read_text(encoding="utf-8") if registry_file.exists() else ""
    )
    if not registry_text:
        violations.append(f"missing planning registry: {catalog.registry_path}")

    for plan in catalog.plans:
        plan_file = repository_root / plan.path
        if not plan_file.is_file():
            violations.append(f"{plan.plan_id}: missing artifact {plan.path}")
            continue
        text = plan_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) < plan.minimum_lines:
            violations.append(
                f"{plan.plan_id}: {len(lines)} lines; minimum is {plan.minimum_lines}"
            )
        required_terms = (
            REQUIRED_DISCOVERY_PLAN_TERMS
            if plan.kind == "discovery"
            else REQUIRED_IMPLEMENTATION_PLAN_TERMS
        )
        for term in required_terms:
            if term.casefold() not in text.casefold():
                violations.append(
                    f"{plan.plan_id}: missing required content marker {term!r}"
                )
        if plan.kind not in {"discovery", "foundation"}:
            for heading in MODULE_SECTIONS:
                if not re.search(rf"^{re.escape(heading)}", text, re.MULTILINE):
                    violations.append(
                        f"{plan.plan_id}: missing template section {heading}"
                    )
        scenario_definitions = _scenario_definitions(text, plan.scenario_prefix)
        scenario_count = len(set(scenario_definitions))
        if len(scenario_definitions) != scenario_count:
            violations.append(f"{plan.plan_id}: duplicate scenario definitions")
        if scenario_count < plan.minimum_scenarios:
            violations.append(
                f"{plan.plan_id}: {scenario_count} unique defined scenarios; "
                f"minimum is {plan.minimum_scenarios}"
            )
        registry_target = str(Path(plan.path).relative_to("docs/plans"))
        if registry_target not in registry_text:
            violations.append(
                f"{plan.plan_id}: registry does not link {registry_target}"
            )

    automation_file = repository_root / catalog.automation_standard_path
    automation_text = (
        automation_file.read_text(encoding="utf-8") if automation_file.exists() else ""
    )
    if not automation_text:
        violations.append(
            f"missing automation standard: {catalog.automation_standard_path}"
        )
    else:
        for routine in REQUIRED_AUTOMATION_ROUTINES:
            if routine not in automation_text:
                violations.append(f"automation standard does not define {routine}")
    _validate_automation_catalog(repository_root, catalog, violations)

    if stage == "synchronized":
        _validate_current_planning_entry_points(repository_root, catalog, violations)
        _validate_contract_baseline(repository_root, catalog, plan_ids, violations)
        violations.extend(validate_contract_adoption(repository_root, catalog))
        violations.extend(validate_event_topology(repository_root, catalog))
        _validate_configuration_baseline(repository_root, catalog, plan_ids, violations)
        violations.extend(validate_requirement_ownership(repository_root, catalog))
        violations.extend(validate_scenario_references(repository_root, catalog))
        _validate_parallel_ownership(repository_root, catalog, plan_ids, violations)
        violations.extend(validate_plan_snapshot(repository_root, catalog))
        snapshot_path = repository_root / catalog.plan_snapshot_path
        snapshot_binding = None
        if snapshot_path.is_file():
            snapshot_binding = (
                "Plan snapshot SHA-256: `"
                + hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
                + "`"
            )
        readiness_file = repository_root / catalog.readiness_audit_path
        if not readiness_file.is_file():
            violations.append(
                f"missing final independent readiness audit: {catalog.readiness_audit_path}"
            )
        else:
            readiness_text = readiness_file.read_text(encoding="utf-8")
            if "Status: **PASS-CONDITIONAL**" not in readiness_text:
                violations.append(
                    "final independent readiness audit is not PASS-CONDITIONAL"
                )
            for number in range(1, 19):
                finding = f"CS1-R{number:02d}"
                if finding not in readiness_text:
                    violations.append(
                        f"final independent readiness audit omits {finding}"
                    )
            if snapshot_binding and snapshot_binding not in readiness_text:
                violations.append(
                    "final independent readiness audit is not bound to the plan snapshot"
                )
        review_file = repository_root / catalog.synchronization_review_path
        if not review_file.is_file():
            violations.append(
                "missing cross-plan synchronization review: "
                f"{catalog.synchronization_review_path}"
            )
        else:
            review_text = review_file.read_text(encoding="utf-8")
            if "Status: **Complete**" not in review_text:
                violations.append("cross-plan synchronization review is not Complete")
            if "Semantic validation: **Passed**" not in review_text:
                violations.append(
                    "cross-plan synchronization review lacks Passed semantic validation"
                )
            for plan in catalog.plans:
                if plan.plan_id not in review_text:
                    violations.append(
                        f"synchronization review does not account for {plan.plan_id}"
                    )
            if snapshot_binding and snapshot_binding not in review_text:
                violations.append(
                    "cross-plan synchronization review is not bound to the plan snapshot"
                )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (defaults to this checkout)",
    )
    parser.add_argument(
        "--stage",
        choices=("draft-complete", "synchronized"),
        default="synchronized",
    )
    arguments = parser.parse_args(argv)
    violations = validate_repository(arguments.root.resolve(), arguments.stage)
    if violations:
        print(f"PLANNING GATE: FAILED ({len(violations)} violation(s))")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print(f"PLANNING GATE: PASSED ({arguments.stage})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
