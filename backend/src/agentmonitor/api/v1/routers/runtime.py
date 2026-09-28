"""Authenticated, read-only M06 runtime transports."""

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
from agentmonitor.api.v1.schemas.runtime import (
    AgentProcessMetricPageV1,
    AgentProcessMetricViewV1,
    AgentProcessPageV1,
    AgentProcessViewV1,
    AgentSessionPageV1,
    AgentSessionViewV1,
    FallbackAttemptWireV1,
    FieldAvailabilityWireV1,
    LiveProcessLocationPageV1,
    LiveProcessLocationViewV1,
    ObservationProvenanceWireV1,
    ProcessCodeFieldWireV1,
    ProcessIdentityWireV1,
    ProcessLabelFieldWireV1,
    ProcessMetricFieldWireV1,
    SessionIdentityWireV1,
    SessionTreeNodeV1,
    SessionTreeViewV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    AgentProcessRecordV1,
    AgentSessionRecordV1,
    ProcessMetricFieldV1,
)
from agentmonitor.contracts.runtime_observation_v1 import (
    SessionTreeViewV1 as DomainSessionTreeViewV1,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    AgentSessionNotFoundV1,
    RuntimeQueryUnavailableV1,
)
from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["runtime"])


@router.get(
    "/process-locations",
    operation_id="runtime_list_process_locations_v1",
    response_model=LiveProcessLocationPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "ListLiveProcessLocationsV1"),
)
def list_process_locations(request: Request) -> LiveProcessLocationPageV1:
    authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset())
    query = observation_ports(request).list_live_process_locations
    if query is None:
        raise ProblemError(503, "observation_data_unavailable")
    result = query()
    return LiveProcessLocationPageV1(
        items=tuple(
            LiveProcessLocationViewV1(
                pid=item.identity.pid,
                start_time_ticks=item.identity.start_time_ticks,
                platform_scope_id=item.identity.platform_scope_id,
                provider_key=item.provider_key,
                state="running",
                account_correlation="unresolved",
                working_directory=item.working_directory,
                observed_at=item.observed_at,
            )
            for item in result.items
        ),
        availability=availability(result.availability),
        provider_version=result.provider_version,
        source_id="linux.proc.cwd.v1",
        truncated=result.truncated,
    )


def _provenance(item: ObservationProvenanceV1) -> ObservationProvenanceWireV1:
    return ObservationProvenanceWireV1(
        provider_key=item.provider_key,
        capability_id=item.capability_id,
        capability_schema_version=item.capability_schema_version,
        adapter_id=item.adapter_id,
        adapter_version=item.adapter_version,
        provider_protocol_version=item.provider_protocol_version,
        source_id=item.source_id,
        source_class=item.source_class,
        mechanism_version=item.mechanism_version,
        parser_version=item.parser_version,
        provider_version=item.provider_version,
        provider_version_availability=FieldAvailabilityWireV1(
            state=item.provider_version_availability.state
        ),
        observed_at=item.observed_at,
        observed_at_availability=FieldAvailabilityWireV1(
            state=item.observed_at_availability.state
        ),
        collected_at=item.collected_at,
        freshness_deadline=item.freshness_deadline,
        freshness_availability=FieldAvailabilityWireV1(
            state=item.freshness_availability.state
        ),
        freshness_policy_id=item.freshness_policy_id,
        precision=item.precision,
        confidence=item.confidence,
        confidence_reason_code=item.confidence_reason_code,
        value_kind=item.value_kind,
        is_experimental=item.is_experimental,
        fallback_lineage=tuple(
            FallbackAttemptWireV1(
                source_id=value.source_id, failure_code=value.failure_code
            )
            for value in item.fallback_lineage
        ),
        warnings=item.warnings,
        operation_id=item.operation_id.value,
        correlation_id=item.correlation_id.value,
        decision_reference=item.decision_reference,
        derivation_method=item.derivation_method,
        input_observation_ids=tuple(
            value.value for value in item.input_observation_ids
        ),
    )


def _process(item: AgentProcessRecordV1) -> AgentProcessViewV1:
    return AgentProcessViewV1(
        process_id=item.process_id.value,
        identity=ProcessIdentityWireV1(
            platform_source=item.identity.platform_source,
            platform_scope_id=item.identity.platform_scope_id,
            pid=item.identity.pid,
            start_time_ticks=item.identity.start_time_ticks,
        ),
        provider_key=item.provider_key,
        installation_id=item.installation_id,
        executable_label=ProcessLabelFieldWireV1(
            state=item.executable_label.state,
            value=item.executable_label.value,
            reason_code=item.executable_label.reason_code,
        ),
        provenance=_provenance(item.provenance),
        first_observed_at=item.first_observed_at,
        last_observed_at=item.last_observed_at,
        presence=item.presence,
        current_snapshot_id=item.current_snapshot_id.value,
        revision=item.revision,
    )


def _process_metric(item: AgentProcessRecordV1) -> AgentProcessMetricViewV1:
    def metric(field: ProcessMetricFieldV1) -> ProcessMetricFieldWireV1:
        return ProcessMetricFieldWireV1(
            state=field.state,
            value=field.value,
            unit=field.unit,
            reason_code=field.reason_code,
        )

    base = _process(item)
    return AgentProcessMetricViewV1(
        **base.model_dump(),
        parent_pid=metric(item.parent_pid),
        user_cpu_ticks=metric(item.user_cpu_ticks),
        system_cpu_ticks=metric(item.system_cpu_ticks),
        resident_pages=metric(item.resident_pages),
        thread_count=metric(item.thread_count),
        kernel_state=ProcessCodeFieldWireV1(
            state=item.kernel_state.state,
            value=item.kernel_state.value,
            reason_code=item.kernel_state.reason_code,
        ),
        clock_ticks_per_second=item.clock_ticks_per_second,
        page_size_bytes=item.page_size_bytes,
    )


