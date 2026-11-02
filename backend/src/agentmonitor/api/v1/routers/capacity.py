"""Authenticated, read-only M05 capacity transports."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request

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
    CapacityForecastPageV1,
    CapacityForecastWireV1,
    CapacityHealthViewV1,
    CapacityHistoryPageV1,
    CapacityHistoryPointV1,
    CapacityObservationProvenanceWireV1,
    CapacityScopeViewV1,
    CapacitySubjectWireV1,
    ExactMetricFieldWireV1,
    ExactQuantityWireV1,
    QuotaAllowanceViewV1,
    QuotaWindowPageV1,
    QuotaWindowViewV1,
)
from agentmonitor.api.v1.serialization import technical_wire
from agentmonitor.contracts.capacity_v1 import AccountCapacityViewV1 as DomainCapacity
from agentmonitor.contracts.capacity_v1 import (
    CapacityAggregateQueryV1,
    CapacityForecastQueryV1,
    CapacityHistoryQueryV1,
    CapacitySubjectV1,
    ExactMetricFieldV1,
    InvalidCapacityContractV1,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityHistoryPointV1 as DomainHistoryPoint,
)
from agentmonitor.contracts.capacity_v1 import (
    QuotaWindowViewV1 as DomainWindow,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.application.queries import (
    CapacityQueryUnavailableV1,
    GetQuotaAllowanceV1,
)

router = APIRouter(tags=["capacity"])


def _utc_filter(value: datetime) -> str:
    if value.utcoffset() != UTC.utcoffset(value):
        raise ProblemError(400, "invalid_filter")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


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


def _provenance(
    item: DomainWindow | DomainHistoryPoint,
) -> CapacityObservationProvenanceWireV1:
    source = item.provenance
    return CapacityObservationProvenanceWireV1(
        capability_id=source.capability_id,
        capability_schema_version=source.capability_schema_version,
        adapter_id=source.adapter_id,
        adapter_version=source.adapter_version,
        provider_protocol_version=source.provider_protocol_version,
        source_id=source.source_id,
        source_class=source.source_class,
        mechanism_version=source.mechanism_version,
        parser_version=source.parser_version,
        provider_version=source.provider_version,
        freshness_deadline=source.freshness_deadline,
        freshness_policy_id=source.freshness_policy_id,
        precision=source.precision,
        confidence=source.confidence,
        confidence_reason_code=source.confidence_reason_code,
        is_experimental=source.is_experimental,
        decision_reference=source.decision_reference,
    )


def _window(item: DomainWindow) -> QuotaWindowViewV1:
    allowance = GetQuotaAllowanceV1()(item)
    return QuotaWindowViewV1(
        window_id=item.window_id.value,
        subject=_subject(item.subject),
        window_key=item.window_key,
        safe_label=item.safe_label,
        semantic_role=item.semantic_role,
        is_constraining=item.is_constraining,
        reset_at=item.reset_at,
        reset_precision=item.reset_precision,
        allowance=QuotaAllowanceViewV1(
            remaining_percentage=_metric(allowance.remaining_percentage),
            calculation=allowance.calculation,
            input_observation_id=allowance.input_observation_id.value,
        )
        if allowance
        else None,
        used=_metric(item.used),
        remaining=_metric(item.remaining),
        limit=_metric(item.limit),
        remaining_ratio=_metric(item.remaining_ratio),
        provenance=_provenance(item),
        freshness=item.freshness,
        current_observation_id=item.current_observation_id.value,
        collection_run_id=item.collection_run_id.value,
        observed_at=item.observed_at,
        collected_at=item.collected_at,
        stored_at=item.stored_at,
    )


def _history_point(item: DomainHistoryPoint) -> CapacityHistoryPointV1:
    return CapacityHistoryPointV1(
        observation_id=item.observation_id.value,
        window_id=item.window_id.value,
        window_definition_id=item.window_definition_id.value,
        subject=_subject(item.subject),
        window_key=item.window_key,
        safe_label=item.safe_label,
        semantic_role=item.semantic_role,
        native_unit=item.native_unit,
        definition_version=item.definition_version,
        metric=item.metric,
        series_kind=item.series_kind,
        value=_metric(item.value),
        provenance=_provenance(item),
        freshness=item.freshness,
        completeness=item.completeness,
        collection_run_id=item.collection_run_id.value,
        derivation_id=(
            item.derivation_id.value if item.derivation_id is not None else None
        ),
        observed_at=item.observed_at,
        interval_start=item.interval_start,
        interval_end=item.interval_end,
        reset_at=item.reset_at,
        reset_precision=item.reset_precision,
        collected_at=item.collected_at,
        stored_at=item.stored_at,
        source_period_start=item.source_period_start,
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


@router.get(
    "/capacity/history",
    operation_id="capacity_list_history_v1",
    response_model=CapacityHistoryPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "ListCapacityHistoryV1"),
)
def list_capacity_history(
    request: Request,
    range_from: Annotated[datetime, Query(alias="from")],
    before: Annotated[datetime, Query()],
    subject_id: str = Query(..., min_length=1, max_length=256),
    metric: Literal["used", "remaining", "limit", "remaining_ratio"] = Query(...),
    series_kind: Literal["raw_provider", "poll_snapshot", "derived"] = Query(...),
    resource_id: str | None = Query(None, min_length=1, max_length=256),
    window_id: str | None = Query(None, min_length=1, max_length=256),
    bucket_method: str | None = Query(None, min_length=1, max_length=32),
    bucket_seconds: int | None = Query(None, ge=1, le=31_536_000),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
) -> CapacityHistoryPageV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(
        request,
        frozenset(
            {
                "subject_id",
                "metric",
                "series_kind",
                "from",
                "before",
                "resource_id",
                "window_id",
                "bucket_method",
                "bucket_seconds",
                "limit",
                "cursor",
            }
        ),
    )
    require_opaque_selector(subject_id)
    if resource_id is not None:
        require_opaque_selector(resource_id)
    if window_id is not None:
        require_opaque_selector(window_id)
    range_start_text = _utc_filter(range_from)
    range_before_text = _utc_filter(before)
    filters: dict[str, str | None] = {
        "subject_id": subject_id,
        "metric": metric,
        "series_kind": series_kind,
        "from": range_start_text,
        "before": range_before_text,
        "resource_id": resource_id,
        "window_id": window_id,
        "bucket_method": bucket_method,
        "bucket_seconds": (str(bucket_seconds) if bucket_seconds is not None else None),
    }
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="capacity_list_history_v1",
        limit=limit,
        filters=filters,
    )
    as_of = datetime.now(UTC)
    try:
        query = CapacityHistoryQueryV1(
            subject_id=OpaqueIdV1(subject_id),
            resource_id=(OpaqueIdV1(resource_id) if resource_id is not None else None),
            window_id=(OpaqueIdV1(window_id) if window_id is not None else None),
            metric=metric,
            series_kind=series_kind,
            range_start=range_from,
            range_before=before,
            as_of=as_of,
            limit=limit,
            after_key=after_key,
            bucket_method=bucket_method,
            bucket_seconds=bucket_seconds,
        )
    except (InvalidCapacityContractV1, TypeError, ValueError):
        raise ProblemError(400, "invalid_filter") from None
    try:
        result = observation_ports(request).list_capacity_history(query)
    except CapacityQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return CapacityHistoryPageV1(
        subject_id=subject_id,
        metric=metric,
        series_kind=series_kind,
        items=tuple(_history_point(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="capacity_list_history_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.get(
    "/capacity/scope",
    operation_id="capacity_get_scope_v1",
    response_model=CapacityScopeViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "GetCapacityAggregateV1"),
)
def get_capacity_scope(
    request: Request,
    scope_kind: Literal["global", "organization", "provider", "account"] = "global",
    scope_id: str | None = Query(None, max_length=128),
) -> CapacityScopeViewV1:
    authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset({"scope_kind", "scope_id"}))
    if (scope_kind == "global") != (scope_id is None):
        raise ProblemError(400, "invalid_filter")
    if scope_id is not None:
        require_opaque_selector(scope_id)
    services = observation_ports(request)
    if (
        services.registry_scope is None
        or services.list_account_resources is None
        or services.get_capacity_aggregate is None
        or services.capacity_health_policy is None
    ):
        raise ProblemError(503, "observation_data_unavailable")
    as_of = datetime.now(UTC)
    try:
        snapshot = services.registry_scope(
            scope_kind, OpaqueIdV1(scope_id) if scope_id is not None else None
        )
        members = set(snapshot.account_ids)
        accounts = tuple(
            account
            for account in services.list_accounts()
            if account.account_id in members
        )
        resources = tuple(
            resource
            for account in accounts
            for resource in services.list_account_resources(account.account_id)
        )
        result = services.get_capacity_aggregate(
            CapacityAggregateQueryV1(
                snapshot, accounts, resources, as_of, services.capacity_health_policy
            )
        )
    except (CapacityQueryUnavailableV1, ValueError):
        raise ProblemError(503, "observation_repository_unavailable") from None
    values = technical_wire(result)
    if not isinstance(values, dict):
        raise ProblemError(500, "internal_error")
    for key in ("accounts", "missing_accounts", "excluded_accounts"):
        coverage = getattr(result, key)
        mapped_coverage = []
        for item in coverage:
            mapped = technical_wire(item)
            if not isinstance(mapped, dict):
                raise ProblemError(500, "internal_error")
            mapped["windows"] = tuple(_window(window) for window in item.windows)
            mapped_coverage.append(mapped)
        values[key] = tuple(mapped_coverage)
    for key in (
        "registered_account_count",
        "eligible_account_count",
        "covered_account_count",
        "excluded_account_count",
        "missing_account_count",
        "observed_capacity_count",
    ):
        values[key] = getattr(result, key)
    values["health_counts"] = tuple(
        {"state": state, "count": count} for state, count in result.health_counts
    )
    values["freshness_counts"] = tuple(
        {"state": state, "count": count} for state, count in result.freshness_counts
    )
    return CapacityScopeViewV1.model_validate(values)


@router.get(
    "/accounts/{account_id}/forecasts",
    operation_id="capacity_list_forecasts_v1",
    response_model=CapacityForecastPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "ListCapacityForecastsV1"),
)
def list_capacity_forecasts(
    account_id: str,
    request: Request,
    resource_id: str | None = Query(None, max_length=128),
    window_id: str | None = Query(None, max_length=128),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
) -> CapacityForecastPageV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(
        request, frozenset({"resource_id", "window_id", "limit", "cursor"})
    )
    for selector in (account_id, resource_id, window_id):
        if selector is not None:
            require_opaque_selector(selector)
    services = observation_ports(request)
    if services.list_capacity_forecasts is None:
        raise ProblemError(503, "observation_data_unavailable")
    if services.get_account(OpaqueIdV1(account_id)) is None:
        raise ProblemError(404, "registry_subject_not_found")
    as_of = datetime.now(UTC)
    filters = {
        "account_id": account_id,
        "resource_id": resource_id,
        "window_id": window_id,
    }
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="capacity_list_forecasts_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = services.list_capacity_forecasts(
            CapacityForecastQueryV1(
                OpaqueIdV1(account_id),
                OpaqueIdV1(resource_id) if resource_id else None,
                OpaqueIdV1(window_id) if window_id else None,
                as_of,
                limit,
                after_key,
            )
        )
    except (CapacityQueryUnavailableV1, ValueError):
        raise ProblemError(503, "observation_repository_unavailable") from None
    return CapacityForecastPageV1(
        account_id=account_id,
        items=tuple(
            CapacityForecastWireV1.model_validate(technical_wire(item))
            for item in result.items
        ),
        page=page_meta(
            request,
            caller,
            operation_id="capacity_list_forecasts_v1",
            limit=limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )
