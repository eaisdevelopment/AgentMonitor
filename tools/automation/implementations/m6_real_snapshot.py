"""Read a privacy-minimized M6 evidence snapshot from the real local database.

This helper is intentionally read-only.  It uses module-owned query ports and
emits only bounded statuses and aggregate counts; account identifiers, names,
quota values, provider payloads and credentials never cross this boundary.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectActiveSchemaCompatibilityV1,
)
from agentmonitor.adapters.persistence.alerting.sqlite.actions import (
    SqliteAlertActionRepositoryV1,
)
from agentmonitor.adapters.persistence.alerting.sqlite.repository import (
    SqliteAlertingRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.cloud_schedule_status import (
    SqliteCloudScheduleStatusV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (
    SqliteRuntimeObservationRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.probe_descriptor import (
    ollama_cloud_scheduled_policy,
)
from agentmonitor.contracts.alerting_v1 import (
    AlertListQueryV1,
    AlertRuleListQueryV1,
    AlertRuleViewV1,
    AlertScopeRefV1,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityHistoryMetricV1,
    CapacityHistoryQueryV1,
    CapacitySubjectV2,
    QuotaWindowViewV1OrV2,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionRunViewV1,
    OllamaCloudLatestSourceSignalQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1,
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
    CredentialBindingAggregateV1,
)

SnapshotStatusV1 = Literal["passed", "blocked", "not_run"]


@dataclass(frozen=True, slots=True)
class M6EvidenceSnapshotV1:
    """Closed sanitized facts consumed by the canonical completion gate."""

    status: SnapshotStatusV1
    reason_code: str
    schema_state: str
    active_ollama_accounts: int = 0
    registered_local_installations: int = 0
    observed_local_installations: int = 0
    active_cloud_targets: int = 0
    owner_confirmed_cloud_targets: int = 0
    verified_cloud_targets: int = 0
    current_balance_targets: int = 0
    history_targets: int = 0
    configured_alert_targets: int = 0
    alerted_targets: int = 0
    process_observation_count: int = 0
    natural_recovery_targets: int = 0
    cross_provider_continuity_targets: int = 0

    def __post_init__(self) -> None:
        counts = tuple(
            value
            for name, value in asdict(self).items()
            if name
            not in {
                "status",
                "reason_code",
                "schema_state",
            }
        )
        if (
            self.status not in {"passed", "blocked", "not_run"}
            or not self.reason_code.startswith("m6_snapshot_")
            or not self.schema_state
            or any(type(value) is not int or value < 0 for value in counts)
            or self.observed_local_installations
            > self.registered_local_installations
            or self.owner_confirmed_cloud_targets > self.active_cloud_targets
            or self.verified_cloud_targets > self.active_cloud_targets
            or self.current_balance_targets > self.verified_cloud_targets
            or self.history_targets > self.current_balance_targets
            or self.alerted_targets > self.configured_alert_targets
            or self.natural_recovery_targets > self.active_cloud_targets
            or self.cross_provider_continuity_targets
            > self.natural_recovery_targets
        ):
            raise ValueError("m6_snapshot_contract_invalid")

    @classmethod
    def not_run(
        cls, *, schema_state: str, reason_code: str
    ) -> M6EvidenceSnapshotV1:
        return cls("not_run", reason_code, schema_state)

    @classmethod
    def blocked(
        cls, *, schema_state: str, reason_code: str
    ) -> M6EvidenceSnapshotV1:
        return cls("blocked", reason_code, schema_state)

    def as_json(self) -> dict[str, object]:
        values = asdict(self)
        return {
            "schema_version": "1.0.0",
            "record_type": "agentmonitor.m6_real_snapshot.v1",
            "status": values.pop("status"),
            "reason_code": values.pop("reason_code"),
            "schema_state": values.pop("schema_state"),
            "counts": values,
        }


def _active_binding(
    aggregate: CredentialBindingAggregateV1,
) -> ActiveCredentialBindingRefV1 | None:
    active = tuple(item for item in aggregate.bindings if item.lifecycle == "active")
    if len(active) != 1:
        return None
    item = active[0]
    return ActiveCredentialBindingRefV1(
        account_id=aggregate.account_id,
        binding_id=item.binding_id,
        generation=item.generation,
    )


def _matching_schedule(
    graph: CloudMonitoringTargetV1,
    schedules: tuple[object, ...],
) -> bool:
    return any(
        getattr(item, "account_id", None) == graph.account_id.value
        and getattr(item, "profile_id", None) == graph.profile_id.value
        and getattr(item, "resource_id", None) == graph.resource_id.value
        and getattr(item, "access_target_id", None) == graph.access_target_id.value
        and getattr(item, "target_generation", None) == graph.binding.generation
        for item in schedules
    )


def _current_cloud_windows(
    capacity: SqliteCapacityRepositoryV1,
    graph: CloudMonitoringTargetV1,
    run_id: OpaqueIdV1,
    as_of: datetime,
) -> tuple[QuotaWindowViewV1OrV2, ...]:
    windows = capacity.list_quota_windows(
        graph.account_id,
        graph.resource_id,
        "subscription.quota",
        as_of,
    )
    return tuple(
        item
        for item in windows
        if isinstance(item.subject, CapacitySubjectV2)
        and item.subject.provider_key == "ollama"
        and item.subject.account_id == graph.account_id
        and item.subject.resource_id == graph.resource_id
        and item.subject.provider_target.target_kind == "cloud_service"
        and item.subject.provider_target.target_id == graph.access_target_id
        and item.collection_run_id == run_id
        and item.provenance.capability_id == "subscription.quota"
        and item.provenance.source_id == "ollama.cloud.balance.v1"
        and item.freshness == "fresh"
    )


def _has_history(
    capacity: SqliteCapacityRepositoryV1,
    graph: CloudMonitoringTargetV1,
    windows: tuple[QuotaWindowViewV1OrV2, ...],
    as_of: datetime,
) -> bool:
    for window in windows:
        metrics: tuple[CapacityHistoryMetricV1, ...] = tuple(
            metric
            for metric in ("remaining_ratio", "remaining", "used", "limit")
            if getattr(window, metric).availability.state in {"available", "stale"}
        )
        for metric in metrics:
            query = CapacityHistoryQueryV1(
                subject_id=graph.account_id,
                resource_id=graph.resource_id,
                window_id=window.window_id,
                metric=metric,
                series_kind="poll_snapshot",
                range_start=as_of - timedelta(days=365),
                range_before=as_of + timedelta(microseconds=1),
                as_of=as_of,
                limit=2,
                after_key=None,
                bucket_method=None,
                bucket_seconds=None,
            )
            points = capacity.recent_capacity_history(query, 2)
            exact = tuple(
                point
                for point in points
                if isinstance(point.subject, CapacitySubjectV2)
                and point.subject.provider_key == "ollama"
                and point.subject.account_id == graph.account_id
                and point.subject.resource_id == graph.resource_id
                and point.subject.provider_target.target_kind == "cloud_service"
                and point.subject.provider_target.target_id == graph.access_target_id
                and point.provenance.source_id == "ollama.cloud.balance.v1"
            )
            if len(exact) >= 2:
                return True
    return False


def _recovery_interval(
    runs: tuple[CollectionRunViewV1, ...],
) -> tuple[datetime, datetime] | None:
    """Return an actual older failure followed by a later successful request."""

    cloud = tuple(
        run
        for run in runs
        if run.source_id == "ollama.cloud.balance.v1"
        and run.capability_id == "subscription.quota"
    )
    for success in cloud:
        if success.state not in {"succeeded", "partial"}:
            continue
        older_failures = tuple(
            run
            for run in cloud
            if run.requested_at < success.requested_at
            and run.state in {"failed", "blocked", "cancelled", "unsupported"}
        )
        if older_failures:
            failure = max(older_failures, key=lambda item: item.requested_at)
            return failure.requested_at, success.requested_at
    return None


def _configured_alert_accounts(
    accounts: tuple[AccountViewV1, ...],
    rules: tuple[AlertRuleViewV1, ...],
) -> tuple[AccountViewV1, ...]:
    configured: list[AccountViewV1] = []
    for account in accounts:
        account_id = account.account_id
        organization_id = account.organization_id
        if any(
            rule.enabled
            and (
                rule.scope.scope_kind == "global"
                or (
                    rule.scope.scope_kind == "provider"
                    and rule.scope.scope_id == "ollama"
                )
                or (
                    rule.scope.scope_kind == "account"
                    and rule.scope.scope_id == account_id.value
                )
                or (
                    organization_id is not None
                    and rule.scope.scope_kind == "organization"
                    and rule.scope.scope_id == organization_id.value
                )
            )
            for rule in rules
        ):
            configured.append(account)
    return tuple(configured)


def read_m6_evidence_snapshot_v1(
    data_root: Path, *, as_of: datetime | None = None
) -> M6EvidenceSnapshotV1:
    """Read one bounded real snapshot; never creates, migrates or collects."""

    instant = as_of or datetime.now(UTC)
    if (
        not isinstance(data_root, Path)
        or not data_root.is_absolute()
        or instant.utcoffset() != timedelta(0)
    ):
        return M6EvidenceSnapshotV1.blocked(
            schema_state="unknown",
            reason_code="m6_snapshot_input_invalid",
        )
    try:
        reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
        schema_state, _ = InspectActiveSchemaCompatibilityV1(reference)
    except (OSError, TypeError, ValueError):
        return M6EvidenceSnapshotV1.blocked(
            schema_state="unreadable",
            reason_code="m6_snapshot_database_unavailable",
        )
    if schema_state != "compatible":
        status = (
            "not_run"
            if schema_state in {"missing", "empty", "upgrade_required"}
            else "blocked"
        )
        reason = "m6_snapshot_schema_" + schema_state
        if status == "not_run":
            return M6EvidenceSnapshotV1.not_run(
                schema_state=schema_state,
                reason_code=reason,
            )
        return M6EvidenceSnapshotV1.blocked(
            schema_state=schema_state,
            reason_code=reason,
        )

    try:
        registry = SqliteRegistryRepositoryV1(reference)
        binding_repository = SqliteCredentialBindingsV1(reference)
        cloud_registry = SqliteCloudCredentialRegistryV1(reference)
        admission = SqliteOllamaCloudAdmissionRepositoryV1(reference)
        capacity = SqliteCapacityRepositoryV1(reference)
        collection = SqliteCollectionRepositoryV1(reference)
        runtime = SqliteRuntimeObservationRepositoryV1(reference)
        policy = ollama_cloud_scheduled_policy()

        accounts = tuple(
            account
            for account in registry.list_accounts("ollama", page_size=201)
            if account.lifecycle == "active"
        )
        installations = registry.list_provider_installations(
            "ollama", page_size=201
        )
        if len(accounts) >= 201 or len(installations) >= 201:
            raise ValueError("m6_snapshot_registry_limit_exceeded")
        observed_installations = tuple(
            item
            for item in installations
            if item.presence_state == "present" and item.version.state == "known_masked"
        )
        schedules = SqliteCloudScheduleStatusV1(reference).list_registered()
        process_rows = runtime.list_processes("ollama", instant, 500)
        if len(process_rows) >= 500:
            raise ValueError("m6_snapshot_process_limit_exceeded")
        processes = tuple(
            item
            for item in process_rows
            if item.presence == "running"
        )
        other_runs = tuple(
            run
            for provider in ("claude", "codex")
            for run in collection.list_runs(provider, None, instant, 500)
            if run.state in {"succeeded", "partial"}
        )

        active_targets = 0
        owner_confirmed = 0
        verified = 0
        current = 0
        history = 0
        recovery = 0
        continuity = 0
        cloud_accounts: list[AccountViewV1] = []
        for account in accounts:
            aggregate = binding_repository.read(account.account_id)
            binding = _active_binding(aggregate)
            graph = cloud_registry.read_monitoring_target(account.account_id)
            if graph is None or graph.lifecycle != "active":
                continue
            active_targets += 1
            cloud_accounts.append(account)
            if (
                graph.identity_state != "owner_confirmed"
                or binding is None
                or graph.binding != binding
            ):
                continue
            owner_confirmed += 1
            receipt = cloud_registry.read_current_verification(binding)
            if (
                receipt is None
                or not account.is_effective_monitoring_enabled
                or receipt.access_target_id != graph.access_target_id
                or receipt.binding != binding
                or receipt.source_id != policy.source_id
                or receipt.adapter_version != policy.adapter_version
                or receipt.manifest_fingerprint != policy.source_fingerprint
                or not _matching_schedule(graph, schedules)
            ):
                continue
            verified += 1
            signal = admission.read_latest_source_signal(
                OllamaCloudLatestSourceSignalQueryV1(
                    account_id=account.account_id,
                    binding_generation=binding.generation,
                    access_target_id=graph.access_target_id,
                    capability_id=policy.capability_id,
                    source_id=policy.source_id,
                    adapter_version=policy.adapter_version,
                    source_fingerprint=policy.source_fingerprint,
                    payload_schema=policy.payload_schema,
                    queried_at=instant,
                )
            )
            if signal.signal != "verified_success" or signal.run_id is None:
                continue
            windows = _current_cloud_windows(
                capacity, graph, signal.run_id, instant
            )
            if not windows:
                continue
            current += 1
            if _has_history(capacity, graph, windows, instant):
                history += 1

            account_runs = collection.list_runs(
                "ollama", account.account_id, instant, 500
            )
            interval = _recovery_interval(account_runs)
            if interval is not None:
                recovery += 1
                start, end = interval
                if any(start <= run.requested_at <= end for run in other_runs):
                    continuity += 1

        alert_rules_page = SqliteAlertingRepositoryV1(reference).list_rules(
            AlertRuleListQueryV1(
                as_of=instant,
                condition_type="capacity_remaining",
                include_archived=False,
                limit=200,
            )
        )
        if alert_rules_page.has_more:
            raise ValueError("m6_snapshot_alert_rule_limit_exceeded")
        configured_accounts = _configured_alert_accounts(
            tuple(cloud_accounts), alert_rules_page.items
        )
        alert_repository = SqliteAlertActionRepositoryV1(reference)
        alerted = sum(
            bool(
                alert_repository.list_alerts(
                    AlertListQueryV1(
                        as_of=instant,
                        condition_type="capacity_remaining",
                        scope=AlertScopeRefV1("account", account.account_id.value),
                        limit=1,
                    )
                ).items
            )
            for account in configured_accounts
        )

        return M6EvidenceSnapshotV1(
            status="passed",
            reason_code="m6_snapshot_query_complete",
            schema_state=schema_state,
            active_ollama_accounts=len(accounts),
            registered_local_installations=len(installations),
            observed_local_installations=len(observed_installations),
            active_cloud_targets=active_targets,
            owner_confirmed_cloud_targets=owner_confirmed,
            verified_cloud_targets=verified,
            current_balance_targets=current,
            history_targets=history,
            configured_alert_targets=len(configured_accounts),
            alerted_targets=alerted,
            process_observation_count=len(processes),
            natural_recovery_targets=recovery,
            cross_provider_continuity_targets=continuity,
        )
    except (OSError, TypeError, ValueError):
        return M6EvidenceSnapshotV1.blocked(
            schema_state=schema_state,
            reason_code="m6_snapshot_query_unavailable",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args(argv)
    snapshot = read_m6_evidence_snapshot_v1(args.data_root)
    print(json.dumps(snapshot.as_json(), sort_keys=True, separators=(",", ":")))
    return 0 if snapshot.status == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
