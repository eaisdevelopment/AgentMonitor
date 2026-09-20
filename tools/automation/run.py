"""Canonical fail-closed dispatcher for AgentMonitor engineering routines."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

CATALOG_PATH = Path("tools/automation/routines.toml")
MANDATORY_ROUTINES = {
    "AUTO-PLAN-CHECK",
    "AUTO-M0-G0",
    "AUTO-M0-G1-CONTRACT",
    "AUTO-M0-G1-FINALIZE",
    "AUTO-M0-G1-EXIT",
    "AUTO-M0-PREFLIGHT",
    "AUTO-M0-POSTFLIGHT",
    "AUTO-M0-LEDGER",
    "AUTO-DOCS-CHECK",
    "AUTO-TEST",
    "AUTO-QUALITY",
    "AUTO-GIT-PREFLIGHT",
    "AUTO-BUILD",
    "AUTO-MIGRATE",
    "AUTO-DEPLOY",
    "AUTO-BACKUP",
    "AUTO-RESTORE",
    "AUTO-RELEASE",
}
EXECUTABLE_STATUSES = {"operational", "operational_limited"}
ALLOWED_STATUSES = EXECUTABLE_STATUSES | {"blocked"}


def index_routines(items: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for item in items:
        routine_id = item["id"]
        if routine_id in indexed:
            raise ValueError(f"duplicate routine ID: {routine_id}")
        indexed[routine_id] = item
    return indexed


def load_catalog(repository_root: Path) -> dict[str, dict]:
    with (repository_root / CATALOG_PATH).open("rb") as stream:
        raw = tomllib.load(stream)
    return index_routines(raw["routines"])


def validate_catalog(repository_root: Path, catalog: dict[str, dict]) -> list[str]:
    violations: list[str] = []
    if set(catalog) != MANDATORY_ROUTINES:
        violations.append("routine catalog does not contain exactly the mandatory IDs")
    for routine_id, routine in catalog.items():
        status = routine.get("status")
        command = routine.get("implementation_command")
        blockers = routine.get("blockers")
        if status not in ALLOWED_STATUSES:
            violations.append(f"{routine_id}: invalid status {status!r}")
        if not routine.get("owner") or not routine.get("scope"):
            violations.append(f"{routine_id}: missing owner or scope")
        if not isinstance(command, list) or any(
            not isinstance(argument, str) or not argument for argument in command
        ):
            violations.append(f"{routine_id}: command must be a string array")
        if not isinstance(blockers, list):
            violations.append(f"{routine_id}: blockers must be an array")
            continue
        if status in EXECUTABLE_STATUSES and not command:
            violations.append(f"{routine_id}: executable status has no command")
        if (
            command
            and len(command) > 1
            and command[0].startswith("python")
            and command[1].endswith(".py")
            and not (repository_root / command[1]).is_file()
        ):
            violations.append(f"{routine_id}: command script does not exist")
        if status == "operational" and blockers:
            violations.append(f"{routine_id}: operational routine has blockers")
        if status == "operational_limited" and not blockers:
            violations.append(
                f"{routine_id}: operational_limited routine must name blockers"
            )
        if status == "blocked" and (command or not blockers):
            violations.append(
                f"{routine_id}: blocked routine must have no implementation "
                "command and named blockers"
            )
        if command and command[0].startswith("/"):
            violations.append(f"{routine_id}: command must be checkout-relative")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("routine", nargs="?")
    parser.add_argument("--list", action="store_true", dest="list_routines")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    try:
        catalog = load_catalog(root)
    except (
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
        tomllib.TOMLDecodeError,
    ) as error:
        print(f"AUTOMATION CATALOG: FAILED — {error}")
        return 2
    violations = validate_catalog(root, catalog)
    if violations:
        print(f"AUTOMATION CATALOG: FAILED ({len(violations)} violation(s))")
        for violation in violations:
            print(f"- {violation}")
        return 2
    if arguments.list_routines:
        for routine_id in sorted(catalog):
            routine = catalog[routine_id]
            print(f"{routine_id}\t{routine['status']}\t{routine['scope']}")
        return 0
    if arguments.routine not in catalog:
        parser.error("routine must be one of the cataloged AUTO-* IDs")
    routine = catalog[arguments.routine]
    if routine["status"] == "blocked":
        print(f"{arguments.routine}: BLOCKED")
        for blocker in routine["blockers"]:
            print(f"- {blocker}")
        return 3
    if routine["status"] == "operational_limited":
        print(f"{arguments.routine}: RUNNING LIMITED SCOPE — {routine['scope']}")
        for blocker in routine["blockers"]:
            print(f"- OUT-OF-SCOPE/BLOCKED: {blocker}")
    else:
        print(f"{arguments.routine}: RUNNING — {routine['scope']}")
    try:
        result = subprocess.run(
            routine["implementation_command"], cwd=root, check=False
        )
    except OSError:
        print(f"{arguments.routine}: BLOCKED by missing or unusable local executable")
        return 3
    if result.returncode == 0:
        print(f"{arguments.routine}: PASSED ({routine['status']})")
    elif result.returncode == 3:
        print(f"{arguments.routine}: BLOCKED by real checkout/environment state")
    else:
        print(f"{arguments.routine}: FAILED (exit {result.returncode})")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
