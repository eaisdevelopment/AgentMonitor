"""Technical safety constraints; these values cannot execute a boundary."""

from dataclasses import dataclass
from typing import ClassVar

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1


@dataclass(frozen=True, slots=True)
class SafeSubprocessExecutionV1(TechnicalValueV1):
    """Bounded read operation policy: no shell, environment values or agent control.

    The adapter resolves an approved operation to its fixed argument vector and
    minimal environment. Cancellation/deadline apply only to that owned child.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-BOUNDARY-001"
    approved_operation_id: OpaqueIdV1
    timeout_ms: int
    maximum_output_bytes: int
    allowed_environment_names: tuple[str, ...]
    correlation_id: OpaqueIdV1


@dataclass(frozen=True, slots=True)
class ApprovedRootAndFileReadV1(TechnicalValueV1):
    """Bounded approved-object read; root/type/symlink checks are adapter-owned."""

    CONTRACT_ID: ClassVar[str] = "CTR-BOUNDARY-003"
    approved_root_ref: OpaqueIdV1
    approved_object_ref: OpaqueIdV1
    maximum_read_bytes: int
    timeout_ms: int
    allowed_field_names: tuple[str, ...]
