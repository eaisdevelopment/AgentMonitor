"""M3-FIX-004 owner fingerprint binding through a real controlling TTY."""

import os
import pty
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)

MODULE = "agentmonitor.composition.claude_otel_identity_binding"


def _environment() -> dict[str, str]:
    return {"PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}


def _run_declined_binding(root: Path) -> tuple[int, bytes]:
    child, master = pty.fork()
    if child == 0:
        os.execve(
            sys.executable,
            [
                sys.executable,
                "-m",
                MODULE,
                "--data-root",
                str(root),
                "--account-id",
                "owner-selected-account",
                "--account-version",
                "1",
            ],
            _environment(),
        )
    captured = bytearray()
    status: int | None = None
    confirmation_sent = False
    deadline = time.monotonic() + 8
    try:
        while time.monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.1)
            if readable:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    chunk = b""
                captured.extend(chunk)
                if len(captured) > 8192:
                    break
                if (
                    not confirmation_sent
                    and b"Type CONFIRM to bind the next authenticated Claude identity:"
                    in captured
                ):
                    os.write(master, b"DECLINE\n")
                    confirmation_sent = True
            completed, result = os.waitpid(child, os.WNOHANG)
            if completed:
                status = result
                break
        if status is None:
            os.kill(child, signal.SIGTERM)
            _, status = os.waitpid(child, 0)
    finally:
        os.close(master)
    return os.waitstatus_to_exitcode(status), bytes(captured)


def test_real_tty_decline_leaves_migrated_registry_unchanged(tmp_path: Path) -> None:
    """M02-DB-021: no fingerprint binding occurs without explicit confirmation."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    before = reference._path.read_bytes()

    status, output = _run_declined_binding(tmp_path)

    assert status == 2
    assert b"Type CONFIRM to bind the next authenticated Claude identity:" in output
    assert b"owner_confirmation_required" in output
    assert b"subject_fingerprint" not in output
    assert reference._path.read_bytes() == before


def test_binding_operator_rejects_redirected_or_fingerprint_arguments(
    tmp_path: Path,
) -> None:
    """NFR-SEC-001: identity material has no argv or redirected-input path."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    before = reference._path.read_bytes()
    command = [
        sys.executable,
        "-m",
        MODULE,
        "--data-root",
        str(tmp_path),
        "--account-id",
        "owner-selected-account",
        "--account-version",
        "1",
    ]

    redirected = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=_environment(),
        timeout=5,
        check=False,
    )
    fingerprint_argument = subprocess.run(
        [*command, "--fingerprint", "forbidden"],
        capture_output=True,
        text=True,
        env=_environment(),
        timeout=5,
        check=False,
    )

    assert redirected.returncode == 2
    assert redirected.stdout == "controlling_tty_required\n"
    assert redirected.stderr == ""
    assert fingerprint_argument.returncode == 2
    assert fingerprint_argument.stdout == "invalid_operator_arguments\n"
    assert fingerprint_argument.stderr == ""
    assert reference._path.read_bytes() == before
