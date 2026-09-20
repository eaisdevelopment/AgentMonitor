"""Build sanitized automation rows through the published CTR-FND-008 V1 type."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from shutil import which
from typing import Literal

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.contracts.foundation_v1 import TestEvidenceSummaryV1  # noqa: E402

EvidenceStatus = Literal["Passed", "Failed", "Blocked", "Not Run"]
_VERSION = re.compile(r"(?<![A-Za-z0-9.])v?(\d+\.\d+(?:\.\d+){0,3})(?![0-9.])")


def actual_tool_versions(names: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """Read only version tokens from known local executables, never environments."""
    versions: list[tuple[str, str]] = []
    for name in names:
        if name == "python":
            version = (
                f"{sys.version_info.major}.{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            )
        else:
            if name == "playwright-chromium":
                node = which("node")
                if node is None:
                    raise ValueError("evidence_tool_unavailable")
                lookup = subprocess.run(
                    [
                        node,
                        "-e",
                        "process.stdout.write(require('playwright').chromium.executablePath())",
                    ],
                    cwd=ROOT / "frontend",
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                candidate = Path(lookup.stdout.strip())
                command = (
                    str(candidate)
                    if lookup.returncode == 0
                    and candidate.is_absolute()
                    and candidate.is_file()
                    else None
                )
            else:
                command = which(name)
            if command is None:
                raise ValueError("evidence_tool_unavailable")
            result = subprocess.run(
                [command, "--version"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            match = _VERSION.search(result.stdout) if result.returncode == 0 else None
            if match is None:
                raise ValueError("evidence_tool_version_unavailable")
            version = match.group(1)
        versions.append((name, version))
    return tuple(versions)


def evidence_row(
    *,
    test_id: str,
    command_id: str,
    boundary: str,
    status: EvidenceStatus,
    versions: tuple[tuple[str, str], ...],
    recorded_at: datetime | None = None,
    requirement_ids: tuple[str, ...] = ("NFR-TEST-002",),
    acceptance_ids: tuple[str, ...] = ("AC-TEST-002",),
    red_reference: str | None = None,
    green_reference: str | None = None,
    refactor_reference: str | None = None,
) -> dict[str, object]:
    """Only a checked live boundary can claim Passed and a runtime version."""
    if status == "Passed" and not versions:
        raise ValueError("passed_boundary_requires_actual_versions")
    if status != "Passed" and (
        versions or red_reference or green_reference or refactor_reference
    ):
        raise ValueError("unpassed_boundary_cannot_claim_green_evidence")
    record = TestEvidenceSummaryV1(
        test_id=test_id,
        requirement_ids=requirement_ids,
        acceptance_ids=acceptance_ids,
        boundary_class=boundary,
        command_registry_id=command_id,
        environment_versions=versions,
        red_reference=red_reference,
        green_reference=green_reference,
        refactor_reference=refactor_reference,
        status=status,
        sanitization_review="allowlisted statuses and versions; review pending",
        recorded_at=recorded_at or datetime.now(UTC),
        reviewer="pending_independent_review",
        live_owner_countersignature=None,
    )
    payload: dict[str, object] = asdict(record)
    payload["contract_id"] = record.CONTRACT_ID
    payload["recorded_at"] = record.recorded_at.isoformat()
    payload["environment_versions"] = [list(pair) for pair in versions]
    return payload
