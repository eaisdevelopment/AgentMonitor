"""Real Git checkout support shared by M5 boundary tests."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def attached_real_checkout_v1() -> Iterator[Path]:
    """Yield a clean, owner-private Git checkout with an attached HEAD."""

    root = Path.home() / f".agentmonitor-m5-attached-{uuid.uuid4().hex}"
    root.mkdir(mode=0o700)
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    try:
        (root / "tracked.txt").write_text("attached boundary\n", encoding="utf-8")
        commands = (
            ("init", "-q"),
            ("add", "tracked.txt"),
            (
                "-c",
                "user.name=AgentMonitor test",
                "-c",
                "user.email=agentmonitor-test@invalid",
                "commit",
                "-q",
                "-m",
                "attached boundary",
            ),
        )
        for command in commands:
            result = subprocess.run(
                ("/usr/bin/git", *command),
                cwd=root,
                env=environment,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            assert result.returncode == 0, result.stderr
        yield root
    finally:
        shutil.rmtree(root)


def git_status_v1(root: Path) -> str:
    """Read the exact porcelain status without optional Git locks."""

    result = subprocess.run(
        ("/usr/bin/git", "status", "--porcelain=v1", "--untracked-files=all"),
        cwd=root,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "GIT_OPTIONAL_LOCKS": "0",
        },
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout
