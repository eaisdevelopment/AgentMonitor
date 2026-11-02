"""Pure capacity coverage over one immutable registry membership revision."""

import hashlib
import json
from collections import Counter
from typing import Literal

from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV1,
    AccountCapacityViewV1OrV2,
    AccountCapacityViewV2,
    CapacityAccountCoverageV1,
    CapacityAccountCoverageV2,
    CapacityAggregateQueryV1,
    CapacityAggregateQueryV2,
    CapacityAggregateViewV1,
    CapacityAggregateViewV2,
    CapacityAggregateWindowGroupV1,
    CapacityAggregateWindowGroupV2,
    CapacityCloudResourceCoverageV2,
    CapacityHealthStateV1,
    CapacitySubjectV2,
    CompletenessV1,
    InvalidCapacityContractV1,
    QuotaWindowViewV1,
    QuotaWindowViewV1OrV2,
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


def aggregate_capacity_v2(
    query: CapacityAggregateQueryV2,
    capacities: tuple[AccountCapacityViewV1OrV2, ...],
) -> CapacityAggregateViewV2:
    """Aggregate V2 coverage while unresolved cloud sharing forbids totals."""
    member_ids = set(query.scope_snapshot.account_ids)
    local_resources = {
        item.resource_id: item
        for item in query.local_resources
        if item.lifecycle == "active"
    }
    cloud_resources = {
        item.resource_id: item for item in query.scope_snapshot.cloud_resources
    }
    window_ids: set[OpaqueIdV1] = set()
    all_windows: dict[OpaqueIdV1, list[QuotaWindowViewV1OrV2]] = {}
    for capacity in capacities:
        subject = capacity.subject
        if subject.account_id not in member_ids:
            raise InvalidCapacityContractV1("capacity_aggregate_subject_outside_scope")
        cloud = cloud_resources.get(subject.resource_id)
        local = local_resources.get(subject.resource_id)
        if cloud is not None:
            if (
                not isinstance(capacity, AccountCapacityViewV2)
                or not isinstance(subject, CapacitySubjectV2)
                or subject.account_id != cloud.account_id
                or subject.provider_key != cloud.provider_key
                or subject.provider_target != cloud.provider_target
            ):
                raise InvalidCapacityContractV1(
                    "capacity_aggregate_subject_outside_scope"
                )
        elif local is not None:
            if (
                subject.account_id != local.account_id
                or isinstance(subject, CapacitySubjectV2)
                and subject.provider_target.target_kind == "cloud_service"
            ):
                raise InvalidCapacityContractV1(
                    "capacity_aggregate_subject_outside_scope"
                )
        else:
            # M05 retains the latest projection independently of M02 resource
            # lifecycle.  A retired resource can therefore remain readable for
            # history after it has left this exact active-membership snapshot.
            continue
        for window in capacity.windows:
            if window.subject != subject or window.window_id in window_ids:
                raise InvalidCapacityContractV1("capacity_aggregate_window_invalid")
            window_ids.add(window.window_id)
            all_windows.setdefault(subject.account_id, []).append(window)

    rows = []
    for account in sorted(query.accounts, key=lambda item: item.account_id.value):
        local_ids = tuple(
            sorted(
                (
                    resource.resource_id
                    for resource in local_resources.values()
                    if resource.account_id == account.account_id
                ),
                key=lambda item: item.value,
            )
        )
        cloud_memberships = tuple(
            sorted(
                (
                    resource
                    for resource in cloud_resources.values()
                    if resource.account_id == account.account_id
                ),
                key=lambda item: item.resource_id.value,
            )
        )
        resources = tuple(
            sorted(
                (*local_ids, *(item.resource_id for item in cloud_memberships)),
                key=lambda item: item.value,
            )
        )
        cloud_coverage = tuple(
            CapacityCloudResourceCoverageV2(
                resource_id=item.resource_id,
                provider_key=item.provider_key,
                provider_target=item.provider_target,
                relationship_state="unresolved",
                reason_codes=("pool_relationship_unknown",),
            )
            for item in cloud_memberships
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
                CapacityAccountCoverageV2(
                    account_id=account.account_id,
                    resource_ids=resources,
                    cloud_resources=cloud_coverage,
                    eligibility="excluded",
                    coverage="excluded",
                    reason_codes=(reason,),
                    health=None,
                    windows=(),
                    input_observation_ids=(),
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
            and all(window.completeness == "complete" for window in windows)
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
        input_ids = tuple(
            sorted(
                {window.current_observation_id for window in windows},
                key=lambda item: item.value,
            )
        )
        rows.append(
            CapacityAccountCoverageV2(
                account_id=account.account_id,
                resource_ids=resources,
                cloud_resources=cloud_coverage,
                eligibility="eligible",
                coverage=coverage,
                reason_codes=reasons,
                health=health,
                windows=windows,
                input_observation_ids=input_ids,
            )
        )
    accounts = tuple(rows)
    eligible = tuple(item for item in accounts if item.eligibility == "eligible")
    covered = tuple(item for item in eligible if item.coverage == "covered")
    missing = tuple(item for item in eligible if item.coverage != "covered")
    excluded = tuple(item for item in accounts if item.eligibility == "excluded")
    health_counts = Counter(
        item.health.state if item.health else "unknown" for item in eligible
    )
    freshness_counts = Counter(
        item.health.freshness if item.health else "freshness_unknown"
        for item in eligible
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
    windows_by_group: dict[tuple[str, str, str, str], list[QuotaWindowViewV1OrV2]] = {}
    for item in eligible:
        for window in item.windows:
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
        CapacityAggregateWindowGroupV2(
            provider_key=provider,
            native_window_key=native_key,
            semantic_role=role or None,
            unit=unit or None,
            resource_ids=tuple(
                sorted(
                    {window.subject.resource_id for window in windows},
                    key=lambda item: item.value,
                )
            ),
            account_ids=tuple(
                sorted(
                    {window.subject.account_id for window in windows},
                    key=lambda item: item.value,
                )
            ),
            input_observation_ids=tuple(
                sorted(
                    {window.current_observation_id for window in windows},
                    key=lambda item: item.value,
                )
            ),
            relationship_state="unresolved",
            reason_codes=("pool_relationship_unknown",),
            numeric_values=(),
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
                item.resource_id.value,
                item.account_id.value,
                item.provider_key,
                item.provider_target.target_kind,
                item.provider_target.target_id.value,
                item.relationship_state,
            )
            for item in query.scope_snapshot.cloud_resources
        ),
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
    relationship_unknown = bool(query.scope_snapshot.cloud_resources)
    completeness: CompletenessV1 = (
        "complete" if eligible and not missing else "partial" if covered else "unknown"
    )
    if relationship_unknown and completeness == "complete":
        completeness = "partial"
    reason_code_values: set[str] = set()
    if not eligible or missing:
        reason_code_values.add("capacity_scope_incomplete")
    if relationship_unknown:
        reason_code_values.add("pool_relationship_unknown")
    reason_codes = tuple(sorted(reason_code_values))
    return CapacityAggregateViewV2(
        scope_kind=query.scope_snapshot.scope_kind,
        scope_id=query.scope_snapshot.scope_id,
        registry_revision=query.scope_snapshot.registry_revision,
        generated_at=query.as_of,
        completeness=completeness,
        availability="available" if covered else "unavailable",
        reason_codes=reason_codes,
        eligible_account_ids=tuple(item.account_id for item in eligible),
        covered_account_ids=tuple(item.account_id for item in covered),
        missing_accounts=missing,
        excluded_accounts=excluded,
        accounts=accounts,
        window_groups=groups,
        health_counts=tuple((state, health_counts[state]) for state in HEALTH_STATES),
        freshness_counts=tuple(
            (state, freshness_counts[state])
            for state in ("fresh", "stale", "freshness_unknown", "conflicted")
        ),
        worst_health=worst,
        input_observation_ids=input_ids,
        input_set_digest=hashlib.sha256(
            json.dumps(digest_input, separators=(",", ":")).encode()
        ).hexdigest(),
        policy_id=query.policy.policy_id,
        policy_version=query.policy.policy_version,
    )
