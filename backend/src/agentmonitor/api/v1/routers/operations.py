"""Authenticated M08 views; no producer files, database reads or diagnostics text."""

from datetime import UTC, datetime, timedelta

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.dependencies import authorize_request, correlation_id
from agentmonitor.api.v1.routers._observation import (
    ERROR_RESPONSES,
    policy,
    reject_unknown_query,
)
from agentmonitor.api.v1.schemas.operations import (
    OperationsDiagnosticsWireV1,
    OperationsHealthWireV1,
    OperationsLivenessWireV1,
    OperationsReadinessWireV1,
    OperationsVersionsWireV1,
)
from agentmonitor.api.v1.serialization import technical_wire as _wire
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import OperationsQueryRequestV1
from agentmonitor.modules.operations.application.service import OperationsServiceV1
from fastapi import APIRouter, Request

router = APIRouter(tags=["operations"])


def _service(request: Request) -> OperationsServiceV1:
    authorize_request(request, "read:status")
    reject_unknown_query(request, frozenset())
    service = getattr(request.app.state, "operations_ports", None)
    if not isinstance(service, OperationsServiceV1):
        raise ProblemError(503, "observation_data_unavailable")
    return service


def _query(request: Request) -> OperationsQueryRequestV1:
    now = datetime.now(UTC)
    return OperationsQueryRequestV1(
        now,
        now + timedelta(seconds=2),
        OpaqueIdV1(correlation_id(request)),
        "administrator",
    )


@router.get(
    "/operations/liveness",
    operation_id="operations_get_liveness_v1",
    response_model=OperationsLivenessWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:status", "GetLivenessV1"),
)
def get_liveness(request: Request) -> OperationsLivenessWireV1:
    service = _service(request)
    return OperationsLivenessWireV1.model_validate(
        _wire(
            service.get_liveness(datetime.now(UTC), OpaqueIdV1(correlation_id(request)))
        )
    )


@router.get(
    "/operations/readiness",
    operation_id="operations_get_readiness_v1",
    response_model=OperationsReadinessWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:status", "GetReadinessV1"),
)
async def get_readiness(request: Request) -> OperationsReadinessWireV1:
    return OperationsReadinessWireV1.model_validate(
        _wire(await _service(request).get_readiness(_query(request)))
    )


@router.get(
    "/operations/health",
    operation_id="operations_get_health_v1",
    response_model=OperationsHealthWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:status", "GetOperationsHealthV1"),
)
async def get_health(request: Request) -> OperationsHealthWireV1:
    return OperationsHealthWireV1.model_validate(
        _wire(await _service(request).get_health(_query(request)))
    )


@router.get(
    "/operations/versions",
    operation_id="operations_get_versions_v1",
    response_model=OperationsVersionsWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:status", "GetVersionInventoryV1"),
)
async def get_versions(request: Request) -> OperationsVersionsWireV1:
    return OperationsVersionsWireV1.model_validate(
        _wire(await _service(request).get_versions(_query(request)))
    )


@router.get(
    "/operations/diagnostics",
    operation_id="operations_get_diagnostics_v1",
    response_model=OperationsDiagnosticsWireV1,
    responses=ERROR_RESPONSES,
    openapi_extra=policy("read:status", "GetDiagnosticSummaryV1"),
)
async def get_diagnostics(request: Request) -> OperationsDiagnosticsWireV1:
    return OperationsDiagnosticsWireV1.model_validate(
        _wire(await _service(request).get_diagnostic_summary(_query(request)))
    )
