"""Pure, fail-closed policy for exact M0 OperationPacketV1 records.

This module performs no I/O and grants no execution authority. The caller must
also validate JSON Schema and verify the real custody and operation-review
records before a live preflight can pass.
"""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone

import m0_g1_records

MANDATORY_STOP_CONDITIONS = frozenset(
    {
        "AUTHENTICATION_PROMPT",
        "MUTATION_OR_UPDATE_PROMPT",
        "UNEXPECTED_NETWORK",
        "UNEXPECTED_COST_OR_RATE_LIMIT",
        "PROHIBITED_DATA",
        "PATH_OR_PERMISSION_MISMATCH",
        "RUNNING_PROCESS_EFFECT",
        "SCOPE_OR_VERSION_MISMATCH",
        "UNKNOWN_BEHAVIOR",
    }
)

_PACKET_KEYS = {
    "record_type",
    "schema_version",
    "packet_id",
    "operation_id",
    "scenario_id",
    "custody_decision_id",
    "finalized_at_utc",
    "expires_at_utc",
    "operation",
    "targets",
    "assertions",
    "side_effect_budget",
    "stop_conditions",
    "approvals",
}
_OPERATION_KEYS = {
    "boundary",
    "executable_ref",
    "arguments",
    "timeout_seconds",
    "network_policy",
}
_BUDGET_KEYS = {
    "network_requests",
    "provider_requests",
    "cost_minor_units",
    "writes_allowed",
    "profile_changes_allowed",
    "process_signals_allowed",
}
_BOUNDARIES = {
    "documentation",
    "filesystem",
    "process",
    "provider_cli",
    "https_api",
    "os_api",
}
_ASSERTION_KINDS = {
    "presence",
    "absence",
    "equality",
    "range",
    "containment",
    "side_effect",
}
_PACKET_ID = re.compile(r"PKT-[A-Z0-9-]+\Z")
_OPERATION_ID = re.compile(r"OP-[A-Z0-9-]+\Z")
_SCENARIO_ID = re.compile(r"M0-[A-Z0-9-]+-[0-9]{3}\Z")
_CUSTODY_ID = re.compile(r"CUST-[A-Z0-9-]+\Z")
_REFERENCE_ID = re.compile(r"REF-[A-Z0-9-]+\Z")
_ASSERTION_ID = re.compile(r"AST-[A-Z0-9-]+\Z")
_DNS_HOST = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+\Z"
)


