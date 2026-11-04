"""Bounded owned cloud-network interruption; account configuration is untouched."""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _line(descriptor: int, timeout: float, maximum: int = 4096) -> bytes:
    """Read one bounded protocol line without trusting child-controlled output."""
    deadline = time.monotonic() + timeout
    result = bytearray()
    while len(result) <= maximum:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([descriptor], [], [], remaining)[0]:
            raise TimeoutError("m6_controlled_child_timeout")
        value = os.read(descriptor, 1)
        if not value:
            raise ValueError("m6_controlled_child_closed")
        result.extend(value)
        if value == b"\n":
            return bytes(result)
    raise ValueError("m6_controlled_child_output_invalid")


def _ticks(pid: int) -> int:
    value = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    return int(value.rsplit(")", 1)[1].split()[19])


def _namespace(pid: int | str) -> int:
    return os.stat(f"/proc/{pid}/ns/net").st_ino


def _file_metadata(path: Path, *, mode: int) -> None:
    value = path.lstat()
    if (
        not stat.S_ISREG(value.st_mode)
        or value.st_uid != os.getuid()
        or stat.S_IMODE(value.st_mode) != mode
        or value.st_nlink != 1
        or path.resolve() != path
    ):
        raise ValueError("m6_controlled_file_unsafe")


@dataclass
class IsolatedWorker:
    process: subprocess.Popen[bytes]
    pid: int
    start_ticks: int
    namespace_inode: int
    parent_namespace_inode: int
    pidfd: int

    def close(self) -> None:
        """Kill only our pinned namespace init; kernel tears down its descendants."""
        try:
            if not select.select([self.pidfd], [], [], 0)[0]:
                signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
            if not select.select([self.pidfd], [], [], 5)[0]:
                raise RuntimeError("m6_controlled_cleanup_unconfirmed")
            self.process.wait(timeout=5)
        finally:
            os.close(self.pidfd)
            if self.process.stdin is not None:
                self.process.stdin.close()
            if self.process.stdout is not None:
                self.process.stdout.close()


def _sandbox_prefix(data_root: Path, env_file: Path) -> list[str]:
    """Mount only approved storage and isolate the real worker's OS boundaries."""
    root = data_root.lstat()
    if (
        not stat.S_ISDIR(root.st_mode)
        or root.st_uid != os.getuid()
        or stat.S_IMODE(root.st_mode) != 0o700
        or data_root.resolve() != data_root
        or env_file.name != ".env"
    ):
        raise ValueError("m6_controlled_root_unsafe")
    lock = env_file.parent / ".ollama-env.lock"
    _file_metadata(env_file, mode=0o600)
    _file_metadata(lock, mode=0o600)
    return [
        "/usr/bin/bwrap",
        "--unshare-net",
        "--unshare-pid",
        "--as-pid-1",
        "--die-with-parent",
        "--new-session",
        "--ro-bind",
        "/",
        "/",
        "--bind",
        str(data_root),
        str(data_root),
        "--bind",
        str(lock),
        str(lock),
        "--ro-bind",
        str(env_file),
        str(env_file),
        "--proc",
        "/proc",
        # A read-only root bind makes host device nodes inaccessible. Give the
        # helper private minimal devices for DEVNULL, never a writable host /dev.
        "--dev",
        "/dev",
    ]


