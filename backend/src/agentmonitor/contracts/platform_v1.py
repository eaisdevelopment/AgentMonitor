"""Portable capabilities; platform implementation/evidence stay adapter-owned."""

from dataclasses import dataclass
from typing import ClassVar

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, TechnicalValueV1


@dataclass(frozen=True, slots=True)
class PortablePlatformPrimitivesV1(TechnicalValueV1):
    """Explicit availability of the portable filesystem/clock safety primitives.

    Process inspection belongs to M06's CTR-RUN-006. No process control is exposed.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-PLAT-001"
    platform_id: str
    adapter_version: str
    approved_roots: FieldAvailabilityV1
    safe_file_reads: FieldAvailabilityV1
    ownership_permissions: FieldAvailabilityV1
    exclusive_locks: FieldAvailabilityV1
    atomic_replace: FieldAvailabilityV1
    durable_fsync: FieldAvailabilityV1
    monotonic_clock: FieldAvailabilityV1
