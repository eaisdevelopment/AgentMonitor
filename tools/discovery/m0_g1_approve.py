"""Owner-controlled finalization of the exact M0 G1 control bundle."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from m0_g1_bundle import bundle_subject, scanner_subject
from m0_g1_exit import (
    is_utc_z_timestamp,
    load_local_custody_selection,
    verify_custody_root,
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
REVIEW_DECISION_PATH = Path(".agentmonitor-local/m0-g1-independent-reviews.json")
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
}
REVIEW_GROUPS = {
    "custody_approvals": ("CUST-M0-G1-001", CUSTODY_ROLES - {"owner"}),
    "scanner_approvals": ("E1-GITLEAKS-8300", CUSTODY_ROLES - {"owner"}),
    "bundle_approvals": ("M0-G1-BUNDLE-001", BUNDLE_ROLES - {"owner"}),
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
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def validate_reviewer_decisions(
    reviews: object,
    *,
    custody_subject: dict[str, object],
    scanner_subject: dict[str, object],
    bundle_subject: dict[str, object],
    as_of: datetime,
) -> list[str]:
    """Require separate, exact-subject decisions from the non-owner reviewers."""

    if not isinstance(reviews, dict):
        return ["independent reviewer decisions are missing"]
    if set(reviews) != {"record_version", *REVIEW_GROUPS}:
        return ["independent reviewer decision fields are not closed"]
    if reviews.get("record_version") != "1.0":
        return ["independent reviewer decision version is invalid"]
    subjects = {
        "custody_approvals": custody_subject,
        "scanner_approvals": scanner_subject,
        "bundle_approvals": bundle_subject,
    }
    violations: list[str] = []
    roles_by_ref: dict[str, set[str]] = {}
    refs_by_role: dict[str, set[str]] = {}
    for group, (subject_id, roles) in REVIEW_GROUPS.items():
        violations.extend(
            f"{group}: {violation}"
            for violation in validate_approval_set(
                subject=subjects[group],
                subject_id=subject_id,
                approvals=reviews[group],
                required_roles=roles,
                as_of=as_of,
            )
        )
        group_approvals = reviews[group]
        if isinstance(group_approvals, list):
            for approval in group_approvals:
                if not isinstance(approval, dict):
                    continue
                role = approval.get("role")
                reviewer_ref = approval.get("reviewer_ref")
                if isinstance(role, str) and isinstance(reviewer_ref, str):
                    if reviewer_ref == REVIEWER_REFS["owner"]:
                        violations.append(
                            "owner reference cannot attest a non-owner review"
                        )
                    roles_by_ref.setdefault(reviewer_ref, set()).add(role)
                    refs_by_role.setdefault(role, set()).add(reviewer_ref)
    if any(len(roles) != 1 for roles in roles_by_ref.values()):
        violations.append("independent reviewer references are not role-distinct")
    if any(len(refs) != 1 for refs in refs_by_role.values()):
        violations.append("reviewer reference changes across review subjects")
    return violations


def _owner_approval(
    subject: dict[str, object],
    *,
    subject_id: str,
    approval_prefix: str,
    decided_at_utc: str,
) -> dict[str, object]:
    return approval_record(
        approval_id=f"APR-{approval_prefix}-OWNER",
        subject_id=subject_id,
        subject_digest=subject_sha256(subject),
        role="owner",
        reviewer_ref=REVIEWER_REFS["owner"],
        decided_at_utc=decided_at_utc,
    )


def owner_completed_approvals(
    subject: dict[str, object],
    reviewer_approvals: list[dict[str, object]],
    *,
    subject_id: str,
    approval_prefix: str,
    decided_at_utc: str,
) -> list[dict[str, object]]:
    """Return reviewer decisions plus the explicit owner's exact-subject record."""

    return [
        *reviewer_approvals,
        _owner_approval(
            subject,
            subject_id=subject_id,
            approval_prefix=approval_prefix,
            decided_at_utc=decided_at_utc,
        ),
    ]


def review_subject_rows(
    custody: dict[str, object],
    scanner: dict[str, object],
    bundle: dict[str, object],
) -> list[tuple[str, str]]:
    """Expose only stable IDs and exact approval digests for role review."""

    return [
        ("CUST-M0-G1-001", subject_sha256(custody)),
        ("E1-GITLEAKS-8300", subject_sha256(scanner)),
        ("M0-G1-BUNDLE-001", subject_sha256(bundle)),
    ]


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


