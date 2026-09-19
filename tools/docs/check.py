"""Validate AgentMonitor documentation against the real repository indexes."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REQUIREMENT_ID = re.compile(
    r"\b(?:FR|NFR|AC)-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b"
)
CONTRACT_ID = re.compile(r"\bCTR-[A-Z]+-\d{3}\b")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "app://", "data:")


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    return unquote(target).split("#", maxsplit=1)[0]


def check_repository(repository_root: Path) -> list[str]:
    violations: list[str] = []
    requirement_text = "\n".join(
        (repository_root / path).read_text(encoding="utf-8")
        for path in (
            "docs/product/requirements.md",
            "docs/product/v1-acceptance-criteria.md",
        )
    )
    known_requirements = set(REQUIREMENT_ID.findall(requirement_text))
    with (repository_root / "docs/plans/contract-baseline.toml").open("rb") as stream:
        contract_raw = tomllib.load(stream)
    known_contracts = {item["id"] for item in contract_raw["contracts"]}

    markdown_files = sorted(
        path
        for path in repository_root.rglob("*.md")
        if path.is_file()
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
    )
    for document in markdown_files:
        relative = document.relative_to(repository_root)
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = _link_target(raw_target)
            if not target or target.startswith(EXTERNAL_SCHEMES):
                continue
            if target.startswith("/"):
                violations.append(f"{relative}: repository document uses absolute link {target}")
                continue
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(repository_root.resolve())
            except ValueError:
                violations.append(f"{relative}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                violations.append(f"{relative}: broken local link: {target}")
        unknown_requirements = sorted(
            set(REQUIREMENT_ID.findall(text)) - known_requirements
        )
        if unknown_requirements:
            violations.append(
                f"{relative}: unknown requirement IDs: {', '.join(unknown_requirements)}"
            )
        unknown_contracts = sorted(set(CONTRACT_ID.findall(text)) - known_contracts)
        if unknown_contracts:
            violations.append(
                f"{relative}: unknown contract IDs: {', '.join(unknown_contracts)}"
            )
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    violations = check_repository(root)
    if violations:
        print(f"DOCUMENTATION CHECK: FAILED ({len(violations)} violation(s))")
        for violation in violations:
            print(f"- {violation}")
        return 1
    markdown_count = sum(1 for path in root.rglob("*.md") if path.is_file())
    print(f"DOCUMENTATION CHECK: PASSED ({markdown_count} Markdown files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
