"""Authenticated, read-only M04 collection-run transport."""

from datetime import UTC, datetime

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, observation_ports
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    availability,
    decode_cursor,
    page_meta,
    policy,
    reject_unknown_query,
    require_opaque_selector,
)
from agentmonitor.api.v1.schemas.collection import (
    CollectionRunPageV1,
    CollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.queries import (
    CollectionQueryUnavailableV1,
)
from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["collection"])


@router.get(
    "/collection-runs",
    operation_id="collection_list_runs_v1",
    response_model=CollectionRunPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "ListCollectionRunsV1"),
)
def list_collection_runs(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
    provider_key: str | None = Query(None, min_length=1, max_length=64),
    account_id: str | None = Query(None, min_length=1, max_length=256),
) -> CollectionRunPageV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(
        request, frozenset({"limit", "cursor", "provider_key", "account_id"})
    )
    if account_id is not None:
        require_opaque_selector(account_id)
    as_of = datetime.now(UTC)
    filters = {"provider_key": provider_key, "account_id": account_id}
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="collection_list_runs_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = observation_ports(request).list_collection_runs.page(
            provider_key=provider_key,
            account_id=OpaqueIdV1(account_id) if account_id else None,
            as_of=as_of,
            limit=limit,
            after_key=after_key,
        )
    except CollectionQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return CollectionRunPageV1(
        items=tuple(
            CollectionRunViewV1(
                run_id=item.run_id.value,
                schedule_id=item.schedule_id.value,
                provider_key=item.provider_key,
                account_id=item.account_id.value if item.account_id else None,
                resource_id=item.resource_id.value if item.resource_id else None,
                capability_id=item.capability_id,
                state=item.state,
                source_id=item.source_id,
                adapter_version=item.adapter_version,
                provider_version=item.provider_version,
                target_generation=item.target_generation,
                fencing_token=item.fencing_token,
                requested_at=item.requested_at,
                started_at=item.started_at,
                completed_at=item.completed_at,
                deadline_at=item.deadline_at,
                duration_ms=item.duration_ms,
                outcome_code=item.outcome_code,
                error_code=item.error_code,
                observation_ids=tuple(value.value for value in item.observation_ids),
            )
            for item in result.items
        ),
        page=page_meta(
            request,
            caller,
            operation_id="collection_list_runs_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )
