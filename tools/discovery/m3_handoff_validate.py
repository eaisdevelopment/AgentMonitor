#!/usr/bin/env python3
"""Fail-closed validation for the scoped M0-to-M3 Claude handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_ROOT = REPOSITORY_ROOT / "docs/discovery/m0"
ACCEPTANCE_PATH = DISCOVERY_ROOT / "m3-handoff-acceptance-v1.json"
MAPPING_PATH = DISCOVERY_ROOT / "m0-to-m03-claude-v1.json"
OTEL_MAPPING_PATH = DISCOVERY_ROOT / "m0-to-m03-claude-otel-v1.json"
EVIDENCE_PATH = DISCOVERY_ROOT / "m3-claude-evidence-v1.json"
SCHEMA_BUNDLE_PATH = DISCOVERY_ROOT / "m3-handoff-schema-bundle-v1.json"
CONTRACT_BUNDLE_PATH = DISCOVERY_ROOT / "m3-ctr-prov-002-contract-bundle-v1.json"
SCHEMA_PATH = DISCOVERY_ROOT / "m3-handoff-record.schema.json"
EXPECTED_JSONSCHEMA_VERSION = "4.26.0"
MAX_RECORD_BYTES = 1_048_576
REQUIRED_ROLES = {
    "owner",
    "security_privacy",
    "test_integrity",
    "root_integration",
}
EXPECTED_BOUNDARY = {
    "authorized_work": "V1-M3-exact-Claude-quota-and-OTLP-live-slice",
    "provider_io_authorized": True,
    "adapter_or_live_work_authorized": True,
    "later_m3_tasks_authorized": True,
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
        raise ValidationError(
            f"artifact is not a regular repository file: {relative_path}"
        )
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValidationError(
            f"record is not a regular file: {path.relative_to(REPOSITORY_ROOT)}"
        )
    raw = path.read_bytes()
    if len(raw) > MAX_RECORD_BYTES:
        raise ValidationError(f"record exceeds {MAX_RECORD_BYTES} bytes")
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(
            f"invalid JSON: {path.relative_to(REPOSITORY_ROOT)}"
        ) from exc
    if not isinstance(value, dict):
        raise ValidationError(
            f"record must be a JSON object: {path.relative_to(REPOSITORY_ROOT)}"
        )
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_bound_schema(records: tuple[dict[str, Any], ...]) -> None:
    try:
        installed = version("jsonschema")
    except PackageNotFoundError as exc:
        raise ValidationError("approved jsonschema dependency is unavailable") from exc
    if installed != EXPECTED_JSONSCHEMA_VERSION:
        raise ValidationError("approved jsonschema dependency version mismatch")
    schema = _read_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValidationError("bound handoff schema is invalid") from exc
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for record in records:
        errors = tuple(validator.iter_errors(record))
        if errors:
            record_type = record.get("record_type", "unknown")
            raise ValidationError(f"bound schema rejected record: {record_type}")


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


def _validate_structural_records() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, str]
]:
    acceptance = _read_json(ACCEPTANCE_PATH)
    mapping = _read_json(MAPPING_PATH)
    otel_mapping = _read_json(OTEL_MAPPING_PATH)
    evidence = _read_json(EVIDENCE_PATH)
    schema_bundle = _read_json(SCHEMA_BUNDLE_PATH)
    contract_bundle = _read_json(CONTRACT_BUNDLE_PATH)

    approval_paths = acceptance.get("approval_paths")
    if not isinstance(approval_paths, list) or len(approval_paths) != 4:
        raise ValidationError("exactly four detached approvals are required")
    approvals = tuple(
        _read_json(_repository_file(relative_path))
        for relative_path in approval_paths
        if isinstance(relative_path, str)
    )
    if len(approvals) != 4:
        raise ValidationError("approval path must be text")
    _validate_bound_schema(
        (
            acceptance,
            mapping,
            otel_mapping,
            evidence,
            schema_bundle,
            contract_bundle,
            *approvals,
        )
    )

    if acceptance.get("record_type") != "M0HandoffAcceptanceV1":
        raise ValidationError("unexpected acceptance record type")
    if acceptance.get("structural_prerequisite_authorized") is not True:
        raise ValidationError("structural authorization flag is not true")
    live_authorized = acceptance.get("adapter_live_handoff_authorized")
    expected_status = "accepted" if live_authorized is True else "blocked"
    if acceptance.get("status") != expected_status:
        raise ValidationError("acceptance status and live authorization disagree")

    subject = acceptance.get("subject")
    if not isinstance(subject, dict):
        raise ValidationError("acceptance subject is missing")
    if subject.get("authorization_boundary") != EXPECTED_BOUNDARY:
        raise ValidationError("authorization boundary is not the approved live scope")
    canonical_subject = json.dumps(
        subject, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    subject_digest = hashlib.sha256(canonical_subject).hexdigest()
    if acceptance.get("subject_sha256") != subject_digest:
        raise ValidationError("acceptance subject digest mismatch")
    _validate_bindings(subject.get("artifact_bindings"))

    decisions: dict[str, str] = {}
    for approval in approvals:
        role = approval.get("role")
        decision = approval.get("decision")
        if role not in REQUIRED_ROLES or role in decisions:
            raise ValidationError("approval roles are missing or duplicated")
        if approval.get("subject_sha256") != subject_digest:
            raise ValidationError(f"stale approval subject digest: {role}")
        if decision not in {"approved", "pending", "rejected"}:
            raise ValidationError(f"invalid approval decision: {role}")
        decisions[role] = decision
    if set(decisions) != REQUIRED_ROLES:
        raise ValidationError("detached approval roles are incomplete")

    if mapping.get("record_type") != "M0ToM03CapabilityMappingV1":
        raise ValidationError("unexpected capability mapping record type")
    if (
        otel_mapping.get("record_type") != "M0ToM03OtelCapabilityMappingV1"
        or otel_mapping.get("mapping_id") != "M0-M03-CLAUDE-OTEL-001"
        or otel_mapping.get("status") != "approved"
        or otel_mapping.get("source_id") != "claude.otel.metrics.http-json.v1"
    ):
        raise ValidationError("OTEL mapping is missing, stale, or unaccepted")
    targeted_probe = otel_mapping.get("targeted_profile_probe")
    if not isinstance(targeted_probe, dict):
        raise ValidationError("targeted OTEL probe binding is missing")
    probe_path = targeted_probe.get("repository_evidence")
    probe_digest = targeted_probe.get("repository_evidence_sha256")
    if not isinstance(probe_path, str) or not isinstance(probe_digest, str):
        raise ValidationError("targeted OTEL probe binding is malformed")
    if _sha256(_repository_file(probe_path)) != probe_digest:
        raise ValidationError("targeted OTEL probe digest mismatch")
    mapping_binding = mapping.get("contract_binding")
    if not isinstance(mapping_binding, dict):
        raise ValidationError("mapping contract binding is missing")
    if mapping_binding.get("bundle_sha256") != _sha256(CONTRACT_BUNDLE_PATH):
        raise ValidationError("mapping contract-bundle digest mismatch")
    schema_binding = mapping.get("schema_binding")
    if not isinstance(schema_binding, dict):
        raise ValidationError("mapping schema-bundle binding is missing")
    if schema_binding.get("bundle_sha256") != _sha256(SCHEMA_BUNDLE_PATH):
        raise ValidationError("mapping schema-bundle digest mismatch")
    _validate_bindings(schema_bundle.get("artifacts"))
    if contract_bundle.get("contract_id") != "CTR-PROV-002":
        raise ValidationError("unexpected provider contract identifier")
    _validate_bindings(contract_bundle.get("normative_artifacts"))
    schema_artifact = contract_bundle.get("schema_artifact")
    if contract_bundle.get("schema_artifact_status") == "current":
        _validate_bindings([schema_artifact])
        if not isinstance(schema_artifact, dict) or (
            mapping_binding.get("schema_sha256") != schema_artifact.get("sha256")
        ):
            raise ValidationError("mapping schema-artifact digest mismatch")

    return acceptance, contract_bundle, decisions


def _technical_blockers(
    contract_bundle: dict[str, Any],
) -> list[str]:
    """Return only evidence blockers for the local technical release lane.

    Detached reviewer records are governance evidence, not a runtime
    prerequisite.  Keeping this list separate prevents a pending review
    document from stopping a real provider/browser verification run.
    """
    blockers: list[str] = []
    capabilities = {
        item.get("capability_id"): item
        for item in _read_json(MAPPING_PATH).get("capabilities", [])
        if isinstance(item, dict)
    }
    correlation = capabilities.get("local.process.account_correlation", {})
    if correlation.get("targeted_profile_probe_status") != "Passed":
        blockers.append("same_account_targeted_probe_not_run")
    if correlation.get("mapping_ref") != "M0-M03-CLAUDE-OTEL-001":
        blockers.append("same_account_otel_mapping_unbound")
    if (
        contract_bundle.get("schema_artifact_status") != "current"
        or contract_bundle.get("schema_artifact") is None
    ):
        blockers.append("ctr_prov_002_schema_missing")
    return blockers


def _live_blockers(
    acceptance: dict[str, Any],
    contract_bundle: dict[str, Any],
    decisions: dict[str, str],
) -> list[str]:
    blockers = _technical_blockers(contract_bundle)
    for role in ("owner", "security_privacy", "test_integrity", "root_integration"):
        if decisions.get(role) != "approved":
            blockers.append(f"{role}_approval_{decisions.get(role, 'missing')}")
    if acceptance.get("adapter_live_handoff_authorized") is not True:
        blockers.append("adapter_live_handoff_not_authorized")
    return blockers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    live_group = parser.add_mutually_exclusive_group()
    live_group.add_argument(
        "--require-adapter-live",
        action="store_true",
        help="strict governance mode; require every detached approval",
    )
    live_group.add_argument(
        "--require-technical-live",
        action="store_true",
        help="local release mode; require technical evidence, not detached approvals",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="validate every bound handoff record against the approved schema",
    )
    args = parser.parse_args(argv)

    try:
        acceptance, contract_bundle, decisions = _validate_structural_records()
        if args.schema_only:
            print("M0/M3 bound schema: VALID")
            return 0
        blockers = _live_blockers(acceptance, contract_bundle, decisions)
        technical_blockers = _technical_blockers(contract_bundle)
        recorded_blockers = acceptance.get("blockers")
        if recorded_blockers != blockers:
            raise ValidationError(
                "recorded live blockers do not match derived blockers"
            )
    except (OSError, ValidationError) as exc:
        print("ST-PROV-001 structural prerequisite: BLOCKED")
        print(f"- {exc}")
        print("provider/account/process/profile/network access: NOT PERFORMED")
        return 2

    print("ST-PROV-001 structural prerequisite: AUTHORIZED")
    if args.require_technical_live:
        if technical_blockers:
            print("M3 technical handoff: BLOCKED")
            for blocker in technical_blockers:
                print(f"- {blocker}")
            print(
                "M3 governance approvals: ADVISORY / NOT REQUIRED BY LOCAL RELEASE POLICY"
            )
            print("provider/account/process/profile/network access: NOT PERFORMED")
            return 2
        print("M3 technical handoff: AUTHORIZED (local owner release policy)")
        print(
            "M3 governance approvals: ADVISORY / NOT REQUIRED BY LOCAL RELEASE POLICY"
        )
        print("provider/account/process/profile/network access: NOT PERFORMED")
        return 0
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
