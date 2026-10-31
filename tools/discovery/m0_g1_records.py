"""Deterministic detached-approval rules for M0 G1 records."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone


RECORD_ID = re.compile(r"APR-[A-Z0-9-]+")
REFERENCE_ID = re.compile(r"REF-[A-Z0-9-]+")
SHA256 = re.compile(r"[a-f0-9]{64}")
APPROVAL_ROLES = {
    "owner",
    "security_privacy",
    "test_integrity",
    "provider_system",
    "root_integration",
}
CUSTODY_APPROVAL_ROLES = {"owner", "security_privacy", "test_integrity"}
REQUIRED_APPROVAL_KEYS = {
    "record_type",
    "schema_version",
    "approval_id",
    "subject_id",
    "subject_sha256",
    "role",
    "decision",
    "reviewer_ref",
    "decided_at_utc",
}
OPTIONAL_APPROVAL_KEYS = {"expires_at_utc"}


def canonical_subject_bytes(subject: dict[str, object]) -> bytes:
    """Return the exact approval projection: canonical JSON, approvals empty."""

    projection = dict(subject)
    if "approvals" in projection:
        projection["approvals"] = []
    return (
        json.dumps(
            projection,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def subject_sha256(subject: dict[str, object]) -> str:
    """Bind an approval to the canonical approval-free subject projection."""

    return hashlib.sha256(canonical_subject_bytes(subject)).hexdigest()


def approval_record(
    *,
    approval_id: str,
    subject_id: str,
    subject_digest: str,
    role: str,
    reviewer_ref: str,
    decided_at_utc: str,
    expires_at_utc: str | None = None,
) -> dict[str, object]:
    """Construct one closed ApprovalRecordV1 value."""

    return {
        "record_type": "ApprovalRecordV1",
        "schema_version": "1.0",
        "approval_id": approval_id,
        "subject_id": subject_id,
        "subject_sha256": subject_digest,
        "role": role,
        "decision": "approved",
        "reviewer_ref": reviewer_ref,
        "decided_at_utc": decided_at_utc,
        "expires_at_utc": expires_at_utc,
    }


def custody_subject(selection: dict[str, object]) -> dict[str, object]:
    """Create the approval-free custody decision from owner selection metadata."""

    return {
        "record_type": "CustodyDecisionV1",
        "schema_version": "1.0",
        "decision_id": "CUST-M0-G1-001",
        "external_root_ref": selection.get("external_root_ref"),
        "owner_selected": selection.get("owner_selected"),
        "repository_storage_prohibited": True,
        "permissions_verified": True,
        "sync_backup_disposition": selection.get("sync_backup_disposition"),
        "retention_until_utc": selection.get("retention_until_utc"),
        "approvals": [],
    }


def _utc_z_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError:
        return None
    if parsed.tzinfo != timezone.utc:
        return None
    return parsed


def _approval_shape_violations(approval: object) -> list[str]:
    if not isinstance(approval, dict):
        return ["approval must be an object"]
    violations: list[str] = []
    keys = set(approval)
    if not REQUIRED_APPROVAL_KEYS <= keys:
        violations.append("approval is missing required fields")
    if keys - REQUIRED_APPROVAL_KEYS - OPTIONAL_APPROVAL_KEYS:
        violations.append("approval contains unknown fields")
    if approval.get("record_type") != "ApprovalRecordV1":
        violations.append("approval record type is invalid")
    if approval.get("schema_version") != "1.0":
        violations.append("approval schema version is invalid")
    approval_id = approval.get("approval_id")
    if not isinstance(approval_id, str) or RECORD_ID.fullmatch(approval_id) is None:
        violations.append("approval ID is invalid")
    subject_digest = approval.get("subject_sha256")
    if not isinstance(subject_digest, str) or SHA256.fullmatch(subject_digest) is None:
        violations.append("approval subject digest is invalid")
    if approval.get("role") not in APPROVAL_ROLES:
        violations.append("approval role is invalid")
    reviewer_ref = approval.get("reviewer_ref")
    if not isinstance(reviewer_ref, str) or REFERENCE_ID.fullmatch(reviewer_ref) is None:
        violations.append("approval reviewer reference is invalid")
    if _utc_z_datetime(approval.get("decided_at_utc")) is None:
        violations.append("approval decision timestamp is invalid")
    expires = approval.get("expires_at_utc")
    if expires is not None and _utc_z_datetime(expires) is None:
        violations.append("approval expiry timestamp is invalid")
    return violations


def validate_approval_set(
    *,
    subject: dict[str, object],
    subject_id: str,
    approvals: object,
    required_roles: set[str],
    as_of: datetime,
) -> list[str]:
    """Validate exact, non-conflicting, unexpired detached approvals."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if not isinstance(approvals, list):
        return ["approvals must be an array"]

    violations: list[str] = []
    expected_digest = subject_sha256(subject)
    observed_roles: list[object] = []
    observed_ids: list[object] = []
    for approval in approvals:
        violations.extend(_approval_shape_violations(approval))
        if not isinstance(approval, dict):
            continue
        role = approval.get("role")
        observed_roles.append(role)
        observed_ids.append(approval.get("approval_id"))
        if approval.get("subject_id") != subject_id:
            violations.append("approval subject ID does not match")
        if approval.get("subject_sha256") != expected_digest:
            violations.append("approval subject digest does not match")
        if approval.get("decision") != "approved":
            violations.append("approval decision is not approved")
        decided_at = _utc_z_datetime(approval.get("decided_at_utc"))
        if decided_at is not None and decided_at > as_of:
            violations.append("approval decision is in the future")
        expires_at = _utc_z_datetime(approval.get("expires_at_utc"))
        if expires_at is not None and expires_at <= as_of:
            violations.append("approval has expired")

    role_set = {role for role in observed_roles if isinstance(role, str)}
    if role_set != required_roles:
        violations.append(
            "approval roles must be exactly " + ",".join(sorted(required_roles))
        )
    if len(observed_roles) != len(role_set):
        violations.append("approval role is duplicated")
    if len(observed_ids) != len(set(observed_ids)):
        violations.append("approval ID is duplicated")
    return list(dict.fromkeys(violations))


def validate_custody_decision(
    *,
    decision: object,
    selection: dict[str, object],
    as_of: datetime,
) -> list[str]:
    """Validate a completed custody record against the exact owner selection."""

    if not isinstance(decision, dict):
        return ["custody decision must be an object"]
    violations: list[str] = []
    expected_keys = set(custody_subject(selection))
    if set(decision) != expected_keys:
        violations.append("custody decision fields are not closed")
    expected = custody_subject(selection)
    for key in expected_keys - {"approvals", "retention_until_utc"}:
        if decision.get(key) != expected.get(key):
            violations.append(f"custody {key} does not match owner selection")
    if decision.get("retention_until_utc") != selection.get("retention_until_utc"):
        violations.append("custody retention does not match owner selection")
    retention = _utc_z_datetime(decision.get("retention_until_utc"))
    if retention is None:
        violations.append("custody retention timestamp is invalid")
    elif retention <= as_of:
        violations.append("custody retention has expired")
    violations.extend(
        validate_approval_set(
            subject=decision,
            subject_id="CUST-M0-G1-001",
            approvals=decision.get("approvals"),
            required_roles=CUSTODY_APPROVAL_ROLES,
            as_of=as_of,
        )
    )
    return list(dict.fromkeys(violations))
