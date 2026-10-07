"""Real Linux/Codex process attribution without process control or content reads."""

from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.platform.linux.processes import (
    LINUX_PROCESS_ADAPTER_VERSION,
    LINUX_PROCESS_SOURCE_VERSION,
    ApprovedLinuxExecutableSelectorV1,
    InspectLinuxProcessesV1,
)
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.contracts.runtime_observation_v1 import PlatformInspectionRequestV1


def test_real_reviewed_executable_proves_codex_installation_attribution() -> None:
    """M5-CDX-RUN-001/002: exact executable identity attributes real processes."""
    installation = discover_default_installation()
    selector = ApprovedLinuxExecutableSelectorV1.from_executable(
        selector_id="linux.proc.codex-process.v1",
        executable_identity="codex",
        provider_key="codex",
        installation_id=installation.installation_ref.value,
        provider_version=installation.provider_version,
        executable=installation.executable_for_adapter,
    )
    request = PlatformInspectionRequestV1(
        operation_id="m5-codex-runtime-live-attribution",
        correlation_id="m5-codex-runtime-live-attribution",
        provider_key="codex",
        installation_id=installation.installation_ref.value,
        provider_version=installation.provider_version,
        source_id="linux.proc.process.v1",
        selector_id="linux.proc.codex-process.v1",
        executable_identity="codex",
        requested_fields=(
            "kernel_state",
            "parent_pid",
            "resident_pages",
            "system_cpu_ticks",
            "thread_count",
            "user_cpu_ticks",
        ),
        maximum_candidates=16_384,
        maximum_results=512,
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
    )

    outcome = InspectLinuxProcessesV1(approved_executable_selectors=(selector,))(
        request
    )

    assert outcome.state in {"success", "partial"}
    assert outcome.processes
    assert all(process.provider_key == "codex" for process in outcome.processes)
    assert all(
        process.installation_id == installation.installation_ref.value
        for process in outcome.processes
    )
    assert all(process.executable_identity is not None for process in outcome.processes)
    assert all(
        process.adapter_version == LINUX_PROCESS_ADAPTER_VERSION
        and process.source_version == LINUX_PROCESS_SOURCE_VERSION
        for process in outcome.processes
    )
    assert all(not hasattr(process, "account_id") for process in outcome.processes)
