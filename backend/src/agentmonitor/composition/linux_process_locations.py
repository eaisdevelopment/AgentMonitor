"""Wire bounded A04 live cwd views to M06 without persisting local paths."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.platform.linux.processes import (
    ApprovedLinuxExecutableSelectorV1,
    InspectLinuxProcessesV1,
    LinuxExecutableFileIdentityV1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_process_installations as discover_claude_process_installations,
)
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation as discover_codex_installation,
)
from agentmonitor.adapters.providers.ollama.installation import (
    discover_installation as discover_ollama_installation,
)
from agentmonitor.contracts.common_v1 import QueryAvailabilityV1
from agentmonitor.contracts.runtime_observation_v1 import (
    LiveProcessLocationsV1,
    LiveProcessLocationV1,
    PlatformInspectionRequestV1,
)


@dataclass(frozen=True, slots=True)
class _ProcessInstallation:
    provider_key: str
    selector_id: str
    executable_identity: str
    installation_id: str
    provider_version: str
    executable: Path
    expected_file_identity: LinuxExecutableFileIdentityV1 | None


def _discover_installations(
    *, include_claude: bool, include_codex: bool, include_ollama: bool
) -> tuple[tuple[_ProcessInstallation, ...], bool]:
    installations: list[_ProcessInstallation] = []
    incomplete = False
    if include_claude:
        try:
            discovered, truncated = discover_claude_process_installations()
            incomplete = incomplete or truncated
            for item in discovered:
                try:
                    executable, expected_file_identity = (
                        item.executable_for_process_observation()
                    )
                    installations.append(
                        _ProcessInstallation(
                            "claude",
                            "linux.proc.claude-process.v1",
                            "claude",
                            item.installation_ref.value,
                            item.provider_version,
                            executable,
                            expected_file_identity,
                        )
                    )
                except (OSError, RuntimeError, ValueError):
                    incomplete = True
        except (OSError, RuntimeError, ValueError):
            incomplete = True
    if include_codex:
        try:
            codex_installation = discover_codex_installation()
            installations.append(
                _ProcessInstallation(
                    "codex",
                    "linux.proc.codex-process.v1",
                    "codex",
                    codex_installation.installation_ref.value,
                    codex_installation.provider_version,
                    codex_installation.executable_for_launch(),
                    None,
                )
            )
        except (OSError, RuntimeError, ValueError):
            incomplete = True
    if include_ollama:
        try:
            ollama_installation = discover_ollama_installation()
            if (
                ollama_installation.outcome != "success"
                or ollama_installation.installation_ref is None
                or ollama_installation.cli_version is None
            ):
                raise ValueError("ollama_process_installation_unavailable")
            executable, expected_file_identity = (
                ollama_installation.executable_for_process_observation()
            )
            installations.append(
                _ProcessInstallation(
                    "ollama",
                    "linux.proc.ollama-process.v1",
                    "ollama",
                    ollama_installation.installation_ref.value,
                    ollama_installation.cli_version,
                    executable,
                    expected_file_identity,
                )
            )
        except (OSError, RuntimeError, ValueError):
            incomplete = True
    return tuple(installations), incomplete


def _read_process_locations_v1(
    *, include_claude: bool, include_codex: bool, include_ollama: bool
) -> LiveProcessLocationsV1:
    observed_at = datetime.now(UTC)
    try:
        installations, truncated = _discover_installations(
            include_claude=include_claude,
            include_codex=include_codex,
            include_ollama=include_ollama,
        )
        items: list[LiveProcessLocationV1] = []
        usable = False
        deadline_at = observed_at + timedelta(seconds=3)
        for installation in installations:
            if datetime.now(UTC) >= deadline_at:
                truncated = True
                break
            try:
                selector = ApprovedLinuxExecutableSelectorV1.from_executable(
                    selector_id=installation.selector_id,
                    executable_identity=installation.executable_identity,
                    provider_key=installation.provider_key,
                    installation_id=installation.installation_id,
                    provider_version=installation.provider_version,
                    executable=installation.executable,
                    expected_file_identity=installation.expected_file_identity,
                )
                operation_id = "process-locations-" + uuid.uuid4().hex
                outcome, locations = InspectLinuxProcessesV1(
                    approved_executable_selectors=(selector,)
                ).locations(
                    PlatformInspectionRequestV1(
                        operation_id=operation_id,
                        correlation_id=operation_id,
                        provider_key=installation.provider_key,
                        installation_id=installation.installation_id,
                        provider_version=installation.provider_version,
                        source_id="linux.proc.process.v1",
                        selector_id=installation.selector_id,
                        executable_identity=installation.executable_identity,
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
                        deadline_at=deadline_at,
                    )
                )
            except (OSError, RuntimeError, ValueError):
                truncated = True
                continue
            usable = usable or outcome.state in {"success", "partial"}
            observed_at = outcome.observed_at
            items.extend(locations)
            if len(items) > 512:
                items = items[:512]
                truncated = True
                break
            truncated = (
                truncated
                or outcome.truncated
                or bool(outcome.omission_codes)
                or len(locations) < len(outcome.processes)
                or outcome.state not in {"success", "partial"}
            )
        versions = {item.provider_version for item in items if item.provider_version}
        return LiveProcessLocationsV1(
            tuple(items),
            QueryAvailabilityV1(
                "available" if usable else "unavailable",
                "same_user_exact_provider_executables"
                if usable
                else "process_source_unavailable",
                observed_at,
            ),
            next(iter(versions)) if len(versions) == 1 else None,
            truncated,
        )
    except (OSError, RuntimeError, ValueError):
        return LiveProcessLocationsV1(
            (),
            QueryAvailabilityV1(
                "unavailable", "process_source_unavailable", datetime.now(UTC)
            ),
            None,
            False,
        )


def read_live_process_locations_v1() -> LiveProcessLocationsV1:
    """Read exact Claude, Codex and Ollama processes for the neutral API view."""
    return _read_process_locations_v1(
        include_claude=True,
        include_codex=True,
        include_ollama=True,
    )


def read_live_claude_process_locations_v1() -> LiveProcessLocationsV1:
    """Compatibility wrapper retained for the existing Claude-only automation."""
    return _read_process_locations_v1(
        include_claude=True,
        include_codex=False,
        include_ollama=False,
    )