def _matches(pattern: re.Pattern[str], value: object) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _utc_instant(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    return parsed if parsed.tzinfo == timezone.utc else None


def _host_is_exact_dns(value: object) -> bool:
    if (
        not isinstance(value, str)
        or len(value) > 253
        or _DNS_HOST.fullmatch(value) is None
    ):
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return True
    return False


def _approval_inputs_safe(approvals: object) -> bool:
    """Guard the existing approval validator against non-schema Python values."""

    return isinstance(approvals, list) and all(
        isinstance(item, dict)
        and isinstance(item.get("role"), str)
        and isinstance(item.get("approval_id"), str)
        for item in approvals
    )


def _custody_is_valid(
    custody_decision: object,
    owner_selection: dict[str, object],
    as_of: datetime,
) -> bool:
    if not isinstance(custody_decision, dict):
        return False
    if not _approval_inputs_safe(custody_decision.get("approvals")):
        return False
    try:
        return not m0_g1_records.validate_custody_decision(
            decision=custody_decision,
            selection=owner_selection,
            as_of=as_of,
        )
    except (TypeError, ValueError):
        return False


def _packet_approvals_valid(
    packet: dict[str, object], required_roles: set[str], as_of: datetime
) -> bool:
    approvals = packet.get("approvals")
    if not _approval_inputs_safe(approvals):
        return False
    try:
        return not m0_g1_records.validate_approval_set(
            subject=packet,
            subject_id=str(packet["packet_id"]),
            approvals=approvals,
            required_roles=required_roles,
            as_of=as_of,
        )
    except (TypeError, ValueError):
        return False


def _append(violations: list[str], code: str) -> None:
    if code not in violations:
        violations.append(code)


def validate_operation_packet(
    *,
    packet: object,
    custody_decision: object,
    owner_selection: dict[str, object],
    as_of: datetime,
) -> list[str]:
    """Return fixed safe violation codes; an empty list is pure-policy only.

    ``as_of`` is supplied by the caller so policy tests use no clock or I/O.
    Owner selection must be independently obtained, not inferred from custody.
    """

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if not isinstance(packet, dict):
        return ["PACKET_SHAPE_INVALID"]
    violations: list[str] = []
    if (
        set(packet) != _PACKET_KEYS
        or packet.get("record_type") != "OperationPacketV1"
        or packet.get("schema_version") != "1.0"
    ):
        _append(violations, "PACKET_SHAPE_INVALID")
    if not all(
        (
            _matches(_PACKET_ID, packet.get("packet_id")),
            _matches(_OPERATION_ID, packet.get("operation_id")),
            _matches(_SCENARIO_ID, packet.get("scenario_id")),
            _matches(_CUSTODY_ID, packet.get("custody_decision_id")),
        )
    ):
        _append(violations, "PACKET_ID_INVALID")

    if not _custody_is_valid(custody_decision, owner_selection, as_of):
        _append(violations, "CUSTODY_INVALID")
    if not isinstance(custody_decision, dict) or packet.get(
        "custody_decision_id"
    ) != custody_decision.get("decision_id"):
        _append(violations, "PACKET_CUSTODY_ID_MISMATCH")

    finalized = _utc_instant(packet.get("finalized_at_utc"))
    expires = _utc_instant(packet.get("expires_at_utc"))
    if finalized is None or expires is None or finalized >= expires:
        _append(violations, "PACKET_INVALID_INTERVAL")
    else:
        if finalized > as_of:
            _append(violations, "PACKET_NOT_FINALIZED")
        if expires <= as_of:
            _append(violations, "PACKET_EXPIRED")
        custody_retention = _utc_instant(
            custody_decision.get("retention_until_utc")
            if isinstance(custody_decision, dict)
            else None
        )
        if custody_retention is None or expires > custody_retention:
            _append(violations, "PACKET_EXCEEDS_CUSTODY_RETENTION")

    operation = packet.get("operation")
    boundary: object = None
    if not isinstance(operation, dict) or not _OPERATION_KEYS <= set(
        operation
    ) <= _OPERATION_KEYS | {"allowed_hosts"}:
        _append(violations, "PACKET_OPERATION_INVALID")
    else:
        boundary = operation.get("boundary")
        args = operation.get("arguments")
        timeout = operation.get("timeout_seconds")
        if (
            not isinstance(boundary, str)
            or boundary not in _BOUNDARIES
            or not _matches(_REFERENCE_ID, operation.get("executable_ref"))
            or not isinstance(args, list)
            or len(args) > 32
            or not all(isinstance(arg, str) and len(arg) <= 512 for arg in args)
            or type(timeout) is not int
            or not 1 <= timeout <= 300
        ):
            _append(violations, "PACKET_OPERATION_INVALID")

    targets = packet.get("targets")
    if (
        not isinstance(targets, list)
        or not 1 <= len(targets) <= 32
        or not all(_matches(_REFERENCE_ID, target) for target in targets)
        or len(targets) != len(set(targets))
    ):
        _append(violations, "PACKET_TARGETS_INVALID")

    assertions = packet.get("assertions")
    if not isinstance(assertions, list) or not 1 <= len(assertions) <= 64:
        _append(violations, "PACKET_ASSERTIONS_INVALID")
    else:
        assertion_ids: list[str] = []
        has_safety_assertion = False
        for assertion in assertions:
            if not isinstance(assertion, dict) or set(assertion) != {
                "assertion_id",
                "kind",
                "expected",
            }:
                _append(violations, "PACKET_ASSERTIONS_INVALID")
                continue
            assertion_id = assertion.get("assertion_id")
            expected = assertion.get("expected")
            if (
                not _matches(_ASSERTION_ID, assertion_id)
                or not isinstance(assertion.get("kind"), str)
                or assertion.get("kind") not in _ASSERTION_KINDS
                or not isinstance(expected, str)
                or not 1 <= len(expected) <= 256
            ):
                _append(violations, "PACKET_ASSERTIONS_INVALID")
            if isinstance(assertion_id, str):
                assertion_ids.append(assertion_id)
            if assertion.get("kind") == "side_effect":
                has_safety_assertion = True
        if len(assertion_ids) != len(set(assertion_ids)):
            _append(violations, "PACKET_DUPLICATE_ASSERTION")
        if not has_safety_assertion:
            _append(violations, "PACKET_SAFETY_ASSERTION_MISSING")

    stop_conditions = packet.get("stop_conditions")
    if (
        not isinstance(stop_conditions, list)
        or not all(isinstance(code, str) for code in stop_conditions)
        or set(stop_conditions) != MANDATORY_STOP_CONDITIONS
        or len(stop_conditions) != len(MANDATORY_STOP_CONDITIONS)
    ):
        _append(violations, "PACKET_STOP_SET_INCOMPLETE")

    budget = packet.get("side_effect_budget")
    network_requests: int | None = None
    provider_requests: int | None = None
    if not isinstance(budget, dict) or set(budget) != _BUDGET_KEYS:
        _append(violations, "PACKET_BUDGET_INVALID")
    else:
        network = budget.get("network_requests")
        provider = budget.get("provider_requests")
        if type(network) is int and 0 <= network <= 20:
            network_requests = network
        else:
            _append(violations, "PACKET_BUDGET_INVALID")
        if type(provider) is int and 0 <= provider <= 20:
            provider_requests = provider
        else:
            _append(violations, "PACKET_BUDGET_INVALID")
        if (
            type(budget.get("cost_minor_units")) is not int
            or budget.get("cost_minor_units") != 0
            or budget.get("writes_allowed") is not False
            or budget.get("profile_changes_allowed") is not False
            or budget.get("process_signals_allowed") is not False
        ):
            _append(violations, "PACKET_MUTATION_BUDGET_NONZERO")
        if (
            network_requests is not None
            and provider_requests is not None
            and provider_requests > network_requests
        ):
            _append(violations, "PACKET_PROVIDER_BUDGET_EXCEEDS_NETWORK")

    if isinstance(operation, dict):
        policy = operation.get("network_policy")
        hosts = operation.get("allowed_hosts", [])
        if policy == "denied":
            if hosts != [] or network_requests != 0 or provider_requests != 0:
                _append(violations, "PACKET_NETWORK_POLICY_MISMATCH")
        elif policy == "exact_allowlist":
            if (
                not isinstance(hosts, list)
                or not hosts
                or network_requests is None
                or network_requests == 0
            ):
                _append(violations, "PACKET_NETWORK_POLICY_MISMATCH")
            if (
                not isinstance(hosts, list)
                or len(hosts) != len({host for host in hosts if isinstance(host, str)})
                or not all(_host_is_exact_dns(host) for host in hosts)
            ):
                _append(violations, "PACKET_NETWORK_HOST_INVALID")
        else:
            _append(violations, "PACKET_NETWORK_POLICY_MISMATCH")
        if boundary == "https_api" and (
            policy != "exact_allowlist"
            or provider_requests is None
            or provider_requests == 0
        ):
            _append(violations, "PACKET_NETWORK_POLICY_MISMATCH")

    required_roles = {"owner", "security_privacy", "test_integrity", "root_integration"}
    if isinstance(boundary, str) and boundary in {"provider_cli", "https_api"}:
        required_roles.add("provider_system")
    if not _packet_approvals_valid(packet, required_roles, as_of):
        _append(violations, "PACKET_APPROVAL_INVALID")
    return violations
