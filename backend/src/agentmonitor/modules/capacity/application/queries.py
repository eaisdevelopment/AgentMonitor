"""M05 provider-neutral query application boundaries."""

import hashlib
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Protocol

from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV1,
    AccountCapacityViewV1OrV2,
    CapacityAggregateQueryV1,
    CapacityAggregateViewV1,
    CapacityAlertConditionQueryV1,
    CapacityAlertConditionV1,
    CapacityCommitStatusV1,
    CapacityForecastPolicyV1,
    CapacityForecastQueryV1,
    CapacityForecastSampleV1,
    CapacityForecastV1,
    CapacityHealthViewV1,
    CapacityHistoryPointV1OrV2,
    CapacityHistoryPointV2,
    CapacityHistoryQueryV1,
    ExactMetricFieldV1,
    QuotaAllowanceV1,
    QuotaWindowViewV1OrV2,
    QuotaWindowViewV2,
)
from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryCollectionV1,
    QueryPageV1,
)
from agentmonitor.contracts.registry_v1 import AlertScopeAndSubjectQueryV1
from agentmonitor.modules.capacity.application.current import (
    ListCapacityAvailabilityConditionsV1 as ListCapacityAvailabilityConditionsV1,
)
from agentmonitor.modules.capacity.application.current import (
    ListCurrentCapacityForecastsV1 as ListCurrentCapacityForecastsV1,
)
from agentmonitor.modules.capacity.application.current import (
    ListForecastAlertConditionsV1 as ListForecastAlertConditionsV1,
)
from agentmonitor.modules.capacity.application.events import (
    AcknowledgeCapacityEventV1 as AcknowledgeCapacityEventV1,
)
from agentmonitor.modules.capacity.application.events import (
    AcknowledgedCapacityEventV1 as AcknowledgedCapacityEventV1,
)
from agentmonitor.modules.capacity.application.events import (
    CapacityEventEvidenceErrorV1 as CapacityEventEvidenceErrorV1,
)
from agentmonitor.modules.capacity.application.events import (
    CapacityEventEvidenceRepositoryV1 as CapacityEventEvidenceRepositoryV1,
)
from agentmonitor.modules.capacity.application.events import (
    ReadAcknowledgedCapacityEventsV1 as ReadAcknowledgedCapacityEventsV1,
)
from agentmonitor.modules.capacity.application.events import (
    ReadCapacityEventsV1 as ReadCapacityEventsV1,
)
from agentmonitor.modules.capacity.domain.aggregation import (
    aggregate_capacity_v1 as aggregate_capacity_v1,
)
from agentmonitor.modules.capacity.domain.alert_conditions import (
    derive_capacity_alert_condition_v1 as derive_capacity_alert_condition_v1,
)
from agentmonitor.modules.capacity.domain.allowance import remaining_percentage_v1
from agentmonitor.modules.capacity.domain.events import (
    capacity_event_acknowledgement_v1 as capacity_event_acknowledgement_v1,
)
from agentmonitor.modules.capacity.domain.events import (
    capacity_event_payload_digest_v1 as capacity_event_payload_digest_v1,
)
from agentmonitor.modules.capacity.domain.forecast import (
    derive_capacity_forecast_v1 as derive_capacity_forecast_v1,
)
from agentmonitor.modules.capacity.domain.forecast import (
    select_latest_compatible_suffix_v1 as select_latest_compatible_suffix_v1,
)
from agentmonitor.modules.capacity.domain.health import (
    default_capacity_health_policy_v1 as default_capacity_health_policy_v1,
)


class GetQuotaAllowanceV1:
    """Publish the per-window display calculation and its exact input lineage."""

    def __call__(self, window: QuotaWindowViewV1OrV2) -> QuotaAllowanceV1 | None:
        result = remaining_percentage_v1(window.used, window.remaining_ratio)
        if result is None:
            return None
        metric, calculation = result
        return QuotaAllowanceV1(metric, calculation, window.current_observation_id)


