"""Real-checkout contract tests for the scoped M0-to-M3 Claude handoff."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_ROOT = REPOSITORY_ROOT / "docs/discovery/m0"
MAPPING_PATH = DISCOVERY_ROOT / "m0-to-m03-claude-v1.json"
OTEL_MAPPING_PATH = DISCOVERY_ROOT / "m0-to-m03-claude-otel-v1.json"
HANDOFF_PATH = DISCOVERY_ROOT / "m3-claude-handoff.md"
EVIDENCE_PATH = DISCOVERY_ROOT / "m3-claude-evidence-v1.json"
ACCEPTANCE_PATH = DISCOVERY_ROOT / "m3-handoff-acceptance-v1.json"
SCHEMA_BUNDLE_PATH = DISCOVERY_ROOT / "m3-handoff-schema-bundle-v1.json"
CONTRACT_BUNDLE_PATH = DISCOVERY_ROOT / "m3-ctr-prov-002-contract-bundle-v1.json"
TARGETED_PROBE_EVIDENCE_PATH = (
    REPOSITORY_ROOT / "docs/evidence/m3-claude-otel-targeted-probe.md"
)
APPROVAL_ROOT = DISCOVERY_ROOT / "m3-handoff-approvals"
M3_PLAN_PATH = (
    REPOSITORY_ROOT
    / "docs/superpowers/plans/2026-09-19-agentmonitor-v1-m3-claude-slice.md"
)
VALIDATOR_PATH = REPOSITORY_ROOT / "tools/discovery/m3_handoff_validate.py"
M0_PYTHON = REPOSITORY_ROOT / ".venv-m0-g1/bin/python"


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class M3HandoffContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mapping = read_json(MAPPING_PATH)
        cls.handoff = HANDOFF_PATH.read_text(encoding="utf-8")
        cls.m3_plan = M3_PLAN_PATH.read_text(encoding="utf-8")

    def test_exact_single_profile_tuple_is_declared(self) -> None:
        self.assertEqual(
            {
                "provider_key": "claude",
                "product": "Claude Code",
                "provider_version": "2.1.278",
                "platform": {"operating_system": "Linux", "architecture": "x86_64"},
                "plan_class": "Claude Max",
                "profile_ref": "REF-M0-CLAUDE-PROFILE-001",
            },
            self.mapping["scope"],
        )

    def test_quota_support_is_limited_by_bounded_network_evidence(self) -> None:
        capabilities = {
            item["capability_id"]: item for item in self.mapping["capabilities"]
        }
        quota = capabilities["subscription.quota"]
        self.assertEqual("supported", quota["decision"])
        self.assertEqual("available", quota["availability"])
        self.assertEqual("verified", quota["network_bounds"]["status"])
        self.assertEqual(
            ["api.anthropic.com:443"], quota["network_bounds"]["allowed_hosts"]
        )
        self.assertEqual(1, quota["network_bounds"]["max_cli_invocations"])
        self.assertEqual(32, quota["network_bounds"]["max_tls_connections"])
        self.assertEqual(4_194_304, quota["network_bounds"]["max_total_upstream_bytes"])
        self.assertEqual(
            4_194_304, quota["network_bounds"]["max_total_downstream_bytes"]
        )
        self.assertIs(False, quota["network_bounds"]["http_request_count_observable"])
        self.assertEqual(30, quota["network_bounds"]["deadline_seconds"])
        self.assertEqual(300, quota["network_bounds"]["minimum_interval_seconds"])
        self.assertEqual(0, quota["network_bounds"]["automatic_retry_count"])
        self.assertEqual("deny", quota["network_bounds"]["redirect_policy"])
        self.assertEqual(
            "no_model_prompt_or_inference_authorized",
            quota["network_bounds"]["cost_policy"],
        )
        self.assertRegex(quota["network_bounds"]["evidence_ref"], r"^REF-[A-Z0-9-]+$")
        self.assertEqual(
            ["M0-CLA-003", "M0-CLA-004", "M0-CLA-010", "M0-COM-007"],
            quota["scenario_ids"],
        )
        self.assertEqual("incremental", quota["render_policy"]["refresh_mode"])
        self.assertEqual("Usage credits", quota["render_policy"]["terminal_marker"])
        self.assertEqual(
            "latest_complete_set_immediately_preceding_terminal_marker",
            quota["render_policy"]["accepted_render"],
        )
        self.assertEqual(
            "allowed", quota["render_policy"]["duplicates_across_refreshes"]
        )
        self.assertEqual(
            "fail_closed",
            quota["render_policy"]["conflicting_duplicates_within_final_render"],
        )

    def test_process_observation_and_account_correlation_are_distinct(self) -> None:
        capabilities = {
            item["capability_id"]: item for item in self.mapping["capabilities"]
        }
        observation = capabilities["local.process.observation"]
        correlation = capabilities["local.process.account_correlation"]
        self.assertEqual("supported", observation["decision"])
        self.assertEqual("available", observation["availability"])
        self.assertEqual("supported", correlation["decision"])
        self.assertEqual("available", correlation["availability"])
        self.assertEqual("automatic_matched", correlation["correlation_outcome"])
        self.assertEqual("Passed", correlation["targeted_profile_probe_status"])
        self.assertEqual(
            ["M0-CLA-008", "M0-LNX-007", "M0-LNX-012"],
            correlation["scenario_ids"],
        )
        self.assertEqual("M0-M03-CLAUDE-OTEL-001", correlation["mapping_ref"])

    def test_official_otel_mapping_is_a_bound_repository_artifact(self) -> None:
        self.assertTrue(OTEL_MAPPING_PATH.is_file(), "OTEL mapping is missing")
        mapping = read_json(OTEL_MAPPING_PATH)
        self.assertEqual("M0-M03-CLAUDE-OTEL-001", mapping["mapping_id"])
        self.assertEqual("approved", mapping["status"])
        self.assertEqual(
            "https://code.claude.com/docs/en/monitoring-usage",
            mapping["official_source"]["url"],
        )
        self.assertEqual("claude.otel.metrics.http-json.v1", mapping["source_id"])
        self.assertEqual("Passed", mapping["targeted_profile_probe"]["status"])
        self.assertEqual(
            str(TARGETED_PROBE_EVIDENCE_PATH.relative_to(REPOSITORY_ROOT)),
            mapping["targeted_profile_probe"]["repository_evidence"],
        )
        self.assertTrue(
            TARGETED_PROBE_EVIDENCE_PATH.is_file(),
            "targeted OTLP probe evidence is missing",
        )
        self.assertEqual(
            sha256(TARGETED_PROBE_EVIDENCE_PATH),
            mapping["targeted_profile_probe"]["repository_evidence_sha256"],
        )
        self.assertFalse(mapping["targeted_profile_probe"]["raw_payload_retained"])
        self.assertFalse(mapping["targeted_profile_probe"]["provider_state_mutated"])

    def test_auth_and_version_drift_outcomes_are_normalized(self) -> None:
        outcomes = self.mapping["normalized_outcomes"]
        self.assertEqual(
            "provider_version_unverified",
            outcomes["compatibility"]["unknown_or_out_of_range_version"],
        )
        self.assertEqual(
            "unverified_provider_version",
            outcomes["operation"]["version_drift"],
        )
        self.assertEqual(
            "reauthentication_required",
            outcomes["operation"]["provider_authentication_signal"],
        )
        self.assertEqual(
            "authorization_insufficient",
            outcomes["operation"]["provider_authorization_signal"],
        )
        self.assertEqual(
            {
                "outer_outcome": "success",
                "typed_identity_result": "wrong_account_detected",
            },
            outcomes["identity_mismatch"],
        )

    def test_repository_docs_contain_no_dynamic_quota_or_process_values(self) -> None:
        normalized = " ".join(self.handoff.lower().split())
        for prohibited in (
            "twelve naturally running",
            "zero input/output tokens",
            "zero session cost",
            "rolling-window, weekly",
        ):
            self.assertNotIn(prohibited, normalized)
        self.assertIn("m3-claude-evidence-v1.json", self.handoff)
        self.assertIn("side-effect reconciliation", normalized)

    def test_evidence_index_has_exact_scenarios_and_side_effect_statuses(self) -> None:
        self.assertTrue(EVIDENCE_PATH.is_file(), "scoped evidence index is missing")
        evidence = read_json(EVIDENCE_PATH)
        scenario_ids = [item["scenario_id"] for item in evidence["scenarios"]]
        self.assertEqual(
            [
                "M0-COM-002",
                "M0-COM-003",
                "M0-COM-005",
                "M0-COM-007",
                "M0-CLA-001",
                "M0-CLA-002",
                "M0-CLA-003",
                "M0-CLA-004",
                "M0-CLA-008",
                "M0-CLA-010",
                "M0-LNX-001",
                "M0-LNX-002",
                "M0-LNX-004",
                "M0-LNX-006",
                "M0-LNX-007",
                "M0-LNX-011",
                "M0-LNX-012",
                "M0-LNX-013",
            ],
            scenario_ids,
        )
        self.assertTrue(
            {item["status"] for item in evidence["scenarios"]}
            <= {"Passed", "Failed", "Blocked", "Not Run"}
        )
        reconciliations = evidence["side_effect_reconciliations"]
        self.assertEqual(
            {"quota_source", "process_observation", "targeted_profile_probe"},
            {item["lane"] for item in reconciliations},
        )
        for item in reconciliations:
            self.assertIn(item["status"], {"Passed", "Failed", "Blocked", "Not Run"})
            self.assertNotIn("observed_value", item)

    def test_schema_and_contract_bundles_bind_current_artifacts(self) -> None:
        self.assertTrue(SCHEMA_BUNDLE_PATH.is_file(), "schema bundle is missing")
        self.assertTrue(CONTRACT_BUNDLE_PATH.is_file(), "contract bundle is missing")
        schema_bundle = read_json(SCHEMA_BUNDLE_PATH)
        contract_bundle = read_json(CONTRACT_BUNDLE_PATH)
        for artifact in schema_bundle["artifacts"]:
            path = REPOSITORY_ROOT / artifact["path"]
            self.assertEqual(sha256(path), artifact["sha256"])
        for artifact in contract_bundle["normative_artifacts"]:
            path = REPOSITORY_ROOT / artifact["path"]
            self.assertEqual(sha256(path), artifact["sha256"])
        self.assertEqual("CTR-PROV-002", contract_bundle["contract_id"])
        self.assertEqual("1.0.0", contract_bundle["contract_version"])
        self.assertEqual("current", contract_bundle["schema_artifact_status"])
        schema_artifact = contract_bundle["schema_artifact"]
        self.assertIsInstance(schema_artifact, dict)
        assert isinstance(schema_artifact, dict)
        self.assertEqual(
            "contracts/provider-system/capability-manifest-v1.schema.json",
            schema_artifact["path"],
        )
        self.assertEqual(
            sha256(REPOSITORY_ROOT / schema_artifact["path"]),
            schema_artifact["sha256"],
        )
        self.assertEqual("current", contract_bundle["status"])
        self.assertIsNone(contract_bundle["blocking_reason"])

    def test_acceptance_binds_every_exact_subject_and_four_detached_roles(self) -> None:
        self.assertTrue(ACCEPTANCE_PATH.is_file(), "handoff acceptance is missing")
        acceptance = read_json(ACCEPTANCE_PATH)
        self.assertEqual("M0HandoffAcceptanceV1", acceptance["record_type"])
        bindings = acceptance["subject"]["artifact_bindings"]
        expected_paths = {
            str(MAPPING_PATH.relative_to(REPOSITORY_ROOT)),
            str(OTEL_MAPPING_PATH.relative_to(REPOSITORY_ROOT)),
            str(HANDOFF_PATH.relative_to(REPOSITORY_ROOT)),
            str(EVIDENCE_PATH.relative_to(REPOSITORY_ROOT)),
            str(SCHEMA_BUNDLE_PATH.relative_to(REPOSITORY_ROOT)),
            str(CONTRACT_BUNDLE_PATH.relative_to(REPOSITORY_ROOT)),
            str(TARGETED_PROBE_EVIDENCE_PATH.relative_to(REPOSITORY_ROOT)),
            str(M3_PLAN_PATH.relative_to(REPOSITORY_ROOT)),
        }
        self.assertEqual(expected_paths, {item["path"] for item in bindings})
        for binding in bindings:
            self.assertEqual(
                sha256(REPOSITORY_ROOT / binding["path"]), binding["sha256"]
            )
        canonical_subject = json.dumps(
            acceptance["subject"], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(canonical_subject).hexdigest(),
            acceptance["subject_sha256"],
        )

        approval_paths = [
            REPOSITORY_ROOT / item for item in acceptance["approval_paths"]
        ]
        self.assertEqual(4, len(approval_paths))
        approvals = [read_json(path) for path in approval_paths]
        self.assertEqual(
            {"owner", "security_privacy", "test_integrity", "root_integration"},
            {item["role"] for item in approvals},
        )
        for approval in approvals:
            self.assertEqual(acceptance["subject_sha256"], approval["subject_sha256"])
        decisions = {item["role"]: item["decision"] for item in approvals}
        all_approved = all(decision == "approved" for decision in decisions.values())
        self.assertEqual("accepted" if all_approved else "blocked", acceptance["status"])
        self.assertIs(True, acceptance["structural_prerequisite_authorized"])
        self.assertIs(all_approved, acceptance["adapter_live_handoff_authorized"])

    def test_bound_schema_validates_every_handoff_record_before_authorization(
        self,
    ) -> None:
        self.assertTrue(M0_PYTHON.is_file(), "approved M0 validator is unavailable")
        result = subprocess.run(
            [str(M0_PYTHON), str(VALIDATOR_PATH), "--schema-only"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("M0/M3 bound schema: VALID", result.stdout)

    def test_m3_plan_has_narrow_non_g9_scoped_entry_amendment(self) -> None:
        normalized = " ".join(self.m3_plan.split())
        for phrase in (
            "M0-M3-CLAUDE-SCOPED-ENTRY-001",
            "does not declare M0 G9 complete",
            "Codex, Ollama, Anthropic API, OpenAI API, Ollama API, and macOS remain deferred",
            "all four detached approval roles",
            "subscription.quota",
            "local.process.account_correlation",
        ):
            self.assertIn(phrase, normalized)

    def test_validator_authorizes_the_exact_adapter_live_handoff(self) -> None:
        self.assertTrue(VALIDATOR_PATH.is_file(), "handoff validator is missing")
        result = subprocess.run(
            [str(M0_PYTHON), str(VALIDATOR_PATH)],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        acceptance = read_json(ACCEPTANCE_PATH)
        approval_paths = [
            REPOSITORY_ROOT / item for item in acceptance["approval_paths"]
        ]
        approvals = [read_json(path) for path in approval_paths]
        all_approved = all(item["decision"] == "approved" for item in approvals)
        # The ordinary validator reports structural authorization with a
        # blocked live lane; only --require-adapter-live is fail-closed.
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("ST-PROV-001 structural prerequisite: AUTHORIZED", result.stdout)
        self.assertIn(
            "M3 adapter/live handoff: AUTHORIZED" if all_approved else "M3 adapter/live handoff: BLOCKED",
            result.stdout,
        )
        self.assertIn(
            "provider/account/process/profile/network access: NOT PERFORMED",
            result.stdout,
        )

        live_result = subprocess.run(
            [str(M0_PYTHON), str(VALIDATOR_PATH), "--require-adapter-live"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            0 if all_approved else 2,
            live_result.returncode,
            live_result.stdout + live_result.stderr,
        )
        self.assertIn(
            "M3 adapter/live handoff: AUTHORIZED"
            if all_approved
            else "M3 adapter/live handoff: BLOCKED",
            live_result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
