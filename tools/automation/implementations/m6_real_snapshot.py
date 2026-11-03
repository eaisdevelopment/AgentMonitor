"""Read a privacy-minimized M6 evidence snapshot from the real local database.

This helper is intentionally read-only.  It uses module-owned query ports and
emits only bounded statuses and aggregate counts; account identifiers, names,
quota values, provider payloads and credentials never cross this boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

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
from agentmonitor.adapters.persistence.collection_control.sqlite.cloud_schedule_status import (  # noqa: E501
    SqliteCloudScheduleStatusV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.ollama_cloud_admission import (  # noqa: E501
    SqliteOllamaCloudAdmissionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.coverage import (
    SqliteOrganizationProviderCoverageRepositoryV1,
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
    AlertHistoryQueryV1,
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
    OllamaCloudLatestSourceSignalQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_coverage_v1 import (
    OrganizationProviderCoverageReadPortV1,
    OrganizationProviderCoverageSelectionV1,
    OrganizationProviderCoverageSnapshotV1,
)
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1,
    ActiveCredentialBindingRefV1,
    CloudMonitoringTargetV1,
    CredentialBindingAggregateV1,
)

from tools.automation.implementations.m6_direct_evidence import (
    CloudOrganizationScopeV1,
    CloudScopeEvidenceV1,
    cloud_reference_digest_v1,
)

SnapshotStatusV1 = Literal["passed", "blocked", "not_run"]
_EMPTY_LINEAGE_SHA256 = hashlib.sha256(b"").hexdigest()


def _lineage_digest(rows: set[tuple[str, ...]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows):
        digest.update("\0".join(row).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


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
    owner_confirmed_required_scopes: int = 0
    verified_cloud_targets: int = 0
    current_balance_targets: int = 0
    history_targets: int = 0
    configured_alert_targets: int = 0
    alerted_targets: int = 0
    process_observation_count: int = 0
    natural_recovery_targets: int = 0
    cross_provider_continuity_targets: int = 0
    current_balance_lineage_sha256: str = _EMPTY_LINEAGE_SHA256
    current_history_lineage_sha256: str = _EMPTY_LINEAGE_SHA256
    cloud_scope_evidence: CloudScopeEvidenceV1 | None = None

    def __post_init__(self) -> None:
        counts = (
            self.active_ollama_accounts,
            self.registered_local_installations,
            self.observed_local_installations,
            self.active_cloud_targets,
            self.owner_confirmed_cloud_targets,
            self.owner_confirmed_required_scopes,
            self.verified_cloud_targets,
            self.current_balance_targets,
            self.history_targets,
            self.configured_alert_targets,
            self.alerted_targets,
            self.process_observation_count,
            self.natural_recovery_targets,
            self.cross_provider_continuity_targets,
        )
        if (
            self.status not in {"passed", "blocked", "not_run"}
            or not self.reason_code.startswith("m6_snapshot_")
            or not self.schema_state
            or any(type(value) is not int or value < 0 for value in counts)
            or self.observed_local_installations > self.registered_local_installations
            or self.owner_confirmed_cloud_targets > self.active_cloud_targets
            or self.verified_cloud_targets > self.active_cloud_targets
            or self.current_balance_targets > self.verified_cloud_targets
            or self.history_targets > self.current_balance_targets
            or self.alerted_targets > self.configured_alert_targets
            or self.natural_recovery_targets > self.active_cloud_targets
            or self.cross_provider_continuity_targets > self.natural_recovery_targets
            or any(
                len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
                for value in (
                    self.current_balance_lineage_sha256,
                    self.current_history_lineage_sha256,
                )
            )
        ):
            raise ValueError("m6_snapshot_contract_invalid")

    @classmethod
    def not_run(cls, *, schema_state: str, reason_code: str) -> M6EvidenceSnapshotV1:
        return cls("not_run", reason_code, schema_state)

    @classmethod
    def blocked(cls, *, schema_state: str, reason_code: str) -> M6EvidenceSnapshotV1:
        return cls("blocked", reason_code, schema_state)

    def as_json(self) -> dict[str, object]:
        values = asdict(self)
        values.pop("cloud_scope_evidence")
        digests = {
            "current_balance_lineage_sha256": values.pop(
                "current_balance_lineage_sha256"
            ),
            "current_history_lineage_sha256": values.pop(
                "current_history_lineage_sha256"
            ),
        }
        return {
            "schema_version": "1.0.0",
            "record_type": "agentmonitor.m6_real_snapshot.v1",
            "status": values.pop("status"),
            "reason_code": values.pop("reason_code"),
            "schema_state": values.pop("schema_state"),
            "counts": values,
            "digests": digests,
            "cloud_scope_evidence": (
                self.cloud_scope_evidence.as_json()
                if self.cloud_scope_evidence is not None
                else None
            ),
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


def _current_history_lineage(
    capacity: SqliteCapacityRepositoryV1,
    graph: CloudMonitoringTargetV1,
    windows: tuple[QuotaWindowViewV1OrV2, ...],
    as_of: datetime,
) -> set[tuple[str, ...]]:
    """Return only current observations proven present in retained history."""

    lineage: set[tuple[str, ...]] = set()
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
                range_before=as_of,
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
                and point.window_id == window.window_id
            )
            if (
                len(exact) >= 2
                and len({point.observation_id for point in exact}) >= 2
                and len({point.collection_run_id for point in exact}) >= 2
                and sum(
                    point.observation_id == window.current_observation_id
                    and point.collection_run_id == window.collection_run_id
                    for point in exact
                )
                == 1
            ):
                lineage.add(
                    (
                        graph.account_id.value,
                        graph.resource_id.value,
                        graph.access_target_id.value,
                        window.window_id.value,
                        window.current_observation_id.value,
                        window.collection_run_id.value,
                    )
                )
                break
    return lineage


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


def _has_deduplicated_current_observation_alert(
    repository: SqliteAlertActionRepositoryV1,
    account: AccountViewV1,
    observation_ids: frozenset[OpaqueIdV1],
    as_of: datetime,
) -> bool:
    """Require one durable transition per matching current alert source event."""

    if not observation_ids:
        return False
    page = repository.list_alerts(
        AlertListQueryV1(
            as_of=as_of,
            condition_type="capacity_remaining",
            scope=AlertScopeRefV1("account", account.account_id.value),
            limit=200,
        )
    )
    if page.has_more:
        raise ValueError("m6_snapshot_alert_limit_exceeded")
    matching = tuple(
        alert
        for alert in page.items
        if alert.subject.provider_key == "ollama"
        and alert.subject.account_id == account.account_id
        and bool(observation_ids.intersection(alert.decision.source.observation_ids))
    )
    if not matching:
        return False
    event_keys: list[tuple[str, str]] = []
    for alert in matching:
        source_event_id = alert.decision.source.event_id
        if not isinstance(source_event_id, OpaqueIdV1):
            return False
        history = repository.list_history(
            AlertHistoryQueryV1(alert.alert_id, as_of, 200)
        )
        if history.has_more:
            raise ValueError("m6_snapshot_alert_history_limit_exceeded")
        if sum(item.source_event_id == source_event_id for item in history.items) != 1:
            return False
        rule_key = (
            alert.rule.rule_id.value
            if alert.rule.rule_id is not None
            else alert.rule.builtin_policy_version
        )
        if rule_key is None:
            return False
        event_keys.append((rule_key, source_event_id.value))
    return len(set(event_keys)) == len(event_keys)


def cloud_scope_evidence_from_registry_v1(
    snapshot: OrganizationProviderCoverageSnapshotV1,
    active_targets: dict[OpaqueIdV1, str],
    owner_confirmed_targets: set[str],
    verified_targets: set[str],
) -> CloudScopeEvidenceV1:
    """Pure privacy projection; every intended scope survives missing evidence."""
    if snapshot.selection.provider_key != "ollama":
        raise ValueError("m6_cloud_scope_provider_invalid")
    records = {item.organization_id: item for item in snapshot.items}
    scopes = []
    for organization_id in snapshot.selection.organization_ids:
        organization_digest = cloud_reference_digest_v1(
            "organization", organization_id.value
        )
        item = records.get(organization_id)
        if item is None:
            scopes.append(
                CloudOrganizationScopeV1(organization_digest, "missing", None, None, 0)
            )
            continue
        account_digest = (
            cloud_reference_digest_v1("account", item.account_id.value)
            if item.account_id
            else None
        )
        disposition = "invalidated" if item.invalidated_at is not None else item.outcome
        target = (
            active_targets.get(item.account_id)
            if item.account_id is not None and item.invalidated_at is None
            else None
        )
        scopes.append(
            CloudOrganizationScopeV1(
                organization_digest,
                disposition,
                account_digest,
                target,
                item.record_version,
                item.invalidation_reason or item.unavailable_reason,
            )
        )
    return CloudScopeEvidenceV1(
        tuple(scopes),
        tuple(sorted(active_targets.values())),
        tuple(sorted(owner_confirmed_targets)),
        tuple(sorted(verified_targets)),
        snapshot.registry_revision,
        snapshot.as_of.isoformat(),
        snapshot.completeness == "complete",
    )


def read_m6_evidence_snapshot_v1(
    data_root: Path,
    *,
    as_of: datetime | None = None,
    coverage_selection: OrganizationProviderCoverageSelectionV1 | None = None,
) -> M6EvidenceSnapshotV1:
    """Read one bounded real snapshot; never creates, migrates or collects."""

    instant = as_of or datetime.now(UTC)
    if (
        not isinstance(data_root, Path)
        or not data_root.is_absolute()
        or instant.utcoffset() != timedelta(0)
        or coverage_selection is not None
        and (
            not isinstance(coverage_selection, OrganizationProviderCoverageSelectionV1)
            or coverage_selection.provider_key != "ollama"
        )
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
        runtime = SqliteRuntimeObservationRepositoryV1(reference)
        policy = ollama_cloud_scheduled_policy()

        accounts = tuple(
            account
            for account in registry.list_accounts("ollama", page_size=201)
            if account.lifecycle == "active"
        )
        installations = registry.list_provider_installations("ollama", page_size=201)
        organizations = registry.list_organizations(page_size=201)
        if (
            len(accounts) >= 201
            or len(installations) >= 201
            or len(organizations) >= 201
        ):
            raise ValueError("m6_snapshot_registry_limit_exceeded")
        observed_installations = tuple(
            item
            for item in installations
            if item.presence_state == "present"
            and item.version.state == "known_masked"
            and instant - timedelta(minutes=10)
            <= item.last_seen_at
            <= instant + timedelta(seconds=5)
        )
        schedules = SqliteCloudScheduleStatusV1(reference).list_registered()
        process_rows = runtime.list_processes("ollama", instant, 500)
        if len(process_rows) >= 500:
            raise ValueError("m6_snapshot_process_limit_exceeded")
        processes = tuple(item for item in process_rows if item.presence == "running")
        active_targets = 0
        owner_confirmed = 0
        verified = 0
        current = 0
        history = 0
        recovery = 0
        continuity = 0
        cloud_accounts: list[AccountViewV1] = []
        coverage_reader: OrganizationProviderCoverageReadPortV1 = (
            SqliteOrganizationProviderCoverageRepositoryV1(reference)
        )
        scope_before = (
            coverage_reader.read_coverage(coverage_selection)
            if coverage_selection is not None
            else None
        )
        active_target_references: dict[OpaqueIdV1, str] = {}
        owner_target_references: set[str] = set()
        verified_target_references: set[str] = set()
        current_observations: dict[OpaqueIdV1, frozenset[OpaqueIdV1]] = {}
        current_balance_lineage: set[tuple[str, ...]] = set()
        current_history_lineage: set[tuple[str, ...]] = set()
        for account in accounts:
            aggregate = binding_repository.read(account.account_id)
            binding = _active_binding(aggregate)
            graph = cloud_registry.read_monitoring_target(account.account_id)
            if graph is None or graph.lifecycle != "active":
                continue
            active_targets += 1
            target_digest = cloud_reference_digest_v1(
                "target",
                "\0".join(
                    (
                        graph.account_id.value,
                        graph.resource_id.value,
                        graph.access_target_id.value,
                    )
                ),
            )
            active_target_references[account.account_id] = target_digest
            cloud_accounts.append(account)
            if (
                graph.identity_state != "owner_confirmed"
                or binding is None
                or graph.binding != binding
            ):
                continue
            owner_confirmed += 1
            owner_target_references.add(target_digest)
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
            verified_target_references.add(target_digest)
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
            windows = _current_cloud_windows(capacity, graph, signal.run_id, instant)
            if not windows:
                continue
            current += 1
            current_observations[account.account_id] = frozenset(
                item.current_observation_id for item in windows
            )
            current_balance_lineage.update(
                (
                    account.account_id.value,
                    graph.resource_id.value,
                    graph.access_target_id.value,
                    item.window_id.value,
                    item.current_observation_id.value,
                    item.collection_run_id.value,
                )
                for item in windows
            )
            history_lineage = _current_history_lineage(
                capacity, graph, windows, instant
            )
            if history_lineage:
                history += 1
                current_history_lineage.update(history_lineage)

            # CTR-COL-002 does not expose the access target, source fingerprint,
            # or candidate revision needed to bind an older failure to this exact
            # current source.  Do not infer M6-A07 from unrelated historical runs.

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
            _has_deduplicated_current_observation_alert(
                alert_repository,
                account,
                current_observations.get(account.account_id, frozenset()),
                instant,
            )
            for account in configured_accounts
        )

        scope_evidence = None
        if coverage_selection is not None and scope_before is not None:
            scope_after = coverage_reader.read_coverage(coverage_selection)
            if (
                scope_before.items != scope_after.items
                or scope_before.registry_revision != scope_after.registry_revision
                or scope_before.completeness != "complete"
            ):
                scope_after = OrganizationProviderCoverageSnapshotV1(
                    coverage_selection,
                    (),
                    scope_after.registry_revision,
                    "unavailable",
                    scope_after.as_of,
                )
            scope_evidence = cloud_scope_evidence_from_registry_v1(
                scope_after,
                active_target_references,
                owner_target_references,
                verified_target_references,
            )
        return M6EvidenceSnapshotV1(
            status="passed",
            reason_code="m6_snapshot_query_complete",
            schema_state=schema_state,
            active_ollama_accounts=len(accounts),
            registered_local_installations=len(installations),
            # Each item is a real M02 reconciliation; a second host cannot be
            # inferred merely from a second account or process row.
            observed_local_installations=len(observed_installations),
            active_cloud_targets=active_targets,
            owner_confirmed_cloud_targets=owner_confirmed,
            owner_confirmed_required_scopes=(
                scope_evidence.owner_confirmed_scopes
                if scope_evidence is not None
                else 0
            ),
            verified_cloud_targets=verified,
            current_balance_targets=current,
            history_targets=history,
            configured_alert_targets=len(configured_accounts),
            alerted_targets=alerted,
            process_observation_count=len(processes),
            natural_recovery_targets=recovery,
            cross_provider_continuity_targets=continuity,
            current_balance_lineage_sha256=_lineage_digest(current_balance_lineage),
            current_history_lineage_sha256=_lineage_digest(current_history_lineage),
            cloud_scope_evidence=scope_evidence,
        )
    except (OSError, TypeError, ValueError):
        return M6EvidenceSnapshotV1.blocked(
            schema_state=schema_state,
            reason_code="m6_snapshot_query_unavailable",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--required-organization-id", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        selection = (
            OrganizationProviderCoverageSelectionV1(
                tuple(OpaqueIdV1(value) for value in args.required_organization_id),
                "ollama",
            )
            if args.required_organization_id
            else None
        )
    except (TypeError, ValueError):
        snapshot = M6EvidenceSnapshotV1.blocked(
            schema_state="unknown", reason_code="m6_snapshot_scope_selection_invalid"
        )
    else:
        snapshot = read_m6_evidence_snapshot_v1(
            args.data_root, coverage_selection=selection
        )
    print(json.dumps(snapshot.as_json(), sort_keys=True, separators=(",", ":")))
    return 0 if snapshot.status == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
