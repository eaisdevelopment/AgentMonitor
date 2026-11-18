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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.composition.budget_dispatch import BudgetWorkV1
    from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
    from agentmonitor.contracts.collection_control_v1 import (
        BudgetCollectionReceiptV1,
        BudgetCollectionRunViewV1,
        CloudBudgetCollectionRunAdmissionV1,
        CloudBudgetReportContextV1,
    )
    from agentmonitor.contracts.registry_v1 import (
        CloudMonitoringTargetV1,
        ProviderAccessTargetV1,
    )

ROOT = Path(__file__).resolve().parents[3]

# Two actual quarter-hour budget waits, each followed by a bounded normal
# scheduling observation, plus owned worker and finite verification overhead.
FINANCIAL_MAX_SECONDS = 2 * (15 * 60 + 600) + 125 + 180
FINANCIAL_REASONS = {
    "m7_financial_context_unavailable",
    "m7_financial_report_unavailable",
    "m7_financial_receipt_unavailable",
    "m7_financial_lineage_invalid",
    "m7_financial_authority_changed",
    "m7_financial_prior_monetary_report_required",
    "m7_financial_retained_report_changed",
    "m7_financial_old_spend_not_current",
    "m7_financial_revision_mismatch",
    "m7_financial_failure_not_observed",
    "m7_financial_failed_context_unavailable",
    "m7_financial_failure_invalid",
    "m7_financial_recovery_context_changed",
    "m7_financial_retry_unbounded",
    "m7_financial_recovery_incomplete",
    "m7_financial_boundary_unavailable",
}


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
            if self.process.stderr is not None:
                self.process.stderr.close()


def financial_worker_diagnostic(output: bytes) -> str | None:
    """Accept only the worker's closed diagnostic, never arbitrary stderr text."""
    from agentmonitor.composition.billing_worker import format_worker_failure

    if len(output) > 4096:
        return None
    for line in output.decode("ascii", errors="replace").splitlines():
        match = re.fullmatch(
            r"BILLING_WORKER_FAILURE phase=([a-z]+) type=([A-Za-z][A-Za-z0-9]*) "
            r"source=(?:backend/src/agentmonitor/([a-z0-9_/.]+):(\d{1,7})|unknown:0)",
            line,
        )
        if match is not None:
            phase, kind, path, number = match.groups()
            if format_worker_failure(phase, kind, path or "", int(number or 0)) == line:
                return line
    return None


def financial_attempt_kind(
    reference: DatabaseRefV1, run: BudgetCollectionRunViewV1
) -> str | None:
    """Read actual dispatch evidence; absence of HTTP is never a provider response."""
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )

    if (
        run.report_id is not None
        or run.payload_digest is not None
        or run.observation_ids
    ):
        return None
    if run.state == "failed" and run.error_code == "ollama_usage_provider_unavailable":
        return "provider_response"
    if not (
        run.state == "running"
        or (run.state == "failed" and run.error_code == "collection_worker_interrupted")
    ):
        return None
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT phase,outcome,response_received_at FROM "
                "collection_cloud_attempt_journal WHERE run_id=?",
                (run.run_id.value,),
            ).one_or_none()
    return (
        "outcome_unknown"
        if row is not None and tuple(row) == ("dispatched", None, None)
        else None
    )