def _start_worker(
    data_root: Path,
    env_file: Path,
    attempt_id: str,
    supervisor_fd: int | None = None,
) -> IsolatedWorker:
    """Start inert, owner-controlled child; no collection before the GO handshake."""
    if re.fullmatch(r"[a-f0-9]{32}", attempt_id) is None:
        raise ValueError("m6_controlled_attempt_invalid")
    command = _sandbox_prefix(data_root, env_file)
    parent_namespace = _namespace("self")
    info_read, info_write = os.pipe2(os.O_CLOEXEC)
    command += ["--info-fd", str(info_write)]
    inherited = (info_write,)
    if supervisor_fd is not None:
        # bwrap retains the shared flock until its namespace is gone even if the
        # observing parent dies. Never explicitly LOCK_UN a shared description.
        command += ["--sync-fd", str(supervisor_fd)]
        inherited += (supervisor_fd,)
    command += [
        sys.executable,
        "-B",
        "-m",
        "tools.automation.implementations.m6_controlled_recovery_interval",
        "--isolated-worker",
        "--data-root",
        str(data_root),
        "--env-file",
        str(env_file),
        "--attempt-id",
        attempt_id,
        "--parent-namespace",
        str(parent_namespace),
    ]
    process = None
    pidfd = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            pass_fds=inherited,
            cwd=ROOT,
            env={
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": str(ROOT / "backend/src") + os.pathsep + str(ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
                "LC_ALL": "C.UTF-8",
            },
        )
        os.close(info_write)
        info_write = -1
        info = bytearray()
        deadline = time.monotonic() + 10
        while b"}" not in info and len(info) < 4096:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([info_read], [], [], remaining)[0]:
                raise TimeoutError("m6_controlled_child_timeout")
            block = os.read(info_read, 4096)
            if not block:
                raise ValueError("m6_controlled_namespace_unavailable")
            info.extend(block)
        pid = json.loads(info)["child-pid"]
        if type(pid) is not int or pid <= 1:
            raise ValueError("m6_controlled_child_identity_invalid")
        pidfd = os.pidfd_open(pid)
        start_ticks = _ticks(pid)
        namespace = _namespace(pid)
        assert process.stdout is not None
        ready = json.loads(_line(process.stdout.fileno(), 10))
        if (
            ready != {"ready": attempt_id}
            or _ticks(pid) != start_ticks
            or namespace == parent_namespace
            or namespace != _namespace(pid)
        ):
            raise ValueError("m6_controlled_child_identity_invalid")
        result = IsolatedWorker(
            process, pid, start_ticks, namespace, parent_namespace, pidfd
        )
        pidfd = None
        return result
    except BaseException:
        if pidfd is not None:
            try:
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                os.close(pidfd)
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            if process.stdin is not None:
                process.stdin.close()
            if process.stdout is not None:
                process.stdout.close()
        raise
    finally:
        os.close(info_read)
        if info_write != -1:
            os.close(info_write)


def _isolated_worker(args: argparse.Namespace) -> int:
    if (
        os.getpid() != 1
        or _namespace("self") == args.parent_namespace
        or not os.statvfs(args.env_file).f_flag & os.ST_RDONLY
        or os.statvfs(args.data_root).f_flag & os.ST_RDONLY
    ):
        return 3
    print(json.dumps({"ready": args.attempt_id}), flush=True)
    if _line(sys.stdin.fileno(), 60, 128) != ("GO " + args.attempt_id + "\n").encode():
        return 3
    return _collector_loop(args)


def _diagnostic(error: Exception, stage: str) -> dict[str, str | int]:
    """Code location only: never exception messages, locals, paths or payloads."""
    trace = error.__traceback__
    while trace is not None and trace.tb_next is not None:
        trace = trace.tb_next
    name = type(error).__name__
    function = trace.tb_frame.f_code.co_name if trace is not None else "unknown"
    safe = r"[A-Za-z_][A-Za-z0-9_]{0,100}"
    return {
        "stage": stage,
        "error_type": name if re.fullmatch(safe, name) else "OtherError",
        "function": function if re.fullmatch(safe, function) else "unknown",
        "line": trace.tb_lineno if trace is not None else 0,
    }


def _collector_loop(args: argparse.Namespace) -> int:
    stage = ["collector_import"]
    try:
        return _collect(args, stage)
    except Exception as error:
        print(json.dumps(_diagnostic(error, stage[0])), flush=True)
        return 3