def _session(item: AgentSessionRecordV1) -> AgentSessionViewV1:
    return AgentSessionViewV1(
        session_id=item.session_id.value,
        identity=SessionIdentityWireV1(
            provider_key=item.identity.provider_key,
            installation_id=item.identity.installation_id,
            identity_kind=item.identity.identity_kind,
            identity_value=item.identity.identity_value,
        ),
        provenance=_provenance(item.provenance),
        first_observed_at=item.first_observed_at,
        last_observed_at=item.last_observed_at,
        correlation_state=item.correlation_state,
        account_id=item.account_id,
        revision=item.revision,
    )


def _session_tree(item: DomainSessionTreeViewV1) -> SessionTreeViewV1:
    return SessionTreeViewV1(
        root_session_id=item.root_session_id.value,
        as_of=item.as_of,
        nodes=tuple(
            SessionTreeNodeV1(
                session=_session(node.session),
                parent_session_id=(
                    node.parent_session_id.value
                    if node.parent_session_id is not None
                    else None
                ),
                child_session_ids=tuple(
                    child_id.value for child_id in node.child_session_ids
                ),
                orphan_reason=node.orphan_reason,
            )
            for node in item.nodes
        ),
        included_count=item.included_count,
        excluded_count=item.excluded_count,
        unknown_count=item.unknown_count,
        partial=item.partial,
        reason_codes=item.reason_codes,
    )


@router.get(
    "/processes",
    operation_id="runtime_list_processes_v1",
    response_model=AgentProcessPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "ListAgentProcessesV1"),
)
def list_processes(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
    provider_key: str | None = Query(None, min_length=1, max_length=64),
) -> AgentProcessPageV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset({"limit", "cursor", "provider_key"}))
    as_of = datetime.now(UTC)
    filters = {"provider_key": provider_key}
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="runtime_list_processes_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = observation_ports(request).list_processes.page(
            provider_key=provider_key, as_of=as_of, limit=limit, after_key=after_key
        )
    except RuntimeQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return AgentProcessPageV1(
        items=tuple(_process(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="runtime_list_processes_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.get(
    "/process-metrics",
    operation_id="runtime_list_process_metrics_v1",
    response_model=AgentProcessMetricPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "ListAgentProcessesV1"),
)
def list_process_metrics(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
    provider_key: str | None = Query(None, min_length=1, max_length=64),
) -> AgentProcessMetricPageV1:
    caller = authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset({"limit", "cursor", "provider_key"}))
    as_of = datetime.now(UTC)
    filters = {"provider_key": provider_key}
    after_key = decode_cursor(
        request,
        caller,
        cursor,
        operation_id="runtime_list_process_metrics_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = observation_ports(request).list_processes.page(
            provider_key=provider_key, as_of=as_of, limit=limit, after_key=after_key
        )
    except RuntimeQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return AgentProcessMetricPageV1(
        items=tuple(_process_metric(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="runtime_list_process_metrics_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.get(
    "/sessions",
    operation_id="runtime_list_sessions_v1",
    response_model=AgentSessionPageV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "ListAgentSessionsV1"),
)
def list_sessions(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
    provider_key: str | None = Query(None, min_length=1, max_length=64),
    account_id: str | None = Query(None, min_length=1, max_length=256),
) -> AgentSessionPageV1:
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
        operation_id="runtime_list_sessions_v1",
        limit=limit,
        filters=filters,
    )
    try:
        result = observation_ports(request).list_sessions.page(
            provider_key=provider_key,
            account_id=OpaqueIdV1(account_id) if account_id is not None else None,
            as_of=as_of,
            limit=limit,
            after_key=after_key,
        )
    except RuntimeQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return AgentSessionPageV1(
        items=tuple(_session(item) for item in result.items),
        page=page_meta(
            request,
            caller,
            operation_id="runtime_list_sessions_v1",
            limit=result.limit,
            has_more=result.has_more,
            next_key=result.next_key,
            filters=filters,
        ),
        availability=availability(result.availability),
    )


@router.get(
    "/sessions/{session_id}/tree",
    operation_id="runtime_get_session_tree_v1",
    response_model=SessionTreeViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "GetSessionTreeV1"),
)
def get_session_tree(
    session_id: str,
    request: Request,
    depth_limit: int = Query(8, ge=1, le=32),
    node_limit: int = Query(200, ge=1, le=200),
) -> SessionTreeViewV1:
    authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset({"depth_limit", "node_limit"}))
    require_opaque_selector(session_id)
    try:
        item = observation_ports(request).get_session_tree(
            OpaqueIdV1(session_id),
            as_of=datetime.now(UTC),
            depth_limit=depth_limit,
            node_limit=node_limit,
        )
    except AgentSessionNotFoundV1:
        raise ProblemError(404, "resource_not_found") from None
    except RuntimeQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return _session_tree(item)


@router.get(
    "/sessions/{session_id}",
    operation_id="runtime_get_session_v1",
    response_model=AgentSessionViewV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:telemetry", "GetAgentSessionV1"),
)
def get_session(session_id: str, request: Request) -> AgentSessionViewV1:
    authorize_request(request, "read:telemetry")
    reject_unknown_query(request, frozenset())
    require_opaque_selector(session_id)
    as_of = datetime.now(UTC)
    try:
        item = observation_ports(request).get_session(
            OpaqueIdV1(session_id), as_of=as_of
        )
    except AgentSessionNotFoundV1:
        raise ProblemError(404, "resource_not_found") from None
    except RuntimeQueryUnavailableV1:
        raise ProblemError(503, "observation_repository_unavailable") from None
    return _session(item)