class CapacityQueryUnavailableV1(RuntimeError):
    pass


class CapacityV2RequiredV1(RuntimeError):
    """Legacy aggregate cannot represent at least one cloud target."""


class CapacityCommitQueryRepositoryV1(Protocol):
    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> CapacityCommitStatusV1: ...

    def list_quota_windows(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        as_of: datetime,
    ) -> tuple[QuotaWindowViewV1OrV2, ...]: ...

    def list_account_quota_windows(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> tuple[QuotaWindowViewV1OrV2, ...]: ...

    def page_account_quota_windows(
        self,
        account_id: OpaqueIdV1,
        as_of: datetime,
        page_size: int,
        after_key: str | None,
    ) -> tuple[QuotaWindowViewV1OrV2, ...]: ...

    def page_capacity_history(
        self,
        query: CapacityHistoryQueryV1,
        page_size: int,
    ) -> tuple[CapacityHistoryPointV1OrV2, ...]: ...

    def recent_capacity_history(
        self,
        query: CapacityHistoryQueryV1,
        page_size: int,
    ) -> tuple[CapacityHistoryPointV1OrV2, ...]: ...

    def get_capacity_health(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        as_of: datetime,
    ) -> CapacityHealthViewV1: ...

    def get_account_capacity(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        as_of: datetime,
    ) -> AccountCapacityViewV1OrV2: ...

    def list_account_capacities(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> tuple[AccountCapacityViewV1OrV2, ...]: ...


class GetCollectionCommitStatusV1:
    def __init__(self, repository: CapacityCommitQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> CapacityCommitStatusV1:
        return self._repository.get_commit_status(run_id, capability_id)


class ListQuotaWindowsV1:
    def __init__(self, repository: CapacityCommitQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        account_id: OpaqueIdV1,
        *,
        as_of: datetime,
    ) -> tuple[QuotaWindowViewV1OrV2, ...]:
        return self._repository.list_account_quota_windows(account_id, as_of)

    def for_scope(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        *,
        as_of: datetime,
    ) -> tuple[QuotaWindowViewV1OrV2, ...]:
        return self._repository.list_quota_windows(
            account_id, resource_id, capability_id, as_of
        )

    def page(
        self,
        account_id: OpaqueIdV1,
        *,
        as_of: datetime,
        limit: int = 50,
        after_key: str | None = None,
    ) -> QueryPageV1[QuotaWindowViewV1OrV2]:
        try:
            rows = self._repository.page_account_quota_windows(
                account_id, as_of, limit + 1, after_key
            )
        except ValueError:
            raise CapacityQueryUnavailableV1("capacity_query_unavailable") from None
        has_more = len(rows) > limit
        items = rows[:limit]
        query_availability = (
            QueryAvailabilityV1("available", "quota_observations_available", as_of)
            if items
            else QueryAvailabilityV1("unavailable", "quota_observations_absent", as_of)
        )
        return QueryPageV1(
            items,
            limit,
            has_more,
            items[-1].window_id.value if has_more else None,
            query_availability,
        )


class ListCapacityHistoryV1:
    """CTR-CAP-006 bounded history query; it never invokes a provider."""

    def __init__(self, repository: CapacityCommitQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, query: CapacityHistoryQueryV1
    ) -> QueryPageV1[CapacityHistoryPointV1OrV2]:
        try:
            rows = self._repository.page_capacity_history(query, query.limit + 1)
        except ValueError:
            raise CapacityQueryUnavailableV1("capacity_query_unavailable") from None
        has_more = len(rows) > query.limit
        items = rows[: query.limit]
        query_availability = (
            QueryAvailabilityV1("available", "capacity_history_available", query.as_of)
            if items
            else QueryAvailabilityV1(
                "unavailable", "capacity_history_absent", query.as_of
            )
        )
        return QueryPageV1(
            items,
            query.limit,
            has_more,
            items[-1].cursor_key if has_more else None,
            query_availability,
        )


class GetCapacityHealthV1:
    def __init__(self, repository: CapacityCommitQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        as_of: datetime,
    ) -> CapacityHealthViewV1:
        return self._repository.get_capacity_health(
            account_id, resource_id, capability_id, as_of
        )


class GetAccountCapacityV1:
    def __init__(self, repository: CapacityCommitQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        account_id: OpaqueIdV1,
        *,
        as_of: datetime,
    ) -> QueryCollectionV1[AccountCapacityViewV1OrV2]:
        try:
            items = self._repository.list_account_capacities(account_id, as_of)
        except ValueError:
            raise CapacityQueryUnavailableV1("capacity_query_unavailable") from None
        query_availability = (
            QueryAvailabilityV1("available", "capacity_observations_available", as_of)
            if items
            else QueryAvailabilityV1(
                "unavailable", "capacity_observations_absent", as_of
            )
        )
        return QueryCollectionV1(items, query_availability)

    def for_scope(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        *,
        as_of: datetime,
    ) -> AccountCapacityViewV1OrV2:
        return self._repository.get_account_capacity(
            account_id, resource_id, capability_id, as_of
        )


class GetCapacityAggregateV1:
    """Read bounded M05 facts and guard against a concurrently changed scope."""

    def __init__(
        self,
        repository: CapacityCommitQueryRepositoryV1,
        scope_query: AlertScopeAndSubjectQueryV1,
    ) -> None:
        self._repository = repository
        self._scope_query = scope_query

    def __call__(self, query: CapacityAggregateQueryV1) -> CapacityAggregateViewV1:
        expected = query.scope_snapshot
        if expected.completeness_state != "complete":
            raise CapacityQueryUnavailableV1("registry_scope_unavailable")
        if self._scope_query(expected.scope_kind, expected.scope_id) != expected:
            raise CapacityQueryUnavailableV1("registry_scope_changed")
        capacities = tuple(
            capacity
            for account in query.accounts
            if account.lifecycle == "active" and account.is_effective_monitoring_enabled
            for capacity in self._repository.list_account_capacities(
                account.account_id, query.as_of
            )
        )
        legacy = tuple(
            capacity
            for capacity in capacities
            if isinstance(capacity, AccountCapacityViewV1)
        )
        if len(legacy) != len(capacities):
            raise CapacityV2RequiredV1("capacity_v2_required")
        if self._scope_query(expected.scope_kind, expected.scope_id) != expected:
            raise CapacityQueryUnavailableV1("registry_scope_changed")
        return aggregate_capacity_v1(query, legacy)


class CapacityAlertQueryRepositoryV1(Protocol):
    def page_capacity_alert_windows(
        self, query: CapacityAlertConditionQueryV1, page_size: int
    ) -> tuple[QuotaWindowViewV1OrV2, ...]: ...


class ListCapacityAlertConditionsV1:
    def __init__(self, repository: CapacityAlertQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, query: CapacityAlertConditionQueryV1
    ) -> QueryPageV1[CapacityAlertConditionV1]:
        rows = self._repository.page_capacity_alert_windows(query, query.limit + 1)
        selected = rows[: query.limit]
        return QueryPageV1(
            tuple(
                derive_capacity_alert_condition_v1(window, as_of=query.as_of)
                for window in selected
            ),
            query.limit,
            len(rows) > query.limit,
            selected[-1].window_id.value if len(rows) > query.limit else None,
            QueryAvailabilityV1(
                "available" if selected else "unavailable",
                "capacity_current_conditions_available"
                if selected
                else "quota_observations_absent",
                query.as_of,
            ),
        )


def _unknown_forecast_metric() -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        FieldAvailabilityV1("unknown"),
        None,
        "unknown",
        "unknown",
        "unknown",
        "forecast_measure_not_observed",
    )


class ListCapacityForecastsV1:
    """Query-only derived views; canonical persistence/events are a later increment."""

    def __init__(self, repository: CapacityCommitQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, query: CapacityForecastQueryV1
    ) -> QueryPageV1[CapacityForecastV1]:
        windows = tuple(
            sorted(
                (
                    window
                    for window in self._repository.list_account_quota_windows(
                        query.account_id, query.as_of
                    )
                    if (
                        query.resource_id is None
                        or window.subject.resource_id == query.resource_id
                    )
                    and (query.window_id is None or window.window_id == query.window_id)
                    and (
                        query.after_key is None
                        or window.window_id.value > query.after_key
                    )
                ),
                key=lambda window: window.window_id.value,
            )
        )
        selected = windows[: query.limit]
        results = tuple(
            result
            for window in selected
            if (result := self._window_forecast(window, query.as_of)) is not None
        )
        has_more = len(windows) > query.limit
        return QueryPageV1(
            results,
            query.limit,
            has_more,
            selected[-1].window_id.value if has_more and selected else None,
            QueryAvailabilityV1(
                "available" if results else "unavailable",
                "capacity_forecast_explanations_available"
                if results
                else "capacity_forecast_history_absent",
                query.as_of,
            ),
        )

    def _window_forecast(
        self, window: QuotaWindowViewV1OrV2, as_of: datetime
    ) -> CapacityForecastV1 | None:
        if isinstance(window, QuotaWindowViewV2):
            return None
        query = CapacityHistoryQueryV1(
            window.subject.account_id,
            window.subject.resource_id,
            window.window_id,
            "used",
            "poll_snapshot",
            as_of - timedelta(days=7),
            as_of + timedelta(microseconds=1),
            as_of,
            200,
            None,
            None,
            None,
        )
        used = self._repository.recent_capacity_history(query, 200)
        if not used:
            return None
        remaining_by_id = {
            point.observation_id: point.value
            for point in self._repository.recent_capacity_history(
                replace(query, metric="remaining"), 200
            )
        }
        ratios_by_id = {
            point.observation_id: point.value
            for point in self._repository.recent_capacity_history(
                replace(query, metric="remaining_ratio"), 200
            )
        }
        samples = []
        for point in used:
            if isinstance(point, CapacityHistoryPointV2):
                return None
            remaining = remaining_by_id.get(
                point.observation_id, _unknown_forecast_metric()
            )
            if (
                remaining.value is None
                and point.value.value is not None
                and point.value.value.unit == "percent"
            ):
                derived = remaining_percentage_v1(
                    point.value,
                    ratios_by_id.get(point.observation_id, _unknown_forecast_metric()),
                )
                remaining = derived[0] if derived is not None else remaining
            provenance = point.provenance
            source = hashlib.sha256(
                "\x1f".join(
                    (
                        provenance.source_id,
                        provenance.capability_schema_version,
                        provenance.adapter_version,
                        provenance.provider_version or "unknown",
                        provenance.mechanism_version,
                        provenance.parser_version or "none",
                    )
                ).encode()
            ).hexdigest()
            segment = (
                OpaqueIdV1(
                    hashlib.sha256(point.reset_at.isoformat().encode()).hexdigest()
                )
                if point.reset_at is not None and point.reset_precision == "exact"
                else None
            )
            samples.append(
                CapacityForecastSampleV1(
                    point.observation_id,
                    point.window_definition_id,
                    point.definition_version,
                    point.subject,
                    point.window_key,
                    point.metric,
                    point.observed_at,
                    point.value,
                    remaining,
                    source,
                    segment,
                    point.reset_at,
                    point.provenance.freshness_deadline,
                    None,
                    None,
                    None,
                    None,
                )
            )
        return derive_capacity_forecast_v1(
            select_latest_compatible_suffix_v1(tuple(samples)),
            policy=CapacityForecastPolicyV1(),
            window_id=window.window_id,
            as_of=as_of,
        )
