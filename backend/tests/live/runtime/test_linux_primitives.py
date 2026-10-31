"""Real read-only Linux portable-capability observation."""

from agentmonitor.adapters.platform.linux.primitives import (
    LinuxPortablePlatformPrimitivesV1,
)


def test_real_linux_runtime_primitives_are_truthfully_scoped() -> None:
    capabilities = LinuxPortablePlatformPrimitivesV1()()

    assert capabilities.platform_id.startswith("linux-")
    assert capabilities.monotonic_clock.state == "available"
    assert capabilities.ownership_permissions.state == "available"
    assert capabilities.approved_roots.state == "unsupported"
    assert capabilities.safe_file_reads.state == "unsupported"
    assert capabilities.exclusive_locks.state == "unsupported"
    assert capabilities.atomic_replace.state == "unsupported"
    assert capabilities.durable_fsync.state == "unsupported"
