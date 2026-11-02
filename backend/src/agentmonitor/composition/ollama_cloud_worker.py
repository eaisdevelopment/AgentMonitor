"""Unwired transient-unit supervisor for optional Ollama cloud work."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import os
import shlex
import stat
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.providers.ollama.cloud_balance.keyring_command import (
    secret_tool_environment,
)
from agentmonitor.composition.ollama_cloud_collection import (
    OllamaCloudCollectionV1,
    require_cloud_manifest,
    require_source_admitted,
)

_PREFIX = "agentmonitor-cloud-worker-"
_SYSTEMCTL = "/usr/bin/systemctl"
_SYSTEMD_RUN = "/usr/bin/systemd-run"
_COMMAND_TIMEOUT_SECONDS = 8


class OllamaCloudWorkerSupervisorV1:
    """Supervise a uniquely named systemd user unit, never an agent process."""

    def __init__(self, data_root: Path) -> None:
        if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
            raise ValueError("ollama_cloud_data_root_invalid")
        self._data_root = data_root
        self._quarantined = False
        self._running = False
        self.last_unit = ""
        self._lock_fd: int | None = None

    @staticmethod
    async def _command(*args: str, pass_fds: tuple[int, ...] = ()) -> tuple[int, str]:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            pass_fds=pass_fds,
        )
        try:
            output, _ = await asyncio.wait_for(
                process.communicate(), _COMMAND_TIMEOUT_SECONDS
            )
        except (TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                process.kill()
                try:
                    await asyncio.wait_for(process.wait(), 2)
                except TimeoutError:
                    pass
            raise
        if len(output) > 16384:
            raise ValueError("ollama_cloud_unit_output_invalid")
        return process.returncode or 0, output.decode("utf-8", "strict")

    async def _show(self, unit: str) -> dict[str, str]:
        _, output = await self._command(
            _SYSTEMCTL,
            "--user",
            "show",
            unit,
            "--property=Id,Description,Transient,FragmentPath,InvocationID,KillMode,ActiveState,ControlGroup,ExecMainStatus,ExecStart,RuntimeMaxUSec,TimeoutStopUSec,RemainAfterExit",
            "--no-pager",
        )
        pairs = [line.partition("=") for line in output.splitlines() if "=" in line]
        result = {key: value for key, _, value in pairs}
        if len(result) != len(pairs):
            raise ValueError("ollama_cloud_unit_identity_invalid")
        return result

    def _identity(self, unit: str, description: str, properties: dict[str, str]) -> str:
        invocation = properties.get("InvocationID", "")
        fragment = f"/run/user/{os.getuid()}/systemd/transient/{unit}"
        executable = str(Path(sys.executable))
        exec_start = properties.get("ExecStart", "")
        argv = exec_start.partition(" ; argv[]=")[2].partition(" ; ignore_errors=")[0]
        try:
            actual_argv = shlex.split(argv)
        except ValueError:
            actual_argv = []
        expected_argv = [
            executable,
            "-m",
            "agentmonitor.composition.ollama_cloud_worker",
            "--data-root",
            str(self._data_root),
        ]
        if (
            properties.get("Id") != unit
            or properties.get("Description") != description
            or properties.get("Transient") != "yes"
            or properties.get("FragmentPath") != fragment
            or properties.get("KillMode") != "control-group"
            or properties.get("RuntimeMaxUSec") != "30s"
            or properties.get("TimeoutStopUSec") != "3s"
            or properties.get("RemainAfterExit") != "yes"
            or not exec_start.startswith("{ path=" + executable + " ;")
            or actual_argv != expected_argv
            or len(invocation) != 32
            or any(c not in "0123456789abcdef" for c in invocation)
        ):
            raise ValueError("ollama_cloud_unit_identity_invalid")
        return invocation

    async def _stop_owned(self, unit: str, description: str, invocation: str) -> bool:
        try:
            before = await self._show(unit)
            if self._identity(unit, description, before) != invocation:
                return False
            code, _ = await self._command(_SYSTEMCTL, "--user", "stop", unit)
            if code:
                return False
            after = await self._show(unit)
            if (
                after.get("Id") == unit
                and after.get("FragmentPath")
                and self._identity(unit, description, after) != invocation
            ):
                return False
            if after.get("Id") == unit and after.get("ActiveState") not in {
                "inactive",
                "failed",
            }:
                return False
            if after.get("ControlGroup"):
                return False
            await self._command(_SYSTEMCTL, "--user", "reset-failed", unit)
            final = await self._show(unit)
            return final.get("FragmentPath", "") == "" and not final.get("ControlGroup")
        except (OSError, ValueError, TimeoutError):
            return False

    @staticmethod
    async def _finish_cleanup(task: asyncio.Task):
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
        return task.result()

    def _acquire_lock(self) -> int:
        directory = os.open(
            self._data_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        try:
            root = os.fstat(directory)
            if root.st_uid != os.getuid() or stat.S_IMODE(root.st_mode) != 0o700:
                raise ValueError("ollama_cloud_root_unsafe")
            descriptor = os.open(
                ".ollama-cloud-worker.lock",
                os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=directory,
            )
            try:
                os.fsync(directory)
            except OSError:
                os.close(descriptor)
                raise
        finally:
            os.close(directory)
        try:
            state = os.fstat(descriptor)
            if (
                not stat.S_ISREG(state.st_mode)
                or state.st_uid != os.getuid()
                or state.st_nlink != 1
                or stat.S_IMODE(state.st_mode) != 0o600
                or state.st_size > 128
            ):
                raise ValueError("ollama_cloud_lock_unsafe")
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.read(descriptor, 129):
                raise ValueError("ollama_cloud_previous_start_unresolved")
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def _mark_start(self, unit: str) -> None:
        if self._lock_fd is None:
            raise ValueError("ollama_cloud_lock_missing")
        data = (unit + "\n").encode("ascii")
        if os.write(self._lock_fd, data) != len(data):
            raise ValueError("ollama_cloud_marker_write_failed")
        os.fsync(self._lock_fd)

    def _clear_marker(self) -> None:
        if self._lock_fd is None:
            raise ValueError("ollama_cloud_lock_missing")
        os.ftruncate(self._lock_fd, 0)
        os.fsync(self._lock_fd)

    async def run_once(self) -> str:
        if self._quarantined:
            return "quarantined"
        if self._running:
            return "worker_busy"
        self._running = True
        try:
            try:
                self._lock_fd = self._acquire_lock()
            except (OSError, ValueError):
                self._quarantined = True
                return "quarantined"
            return await self._run_transient()
        except asyncio.CancelledError:
            self._quarantined = True
            raise
        finally:
            if self._lock_fd is not None:
                os.close(self._lock_fd)
                self._lock_fd = None
            self._running = False

    async def _run_transient(self) -> str:
        code, existing = await self._command(
            _SYSTEMCTL,
            "--user",
            "list-units",
            "--all",
            "--plain",
            "--no-legend",
            _PREFIX + "*.service",
        )
        if code or existing.strip():
            self._quarantined = True
            return "quarantined"
        token = uuid.uuid4().hex
        unit = _PREFIX + token + ".service"
        self.last_unit = unit
        description = "AgentMonitor cloud worker " + token
        environment = secret_tool_environment(os.environ)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
        command = [
            _SYSTEMD_RUN,
            "--user",
            "--quiet",
            "--unit=" + unit,
            "--description=" + description,
            "--property=KillMode=control-group",
            "--property=RuntimeMaxSec=30s",
            "--property=TimeoutStopSec=3s",
            "--property=RemainAfterExit=yes",
        ]
        command += [
            "--setenv=" + key + "=" + value for key, value in environment.items()
        ]
        command += [
            sys.executable,
            "-m",
            "agentmonitor.composition.ollama_cloud_worker",
            "--data-root",
            str(self._data_root),
        ]
        self._mark_start(unit)
        if self._lock_fd is None:
            raise ValueError("ollama_cloud_lock_missing")
        start = asyncio.create_task(self._command(*command, pass_fds=(self._lock_fd,)))
        cancelled = False
        try:
            try:
                code, _ = await asyncio.shield(start)
            except asyncio.CancelledError:
                cancelled = True
                self._quarantined = True
                code, _ = await self._finish_cleanup(start)
            if code:
                self._quarantined = True
                return "quarantined"
            properties = await self._show(unit)
            invocation = self._identity(unit, description, properties)
            if cancelled:
                await self._finish_cleanup(
                    asyncio.create_task(self._stop_owned(unit, description, invocation))
                )
                raise asyncio.CancelledError
            for _ in range(300):
                properties = await self._show(unit)
                if self._identity(unit, description, properties) != invocation:
                    raise ValueError("ollama_cloud_unit_identity_changed")
                if properties.get("ActiveState") in {"failed", "inactive"} or (
                    properties.get("ActiveState") == "active"
                    and not properties.get("ControlGroup")
                ):
                    status = properties.get("ExecMainStatus")
                    clean = await self._stop_owned(unit, description, invocation)
                    if not clean:
                        self._quarantined = True
                        return "quarantined"
                    self._clear_marker()
                    return (
                        "not_admitted"
                        if status == "3"
                        else "completed"
                        if status == "0"
                        else "unavailable"
                    )
                await asyncio.sleep(0.1)
            self._quarantined = True
            await self._stop_owned(unit, description, invocation)
            return "worker_timeout"
        except asyncio.CancelledError:
            self._quarantined = True
            try:
                properties = await self._finish_cleanup(
                    asyncio.create_task(self._show(unit))
                )
                invocation = self._identity(unit, description, properties)
                await self._finish_cleanup(
                    asyncio.create_task(self._stop_owned(unit, description, invocation))
                )
            except (OSError, ValueError, RuntimeError, TimeoutError):
                pass
            raise
        except (OSError, ValueError, RuntimeError, TimeoutError):
            self._quarantined = True
            return "quarantined"

    async def run(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception:  # noqa: BLE001 - optional lane, no provider details.
                self._quarantined = True
            await asyncio.sleep(60)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args()
    if not args.data_root.is_absolute() or args.data_root in {Path("/"), Path.home()}:
        return 2
    try:
        require_source_admitted()
        require_cloud_manifest()
    except ValueError:
        return 3
    try:
        collector = OllamaCloudCollectionV1(
            DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root)
        )
        now = datetime.now(UTC)
        rate, _, _ = collector.recover_journals(
            as_of=now,
            owner_stale_before=now - timedelta(minutes=2),
            recovery_lease_expires_at=now + timedelta(seconds=45),
        )
        if rate not in {
            "outcome_unknown",
            "legacy_unresolved",
            "owner_active_or_unverified",
        }:
            collector.tick()
        return 0
    except Exception:  # noqa: BLE001 - the process returns only a closed status.
        return 1


if __name__ == "__main__":
    sys.exit(main())
