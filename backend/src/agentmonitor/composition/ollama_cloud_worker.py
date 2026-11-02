"""Transient-unit supervisor for optional Ollama cloud work."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import os
import select
import shlex
import stat
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypeVar

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.composition.ollama_cloud_collection import (
    OllamaCloudCollectionV1,
    require_probe_authorized,
)
from agentmonitor.composition.ollama_env_store import (
    recover_env_location_if_unused,
    recover_ollama_env_staging,
)

_PREFIX = "agentmonitor-cloud-worker-"
_SYSTEMCTL = "/usr/bin/systemctl"
_SYSTEMD_RUN = "/usr/bin/systemd-run"


def _manager_environment() -> dict[str, str]:
    """Use the local user bus without forwarding a keyring/display environment."""
    runtime = f"/run/user/{os.getuid()}"
    return {
        "PATH": "/usr/bin:/bin",
        "XDG_RUNTIME_DIR": runtime,
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime}/bus",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


_COMMAND_TIMEOUT_SECONDS = 8
_CLEANUP_TIMEOUT_SECONDS = 20
_START_AUTHORITY_TIMEOUT_SECONDS = 8
_START_AUTHORIZATION_REVOKED_EXIT = 5
_T = TypeVar("_T")


def recovery_exit_code(rate_state: str) -> int:
    """Unknown recovery states never report a successful drain."""
    return 0 if rate_state in {"idle", "recovered"} else 4


def _valid_start_token(token: str) -> bool:
    return len(token) == 32 and all(
        character in "0123456789abcdef" for character in token
    )


def _consume_start_authority(token: str) -> bool:
    """Consume one parent-issued start grant before opening any owned state."""
    if not _valid_start_token(token):
        return False
    expected = ("START " + token + "\n").encode("ascii")
    received = bytearray()
    deadline = time.monotonic() + _START_AUTHORITY_TIMEOUT_SECONDS
    while len(received) <= len(expected):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            ready, _, _ = select.select([sys.stdin.fileno()], [], [], remaining)
        except (OSError, ValueError):
            return False
        if not ready:
            return False
        try:
            chunk = os.read(sys.stdin.fileno(), len(expected) + 1 - len(received))
        except OSError:
            return False
        if not chunk:
            return False
        received.extend(chunk)
        if b"\n" in received:
            return bytes(received) == expected
    return False


class OllamaCloudWorkerSupervisorV1:
    """Supervise a uniquely named systemd user unit, never an agent process."""

    def __init__(
        self, data_root: Path, *, credential_env_file: Path | None = None
    ) -> None:
        if not data_root.is_absolute() or data_root in {Path("/"), Path.home()}:
            raise ValueError("ollama_cloud_data_root_invalid")
        self._data_root = data_root
        if credential_env_file is not None and (
            not credential_env_file.is_absolute()
            or credential_env_file.name != ".env"
            or ".." in credential_env_file.parts
        ):
            raise ValueError("ollama_cloud_env_path_invalid")
        self._credential_env_file = credential_env_file
        self._quarantined = False
        self._running = False
        self._lifecycle_running = False
        self.last_unit = ""
        self._lock_fd: int | None = None
        self._root_fd: int | None = None
        self._active_recovery_only = False
        self._recovery_unresolved = False

    def is_available(self) -> bool:
        """Expose quarantine and unresolved-start state without starting work."""
        if (
            self._quarantined
            or self._recovery_unresolved
            or not all(os.access(path, os.X_OK) for path in (_SYSTEMCTL, _SYSTEMD_RUN))
        ):
            return False
        if self._running:
            return True
        root_fd = None
        lock_fd = None
        try:
            manager = os.stat(
                f"/run/user/{os.getuid()}/systemd/private", follow_symlinks=False
            )
            if not stat.S_ISSOCK(manager.st_mode) or manager.st_uid != os.getuid():
                return False
            root_fd = os.open(
                self._data_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            root = os.fstat(root_fd)
            path_root = os.stat(self._data_root, follow_symlinks=False)
            if (
                root.st_uid != os.getuid()
                or stat.S_IMODE(root.st_mode) != 0o700
                or not stat.S_ISDIR(path_root.st_mode)
                or path_root.st_uid != os.getuid()
                or stat.S_IMODE(path_root.st_mode) != 0o700
                or (root.st_dev, root.st_ino) != (path_root.st_dev, path_root.st_ino)
            ):
                return False
            try:
                lock_fd = os.open(
                    ".ollama-cloud-worker.lock",
                    os.O_RDONLY | os.O_NOFOLLOW,
                    dir_fd=root_fd,
                )
            except FileNotFoundError:
                return True
            lock = os.fstat(lock_fd)
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            current_root = os.stat(self._data_root, follow_symlinks=False)
            current_lock = os.stat(
                ".ollama-cloud-worker.lock", dir_fd=root_fd, follow_symlinks=False
            )
            return (
                stat.S_ISREG(lock.st_mode)
                and lock.st_uid == os.getuid()
                and lock.st_nlink == 1
                and stat.S_IMODE(lock.st_mode) == 0o600
                and lock.st_size == 0
                and (root.st_dev, root.st_ino)
                == (current_root.st_dev, current_root.st_ino)
                and (lock.st_dev, lock.st_ino)
                == (current_lock.st_dev, current_lock.st_ino)
                and current_lock.st_uid == os.getuid()
                and current_lock.st_nlink == 1
                and stat.S_IMODE(current_lock.st_mode) == 0o600
                and current_lock.st_size == 0
            )
        except OSError:
            return False
        finally:
            if lock_fd is not None:
                os.close(lock_fd)
            if root_fd is not None:
                os.close(root_fd)

    @staticmethod
    async def _command(*args: str, pass_fds: tuple[int, ...] = ()) -> tuple[int, str]:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            pass_fds=pass_fds,
            env=_manager_environment(),
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

    @staticmethod
    async def _start_command(authority_reader: int, *args: str) -> int:
        """Start through the real manager while passing only the read authority."""
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=authority_reader,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=_manager_environment(),
        )
        try:
            await asyncio.wait_for(process.wait(), _COMMAND_TIMEOUT_SECONDS)
        except (TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                process.kill()
                try:
                    await asyncio.wait_for(process.wait(), 2)
                except TimeoutError:
                    pass
            raise
        return process.returncode or 0

    async def _show(self, unit: str) -> dict[str, str]:
        code, output = await self._command(
            _SYSTEMCTL,
            "--user",
            "show",
            unit,
            "--property=Id,LoadState,Description,Transient,FragmentPath,InvocationID,KillMode,ActiveState,ControlGroup,ExecMainStatus,ExecStart,RuntimeMaxUSec,TimeoutStopUSec,RemainAfterExit,LimitCORE",
            "--no-pager",
        )
        pairs = [line.partition("=") for line in output.splitlines() if "=" in line]
        result = {key: value for key, _, value in pairs}
        if (
            code != 0
            or len(result) != len(pairs)
            or result.get("Id") != unit
            or not result.get("LoadState")
        ):
            raise ValueError("ollama_cloud_unit_identity_invalid")
        return result

    def _identity(
        self,
        unit: str,
        description: str,
        start_token: str,
        properties: dict[str, str],
    ) -> str:
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
        if self._credential_env_file is not None:
            expected_argv += ["--credential-env-file", str(self._credential_env_file)]
        if self._active_recovery_only:
            expected_argv.append("--recovery-only")
        expected_argv += ["--start-authority", start_token]
        if (
            properties.get("Id") != unit
            or properties.get("Description") != description
            or properties.get("Transient") != "yes"
            or properties.get("FragmentPath") != fragment
            or properties.get("KillMode") != "control-group"
            or properties.get("RuntimeMaxUSec") != "30s"
            or properties.get("LimitCORE") != "0"
            or properties.get("TimeoutStopUSec") != "3s"
            or properties.get("RemainAfterExit") != "yes"
            or not exec_start.startswith("{ path=" + executable + " ;")
            or actual_argv != expected_argv
            or len(invocation) != 32
            or any(c not in "0123456789abcdef" for c in invocation)
        ):
            raise ValueError("ollama_cloud_unit_identity_invalid")
        return invocation

    async def _stop_owned(
        self,
        unit: str,
        description: str,
        start_token: str,
        invocation: str,
    ) -> bool:
        try:
            before = await self._show(unit)
            if self._identity(unit, description, start_token, before) != invocation:
                return False
            code, _ = await self._command(_SYSTEMCTL, "--user", "stop", unit)
            if code:
                return False
            after = await self._show(unit)
            if (
                after.get("Id") == unit
                and after.get("FragmentPath")
                and self._identity(unit, description, start_token, after) != invocation
            ):
                return False
            if after.get("Id") == unit and after.get("ActiveState") not in {
                "inactive",
                "failed",
            }:
                return False
            if after.get("ControlGroup"):
                return False
            if after.get("LoadState") != "not-found":
                reset_code, _ = await self._command(
                    _SYSTEMCTL, "--user", "reset-failed", unit
                )
                if reset_code:
                    return False
            final = await self._show(unit)
            return (
                final.get("LoadState") == "not-found"
                and final.get("FragmentPath", "") == ""
                and not final.get("ControlGroup")
            )
        except (OSError, ValueError, TimeoutError):
            return False

    @staticmethod
    async def _finish_cleanup(task: asyncio.Task[_T], deadline: float) -> _T | None:
        """Bound all cleanup steps by one monotonic deadline despite cancellation."""
        while not task.done():
            # Keep time for the manager child's own cancellation/kill/wait.
            remaining = deadline - asyncio.get_running_loop().time() - 3
            if remaining <= 0:
                task.cancel()
                try:
                    await asyncio.wait_for(task, 3)
                except (asyncio.CancelledError, TimeoutError, OSError, ValueError):
                    pass
                return None
            try:
                return await asyncio.wait_for(asyncio.shield(task), remaining)
            except asyncio.CancelledError:
                continue
            except TimeoutError:
                task.cancel()
                try:
                    await asyncio.wait_for(task, 3)
                except (asyncio.CancelledError, TimeoutError, OSError, ValueError):
                    pass
                return None
        return task.result()

    async def _cancelled_cleanup(
        self,
        unit: str,
        description: str,
        start_token: str,
        start: asyncio.Task[int],
    ) -> bool:
        deadline = asyncio.get_running_loop().time() + _CLEANUP_TIMEOUT_SECONDS
        try:
            cleaned = False
            try:
                properties = await self._finish_cleanup(
                    asyncio.create_task(self._show(unit)), deadline
                )
                if (
                    properties is not None
                    and properties.get("LoadState") != "not-found"
                ):
                    invocation = self._identity(
                        unit, description, start_token, properties
                    )
                    cleaned = (
                        await self._finish_cleanup(
                            asyncio.create_task(
                                self._stop_owned(
                                    unit, description, start_token, invocation
                                )
                            ),
                            deadline,
                        )
                        is True
                    )
            except (OSError, ValueError, RuntimeError, TimeoutError):
                pass
            try:
                await self._finish_cleanup(start, deadline)
            except (OSError, ValueError, RuntimeError, TimeoutError):
                # A timed-out manager client may nevertheless have queued the unit.
                pass
            if asyncio.get_running_loop().time() >= deadline:
                return False
            properties = await self._finish_cleanup(
                asyncio.create_task(self._show(unit)), deadline
            )
            if properties is None:
                return False
            if (
                properties.get("LoadState") == "not-found"
                and not properties.get("FragmentPath")
                and not properties.get("ControlGroup")
            ):
                return True
            invocation = self._identity(unit, description, start_token, properties)
            final_cleaned = await self._finish_cleanup(
                asyncio.create_task(
                    self._stop_owned(unit, description, start_token, invocation)
                ),
                deadline,
            )
            return cleaned or final_cleaned is True
        except (OSError, ValueError, RuntimeError, TimeoutError):
            return False

    def _acquire_lock(self) -> int:
        directory = os.open(
            self._data_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        descriptor = None
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
            os.fsync(directory)
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
            self._root_fd = directory
            self._lock_fd = descriptor
            self._verify_lock()
            return descriptor
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            os.close(directory)
            self._root_fd = None
            self._lock_fd = None
            raise

    def _verify_lock(self) -> None:
        if self._root_fd is None or self._lock_fd is None:
            raise ValueError("ollama_cloud_lock_missing")
        fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pinned_root = os.fstat(self._root_fd)
        path_root = os.stat(self._data_root, follow_symlinks=False)
        pinned_lock = os.fstat(self._lock_fd)
        path_lock = os.stat(
            ".ollama-cloud-worker.lock", dir_fd=self._root_fd, follow_symlinks=False
        )
        if (
            not stat.S_ISDIR(path_root.st_mode)
            or path_root.st_uid != os.getuid()
            or stat.S_IMODE(path_root.st_mode) != 0o700
            or (pinned_root.st_dev, pinned_root.st_ino)
            != (path_root.st_dev, path_root.st_ino)
            or not stat.S_ISREG(path_lock.st_mode)
            or path_lock.st_uid != os.getuid()
            or stat.S_IMODE(path_lock.st_mode) != 0o600
            or pinned_lock.st_nlink != 1
            or (pinned_lock.st_dev, pinned_lock.st_ino)
            != (path_lock.st_dev, path_lock.st_ino)
        ):
            raise ValueError("ollama_cloud_lock_replaced")

    def _mark_start(self, unit: str) -> None:
        if self._lock_fd is None:
            raise ValueError("ollama_cloud_lock_missing")
        self._verify_lock()
        data = (unit + "\n").encode("ascii")
        os.ftruncate(self._lock_fd, 0)
        os.lseek(self._lock_fd, 0, os.SEEK_SET)
        if os.write(self._lock_fd, data) != len(data):
            raise ValueError("ollama_cloud_marker_write_failed")
        os.fsync(self._lock_fd)

    def _read_marker(self) -> str:
        if self._lock_fd is None:
            raise ValueError("ollama_cloud_lock_missing")
        self._verify_lock()
        os.lseek(self._lock_fd, 0, os.SEEK_SET)
        data = os.read(self._lock_fd, 129)
        if len(data) > 128:
            raise ValueError("ollama_cloud_marker_invalid")
        try:
            marker = data.decode("ascii")
        except UnicodeDecodeError:
            raise ValueError("ollama_cloud_marker_invalid") from None
        if not marker:
            return ""
        if marker.count("\n") != 1 or not marker.endswith("\n"):
            raise ValueError("ollama_cloud_marker_invalid")
        unit = marker[:-1]
        self._unit_token(unit)
        return unit

    def _clear_marker(self) -> None:
        if self._lock_fd is None:
            raise ValueError("ollama_cloud_lock_missing")
        self._verify_lock()
        os.ftruncate(self._lock_fd, 0)
        os.lseek(self._lock_fd, 0, os.SEEK_SET)
        os.fsync(self._lock_fd)

    @staticmethod
    def _unit_token(unit: str) -> str:
        suffix = ".service"
        if not unit.startswith(_PREFIX) or not unit.endswith(suffix):
            raise ValueError("ollama_cloud_unit_identity_invalid")
        token = unit[len(_PREFIX) : -len(suffix)]
        if not _valid_start_token(token):
            raise ValueError("ollama_cloud_unit_identity_invalid")
        return token

    async def _recover_recorded_start(self, unit: str) -> bool:
        token = self._unit_token(unit)
        description = "AgentMonitor cloud worker " + token
        properties = await self._show(unit)
        if (
            properties.get("LoadState") == "not-found"
            and not properties.get("FragmentPath")
            and not properties.get("ControlGroup")
        ):
            return True
        invocation = self._identity(unit, description, token, properties)
        return await self._stop_owned(unit, description, token, invocation)

    async def _recover_listed_units(self, listing: str) -> bool:
        units = [line.split(maxsplit=1)[0] for line in listing.splitlines() if line]
        if not units or len(units) > 8 or len(set(units)) != len(units):
            return False
        for unit in units:
            if not await self._recover_recorded_start(unit):
                return False
        return True

    async def run_once(self, *, recovery_only: bool = False) -> str:
        if self._quarantined:
            return "quarantined"
        if self._running:
            return "worker_busy"
        self._running = True
        self._active_recovery_only = recovery_only
        try:
            try:
                self._lock_fd = self._acquire_lock()
            except (OSError, ValueError):
                self._quarantined = True
                return "quarantined"
            try:
                marker = self._read_marker()
                if marker:
                    self._recovery_unresolved = True
                    if not await self._recover_recorded_start(marker):
                        return "recovery_unresolved"
                    self._clear_marker()
                    self._recovery_unresolved = False
                    return "recovered"
            except (OSError, ValueError, RuntimeError, TimeoutError):
                self._quarantined = True
                return "quarantined"
            return await self._run_transient()
        except asyncio.CancelledError:
            self._recovery_unresolved = True
            raise
        finally:
            if self._lock_fd is not None:
                os.close(self._lock_fd)
                self._lock_fd = None
            if self._root_fd is not None:
                os.close(self._root_fd)
                self._root_fd = None
            self._running = False

    async def _run_transient(self) -> str:
        # systemctl flattens argv, so whitespace would make identity ambiguous.
        if any(
            character.isspace()
            for character in sys.executable
            + str(self._data_root)
            + (str(self._credential_env_file) if self._credential_env_file else "")
        ):
            self._quarantined = True
            return "quarantined"
        code, existing = await self._command(
            _SYSTEMCTL,
            "--user",
            "list-units",
            "--all",
            "--plain",
            "--no-legend",
            _PREFIX + "*.service",
        )
        if code:
            self._quarantined = True
            return "quarantined"
        if existing.strip():
            try:
                if await self._recover_listed_units(existing):
                    return "recovered"
            except (OSError, ValueError, RuntimeError, TimeoutError):
                pass
            self._quarantined = True
            return "quarantined"
        token = uuid.uuid4().hex
        unit = _PREFIX + token + ".service"
        self.last_unit = unit
        description = "AgentMonitor cloud worker " + token
        environment = _manager_environment()
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
        command = [
            _SYSTEMD_RUN,
            "--user",
            "--quiet",
            "--pipe",
            "--unit=" + unit,
            "--description=" + description,
            "--property=KillMode=control-group",
            "--property=RuntimeMaxSec=30s",
            "--property=LimitCORE=0",
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
        if self._credential_env_file is not None:
            command += ["--credential-env-file", str(self._credential_env_file)]
        if self._active_recovery_only:
            command.append("--recovery-only")
        command += ["--start-authority", token]
        self._mark_start(unit)
        if self._lock_fd is None:
            raise ValueError("ollama_cloud_lock_missing")
        self._verify_lock()
        authority_reader, authority_writer = os.pipe2(os.O_CLOEXEC)
        start = asyncio.create_task(self._start_command(authority_reader, *command))
        try:
            start_deadline = (
                asyncio.get_running_loop().time() + _COMMAND_TIMEOUT_SECONDS
            )
            invocation = ""
            while asyncio.get_running_loop().time() < start_deadline:
                if start.done():
                    code = await asyncio.shield(start)
                    if code:
                        raise ValueError("ollama_cloud_unit_start_failed")
                properties = await self._show(unit)
                if properties.get("LoadState") != "not-found":
                    invocation = self._identity(unit, description, token, properties)
                    break
                await asyncio.sleep(0.05)
            if not invocation:
                raise TimeoutError("ollama_cloud_unit_start_timeout")
            self._verify_lock()
            authority = ("START " + token + "\n").encode("ascii")
            if os.write(authority_writer, authority) != len(authority):
                raise ValueError("ollama_cloud_start_authority_write_failed")
            os.close(authority_writer)
            authority_writer = -1
            for _ in range(300):
                properties = await self._show(unit)
                if self._identity(unit, description, token, properties) != invocation:
                    raise ValueError("ollama_cloud_unit_identity_changed")
                if properties.get("ActiveState") in {"failed", "inactive"} or (
                    properties.get("ActiveState") == "active"
                    and not properties.get("ControlGroup")
                ):
                    status = properties.get("ExecMainStatus")
                    clean = await self._stop_owned(unit, description, token, invocation)
                    if not clean:
                        self._recovery_unresolved = True
                        return "recovery_unresolved"
                    await self._finish_cleanup(
                        start, asyncio.get_running_loop().time() + 5
                    )
                    if not start.done():
                        self._recovery_unresolved = True
                        return "recovery_unresolved"
                    self._clear_marker()
                    self._recovery_unresolved = status not in {"0", "3"}
                    return (
                        "not_admitted"
                        if status == "3"
                        else "recovery_unresolved"
                        if status == "4"
                        else "completed"
                        if status == "0"
                        else "unavailable"
                    )
                await asyncio.sleep(0.1)
            clean = await self._stop_owned(unit, description, token, invocation)
            if clean:
                self._clear_marker()
            else:
                self._recovery_unresolved = True
            return "worker_timeout"
        except asyncio.CancelledError:
            if authority_writer >= 0:
                os.close(authority_writer)
                authority_writer = -1
            self._recovery_unresolved = True
            await self._cancelled_cleanup(unit, description, token, start)
            raise
        except (OSError, ValueError, RuntimeError, TimeoutError):
            if authority_writer >= 0:
                os.close(authority_writer)
                authority_writer = -1
            self._recovery_unresolved = True
            await self._cancelled_cleanup(unit, description, token, start)
            return "recovery_unresolved"
        finally:
            if authority_writer >= 0:
                os.close(authority_writer)
            if authority_reader >= 0:
                os.close(authority_reader)

    async def run(self) -> None:
        self._lifecycle_running = True
        try:
            while True:
                try:
                    await self.run_once(recovery_only=self._credential_env_file is None)
                except Exception:  # noqa: BLE001 - optional lane, no provider details.
                    self._quarantined = True
                await asyncio.sleep(60)
        finally:
            self._lifecycle_running = False

    def is_monitoring_available(self) -> bool:
        """Include lifecycle supervision; capability alone is not polling."""
        return (
            self._credential_env_file is not None
            and self._lifecycle_running
            and self.is_available()
        )

    def is_configured(self) -> bool:
        return self._credential_env_file is not None

    def credential_env_file(self) -> Path | None:
        return self._credential_env_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--credential-env-file", type=Path)
    parser.add_argument("--recovery-only", action="store_true")
    parser.add_argument("--start-authority", required=True)
    args = parser.parse_args()
    if not args.data_root.is_absolute() or args.data_root in {Path("/"), Path.home()}:
        return 2
    if not _consume_start_authority(args.start_authority):
        return _START_AUTHORIZATION_REVOKED_EXIT
    if not (args.data_root / "agentmonitor.db").is_file():
        return 3
    try:
        collector = OllamaCloudCollectionV1(
            DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root),
            data_root=args.data_root,
            credential_env_file=args.credential_env_file,
        )
        now = datetime.now(UTC)
        rate, _, _ = collector.recover_journals(
            as_of=now,
            owner_stale_before=now - timedelta(minutes=2),
            recovery_lease_expires_at=now + timedelta(seconds=45),
        )
        if recovery_exit_code(rate) != 0:
            return 4
        if args.recovery_only:
            return 0
        if args.credential_env_file is None:
            return 3
        recover_ollama_env_staging(args.credential_env_file, args.data_root)
        recover_env_location_if_unused(
            args.data_root,
            has_unfinished_bindings=SqliteCredentialBindingsV1(
                DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root)
            ).has_unfinished_bindings,
        )
        if recovery_exit_code(rate) == 0:
            try:
                require_probe_authorized(args.credential_env_file is not None)
            except ValueError:
                return 3
            if collector.preferred_work_lane() == "scheduled":
                try:
                    scheduled = collector.tick()
                except ValueError as error:
                    if str(error) != "ollama_cloud_source_not_admitted":
                        raise
                    scheduled = "ollama_cloud_no_eligible_accounts"
                if scheduled == "ollama_cloud_no_eligible_accounts":
                    collector.verification_tick()
            elif collector.verification_tick() == "no_candidate":
                try:
                    collector.tick()
                except ValueError as error:
                    if str(error) != "ollama_cloud_source_not_admitted":
                        raise
        return 0
    except Exception:  # noqa: BLE001 - the process returns only a closed status.
        return 1


if __name__ == "__main__":
    sys.exit(main())
