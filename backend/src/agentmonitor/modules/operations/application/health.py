"""M08 read-only leaf fan-out; asyncio is confined to this approved application seam.

Producer ports enforce actual I/O deadlines. These guards cannot make an
uncancellable blocking adapter safe. Only owned health tasks are cancelled.
"""

import asyncio
from datetime import UTC, datetime

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.foundation_v1 import GetLifecycleStateV1
from agentmonitor.contracts.operations_v1 import (
    ComponentHealthRequestV1,
    ComponentHealthResultV1,
    ComponentRegistrationV1,
    GetComponentHealthV1,
    GetSchemaVersionV1,
    HealthViewV1,
    InvalidOperationsContractV1,
    LivenessViewV1,
    OperationsQueryRequestV1,
    ReadinessViewV1,
    VersionValueV1,
)
from agentmonitor.modules.operations.domain.health import (
    classify_liveness_v1,
    classify_operations_health_v1,
    validate_manifest_v1,
)


class OperationsHealthQueriesV1:
    def __init__(
        self,
        manifest: tuple[ComponentRegistrationV1, ...],
        leaves: tuple[tuple[str, GetComponentHealthV1], ...],
        lifecycle: GetLifecycleStateV1,
        schema_version: GetSchemaVersionV1,
    ) -> None:
        validate_manifest_v1(manifest)
        available = dict(leaves)
        if len(available) != len(leaves) or not available.keys() <= {
            item.component_key for item in manifest
        }:
            raise InvalidOperationsContractV1("operations_manifest_invalid")
        self._manifest = manifest
        self._leaves = available
        self._lifecycle = lifecycle
        self._schema_version = schema_version

    def get_liveness(
        self, as_of: datetime, correlation_id: OpaqueIdV1
    ) -> LivenessViewV1:
        return classify_liveness_v1(self._lifecycle().phase, as_of, correlation_id)

    async def _read_leaf(
        self, registration: ComponentRegistrationV1, request: OperationsQueryRequestV1
    ) -> ComponentHealthResultV1:
        key = registration.component_key
        reason = "operations_component_unavailable"
        leaf = self._leaves.get(key)
        if leaf is None:
            reason = (
                "operations_required_component_missing"
                if registration.criticality == "required_for_normal_readiness"
                else reason
            )
        else:
            remaining = (request.deadline - datetime.now(UTC)).total_seconds()
            if remaining <= 0:
                reason = "operations_component_timeout"
            else:
                try:
                    result = await asyncio.wait_for(
                        leaf(
                            ComponentHealthRequestV1(
                                key,
                                request.correlation_id,
                                request.as_of,
                                request.deadline,
                                request.disclosure_level,
                                registration.indicator_keys,
                            )
                        ),
                        remaining,
                    )
                    if (
                        type(result) is not ComponentHealthResultV1
                        or result.component_key != key
                        or result.sample is not None
                        and not {item.key for item in result.sample.indicators}
                        <= set(registration.indicator_keys)
                    ):
                        reason = "operations_component_invalid"
                    else:
                        return result
                except TimeoutError:
                    reason = "operations_component_timeout"
                except asyncio.CancelledError:
                    task = asyncio.current_task()
                    if task is not None and task.cancelling():
                        raise
                    reason = "operations_component_unavailable"
                except Exception:
                    # Boundary classification discards raw exception objects/text.
                    reason = "operations_component_unavailable"
        return ComponentHealthResultV1(
            key, "unavailable", None, datetime.now(UTC), reason
        )

    async def get_health_and_readiness(
        self, request: OperationsQueryRequestV1
    ) -> tuple[HealthViewV1, ReadinessViewV1]:
        results = await asyncio.gather(
            *(self._read_leaf(registration, request) for registration in self._manifest)
        )
        return classify_operations_health_v1(
            self._manifest,
            tuple(results),
            as_of=datetime.now(UTC),
            correlation_id=request.correlation_id,
        )

    async def get_schema_version(
        self, request: OperationsQueryRequestV1
    ) -> VersionValueV1:
        remaining = (request.deadline - datetime.now(UTC)).total_seconds()
        if remaining > 0:
            try:
                result = await asyncio.wait_for(
                    self._schema_version(request), remaining
                )
                if type(result) is VersionValueV1 and result.source == "schema_port":
                    return result
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
        return VersionValueV1(None, FieldAvailabilityV1("unavailable"), "schema_port")
