"""Owned authentication support against real filesystem, Linux, and Claude."""

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.claude.authentication import owned_process
from agentmonitor.adapters.providers.claude.authentication.browser import (
    create_managed_browser_opener_v1,
)
from agentmonitor.adapters.providers.claude.authentication.identity import (
    claude_identity_environment_v1,
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.claude.subscription.source import (
    ClaudeUsageSourceFailure,
    collect_usage_once,
)


def test_fresh_managed_quota_source_requires_auth_without_terminal_setup(
    tmp_path: Path,
) -> None:
    """Real unauthenticated Claude must report auth, without theme interaction."""
    installation = discover_default_installation()
    before = read_default_profile_identity_v1(installation)
    assert before is not None
    root = tmp_path / "fresh-quota-profile"
    root.mkdir(mode=0o700)
    result = collect_usage_once(
        installation.executable_for_adapter,
        deadline_ms=14_000,
        managed_profile_root=root,
    )
    assert isinstance(result, ClaudeUsageSourceFailure)
    assert result.code == "claude_reauthentication_required", result.code
    after = read_default_profile_identity_v1(installation)
    assert after is not None and after.fingerprint == before.fingerprint


def test_browser_opener_never_follows_an_existing_leaf_symlink(tmp_path: Path) -> None:
    directory = tmp_path / "signin"
    directory.mkdir(mode=0o700)
    target = tmp_path / "owned-file"
    target.write_text("")
    target.chmod(0o600)
    (directory / "open-sign-in").symlink_to(target)
    with pytest.raises((FileExistsError, ValueError)):
        create_managed_browser_opener_v1(directory)
    assert target.read_bytes() == b""
    assert target.stat().st_mode & 0o777 == 0o600


def test_service_death_ends_only_its_native_claude_child(tmp_path: Path) -> None:
    """Actual Claude first-run waits without input; no auth or content is read."""
    installation = discover_default_installation()
    before = read_default_profile_identity_v1(installation)
    assert before is not None
    root = tmp_path / "native-profile"
    root.mkdir(mode=0o700)
    guard = Path(owned_process.__file__)
    script = """import os,pty,subprocess,sys,time
master,slave=pty.openpty()
process=subprocess.Popen(["/usr/bin/python3","-I",sys.argv[1],sys.argv[2],"--ax-screen-reader","--safe-mode","--restricted","--setting-sources","user","--strict-mcp-config","--no-chrome","--permission-mode","dontAsk"],stdin=slave,stdout=slave,stderr=slave,cwd=sys.argv[3],start_new_session=True)
os.close(slave)
print(process.pid,flush=True)
time.sleep(45)
"""
    parent = subprocess.Popen(
        [
            "/usr/bin/python3",
            "-I",
            "-c",
            script,
            str(guard),
            str(installation.executable_for_adapter),
            str(root),
        ],
        cwd=root,
        env=claude_identity_environment_v1(root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    child: int | None = None
    child_start: str | None = None
    try:
        assert parent.stdout is not None
        text = parent.stdout.readline().strip()
        assert text.isdecimal()
        child = int(text)
        child_stat = Path("/proc", str(child), "stat")
        deadline = time.monotonic() + 5
        while True:
            assert child_stat.exists(), "native child exited before lifetime check"
            fields = child_stat.read_text().rsplit(") ", 1)[1].split()
            child_start = fields[19]
            executable = Path("/proc", str(child), "exe")
            if executable.resolve() == installation.executable_for_adapter.resolve():
                break
            assert time.monotonic() < deadline, "native child never started"
            time.sleep(0.02)
        parent.kill()
        parent.wait(timeout=3)
        deadline = time.monotonic() + 3
        while child_stat.exists():
            fields = child_stat.read_text().rsplit(") ", 1)[1].split()
            if fields[0] == "Z" or fields[19] != child_start:
                break
            assert time.monotonic() < deadline, (
                "native auth child survived service death"
            )
            time.sleep(0.02)
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=3)
        if parent.stdout is not None:
            parent.stdout.close()
        if child is not None and child_start is not None:
            child_stat = Path("/proc", str(child), "stat")
            if child_stat.exists():
                fields = child_stat.read_text().rsplit(") ", 1)[1].split()
                if fields[0] != "Z" and fields[19] == child_start:
                    os.kill(child, signal.SIGTERM)
    after = read_default_profile_identity_v1(installation)
    assert after is not None and after.fingerprint == before.fingerprint
