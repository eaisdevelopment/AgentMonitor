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
    AgentProcessPageV1,
    AgentProcessViewV1,
    AgentSessionPageV1,
    AgentSessionViewV1,
    FallbackAttemptWireV1,
    FieldAvailabilityWireV1,
    ObservationProvenanceWireV1,
    ProcessIdentityWireV1,
    ProcessLabelFieldWireV1,
    SessionIdentityWireV1,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    AgentProcessRecordV1,
    AgentSessionRecordV1,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    AgentSessionNotFoundV1,
    RuntimeQueryUnavailableV1,
)
from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["runtime"])


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
