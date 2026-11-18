"""Pure M7 execution receipt encoding; never accepts owner-entered evidence."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class ExitContext:
    source_revision: str
    installed_revision: str
    schema_revision: str
    service_identity: str


@dataclass(frozen=True, slots=True)
class TimedCheck:
    lane: str
    name: str
    status: str
    reason_code: str | None
    started_at: datetime
    finished_at: datetime


def build_receipt(
    before: ExitContext,
    after: ExitContext,
    checks: tuple[TimedCheck, ...],
    required: Mapping[str, tuple[str, ...]],
) -> dict[str, object]:
    """All required boundaries, exact identities and actual UTC execution times."""
    if (
        before != after
        or before.source_revision != before.installed_revision
        or re.fullmatch(r"[a-f0-9]{40}", before.source_revision) is None
        or re.fullmatch(r"v[0-9]+_[0-9]+", before.schema_revision) is None
        or re.fullmatch(r"[a-f0-9]{64}", before.service_identity) is None
    ):
        raise ValueError("m7_receipt_context_invalid")
    expected = {
        (lane, name) for lane in (*required["exit"], "exit") for name in required[lane]
    }
    actual = [(check.lane, check.name) for check in checks]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("m7_receipt_checks_invalid")
    for check in checks:
        if (
            check.status not in {"passed", "failed", "blocked", "not_run"}
            or check.started_at.utcoffset() != timedelta(0)
            or check.finished_at.utcoffset() != timedelta(0)
            or check.finished_at < check.started_at
            or (
                check.reason_code is not None
                and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", check.reason_code) is None
            )
        ):
            raise ValueError("m7_receipt_check_invalid")
    statuses = {check.status for check in checks}
    status = (
        "failed"
        if "failed" in statuses
        else "passed"
        if statuses == {"passed"}
        else "blocked"
    )
    return {
        "record_type": "agentmonitor.m7_exit_receipt.v1",
        "status": status,
        "source_revision": before.source_revision,
        "installed_revision": before.installed_revision,
        "schema_revision": before.schema_revision,
        "service_identity": before.service_identity,
        "started_at": min(check.started_at for check in checks).isoformat(),
        "finished_at": max(check.finished_at for check in checks).isoformat(),
        "checks": [
            {
                "lane": check.lane,
                "name": check.name,
                "status": check.status,
                "disposition": "required",
                "evidence_reference": f"{check.lane}/{check.name}",
                "reason_code": check.reason_code,
                "started_at": check.started_at.isoformat(),
                "finished_at": check.finished_at.isoformat(),
            }
            for check in checks
        ],
        "conditional_scenarios": "not_inferred_from_required_check_results",
        "owner_acceptance": "not_recorded",
        "publication": "not_verified",
    }
