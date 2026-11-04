"""Pure controlled-network evidence policy; never proves natural provider failure."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentmonitor.contracts.collection_recovery_v1 import (
        CollectionRecoveryRunV1,
        CollectionRecoveryScopeV1,
    )


@dataclass(frozen=True, slots=True)
class ControlledNetworkWitnessV1:
    attempt_id: str
    source_revision: str
    service_invocation_id: str
    worker_pid: int
    worker_start_ticks: int
    parent_namespace_inode: int
    worker_namespace_inode: int
    failure_run_id: str
    started_at: datetime
    completed_at: datetime
    cleanup_confirmed: bool


@dataclass(frozen=True, slots=True)
class ControlledRecoveryEvidenceV1:
    record_type: str
    schema_version: str
    status: str
    reason_code: str
    source_revision: str
    service_invocation_id: str
    attempt_id: str
    controlled_recovery_targets: int
    cross_provider_continuity_targets: int
    dashboard_sample_count: int
    lineage_sha256: str
    scope_sha256: str
    started_at: str
    completed_at: str
    dashboard_observed_at: tuple[str, ...]
    continuity_run_ids: tuple[tuple[str, str], ...]
    recovery_run_pairs: tuple[tuple[str, str], ...]
    worker_pid: int
    worker_start_ticks: int
    parent_namespace_inode: int
    worker_namespace_inode: int
    cleanup_confirmed: bool
    isolation_started_at: str
    isolation_completed_at: str
    failure_completed_at: str
    recovery_completed_at: str

    @property
    def natural_recovery_targets(self) -> int:
        return 0


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _lineage(value: dict) -> str:
    return _digest(
        {key: item for key, item in value.items() if key != "lineage_sha256"}
    )


def build_controlled_recovery_evidence_v1(
    *,
    revision: str,
    service_invocation_id: str,
    attempt_id: str,
    scope: CollectionRecoveryScopeV1,
    witness: ControlledNetworkWitnessV1,
    failure: CollectionRecoveryRunV1,
    recovery: CollectionRecoveryRunV1,
    dashboard_observed_at: tuple[datetime, ...],
    continuity_runs: tuple[CollectionRecoveryRunV1, ...],
    now: datetime,
) -> ControlledRecoveryEvidenceV1:
    """Classify supplied terminal facts; caller owns authentic boundary acquisition."""
    try:
        if (
            not isinstance(witness, ControlledNetworkWitnessV1)
            or witness.attempt_id != attempt_id
            or witness.source_revision != revision
            or witness.service_invocation_id != service_invocation_id
            or witness.failure_run_id != failure.run_id.value
            or scope.provider_key != "ollama"
            or not all(_matches(run, scope) for run in (failure, recovery))
            or not witness.started_at
            <= failure.requested_at
            <= failure.completed_at
            <= witness.completed_at
            or not witness.completed_at
            < recovery.requested_at
            <= recovery.completed_at
            <= now
            or failure.state != "failed"
            or failure.dispatch_certainty not in {"not_started", "may_have_started"}
            or failure.response_outcome is not None
            or failure.failure_code != "provider_unavailable"
            or failure.payload_digest is not None
            or failure.observation_ids
            or not _committed(recovery)
            or len(continuity_runs) != 2
            or {run.provider_key for run in continuity_runs} != {"claude", "codex"}
            or any(
                not _continuity_committed(run)
                or not witness.started_at <= run.requested_at <= run.completed_at <= now
                for run in continuity_runs
            )
        ):
            raise ValueError
        result = ControlledRecoveryEvidenceV1(
            record_type="agentmonitor.m6_controlled_recovery_interval.v1",
            schema_version="1.0.0",
            status="passed",
            reason_code="m6_controlled_network_recovery_observed",
            source_revision=revision,
            service_invocation_id=service_invocation_id,
            attempt_id=attempt_id,
            controlled_recovery_targets=1,
            cross_provider_continuity_targets=1,
            dashboard_sample_count=len(dashboard_observed_at),
            lineage_sha256="",
            scope_sha256=_digest(asdict(scope)),
            started_at=witness.started_at.isoformat(),
            completed_at=now.isoformat(),
            dashboard_observed_at=tuple(
                sample.isoformat() for sample in dashboard_observed_at
            ),
            continuity_run_ids=tuple(
                sorted((run.provider_key, run.run_id.value) for run in continuity_runs)
            ),
            recovery_run_pairs=((failure.run_id.value, recovery.run_id.value),),
            worker_pid=witness.worker_pid,
            worker_start_ticks=witness.worker_start_ticks,
            parent_namespace_inode=witness.parent_namespace_inode,
            worker_namespace_inode=witness.worker_namespace_inode,
            cleanup_confirmed=witness.cleanup_confirmed,
            isolation_started_at=witness.started_at.isoformat(),
            isolation_completed_at=witness.completed_at.isoformat(),
            failure_completed_at=failure.completed_at.isoformat(),
            recovery_completed_at=recovery.completed_at.isoformat(),
        )
        value = asdict(result)
        value["lineage_sha256"] = _lineage(value)
        return parse_controlled_recovery_interval_v1(
            json.loads(json.dumps(value)),
            revision=revision,
            service_invocation_id=service_invocation_id,
            attempt_id=attempt_id,
            return_code=0,
            now=now,
        )
    except (ValueError, TypeError, AttributeError):
        raise ValueError("m6_controlled_recovery_evidence_invalid") from None


def parse_controlled_recovery_interval_v1(
    value: object,
    *,
    revision: str,
    service_invocation_id: str,
    attempt_id: str,
    return_code: int,
    now: datetime,
) -> ControlledRecoveryEvidenceV1:
    """Consume a fresh receipt bound to the gate's independently generated nonce."""
    try:
        if not isinstance(value, dict) or set(value) != {
            field.name for field in fields(ControlledRecoveryEvidenceV1)
        }:
            raise ValueError
        data = dict(value)
        for key in (
            "dashboard_observed_at",
            "continuity_run_ids",
            "recovery_run_pairs",
        ):
            if not isinstance(data[key], list) or len(data[key]) > 100:
                raise ValueError
        for key in ("continuity_run_ids", "recovery_run_pairs"):
            if any(
                not isinstance(pair, list)
                or len(pair) != 2
                or any(
                    not isinstance(item, str)
                    or re.fullmatch(r"[A-Za-z0-9_.:@-]{1,128}", item) is None
                    for item in pair
                )
                for pair in data[key]
            ):
                raise ValueError
            data[key] = tuple(tuple(pair) for pair in data[key])
        data["dashboard_observed_at"] = tuple(data["dashboard_observed_at"])
        result = ControlledRecoveryEvidenceV1(**data)
        start, end, isolation_start, isolation_end, failed, recovered = (
            _utc_time(getattr(result, key))
            for key in (
                "started_at",
                "completed_at",
                "isolation_started_at",
                "isolation_completed_at",
                "failure_completed_at",
                "recovery_completed_at",
            )
        )
        samples = tuple(_utc_time(sample) for sample in result.dashboard_observed_at)
        if (
            result.record_type != "agentmonitor.m6_controlled_recovery_interval.v1"
            or result.schema_version != "1.0.0"
            or result.status != "passed"
            or result.reason_code != "m6_controlled_network_recovery_observed"
            or result.source_revision != revision
            or result.service_invocation_id != service_invocation_id
            or result.attempt_id != attempt_id
            or any(
                not isinstance(value, str) or re.fullmatch(pattern, value) is None
                for pattern, value in (
                    (r"[a-f0-9]{40}", revision),
                    (r"[a-f0-9]{32}", service_invocation_id),
                    (r"[a-f0-9]{32}", attempt_id),
                    (r"[a-f0-9]{64}", result.scope_sha256),
                    (r"[a-f0-9]{64}", result.lineage_sha256),
                )
            )
            or _lineage(data) != result.lineage_sha256
            or type(return_code) is not int
            or return_code != 0
            or not isinstance(now, datetime)
            or now.utcoffset() != timedelta(0)
            or not start
            == isolation_start
            <= failed
            <= isolation_end
            < recovered
            <= end
            or not start <= end <= start + timedelta(seconds=660)
            or not now - timedelta(seconds=30) <= end <= now
            or any(
                type(count) is not int or count < 1
                for count in (
                    result.controlled_recovery_targets,
                    result.cross_provider_continuity_targets,
                    result.dashboard_sample_count,
                    result.worker_pid,
                    result.worker_start_ticks,
                    result.parent_namespace_inode,
                    result.worker_namespace_inode,
                )
            )
            or result.controlled_recovery_targets != 1
            or result.cross_provider_continuity_targets != 1
            or result.parent_namespace_inode == result.worker_namespace_inode
            or result.cleanup_confirmed is not True
            or result.dashboard_sample_count != len(samples)
            or len(samples) < 2
            or any(not start <= sample <= end for sample in samples)
            or any(
                left >= right for left, right in zip(samples, samples[1:], strict=False)
            )
            or not any(failed <= sample < recovered for sample in samples)
            or not any(recovered <= sample for sample in samples)
            or len(result.recovery_run_pairs) != 1
            or tuple(pair[0] for pair in result.continuity_run_ids)
            != ("claude", "codex")
        ):
            raise ValueError
        run_ids = tuple(
            item for pair in result.recovery_run_pairs for item in pair
        ) + tuple(pair[1] for pair in result.continuity_run_ids)
        if len(set(run_ids)) != 4:
            raise ValueError
        return result
    except (ValueError, TypeError, AttributeError, KeyError):
        raise ValueError("m6_controlled_recovery_evidence_invalid") from None


def _utc_time(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.utcoffset() != timedelta(0):
        raise ValueError
    return result


def _matches(run: CollectionRecoveryRunV1, scope: CollectionRecoveryScopeV1) -> bool:
    return run.provider_target_kind == "cloud_service" and all(
        getattr(run, field.name) == getattr(scope, field.name)
        for field in fields(scope)
    )


def _committed(run: CollectionRecoveryRunV1) -> bool:
    return (
        run.state in {"succeeded", "partial"}
        and run.dispatch_certainty == "response_received"
        and run.response_outcome == "succeeded"
        and run.failure_code is None
        and run.payload_digest is not None
        and bool(run.observation_ids)
    )


def _continuity_committed(run: CollectionRecoveryRunV1) -> bool:
    """Claude/Codex quota commits do not carry Ollama dispatch metadata."""
    return (
        run.capability_id == "subscription.quota"
        and run.state in {"succeeded", "partial"}
        and run.payload_digest is not None
        and bool(run.observation_ids)
    )
