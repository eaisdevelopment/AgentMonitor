"""Authenticated, read-only M05 capacity transports."""

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
from agentmonitor.api.v1.schemas.capacity import (
    AccountCapacityItemV1,
    AccountCapacityViewV1,
    CapacityHealthViewV1,
    CapacityObservationProvenanceWireV1,
    CapacitySubjectWireV1,
    ExactMetricFieldWireV1,
    ExactQuantityWireV1,
    QuotaWindowPageV1,
    QuotaWindowViewV1,
)
from agentmonitor.contracts.capacity_v1 import AccountCapacityViewV1 as DomainCapacity
from agentmonitor.contracts.capacity_v1 import (
    CapacitySubjectV1,
    ExactMetricFieldV1,
)
from agentmonitor.contracts.capacity_v1 import (
    QuotaWindowViewV1 as DomainWindow,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.queries import CapacityQueryUnavailableV1
from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["capacity"])


def _metric(item: ExactMetricFieldV1) -> ExactMetricFieldWireV1:
    value = item.value
    return ExactMetricFieldWireV1(
        availability=item.availability.state,
        value=None
        if value is None
        else ExactQuantityWireV1(
            coefficient=value.amount.coefficient,
            scale=value.amount.scale,
            unit=value.unit,
        ),
        precision=item.precision,
        confidence=item.confidence,
        value_kind=item.value_kind,
        reason_code=item.reason_code,
    )


def _subject(item: CapacitySubjectV1) -> CapacitySubjectWireV1:
    return CapacitySubjectWireV1(
        provider_key=item.provider_key,
        installation_id=item.installation_id.value,
        account_id=item.account_id.value,
        resource_id=item.resource_id.value,
    )


def _window(item: DomainWindow) -> QuotaWindowViewV1:
    return QuotaWindowViewV1(
        window_id=item.window_id.value,
        subject=_subject(item.subject),
        window_key=item.window_key,
        safe_label=item.safe_label,
        used=_metric(item.used),
        remaining=_metric(item.remaining),
        limit=_metric(item.limit),
        remaining_ratio=_metric(item.remaining_ratio),
        provenance=CapacityObservationProvenanceWireV1(
            capability_id=item.provenance.capability_id,
            capability_schema_version=item.provenance.capability_schema_version,
            adapter_id=item.provenance.adapter_id,
            adapter_version=item.provenance.adapter_version,
            provider_protocol_version=item.provenance.provider_protocol_version,
            source_id=item.provenance.source_id,
            source_class=item.provenance.source_class,
            mechanism_version=item.provenance.mechanism_version,
            parser_version=item.provenance.parser_version,
            provider_version=item.provenance.provider_version,
            freshness_deadline=item.provenance.freshness_deadline,
            freshness_policy_id=item.provenance.freshness_policy_id,
            precision=item.provenance.precision,
            confidence=item.provenance.confidence,
            confidence_reason_code=item.provenance.confidence_reason_code,
            is_experimental=item.provenance.is_experimental,
            decision_reference=item.provenance.decision_reference,
        ),
        freshness=item.freshness,
        current_observation_id=item.current_observation_id.value,
        collection_run_id=item.collection_run_id.value,
        observed_at=item.observed_at,
        collected_at=item.collected_at,
        stored_at=item.stored_at,
    )


def _capacity(item: DomainCapacity) -> AccountCapacityItemV1:
    health = item.health
    return AccountCapacityItemV1(
        subject=_subject(item.subject),
        windows=tuple(_window(value) for value in item.windows),
        health=None
        if health is None
        else CapacityHealthViewV1(
            state=health.state,
            completeness=health.completeness,
            freshness=health.freshness,
            constraining_window_id=health.constraining_window_id,
            policy_id=health.policy_id,
            policy_version=health.policy_version,
            explanation_codes=health.explanation_codes,
        ),
    )


@router.get(
    "/accounts/{account_id}/capacity",
    operation_id="capacity_get_account_v1",
    response_model=AccountCapacityViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "GetAccountCapacityV1"),
)
def get_account_capacity(account_id: str, request: Request) -> AccountCapacityViewV1:
    authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset())
    require_opaque_selector(account_id)
    as_of = datetime.now(UTC)
    try:
        result = observation_ports(request).get_account_capacity(
            OpaqueIdV1(account_id), as_of=as_of
        )
    except CapacityQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return AccountCapacityViewV1(
        account_id=account_id,
        items=tuple(_capacity(item) for item in result.items),
        availability=availability(result.availability),
    )


@router.get(
    "/accounts/{account_id}/quotas",
    operation_id="capacity_list_quota_windows_v1",
    response_model=QuotaWindowPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "ListQuotaWindowsV1"),
)
def list_quota_windows(
    account_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
) -> QuotaWindowPageV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset({"limit", "cursor"}))
    require_opaque_selector(account_id)
    as_of = datetime.now(UTC)
    filters: dict[str, str | None] = {"account_id": account_id}
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="capacity_list_quota_windows_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = observation_ports(request).list_quota_windows.page(
            OpaqueIdV1(account_id), as_of=as_of, limit=limit, after_key=after_key
        )
    except CapacityQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return QuotaWindowPageV1(
        account_id=account_id,
        items=tuple(_window(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="capacity_list_quota_windows_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )
