"""Real provider-neutral live process locations include exact Codex processes."""

from pathlib import Path

from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.composition.linux_process_locations import (
    read_live_process_locations_v1,
)


def test_live_process_locations_include_current_codex_processes() -> None:
    """M5-CDX-RUN-003/004: the shared live view includes Codex without guessing."""
    result = read_live_process_locations_v1()
    codex = tuple(item for item in result.items if item.provider_key == "codex")

    assert result.availability.state == "available"
    assert codex
    assert all(item.snapshot is not None for item in codex)
    assert all(item.provider_version == "0.160.0" for item in codex)
    assert all(item.account_association is None for item in codex)


def _proc_identity(pid: int) -> tuple[int, int] | None:
    """Independently read only the admitted parent/start fields from procfs."""

    try:
        raw = (Path("/proc") / str(pid) / "stat").read_bytes()
    except (FileNotFoundError, ProcessLookupError):
        return None
    assert 1 <= len(raw) <= 16 * 1024
    assert raw.endswith(b"\n")
    close_index = raw.rfind(b")")
    assert close_index > 0
    fields = raw[close_index + 2 :].decode("ascii").split()
    assert len(fields) > 19
    parent_pid = int(fields[1])
    start_time_ticks = int(fields[19])
    assert parent_pid >= 0
    assert start_time_ticks > 0
    return parent_pid, start_time_ticks


def test_live_codex_process_identity_and_hierarchy_match_procfs() -> None:
    """M5-CDX-RUN-005/006: PID/start/executable/parent facts match live procfs."""

    result = read_live_process_locations_v1()
    installation = discover_default_installation()
    expected_executable = installation.executable_for_adapter.resolve(strict=True)
    stable = []
    for item in result.items:
        if item.provider_key != "codex" or item.snapshot is None:
            continue
        identity = _proc_identity(item.identity.pid)
        if identity is None:
            continue
        try:
            executable = (Path("/proc") / str(item.identity.pid) / "exe").resolve(
                strict=True
            )
        except (FileNotFoundError, ProcessLookupError):
            continue
        parent_pid, start_time_ticks = identity
        assert start_time_ticks == item.identity.start_time_ticks
        assert item.snapshot.parent_pid.state == "present"
        assert item.snapshot.parent_pid.value == parent_pid
        assert parent_pid != item.identity.pid
        assert executable.samefile(expected_executable)
        stable.append(item)

    assert stable, "one stable real Codex process is required"
    by_scope_and_pid = {
        (item.identity.platform_scope_id, item.identity.pid): item for item in stable
    }
    for item in stable:
        snapshot = item.snapshot
        assert snapshot is not None
        candidate_parent_pid = snapshot.parent_pid.value
        assert candidate_parent_pid is not None
        parent = by_scope_and_pid.get(
            (item.identity.platform_scope_id, candidate_parent_pid)
        )
        if parent is not None:
            assert parent.identity.start_time_ticks <= item.identity.start_time_ticks
        visited: set[int] = set()
        current = item
        while current.identity.pid not in visited:
            visited.add(current.identity.pid)
            current_snapshot = current.snapshot
            assert current_snapshot is not None
            current_parent_pid = current_snapshot.parent_pid.value
            if current_parent_pid is None:
                break
            next_item = by_scope_and_pid.get(
                (current.identity.platform_scope_id, current_parent_pid)
            )
            if next_item is None:
                break
            current = next_item
        else:
            raise AssertionError("Codex process hierarchy contains a cycle")
