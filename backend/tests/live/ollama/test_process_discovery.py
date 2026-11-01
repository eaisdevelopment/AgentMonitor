"""Exercise real Ollama process identification without inspecting process content."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from shutil import which

from agentmonitor.adapters.platform.linux.processes import (
    ApprovedLinuxExecutableSelectorV1,
    InspectLinuxProcessesV1,
)
from agentmonitor.adapters.providers.ollama.installation import discover_installation
from agentmonitor.contracts.runtime_observation_v1 import PlatformInspectionRequestV1


def test_real_ollama_executable_process_is_attributed_without_an_account():
    installation = discover_installation()
    assert installation.outcome == "success"
    executable_name = which("ollama")
    assert executable_name is not None
    executable = Path(executable_name).resolve(strict=True)
    info = executable.stat()
    installation_ref = sha256(f"{info.st_dev}:{info.st_ino}".encode()).hexdigest()
    selector = ApprovedLinuxExecutableSelectorV1.from_executable(
        selector_id="linux.proc.ollama-process.v1",
        executable_identity="ollama",
        provider_key="ollama",
        installation_id=installation_ref,
        provider_version=installation.cli_version,
        executable=executable,
    )
    request = PlatformInspectionRequestV1(
        operation_id="m6-real-ollama-process-discovery",
        correlation_id="m6-real-ollama-process-discovery",
        provider_key="ollama",
        installation_id=installation_ref,
        provider_version=installation.cli_version,
        source_id="linux.proc.process.v1",
        selector_id="linux.proc.ollama-process.v1",
        executable_identity="ollama",
        requested_fields=("kernel_state", "parent_pid", "thread_count"),
        maximum_candidates=16384,
        maximum_results=512,
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
    )
    outcome = InspectLinuxProcessesV1(approved_executable_selectors=(selector,))(request)
    assert outcome.state in {"success", "partial"}
    assert outcome.processes
    assert all(process.provider_key == "ollama" for process in outcome.processes)
    assert all(process.installation_id == installation_ref for process in outcome.processes)
    assert all(not hasattr(process, "account_id") for process in outcome.processes)
