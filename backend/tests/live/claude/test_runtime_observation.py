"""Real Linux/Claude process facts; no provider process is created or controlled."""

import hashlib
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.contracts import runtime_observation_v1 as runtime_contracts


def _request() -> runtime_contracts.PlatformInspectionRequestV1:
    return runtime_contracts.PlatformInspectionRequestV1(
        operation_id="m3-runtime-live-observation",
        correlation_id="m3-runtime-live-observation",
        provider_key=None,
        installation_id=None,
        provider_version=None,
        source_id="linux.proc.process.v1",
        selector_id="linux.proc.claude-process.v1",
        executable_identity="claude",
        requested_fields=(
            "kernel_state",
            "parent_pid",
            "resident_pages",
            "system_cpu_ticks",
            "thread_count",
            "user_cpu_ticks",
        ),
        maximum_candidates=4096,
        maximum_results=128,
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
    )


def test_real_same_uid_comm_candidate_has_generic_pid_start_identity() -> None:
    """Read-only procfs proof only; exact Claude/version attribution is Blocked."""
    assert hasattr(runtime_contracts, "PlatformInspectionRequestV1")
    from agentmonitor.adapters.platform.linux.processes import InspectLinuxProcessesV1

    request = _request()

    outcome = InspectLinuxProcessesV1()(request)

    assert outcome.state in {"success", "partial"}
    assert outcome.processes
    assert all(process.identity.pid > 0 for process in outcome.processes)
    assert all(process.identity.start_time_ticks > 0 for process in outcome.processes)
    assert all(process.identity.platform_scope_id for process in outcome.processes)
    assert all(
        process.executable_label.value == "claude" for process in outcome.processes
    )
    assert all(process.provider_key is None for process in outcome.processes)
    assert all(process.installation_id is None for process in outcome.processes)
    assert all(process.executable_identity is None for process in outcome.processes)
    if outcome.state == "success":
        assert outcome.candidate_count == len(outcome.processes)

    independently_verified = 0
    for process in outcome.processes:
        proc_dir = Path("/proc") / str(process.identity.pid)
        try:
            current_uid = proc_dir.stat(follow_symlinks=False).st_uid
            with (proc_dir / "stat").open("rb") as stream:
                raw = stream.read(16 * 1024 + 1)
        except (FileNotFoundError, ProcessLookupError):
            continue
        assert len(raw) <= 16 * 1024
        assert raw.endswith(b"\n")
        close_index = raw.rfind(b")")
        fields = raw[close_index + 2 :].decode("ascii").split()
        current_start_ticks = int(fields[19])
        if current_start_ticks != process.identity.start_time_ticks:
            continue
        assert current_uid == os.getuid()
        assert raw[raw.find(b"(") + 1 : close_index] == b"claude"
        independently_verified += 1

    assert independently_verified > 0


def test_real_reviewed_executable_proves_claude_installation_attribution() -> None:
    """LNX-LIVE-001: exact executable identity, not comm, proves attribution."""
    from agentmonitor.adapters.platform.linux.processes import (
        LINUX_PROCESS_ADAPTER_VERSION,
        LINUX_PROCESS_SOURCE_VERSION,
        ApprovedLinuxExecutableSelectorV1,
        InspectLinuxProcessesV1,
    )

    installation = discover_default_installation()
    selector = ApprovedLinuxExecutableSelectorV1.from_executable(
        selector_id="linux.proc.claude-process.v1",
        executable_identity="claude",
        provider_key="claude",
        installation_id=installation.installation_ref.value,
        provider_version=installation.provider_version,
        executable=installation.executable_for_adapter,
    )
    request = runtime_contracts.PlatformInspectionRequestV1(
        operation_id="m3-runtime-live-executable-attribution",
        correlation_id="m3-runtime-live-executable-attribution",
        provider_key="claude",
        installation_id=installation.installation_ref.value,
        provider_version=installation.provider_version,
        source_id="linux.proc.process.v1",
        selector_id="linux.proc.claude-process.v1",
        executable_identity="claude",
        requested_fields=("parent_pid",),
        maximum_candidates=4096,
        maximum_results=128,
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
    )

    outcome = InspectLinuxProcessesV1(approved_executable_selectors=(selector,))(
        request
    )

    assert outcome.state in {"success", "partial"}
    assert outcome.processes
    assert all(process.provider_key == "claude" for process in outcome.processes)
    assert all(
        process.installation_id == installation.installation_ref.value
        for process in outcome.processes
    )
    assert all(
        process.adapter_version == LINUX_PROCESS_ADAPTER_VERSION
        and process.source_version == LINUX_PROCESS_SOURCE_VERSION
        for process in outcome.processes
    )

    approved_stat = installation.executable_for_adapter.stat()
    canonical_identity = "\x1f".join(
        (
            "linux.proc.executable-identity.v1",
            str(approved_stat.st_dev),
            str(approved_stat.st_ino),
            str(stat.S_IFMT(approved_stat.st_mode)),
            str(approved_stat.st_size),
            str(approved_stat.st_mtime_ns),
            str(approved_stat.st_ctime_ns),
        )
    ).encode("ascii")
    expected_fingerprint = hashlib.sha256(canonical_identity).hexdigest()
    assert {process.executable_identity for process in outcome.processes} == {
        expected_fingerprint
    }
    independently_verified = 0
    for process in outcome.processes:
        proc_dir = Path("/proc") / str(process.identity.pid)
        try:
            current_stat = proc_dir.stat(follow_symlinks=False)
            executable_stat = (proc_dir / "exe").stat()
            with (proc_dir / "stat").open("rb") as stream:
                raw = stream.read(16 * 1024 + 1)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        assert len(raw) <= 16 * 1024
        assert raw.endswith(b"\n")
        close_index = raw.rfind(b")")
        fields = raw[close_index + 2 :].decode("ascii").split()
        if int(fields[19]) != process.identity.start_time_ticks:
            continue
        assert current_stat.st_uid == os.getuid()
        assert (executable_stat.st_dev, executable_stat.st_ino) == (
            approved_stat.st_dev,
            approved_stat.st_ino,
        )
        independently_verified += 1

    assert independently_verified > 0
