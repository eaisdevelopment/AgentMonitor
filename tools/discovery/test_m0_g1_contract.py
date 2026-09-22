"""Real-checkout contract tests for the minimal Milestone 0 G1 bundle."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_ROOT = REPOSITORY_ROOT / "docs/plans/discovery"
TEMPLATE_ROOT = REPOSITORY_ROOT / "docs/templates"
SPEC_PATH = DISCOVERY_ROOT / "m0-g1-control-specification.md"
SCHEMA_PATH = DISCOVERY_ROOT / "m0-g1-record.schema.json"

EXPECTED_RECORDS = {
    "ApprovalRecordV1",
    "CustodyDecisionV1",
    "E1ScannerAdmissionV1",
    "IncidentRecordV1",
    "OperationPacketV1",
    "RunResultV1",
    "ScenarioLedgerV1",
}

EXPECTED_TEMPLATES = {
    "m0-custody-register-template.md",
    "m0-e1-admission-template.md",
    "m0-operation-assertion-packet-template.md",
    "m0-run-result-template.md",
    "m0-scenario-ledger-template.md",
    "m0-stop-incident-template.md",
}

OBSOLETE_PATHS = {
    "docs/plans/discovery/m0-g1-record-contract.toml",
    "docs/plans/discovery/m0-g1-review-freeze.toml",
    "docs/plans/discovery/m0-sequencing-clarification-001.md",
    "tools/discovery/m0_g1_contract_core_tests.py",
    "tools/discovery/m0_g1_contract_e1_pipeline_tests.py",
    "tools/discovery/m0_g1_contract_evidence_tests.py",
    "tools/discovery/m0_g1_contract_governance_tests.py",
    "tools/discovery/m0_g1_contract_provider_tests.py",
    "tools/discovery/m0_g1_contract_recovery_tests.py",
    "tools/discovery/m0_g1_contract_test_support.py",
    "tools/discovery/update_m0_g1_review_freeze.py",
}

OBSOLETE_TEMPLATES = {
    "m0-code-registry-template.md",
    "m0-execution-attempt-start-template.md",
    "m0-provider-product-registry-template.md",
    "m0-publication-result-template.md",
    "m0-scenario-disposition-template.md",
    "m0-scope-binding-template.md",
}


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def iter_object_schemas(value: object):
    if isinstance(value, dict):
        if value.get("type") == "object":
            yield value
        for child in value.values():
            yield from iter_object_schemas(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_object_schemas(child)


class MinimalM0G1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = SPEC_PATH.read_text(encoding="utf-8")
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_bundle_is_small_and_obsolete_design_is_absent(self) -> None:
        self.assertLessEqual(line_count(SPEC_PATH), 260)
        self.assertLessEqual(line_count(SCHEMA_PATH), 900)
        self.assertLessEqual(line_count(Path(__file__)), 240)
        self.assertLessEqual(
            sum(line_count(TEMPLATE_ROOT / name) for name in EXPECTED_TEMPLATES),
            500,
        )
        for relative_path in OBSOLETE_PATHS:
            self.assertFalse((REPOSITORY_ROOT / relative_path).exists(), relative_path)
        for name in OBSOLETE_TEMPLATES:
            self.assertFalse((TEMPLATE_ROOT / name).exists(), name)

    def test_schema_has_only_the_records_g1_needs(self) -> None:
        self.assertEqual(
            "https://json-schema.org/draft/2020-12/schema",
            self.schema["$schema"],
        )
        self.assertEqual(EXPECTED_RECORDS, set(self.schema["$defs"]))
        self.assertEqual(
            {f"#/$defs/{name}" for name in EXPECTED_RECORDS},
            {item["$ref"] for item in self.schema["oneOf"]},
        )
        for object_schema in iter_object_schemas(self.schema):
            self.assertIs(False, object_schema.get("additionalProperties"))

    def test_records_encode_the_required_safety_controls(self) -> None:
        definitions = self.schema["$defs"]
        self.assertTrue(
            {
                "external_root_ref",
                "retention_until_utc",
                "owner_selected",
                "repository_storage_prohibited",
            }
            <= set(definitions["CustodyDecisionV1"]["properties"])
        )
        self.assertIn(
            "owner_accepted_synced",
            definitions["CustodyDecisionV1"]["properties"]
            ["sync_backup_disposition"]["enum"],
        )
        operation = definitions["OperationPacketV1"]["properties"]
        self.assertTrue(
            {
                "scenario_id",
                "operation",
                "targets",
                "assertions",
                "side_effect_budget",
                "stop_conditions",
                "approvals",
            }
            <= set(operation)
        )
        self.assertEqual(
            ["Passed", "Failed", "Blocked", "Not Run"],
            definitions["ScenarioLedgerV1"]["$defs"]["entry"]["properties"]
            ["status"]["enum"],
        )
        self.assertIn(
            "prohibited_data_observed",
            definitions["RunResultV1"]["properties"],
        )
        self.assertIn(
            "telemetry_disabled",
            definitions["E1ScannerAdmissionV1"]["properties"],
        )

    def test_spec_defines_goal_authority_and_exit_without_execution_engine(self) -> None:
        normalized_spec = " ".join(self.spec.replace("`", "").split())
        required_phrases = (
            "minimum safety controls required before G2",
            "does not authorize provider, account, process, profile, or evidence-root access",
            "M0-COM-001 is the first ordinary scenario after G1",
            "owner selects the external custody root",
            "one exact operation packet",
            "Passed, Failed, Blocked, or Not Run",
            "G1 exits only when",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, normalized_spec)
        for obsolete_term in (
            "fencing epoch",
            "takeover",
            "execution lease",
            "boundary progress stream",
            "publication recovery",
        ):
            self.assertNotIn(obsolete_term, self.spec.lower())

    def test_only_the_six_g1_authoring_templates_exist(self) -> None:
        actual = {path.name for path in TEMPLATE_ROOT.glob("m0-*-template.md")}
        self.assertEqual(EXPECTED_TEMPLATES, actual)
        for name in EXPECTED_TEMPLATES:
            text = (TEMPLATE_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("Never include secrets or prohibited content", text)
            self.assertNotIn("m0-g1-record-contract.toml", text)

    def test_operation_template_requires_root_review_and_operator_checkpoint(self) -> None:
        text = (
            TEMPLATE_ROOT / "m0-operation-assertion-packet-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| Root/integration |", text)
        self.assertIn("Operator sign-off is a separate preflight record", text)
        self.assertIn("not an `OperationPacketV1` field", " ".join(text.split()))

    def test_indexes_reference_only_the_minimal_bundle(self) -> None:
        docs_index = (REPOSITORY_ROOT / "docs/README.md").read_text(encoding="utf-8")
        template_index = (TEMPLATE_ROOT / "README.md").read_text(encoding="utf-8")
        for text in (docs_index, template_index):
            self.assertNotIn("m0-g1-record-contract.toml", text)
            self.assertNotIn("m0-g1-review-freeze.toml", text)
            self.assertNotIn("m0-sequencing-clarification-001.md", text)
        for name in EXPECTED_TEMPLATES:
            self.assertIn(name, template_index)


if __name__ == "__main__":
    unittest.main()
