#!/usr/bin/env python3
"""Fail-closed validation for the scoped M0-to-M3 Claude handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_ROOT = REPOSITORY_ROOT / "docs/discovery/m0"
ACCEPTANCE_PATH = DISCOVERY_ROOT / "m3-handoff-acceptance-v1.json"
MAPPING_PATH = DISCOVERY_ROOT / "m0-to-m03-claude-v1.json"
CONTRACT_BUNDLE_PATH = DISCOVERY_ROOT / "m3-ctr-prov-002-contract-bundle-v1.json"
MAX_RECORD_BYTES = 1_048_576
REQUIRED_ROLES = {
    "owner",
    "security_privacy",
    "test_integrity",
    "root_integration",
}
EXPECTED_BOUNDARY = {
    "authorized_work": "ST-PROV-001-pure-provider-neutral-protocol-only",
    "provider_io_authorized": False,
    "adapter_or_live_work_authorized": False,
    "later_m3_tasks_authorized": False,
}


class ValidationError(ValueError):
    """A handoff record is absent, ambiguous, stale, or inconsistent."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _repository_file(relative_path: str) -> Path:
    candidate = REPOSITORY_ROOT / relative_path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(REPOSITORY_ROOT.resolve())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise ValidationError(f"invalid repository artifact: {relative_path}") from exc
    if candidate.is_symlink() or not resolved.is_file():
        raise ValidationError(f"artifact is not a regular repository file: {relative_path}")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValidationError(f"record is not a regular file: {path.relative_to(REPOSITORY_ROOT)}")
    raw = path.read_bytes()
    if len(raw) > MAX_RECORD_BYTES:
        raise ValidationError(f"record exceeds {MAX_RECORD_BYTES} bytes")
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON: {path.relative_to(REPOSITORY_ROOT)}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"record must be a JSON object: {path.relative_to(REPOSITORY_ROOT)}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_bindings(bindings: Any) -> None:
    if not isinstance(bindings, list) or not bindings:
        raise ValidationError("artifact bindings are missing")
    paths: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
            raise ValidationError("malformed artifact binding")
        relative_path = binding["path"]
        expected_digest = binding["sha256"]
        if not isinstance(relative_path, str) or relative_path in paths:
            raise ValidationError("duplicate or malformed artifact path")
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            raise ValidationError(f"malformed digest for {relative_path}")
        if _sha256(_repository_file(relative_path)) != expected_digest:
            raise ValidationError(f"artifact digest mismatch: {relative_path}")
        paths.add(relative_path)