def _collect(args: argparse.Namespace, stage: list[str]) -> int:
    # Imports after authorization keep the inert preflight free of collector I/O.
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.composition.ollama_cloud_collection import OllamaCloudCollectionV1
    from agentmonitor.contracts.collection_control_v1 import CollectionFailedV1

    stage[0] = "collector_init"
    collector = OllamaCloudCollectionV1(
        DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root),
        data_root=args.data_root,
        credential_env_file=args.env_file,
    )
    deadline = time.monotonic() + 300
    stage[0] = "collector_tick"
    while time.monotonic() < deadline:
        outcome = collector.tick()
        if isinstance(outcome, CollectionFailedV1):
            print(json.dumps({"failure_run_id": outcome.run_id.value}), flush=True)
            return 0
        if not isinstance(outcome, str) or outcome not in {
            "busy",
            "not_due",
            "no_candidate",
            "replayed_active",
            "replayed_terminal",
        }:
            print(
                json.dumps(
                    {
                        "stage": "collector_tick",
                        "error_type": "NoEligibleAccounts"
                        if outcome == "ollama_cloud_no_eligible_accounts"
                        else "UnexpectedOutcome",
                        "function": "_collect",
                        "line": 0,
                    }
                ),
                flush=True,
            )
            return 3
        time.sleep(min(5, max(0, deadline - time.monotonic())))
    return 3


@contextmanager
def _supervisor_lock(data_root: Path) -> Iterator[int]:
    """Borrow only an empty safe lock; foreign recovery markers remain untouched."""
    from agentmonitor.composition.ollama_cloud_worker import (
        OllamaCloudWorkerSupervisorV1,
    )

    supervisor = OllamaCloudWorkerSupervisorV1(data_root)
    try:
        descriptor = supervisor._acquire_lock()
        if supervisor._read_marker():
            raise BlockingIOError("m6_controlled_worker_busy")
        yield descriptor
        supervisor._verify_lock()
        if supervisor._read_marker():
            raise ValueError("m6_controlled_worker_marker_changed")
    finally:
        if supervisor._lock_fd is not None:
            os.close(supervisor._lock_fd)
            supervisor._lock_fd = None
        if supervisor._root_fd is not None:
            os.close(supervisor._root_fd)
            supervisor._root_fd = None