def financial_unknown_release(
    reference: DatabaseRefV1, run: BudgetCollectionRunViewV1
) -> tuple[datetime, datetime] | None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        open_sqlite_database,
    )

    if run.state != "failed" or run.error_code != "collection_worker_interrupted":
        return None
    if financial_attempt_kind(reference, run) != "outcome_unknown":
        return None
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT u.released_at,u.next_allowed_at FROM "
                "collection_cloud_attempt_journal j JOIN "
                "collection_cloud_uncertain_outcome u ON u.admission_id=j.admission_id "
                "WHERE j.run_id=? AND u.reason='abandoned_outcome_unknown'",
                (run.run_id.value,),
            ).one_or_none()
    if row is None or row[0] is None or row[1] is None:
        return None
    released, retry = map(datetime.fromisoformat, row)
    if retry < released + timedelta(seconds=300):
        return None
    return released, retry


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
    *,
    financial: bool = False,
    runtime: Path | None = None,
) -> IsolatedWorker:
    """Start inert, owner-controlled child; no collection before the GO handshake."""
    if re.fullmatch(r"[a-f0-9]{32}", attempt_id) is None:
        raise ValueError("m6_controlled_attempt_invalid")
    command = _sandbox_prefix(data_root, env_file)
    parent_namespace = _namespace("self")
    info_read, info_write = os.pipe2(os.O_CLOEXEC)
    command += ["--info-fd", str(info_write)]
    inherited: tuple[int, ...] = (info_write,)
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
    if financial:
        command.append("--financial")
    process = None
    pidfd = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if financial else subprocess.DEVNULL,
            pass_fds=inherited,
            cwd=ROOT,
            env={
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": str((runtime or ROOT) / "backend/src")
                + os.pathsep
                + str(ROOT),
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
            if process.stderr is not None:
                process.stderr.close()
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
        return (
            _collect_financial(args, stage) if args.financial else _collect(args, stage)
        )
    except Exception as error:
        print(json.dumps(_diagnostic(error, stage[0])), flush=True)
        return 3


def _collect_financial(args: argparse.Namespace, stage: list[str]) -> int:
    """Use the fixed real billing entrypoint after GO and its separate START grant."""
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.composition import billing_worker
    from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1

    began = datetime.now(UTC)
    sys.argv = [
        "billing_worker",
        "--data-root",
        str(args.data_root),
        "--credential-env-file",
        str(args.env_file),
        "--start-authority",
        args.attempt_id,
    ]
    stage[0] = "financial_worker"
    outcome = billing_worker.main()
    if outcome not in {0, 4}:
        print(json.dumps({"worker_exit_code": outcome}), flush=True)
        return 3
    repository = SqliteCollectionRepositoryV1(
        DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root)
    )
    reference = DatabaseRefV1(args.data_root / "agentmonitor.db", args.data_root)
    try:
        failures = tuple(
            run
            for run in repository.list_runs("ollama", None, datetime.now(UTC), 100)
            if isinstance(run, BudgetCollectionRunViewV1)
            and run.requested_at >= began
            and run.source_id == "ollama.cloud.usage.v1"
            and financial_attempt_kind(reference, run) is not None
        )
    except (RuntimeError, ValueError):
        if outcome != 0:
            print(json.dumps({"worker_exit_code": outcome}), flush=True)
            return 3
        raise
    if len(failures) != 1:
        print(
            json.dumps(
                {"worker_exit_code": outcome}
                if outcome
                else {"matching_failure_count": len(failures)}
            ),
            flush=True,
        )
        return 3
    print(json.dumps({"failure_run_id": failures[0].run_id.value}), flush=True)
    return 0


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
def _supervisor_lock(data_root: Path, *, financial: bool = False) -> Iterator[int]:
    """Borrow only an empty safe lock; foreign recovery markers remain untouched."""
    from agentmonitor.composition.ollama_cloud_worker import (
        OllamaCloudWorkerSupervisorV1,
    )

    supervisor: OllamaCloudWorkerSupervisorV1
    if financial:
        from agentmonitor.composition.billing_worker_supervisor import (
            BillingWorkerSupervisorV1,
        )

        supervisor = BillingWorkerSupervisorV1(data_root)
    else:
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


def financial_observation_end(
    now: datetime,
    next_allowed: datetime | None,
    *,
    schedule_due: datetime | None = None,
) -> datetime:
    """Wait through actual budget/cadence eligibility, then observe normal recovery."""
    boundary = max(now, next_allowed or now, schedule_due or now)
    if boundary > now + timedelta(minutes=15):
        raise ValueError("m7_financial_retry_unbounded")
    return boundary + timedelta(seconds=600)