def _validate_structural_records() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    acceptance = _read_json(ACCEPTANCE_PATH)
    mapping = _read_json(MAPPING_PATH)
    contract_bundle = _read_json(CONTRACT_BUNDLE_PATH)

    if acceptance.get("record_type") != "M0HandoffAcceptanceV1":
        raise ValidationError("unexpected acceptance record type")
    if acceptance.get("status") != "structural_prerequisite_authorized":
        raise ValidationError("structural prerequisite is not authorized")
    if acceptance.get("structural_prerequisite_authorized") is not True:
        raise ValidationError("structural authorization flag is not true")
    if acceptance.get("adapter_live_handoff_authorized") is not False:
        raise ValidationError("adapter/live authorization must remain false")

    subject = acceptance.get("subject")
    if not isinstance(subject, dict):
        raise ValidationError("acceptance subject is missing")
    if subject.get("authorization_boundary") != EXPECTED_BOUNDARY:
        raise ValidationError("authorization boundary is not the approved pure scope")
    canonical_subject = json.dumps(
        subject, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    subject_digest = hashlib.sha256(canonical_subject).hexdigest()
    if acceptance.get("subject_sha256") != subject_digest:
        raise ValidationError("acceptance subject digest mismatch")
    _validate_bindings(subject.get("artifact_bindings"))

    approval_paths = acceptance.get("approval_paths")
    if not isinstance(approval_paths, list) or len(approval_paths) != 4:
        raise ValidationError("exactly four detached approvals are required")
    decisions: dict[str, str] = {}
    for relative_path in approval_paths:
        if not isinstance(relative_path, str):
            raise ValidationError("approval path must be text")
        approval = _read_json(_repository_file(relative_path))
        role = approval.get("role")
        decision = approval.get("decision")
        if role not in REQUIRED_ROLES or role in decisions:
            raise ValidationError("approval roles are missing or duplicated")
        if approval.get("subject_sha256") != subject_digest:
            raise ValidationError(f"stale approval subject digest: {role}")
        if decision not in {"approved", "pending", "rejected"}:
            raise ValidationError(f"invalid approval decision: {role}")
        decisions[role] = decision
    if set(decisions) != REQUIRED_ROLES or decisions["owner"] != "approved":
        raise ValidationError("owner approval or detached roles are incomplete")

    if mapping.get("record_type") != "M0ToM03CapabilityMappingV1":
        raise ValidationError("unexpected capability mapping record type")
    mapping_binding = mapping.get("contract_binding")
    if not isinstance(mapping_binding, dict):
        raise ValidationError("mapping contract binding is missing")
    if mapping_binding.get("bundle_sha256") != _sha256(CONTRACT_BUNDLE_PATH):
        raise ValidationError("mapping contract-bundle digest mismatch")
    if contract_bundle.get("contract_id") != "CTR-PROV-002":
        raise ValidationError("unexpected provider contract identifier")
    _validate_bindings(contract_bundle.get("normative_artifacts"))

    return acceptance, contract_bundle, decisions


def _live_blockers(
    acceptance: dict[str, Any],
    contract_bundle: dict[str, Any],
    decisions: dict[str, str],
) -> list[str]:
    blockers: list[str] = []
    capabilities = {
        item.get("capability_id"): item
        for item in _read_json(MAPPING_PATH).get("capabilities", [])
        if isinstance(item, dict)
    }
    correlation = capabilities.get("local.process.account_correlation", {})
    if correlation.get("targeted_profile_probe_status") != "Passed":
        blockers.append("same_account_targeted_probe_not_run")
    if (
        contract_bundle.get("schema_artifact_status") != "current"
        or contract_bundle.get("schema_artifact") is None
    ):
        blockers.append("ctr_prov_002_schema_missing")
    for role in ("security_privacy", "test_integrity", "root_integration"):
        if decisions.get(role) != "approved":
            blockers.append(f"{role}_approval_{decisions.get(role, 'missing')}")
    if acceptance.get("adapter_live_handoff_authorized") is not True and not blockers:
        blockers.append("adapter_live_handoff_not_authorized")
    return blockers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-adapter-live",
        action="store_true",
        help="fail unless the complete adapter/live handoff is authorized",
    )
    args = parser.parse_args(argv)

    try:
        acceptance, contract_bundle, decisions = _validate_structural_records()
        blockers = _live_blockers(acceptance, contract_bundle, decisions)
        recorded_blockers = acceptance.get("blockers")
        if recorded_blockers != blockers:
            raise ValidationError("recorded live blockers do not match derived blockers")
    except (OSError, ValidationError) as exc:
        print("ST-PROV-001 structural prerequisite: BLOCKED")
        print(f"- {exc}")
        print("provider/account/process/profile/network access: NOT PERFORMED")
        return 2

    print("ST-PROV-001 structural prerequisite: AUTHORIZED")
    if blockers:
        print("M3 adapter/live handoff: BLOCKED")
        for blocker in blockers:
            print(f"- {blocker}")
    else:
        print("M3 adapter/live handoff: AUTHORIZED")
    print("provider/account/process/profile/network access: NOT PERFORMED")
    return 2 if args.require_adapter_live and blockers else 0


if __name__ == "__main__":
    sys.exit(main())
