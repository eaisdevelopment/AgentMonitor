"""Real native Claude process discovery independent of quota-version retention."""

from __future__ import annotations

import os
import pwd
from pathlib import Path

import pytest
from agentmonitor.adapters.platform.linux.processes import (
    ApprovedLinuxExecutableSelectorV1,
)
from agentmonitor.adapters.providers.claude.installation import (
    ClaudeInstallationUnavailable,
    discover_default_installation,
    discover_process_installations,
)
from agentmonitor.composition.linux_process_locations import (
    read_live_claude_process_locations_v1,
)


def test_owner_selected_terminal_is_discovered_after_quota_binary_retirement() -> None:
    """M06-ASSOC-06: a real retained-version terminal remains observable."""
    raw_pid = os.environ.get("AGENTMONITOR_TEST_AGENT_PID")
    if raw_pid is None:
        pytest.skip("real owner-selected Claude PID required")
    pid = int(raw_pid)
    process_executable = (Path("/proc") / str(pid) / "exe").resolve(strict=True)
    native_versions = (
        Path(pwd.getpwuid(os.getuid()).pw_dir) / ".local/share/claude/versions"
    )
    assert process_executable.parent == native_versions

    try:
        discover_default_installation()
    except ClaudeInstallationUnavailable:
        pass

    installations, _ = discover_process_installations()

    selected = next(
        item
        for item in installations
        if item.executable_for_adapter == process_executable
    )
    assert selected.provider_version == process_executable.name
    selected_path, selected_identity = selected.executable_for_process_observation()
    assert selected_path == process_executable
    selector = ApprovedLinuxExecutableSelectorV1.from_executable(
        selector_id="linux.proc.claude-process.v1",
        executable_identity="claude",
        provider_key="claude",
        installation_id=selected.installation_ref.value,
        provider_version=selected.provider_version,
        executable=selected_path,
        expected_file_identity=selected_identity,
    )
    assert selector.is_current()
    other = next(
        (
            item
            for item in installations
            if item.executable_for_adapter != selected_path
        ),
        None,
    )
    if other is not None:
        _, other_identity = other.executable_for_process_observation()
        with pytest.raises(ValueError, match="^linux_executable_identity_changed$"):
            ApprovedLinuxExecutableSelectorV1.from_executable(
                selector_id="linux.proc.claude-process.v1",
                executable_identity="claude",
                provider_key="claude",
                installation_id=selected.installation_ref.value,
                provider_version=selected.provider_version,
                executable=selected_path,
                expected_file_identity=other_identity,
            )
    observed = read_live_claude_process_locations_v1()
    assert observed.availability.state == "available"
    assert any(item.identity.pid == pid for item in observed.items)
