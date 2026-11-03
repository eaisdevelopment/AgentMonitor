"""Observe a real current provider failure and recovery for at most 660 seconds.

No provider call is requested and no application state is changed. Without a
currently qualifying failure the command returns Not Run immediately. A past
recovery cannot manufacture historical dashboard availability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite.recovery import (
    SqliteCollectionRecoveryQueryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_scheduled_policy,
)
from agentmonitor.contracts.collection_recovery_v1 import (
    CollectionRecoveryQueryV1,
    CollectionRecoveryRunV1,
    CollectionRecoveryScopeV1,
)
from agentmonitor.modules.collection_control.domain.recovery_evidence import (
    committed_recovery_after,
    latest_natural_failure,
)

ROOT = Path(__file__).resolve().parents[3]
DATA = Path("/home/dev/.local/share/agentmonitor")
MAX_OBSERVATION_SECONDS = 600


@dataclass(frozen=True, slots=True)
class ServiceIdentityV1:
    pid: int
    invocation_id: str
    started_at: datetime


def _identity() -> ServiceIdentityV1:
    runtime = f"/run/user/{os.getuid()}"
    result = subprocess.run(
        [
            "/usr/bin/systemctl",
            "--user",
            "show",
            "agentmonitor-dashboard.service",
            "-p",
            "ActiveState",
            "-p",
            "MainPID",
            "-p",
            "InvocationID",
            "-p",
            "ExecMainStartTimestamp",
            "--no-pager",
        ],
        capture_output=True,
        timeout=5,
        check=False,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C",
            "TZ": "UTC",
            "XDG_RUNTIME_DIR": runtime,
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + runtime + "/bus",
        },
    )
    if result.returncode or len(result.stdout) > 4096:
        raise ValueError("m6_recovery_service_unavailable")
    values = dict(
        line.split("=", 1) for line in result.stdout.decode("ascii").splitlines()
    )
    if (
        values.get("ActiveState") != "active"
        or not re.fullmatch(r"[a-f0-9]{32}", values.get("InvocationID", ""))
        or not values.get("MainPID", "").isdigit()
        or int(values["MainPID"]) <= 1
    ):
        raise ValueError("m6_recovery_service_unavailable")
    stamp = values["ExecMainStartTimestamp"]
    if not stamp.endswith((" UTC", " GMT")):
        raise ValueError("m6_recovery_service_time_unavailable")
    started = datetime.strptime(stamp[:-4], "%a %Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return ServiceIdentityV1(int(values["MainPID"]), values["InvocationID"], started)


def _dashboard_probe(revision: str) -> datetime:
    result = subprocess.run(
        [
            "/usr/bin/node",
            "frontend/tests/browser/m6/probe_recovery_continuity.mjs",
            revision,
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=25,
        check=False,
    )
    if result.returncode or len(result.stdout) > 4096:
        raise ValueError("m6_recovery_dashboard_unavailable")
    value = json.loads(result.stdout)
    if (
        set(value) != {"record_type", "status", "source_revision", "observed_at"}
        or value["record_type"] != "agentmonitor.m6_recovery_dashboard_probe.v1"
        or value["status"] != "passed"
        or value["source_revision"] != revision
    ):
        raise ValueError("m6_recovery_dashboard_unavailable")
    observed = datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
    now = datetime.now(UTC)
    if (
        observed.utcoffset() != timedelta(0)
        or not now - timedelta(seconds=30) <= observed <= now
    ):
        raise ValueError("m6_recovery_dashboard_time_invalid")
    return observed


def _scopes(reference: DatabaseRefV1) -> tuple[CollectionRecoveryScopeV1, ...]:
    registry = SqliteRegistryRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    policy = ollama_cloud_scheduled_policy()
    accounts = registry.list_accounts("ollama", page_size=101)
    if len(accounts) > 100:
        raise ValueError("m6_recovery_target_limit")
    result = []
    for account in accounts:
        if account.lifecycle != "active" or not account.is_effective_monitoring_enabled:
            continue
        graph = cloud.read_monitoring_target(account.account_id)
        if (
            graph is None
            or graph.lifecycle != "active"
            or graph.identity_state != "owner_confirmed"
        ):
            continue
        receipt = cloud.read_current_verification(graph.binding)
        if (
            receipt is None
            or receipt.access_target_id != graph.access_target_id
            or receipt.binding != graph.binding
            or receipt.source_id != policy.source_id
            or receipt.adapter_version != policy.adapter_version
            or receipt.manifest_fingerprint != policy.source_fingerprint
        ):
            continue
        result.append(
            CollectionRecoveryScopeV1(
                account.account_id,
                graph.access_target_id,
                graph.binding.generation,
                policy.capability_id,
                policy.source_id,
                policy.adapter_version,
                policy.source_fingerprint,
                policy.payload_schema,
                "ollama",
            )
        )
    return tuple(result)


def _runs(
    repository: SqliteCollectionRecoveryQueryV1,
    provider: str,
    start: datetime,
    end: datetime,
    scope: CollectionRecoveryScopeV1 | None = None,
) -> tuple[CollectionRecoveryRunV1, ...]:
    result = repository.read_recovery_runs(
        CollectionRecoveryQueryV1(provider, start, end, scope, 500)
    )
    if result.has_more:
        raise ValueError("m6_recovery_history_incomplete")
    return result.items


def _committed_in_interval(
    runs: tuple[CollectionRecoveryRunV1, ...], start: datetime
) -> CollectionRecoveryRunV1 | None:
    return next(
        (
            item
            for item in runs
            if item.capability_id == "subscription.quota"
            and item.requested_at >= start
            and item.state in {"succeeded", "partial"}
            and item.payload_digest is not None
            and bool(item.observation_ids)
        ),
        None,
    )


def observe_recovery_interval(revision: str) -> dict[str, object]:
    """Only actual service/HTTP/run observations can produce positive counts."""
    if re.fullmatch(r"[a-f0-9]{40}", revision) is None:
        raise ValueError("m6_recovery_revision_invalid")
    began = datetime.now(UTC)
    deadline = time.monotonic() + MAX_OBSERVATION_SECONDS
    result: dict[str, object] = {
        "record_type": "agentmonitor.m6_recovery_interval.v1",
        "schema_version": "1.0.0",
        "status": "not_run",
        "reason_code": "m6_recovery_current_natural_failure_absent",
        "source_revision": revision,
        "service_invocation_id": None,
        "natural_recovery_targets": 0,
        "cross_provider_continuity_targets": 0,
        "dashboard_sample_count": 0,
        "started_at": began.isoformat(),
        "completed_at": began.isoformat(),
        "lineage_sha256": hashlib.sha256(b"").hexdigest(),
        "dashboard_observed_at": [],
        "continuity_run_ids": [],
        "recovery_run_pairs": [],
    }
    try:
        identity = _identity()
        result["service_invocation_id"] = identity.invocation_id
        reference = DatabaseRefV1(DATA / "agentmonitor.db", DATA)
        repository = SqliteCollectionRecoveryQueryV1(reference)
        start = max(identity.started_at, began - timedelta(hours=23))
        candidates = []
        for scope in _scopes(reference):
            failure = latest_natural_failure(
                _runs(repository, "ollama", start, began, scope), scope
            )
            if failure is not None:
                candidates.append((scope, failure))
        if not candidates:
            return result
        first_probe = _dashboard_probe(revision)
        if _identity() != identity:
            raise ValueError("m6_recovery_service_changed")
        # It must still be a failed target while the first real UI probe occurs.
        candidates = [
            (scope, failure)
            for scope, failure in candidates
            if latest_natural_failure(
                _runs(repository, "ollama", start, datetime.now(UTC), scope), scope
            )
            == failure
        ]
        if not candidates:
            return result
        result["dashboard_sample_count"] = 1
        probe_times = [first_probe.isoformat()]
        result["dashboard_observed_at"] = probe_times
        samples = 1
        recovered: dict[CollectionRecoveryScopeV1, CollectionRecoveryRunV1] = {}
        while time.monotonic() < deadline:
            time.sleep(min(15, max(0, deadline - time.monotonic())))
            if _identity() != identity:
                raise ValueError("m6_recovery_service_changed")
            observed = _dashboard_probe(revision)
            samples += 1
            probe_times.append(observed.isoformat())
            result["dashboard_sample_count"] = samples
            if _identity() != identity:
                raise ValueError("m6_recovery_service_changed")
            current_scopes = _scopes(reference)
            if any(scope not in current_scopes for scope, _ in candidates):
                raise ValueError("m6_recovery_scope_changed")
            for scope, failed in candidates:
                recovery = committed_recovery_after(
                    _runs(repository, "ollama", start, observed, scope),
                    failed,
                    scope,
                )
                if recovery is not None and recovery.completed_at >= first_probe:
                    recovered[scope] = recovery
            if not recovered:
                continue
            continuity_runs = tuple(
                _committed_in_interval(
                    _runs(repository, provider, first_probe, observed), first_probe
                )
                for provider in ("claude", "codex")
            )
            if all(item is not None for item in continuity_runs):
                continuity_ids = [
                    (item.provider_key, item.run_id.value)
                    for item in continuity_runs
                    if item is not None
                ]
                recovery_pairs = [
                    (failure.run_id.value, recovered[scope].run_id.value)
                    for scope, failure in candidates
                    if scope in recovered
                ]
                lines = [
                    revision,
                    identity.invocation_id,
                    first_probe.isoformat(),
                    observed.isoformat(),
                ]
                lines.extend(probe_times)
                for provider, run_id in continuity_ids:
                    lines.extend((provider, run_id))
                for scope, failure in candidates:
                    if scope in recovered:
                        lines.extend(
                            (
                                scope.account_id.value,
                                scope.access_target_id.value,
                                str(scope.binding_generation),
                                scope.source_fingerprint,
                                failure.run_id.value,
                                recovered[scope].run_id.value,
                            )
                        )
                result.update(
                    status="passed",
                    reason_code="m6_recovery_observed",
                    natural_recovery_targets=len(recovered),
                    cross_provider_continuity_targets=len(recovered),
                    dashboard_sample_count=samples,
                    continuity_run_ids=continuity_ids,
                    recovery_run_pairs=recovery_pairs,
                    lineage_sha256=hashlib.sha256(
                        "\0".join(lines).encode()
                    ).hexdigest(),
                )
                return result
        result.update(
            status="not_run",
            reason_code="m6_recovery_interval_incomplete",
            dashboard_sample_count=samples,
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        TimeoutError,
        subprocess.SubprocessError,
        KeyError,
        TypeError,
    ):
        result.update(
            status="blocked", reason_code="m6_recovery_observation_unavailable"
        )
    finally:
        result["completed_at"] = datetime.now(UTC).isoformat()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    result = observe_recovery_interval(args.revision)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
