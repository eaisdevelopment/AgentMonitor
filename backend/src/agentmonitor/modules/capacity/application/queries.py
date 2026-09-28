"""M05 provider-neutral query application boundaries."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.capacity_v1 import (
    AccountCapacityViewV1,
    CapacityCommitStatusV1,
    CapacityHealthViewV1,
    CapacityHistoryPointV1,
    CapacityHistoryQueryV1,
    QuotaAllowanceV1,
    QuotaWindowViewV1,
)
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryCollectionV1,
    QueryPageV1,
)
from agentmonitor.modules.capacity.domain.allowance import remaining_percentage_v1


class GetQuotaAllowanceV1:
    """Publish the per-window display calculation and its exact input lineage."""

    def __call__(self, window: QuotaWindowViewV1) -> QuotaAllowanceV1 | None:
        result = remaining_percentage_v1(window.used, window.remaining_ratio)
        if result is None:
            return None
        metric, calculation = result
        return QuotaAllowanceV1(metric, calculation, window.current_observation_id)


class CapacityQueryUnavailableV1(RuntimeError):
    pass


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
    ) -> tuple[QuotaWindowViewV1, ...]: ...

    def list_account_quota_windows(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> tuple[QuotaWindowViewV1, ...]: ...

    def page_account_quota_windows(
        self,
        account_id: OpaqueIdV1,
        as_of: datetime,
        page_size: int,
        after_key: str | None,
    ) -> tuple[QuotaWindowViewV1, ...]: ...

    def page_capacity_history(
        self,
        query: CapacityHistoryQueryV1,
        page_size: int,
    ) -> tuple[CapacityHistoryPointV1, ...]: ...

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
    ) -> AccountCapacityViewV1: ...

    def list_account_capacities(
        self, account_id: OpaqueIdV1, as_of: datetime
    ) -> tuple[AccountCapacityViewV1, ...]: ...


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
    ) -> tuple[QuotaWindowViewV1, ...]:
        return self._repository.list_account_quota_windows(account_id, as_of)

    def for_scope(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        capability_id: str,
        *,
        as_of: datetime,
    ) -> tuple[QuotaWindowViewV1, ...]:
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
    ) -> QueryPageV1[QuotaWindowViewV1]:
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
    ) -> QueryPageV1[CapacityHistoryPointV1]:
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
    ) -> QueryCollectionV1[AccountCapacityViewV1]:
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
    ) -> AccountCapacityViewV1:
        return self._repository.get_account_capacity(
            account_id, resource_id, capability_id, as_of
        )
