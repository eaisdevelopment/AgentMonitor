"""Render the exact synchronized-Draft plan/control digest snapshot to stdout."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from validate_plans import load_catalog


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_snapshot(repository_root: Path) -> str:
    catalog = load_catalog(repository_root)
    lines = [
        'schema_version = "1.0"',
        'baseline_version = "1.0.0-draft"',
        'status = "draft_synchronized"',
        'owner = "integration_steward"',
        f"plan_count = {len(catalog.plans)}",
        "control_count = 9",
        "owner_approved = false",
        "implementation_authorized = false",
        "implemented = false",
        "live_verified = false",
        'readiness_audit = "docs/plans/integration/cs1-final-readiness-audit.md"',
    ]
    for plan in catalog.plans:
        content = (repository_root / plan.path).read_bytes()
        text = content.decode("utf-8")
        version_match = re.search(r"Plan version:\s*`?([^`\n]+)", text)
        if version_match is None:
            raise ValueError(f"{plan.plan_id} has no Plan version")
        lines.extend(
            [
                "",
                "[[plans]]",
                f"id = {_quote(plan.plan_id)}",
                f"path = {_quote(plan.path)}",
                f"plan_version = {_quote(version_match.group(1).strip())}",
                f"sha256 = {_quote(hashlib.sha256(content).hexdigest())}",
                f"bytes = {len(content)}",
            ]
        )
    controls = (
        ("planning-catalog", "docs/plans/planning-catalog.toml"),
        ("contract-baseline", catalog.contract_baseline_path),
        ("contract-adoption", catalog.contract_adoption_path),
        ("configuration-baseline", catalog.configuration_baseline_path),
        ("requirement-ownership", catalog.requirement_ownership_path),
        ("parallel-ownership", catalog.parallel_ownership_path),
        ("automation-routines", catalog.automation_catalog_path),
        ("automation-standard", catalog.automation_standard_path),
        ("m0-g0-approval", catalog.m0_g0_approval_path),
    )
    for control_id, path in controls:
        content = (repository_root / path).read_bytes()
        lines.extend(
            [
                "",
                "[[controls]]",
                f"id = {_quote(control_id)}",
                f"path = {_quote(path)}",
                f"sha256 = {_quote(hashlib.sha256(content).hexdigest())}",
                f"bytes = {len(content)}",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    print(render_snapshot(Path(__file__).resolve().parents[2]), end="")


if __name__ == "__main__":
    main()
