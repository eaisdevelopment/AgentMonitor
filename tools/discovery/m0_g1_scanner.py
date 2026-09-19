"""Pinned, output-discarding local E1 scanner verification."""

from __future__ import annotations

import hashlib
import re
import stat
import subprocess
import tempfile
from pathlib import Path


EXPECTED_SCANNER_VERSION = "8.30.0"
EXPECTED_SCANNER_SHA256 = (
    "8b6fd684fcd5b4ebe39b68abb072ce59e1063ce7ed4abd556157697845f1f088"
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_e1_scanner(repository_root: Path) -> list[str]:
    """Verify the pinned scanner on one repository-safe, sanitized artifact."""

    scanner = repository_root / ".venv-m0-g1/bin/gitleaks"
    target = (
        repository_root
        / "docs/plans/discovery/m0-g1-contract-test-evidence.md"
    )
    strace = Path("/usr/bin/strace")
    try:
        scanner_metadata = scanner.lstat()
        target_metadata = target.lstat()
    except OSError:
        return ["scanner binary or sanitized verification target is unavailable"]
    if not stat.S_ISREG(scanner_metadata.st_mode) or scanner.is_symlink():
        return ["scanner binary must be a regular non-symlink file"]
    if _file_sha256(scanner) != EXPECTED_SCANNER_SHA256:
        return ["scanner binary digest does not match admission"]
    if not stat.S_ISREG(target_metadata.st_mode) or target.is_symlink():
        return ["scanner target must be a regular non-symlink file"]
    if target_metadata.st_size > 1024 * 1024:
        return ["scanner target exceeds the one-megabyte verification limit"]
    if (target.parent / ".gitleaks.toml").exists():
        return ["target-local Gitleaks configuration is prohibited"]
    if not strace.is_file():
        return ["network-call verification tool is unavailable"]

    safe_environment = {"PATH": "/usr/bin:/bin"}
    try:
        version_result = subprocess.run(
            [str(scanner), "version"],
            cwd=repository_root,
            env=safe_environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ["scanner version verification failed"]
    if (
        version_result.returncode != 0
        or version_result.stdout.strip() != EXPECTED_SCANNER_VERSION
    ):
        return ["scanner version does not match admission"]

    before_identity = (
        target_metadata.st_dev,
        target_metadata.st_ino,
        target_metadata.st_size,
        target_metadata.st_mtime_ns,
        _file_sha256(target),
    )
    with tempfile.TemporaryDirectory(prefix="agentmonitor-g1-scanner-") as raw_dir:
        trace_path = Path(raw_dir) / "network.trace"
        command = [
            str(strace),
            "-f",
            "-e",
            "trace=network",
            "-o",
            str(trace_path),
            str(scanner),
            "dir",
            "--no-banner",
            "--no-color",
            "--redact=100",
            "--log-level=error",
            "--max-archive-depth=0",
            "--max-decode-depth=0",
            "--max-target-megabytes=1",
            "--timeout=5",
            "--exit-code=7",
            "--gitleaks-ignore-path=/dev/null",
            str(target),
        ]
        try:
            scan_result = subprocess.run(
                command,
                cwd=raw_dir,
                env=safe_environment,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            trace = trace_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            return ["scanner execution failed or timed out"]
    if scan_result.returncode == 7:
        return ["scanner reported a finding in sanitized G1 evidence"]
    if scan_result.returncode != 0:
        return ["scanner returned an internal error"]
    if re.search(r"\b(?:socket|connect|sendto|recvfrom)\(", trace):
        return ["scanner attempted a network operation"]

    try:
        after_metadata = target.lstat()
        after_identity = (
            after_metadata.st_dev,
            after_metadata.st_ino,
            after_metadata.st_size,
            after_metadata.st_mtime_ns,
            _file_sha256(target),
        )
    except OSError:
        return ["scanner target was unavailable after verification"]
    if before_identity != after_identity:
        return ["scanner target changed during verification"]
    return []
