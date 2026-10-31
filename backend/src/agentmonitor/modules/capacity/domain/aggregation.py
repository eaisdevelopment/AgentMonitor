"""Pure capacity coverage over one immutable registry membership revision."""

import hashlib
import json
from collections import Counter
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV1,
    CapacityAccountCoverageV1,
    CapacityAggregateQueryV1,
    CapacityAggregateViewV1,
    CapacityAggregateWindowGroupV1,
    CapacityHealthStateV1,
    CompletenessV1,
    InvalidCapacityContractV1,
    QuotaWindowViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.health import classify_capacity_windows_v1

HEALTH_STATES: tuple[CapacityHealthStateV1, ...] = (
    "available",
    "constrained",
    "critical",
    "exhausted",
    "reauthentication_required",
    "unknown",
)


def aggregate_capacity_v1(
    query: CapacityAggregateQueryV1,
    capacities: tuple[AccountCapacityViewV1, ...],
) -> CapacityAggregateViewV1:
    """Inventory only: absent pool relationship evidence forbids numeric totals."""
    member_ids = set(query.scope_snapshot.account_ids)
    window_ids: set[OpaqueIdV1] = set()
    all_windows: dict[OpaqueIdV1, list[QuotaWindowViewV1]] = {}
    for capacity in capacities:
        if capacity.subject.account_id not in member_ids:
            raise InvalidCapacityContractV1("capacity_aggregate_subject_outside_scope")
        for window in capacity.windows:
            if window.subject != capacity.subject or window.window_id in window_ids:
                raise InvalidCapacityContractV1("capacity_aggregate_window_invalid")
            window_ids.add(window.window_id)
            all_windows.setdefault(window.subject.account_id, []).append(window)
    rows = []
    for account in sorted(query.accounts, key=lambda item: item.account_id.value):
        resources = tuple(
            sorted(
                (
                    resource.resource_id
                    for resource in query.resources
                    if resource.account_id == account.account_id
                    and resource.lifecycle == "active"
                ),
                key=lambda item: item.value,
            )
        )
        if (
            not account.is_effective_monitoring_enabled
            or account.lifecycle != "active"
            or not resources
        ):
            reason = (
                "account_inactive"
                if account.lifecycle != "active"
                else "monitoring_disabled"
                if not account.is_effective_monitoring_enabled
                else "active_resource_absent"
            )
            rows.append(
                CapacityAccountCoverageV1(
                    account.account_id,
                    resources,
                    "excluded",
                    "excluded",
                    (reason,),
                    None,
                    (),
                    (),
                )
            )
            continue
        windows = tuple(
            sorted(
                (
                    window
                    for window in all_windows.get(account.account_id, ())
                    if window.subject.resource_id in resources
                ),
                key=lambda window: window.window_id.value,
            )
        )
        health = classify_capacity_windows_v1(windows, policy=query.policy)
        represented = {window.subject.resource_id for window in windows}
        fresh = tuple(window for window in windows if window.freshness == "fresh")
        complete = (
            bool(windows)
            and represented == set(resources)
            and len(fresh) == len(windows)
            and health.completeness == "complete"
        )
        coverage: Literal["covered", "partial", "missing"] = (
            "covered" if complete else "partial" if fresh else "missing"
        )
        reasons = (
            ()
            if complete
            else ("quota_observations_absent",)
            if not windows
            else tuple(
                sorted(
                    {
                        "resource_reading_missing"
                        if represented != set(resources)
                        else "capacity_reading_partial",
                        *(
                            "capacity_" + window.freshness
                            for window in windows
                            if window.freshness != "fresh"
                        ),
                    }
                )
            )
        )
        rows.append(
            CapacityAccountCoverageV1(
                account.account_id,
                resources,
                "eligible",
                coverage,
                reasons,
                health,
                windows,
                tuple(
                    sorted(
                        {window.current_observation_id for window in windows},
                        key=lambda item: item.value,
                    )
                ),
            )
        )
    accounts = tuple(rows)
    eligible = tuple(row for row in accounts if row.eligibility == "eligible")
    covered = tuple(row for row in eligible if row.coverage == "covered")
    missing = tuple(row for row in eligible if row.coverage != "covered")
    excluded = tuple(row for row in accounts if row.eligibility == "excluded")
    health_counts = Counter(
        row.health.state if row.health else "unknown" for row in eligible
    )
    freshness_counts = Counter(
        row.health.freshness if row.health else "freshness_unknown" for row in eligible
    )
    priority: tuple[CapacityHealthStateV1, ...] = (
        "reauthentication_required",
        "exhausted",
        "critical",
        "constrained",
    )
    worst: CapacityHealthStateV1 = next(
        (state for state in priority if health_counts[state]),
        "unknown" if missing or not eligible else "available",
    )
    windows_by_group: dict[tuple[str, str, str, str], list[QuotaWindowViewV1]] = {}
    for row in eligible:
        for window in row.windows:
            native_value = next(
                (
                    field.value
                    for field in (window.used, window.remaining, window.limit)
                    if field.value is not None
                ),
                None,
            )
            key = (
                window.subject.provider_key,
                window.window_key,
                window.semantic_role or "",
                native_value.unit if native_value else "",
            )
            windows_by_group.setdefault(key, []).append(window)
    groups = tuple(
        CapacityAggregateWindowGroupV1(
            provider,
            native_key,
            role or None,
            unit or None,
            tuple(
                sorted(
                    {window.subject.resource_id for window in windows},
                    key=lambda item: item.value,
                )
            ),
            tuple(
                sorted(
                    {window.subject.account_id for window in windows},
                    key=lambda item: item.value,
                )
            ),
            tuple(
                sorted(
                    {window.current_observation_id for window in windows},
                    key=lambda item: item.value,
                )
            ),
            "unknown",
            ("pool_relationship_unknown",),
            (),
        )
        for (provider, native_key, role, unit), windows in sorted(
            windows_by_group.items()
        )
    )
    input_ids = tuple(
        sorted(
            {item for row in eligible for item in row.input_observation_ids},
            key=lambda item: item.value,
        )
    )
    digest_input = (
        query.scope_snapshot.scope_kind,
        query.scope_snapshot.scope_id.value if query.scope_snapshot.scope_id else None,
        query.scope_snapshot.registry_revision,
        query.as_of.isoformat(),
        query.policy.policy_id,
        query.policy.policy_version,
        tuple(
            (
                row.account_id.value,
                row.eligibility,
                row.coverage,
                tuple(item.value for item in row.input_observation_ids),
            )
            for row in accounts
        ),
    )
    completeness: CompletenessV1 = (
        "complete" if eligible and not missing else "partial" if covered else "unknown"
    )
    return CapacityAggregateViewV1(
        query.scope_snapshot.scope_kind,
        query.scope_snapshot.scope_id,
        query.scope_snapshot.registry_revision,
        query.as_of,
        completeness,
        "available" if covered else "unavailable",
        () if eligible and not missing else ("capacity_scope_incomplete",),
        tuple(row.account_id for row in eligible),
        tuple(row.account_id for row in covered),
        missing,
        excluded,
        accounts,
        groups,
        tuple((state, health_counts[state]) for state in HEALTH_STATES),
        tuple(
            (state, freshness_counts[state])
            for state in ("fresh", "stale", "freshness_unknown", "conflicted")
        ),
        worst,
        input_ids,
        hashlib.sha256(
            json.dumps(digest_input, separators=(",", ":")).encode()
        ).hexdigest(),
        query.policy.policy_id,
        query.policy.policy_version,
    )
