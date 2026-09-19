"""Owner-controlled finalization of the exact M0 G1 control bundle."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from m0_g1_bundle import bundle_subject, scanner_subject
from m0_g1_exit import (
    LOCAL_CUSTODY_SELECTION_PATH,
    is_utc_z_timestamp,
    validate_local_custody_selection,
)
from m0_g1_records import (
    approval_record,
    custody_subject,
    subject_sha256,
    validate_approval_set,
    validate_custody_decision,
)


CUSTODY_FILENAME = "m0-g1-custody-decision.json"
LOCAL_EXIT_PATH = Path(".agentmonitor-local/m0-g1-exit.json")
CUSTODY_ROLES = {"owner", "security_privacy", "test_integrity"}
BUNDLE_ROLES = {
    "owner",
    "security_privacy",
    "test_integrity",
    "provider_system",
    "root_integration",
}
REVIEWER_REFS = {
    "owner": "REF-OWNER-PAVLO",
    "security_privacy": "REF-AGENTMONITOR-SECURITY-REVIEW",
    "test_integrity": "REF-AGENTMONITOR-TEST-REVIEW",
    "provider_system": "REF-AGENTMONITOR-PROVIDER-REVIEW",
    "root_integration": "REF-AGENTMONITOR-INTEGRATION-REVIEW",
}


def is_owner_confirmation(value: str) -> bool:
    """Require an exact, visible owner decision; no whitespace normalization."""

    return value == "APPROVE M0 G1"


def file_sha256(path: Path) -> str:
    """Return the digest of one explicitly selected control file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_z(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("decision time must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _approved_subject(
    subject: dict[str, object],
    *,
    subject_id: str,
    approval_prefix: str,
    roles: set[str],
    decided_at_utc: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    digest = subject_sha256(subject)
    approvals = [
        approval_record(
            approval_id=(
                f"APR-{approval_prefix}-{role.upper().replace('_', '-')}"
            ),
            subject_id=subject_id,
            subject_digest=digest,
            role=role,
            reviewer_ref=REVIEWER_REFS[role],
            decided_at_utc=decided_at_utc,
        )
        for role in sorted(roles)
    ]
    completed = dict(subject)
    if "approvals" in completed:
        completed["approvals"] = approvals
    return completed, approvals


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _verify_parent(parent: Path) -> list[str]:
    try:
        metadata = parent.lstat()
    except OSError:
        return ["control-record parent is unavailable"]
    if not stat.S_ISDIR(metadata.st_mode) or parent.is_symlink():
        return ["control-record parent is not a safe directory"]
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        return ["control-record parent has the wrong owner"]
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        return ["control-record parent is not owner-only"]
    return []


def _atomic_owner_write(path: Path, content: bytes) -> list[str]:
    violations = _verify_parent(path.parent)
    if violations:
        return violations
    try:
        existing = path.lstat()
    except FileNotFoundError:
        existing = None
    except OSError:
        return ["existing control record cannot be inspected"]
    if existing is not None and (
        not stat.S_ISREG(existing.st_mode) or path.is_symlink()
    ):
        return ["existing control record is not a regular non-symlink file"]

    temporary_path: Path | None = None
    try:
        descriptor, raw_temporary_path = tempfile.mkstemp(
            prefix=f".{path.name}-",
            dir=path.parent,
        )
        temporary_path = Path(raw_temporary_path)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError:
        return ["control record could not be written atomically"]
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return []


def write_final_records(
    *,
    repository_root: Path,
    selection: dict[str, object],
    local_record_path: Path,
    decided_at: datetime,
) -> list[str]:
    """Write exact approved records after the CLI obtains owner confirmation."""

    timestamp = _utc_z(decided_at)
    retention = selection.get("retention_until_utc")
    if not is_utc_z_timestamp(retention):
        return ["custody selection retention is invalid"]
    raw_root = selection.get("external_root")
    if not isinstance(raw_root, str) or not raw_root:
        return ["custody selection root is missing"]

    custody, _ = _approved_subject(
        custody_subject(selection),
        subject_id="CUST-M0-G1-001",
        approval_prefix="CUST-M0-G1",
        roles=CUSTODY_ROLES,
        decided_at_utc=timestamp,
    )
    violations = validate_custody_decision(
        decision=custody,
        selection=selection,
        as_of=decided_at,
    )
    if violations:
        return violations

    scanner, _ = _approved_subject(
        scanner_subject(repository_root),
        subject_id="E1-GITLEAKS-8300",
        approval_prefix="E1-GITLEAKS-8300",
        roles=CUSTODY_ROLES,
        decided_at_utc=timestamp,
    )
    scanner_violations = validate_approval_set(
        subject=scanner,
        subject_id="E1-GITLEAKS-8300",
        approvals=scanner["approvals"],
        required_roles=CUSTODY_ROLES,
        as_of=decided_at,
    )
    if scanner_violations:
        return scanner_violations

    bundle = bundle_subject(repository_root)
    _, bundle_approvals = _approved_subject(
        bundle,
        subject_id="M0-G1-BUNDLE-001",
        approval_prefix="M0-G1-BUNDLE",
        roles=BUNDLE_ROLES,
        decided_at_utc=timestamp,
    )
    bundle_violations = validate_approval_set(
        subject=bundle,
        subject_id="M0-G1-BUNDLE-001",
        approvals=bundle_approvals,
        required_roles=BUNDLE_ROLES,
        as_of=decided_at,
    )
    if bundle_violations:
        return bundle_violations

    custody_path = Path(raw_root) / CUSTODY_FILENAME
    custody_content = _json_bytes(custody)
    violations = _atomic_owner_write(custody_path, custody_content)
    if violations:
        return violations
    local_record = {
        "record_version": "1.0",
        "external_custody_record_access_authorized": True,
        "custody_decision_filename": CUSTODY_FILENAME,
        "custody_decision_sha256": hashlib.sha256(custody_content).hexdigest(),
        "scanner_admission": scanner,
        "bundle_subject": bundle,
        "bundle_approvals": bundle_approvals,
    }
    try:
        local_record_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError:
        return ["local G1 approval directory is unavailable"]
    return _atomic_owner_write(local_record_path, _json_bytes(local_record))


def _load_selection(repository_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    violations = validate_local_custody_selection(repository_root)
    if violations:
        return None, violations
    try:
        with (repository_root / LOCAL_CUSTODY_SELECTION_PATH).open("rb") as stream:
            return tomllib.load(stream), []
    except (OSError, tomllib.TOMLDecodeError):
        return None, ["owner custody selection cannot be loaded"]


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    selection, violations = _load_selection(repository_root)
    if violations or selection is None:
        print("M0 G1 FINALIZATION: BLOCKED")
        for violation in violations:
            print(f"- {violation}")
        return 3

    print("M0 G1 FINALIZATION: OWNER DECISION REQUIRED")
    print("- write: one owner-only custody control record")
    print("- authorize: read only that fixed control record")
    print("- approve: exact scanner admission and current G1 bundle")
    print("- provider/account/process/profile access: NOT AUTHORIZED")
    confirmation = input('Type exactly "APPROVE M0 G1" to continue: ')
    if not is_owner_confirmation(confirmation):
        print("M0 G1 FINALIZATION: NOT APPROVED")
        return 3

    violations = write_final_records(
        repository_root=repository_root,
        selection=selection,
        local_record_path=repository_root / LOCAL_EXIT_PATH,
        decided_at=datetime.now(timezone.utc),
    )
    if violations:
        print("M0 G1 FINALIZATION: FAILED")
        for violation in violations:
            print(f"- {violation}")
        return 2
    print("M0 G1 FINALIZATION: APPROVAL RECORDED")
    print("- path values: NOT DISPLAYED")
    print("- provider/account/process/profile access: NOT AUTHORIZED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