def financial_slot_ready_at(
    now: datetime,
    gate: tuple[str, datetime | None],
    scheduled: datetime,
) -> datetime | None:
    """Predict readiness only from released gate state and actual schedule data."""
    state, allowance = gate
    if state == "ready":
        return max(now, scheduled)
    if state == "not_due" and allowance is not None:
        return max(now, scheduled, allowance)
    return None


def financial_has_next_turn(
    work: tuple[BudgetWorkV1, ...],
    monetary_keys: frozenset[tuple[str, str, str]],
) -> bool:
    """Do not isolate a different context or an explicit owner request."""
    return bool(
        work
        and work[0].key in monetary_keys
        and work[0].queued_run_id is None
        and work[0].scheduled_due
    )


@dataclass(frozen=True)
class FinancialBaseline:
    graph: CloudMonitoringTargetV1
    service: ProviderAccessTargetV1
    context: CloudBudgetReportContextV1
    run: BudgetCollectionRunViewV1
    stored: BudgetReportViewV1
    receipt: BudgetCollectionReceiptV1


def _financial_snapshot(
    reference: DatabaseRefV1, run: BudgetCollectionRunViewV1
) -> FinancialBaseline:
    """Read and check immutable financial authority, report, provenance and receipt."""
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.adapters.providers.ollama.api.manifest import (
        ADAPTER_VERSION,
        EVIDENCE_REFERENCE,
    )
    from agentmonitor.adapters.providers.ollama.api.policy import SOURCE_ID
    from agentmonitor.contracts.collection_control_v1 import CloudBudgetReportContextV1
    from agentmonitor.modules.capacity.application.budget_commit import (
        budget_report_payload_digest,
    )

    runs = SqliteCollectionRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    captured = runs.get_budget_target(run.run_id)
    if not isinstance(captured, tuple) or not isinstance(
        captured[2], CloudBudgetReportContextV1
    ):
        raise ValueError("m7_financial_context_unavailable")
    graph, service, context = captured
    if run.report_id is None:
        raise ValueError("m7_financial_report_unavailable")
    stored = reports.get_report(graph.account_id, run.report_id)
    status = reports.get_commit_status(run.run_id, run.capability_id)
    provenance = reports.get_report_provenance(graph.account_id, run.report_id)
    if stored is None or status.receipt is None or provenance is None:
        raise ValueError("m7_financial_receipt_unavailable")
    receipt, report = status.receipt, stored.report
    if not (
        run.state == "succeeded"
        and run.source_id == report.source_id == SOURCE_ID
        and run.adapter_version == provenance.adapter_version == ADAPTER_VERSION
        and provenance.decision_reference == EVIDENCE_REFERENCE
        and provenance.operation_id == run.run_id
        and run.account_id == report.subject.account_id == graph.account_id
        and run.resource_id == report.subject.resource_id == graph.resource_id
        and report.subject.provider_target.target_id == service.access_target_id
        and run.target_generation
        == report.binding_generation
        == graph.binding.generation
        and report.binding_id == graph.binding.binding_id
        and report.scope_generation == 1
        and report.scope_evidence == "unresolved"
        and report.source_category == context.scope + "_requests_and_cost"
        and report.grouping == context.grouping
        and report.requested_period.start == context.interval_start
        and report.requested_period.end == context.interval_end
        and report.covered_period == report.requested_period
        and report.completeness == "complete"
        and receipt.run_id == run.run_id
        and receipt.report_id == stored.report_id
        and receipt.target_generation == run.target_generation
        and receipt.payload_digest
        == run.payload_digest
        == budget_report_payload_digest(report)
        and receipt.stored_at == stored.stored_at
    ):
        raise ValueError("m7_financial_lineage_invalid")
    return FinancialBaseline(graph, service, context, run, stored, receipt)


