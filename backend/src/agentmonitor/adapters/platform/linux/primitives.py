"""Narrow real Linux CTR-PLAT-001 capability producer for the runtime slice."""

from __future__ import annotations

import os
import platform
import time
from pathlib import Path

from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.platform_v1 import PortablePlatformPrimitivesV1


class LinuxPortablePlatformPrimitivesV1:
    """Observe only the Linux primitives actually exercised by M3 Task 5."""

    def __call__(self) -> PortablePlatformPrimitivesV1:
        machine = platform.machine().strip().lower() or "unknown"
        try:
            owner_available = Path("/proc/self").stat().st_uid == os.getuid()
        except OSError:
            owner_available = False
        before = time.monotonic_ns()
        after = time.monotonic_ns()
        monotonic_available = after >= before
        return PortablePlatformPrimitivesV1(
            platform_id=f"linux-{machine}",
            adapter_version="1.0.0",
            approved_roots=FieldAvailabilityV1("unsupported"),
            safe_file_reads=FieldAvailabilityV1("unsupported"),
            ownership_permissions=FieldAvailabilityV1(
                "available" if owner_available else "unavailable"
            ),
            exclusive_locks=FieldAvailabilityV1("unsupported"),
            atomic_replace=FieldAvailabilityV1("unsupported"),
            durable_fsync=FieldAvailabilityV1("unsupported"),
            monotonic_clock=FieldAvailabilityV1(
                "available" if monotonic_available else "unavailable"
            ),
        )
