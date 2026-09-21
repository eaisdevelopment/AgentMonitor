"""Pure policy tests for M0 per-run OperationPacketV1 preflight."""

from __future__ import annotations

import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import m0_g1_records
import m0_preflight_policy

AS_OF = datetime(2026, 9, 21, 13, 0, tzinfo=timezone.utc)
APPROVAL_TIME = "2026-09-21T12:15:00Z"
ROLES = ("owner", "security_privacy", "test_integrity", "root_integration")
REQUIRED_STOP_CODES = (
    "AUTHENTICATION_PROMPT",
    "MUTATION_OR_UPDATE_PROMPT",
    "UNEXPECTED_NETWORK",
    "UNEXPECTED_COST_OR_RATE_LIMIT",
    "PROHIBITED_DATA",
    "PATH_OR_PERMISSION_MISMATCH",
    "RUNNING_PROCESS_EFFECT",
    "SCOPE_OR_VERSION_MISMATCH",
    "UNKNOWN_BEHAVIOR",
)


def _approve(
    subject: dict[str, object], subject_id: str, roles: tuple[str, ...]
) -> None:
    digest = m0_g1_records.subject_sha256(subject)
    subject["approvals"] = [
        m0_g1_records.approval_record(
            approval_id=f"APR-{subject_id}-{role.upper().replace('_', '-')}",
            subject_id=subject_id,
            subject_digest=digest,
            role=role,
            reviewer_ref=f"REF-{role.upper().replace('_', '-')}",
            decided_at_utc=APPROVAL_TIME,
        )
        for role in roles
    ]


def _records() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    selection: dict[str, object] = {
        "external_root_ref": "REF-M0-CUSTODY-001",
        "owner_selected": True,
        "sync_backup_disposition": "excluded",
        "retention_until_utc": "2027-09-21T00:00:00Z",
    }
    custody = m0_g1_records.custody_subject(selection)
    _approve(custody, "CUST-M0-G1-001", ("owner", "security_privacy", "test_integrity"))
    packet: dict[str, object] = {
        "record_type": "OperationPacketV1",
        "schema_version": "1.0",
        "packet_id": "PKT-M0-COM-001",
        "operation_id": "OP-M0-COM-001",
        "scenario_id": "M0-COM-001",
        "custody_decision_id": "CUST-M0-G1-001",
        "finalized_at_utc": "2026-09-21T12:00:00Z",
        "expires_at_utc": "2026-09-21T14:00:00Z",
        "operation": {
            "boundary": "documentation",
            "executable_ref": "REF-REVIEWED-PROCEDURE-001",
            "arguments": [],
            "timeout_seconds": 30,
            "network_policy": "denied",
        },
        "targets": ["REF-SCOPE-001"],
        "assertions": [
            {
                "assertion_id": "AST-OBS-001",
                "kind": "presence",
                "expected": "owner-visible scope",
            },
            {
                "assertion_id": "AST-SAFE-001",
                "kind": "side_effect",
                "expected": "no mutation",
            },
        ],
        "side_effect_budget": {
            "network_requests": 0,
            "provider_requests": 0,
            "cost_minor_units": 0,
            "writes_allowed": False,
            "profile_changes_allowed": False,
            "process_signals_allowed": False,
        },
        "stop_conditions": list(REQUIRED_STOP_CODES),
        "approvals": [],
    }
    _approve(packet, "PKT-M0-COM-001", ROLES)
    return packet, custody, selection


def _violations(
    packet: object, custody: object, selection: dict[str, object]
) -> list[str]:
    return m0_preflight_policy.validate_operation_packet(
        packet=packet,
        custody_decision=custody,
        owner_selection=selection,
        as_of=AS_OF,
    )