def _financial_authority_current(
    reference: DatabaseRefV1, baseline: FinancialBaseline
) -> bool:
    from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
        SqliteCloudCredentialRegistryV1,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.repository import (
        SqliteRegistryRepositoryV1,
    )

    registry, cloud = (
        SqliteRegistryRepositoryV1(reference),
        SqliteCloudCredentialRegistryV1(reference),
    )
    account = registry.get_account(baseline.graph.account_id)
    return bool(
        account is not None
        and account.lifecycle == "active"
        and account.is_effective_monitoring_enabled
        and cloud.read_monitoring_target(baseline.graph.account_id) == baseline.graph
        and cloud.read_active_access_target(baseline.graph.access_target_id)
        == baseline.service
    )


def _financial_sample(
    reference: DatabaseRefV1, baseline: FinancialBaseline, now: datetime
) -> CloudBudgetCollectionRunAdmissionV1:
    from agentmonitor.adapters.persistence.registry.sqlite.repository import (
        SqliteRegistryRepositoryV1,
    )
    from agentmonitor.composition.ollama_usage_run import build_ollama_usage_run
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    account = SqliteRegistryRepositoryV1(reference).get_account(
        baseline.graph.account_id
    )
    if account is None:
        raise ValueError("m7_financial_authority_changed")
    return build_ollama_usage_run(
        graph=baseline.graph,
        service=baseline.service,
        context=baseline.context,
        registry_revision=account.registry_revision,
        scheduler_instance_id=OpaqueIdV1("financial-recovery-observer"),
        run_id=OpaqueIdV1("financial-recovery-observer"),
        request_id=OpaqueIdV1("financial-recovery-observer"),
        requested_at=now,
    )


def _financial_next_boundary(
    reference: DatabaseRefV1, baseline: FinancialBaseline, now: datetime
) -> datetime:
    """Read exact persisted context timing; never change its scheduling policy."""
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )

    runs = SqliteCollectionRepositoryV1(reference)
    sample = _financial_sample(reference, baseline, now)
    snapshot = runs.read_budget_dispatch_snapshot(
        provider_key=sample.provider_key,
        capability_id=sample.capability_id,
        source_id=sample.source_id,
        manifest_fingerprint=sample.manifest_fingerprint,
        collection_policy_version=sample.collection_policy_version,
        operation_families=(sample.operation_family,),
        budget_scope_digests=(sample.budget_scope_digest,),
        schedule_ids=(sample.schedule_id,),
        as_of=now,
    )
    schedules = tuple(
        item for item in snapshot.schedules if item.schedule_id == sample.schedule_id
    )
    if len(schedules) != 1:
        raise ValueError("m7_financial_context_unavailable")
    timing = schedules[0]
    budget = runs.get_budget_next_allowed_at(
        sample.budget_scope_digest, "request", "count", now
    )
    return max(now, timing.next_due_at, timing.not_before_at or now, budget or now)


def _financial_baselines(reference: DatabaseRefV1) -> tuple[FinancialBaseline, ...]:
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.adapters.providers.ollama.api.manifest import ADAPTER_VERSION
    from agentmonitor.adapters.providers.ollama.api.policy import (
        SOURCE_ID,
        completed_period,
    )
    from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1

    now = datetime.now(UTC)
    selected: list[FinancialBaseline] = []
    runs = SqliteCollectionRepositoryV1(reference)
    for run in runs.list_runs("ollama", None, now, 500):
        if (
            not isinstance(run, BudgetCollectionRunViewV1)
            or run.state != "succeeded"
            or run.source_id != SOURCE_ID
            or run.adapter_version != ADAPTER_VERSION
        ):
            continue
        captured = runs.get_budget_target(run.run_id)
        if not isinstance(captured, tuple):
            continue
        graph, _, context = captured
        if any(
            item.graph.resource_id == graph.resource_id and item.context == context
            for item in selected
        ):
            continue
        baseline = _financial_snapshot(reference, run)
        if (
            not _financial_authority_current(reference, baseline)
            or baseline.stored.report.requested_period
            != completed_period(now, baseline.context.range_key)
            or baseline.context.scope != "self"
            or baseline.context.grouping
            or not baseline.stored.report.cost_buckets
        ):
            continue
        if any(
            item.graph.resource_id == baseline.graph.resource_id
            and item.context == baseline.context
            for item in selected
        ):
            continue
        if (
            run.schedule_id
            != _financial_sample(reference, baseline, run.requested_at).schedule_id
        ):
            continue
        selected.append(baseline)
    if not selected:
        raise ValueError("m7_financial_prior_monetary_report_required")
    return tuple(selected)


