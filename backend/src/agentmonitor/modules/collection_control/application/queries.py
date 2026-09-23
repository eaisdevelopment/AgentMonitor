"""Read-only M04 collection-run query boundary."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.collection_control_v1 import CollectionRunViewV1
from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)


class CollectionQueryUnavailableV1(RuntimeError):
    pass


class CollectionRunQueryRepositoryV1(Protocol):
    def list_runs(
        self,
        provider_key: str | None,
        account_id: OpaqueIdV1 | None,
        as_of: datetime,
        page_size: int,
        after_key: str | None = None,
    ) -> tuple[CollectionRunViewV1, ...]: ...


class ListCollectionRunsV1:
    def __init__(self, repository: CollectionRunQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        *,
        provider_key: str | None = None,
        account_id: OpaqueIdV1 | None = None,
        as_of: datetime,
        page_size: int = 100,
    ) -> tuple[CollectionRunViewV1, ...]:
        return self._repository.list_runs(provider_key, account_id, as_of, page_size)

    def page(
        self,
        *,
        provider_key: str | None = None,
        account_id: OpaqueIdV1 | None = None,
        as_of: datetime,
        limit: int = 50,
        after_key: str | None = None,
    ) -> QueryPageV1[CollectionRunViewV1]:
        try:
            rows = self._repository.list_runs(
                provider_key, account_id, as_of, limit + 1, after_key
            )
        except ValueError:
            raise CollectionQueryUnavailableV1("collection_query_unavailable") from None
        has_more = len(rows) > limit
        items = rows[:limit]
        return QueryPageV1(
            items,
            limit,
            has_more,
            items[-1].run_id.value if has_more else None,
            QueryAvailabilityV1("available", "collection_query_complete", as_of),
        )
