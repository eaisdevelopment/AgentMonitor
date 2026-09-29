"""M05 public current producer ports; only the owned adapter touches storage."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.capacity_v1 import (
    CapacityAvailabilityAlertConditionV1,
    CapacityAvailabilityQueryV1,
    CapacityForecastQueryV1,
    CurrentCapacityForecastV1,
    ForecastAlertConditionV1,
)
from agentmonitor.contracts.common_v1 import QueryPageV1
from agentmonitor.modules.capacity.domain.forecast import (
    derive_forecast_alert_condition_v1,
)


class CurrentCapacityRepositoryV1(Protocol):
    def page_current_forecasts(
        self, query: CapacityForecastQueryV1
    ) -> QueryPageV1[CurrentCapacityForecastV1]: ...
    def page_current_availability(
        self, query: CapacityAvailabilityQueryV1
    ) -> QueryPageV1[CapacityAvailabilityAlertConditionV1]: ...
    def refresh_current_projections(
        self, as_of: datetime, after_key: str | None, limit: int
    ) -> QueryPageV1[CurrentCapacityForecastV1]: ...


class ListCurrentCapacityForecastsV1:
    CONTRACT_ID = "CTR-CAP-007"
    OWNER = "PLAN-M05"

    def __init__(self, repository: CurrentCapacityRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, query: CapacityForecastQueryV1
    ) -> QueryPageV1[CurrentCapacityForecastV1]:
        return self._repository.page_current_forecasts(query)


class ListForecastAlertConditionsV1:
    CONTRACT_ID = "CTR-CAP-008"
    OWNER = "PLAN-M05"

    def __init__(self, repository: CurrentCapacityRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, query: CapacityForecastQueryV1
    ) -> QueryPageV1[ForecastAlertConditionV1]:
        page = self._repository.page_current_forecasts(query)
        return QueryPageV1(
            tuple(
                derive_forecast_alert_condition_v1(
                    item.forecast,
                    reset_at=item.source_reset_at,
                    observed_at=item.source_observed_at,
                    recorded_at=item.recorded_at,
                )
                for item in page.items
            ),
            page.limit,
            page.has_more,
            page.next_key,
            page.availability,
        )


class ListCapacityAvailabilityConditionsV1:
    CONTRACT_ID = "CTR-CAP-009"
    OWNER = "PLAN-M05"

    def __init__(self, repository: CurrentCapacityRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, query: CapacityAvailabilityQueryV1
    ) -> QueryPageV1[CapacityAvailabilityAlertConditionV1]:
        return self._repository.page_current_availability(query)


class RefreshCurrentCapacityProjectionsV1:
    CONTRACT_ID = "CTR-CAP-007"
    OWNER = "PLAN-M05"

    def __init__(self, repository: CurrentCapacityRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, as_of: datetime, after_key: str | None = None, limit: int = 32
    ) -> QueryPageV1[CurrentCapacityForecastV1]:
        if type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError("capacity_refresh_limit_invalid")
        return self._repository.refresh_current_projections(as_of, after_key, limit)