def _financial_retained(
    reference: DatabaseRefV1, baseline: FinancialBaseline, *, current: bool
) -> None:
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.contracts.capacity_v1 import BudgetCurrentQueryV1

    reports, runs = (
        SqliteBudgetReportRepositoryV1(reference),
        SqliteCollectionRepositoryV1(reference),
    )
    if (
        runs.get_run(baseline.run.run_id) != baseline.run
        or _financial_snapshot(reference, baseline.run) != baseline
    ):
        raise ValueError("m7_financial_retained_report_changed")
    if current:
        selected = reports.get_current_reports(
            BudgetCurrentQueryV1(
                baseline.graph.account_id,
                baseline.graph.resource_id,
                1,
                baseline.stored.report.requested_period,
                datetime.now(UTC),
                active_binding=baseline.graph.binding,
            )
        )
        if not any(item.current == baseline.stored for item in selected.items):
            raise ValueError("m7_financial_old_spend_not_current")


def _financial_monetary_turn(
    reference: DatabaseRefV1,
    baselines: tuple[FinancialBaseline, ...],
    now: datetime,
) -> bool:
    """Read the actual cloud order; never enqueue, register, recover or dispatch."""
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.composition.financial_dispatch import prepare_financial_dispatch
    from agentmonitor.composition.ollama_usage_inventory import read_usage_inventory
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    deadline = time.monotonic() + 30
    inventory = read_usage_inventory(
        reference,
        as_of=now,
        deadline_monotonic=deadline,
        scheduler_instance_id=OpaqueIdV1("financial-recovery-observer"),
    )
    work, _, scheduled = prepare_financial_dispatch(
        SqliteCollectionRepositoryV1(reference),
        None,
        inventory,
        deadline_monotonic=deadline,
        as_of=now,
    )
    monetary_keys = frozenset(
        key
        for key, run in scheduled.items()
        if any(
            (run.cloud_target, run.service_target, run.report_context)
            == (item.graph, item.service, item.context)
            for item in baselines
        )
    )
    return financial_has_next_turn(work, monetary_keys)


