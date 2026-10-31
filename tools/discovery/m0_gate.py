"""Validate the exact, restricted Milestone 0 G0 approval against this checkout.

This gate reads repository governance artifacts only.  It does not inspect a
provider installation, account, process, profile, credential, or evidence root.
"""

from __future__ import annotations

import hashlib
import re
import sys
import tomllib
from pathlib import Path


APPROVAL_PATH = Path("docs/plans/discovery/m0-g0-approval.toml")
EXPECTED_PLAN_PATH = Path("docs/plans/discovery/m0-execution-plan.md")
EXPECTED_ROLES = {
    "owner",
    "root_integration",
    "security_privacy",
    "test_integrity",
    "provider_system",
}
REQUIRED_CONTROL_IDS = {
    "M0CTL-NOREAD",
    "M0CTL-NETWORK",
    "M0CTL-E1-ADMISSION",
    "M0CTL-ASSERTIONS",
    "M0CTL-ATIME",
    "M0CTL-G5-OPERATIONS",
    "M0CTL-AUTH-SCOPE",
    "M0CTL-CAPABILITY-VOCABULARY",
    "M0CTL-API-OWNERSHIP",
}
PROHIBITED_AUTHORITY_FLAGS = {
    "implementation_authorized",
    "provider_operations_authorized",
    "account_access_authorized",
    "evidence_custody_approved",
    "g1_complete",
    "preflight_implemented",
}


def _load_toml(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def validate_g0(repository_root: Path) -> list[str]:
    """Return fail-closed violations for the real M0 plan and approval record."""

    violations: list[str] = []
    approval_path = repository_root / APPROVAL_PATH
    try:
        approval = _load_toml(approval_path)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError) as error:
        return [f"G0 approval record cannot be loaded: {error}"]

    if approval.get("schema_version") != "1.0":
        violations.append("G0 approval schema must be 1.0")
    if approval.get("status") != "approved_for_gated_discovery":
        violations.append("G0 status is not approved_for_gated_discovery")
    if approval.get("plan_id") != "PLAN-M0-DISCOVERY":
        violations.append("G0 approval names the wrong plan")
    if approval.get("plan_path") != EXPECTED_PLAN_PATH.as_posix():
        violations.append("G0 approval names the wrong plan path")
    if not approval.get("approval_id") or not approval.get("approved_at"):
        violations.append("G0 approval identity/date is missing")
    if not approval.get("owner_direction") or not approval.get("scope"):
        violations.append("G0 owner direction or restricted scope is missing")

    for flag in sorted(PROHIBITED_AUTHORITY_FLAGS):
        if approval.get(flag) is not False:
            violations.append(f"{flag} must remain false at G0")

    plan_path = repository_root / EXPECTED_PLAN_PATH
    try:
        plan_bytes = plan_path.read_bytes()
        plan_text = plan_bytes.decode("utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError) as error:
        violations.append(f"approved M0 plan cannot be loaded: {error}")
        return violations

    if approval.get("plan_sha256") != hashlib.sha256(plan_bytes).hexdigest():
        violations.append("G0 approval does not match the exact M0 plan SHA-256")
    if approval.get("plan_bytes") != len(plan_bytes):
        violations.append("G0 approval does not match the exact M0 plan byte count")
    version_match = re.search(r"Plan version:\s*`?([^`\n]+)", plan_text)
    if version_match is None or approval.get("plan_version") != version_match.group(1).strip():
        violations.append("G0 approval does not match the M0 plan version")
    if "- Status: **Approved for gated discovery**" not in plan_text:
        violations.append("M0 plan status is not Approved for gated discovery")
    if f"- Approval record: `{APPROVAL_PATH.as_posix()}`" not in plan_text:
        violations.append("M0 plan does not link the exact G0 approval record")

    declared_controls = approval.get("required_control_ids")
    if not isinstance(declared_controls, list) or set(declared_controls) != REQUIRED_CONTROL_IDS:
        violations.append("G0 approval does not declare the exact required safety controls")
    for control_id in sorted(REQUIRED_CONTROL_IDS):
        if control_id not in plan_text:
            violations.append(f"approved M0 plan lacks control {control_id}")

    reviewers = approval.get("reviewers")
    if not isinstance(reviewers, list):
        violations.append("G0 reviewer decisions are missing")
        return violations
    roles = [item.get("role") for item in reviewers if isinstance(item, dict)]
    if len(roles) != len(set(roles)) or set(roles) != EXPECTED_ROLES:
        violations.append("G0 approval does not contain exactly the required reviewer roles")
    for item in reviewers:
        if not isinstance(item, dict):
            violations.append("G0 reviewer record is not a table")
            continue
        role = item.get("role", "<missing>")
        if item.get("decision") != "approved":
            violations.append(f"{role}: reviewer decision is not approved")
        if item.get("reviewed_plan_version") != approval.get("plan_version"):
            violations.append(f"{role}: reviewed plan version does not match")
        if not item.get("date") or not item.get("conditions"):
            violations.append(f"{role}: review date or conditions are missing")
    return violations


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    violations = validate_g0(repository_root)
    if violations:
        print(f"M0 G0 APPROVAL: FAILED ({len(violations)} violation(s))")
        for violation in violations:
            print(f"- {violation}")
        return 2
    print("M0 G0 APPROVAL: PASSED")
    print("- scope: exact plan approval only")
    print("- provider/account/process/profile operations: NOT AUTHORIZED")
    print("- G1 evidence custody and per-scenario preflight: NOT COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
