"""Exercise real Ollama process identification without inspecting process content."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from shutil import which

from agentmonitor.adapters.platform.linux.processes import (
    LINUX_PROCESS_ADAPTER_VERSION,
    LINUX_PROCESS_SOURCE_VERSION,
    ApprovedLinuxExecutableSelectorV1,
    InspectLinuxProcessesV1,
)
from agentmonitor.adapters.providers.ollama.installation import discover_installation
from agentmonitor.composition.linux_process_locations import (
    read_live_process_locations_v1,
)
from agentmonitor.contracts.runtime_observation_v1 import PlatformInspectionRequestV1


def test_real_ollama_executable_process_is_attributed_without_an_account():
    installation = discover_installation()
    assert installation.outcome == "success"
    assert installation.installation_ref is not None
    executable, expected_file_identity = (
        installation.executable_for_process_observation()
    )
    selector = ApprovedLinuxExecutableSelectorV1.from_executable(
        selector_id="linux.proc.ollama-process.v1",
        executable_identity="ollama",
        provider_key="ollama",
        installation_id=installation.installation_ref.value,
        provider_version=installation.cli_version,
        executable=executable,
        expected_file_identity=expected_file_identity,
    )
    request = PlatformInspectionRequestV1(
        operation_id="m6-real-ollama-process-discovery",
        correlation_id="m6-real-ollama-process-discovery",
        provider_key="ollama",
        installation_id=installation.installation_ref.value,
        provider_version=installation.cli_version,
        source_id="linux.proc.process.v1",
        selector_id="linux.proc.ollama-process.v1",
        executable_identity="ollama",
        requested_fields=("kernel_state", "parent_pid", "thread_count"),
        maximum_candidates=16384,
        maximum_results=512,
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
    )
    outcome = InspectLinuxProcessesV1(approved_executable_selectors=(selector,))(
        request
    )
    assert outcome.state in {"success", "partial"}
    assert outcome.processes
    assert all(process.provider_key == "ollama" for process in outcome.processes)
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


def test_shared_live_locations_include_exact_ollama_without_guessing_account():
    installation = discover_installation()
    assert installation.outcome == "success"
    assert installation.installation_ref is not None
    executable_name = which("ollama")
    assert executable_name is not None
    executable = Path(executable_name).resolve(strict=True)

    result = read_live_process_locations_v1()
    ollama = tuple(item for item in result.items if item.provider_key == "ollama")

    assert result.availability.state in {"available", "partial"}
    if result.availability.state == "partial":
        assert result.availability.reason_code == "provider_discovery_partial"
    assert ollama
    assert all(item.snapshot is not None for item in ollama)
    assert all(item.provider_version == installation.cli_version for item in ollama)
    assert all(item.account_association is None for item in ollama)
    stable = []
    for item in ollama:
        try:
            observed_executable = (
                Path("/proc") / str(item.identity.pid) / "exe"
            ).resolve(strict=True)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        assert observed_executable.samefile(executable)
        stable.append(item)
    assert stable, "one stable real same-user Ollama process is required"
