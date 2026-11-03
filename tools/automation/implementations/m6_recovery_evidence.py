"""Pure fail-closed validation of one gate-owned bounded observation result."""

import re
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from typing import Literal


@dataclass(frozen=True, slots=True)
class RecoveryIntervalEvidenceV1:
    record_type: str
    schema_version: str
    status: Literal["passed", "not_run", "blocked"]
    reason_code: str
    source_revision: str
    service_invocation_id: str | None
    natural_recovery_targets: int
    cross_provider_continuity_targets: int
    dashboard_sample_count: int
    lineage_sha256: str
    started_at: str
    completed_at: str
    dashboard_observed_at: tuple[str, ...]
    continuity_run_ids: tuple[tuple[str, str], ...]
    recovery_run_pairs: tuple[tuple[str, str], ...]


def parse_recovery_interval_v1(
    value: object,
    *,
    revision: str,
    return_code: int,
    now: datetime,
) -> RecoveryIntervalEvidenceV1:
    """Validate only supplied facts; no files, processes or HTTP behavior."""
    try:
        if not isinstance(value, dict) or set(value) != {
            field.name for field in fields(RecoveryIntervalEvidenceV1)
        }:
            raise ValueError
        value = dict(value)
        for key in (
            "dashboard_observed_at",
            "continuity_run_ids",
            "recovery_run_pairs",
        ):
            if not isinstance(value[key], list) or len(value[key]) > 100:
                raise ValueError
        value["dashboard_observed_at"] = tuple(value["dashboard_observed_at"])
        for key in ("continuity_run_ids", "recovery_run_pairs"):
            if any(
                not isinstance(item, list)
                or len(item) != 2
                or any(
                    not isinstance(part, str) or not 1 <= len(part) <= 128
                    for part in item
                )
                for item in value[key]
            ):
                raise ValueError
            value[key] = tuple(tuple(item) for item in value[key])
        result = RecoveryIntervalEvidenceV1(**value)
        start = datetime.fromisoformat(result.started_at)
        end = datetime.fromisoformat(result.completed_at)
        samples = tuple(
            datetime.fromisoformat(value) for value in result.dashboard_observed_at
        )
        if (
            len(samples) != result.dashboard_sample_count
            or any(
                sample.utcoffset() != timedelta(0) or not start <= sample <= end
                for sample in samples
            )
            or any(
                left >= right for left, right in zip(samples, samples[1:], strict=False)
            )
        ):
            raise ValueError
        allowed = {
            "passed": {"m6_recovery_observed"},
            "not_run": {
                "m6_recovery_current_natural_failure_absent",
                "m6_recovery_interval_incomplete",
            },
            "blocked": {"m6_recovery_observation_unavailable"},
        }
        if (
            result.record_type != "agentmonitor.m6_recovery_interval.v1"
            or result.schema_version != "1.0.0"
            or result.reason_code not in allowed.get(result.status, set())
            or result.source_revision != revision
            or re.fullmatch(r"[a-f0-9]{40}", revision) is None
            or result.service_invocation_id is not None
            and re.fullmatch(r"[a-f0-9]{32}", result.service_invocation_id) is None
            or re.fullmatch(r"[a-f0-9]{64}", result.lineage_sha256) is None
            or start.utcoffset() != timedelta(0)
            or end.utcoffset() != timedelta(0)
            or now.utcoffset() != timedelta(0)
            or not start <= end <= start + timedelta(seconds=660)
            or not now - timedelta(seconds=30) <= end <= now
            or return_code != (0 if result.status == "passed" else 3)
            or any(
                type(count) is not int or count < 0
                for count in (
                    result.natural_recovery_targets,
                    result.cross_provider_continuity_targets,
                    result.dashboard_sample_count,
                )
            )
            or result.natural_recovery_targets != len(result.recovery_run_pairs)
            or result.natural_recovery_targets
            != result.cross_provider_continuity_targets
        ):
            raise ValueError
        if result.status == "passed":
            if (
                result.service_invocation_id is None
                or result.dashboard_sample_count < 2
                or result.natural_recovery_targets < 1
                or tuple(item[0] for item in result.continuity_run_ids)
                != ("claude", "codex")
                or len({item for pair in result.recovery_run_pairs for item in pair})
                != 2 * result.natural_recovery_targets
            ):
                raise ValueError
        elif (
            result.natural_recovery_targets
            or result.cross_provider_continuity_targets
            or result.continuity_run_ids
        ):
            raise ValueError
        return result
    except (ValueError, TypeError, AttributeError):
        raise ValueError("m6_recovery_interval_evidence_invalid") from None
