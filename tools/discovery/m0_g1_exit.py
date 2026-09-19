"""Fail-closed Milestone 0 G1 exit gate.

The no-argument repository routine validates implementation authority, the
isolated schema environment, and one bounded local scanner operation. It never
accesses provider, account, process, profile, or external-custody state.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
import tomllib
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from m0_g1_bundle import bundle_subject, scanner_subject
from m0_g1_records import (
    validate_approval_set,
    validate_custody_decision,
)
from m0_g1_scanner import verify_e1_scanner


APPROVAL_PATH = Path(
    "docs/plans/discovery/m0-g1-implementation-approval.toml"
)
SCHEMA_PATH = Path("docs/plans/discovery/m0-g1-record.schema.json")
LOCAL_CUSTODY_SELECTION_PATH = Path(
    ".agentmonitor-local/m0-g1-custody.toml"
)
LOCAL_FINAL_APPROVAL_PATH = Path(".agentmonitor-local/m0-g1-exit.json")
CUSTODY_DECISION_FILENAME = "m0-g1-custody-decision.json"
EXPECTED_CONTRACT_ID = "M0-G1-CONTROLS"
EXPECTED_CONTRACT_VERSION = "0.3.0-draft"
EXPECTED_JSONSCHEMA_VERSION = "4.26.0"
DENIED_AUTHORITY_FLAGS = (
    "evidence_root_access_authorized",
    "provider_operations_authorized",
    "account_access_authorized",
    "g1_complete",
    "g2_authorized",
)
REQUIRED_AUTHORITY_FLAGS = (
    "implementation_authorized",
    "dependency_installation_authorized",
    "scanner_execution_authorized",
)
UTC_Z_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z"
)
FINAL_APPROVAL_KEYS = {
    "record_version",
    "external_custody_record_access_authorized",
    "custody_decision_filename",
    "custody_decision_sha256",
    "scanner_admission",
    "bundle_subject",
    "bundle_approvals",
}
CUSTODY_APPROVAL_ROLES = {"owner", "security_privacy", "test_integrity"}
BUNDLE_APPROVAL_ROLES = {
    "owner",
    "security_privacy",
    "test_integrity",
    "provider_system",
    "root_integration",
}
MAX_CONTROL_RECORD_BYTES = 262_144


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_implementation_approval(repository_root: Path) -> list[str]:
    """Validate the exact owner-approved contract without expanding authority."""

    approval_path = repository_root / APPROVAL_PATH
    try:
        with approval_path.open("rb") as stream:
            approval = tomllib.load(stream)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError) as error:
        return [f"implementation approval cannot be loaded: {error}"]

    violations: list[str] = []
    if approval.get("schema_version") != "1.0":
        violations.append("implementation approval schema must be 1.0")
    if approval.get("status") != "approved_for_implementation":
        violations.append("implementation is not owner-approved")
    if approval.get("contract_id") != EXPECTED_CONTRACT_ID:
        violations.append("implementation approval names the wrong contract")
    if approval.get("contract_version") != EXPECTED_CONTRACT_VERSION:
        violations.append("implementation approval names the wrong contract version")
    for flag in REQUIRED_AUTHORITY_FLAGS:
        if approval.get(flag) is not True:
            violations.append(f"{flag} must be true")
    for flag in DENIED_AUTHORITY_FLAGS:
        if approval.get(flag) is not False:
            violations.append(f"{flag} must remain false")

    for prefix in ("specification", "schema"):
        relative_path = approval.get(f"{prefix}_path")
        if not isinstance(relative_path, str) or not relative_path:
            violations.append(f"{prefix} path is missing")
            continue
        path = repository_root / relative_path
        try:
            content = path.read_bytes()
        except OSError as error:
            violations.append(f"{prefix} cannot be loaded: {error}")
            continue
        if approval.get(f"{prefix}_sha256") != _sha256(content):
            violations.append(f"{prefix} SHA-256 does not match approval")
        if approval.get(f"{prefix}_bytes") != len(content):
            violations.append(f"{prefix} byte count does not match approval")
    return violations


def installed_jsonschema_version() -> str | None:
    """Return package metadata only; do not import or execute the dependency."""

    try:
        return version("jsonschema")
    except PackageNotFoundError:
        return None


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _iter_references(value: object):
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            yield reference
        for child in value.values():
            yield from _iter_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_references(child)


def validate_schema_contract(repository_root: Path) -> list[str]:
    """Validate the exact repository schema with the admitted local package."""

    if installed_jsonschema_version() != EXPECTED_JSONSCHEMA_VERSION:
        return ["schema validator dependency version does not match admission"]
    schema_path = repository_root / SCHEMA_PATH
    try:
        schema = json.loads(
            schema_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        return [f"schema cannot be loaded safely: {error}"]
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        return ["schema must declare Draft 2020-12"]
    if any(not reference.startswith("#/") for reference in _iter_references(schema)):
        return ["schema contains a non-local reference"]

    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        return [f"schema metaschema validation failed at {list(error.path)}"]
    return []


def is_utc_z_timestamp(value: object) -> bool:
    """Accept a calendar-valid RFC 3339-style timestamp only in UTC-Z form."""

    if not isinstance(value, str) or UTC_Z_TIMESTAMP.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError:
        return False
    return parsed.tzinfo == timezone.utc


def verify_custody_root(path: Path, repository_root: Path) -> list[str]:
    """Perform read-only OS checks on one explicitly supplied custody root."""

    violations: list[str] = []
    if not path.is_absolute():
        return ["custody root must be an absolute path"]
    try:
        metadata = path.lstat()
    except OSError:
        return ["custody root is unavailable"]
    if stat.S_ISLNK(metadata.st_mode):
        return ["custody root must not be a symbolic link"]
    if not stat.S_ISDIR(metadata.st_mode):
        violations.append("custody root must be a directory")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        violations.append("custody root must be owned by the current user")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        violations.append("custody root permissions are not owner-only")
    try:
        resolved_root = path.resolve(strict=True)
        resolved_repository = repository_root.resolve(strict=True)
    except OSError:
        violations.append("custody root containment cannot be resolved")
        return violations
    if (
        resolved_root == resolved_repository
        or resolved_repository in resolved_root.parents
        or resolved_root in resolved_repository.parents
    ):
        violations.append("custody root must be outside the repository")
    return violations


def validate_local_custody_selection(repository_root: Path) -> list[str]:
    """Validate owner-supplied local custody metadata without listing contents."""

    selection_path = repository_root / LOCAL_CUSTODY_SELECTION_PATH
    try:
        metadata = selection_path.lstat()
    except FileNotFoundError:
        return ["owner custody selection is not configured"]
    except OSError:
        return ["owner custody selection is unavailable"]
    if not stat.S_ISREG(metadata.st_mode) or selection_path.is_symlink():
        return ["owner custody selection must be a regular non-symlink file"]
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        return ["owner custody selection must belong to the current user"]
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        return ["owner custody selection permissions are not owner-only"]
    try:
        with selection_path.open("rb") as stream:
            selection = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        return ["owner custody selection cannot be parsed"]

    violations: list[str] = []
    if selection.get("schema_version") != "1.0":
        violations.append("custody selection schema must be 1.0")
    if selection.get("owner_selected") is not True:
        violations.append("custody selection is not owner-confirmed")
    external_root_ref = selection.get("external_root_ref")
    if not isinstance(external_root_ref, str) or re.fullmatch(
        r"REF-[A-Z0-9-]+", external_root_ref
    ) is None:
        violations.append("custody selection reference is invalid")
    if selection.get("sync_backup_disposition") not in {
        "excluded",
        "owner_accepted_encrypted",
    }:
        violations.append("custody sync/backup disposition is not accepted")
    retention = selection.get("retention_until_utc")
    if not is_utc_z_timestamp(retention):
        violations.append("custody retention deadline is not a UTC-Z timestamp")
    elif datetime.fromisoformat(f"{retention[:-1]}+00:00") <= datetime.now(
        timezone.utc
    ):
        violations.append("custody retention deadline has expired")

    raw_root = selection.get("external_root")
    if not isinstance(raw_root, str) or not raw_root:
        violations.append("custody root is not configured")
    else:
        violations.extend(verify_custody_root(Path(raw_root), repository_root))
    return violations


def _read_owner_json(path: Path, label: str) -> tuple[object | None, list[str]]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None, [f"{label} is missing"]
    except OSError:
        return None, [f"{label} is unavailable"]
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        return None, [f"{label} must be a regular non-symlink file"]
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        return None, [f"{label} must belong to the current user"]
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        return None, [f"{label} permissions are not owner-only"]
    if metadata.st_size > MAX_CONTROL_RECORD_BYTES:
        return None, [f"{label} exceeds the size limit"]
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None, [f"{label} cannot be parsed safely"]
    return value, []


def _record_schema_violations(
    repository_root: Path,
    record: object,
    definition_name: str,
) -> list[str]:
    try:
        schema = json.loads(
            (repository_root / SCHEMA_PATH).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return ["G1 record schema cannot be loaded safely"]
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": f"#/$defs/{definition_name}",
            "$defs": schema["$defs"],
        }
    )
    errors = sorted(validator.iter_errors(record), key=lambda item: list(item.path))
    if errors:
        return [f"{definition_name} does not satisfy the G1 schema"]
    return []


def validate_final_approval_state(
    *,
    repository_root: Path,
    selection: dict[str, object],
    local_record_path: Path,
    as_of: datetime,
) -> list[str]:
    """Validate signed local state before reading one fixed custody record."""

    local_value, violations = _read_owner_json(
        local_record_path,
        "final G1 approval state",
    )
    if violations:
        return violations
    if not isinstance(local_value, dict) or set(local_value) != FINAL_APPROVAL_KEYS:
        return ["final G1 approval state fields are not closed"]
    if local_value.get("record_version") != "1.0":
        violations.append("final G1 approval state version is invalid")
    if local_value.get("external_custody_record_access_authorized") is not True:
        violations.append("external custody control-record access is not authorized")
    if local_value.get("custody_decision_filename") != CUSTODY_DECISION_FILENAME:
        violations.append("custody decision filename is not fixed")

    expected_bundle = bundle_subject(repository_root)
    observed_bundle = local_value.get("bundle_subject")
    if observed_bundle != expected_bundle:
        violations.append("approved G1 bundle does not match the current checkout")
    bundle_approvals = local_value.get("bundle_approvals")
    violations.extend(
        validate_approval_set(
            subject=expected_bundle,
            subject_id="M0-G1-BUNDLE-001",
            approvals=bundle_approvals,
            required_roles=BUNDLE_APPROVAL_ROLES,
            as_of=as_of,
        )
    )

    observed_scanner = local_value.get("scanner_admission")
    expected_scanner = scanner_subject(repository_root)
    if not isinstance(observed_scanner, dict):
        violations.append("scanner admission is not an object")
    else:
        scanner_projection = dict(observed_scanner)
        scanner_projection["approvals"] = []
        if scanner_projection != expected_scanner:
            violations.append("scanner admission does not match the verified scanner")
        violations.extend(
            _record_schema_violations(
                repository_root,
                observed_scanner,
                "E1ScannerAdmissionV1",
            )
        )
        violations.extend(
            validate_approval_set(
                subject=observed_scanner,
                subject_id="E1-GITLEAKS-8300",
                approvals=observed_scanner.get("approvals"),
                required_roles=CUSTODY_APPROVAL_ROLES,
                as_of=as_of,
            )
        )
    if violations:
        return list(dict.fromkeys(violations))

    raw_root = selection.get("external_root")
    if not isinstance(raw_root, str) or not raw_root:
        return ["custody root is not configured"]
    root_violations = verify_custody_root(Path(raw_root), repository_root)
    if root_violations:
        return root_violations
    custody_path = Path(raw_root) / CUSTODY_DECISION_FILENAME
    custody_value, custody_violations = _read_owner_json(
        custody_path,
        "custody decision",
    )
    if custody_violations:
        return custody_violations
    try:
        custody_digest = _sha256(custody_path.read_bytes())
    except OSError:
        return ["custody decision cannot be digested"]
    if custody_digest != local_value.get("custody_decision_sha256"):
        return ["custody decision digest does not match approval state"]
    violations.extend(
        _record_schema_violations(
            repository_root,
            custody_value,
            "CustodyDecisionV1",
        )
    )
    violations.extend(
        validate_custody_decision(
            decision=custody_value,
            selection=selection,
            as_of=as_of,
        )
    )
    return list(dict.fromkeys(violations))


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    violations = validate_implementation_approval(repository_root)
    if violations:
        print("M0 G1 EXIT: FAILED — implementation approval invalid")
        for violation in violations:
            print(f"- {violation}")
        print("- live custody/scanner evidence: NOT ACCESSED")
        return 2

    print("M0 G1 EXIT: implementation approval: VERIFIED")
    installed_version = installed_jsonschema_version()
    if installed_version != EXPECTED_JSONSCHEMA_VERSION:
        observed = installed_version if installed_version is not None else "not installed"
        print("M0 G1 EXIT: schema validator dependency: BLOCKED")
        print(f"- required jsonschema: {EXPECTED_JSONSCHEMA_VERSION}")
        print(f"- observed jsonschema: {observed}")
        print("- dependency installation authority: absent")
        print("M0 G1 EXIT: live custody/scanner evidence: NOT ACCESSED")
        return 3

    print("M0 G1 EXIT: schema validator dependency: VERIFIED")
    schema_violations = validate_schema_contract(repository_root)
    if schema_violations:
        print("M0 G1 EXIT: schema contract: FAILED")
        for violation in schema_violations:
            print(f"- {violation}")
        print("M0 G1 EXIT: live custody/scanner evidence: NOT ACCESSED")
        return 2

    print("M0 G1 EXIT: schema contract: VERIFIED")
    scanner_violations = verify_e1_scanner(repository_root)
    if scanner_violations:
        print("M0 G1 EXIT: local scanner verification: FAILED")
        for violation in scanner_violations:
            print(f"- {violation}")
        print("M0 G1 EXIT: external custody evidence: NOT ACCESSED")
        return 2

    print("M0 G1 EXIT: local scanner verification: VERIFIED")
    custody_violations = validate_local_custody_selection(repository_root)
    if custody_violations:
        print("M0 G1 EXIT: custody selection: BLOCKED")
        for violation in custody_violations:
            print(f"- {violation}")
        print("M0 G1 EXIT: external custody evidence: NOT ACCESSED")
        return 3

    print("M0 G1 EXIT: custody selection metadata: VERIFIED")
    try:
        with (repository_root / LOCAL_CUSTODY_SELECTION_PATH).open("rb") as stream:
            custody_selection = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        print("M0 G1 EXIT: FAILED — custody selection cannot be reloaded")
        print("M0 G1 EXIT: external custody contents: NOT ACCESSED")
        return 2

    local_final_path = repository_root / LOCAL_FINAL_APPROVAL_PATH
    final_violations = validate_final_approval_state(
        repository_root=repository_root,
        selection=custody_selection,
        local_record_path=local_final_path,
        as_of=datetime.now(timezone.utc),
    )
    if final_violations:
        if not local_final_path.exists():
            print("M0 G1 EXIT: final approvals/custody: BLOCKED")
            result = 3
        else:
            print("M0 G1 EXIT: final approvals/custody: FAILED")
            result = 2
        for violation in final_violations:
            print(f"- {violation}")
        print("M0 G1 EXIT: provider/account/process/profile access: NOT PERFORMED")
        return result

    print("M0 G1 EXIT: custody decision and approvals: VERIFIED")
    print("M0 G1 EXIT: scanner admission approvals: VERIFIED")
    print("M0 G1 EXIT: exact G1 bundle approvals: VERIFIED")
    print("M0 G1 EXIT: provider/account/process/profile access: NOT PERFORMED")
    print("M0 G1 FINISHED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