class OperationPacketPolicyTests(unittest.TestCase):
    def test_exact_approved_non_network_packet_satisfies_pure_policy(self) -> None:
        packet, custody, selection = _records()
        self.assertEqual([], _violations(packet, custody, selection))

    def test_packet_and_custody_id_binding_fails_closed(self) -> None:
        packet, custody, selection = _records()
        packet["custody_decision_id"] = "CUST-M0-G1-999"
        self.assertIn(
            "PACKET_CUSTODY_ID_MISMATCH", _violations(packet, custody, selection)
        )
        packet["custody_decision_id"] = "CUST-M0-G1-001"
        custody["permissions_verified"] = False
        self.assertIn("CUSTODY_INVALID", _violations(packet, custody, selection))

    def test_packet_lifetime_must_be_current_and_inside_custody_retention(self) -> None:
        for field, value, expected in (
            ("finalized_at_utc", "2026-09-21T13:01:00Z", "PACKET_NOT_FINALIZED"),
            ("expires_at_utc", "2026-09-21T13:00:00Z", "PACKET_EXPIRED"),
            ("expires_at_utc", "2026-09-21T11:59:00Z", "PACKET_INVALID_INTERVAL"),
            (
                "expires_at_utc",
                "2027-09-22T00:00:00Z",
                "PACKET_EXCEEDS_CUSTODY_RETENTION",
            ),
            ("expires_at_utc", "not-a-time", "PACKET_INVALID_INTERVAL"),
        ):
            with self.subTest(field=field, value=value):
                packet, custody, selection = _records()
                packet[field] = value
                self.assertIn(expected, _violations(packet, custody, selection))

    def test_exact_detached_approvals_are_required_and_changed_bytes_invalidate_them(
        self,
    ) -> None:
        packet, custody, selection = _records()
        packet["approvals"] = packet["approvals"][:-1]
        self.assertIn(
            "PACKET_APPROVAL_INVALID", _violations(packet, custody, selection)
        )

        packet, custody, selection = _records()
        packet["operation"]["timeout_seconds"] = 31
        self.assertIn(
            "PACKET_APPROVAL_INVALID", _violations(packet, custody, selection)
        )

        packet, custody, selection = _records()
        packet["approvals"][0]["decision"] = "rejected"
        self.assertIn(
            "PACKET_APPROVAL_INVALID", _violations(packet, custody, selection)
        )

        packet, custody, selection = _records()
        packet["approvals"][0]["expires_at_utc"] = "2026-09-21T13:00:00Z"
        self.assertIn(
            "PACKET_APPROVAL_INVALID", _violations(packet, custody, selection)
        )

    def test_assertions_must_be_unique_and_complete_stop_set_mandatory(self) -> None:
        packet, custody, selection = _records()
        packet["assertions"].append(copy.deepcopy(packet["assertions"][0]))
        self.assertIn(
            "PACKET_DUPLICATE_ASSERTION", _violations(packet, custody, selection)
        )

        packet, custody, selection = _records()
        packet["stop_conditions"].remove("PROHIBITED_DATA")
        self.assertIn(
            "PACKET_STOP_SET_INCOMPLETE", _violations(packet, custody, selection)
        )

    def test_safety_assertion_cannot_be_omitted_even_with_exact_approval(self) -> None:
        packet, custody, selection = _records()
        packet["assertions"] = [packet["assertions"][0]]
        _approve(packet, "PKT-M0-COM-001", ROLES)
        self.assertIn(
            "PACKET_SAFETY_ASSERTION_MISSING", _violations(packet, custody, selection)
        )

    def test_mutation_and_cost_budgets_are_zero(self) -> None:
        for key, value in (
            ("cost_minor_units", 1),
            ("writes_allowed", True),
            ("profile_changes_allowed", True),
            ("process_signals_allowed", True),
        ):
            with self.subTest(key=key):
                packet, custody, selection = _records()
                packet["side_effect_budget"][key] = value
                self.assertIn(
                    "PACKET_MUTATION_BUDGET_NONZERO",
                    _violations(packet, custody, selection),
                )

    def test_denied_network_rejects_requests_and_hosts(self) -> None:
        packet, custody, selection = _records()
        packet["side_effect_budget"]["network_requests"] = 1
        self.assertIn(
            "PACKET_NETWORK_POLICY_MISMATCH", _violations(packet, custody, selection)
        )

        packet, custody, selection = _records()
        packet["operation"]["allowed_hosts"] = ["api.example.com"]
        self.assertIn(
            "PACKET_NETWORK_POLICY_MISMATCH", _violations(packet, custody, selection)
        )

    def test_exact_allowlist_requires_bounded_requests_and_exact_valid_hosts(
        self,
    ) -> None:
        packet, custody, selection = _records()
        packet["operation"]["network_policy"] = "exact_allowlist"
        self.assertIn(
            "PACKET_NETWORK_POLICY_MISMATCH", _violations(packet, custody, selection)
        )

        for host in (
            "*.example.com",
            "https://api.example.com",
            "api.example.com:443",
            "localhost",
            "127.0.0.1",
            "API.EXAMPLE.COM",
        ):
            with self.subTest(host=host):
                packet, custody, selection = _records()
                packet["operation"]["network_policy"] = "exact_allowlist"
                packet["operation"]["allowed_hosts"] = [host]
                packet["side_effect_budget"]["network_requests"] = 1
                self.assertIn(
                    "PACKET_NETWORK_HOST_INVALID",
                    _violations(packet, custody, selection),
                )

    def test_provider_request_count_cannot_exceed_network_request_count(self) -> None:
        packet, custody, selection = _records()
        packet["operation"]["network_policy"] = "exact_allowlist"
        packet["operation"]["allowed_hosts"] = ["api.example.com"]
        packet["side_effect_budget"]["network_requests"] = 1
        packet["side_effect_budget"]["provider_requests"] = 2
        self.assertIn(
            "PACKET_PROVIDER_BUDGET_EXCEEDS_NETWORK",
            _violations(packet, custody, selection),
        )

    def test_provider_boundary_requires_provider_system_approval(self) -> None:
        packet, custody, selection = _records()
        packet["operation"]["boundary"] = "https_api"
        packet["operation"]["network_policy"] = "exact_allowlist"
        packet["operation"]["allowed_hosts"] = ["api.example.com"]
        packet["side_effect_budget"]["network_requests"] = 1
        packet["side_effect_budget"]["provider_requests"] = 1
        _approve(packet, "PKT-M0-COM-001", ROLES)
        self.assertIn(
            "PACKET_APPROVAL_INVALID", _violations(packet, custody, selection)
        )
        _approve(packet, "PKT-M0-COM-001", ROLES + ("provider_system",))
        self.assertEqual([], _violations(packet, custody, selection))

    def test_non_schema_values_fail_closed_without_echoing_input(self) -> None:
        packet, custody, selection = _records()
        packet["assertions"] = "sensitive-value"
        violations = _violations(packet, custody, selection)
        self.assertIn("PACKET_ASSERTIONS_INVALID", violations)
        self.assertNotIn("sensitive-value", " ".join(violations))

    def test_unhashable_non_schema_values_return_codes_not_exceptions(self) -> None:
        for area, value, code in (
            ("boundary", [], "PACKET_OPERATION_INVALID"),
            ("kind", [], "PACKET_ASSERTIONS_INVALID"),
        ):
            with self.subTest(area=area):
                packet, custody, selection = _records()
                if area == "boundary":
                    packet["operation"]["boundary"] = value
                else:
                    packet["assertions"][0]["kind"] = value
                self.assertIn(code, _violations(packet, custody, selection))


if __name__ == "__main__":
    unittest.main()