def _unique_json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_reviewer_decisions(
    repository_root: Path,
) -> tuple[object | None, list[str]]:
    """Read a bounded owner-only local file without following a symlink."""

    path = repository_root / REVIEW_DECISION_PATH
    if _verify_parent(path.parent):
        return None, ["independent reviewer decision parent is not owner-only"]
    if not hasattr(os, "O_NOFOLLOW"):
        return None, ["independent reviewer decision file cannot be read safely"]
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return None, ["independent reviewer decisions are missing"]
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            return None, ["independent reviewer decision file is not regular"]
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            return None, ["independent reviewer decision file has the wrong owner"]
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            return None, ["independent reviewer decision file is not owner-only"]
        if not 0 < metadata.st_size <= 65536:
            return None, ["independent reviewer decision file has invalid size"]
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            content = stream.read(65537)
        if len(content) > 65536:
            return None, ["independent reviewer decision file has invalid size"]
    except OSError:
        return None, ["independent reviewer decision file cannot be read safely"]
    finally:
        os.close(descriptor)
    try:
        return json.loads(
            content.decode("utf-8"), object_pairs_hook=_unique_json_pairs
        ), []
    except (UnicodeDecodeError, ValueError):
        return None, ["independent reviewer decision file is invalid"]


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
    owner_confirmation: str,
    reviewer_decisions: object = None,
) -> list[str]:
    """Write exact approved records after the CLI obtains owner confirmation."""

    if not is_owner_confirmation(owner_confirmation):
        return ["exact owner confirmation is missing"]
    timestamp = _utc_z(decided_at)
    retention = selection.get("retention_until_utc")
    if not is_utc_z_timestamp(retention):
        return ["custody selection retention is invalid"]
    raw_root = selection.get("external_root")
    if not isinstance(raw_root, str) or not raw_root:
        return ["custody selection root is missing"]
    violations = verify_custody_root(Path(raw_root), repository_root)
    if violations:
        return violations

    custody = custody_subject(selection)
    scanner = scanner_subject(repository_root)
    bundle = bundle_subject(repository_root)
    violations = validate_reviewer_decisions(
        reviewer_decisions,
        custody_subject=custody,
        scanner_subject=scanner,
        bundle_subject=bundle,
        as_of=decided_at,
    )
    if violations:
        return violations
    reviews = cast(dict[str, list[dict[str, object]]], reviewer_decisions)
    custody["approvals"] = owner_completed_approvals(
        custody,
        reviews["custody_approvals"],
        subject_id="CUST-M0-G1-001",
        approval_prefix="CUST-M0-G1",
        decided_at_utc=timestamp,
    )
    violations = validate_custody_decision(
        decision=custody,
        selection=selection,
        as_of=decided_at,
    )
    if violations:
        return violations

    scanner["approvals"] = owner_completed_approvals(
        scanner,
        reviews["scanner_approvals"],
        subject_id="E1-GITLEAKS-8300",
        approval_prefix="E1-GITLEAKS-8300",
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

    bundle_approvals = owner_completed_approvals(
        bundle,
        reviews["bundle_approvals"],
        subject_id="M0-G1-BUNDLE-001",
        approval_prefix="M0-G1-BUNDLE",
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


def main() -> int:
    if sys.argv[1:] not in ([], ["--review-subjects"]):
        print("M0 G1 FINALIZATION: BLOCKED — unsupported argument")
        return 3
    repository_root = Path(__file__).resolve().parents[2]
    selection, violations = load_local_custody_selection(repository_root)
    if violations or selection is None:
        print("M0 G1 FINALIZATION: BLOCKED")
        for violation in violations:
            print(f"- {violation}")
        return 3

    if sys.argv[1:] == ["--review-subjects"]:
        try:
            rows = review_subject_rows(
                custody_subject(selection),
                scanner_subject(repository_root),
                bundle_subject(repository_root),
            )
        except OSError:
            print("M0 G1 REVIEW SUBJECTS: BLOCKED — subject unavailable")
            return 3
        print("M0 G1 REVIEW SUBJECTS: DIGESTS ONLY — NOT AN APPROVAL")
        for subject_id, digest in rows:
            print(f"{subject_id} {digest}")
        return 0

    reviews, violations = load_reviewer_decisions(repository_root)
    if not violations:
        violations = validate_reviewer_decisions(
            reviews,
            custody_subject=custody_subject(selection),
            scanner_subject=scanner_subject(repository_root),
            bundle_subject=bundle_subject(repository_root),
            as_of=datetime.now(timezone.utc),
        )
    if violations:
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
        owner_confirmation=confirmation,
        reviewer_decisions=reviews,
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
