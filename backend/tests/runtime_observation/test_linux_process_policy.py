"""Linux process parsing/policy checks with one real bounded procfs read."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.platform.linux.processes import (
    InspectLinuxProcessesV1,
    _read_bounded,
    _same_owner,
    _validate_system_units,
)
from agentmonitor.contracts.runtime_observation_v1 import PlatformInspectionRequestV1


@pytest.mark.parametrize(("clock_ticks", "page_size"), [(0, 4096), (100, 0)])
def test_nonpositive_linux_system_units_fail_closed(
    clock_ticks: int, page_size: int
) -> None:
    with pytest.raises(ValueError, match="linux_process_units_invalid"):
        _validate_system_units(clock_ticks, page_size)


def test_real_proc_stat_read_is_bounded_before_materialization() -> None:
    raw = _read_bounded(Path("/proc/self/stat"), 16 * 1024)

    assert raw.endswith(b"\n")
    assert len(raw) <= 16 * 1024


def test_bounded_read_rejects_limit_smaller_than_real_proc_record() -> None:
    with pytest.raises(ValueError, match="linux_process_source_oversize"):
        _read_bounded(Path("/proc/self/stat"), 1)


def test_owner_identity_change_fails_closed() -> None:
    assert _same_owner(1000, 1000)
    assert not _same_owner(1000, 1001)


def test_caller_asserted_provider_attribution_is_rejected_before_io() -> None:
    request = PlatformInspectionRequestV1(
        operation_id="attribution-policy-test",
        correlation_id="attribution-policy-test",
        provider_key="claude",
        installation_id="unverified-installation",
        provider_version="unverified-version",
        source_id="linux.proc.process.v1",
        selector_id="linux.proc.claude-process.v1",
        executable_identity="claude",
        requested_fields=(),
        maximum_candidates=1,
        maximum_results=1,
        deadline_at=datetime.now(UTC) + timedelta(seconds=1),
    )

    outcome = InspectLinuxProcessesV1()(request)

    assert outcome.state == "unverified_platform_version"
    assert outcome.error_code == "linux_provider_attribution_unverified"
    assert outcome.processes == ()