def _phase_probe(revision: str, account_id: str, phase: str, run_id: str) -> datetime:
    result = subprocess.run(
        [
            "/usr/bin/node",
            "frontend/tests/browser/m6/probe_controlled_recovery.mjs",
            revision,
            account_id,
            phase,
            run_id,
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=25,
        check=False,
    )
    if result.returncode or len(result.stdout) > 4096:
        raise ValueError("m6_controlled_dashboard_unavailable")
    value = json.loads(result.stdout)
    if (
        set(value) != {"record_type", "status", "source_revision", "observed_at"}
        or value["record_type"]
        != "agentmonitor.m6_controlled_recovery_dashboard_probe.v1"
        or value["status"] != "passed"
        or value["source_revision"] != revision
    ):
        raise ValueError("m6_controlled_dashboard_unavailable")
    observed = datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
    if observed.utcoffset() != timedelta(0) or not (
        datetime.now(UTC) - timedelta(seconds=30) <= observed <= datetime.now(UTC)
    ):
        raise ValueError("m6_controlled_dashboard_time_invalid")
    return observed


def _is_committed(run: object) -> bool:
    from agentmonitor.contracts.collection_recovery_v1 import CollectionRecoveryRunV1

    return (
        isinstance(run, CollectionRecoveryRunV1)
        and run.state in {"succeeded", "partial"}
        and run.dispatch_certainty == "response_received"
        and run.response_outcome == "succeeded"
        and run.failure_code is None
        and run.payload_digest is not None
        and bool(run.observation_ids)
    )


def observe_controlled_recovery_interval(
    revision: str, attempt_id: str
) -> dict[str, object]:
    """One real isolated request followed exclusively by normal scheduled recovery."""
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.recovery import (
        SqliteCollectionRecoveryQueryV1,
    )
    from agentmonitor.composition.ollama_credential_operator import (
        selected_env_from_service,
    )

    from tools.automation.implementations.m6_controlled_recovery_evidence import (
        ControlledNetworkWitnessV1,
        build_controlled_recovery_evidence_v1,
    )
    from tools.automation.implementations.m6_recovery_interval import (
        DATA,
        _committed_in_interval,
        _dashboard_probe,
        _identity,
        _runs,
        _scopes,
    )

    if (
        re.fullmatch(r"[a-f0-9]{40}", revision) is None
        or re.fullmatch(r"[a-f0-9]{32}", attempt_id) is None
    ):
        raise ValueError("m6_controlled_input_invalid")
    began = datetime.now(UTC)
    deadline = time.monotonic() + 625
    result: dict[str, object] = {
        "record_type": "agentmonitor.m6_controlled_recovery_unavailable.v1",
        "schema_version": "1.0.0",
        "status": "not_run",
        "reason_code": "m6_controlled_target_unavailable",
        "source_revision": revision,
        "service_invocation_id": None,
        "attempt_id": attempt_id,
        "started_at": began.isoformat(),
        "completed_at": began.isoformat(),
    }
    try:
        identity = _identity()
        result["service_invocation_id"] = identity.invocation_id
        reference = DatabaseRefV1(DATA / "agentmonitor.db", DATA)
        repository = SqliteCollectionRecoveryQueryV1(reference)
        scopes = _scopes(reference)
        if not scopes:
            return result
        env_file = selected_env_from_service(DATA)
        # At most one owned isolated child. The normal worker gets its own
        # chance to finish or recover a marker; this harness never does that.
        lock_deadline = min(deadline, time.monotonic() + 60)
        worker = None
        failure_id = None
        isolation_start = None
        isolation_end = None
        samples: list[datetime] = []
        while time.monotonic() < lock_deadline:
            if _identity() != identity or _scopes(reference) != scopes:
                raise ValueError("m6_controlled_scope_changed")
            try:
                with _supervisor_lock(DATA) as descriptor:
                    isolation_start = datetime.now(UTC)
                    worker = _start_worker(DATA, env_file, attempt_id, descriptor)
                    try:
                        samples.append(_dashboard_probe(revision))
                        if _identity() != identity or _scopes(reference) != scopes:
                            raise ValueError("m6_controlled_scope_changed")
                        assert worker.process.stdin is not None
                        assert worker.process.stdout is not None
                        worker.process.stdin.write(("GO " + attempt_id + "\n").encode())
                        worker.process.stdin.flush()
                        record = json.loads(_line(worker.process.stdout.fileno(), 325))
                        if (
                            isinstance(record, dict)
                            and set(record)
                            == {"stage", "error_type", "function", "line"}
                            and record["stage"]
                            in {"collector_import", "collector_init", "collector_tick"}
                            and type(record["line"]) is int
                            and 0 <= record["line"] <= 100000
                            and all(
                                isinstance(record[key], str)
                                and re.fullmatch(
                                    r"[A-Za-z_][A-Za-z0-9_]{0,100}", record[key]
                                )
                                for key in ("error_type", "function")
                            )
                        ):
                            print(
                                json.dumps(record, sort_keys=True),
                                file=sys.stderr,
                                flush=True,
                            )
                        if (
                            not isinstance(record, dict)
                            or set(record) != {"failure_run_id"}
                            or not isinstance(record["failure_run_id"], str)
                            or re.fullmatch(
                                r"[A-Za-z0-9_.:@-]{1,128}", record["failure_run_id"]
                            )
                            is None
                            or worker.process.wait(timeout=5) != 0
                        ):
                            raise ValueError("m6_controlled_failure_invalid")
                        failure_id = record["failure_run_id"]
                    finally:
                        worker.close()
                        isolation_end = datetime.now(UTC)
                break
            except BlockingIOError:
                time.sleep(min(2, max(0, lock_deadline - time.monotonic())))
        if worker is None:
            result["reason_code"] = "m6_controlled_worker_busy"
            return result
        if failure_id is None or isolation_start is None or isolation_end is None:
            result["reason_code"] = "m6_controlled_failure_unobserved"
            return result
        if _identity() != identity or _scopes(reference) != scopes:
            raise ValueError("m6_controlled_scope_changed")
        failed = [
            run
            for run in _runs(repository, "ollama", isolation_start, isolation_end)
            if run.run_id.value == failure_id
        ]
        if len(failed) != 1:
            raise ValueError("m6_controlled_failure_invalid")
        failure = failed[0]
        matching_scopes = [
            scope
            for scope in scopes
            if any(
                run == failure
                for run in _runs(
                    repository, "ollama", isolation_start, isolation_end, scope
                )
            )
        ]
        if len(matching_scopes) != 1 or (
            failure.state != "failed"
            or failure.failure_code != "provider_unavailable"
            or failure.response_outcome is not None
            or failure.dispatch_certainty not in {"not_started", "may_have_started"}
            or failure.payload_digest is not None
            or failure.observation_ids
        ):
            raise ValueError("m6_controlled_failure_invalid")
        scope = matching_scopes[0]
        samples.append(
            _phase_probe(revision, scope.account_id.value, "failed", failure_id)
        )
        witness = ControlledNetworkWitnessV1(
            attempt_id,
            revision,
            identity.invocation_id,
            worker.pid,
            worker.start_ticks,
            worker.parent_namespace_inode,
            worker.namespace_inode,
            failure_id,
            isolation_start,
            isolation_end,
            True,
        )
        while time.monotonic() < deadline - 30:
            if _identity() != identity or _scopes(reference) != scopes:
                raise ValueError("m6_controlled_scope_changed")
            now = datetime.now(UTC)
            recoveries = [
                run
                for run in _runs(repository, "ollama", isolation_end, now, scope)
                if run.requested_at > isolation_end and _is_committed(run)
            ]
            continuity = []
            for provider in ("claude", "codex"):
                run = _committed_in_interval(
                    _runs(repository, provider, isolation_start, now), isolation_start
                )
                if run is not None:
                    continuity.append(run)
            if recoveries and len(continuity) == 2:
                recovery = max(recoveries, key=lambda run: run.completed_at)
                samples.append(
                    _phase_probe(
                        revision,
                        scope.account_id.value,
                        "recovered",
                        recovery.run_id.value,
                    )
                )
                if _identity() != identity or _scopes(reference) != scopes:
                    raise ValueError("m6_controlled_scope_changed")
                evidence = build_controlled_recovery_evidence_v1(
                    revision=revision,
                    service_invocation_id=identity.invocation_id,
                    attempt_id=attempt_id,
                    scope=scope,
                    witness=witness,
                    failure=failure,
                    recovery=recovery,
                    dashboard_observed_at=tuple(samples),
                    continuity_runs=tuple(continuity),
                    now=datetime.now(UTC),
                )
                return asdict(evidence)
            # Actual browser continuity is sampled while recovery remains pending.
            samples.append(_dashboard_probe(revision))
            time.sleep(min(10, max(0, deadline - 30 - time.monotonic())))
        result["reason_code"] = "m6_controlled_recovery_incomplete"
    except (
        OSError,
        ValueError,
        RuntimeError,
        TimeoutError,
        subprocess.SubprocessError,
        KeyError,
        TypeError,
    ):
        result.update(
            status="blocked", reason_code="m6_controlled_boundary_unavailable"
        )
    finally:
        result["completed_at"] = datetime.now(UTC).isoformat()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isolated-worker", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--parent-namespace", type=int)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--revision")
    args = parser.parse_args()
    try:
        if args.isolated_worker:
            return _isolated_worker(args)
        result = observe_controlled_recovery_interval(args.revision, args.attempt_id)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "passed" else 3
    except (OSError, ValueError, TimeoutError):
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
