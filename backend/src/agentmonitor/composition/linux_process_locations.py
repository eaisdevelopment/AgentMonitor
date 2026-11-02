"""Wire bounded A04 live cwd views to M06 without persisting local paths."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

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


@dataclass(frozen=True, slots=True)
class _ProviderDiscoveryResultV1:
    state: Literal["available", "unavailable"]
    installations: tuple[_ProcessInstallation, ...]
    truncated: bool


def _merge_provider_discoveries_v1(
    discoveries: tuple[_ProviderDiscoveryResultV1, ...],
) -> tuple[tuple[_ProcessInstallation, ...], bool]:
    """Merge completed scopes without treating unavailability as truncation."""

    return (
        tuple(
            installation
            for discovery in discoveries
            if discovery.state == "available"
            for installation in discovery.installations
        ),
        any(
            discovery.state == "available" and discovery.truncated
            for discovery in discoveries
        ),
    )


def _discovery_availability_v1(
    *, usable: bool, provider_unavailable: bool
) -> tuple[Literal["available", "partial", "unavailable"], str]:
    """Report absent provider coverage separately from result truncation."""
    if not usable:
        return "unavailable", "process_source_unavailable"
    if provider_unavailable:
        return "partial", "provider_discovery_partial"
    return "available", "same_user_exact_provider_executables"


def _discover_claude_installations_v1() -> _ProviderDiscoveryResultV1:
    installations: list[_ProcessInstallation] = []
    try:
        discovered, truncated = discover_claude_process_installations()
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
                truncated = True
        return _ProviderDiscoveryResultV1("available", tuple(installations), truncated)
    except (OSError, RuntimeError, ValueError):
        return _ProviderDiscoveryResultV1("unavailable", (), False)


def _discover_codex_installations_v1() -> _ProviderDiscoveryResultV1:
    try:
        codex_installation = discover_codex_installation()
        return _ProviderDiscoveryResultV1(
            "available",
            (
                _ProcessInstallation(
                    "codex",
                    "linux.proc.codex-process.v1",
                    "codex",
                    codex_installation.installation_ref.value,
                    codex_installation.provider_version,
                    codex_installation.executable_for_launch(),
                    None,
                ),
            ),
            False,
        )
    except (OSError, RuntimeError, ValueError):
        return _ProviderDiscoveryResultV1("unavailable", (), False)


def _discover_ollama_installations_v1() -> _ProviderDiscoveryResultV1:
    try:
        ollama_installation = discover_ollama_installation()
        if (
            ollama_installation.outcome != "success"
            or ollama_installation.installation_ref is None
            or ollama_installation.cli_version is None
        ):
            return _ProviderDiscoveryResultV1("unavailable", (), False)
        executable, expected_file_identity = (
            ollama_installation.executable_for_process_observation()
        )
        return _ProviderDiscoveryResultV1(
            "available",
            (
                _ProcessInstallation(
                    "ollama",
                    "linux.proc.ollama-process.v1",
                    "ollama",
                    ollama_installation.installation_ref.value,
                    ollama_installation.cli_version,
                    executable,
                    expected_file_identity,
                ),
            ),
            False,
        )
    except (OSError, RuntimeError, ValueError):
        return _ProviderDiscoveryResultV1("unavailable", (), False)


def _requested_provider_discoveries_v1(
    *, include_claude: bool, include_codex: bool, include_ollama: bool
) -> tuple[Callable[[], _ProviderDiscoveryResultV1], ...]:
    discoveries: list[Callable[[], _ProviderDiscoveryResultV1]] = []
    if include_claude:
        discoveries.append(_discover_claude_installations_v1)
    if include_codex:
        discoveries.append(_discover_codex_installations_v1)
    if include_ollama:
        discoveries.append(_discover_ollama_installations_v1)
    return tuple(discoveries)


def _read_process_locations_v1(
    *, include_claude: bool, include_codex: bool, include_ollama: bool
) -> LiveProcessLocationsV1:
    observed_at = datetime.now(UTC)
    deadline_at = observed_at + timedelta(seconds=3)
    deadline_monotonic = time.monotonic() + 3.0
    discoveries = _requested_provider_discoveries_v1(
        include_claude=include_claude,
        include_codex=include_codex,
        include_ollama=include_ollama,
    )
    if not discoveries:
        return LiveProcessLocationsV1(
            (),
            QueryAvailabilityV1(
                "unavailable", "process_source_unavailable", observed_at
            ),
            None,
            False,
        )

    executor = ThreadPoolExecutor(
        max_workers=len(discoveries),
        thread_name_prefix="agentmonitor-process-source",
    )
    pending: dict[Future[_ProviderDiscoveryResultV1], int] = {}
    try:
        pending = {
            executor.submit(discovery): index
            for index, discovery in enumerate(discoveries)
        }
        items: list[LiveProcessLocationV1] = []
        usable = False
        provider_unavailable = False
        truncated = False
        while pending and len(items) < 512:
            remaining = deadline_monotonic - time.monotonic()
            if remaining <= 0:
                truncated = True
                break
            completed, _ = wait(
                pending,
                timeout=remaining,
                return_when=FIRST_COMPLETED,
            )
            if not completed:
                truncated = True
                break
            for future in sorted(completed, key=pending.__getitem__):
                pending.pop(future)
                try:
                    discovery = future.result()
                except (OSError, RuntimeError, ValueError):
                    discovery = _ProviderDiscoveryResultV1("unavailable", (), False)
                provider_unavailable = provider_unavailable or discovery.state == "unavailable"
                installations, discovery_truncated = _merge_provider_discoveries_v1(
                    (discovery,)
                )
                truncated = truncated or discovery_truncated
                for installation in installations:
                    if time.monotonic() >= deadline_monotonic:
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
                            expected_file_identity=(
                                installation.expected_file_identity
                            ),
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
                                executable_identity=(installation.executable_identity),
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
        if pending:
            truncated = True
        versions = {item.provider_version for item in items if item.provider_version}
        state, reason = _discovery_availability_v1(
            usable=usable, provider_unavailable=provider_unavailable
        )
        return LiveProcessLocationsV1(
            tuple(items),
            QueryAvailabilityV1(
                state,
                reason,
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
    finally:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)


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
