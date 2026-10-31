"""Real isolated Codex app-server identity boundary for M5-CDX-SOURCE-001."""

from __future__ import annotations

import os
import pwd
import subprocess
import sys
from pathlib import Path

from agentmonitor.adapters.providers.codex.authentication.identity import (
    read_managed_profile_identity_v1,
)
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)

_STRACE = Path("/usr/bin/strace")


def test_empty_private_managed_root_reports_auth_required(tmp_path: Path) -> None:
    """A real empty managed root is read without consulting a default profile."""
    installation = discover_default_installation()
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir(mode=0o700)
    managed_root = profiles_root / "managed-codex"
    managed_root.mkdir(mode=0o700)
    root_mtime_before = managed_root.stat().st_mtime_ns

    assert (
        read_managed_profile_identity_v1(
            installation,
            managed_profiles_root=profiles_root,
            managed_profile_root=managed_root,
        )
        is None
    )
    assert managed_root.stat().st_mode & 0o077 == 0
    assert sum(1 for _ in managed_root.rglob("*")) == 0
    assert managed_root.stat().st_mtime_ns == root_mtime_before


def test_production_managed_root_validation_never_accesses_default_profile(
    tmp_path: Path,
) -> None:
    """M5-CDX-SOURCE-010: path protection needs no default-profile metadata."""

    assert _STRACE.is_file() and not _STRACE.is_symlink()
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir(mode=0o700)
    managed_root = profiles_root / "managed-codex"
    managed_root.mkdir(mode=0o700)
    trace = tmp_path / "managed-root.trace"
    source_root = Path(__file__).resolve().parents[5] / "src"
    default_profile = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".codex"
    script = (
        "import sys; from pathlib import Path; "
        "from agentmonitor.adapters.providers.codex.transport import "
        "validate_codex_managed_profile_root_v1; "
        "validate_codex_managed_profile_root_v1("
        "managed_profiles_root=Path(sys.argv[1]), "
        "managed_profile_root=Path(sys.argv[2]))"
    )
    result = subprocess.run(
        [
            str(_STRACE),
            "-f",
            "-qq",
            "-s",
            "4096",
            "-e",
            "trace=%file",
            "-o",
            str(trace),
            sys.executable,
            "-c",
            script,
            str(profiles_root),
            str(managed_root),
        ],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={
            "CODEX_HOME": os.fspath(default_profile),
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(source_root),
        },
        timeout=10,
    )
    assert result.returncode == 0
    assert os.fspath(default_profile) not in trace.read_text(encoding="utf-8")
