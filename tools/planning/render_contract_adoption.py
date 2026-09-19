"""Render exact per-plan contract adoption from the real Draft baseline."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from validate_plans import load_catalog


def _array(values: list[str]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def render_contract_adoption(repository_root: Path) -> str:
    catalog = load_catalog(repository_root)
    baseline_path = repository_root / catalog.contract_baseline_path
    baseline_bytes = baseline_path.read_bytes()
    baseline = tomllib.loads(baseline_bytes.decode("utf-8"))
    contracts = baseline["contracts"]
    lines = [
        'schema_version = "1.0"',
        'status = "draft_exact"',
        f'contract_baseline_version = {json.dumps(baseline["baseline_version"])}',
        f'contract_baseline_sha256 = "{hashlib.sha256(baseline_bytes).hexdigest()}"',
        f"plan_count = {len(catalog.plans)}",
        "owner_approved = false",
        "implementation_authorized = false",
    ]
    for plan in catalog.plans:
        plan_bytes = (repository_root / plan.path).read_bytes()
        publishes = sorted(
            contract["id"]
            for contract in contracts
            if contract["producer"] == plan.plan_id
        )
        consumes = sorted(
            contract["id"]
            for contract in contracts
            if plan.plan_id in contract["consumers"]
        )
        lines.extend(
            [
                "",
                "[[plans]]",
                f'id = {json.dumps(plan.plan_id)}',
                f'plan_path = {json.dumps(plan.path)}',
                f'plan_sha256 = "{hashlib.sha256(plan_bytes).hexdigest()}"',
                f"publishes = {_array(publishes)}",
                f"consumes = {_array(consumes)}",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    print(render_contract_adoption(Path(__file__).resolve().parents[2]), end="")


if __name__ == "__main__":
    main()