def observe_financial_recovery_interval(
    revision: str, attempt_id: str
) -> dict[str, object]:
    """One owned network-isolated financial worker, then passive natural recovery."""
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite import (
        ollama_cloud_admission,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.recovery import (
        SqliteCollectionRecoveryQueryV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.composition.billing_worker_supervisor import (
        BillingWorkerSupervisorV1,
    )
    from agentmonitor.composition.ollama_credential_operator import (
        selected_env_from_service,
    )
    from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    from tools.automation.implementations.m6_cutover import (
        _FIXED_UNIT,
        _cwd,
        _verify_retained_baseline,
    )
    from tools.automation.implementations.m6_recovery_interval import (
        DATA,
        _committed_in_interval,
        _dashboard_probe,
        _identity,
        _runs,
    )

    if (
        not isinstance(revision, str)
        or re.fullmatch(r"[a-f0-9]{40}", revision) is None
        or re.fullmatch(r"[a-f0-9]{32}", attempt_id) is None
    ):
        raise ValueError("m7_financial_input_invalid")
    result: dict[str, object] = {
        "record_type": "agentmonitor.m7_financial_recovery.v1",
        "isolation_scope": "owned_billing_worker_network",
        "status": "not_run",
        "reason_code": "m7_financial_failure_not_observed",
        "source_revision": revision,
        "attempt_id": attempt_id,
        "started_at": datetime.now(UTC).isoformat(),
    }
    stage = "preflight"
    try:
        runtime = Path(_cwd(_FIXED_UNIT))
        if _verify_retained_baseline(runtime)[0] != revision:
            raise ValueError("m7_financial_revision_mismatch")
        identity = _identity()
        result["service_invocation_id"] = identity.invocation_id
        reference = DatabaseRefV1(DATA / "agentmonitor.db", DATA)
        runs = SqliteCollectionRepositoryV1(reference)
        gate = ollama_cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
        baselines = _financial_baselines(reference)
        samples = [_dashboard_probe(revision)]
        env_file = selected_env_from_service(DATA)
        # Reserve only an idle worker slot, at most one existing worker interval
        # before eligibility. No worker starts before actual global/financial
        # allowance; waiting never reserves, refunds, or rewrites budget state.
        now = datetime.now(UTC)
        boundaries = [
            _financial_next_boundary(reference, item, now) for item in baselines
        ]
        wait_end = financial_observation_end(now, min(boundaries))
        worker = None
        failure_id = None
        stage = "admission"
        while datetime.now(UTC) < wait_end:
            # Yield between every attempt, including a declined monetary turn,
            # so the normal worker can serve the context that actually comes first.
            time.sleep(2)
            if _identity() != identity or not all(
                _financial_authority_current(reference, item) for item in baselines
            ):
                raise ValueError("m7_financial_authority_changed")
            now = datetime.now(UTC)
            ready_at = financial_slot_ready_at(
                now,
                gate.read_usage_gate_status(now),
                min(
                    _financial_next_boundary(reference, item, now) for item in baselines
                ),
            )
            reserve_seconds = BillingWorkerSupervisorV1._runtime_seconds
            if ready_at is not None and ready_at <= now + timedelta(
                seconds=reserve_seconds
            ):
                try:
                    with _supervisor_lock(DATA, financial=True) as descriptor:
                        reserve_end = min(
                            wait_end,
                            datetime.now(UTC) + timedelta(seconds=reserve_seconds),
                        )
                        print(
                            "M7 FINANCIAL RECOVERY: idle slot reserved; "
                            "waiting for existing allowance",
                            file=sys.stderr,
                            flush=True,
                        )
                        while datetime.now(UTC) < reserve_end:
                            if _identity() != identity or not all(
                                _financial_authority_current(reference, item)
                                for item in baselines
                            ):
                                raise ValueError("m7_financial_authority_changed")
                            now = datetime.now(UTC)
                            ready_at = financial_slot_ready_at(
                                now,
                                gate.read_usage_gate_status(now),
                                min(
                                    _financial_next_boundary(reference, item, now)
                                    for item in baselines
                                ),
                            )
                            if ready_at is not None and ready_at <= now:
                                break
                            time.sleep(0.25)
                        else:
                            continue
                        baselines = _financial_baselines(reference)
                        if not _financial_monetary_turn(
                            reference, baselines, datetime.now(UTC)
                        ):
                            continue
                        for item in baselines:
                            _financial_retained(reference, item, current=True)
                        samples.append(_dashboard_probe(revision))
                        if _identity() != identity:
                            raise ValueError("m7_financial_authority_changed")
                        isolation_start = datetime.now(UTC)
                        stage = "worker_start"
                        worker = _start_worker(
                            DATA,
                            env_file,
                            attempt_id,
                            descriptor,
                            financial=True,
                            runtime=runtime,
                        )
                        try:
                            assert (
                                worker.process.stdin is not None
                                and worker.process.stdout is not None
                            )
                            stage = "worker_collect"
                            worker.process.stdin.write(
                                f"GO {attempt_id}\nSTART {attempt_id}\n".encode()
                            )
                            worker.process.stdin.flush()
                            record = json.loads(
                                _line(worker.process.stdout.fileno(), 125)
                            )
                            if isinstance(record, dict):
                                for name in (
                                    "worker_exit_code",
                                    "matching_failure_count",
                                ):
                                    value = record.get(name)
                                    if type(value) is int and 0 <= value <= 255:
                                        print(
                                            json.dumps({"stage": stage, name: value}),
                                            file=sys.stderr,
                                            flush=True,
                                        )
                                if record.get("worker_exit_code") == 4:
                                    stderr_stream = worker.process.stderr
                                    if (
                                        stderr_stream is not None
                                        and select.select([stderr_stream], [], [], 1)[0]
                                    ):
                                        diagnostic = financial_worker_diagnostic(
                                            os.read(stderr_stream.fileno(), 4096)
                                        )
                                        if diagnostic is not None:
                                            print(
                                                diagnostic, file=sys.stderr, flush=True
                                            )
                            if (
                                not isinstance(record, dict)
                                or set(record) != {"failure_run_id"}
                                or not isinstance(record["failure_run_id"], str)
                                or worker.process.wait(timeout=5) != 0
                            ):
                                raise ValueError("m7_financial_failure_not_observed")
                            failure_id = OpaqueIdV1(record["failure_run_id"])
                        finally:
                            worker.close()
                            isolation_end = datetime.now(UTC)
                    break
                except BlockingIOError:
                    pass
        if worker is None or failure_id is None:
            return result
        failure = runs.get_run(failure_id)
        captured = runs.get_budget_target(failure_id)
        matching = [
            item
            for item in baselines
            if (item.graph, item.service, item.context) == captured
        ]
        if len(matching) != 1 or not isinstance(failure, BudgetCollectionRunViewV1):
            raise ValueError("m7_financial_failed_context_unavailable")
        prior = matching[0]
        kind = financial_attempt_kind(reference, failure)
        unknown_release = None
        if kind == "outcome_unknown":
            # A real lost response remains uncertain until the normal installed
            # reconciler expires its owner/lease and records the existing cooldown.
            stage = "uncertain_release"
            release_end = min(wait_end, datetime.now(UTC) + timedelta(seconds=480))
            while datetime.now(UTC) < release_end:
                if _identity() != identity or not _financial_authority_current(
                    reference, prior
                ):
                    raise ValueError("m7_financial_authority_changed")
                current_failure = runs.get_run(failure_id)
                if isinstance(current_failure, BudgetCollectionRunViewV1):
                    unknown_release = financial_unknown_release(
                        reference, current_failure
                    )
                    if unknown_release is not None:
                        failure = current_failure
                        break
                time.sleep(5)
            if unknown_release is None:
                raise ValueError("m7_financial_recovery_incomplete")
        if not (
            failure.state == "failed"
            and (
                (
                    kind == "provider_response"
                    and failure.error_code == "ollama_usage_provider_unavailable"
                )
                or (kind == "outcome_unknown" and unknown_release is not None)
            )
            and failure.report_id is None
            and failure.payload_digest is None
            and not failure.observation_ids
            and isolation_start <= failure.requested_at <= isolation_end
            and failure.schedule_id
            == _financial_sample(reference, prior, failure.requested_at).schedule_id
        ):
            raise ValueError("m7_financial_failure_invalid")
        _financial_retained(reference, prior, current=True)
        result.update(
            failure_kind=kind,
            failure_run_id=failure_id.value,
            old_report_id=prior.stored.report_id.value,
            old_payload_digest=prior.receipt.payload_digest,
            isolation_started_at=isolation_start.isoformat(),
            isolation_ended_at=isolation_end.isoformat(),
            namespace_cleanup_confirmed=True,
            namespace_pid=worker.pid,
            namespace_start_ticks=worker.start_ticks,
            parent_namespace_inode=worker.parent_namespace_inode,
            isolated_namespace_inode=worker.namespace_inode,
        )
        now = datetime.now(UTC)
        boundary = runs.get_budget_next_allowed_at(
            _financial_sample(reference, prior, now).budget_scope_digest,
            "request",
            "count",
            now,
        )
        if unknown_release is not None:
            result.update(
                uncertainty_released_at=unknown_release[0].isoformat(),
                uncertainty_next_allowed_at=unknown_release[1].isoformat(),
            )
            boundary = max(boundary or now, unknown_release[1])
        end = financial_observation_end(
            now, boundary, schedule_due=_financial_next_boundary(reference, prior, now)
        )
        repository = SqliteCollectionRecoveryQueryV1(reference)
        stage = "recovery"
        while datetime.now(UTC) < end:
            if _identity() != identity or not _financial_authority_current(
                reference, prior
            ):
                raise ValueError("m7_financial_authority_changed")
            _financial_retained(reference, prior, current=False)
            now = datetime.now(UTC)
            latest = runs.get_latest_budget_run(
                prior.graph.account_id,
                prior.graph.resource_id,
                1,
                now,
                report_context=prior.context,
            )
            other = [
                _committed_in_interval(
                    _runs(repository, provider, isolation_end, now), isolation_end
                )
                for provider in ("claude", "codex")
            ]
            if (
                latest is not None
                and latest.state == "succeeded"
                and latest.requested_at > isolation_end
                and latest.schedule_id == failure.schedule_id
                and (
                    unknown_release is None or latest.requested_at >= unknown_release[1]
                )
                and any(item is not None for item in other)
            ):
                recovered = _financial_snapshot(reference, latest)
                if (recovered.graph, recovered.service, recovered.context) != captured:
                    raise ValueError("m7_financial_recovery_context_changed")
                samples.append(_dashboard_probe(revision))
                if (
                    _identity() != identity
                    or _verify_retained_baseline(runtime)[0] != revision
                ):
                    raise ValueError("m7_financial_revision_mismatch")
                result.update(
                    status="passed",
                    reason_code="m7_financial_uncertain_source_recovered"
                    if unknown_release is not None
                    else "m7_financial_source_recovered",
                    recovery_run_id=latest.run_id.value,
                    recovery_report_id=recovered.stored.report_id.value,
                    recovery_payload_digest=recovered.receipt.payload_digest,
                    continuity_run_ids=[
                        item.run_id.value for item in other if item is not None
                    ],
                    dashboard_observed_at=[stamp.isoformat() for stamp in samples],
                )
                return result
            samples.append(_dashboard_probe(revision))
            time.sleep(10)
        result["reason_code"] = "m7_financial_recovery_incomplete"
    except (
        OSError,
        ValueError,
        RuntimeError,
        TimeoutError,
        subprocess.SubprocessError,
        KeyError,
        TypeError,
    ) as error:
        reason = "m7_financial_boundary_unavailable"

        if isinstance(error, ValueError) and str(error) in FINANCIAL_REASONS:
            reason = str(error)
        result.update(status="blocked", reason_code=reason, stage=stage)
        print(json.dumps(_diagnostic(error, stage)), file=sys.stderr, flush=True)
    finally:
        result["completed_at"] = datetime.now(UTC).isoformat()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isolated-worker", action="store_true")
    parser.add_argument("--financial", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--parent-namespace", type=int)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--revision")
    args = parser.parse_args()
    try:
        if args.isolated_worker:
            return _isolated_worker(args)
        result = (
            observe_financial_recovery_interval(args.revision, args.attempt_id)
            if args.financial
            else observe_controlled_recovery_interval(args.revision, args.attempt_id)
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "passed" else 3
    except (OSError, ValueError, TimeoutError):
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
