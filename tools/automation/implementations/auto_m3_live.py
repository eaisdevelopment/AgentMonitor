"""Run the populated V1-M3 browser against the owner-controlled local stack."""

from __future__ import annotations

import json
import os
import select
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[3]
BACKEND_PYTHON = ROOT / "backend/.venv/bin/python"
NODE_SCENARIO = ROOT / "frontend/tests/browser/p02/populated_monitoring_dashboard.mjs"
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (  # noqa: E402
    DatabaseRefV1,
    SqlitePolicyError,
    checkpoint_sqlite_database,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (  # noqa: E402
    RegistryRepositoryErrorV1,
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1  # noqa: E402
from agentmonitor.modules.registry.application.accounts import (  # noqa: E402
    ListAccountsV1,
)


def _blocked(code: str) -> int:
    print(f"M3 LIVE: BLOCKED — {code}")
    return 3


def _failed(code: str) -> int:
    print(f"M3 LIVE: FAILED — {code}")
    return 1


def _owner_target() -> tuple[Path, Path, OpaqueIdV1] | None:
    raw_root = os.environ.get("AGENTMONITOR_M3_DATA_ROOT", "")
    raw_account = os.environ.get("AGENTMONITOR_M3_ACCOUNT_ID", "")
    try:
        data_root = (
            Path(raw_root)
            if raw_root
            else Path.home() / ".local" / "share" / "agentmonitor"
        )
        reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
        reference.validate()
        config = data_root / "service.env"
        info = config.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return None
        if os.name == "posix" and (
            info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600
        ):
            return None
        if raw_account:
            account_id = OpaqueIdV1(raw_account)
        else:
            accounts = tuple(
                account
                for account in ListAccountsV1(SqliteRegistryRepositoryV1(reference))(
                    "claude"
                )
                if account.lifecycle == "active"
                and account.identity_state == "owner_confirmed"
            )
            if len(accounts) != 1:
                return None
            account_id = accounts[0].account_id
    except (
        FileNotFoundError,
        OSError,
        TypeError,
        ValueError,
        RegistryRepositoryErrorV1,
        SqlitePolicyError,
    ):
        return None
    return data_root, config, account_id


def _owner_env_value(key: str) -> str | None:
    """Read one explicitly named owner secret without printing or persisting it."""
    supplied = os.environ.get(key, "").strip()
    if supplied:
        return supplied
    env_path = ROOT / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith(f"{key}="):
                continue
            value = line.partition("=")[2].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return value or None
    except (OSError, UnicodeError):
        return None
    return None


def _credential_from_owner() -> str | None:
    """Read the owner password from the explicit local secret or one prompt."""
    configured = _owner_env_value("AGENTMONITOR_DASHBOARD_PASSWORD")
    if configured:
        return configured
    supplied = ""
    try:
        readable, _, _ = select.select([sys.stdin], [], [], 0)
        if readable:
            supplied = sys.stdin.read(4097)
    except (OSError, ValueError):
        supplied = ""
    if supplied:
        if len(supplied) > 4096:
            return None
        return supplied.removesuffix("\n")

    zenity = which("zenity")
    if zenity is None or os.name != "posix":
        return None
    environment = os.environ.copy()
    environment.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    environment.setdefault("WAYLAND_DISPLAY", "wayland-0")
    environment.setdefault(
        "DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{os.getuid()}/bus"
    )
    prompt = subprocess.run(
        [
            zenity,
            "--password",
            "--title=AgentMonitor M3 live browser acceptance",
            "--text=Enter the AgentMonitor dashboard password",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    if prompt.returncode != 0 or not prompt.stdout:
        return None
    return prompt.stdout.removesuffix("\n")


def _wait_for_origin(process: subprocess.Popen[str]) -> str | None:
    if process.stdout is None:
        return None
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and process.poll() is None:
        readable, _, _ = select.select([process.stdout], [], [], 0.1)
        if not readable:
            continue
        line = process.stdout.readline()
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        origin = event.get("origin")
        if (
            event.get("event") == "ready"
            and isinstance(origin, str)
            and origin.startswith("http://127.0.0.1:")
        ):
            return origin
    return None


def _stop_server(process: subprocess.Popen[str]) -> bool:
    if process.poll() is not None:
        return process.returncode == 0
    process.send_signal(signal.SIGTERM)
    try:
        return process.wait(timeout=10) == 0
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        return False


def main() -> int:
    target = _owner_target()
    if target is None:
        return _blocked("owner_target_unavailable")
    data_root, config, account_id = target
    if not BACKEND_PYTHON.is_file() or not NODE_SCENARIO.is_file():
        return _blocked("installed_test_toolchain_unavailable")
    credential = _credential_from_owner()
    if credential is None or not credential:
        return _blocked("owner_credential_unavailable")

    reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    try:
        checkpoint_sqlite_database(reference)
    except SqlitePolicyError:
        return _failed("database_checkpoint_failed")
    build = subprocess.run(
        ["npm", "--prefix", "frontend", "run", "build"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=120,
    )
    if build.returncode != 0:
        return _failed("production_build_failed")

    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "PYTHONPATH": str(ROOT / "backend/src"),
    }
    server = subprocess.Popen(
        [
            str(BACKEND_PYTHON),
            "-m",
            "agentmonitor.composition.bootstrap",
            "--config",
            str(config),
            "--data-root",
            str(data_root),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--authenticated-dashboard",
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    result = 1
    try:
        origin = _wait_for_origin(server)
        if origin is None:
            return _failed("dashboard_not_ready")
        browser = subprocess.run(
            ["node", str(NODE_SCENARIO), origin, account_id.value],
            input=credential,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=240,
        )
        credential = ""
        if browser.returncode != 0:
            message = (browser.stdout + browser.stderr).strip()
            if message:
                print(message)
            return _failed("populated_browser_failed")
        print(browser.stdout.strip())
        result = 0
    except subprocess.TimeoutExpired:
        return _failed("live_boundary_timeout")
    finally:
        credential = ""
        stopped = _stop_server(server)
        try:
            checkpoint_sqlite_database(reference)
        except SqlitePolicyError:
            stopped = False
        if not stopped:
            result = 1
    if result != 0:
        return _failed("dashboard_shutdown_or_checkpoint_failed")
    print("M3 LIVE: PASSED — real populated authenticated Claude dashboard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
