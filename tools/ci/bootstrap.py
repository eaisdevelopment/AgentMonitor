"""Bootstrap M1's exact admitted tools in a clean, secret-free Linux CI checkout."""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = ROOT / ".ci-tools"
NODE_VERSION = "22.23.2"
UV_VERSION = "0.11.16"
NODE_ARCHIVE = f"node-v{NODE_VERSION}-linux-x64.tar.xz"
UV_ARCHIVE = "uv-x86_64-unknown-linux-gnu.tar.gz"
NODE_SHA256 = "d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307"
UV_SHA256 = "74947fe2c03315cf07e82ab3acc703eddef01aba4d5232a98e4c6825ec116131"
NODE_ROOT = TOOL_ROOT / f"node-v{NODE_VERSION}-linux-x64"
UV_ROOT = TOOL_ROOT / "uv-x86_64-unknown-linux-gnu"


def fail(code: str) -> NoReturn:
    print(f"CI-BOOTSTRAP: FAILED — {code}")
    raise SystemExit(1)


def download(url: str, destination: Path, expected_sha256: str) -> None:
    """Download one upstream release archive and enforce its recorded digest."""
    digest = hashlib.sha256()
    total = 0
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "AgentMonitor-M1-CI"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            with destination.open("xb") as stream:
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > 100 * 1024 * 1024:
                        fail("tool_archive_size_limit")
                    digest.update(block)
                    stream.write(block)
    except (OSError, urllib.error.URLError, TimeoutError):
        fail("tool_archive_download_unavailable")
    if digest.hexdigest() != expected_sha256:
        fail("tool_archive_digest_mismatch")


def extract(archive_path: Path, destination: Path, expected_prefix: str) -> None:
    """Extract only the digest-verified upstream archive under one known root."""
    try:
        with tarfile.open(archive_path) as archive:
            members = archive.getmembers()
            if not members or any(
                not member.name.startswith(expected_prefix + "/")
                and member.name != expected_prefix
                for member in members
            ):
                fail("tool_archive_layout_invalid")
            archive.extractall(destination, filter="data")
    except (OSError, tarfile.TarError, ValueError):
        fail("tool_archive_extract_failed")


def run(command: list[str], *, environment: dict[str, str]) -> None:
    if subprocess.run(command, cwd=ROOT, env=environment, check=False).returncode:
        fail("locked_install_or_toolchain_check_failed")


def main() -> int:
    if (sys.version_info.major, sys.version_info.minor, sys.version_info.micro) != (
        3,
        12,
        3,
    ):
        fail("python_version_not_3_12_3")
    if sys.platform != "linux" or platform.machine() != "x86_64":
        fail("ci_platform_not_linux_x86_64")
    if (ROOT / ".env").exists() or (ROOT / ".env").is_symlink():
        fail("owner_env_must_not_enter_ci")
    if TOOL_ROOT.exists():
        fail("ci_tool_root_already_exists")
    old_umask = os.umask(0o077)
    try:
        TOOL_ROOT.mkdir(mode=0o700)
        with tempfile.TemporaryDirectory(prefix="download-", dir=TOOL_ROOT) as raw:
            scratch = Path(raw)
            node_archive = scratch / NODE_ARCHIVE
            uv_archive = scratch / UV_ARCHIVE
            download(
                f"https://nodejs.org/dist/v{NODE_VERSION}/{NODE_ARCHIVE}",
                node_archive,
                NODE_SHA256,
            )
            download(
                f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/{UV_ARCHIVE}",
                uv_archive,
                UV_SHA256,
            )
            extract(node_archive, TOOL_ROOT, NODE_ROOT.name)
            extract(uv_archive, TOOL_ROOT, UV_ROOT.name)
        node = NODE_ROOT / "bin/node"
        npm = NODE_ROOT / "bin/npm"
        uv = UV_ROOT / "uv"
        if not all(path.is_file() for path in (node, npm, uv)):
            fail("tool_archive_required_binary_missing")
        environment = {
            "PATH": f"{node.parent}:{uv.parent}:{os.defpath}",
            "UV_CACHE_DIR": str(TOOL_ROOT / "uv-cache"),
            "NPM_CONFIG_CACHE": str(TOOL_ROOT / "npm-cache"),
            "NPM_CONFIG_UPDATE_NOTIFIER": "false",
        }
        run(
            [
                sys.executable,
                "tooling/foundation/check_toolchain.py",
                "--root",
                ".",
                "--node",
                str(node),
                "--npm",
                str(npm),
                "--uv",
                str(uv),
            ],
            environment=environment,
        )
        run(
            [str(uv), "lock", "--check", "--directory", "backend"],
            environment=environment,
        )
        run(
            [str(uv), "sync", "--frozen", "--no-build", "--directory", "backend"],
            environment=environment,
        )
        run(
            [
                str(npm),
                "ci",
                "--prefix",
                "frontend",
                "--ignore-scripts",
                "--no-audit",
                "--no-fund",
            ],
            environment=environment,
        )
        print("CI-BOOTSTRAP: PASSED exact toolchain and frozen project installs")
        print("CI-BOOTSTRAP: M0 owner-local state and credentials NOT COPIED")
    finally:
        os.umask(old_umask)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
