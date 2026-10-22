"""Pure trace policy and real-owner tests for M5 Codex containment evidence."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import inspect
import json
import os
import platform
import re
import resource
import select
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from tools.automation.implementations import m5_codex_containment as containment
from tools.automation.implementations.m5_codex_containment import (
    M5CodexContainmentErrorV1,
    M5CodexContainmentEvidenceV1,
    M5CodexContainmentUnavailableV1,
    _collect_driver_channels,
    _managed_profile_tree_digest,
    _open_private_channel,
    _process_start_ticks,
    _read_private_channel,
    _resolve_executable,
    _start_containment_process,
    _validate_selection,
    _validate_strace_executable,
    _write_private_channel,
    evaluate_codex_trace_policy_v1,
    verify_codex_managed_profile_containment_v1,
)

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_LIVE_SELECTORS = (
    "AGENTMONITOR_TEST_OWNER_DATA_ROOT",
    "AGENTMONITOR_TEST_CODEX_ACCOUNT_ID",
    "AGENTMONITOR_M5_OWNER_IMPLEMENTATION_REVISION",
    "AGENTMONITOR_M5_OWNER_SERVICE_PID",
    "AGENTMONITOR_M5_OWNER_SERVICE_START_TIME_TICKS",
)


_TRACE_EXECUTABLE = Path("/opt/codex/bin/codex")
_TRACE_MANAGED_ROOT = Path("/owner/profiles/codex/opaque")
_TRACE_CHMOD_TARGET = _TRACE_MANAGED_ROOT / "runtime" / "prepared"
_TRACE_APP_SERVER_ARGUMENTS = (
    "-c",
    'cli_auth_credentials_store="file"',
    "-c",
    "analytics.enabled=false",
    "-c",
    'otel.exporter="none"',
    "-c",
    'otel.trace_exporter="none"',
    "-c",
    'otel.metrics_exporter="none"',
    "-c",
    "otel.log_user_prompt=false",
    "app-server",
    "--listen",
    "stdio://",
)


def _trace_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _trace_exec(pid: int, executable: Path, arguments: tuple[str, ...]) -> str:
    argv = (os.fspath(executable), *arguments)
    return (
        f"{pid} execve({_trace_string(os.fspath(executable))}, "
        f"[{', '.join(_trace_string(value) for value in argv)}], 0x0) = 0"
    )


def _trace_version_exec(pid: int, executable: Path) -> str:
    return _trace_exec(pid, executable, ("--version",))


def _trace_app_server_exec(pid: int, executable: Path) -> str:
    return _trace_exec(pid, executable, _TRACE_APP_SERVER_ARGUMENTS)


def _driver_result_payload(state: str) -> bytes:
    """Return one exact structural driver result without provider content."""

    if state == "passed":
        identity_count = 1
        quota_count = 1
        identity_digest: str | None = "a" * 64
        bucket_count = 1
        window_count = 1
    elif state in {"failed", "unavailable"}:
        identity_count = 0
        quota_count = 0
        identity_digest = None
        bucket_count = 0
        window_count = 0
    else:
        raise ValueError("closed driver state required")
    return json.dumps(
        {
            "identity_binding_digest": identity_digest,
            "identity_operation_count": identity_count,
            "quota_bucket_count": bucket_count,
            "quota_operation_count": quota_count,
            "quota_window_count": window_count,
            "schema": "agentmonitor.m5-codex-containment-result.v1",
            "state": state,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _write_all(descriptor: int, payload: bytes) -> None:
    """Write structural test bytes through a real kernel descriptor."""

    written = 0
    while written < len(payload):
        count = os.write(descriptor, payload[written:])
        if count <= 0:
            raise OSError
        written += count


def _start_input_drain_process(
    input_descriptor: int,
    *,
    returncode: int,
) -> subprocess.Popen[bytes]:
    """Start a real child that drains one inherited pipe and exits exactly."""

    return subprocess.Popen(
        [
            "/usr/bin/python3",
            "-I",
            "-c",
            (
                "import os,sys\n"
                "fd=int(sys.argv[1])\n"
                "while os.read(fd,65536): pass\n"
                "raise SystemExit(int(sys.argv[2]))\n"
            ),
            str(input_descriptor),
            str(returncode),
        ],
        cwd="/",
        env={"LANG": "C.UTF-8"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        pass_fds=(input_descriptor,),
        shell=False,
        start_new_session=True,
    )


def _two_operation_chmod_trace(
    *,
    identity_chmod_count: int = 1,
    quota_chmod_count: int = 1,
) -> str:
    """Build one closed, sequential provider trace with configurable chmods."""

    lines = [
        _trace_version_exec(100, _TRACE_EXECUTABLE),
        "100 exit_group(0) = ?",
        _trace_app_server_exec(200, _TRACE_EXECUTABLE),
        "200 clone(child_stack=NULL, flags=SIGCHLD) = 201",
    ]
    lines.extend(
        f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        for _ in range(identity_chmod_count)
    )
    lines.extend(
        (
            "201 exit_group(0) = ?",
            "200 exit_group(0) = ?",
            _trace_app_server_exec(300, _TRACE_EXECUTABLE),
            "300 clone(child_stack=NULL, flags=SIGCHLD) = 301",
        )
    )
    lines.extend(
        f'301 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        for _ in range(quota_chmod_count)
    )
    lines.extend(("301 exit_group(0) = ?", "300 exit_group(0) = ?"))
    return "\n".join(lines)


class M5CodexContainmentPolicyTests(unittest.TestCase):
    def test_exact_two_app_server_lineage_chmods_are_admitted(self) -> None:
        """M5-CDX-GATE-001: one inode-bound chmod per operation is admitted."""

        summary = evaluate_codex_trace_policy_v1(
            _two_operation_chmod_trace(),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 2)
        self.assertEqual(summary.default_profile_access_count, 0)
        self.assertEqual(summary.default_profile_write_count, 0)

    def test_chmod_cardinality_and_lineage_fail_closed(self) -> None:
        """M5-CDX-GATE-001: the admitted chmod pattern is exact, not broad."""

        cases = {
            "zero": (0, 0),
            "one": (1, 0),
            "three": (2, 1),
            "both_in_identity_lineage": (2, 0),
        }
        for label, counts in cases.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1),
            ):
                evaluate_codex_trace_policy_v1(
                    _two_operation_chmod_trace(
                        identity_chmod_count=counts[0],
                        quota_chmod_count=counts[1],
                    ),
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )

    def test_chmod_shape_target_and_operation_matrix_fails_closed(self) -> None:
        """M5-CDX-GATE-001: no lexical or lineage variant widens chmod."""

        exact = f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        quota_exact = f'301 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        cases = {
            "different_target": _two_operation_chmod_trace().replace(
                quota_exact,
                f'301 chmod("{_TRACE_MANAGED_ROOT}/runtime/other", 0700) = 0',
            ),
            "failed": _two_operation_chmod_trace().replace(
                exact,
                f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = -1 EPERM (Operation not permitted)',
            ),
            "wrong_mode": _two_operation_chmod_trace().replace(
                exact,
                f'201 chmod("{_TRACE_CHMOD_TARGET}", 0600) = 0',
            ),
            "profile_root": _two_operation_chmod_trace().replace(
                exact,
                f'201 chmod("{_TRACE_MANAGED_ROOT}", 0700) = 0',
            ),
            "outside_root": _two_operation_chmod_trace().replace(
                exact,
                '201 chmod("/tmp/outside", 0700) = 0',
            ),
            "default_root": _two_operation_chmod_trace().replace(
                exact,
                '201 chmod("/home/owner/.codex/state", 0700) = 0',
            ),
            "relative": _two_operation_chmod_trace().replace(
                exact,
                '201 chmod("runtime/prepared", 0700) = 0',
            ),
            "dotdot": _two_operation_chmod_trace().replace(
                exact,
                f'201 chmod("{_TRACE_MANAGED_ROOT}/runtime/../prepared", 0700) = 0',
            ),
            "parser_suffix": _two_operation_chmod_trace().replace(
                exact,
                f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700, 0) = 0',
            ),
            "parser_prefix": _two_operation_chmod_trace().replace(
                exact,
                f'201 chmod(AT_FDCWD, "{_TRACE_CHMOD_TARGET}", 0700) = 0',
            ),
            "version_lineage": _two_operation_chmod_trace(
                identity_chmod_count=0
            ).replace(
                "100 exit_group(0) = ?",
                f'100 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0\n100 exit_group(0) = ?',
            ),
            "unattributed": (
                f'99 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0\n'
                + _two_operation_chmod_trace(identity_chmod_count=0)
            ),
            "overlap": _two_operation_chmod_trace().replace(
                "100 exit_group(0) = ?\n",
                "",
            ),
            "descendant_overlap": _two_operation_chmod_trace().replace(
                "201 exit_group(0) = ?\n",
                "",
            ),
            "ambiguous_child_pid": _two_operation_chmod_trace().replace(
                "200 clone(child_stack=NULL, flags=SIGCHLD) = 201",
                "200 clone(child_stack=NULL, flags=SIGCHLD) = ?",
            ),
            "unattributed_target_rename": (
                f'99 rename("{_TRACE_CHMOD_TARGET}", '
                f'"{_TRACE_CHMOD_TARGET}.old") = 0\n' + _two_operation_chmod_trace()
            ),
            "version_argv_suffix": _two_operation_chmod_trace().replace(
                _trace_version_exec(100, _TRACE_EXECUTABLE),
                _trace_exec(100, _TRACE_EXECUTABLE, ("--version", "extra")),
                1,
            ),
            "app_server_argv_suffix": _two_operation_chmod_trace().replace(
                _trace_app_server_exec(200, _TRACE_EXECUTABLE),
                _trace_exec(
                    200,
                    _TRACE_EXECUTABLE,
                    (*_TRACE_APP_SERVER_ARGUMENTS, "extra"),
                ),
                1,
            ),
        }
        for label, trace in cases.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1),
            ):
                evaluate_codex_trace_policy_v1(
                    trace,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )

    def test_root_exit_group_closes_only_its_thread_descendants(self) -> None:
        """M5-CDX-GATE-001: real provider threads need no individual exit."""

        trace = (
            _two_operation_chmod_trace()
            .replace(
                "200 clone(child_stack=NULL, flags=SIGCHLD) = 201",
                (
                    "200 clone(child_stack=NULL, "
                    "flags=CLONE_VM|CLONE_THREAD|SIGCHLD) = 201"
                ),
            )
            .replace(
                "201 exit_group(0) = ?\n",
                "",
                1,
            )
            .replace(
                "300 clone(child_stack=NULL, flags=SIGCHLD) = 301",
                (
                    "300 clone(child_stack=NULL, "
                    "flags=CLONE_VM|CLONE_THREAD|SIGCHLD) = 301"
                ),
            )
            .replace(
                "301 exit_group(0) = ?\n",
                "",
                1,
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)

    def test_namespace_and_other_mutators_fail_closed(self) -> None:
        """M5-CDX-GATE-001: replacement and namespace syscalls never pass."""

        target = os.fspath(_TRACE_CHMOD_TARGET)
        ancestor = os.fspath(_TRACE_MANAGED_ROOT / "runtime")
        operations = {
            "link": f'link("{target}", "{target}.link") = 0',
            "linkat": (
                f'linkat(AT_FDCWD, "{target}", AT_FDCWD, "{target}.link", 0) = 0'
            ),
            "symlink": f'symlink("prepared", "{target}.link") = 0',
            "symlinkat": (f'symlinkat("prepared", AT_FDCWD, "{target}.link") = 0'),
            "rename": f'rename("{target}", "{target}.old") = 0',
            "renameat": (
                f'renameat(AT_FDCWD, "{ancestor}", AT_FDCWD, "{ancestor}.old") = 0'
            ),
            "renameat2": (
                f'renameat2(AT_FDCWD, "{target}", AT_FDCWD, "{target}.old", 0) = 0'
            ),
            "unlink": f'unlink("{target}") = 0',
            "unlinkat": f'unlinkat(AT_FDCWD, "{ancestor}", AT_REMOVEDIR) = 0',
            "rmdir": f'rmdir("{ancestor}") = 0',
            "chown": f'chown("{target}", 1000, 1000) = 0',
            "lchown": f'lchown("{target}", 1000, 1000) = 0',
            "fchmod": "fchmod(9, 0700) = 0",
            "fchmodat": f'fchmodat(AT_FDCWD, "{target}", 0700) = 0',
            "fchown": "fchown(9, 1000, 1000) = 0",
            "ftruncate": "ftruncate(9, 0) = 0",
            "truncate": f'truncate("{target}", 0) = 0',
            "setxattr": (f'setxattr("{target}", "user.agentmonitor", "x", 1, 0) = 0'),
            "lsetxattr": (f'lsetxattr("{target}", "user.agentmonitor", "x", 1, 0) = 0'),
            "removexattr": f'removexattr("{target}", "user.agentmonitor") = 0',
            "lremovexattr": (f'lremovexattr("{target}", "user.agentmonitor") = 0'),
            "fsetxattr": 'fsetxattr(9, "user.agentmonitor", "x", 1, 0) = 0',
            "fremovexattr": 'fremovexattr(9, "user.agentmonitor") = 0',
            "futimesat": f'futimesat(AT_FDCWD, "{target}", NULL) = 0',
            "ioctl_fs_setflags": ("ioctl(9, FS_IOC_SETFLAGS, [FS_NODUMP_FL]) = 0"),
            "io_uring_setup": "io_uring_setup(8, 0x7f0000001000) = 9",
            "io_uring_enter": ("io_uring_enter(9, 1, 1, 0, 0x7f0000002000, 8) = 1"),
            "io_uring_register": ("io_uring_register(9, 0, 0x7f0000003000, 1) = 0"),
            "utimensat": (f'utimensat(AT_FDCWD, "{target}", NULL, 0) = 0'),
            "chroot": f'chroot("{ancestor}") = 0',
            "pivot_root": f'pivot_root("{ancestor}", "{target}") = 0',
            "mount": f'mount("none", "{ancestor}", "tmpfs", 0, NULL) = 0',
            "umount": f'umount("{ancestor}") = 0',
            "umount2": f'umount2("{ancestor}", 0) = 0',
            "open_tree": f'open_tree(AT_FDCWD, "{ancestor}", 0) = 9',
            "move_mount": (
                f'move_mount(AT_FDCWD, "{ancestor}", AT_FDCWD, "{target}", 0) = 0'
            ),
            "fsopen": 'fsopen("tmpfs", 0) = 9',
            "fsconfig": 'fsconfig(9, FSCONFIG_SET_STRING, "source", "none", 0) = 0',
            "fsmount": "fsmount(9, 0, 0) = 10",
            "fspick": f'fspick(AT_FDCWD, "{ancestor}", 0) = 9',
            "mount_setattr": (f'mount_setattr(AT_FDCWD, "{ancestor}", 0, NULL, 0) = 0'),
            "setns": "setns(9, CLONE_NEWNS) = 0",
            "unshare": "unshare(CLONE_NEWNS) = 0",
            "clone_newns": ("clone(child_stack=NULL, flags=CLONE_NEWNS|SIGCHLD) = 777"),
            "clone3_newns": "clone3({flags=CLONE_NEWNS}, 88) = 777",
        }
        anchor = f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        for label, operation in operations.items():
            trace = _two_operation_chmod_trace().replace(
                anchor,
                f"{anchor}\n201 {operation}",
            )
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1),
            ):
                evaluate_codex_trace_policy_v1(
                    trace,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )

    def test_raw_mutator_results_are_classified_globally(self) -> None:
        """M5-CDX-GATE-001: raw calls have one exact global result policy."""

        calls = {
            "fsetxattr": "fsetxattr(0x9, 0x1, 0x2, 0x1, 0) {result}",
            "fremovexattr": "fremovexattr(0x9, 0x1) {result}",
            "ioctl": "ioctl(0x9, 0x40086602, 0x1) {result}",
            "io_uring_setup": "io_uring_setup(0x8, 0x1) {result}",
            "io_uring_enter": ("io_uring_enter(0x9, 0x1, 0x1, 0, 0x1, 0x8) {result}"),
            "io_uring_register": ("io_uring_register(0x9, 0, 0x1, 0x1) {result}"),
        }
        first_exec = f'100 execve("{_TRACE_EXECUTABLE}"'
        provider_anchor = f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        closed_anchor = "200 exit_group(0) = ?"
        for name, template in calls.items():
            successful_results = ["= 0", "= 1"]
            if name == "io_uring_setup":
                successful_results.append("= 9<anon_inode:[io_uring]>")
            for successful_result in successful_results:
                successful = template.format(result=successful_result)
                for scope in ("driver", "provider"):
                    with self.subTest(
                        syscall=name,
                        result=successful_result,
                        scope=scope,
                    ):
                        trace = _two_operation_chmod_trace()
                        if scope == "driver":
                            trace = trace.replace(
                                first_exec,
                                f"99 {successful}\n{first_exec}",
                                1,
                            )
                        else:
                            trace = trace.replace(
                                provider_anchor,
                                f"{provider_anchor}\n201 {successful}",
                                1,
                            )
                        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                            evaluate_codex_trace_policy_v1(
                                trace,
                                provider_executable=_TRACE_EXECUTABLE,
                                managed_profile_root=_TRACE_MANAGED_ROOT,
                                default_codex_roots=(Path("/home/owner/.codex"),),
                            )
                        self.assertEqual(
                            str(raised.exception),
                            "m5_codex_containment_fd_write_unverifiable",
                        )

            with self.subTest(syscall=name, result="exact_failure"):
                failed = template.format(result="= -1 EBADF (Bad file descriptor)")
                trace = _two_operation_chmod_trace().replace(
                    provider_anchor,
                    f"{provider_anchor}\n201 {failed}",
                    1,
                )
                summary = evaluate_codex_trace_policy_v1(
                    trace,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )
                self.assertEqual(summary.provider_execution_count, 3)

            with self.subTest(syscall=name, result="failed_after_exit"):
                failed_after_exit = _two_operation_chmod_trace().replace(
                    closed_anchor,
                    f"{closed_anchor}\n200 {failed}",
                    1,
                )
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        failed_after_exit,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_trace_invalid",
                )

            malformed_results = [
                "= ?",
                "= 00",
                "= +1",
                "= 0 garbage",
                "= 0<>",
                "= -1 EBADF",
            ]
            if name != "io_uring_setup":
                malformed_results.append("= 1<unexpected>")
            for malformed_result in malformed_results:
                with self.subTest(syscall=name, result=malformed_result):
                    malformed = template.format(result=malformed_result)
                    trace = _two_operation_chmod_trace().replace(
                        provider_anchor,
                        f"{provider_anchor}\n201 {malformed}",
                        1,
                    )
                    with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                        evaluate_codex_trace_policy_v1(
                            trace,
                            provider_executable=_TRACE_EXECUTABLE,
                            managed_profile_root=_TRACE_MANAGED_ROOT,
                            default_codex_roots=(Path("/home/owner/.codex"),),
                        )
                    self.assertEqual(
                        str(raised.exception),
                        "m5_codex_containment_trace_invalid",
                    )

    def test_unattributed_namespace_changes_fail_closed(self) -> None:
        """M5-CDX-GATE-001: the trusted driver cannot change namespaces."""

        first = f'100 execve("{_TRACE_EXECUTABLE}"'
        cases = {
            "mount": '99 mount("none", "/tmp", "tmpfs", 0, NULL) = 0',
            "setns": "99 setns(9, CLONE_NEWNS) = 0",
            "unshare": "99 unshare(CLONE_NEWNS) = 0",
            "clone_newns": (
                "99 clone(child_stack=NULL, flags=CLONE_NEWNS|SIGCHLD) = 98"
            ),
        }
        for label, operation in cases.items():
            with self.subTest(label=label):
                trace = _two_operation_chmod_trace().replace(
                    first,
                    f"{operation}\n{first}",
                    1,
                )
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        trace,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_namespace_operation_rejected",
                )

    def test_unattributed_links_touching_chmod_target_fail_closed(self) -> None:
        """M5-CDX-GATE-001: driver links cannot replace target ancestry."""

        target = os.fspath(_TRACE_CHMOD_TARGET)
        ancestor = os.fspath(_TRACE_MANAGED_ROOT / "runtime")
        first = f'100 execve("{_TRACE_EXECUTABLE}"'
        cases = {
            "hardlink_target": f'99 link("{target}", "{target}.alias") = 0',
            "hardlink_ancestor": (f'99 link("{ancestor}", "{ancestor}.alias") = 0'),
            "symlink_target": f'99 symlink("prepared", "{target}") = 0',
            "symlink_ancestor": f'99 symlink("runtime", "{ancestor}") = 0',
        }
        for label, operation in cases.items():
            with self.subTest(label=label):
                trace = _two_operation_chmod_trace().replace(
                    first,
                    f"{operation}\n{first}",
                    1,
                )
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        trace,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_link_operation_rejected",
                )

    def test_child_pid_result_requires_exact_positive_decimal(self) -> None:
        """M5-CDX-GATE-001: clone results cannot contain parser ambiguity."""

        exact = "200 clone(child_stack=NULL, flags=SIGCHLD) = 201"
        cases = {
            "trailing": f"{exact} trailing",
            "prefix": exact.replace("= 201", "= child201"),
            "zero": exact.replace("= 201", "= 0"),
        }
        for label, replacement in cases.items():
            with self.subTest(label=label):
                trace = _two_operation_chmod_trace().replace(exact, replacement, 1)
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        trace,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_trace_invalid",
                )

    def test_chdir_requires_normalized_path_and_exact_success(self) -> None:
        """M5-CDX-GATE-001: cwd evidence is lexical and result exact."""

        first_app_server = _trace_app_server_exec(200, _TRACE_EXECUTABLE)
        managed = os.fspath(_TRACE_MANAGED_ROOT)
        cases = {
            "dotdot": f'200 chdir("/escape/../{managed.removeprefix("/")}") = 0',
            "double_slash": '200 chdir("/owner//profiles/codex/opaque") = 0',
            "ambiguous_result": f'200 chdir("{managed}") = ?',
        }
        for label, chdir in cases.items():
            with self.subTest(label=label):
                trace = _two_operation_chmod_trace().replace(
                    first_app_server,
                    f"{chdir}\n{first_app_server}",
                    1,
                )
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        trace,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_trace_invalid",
                )

    def test_clone_fs_child_chdir_changes_parent_cwd(self) -> None:
        """M5-CDX-GATE-001: a shared child cwd applies to its parent."""

        first_app_server = _trace_app_server_exec(200, _TRACE_EXECUTABLE)
        trace = _two_operation_chmod_trace().replace(
            first_app_server,
            (
                "200 clone(child_stack=NULL, flags=CLONE_FS|SIGCHLD) = 250\n"
                '250 chdir("/tmp") = 0\n'
                "250 exit_group(0) = ?\n"
                f"{first_app_server}"
            ),
            1,
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=_TRACE_EXECUTABLE,
                managed_profile_root=_TRACE_MANAGED_ROOT,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_working_directory_escape",
        )

    def test_clone_untraced_is_rejected_before_process_lineage_can_escape(
        self,
    ) -> None:
        """M5-CDX-GATE-001: every successful child remains in the trace."""

        first = f'100 execve("{_TRACE_EXECUTABLE}"'
        trace = _two_operation_chmod_trace().replace(
            first,
            f"99 clone(child_stack=NULL, flags=CLONE_UNTRACED|SIGCHLD) = 98\n{first}",
            1,
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=_TRACE_EXECUTABLE,
                managed_profile_root=_TRACE_MANAGED_ROOT,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_trace_invalid",
        )

    def test_relative_at_path_cannot_spoof_the_directory_descriptor(self) -> None:
        """M5-CDX-GATE-001: quoted AT_FDCWD text is never a dirfd token."""

        chmod = f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        trace = _two_operation_chmod_trace().replace(
            chmod,
            (
                '201 openat(AT_FDCWD, "/tmp", O_RDONLY|O_DIRECTORY) = 9</tmp>\n'
                '201 mkdirat(9</tmp>, "evil, AT_FDCWD,", 0700) = 0\n'
                f"{chmod}"
            ),
            1,
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=_TRACE_EXECUTABLE,
                managed_profile_root=_TRACE_MANAGED_ROOT,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_trace_invalid",
        )

    def test_app_server_exec_after_driver_cwd_escape_fails_closed(self) -> None:
        """M5-CDX-GATE-001: relative writes use the real inherited cwd."""

        trace = (
            _two_operation_chmod_trace()
            .replace(
                f'200 execve("{_TRACE_EXECUTABLE}"',
                f'200 chdir("/tmp") = 0\n200 execve("{_TRACE_EXECUTABLE}"',
                1,
            )
            .replace(
                f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0',
                (
                    '201 mkdir("escaped", 0700) = 0\n'
                    f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
                ),
                1,
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=_TRACE_EXECUTABLE,
                managed_profile_root=_TRACE_MANAGED_ROOT,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_working_directory_escape",
        )

    def test_provider_writes_inside_managed_profile_are_counted(self) -> None:
        """M5-CDX-GATE-001: exact child writes remain inside the selected root."""

        managed = Path("/owner/profiles/codex/opaque")
        executable = Path(
            "/home/owner/.codex/packages/standalone/releases/0.160.0/bin/codex"
        )
        trace = "\n".join(
            (
                '100 execve("/usr/bin/python3", ["python3"], 0x0) = 0',
                _trace_version_exec(101, executable),
                f'101 openat(AT_FDCWD, "{executable}", O_RDONLY) = 3<{executable}>',
                "101 exit_group(0) = ?",
                _trace_app_server_exec(102, executable),
                f'102 openat(AT_FDCWD, "{managed}/state.sqlite", O_RDWR|O_CREAT, 0600) = 4<{managed}/state.sqlite>',
                "102 clone(child_stack=NULL, flags=SIGCHLD) = 103",
                '103 mkdir("runtime", 0700) = 0',
                f'103 chmod("{managed}/runtime/prepared", 0700) = 0',
                "103 exit_group(0) = ?",
                "102 exit_group(0) = ?",
                _trace_app_server_exec(104, executable),
                f'104 newfstatat(AT_FDCWD, "{managed}/auth.json", {{st_mode=S_IFREG|0600}}, 0) = 0',
                f'104 chmod("{managed}/runtime/prepared", 0700) = 0',
                "104 exit_group(0) = ?",
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 4)
        self.assertGreaterEqual(summary.provider_access_count, 5)
        self.assertEqual(summary.default_profile_access_count, 0)
        self.assertEqual(summary.default_profile_write_count, 0)

    def test_default_profile_read_fails_closed(self) -> None:
        """M5-CDX-GATE-001: even a metadata read of default auth is rejected."""

        executable = Path("/opt/codex/bin/codex")
        trace = "\n".join(
            (
                _trace_version_exec(200, executable),
                _trace_app_server_exec(201, executable),
                '201 newfstatat(AT_FDCWD, "/home/owner/.codex/auth.json", {}, 0) = 0',
                _trace_app_server_exec(202, executable),
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=executable,
                managed_profile_root=Path("/owner/profiles/codex/opaque"),
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(
            str(raised.exception), "m5_codex_default_profile_access_detected"
        )
        self.assertIs(type(raised.exception), M5CodexContainmentErrorV1)

    def test_pre_exec_driver_default_profile_read_fails_closed(self) -> None:
        """M5-CDX-GATE-001: driver-side adapter reads are also contained."""

        executable = Path("/opt/codex/bin/codex")
        trace = "\n".join(
            (
                '250 newfstatat(AT_FDCWD, "/home/owner/.codex/auth.json", {}, 0) = 0',
                _trace_version_exec(250, executable),
                _trace_app_server_exec(251, executable),
                _trace_app_server_exec(252, executable),
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=executable,
                managed_profile_root=Path("/owner/profiles/codex/opaque"),
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(
            str(raised.exception), "m5_codex_default_profile_access_detected"
        )
        self.assertIs(type(raised.exception), M5CodexContainmentErrorV1)

    def test_provider_descendant_write_outside_managed_profile_fails_closed(
        self,
    ) -> None:
        """M5-CDX-GATE-001: provider descendants inherit the write boundary."""

        executable = Path("/opt/codex/bin/codex")
        trace = "\n".join(
            (
                _trace_version_exec(300, executable),
                "300 exit_group(0) = ?",
                _trace_app_server_exec(301, executable),
                "301 clone3({flags=CLONE_VM}, 88) = 302",
                '302 openat(AT_FDCWD, "/tmp/codex-state", O_WRONLY|O_CREAT, 0600) = 5</tmp/codex-state>',
                _trace_app_server_exec(303, executable),
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=executable,
                managed_profile_root=Path("/owner/profiles/codex/opaque"),
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(str(raised.exception), "m5_codex_managed_profile_write_escape")

    def test_unfinished_clone_activates_child_at_syscall_start(self) -> None:
        """M5-CDX-GATE-001: interleaved child activity cannot evade policy."""

        executable = Path("/opt/codex/bin/codex")
        trace = "\n".join(
            (
                _trace_version_exec(350, executable),
                "350 exit_group(0) = ?",
                _trace_app_server_exec(351, executable),
                "351 clone(child_stack=NULL, flags=SIGCHLD <unfinished ...>",
                '352 openat(AT_FDCWD, "/tmp/escaped", O_WRONLY|O_CREAT, 0600) = 5</tmp/escaped>',
                "351 <... clone resumed>) = 352",
                _trace_app_server_exec(353, executable),
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=executable,
                managed_profile_root=Path("/owner/profiles/codex/opaque"),
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(str(raised.exception), "m5_codex_managed_profile_write_escape")

    def test_non_provider_driver_write_is_not_attributed_to_codex(self) -> None:
        """M5-CDX-GATE-001: the private result write is outside provider counts."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                '400 openat(AT_FDCWD, "/owner/private/result.json", O_WRONLY|O_CREAT, 0600) = 3</owner/private/result.json>',
                _trace_version_exec(401, executable),
                "401 exit_group(0) = ?",
                _trace_app_server_exec(402, executable),
                f'402 openat(AT_FDCWD, "{managed}/state", O_RDWR|O_CREAT, 0600) = 4<{managed}/state>',
                f'402 chmod("{managed}/runtime/prepared", 0700) = 0',
                "402 exit_group(0) = ?",
                _trace_app_server_exec(403, executable),
                f'403 chmod("{managed}/runtime/prepared", 0700) = 0',
                "403 exit_group(0) = ?",
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_write_count, 3)

    def test_pre_exec_driver_filesystem_activity_is_not_attributed(self) -> None:
        """M5-CDX-GATE-001: a child becomes a provider only at exact exec."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                '500 chdir("/tmp/agentmonitor-codex-version") = 0',
                '500 openat(AT_FDCWD, "/tmp/driver-state", O_WRONLY|O_CREAT, 0600) = 4</tmp/driver-state>',
                _trace_version_exec(500, executable),
                "500 exit_group(0) = ?",
                f'501 chdir("{managed}") = 0',
                _trace_app_server_exec(501, executable),
                f'501 openat(AT_FDCWD, "{managed}/state", O_RDWR|O_CREAT, 0600) = 4<{managed}/state>',
                f'501 chmod("{managed}/runtime/prepared", 0700) = 0',
                "501 exit_group(0) = ?",
                _trace_app_server_exec(502, executable),
                f'502 chmod("{managed}/runtime/prepared", 0700) = 0',
                "502 exit_group(0) = ?",
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 3)

    def test_exited_provider_pid_is_not_attributed_after_reuse(self) -> None:
        """M5-CDX-GATE-001: process exit closes its provider attribution epoch."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                _trace_version_exec(550, executable),
                "550 exit_group(0) = ?",
                _trace_app_server_exec(551, executable),
                "551 exit_group(0) = ?",
                '551 openat(AT_FDCWD, "/tmp/reused-pid-state", O_WRONLY|O_CREAT, 0600) = 4</tmp/reused-pid-state>',
                _trace_app_server_exec(552, executable),
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=executable,
                managed_profile_root=managed,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(str(raised.exception), "m5_codex_containment_trace_invalid")

    def test_numeric_dirfd_relative_write_fails_closed(self) -> None:
        """M5-CDX-GATE-001: an unresolved dirfd cannot imply managed scope."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                _trace_version_exec(600, executable),
                "600 exit_group(0) = ?",
                _trace_app_server_exec(601, executable),
                '601 openat(9</outside>, "escaped", O_WRONLY|O_CREAT, 0600) = 5</outside/escaped>',
                _trace_app_server_exec(602, executable),
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1):
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=executable,
                managed_profile_root=managed,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

    def test_resolved_writable_open_symlink_escape_fails_closed(self) -> None:
        """M5-CDX-GATE-001: resolved descriptor targets govern containment."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                _trace_version_exec(700, executable),
                "700 exit_group(0) = ?",
                _trace_app_server_exec(701, executable),
                f'701 openat(AT_FDCWD</outside>, "{managed}/link/state", O_WRONLY|O_CREAT, 0600) = 5</outside/state>',
                _trace_app_server_exec(702, executable),
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=executable,
                managed_profile_root=managed,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(str(raised.exception), "m5_codex_managed_profile_write_escape")

    def test_path_following_mutator_is_rejected_without_a_resolved_target(self) -> None:
        """M5-CDX-GATE-001: lexical mutator paths cannot prove containment."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                _trace_version_exec(750, executable),
                "750 exit_group(0) = ?",
                _trace_app_server_exec(751, executable),
                f'751 truncate("{managed}/possible-link", 0) = 0',
                _trace_app_server_exec(752, executable),
            )
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                trace,
                provider_executable=executable,
                managed_profile_root=managed,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_path_mutator_unverifiable",
        )


class M5CodexContainmentPrerequisiteTests(unittest.TestCase):
    def test_containment_version_discovery_emits_no_unattributed_chmod(self) -> None:
        """M5-CDX-GATE-001: the traced driver adds no setup chmod record."""

        executable = _resolve_executable()
        source = (
            "from agentmonitor.adapters.providers.codex.installation "
            "import CodexInstallationUnavailable\n"
            "from tools.automation.implementations.m5_codex_containment "
            "import _discover_containment_installation_v1\n"
            "try:\n"
            "    installation=_discover_containment_installation_v1()\n"
            "except CodexInstallationUnavailable as error:\n"
            "    assert str(error) == 'codex_version_unverified'\n"
            "else:\n"
            "    assert installation.provider_version == '0.160.0'\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            trace_path = Path(raw) / "trace"
            process = subprocess.run(
                [
                    "/usr/bin/strace",
                    "--kill-on-exit",
                    "-f",
                    "-qq",
                    "-e",
                    "trace=execve,chmod",
                    "-e",
                    "signal=none",
                    "-o",
                    os.fspath(trace_path),
                    "--",
                    os.fspath(containment._BACKEND_PYTHON),
                    "-c",
                    source,
                ],
                cwd=containment.ROOT,
                env={
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "PATH": os.pathsep.join(
                        (
                            os.fspath(executable.launcher_directory),
                            "/usr/bin",
                            "/bin",
                        )
                    ),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": os.pathsep.join(
                        (
                            os.fspath(containment.ROOT),
                            os.fspath(containment.BACKEND_SOURCE),
                        )
                    ),
                },
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            observed = trace_path.read_text(encoding="utf-8")

        self.assertEqual(process.returncode, 0)
        self.assertNotIn(" chmod(", observed)
        version_execs = tuple(
            line
            for line in observed.splitlines()
            if f'execve("{executable.path}"' in line and '"--version"' in line
        )
        self.assertEqual(len(version_execs), 1)

    def test_exact_selector_records_invalid_namespace_syscalls(self) -> None:
        """M5-CDX-GATE-001: admitted strace observes every namespace seam."""

        self.assertEqual(
            (platform.system(), platform.machine()),
            ("Linux", "x86_64"),
        )
        containment._validate_strace_selector_v1()
        self.assertEqual(
            containment._STRACE_SELECTOR_V1,
            "trace=%file,%process,chdir,fchdir,fchmod,fchown,ftruncate,"
            "fallocate,fsetxattr,fremovexattr,ioctl,io_uring_setup,"
            "io_uring_enter,io_uring_register,clone,clone3,setns,unshare,"
            "chroot,pivot_root,mount,umount,umount2,open_tree,move_mount,"
            "fsopen,fsconfig,fsmount,fspick,mount_setattr",
        )
        self.assertEqual(
            containment._STRACE_RAW_V1,
            "raw=fsetxattr,fremovexattr,ioctl,io_uring_setup,io_uring_enter,"
            "io_uring_register",
        )
        syscall_numbers = {
            "io_uring_setup": (425, (0, 0)),
            "io_uring_enter": (426, (-1, 0, 0, 0, 0, 0)),
            "io_uring_register": (427, (-1, 0, 0, 0)),
            "clone": (56, (-1, 0, 0, 0, 0)),
            "pivot_root": (155, (0, 0)),
            "chroot": (161, (0,)),
            "mount": (165, (0, 0, 0, 0, 0)),
            "umount2": (166, (0, 0)),
            "unshare": (272, (-1,)),
            "setns": (308, (-1, 0)),
            "open_tree": (428, (-1, 0, 0)),
            "move_mount": (429, (-1, 0, -1, 0, 0)),
            "fsopen": (430, (0, 0)),
            "fsconfig": (431, (-1, 0, 0, 0, 0)),
            "fsmount": (432, (-1, 0, 0)),
            "fspick": (433, (-1, 0, 0)),
            "clone3": (435, (0, 0)),
            "mount_setattr": (442, (-1, 0, 0, 0, 0)),
        }
        calls = repr(tuple(syscall_numbers.values()))
        source = (
            "import ctypes\n"
            "libc=ctypes.CDLL(None,use_errno=True)\n"
            f"calls={calls}\n"
            "for number,arguments in calls:\n"
            "    libc.syscall(number,*arguments)\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            trace_path = Path(raw) / "trace"
            process = subprocess.run(
                [
                    "/usr/bin/strace",
                    "--kill-on-exit",
                    "-f",
                    "-qq",
                    "-e",
                    containment._STRACE_SELECTOR_V1,
                    "-e",
                    containment._STRACE_RAW_V1,
                    "-e",
                    "signal=none",
                    "-o",
                    os.fspath(trace_path),
                    "--",
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    source,
                ],
                cwd="/",
                env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            self.assertEqual(process.returncode, 0)
            observed = trace_path.read_text(encoding="utf-8")
        for name in syscall_numbers:
            with self.subTest(syscall=name):
                matching = tuple(
                    line for line in observed.splitlines() if f"{name}(" in line
                )
                self.assertTrue(matching)
                self.assertTrue(all(" = -1 " in line for line in matching))
        self.assertIn("umount", containment._STRACE_SELECTOR_V1.split(","))

    def test_exact_selector_records_fd_metadata_mutators(self) -> None:
        """M5-CDX-GATE-001: fd metadata writes cannot escape trace policy."""

        xattr_name = "user.agentmonitor_private_name"
        xattr_value = "PRIVATE_VALUE_1_12"
        source = (
            "import array,fcntl,os,sys\n"
            "descriptor=os.open(sys.argv[1],os.O_RDONLY|os.O_CLOEXEC)\n"
            "try:\n"
            f"    os.setxattr(descriptor,{xattr_name!r},{xattr_value.encode()!r})\n"
            f"    os.removexattr(descriptor,{xattr_name!r})\n"
            "    flags=array.array('L',[0])\n"
            "    fcntl.ioctl(descriptor,0x80086601,flags,True)\n"
            "    original=flags[0]\n"
            "    try:\n"
            "        flags[0]=original|0x40\n"
            "        fcntl.ioctl(descriptor,0x40086602,flags)\n"
            "    finally:\n"
            "        flags[0]=original\n"
            "        fcntl.ioctl(descriptor,0x40086602,flags)\n"
            "finally:\n"
            "    os.close(descriptor)\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            target.touch(mode=0o600)
            script = root / "probe.py"
            script.write_text(source, encoding="utf-8")
            trace_path = root / "trace"
            process = subprocess.run(
                [
                    "/usr/bin/strace",
                    "--kill-on-exit",
                    "-f",
                    "-qq",
                    "-e",
                    containment._STRACE_SELECTOR_V1,
                    "-e",
                    containment._STRACE_RAW_V1,
                    "-e",
                    "signal=none",
                    "-o",
                    os.fspath(trace_path),
                    "--",
                    "/usr/bin/python3",
                    "-I",
                    os.fspath(script),
                    os.fspath(target),
                ],
                cwd="/",
                env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            self.assertEqual(process.returncode, 0)
            observed = trace_path.read_text(encoding="utf-8")

        for name, marker in (
            ("fsetxattr", "fsetxattr("),
            ("fremovexattr", "fremovexattr("),
            ("ioctl_fs_setflags", "0x40086602"),
        ):
            with self.subTest(syscall=name):
                self.assertIn(marker, observed)
        self.assertNotIn(xattr_name, observed)
        self.assertNotIn(xattr_value, observed)
        self.assertNotIn("FS_IOC_SETFLAGS", observed)
        self.assertNotIn("FS_NODUMP_FL", observed)

    def test_exact_selector_exposes_clone_untraced_flag(self) -> None:
        """M5-CDX-GATE-001: an untraced child request is itself visible."""

        source = (
            "import ctypes,os,signal\n"
            "libc=ctypes.CDLL(None,use_errno=True)\n"
            "pid=libc.syscall(56,0x00800000|signal.SIGCHLD,0,0,0,0)\n"
            "if pid == 0:\n"
            "    os._exit(0)\n"
            "if pid < 0:\n"
            "    raise OSError(ctypes.get_errno(),'clone')\n"
            "os.waitpid(pid,0)\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            trace_path = Path(raw) / "trace"
            process = subprocess.run(
                [
                    "/usr/bin/strace",
                    "--kill-on-exit",
                    "-f",
                    "-yy",
                    "-qq",
                    "-s",
                    "4096",
                    "-e",
                    containment._STRACE_SELECTOR_V1,
                    "-e",
                    containment._STRACE_RAW_V1,
                    "-e",
                    "signal=none",
                    "-o",
                    os.fspath(trace_path),
                    "--",
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    source,
                ],
                cwd="/",
                env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            self.assertEqual(process.returncode, 0)
            observed = trace_path.read_text(encoding="utf-8")

        matching = tuple(
            line
            for line in observed.splitlines()
            if "clone(" in line and "CLONE_UNTRACED" in line
        )
        self.assertEqual(len(matching), 1)
        self.assertRegex(matching[0], r" = [1-9][0-9]*$")

    def test_selection_rejects_nonprivate_intermediate_profiles_root(self) -> None:
        """M5-CDX-GATE-001: every enclosing profile root remains private."""

        with tempfile.TemporaryDirectory() as raw:
            owner = Path(raw)
            owner.chmod(0o700)
            profiles_root = owner / "profiles"
            profiles_root.mkdir(mode=0o755)
            profiles_root.chmod(0o755)
            provider_root = profiles_root / "codex"
            provider_root.mkdir(mode=0o700)
            account_id = "account-one"
            managed = provider_root / hashlib.sha256(account_id.encode()).hexdigest()
            managed.mkdir(mode=0o700)

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _validate_selection(
                    owner_data_root=owner,
                    account_id=account_id,
                    managed_profiles_root=provider_root,
                    managed_profile_root=managed,
                    revision="a" * 40,
                    service_pid=os.getpid(),
                    service_start_time_ticks=_process_start_ticks(os.getpid()),
                )

            self.assertEqual(
                str(raised.exception), "m5_codex_containment_selection_invalid"
            )

    def test_external_signature_does_not_accept_an_identity_fingerprint(self) -> None:
        """M5-CDX-GATE-001: fresh identity binding stays inside traced work."""

        parameters = inspect.signature(
            verify_codex_managed_profile_containment_v1
        ).parameters

        self.assertNotIn("expected_identity_fingerprint", parameters)

        with tempfile.TemporaryDirectory() as raw:
            owner = Path(raw)
            owner.chmod(0o700)
            profiles_root = owner / "profiles"
            profiles_root.mkdir(mode=0o700)
            profiles = profiles_root / "codex"
            profiles.mkdir(mode=0o700)
            account_id = "account-one"
            managed = profiles / hashlib.sha256(account_id.encode()).hexdigest()
            managed.mkdir(mode=0o700)
            with self.assertRaises(M5CodexContainmentUnavailableV1) as raised:
                _validate_selection(
                    owner_data_root=owner,
                    account_id=account_id,
                    managed_profiles_root=profiles,
                    managed_profile_root=managed,
                    revision="a" * 40,
                    service_pid=os.getpid(),
                    service_start_time_ticks=_process_start_ticks(os.getpid()) + 1,
                )
        self.assertEqual(str(raised.exception), "m5_codex_containment_service_mismatch")

    def test_unsupported_platform_is_typed_unavailable(self) -> None:
        """M5-CDX-GATE-001: an unsupported host is a blocked prerequisite."""

        with self.assertRaises(M5CodexContainmentUnavailableV1) as raised:
            _resolve_executable(
                system_name="Darwin",
                machine_name="arm64",
                search_path="/usr/bin:/bin",
            )

        self.assertEqual(
            str(raised.exception), "m5_codex_containment_platform_unverified"
        )

    def test_missing_strace_is_typed_unavailable(self) -> None:
        """M5-CDX-GATE-001: an absent real tracer blocks containment."""

        with tempfile.TemporaryDirectory() as raw:
            missing = Path(raw) / "strace"
            with self.assertRaises(M5CodexContainmentUnavailableV1) as raised:
                _validate_strace_executable(missing)

        self.assertEqual(
            str(raised.exception), "m5_codex_containment_strace_unavailable"
        )

    def test_missing_executable_is_typed_unavailable(self) -> None:
        """M5-CDX-GATE-001: an absent real Codex binary blocks containment."""

        with (
            tempfile.TemporaryDirectory() as raw,
            self.assertRaises(M5CodexContainmentUnavailableV1) as raised,
        ):
            _resolve_executable(
                system_name="Linux",
                machine_name="x86_64",
                search_path=raw,
            )

        self.assertEqual(
            str(raised.exception), "m5_codex_containment_executable_unavailable"
        )

    def test_popen_unavailable_is_typed_unavailable(self) -> None:
        """M5-CDX-GATE-001: an OS launch refusal blocks containment."""

        with (
            tempfile.TemporaryDirectory() as raw,
            self.assertRaises(M5CodexContainmentUnavailableV1) as raised,
        ):
            _start_containment_process(
                ["/proc/self/status"],
                cwd=Path(raw),
                environment={"LANG": "C.UTF-8"},
                pass_fds=(),
            )

        self.assertEqual(
            str(raised.exception), "m5_codex_containment_driver_unavailable"
        )


class M5CodexContainmentPrivateChannelTests(unittest.TestCase):
    def test_inherited_channel_accepts_a_real_multidigit_descriptor(self) -> None:
        """M5-CDX-GATE-001: ordinary inherited fds above nine remain usable."""

        descriptors: list[int] = []
        variable = containment._RESULT_FD_ENV
        previous = os.environ.get(variable)
        try:
            while not descriptors or descriptors[-1] < 10:
                descriptors.extend(os.pipe2(os.O_CLOEXEC))
            selected = descriptors[-1]
            os.environ[variable] = str(selected)

            self.assertEqual(containment._inherited_descriptor(variable), selected)
            for invalid in ("0", "2", "03", "1000000", "-1", ""):
                with self.subTest(invalid=invalid):
                    os.environ[variable] = invalid
                    with self.assertRaises(M5CodexContainmentErrorV1):
                        containment._inherited_descriptor(variable)
        finally:
            if previous is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = previous
            for descriptor in descriptors:
                os.close(descriptor)

    def _collect_prefilled_channels(
        self,
        *,
        result_payload: bytes,
        trace_payload: bytes,
        returncode: int = 0,
        break_input: bool = False,
    ) -> tuple[int, bytes, bytes]:
        """Collect bounded bytes from real pipes around one real child."""

        input_reader, input_writer = _open_private_channel()
        result_reader, result_writer = _open_private_channel()
        trace_reader, trace_writer = _open_private_channel()
        process: subprocess.Popen[bytes] | None = None
        try:
            _write_all(result_writer, result_payload)
            os.close(result_writer)
            result_writer = -1
            _write_all(trace_writer, trace_payload)
            os.close(trace_writer)
            trace_writer = -1
            if break_input:
                os.close(input_reader)
                input_reader = -1
                process = subprocess.Popen(
                    ["/usr/bin/true"],
                    cwd="/",
                    env={"LANG": "C.UTF-8"},
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                    start_new_session=True,
                )
            else:
                process = _start_input_drain_process(
                    input_reader,
                    returncode=returncode,
                )
                os.close(input_reader)
                input_reader = -1
            owned_input_writer = input_writer
            input_writer = -1
            return _collect_driver_channels(
                process,
                input_descriptor=owned_input_writer,
                input_payload=b"selection",
                result_descriptor=result_reader,
                trace_descriptor=trace_reader,
            )
        finally:
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            for descriptor in (
                input_reader,
                input_writer,
                result_reader,
                result_writer,
                trace_reader,
                trace_writer,
            ):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

    def _collect_child_generated_trace(
        self,
        *,
        trace_size: int,
    ) -> tuple[int, bytes, bytes]:
        """Drain a child-generated trace that may exceed pipe capacity."""

        input_reader, input_writer = _open_private_channel()
        result_reader, result_writer = _open_private_channel()
        trace_reader, trace_writer = _open_private_channel()
        process: subprocess.Popen[bytes] | None = None
        result_payload = _driver_result_payload("passed")
        source = (
            "import os,sys\n"
            "input_fd,result_fd,trace_fd=map(int,sys.argv[1:4])\n"
            "result=bytes.fromhex(sys.argv[4])\n"
            "remaining=int(sys.argv[5])\n"
            "while os.read(input_fd,65536): pass\n"
            "os.write(result_fd,result)\n"
            "os.close(result_fd)\n"
            "chunk=b'T'*65536\n"
            "try:\n"
            "    while remaining:\n"
            "        part=chunk[:min(remaining,len(chunk))]\n"
            "        offset=0\n"
            "        while offset < len(part):\n"
            "            offset += os.write(trace_fd,part[offset:])\n"
            "        remaining -= len(part)\n"
            "except BrokenPipeError:\n"
            "    pass\n"
            "try: os.close(trace_fd)\n"
            "except OSError: pass\n"
        )
        try:
            process = subprocess.Popen(
                [
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    source,
                    str(input_reader),
                    str(result_writer),
                    str(trace_writer),
                    result_payload.hex(),
                    str(trace_size),
                ],
                cwd="/",
                env={"LANG": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(input_reader, result_writer, trace_writer),
                shell=False,
                start_new_session=True,
            )
            os.close(input_reader)
            input_reader = -1
            os.close(result_writer)
            result_writer = -1
            os.close(trace_writer)
            trace_writer = -1
            owned_input_writer = input_writer
            input_writer = -1
            return _collect_driver_channels(
                process,
                input_descriptor=owned_input_writer,
                input_payload=b"selection",
                result_descriptor=result_reader,
                trace_descriptor=trace_reader,
            )
        finally:
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            for descriptor in (
                input_reader,
                input_writer,
                result_reader,
                result_writer,
                trace_reader,
                trace_writer,
            ):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

    def test_empty_result_precedes_a_broken_input_channel(self) -> None:
        """M5-CDX-GATE-001: useful result EOF wins the closed precedence."""

        input_reader, input_writer = _open_private_channel()
        result_reader, result_writer = _open_private_channel()
        trace_reader, trace_writer = _open_private_channel()
        process: subprocess.Popen[bytes] | None = None
        try:
            os.close(input_reader)
            input_reader = -1
            os.close(result_writer)
            result_writer = -1
            _write_private_channel(trace_writer, b"safe trace", maximum=4096)
            os.close(trace_writer)
            trace_writer = -1
            process = subprocess.Popen(
                ["/usr/bin/true"],
                cwd="/",
                env={"LANG": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                start_new_session=True,
            )
            owned_input_writer = input_writer
            input_writer = -1

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _collect_driver_channels(
                    process,
                    input_descriptor=owned_input_writer,
                    input_payload=b"selection",
                    result_descriptor=result_reader,
                    trace_descriptor=trace_reader,
                )

            self.assertEqual(
                str(raised.exception),
                "m5_codex_containment_result_channel_empty",
            )
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for descriptor in (
                input_reader,
                input_writer,
                result_reader,
                result_writer,
                trace_reader,
                trace_writer,
            ):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

    def test_oversized_result_precedes_an_empty_trace_channel(self) -> None:
        """M5-CDX-GATE-001: result transport failure has closed precedence."""

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            self._collect_prefilled_channels(
                result_payload=b"R" * (4096 + 1),
                trace_payload=b"",
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_result_channel_invalid",
        )

    def test_empty_trace_precedes_a_malformed_result_schema(self) -> None:
        """M5-CDX-GATE-001: trace EOF precedes result schema validation."""

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            self._collect_prefilled_channels(
                result_payload=b"not-json",
                trace_payload=b"",
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_trace_channel_empty",
        )

    def test_oversized_trace_has_a_trace_specific_failure(self) -> None:
        """M5-CDX-GATE-001: trace overflow is bounded and classified."""

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            self._collect_child_generated_trace(trace_size=(16 * 1024 * 1024) + 1)

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_trace_channel_invalid",
        )

    def test_malformed_result_schema_precedes_a_broken_input(self) -> None:
        """M5-CDX-GATE-001: schema failure precedes the input outcome."""

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            self._collect_prefilled_channels(
                result_payload=b'{"schema":"wrong"}',
                trace_payload=b"safe trace",
                break_input=True,
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_result_invalid",
        )

    def test_result_schema_rejects_every_nonclosed_shape(self) -> None:
        """M5-CDX-GATE-001: result parsing admits only the closed schema."""

        extra_key = json.loads(_driver_result_payload("passed"))
        extra_key["extra"] = True
        nonzero_failure = json.loads(_driver_result_payload("failed"))
        nonzero_failure["identity_operation_count"] = 1
        passed_payload = _driver_result_payload("passed")
        cases = {
            "invalid_utf8": b"\xff",
            "non_object": b"[]",
            "extra_key": json.dumps(extra_key).encode("utf-8"),
            "nonzero_failure": json.dumps(nonzero_failure).encode("utf-8"),
            "duplicate_key": b'{"schema":"wrong",' + passed_payload[1:],
        }
        for label, payload in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    self._collect_prefilled_channels(
                        result_payload=payload,
                        trace_payload=b"safe trace",
                    )
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_result_invalid",
                )

    def test_broken_input_has_an_input_specific_failure(self) -> None:
        """M5-CDX-GATE-001: a closed selector reader is reported exactly."""

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            self._collect_prefilled_channels(
                result_payload=_driver_result_payload("passed"),
                trace_payload=b"safe trace",
                break_input=True,
            )

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_input_channel_invalid",
        )

    def test_driver_returncode_and_result_state_matrix_is_closed(self) -> None:
        """M5-CDX-GATE-001: only three exact rc/state pairs are meaningful."""

        cases = (
            (
                "unavailable",
                3,
                M5CodexContainmentUnavailableV1,
                "m5_codex_containment_provider_unavailable",
            ),
            (
                "failed",
                2,
                M5CodexContainmentErrorV1,
                "m5_codex_containment_operation_failed",
            ),
            (
                "failed",
                0,
                M5CodexContainmentErrorV1,
                "m5_codex_containment_driver_status_invalid",
            ),
            (
                "passed",
                2,
                M5CodexContainmentErrorV1,
                "m5_codex_containment_driver_status_invalid",
            ),
            (
                "passed",
                3,
                M5CodexContainmentErrorV1,
                "m5_codex_containment_driver_status_invalid",
            ),
            (
                "failed",
                4,
                M5CodexContainmentErrorV1,
                "m5_codex_containment_driver_status_invalid",
            ),
        )
        for state, returncode, error_type, code in cases:
            with self.subTest(state=state, returncode=returncode):
                with self.assertRaises(error_type) as raised:
                    self._collect_prefilled_channels(
                        result_payload=_driver_result_payload(state),
                        trace_payload=b"safe trace",
                        returncode=returncode,
                    )
                self.assertEqual(str(raised.exception), code)

    def test_result_and_trace_can_finish_in_either_order(self) -> None:
        """M5-CDX-GATE-001: channel settlement is completion-order independent."""

        result_payload = _driver_result_payload("passed")
        trace_payload = b"safe trace"
        source = (
            "import os,sys,time\n"
            "input_fd,result_fd,trace_fd=map(int,sys.argv[1:4])\n"
            "result=bytes.fromhex(sys.argv[4])\n"
            "trace=bytes.fromhex(sys.argv[5])\n"
            "order=sys.argv[6]\n"
            "first=(result_fd,result) if order=='result' else (trace_fd,trace)\n"
            "second=(trace_fd,trace) if order=='result' else (result_fd,result)\n"
            "os.write(first[0],first[1]); os.close(first[0])\n"
            "time.sleep(0.1)\n"
            "os.write(second[0],second[1]); os.close(second[0])\n"
            "while os.read(input_fd,65536): pass\n"
        )
        for order in ("result", "trace"):
            with self.subTest(order=order):
                input_reader, input_writer = _open_private_channel()
                result_reader, result_writer = _open_private_channel()
                trace_reader, trace_writer = _open_private_channel()
                process: subprocess.Popen[bytes] | None = None
                try:
                    process = subprocess.Popen(
                        [
                            "/usr/bin/python3",
                            "-I",
                            "-c",
                            source,
                            str(input_reader),
                            str(result_writer),
                            str(trace_writer),
                            result_payload.hex(),
                            trace_payload.hex(),
                            order,
                        ],
                        cwd="/",
                        env={"LANG": "C.UTF-8"},
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        pass_fds=(input_reader, result_writer, trace_writer),
                        shell=False,
                        start_new_session=True,
                    )
                    os.close(input_reader)
                    input_reader = -1
                    os.close(result_writer)
                    result_writer = -1
                    os.close(trace_writer)
                    trace_writer = -1
                    owned_input_writer = input_writer
                    input_writer = -1

                    returncode, observed_result, observed_trace = (
                        _collect_driver_channels(
                            process,
                            input_descriptor=owned_input_writer,
                            input_payload=b"selection",
                            result_descriptor=result_reader,
                            trace_descriptor=trace_reader,
                        )
                    )

                    self.assertEqual(returncode, 0)
                    self.assertEqual(observed_result, result_payload)
                    self.assertEqual(observed_trace, trace_payload)
                finally:
                    if process is not None and process.poll() is None:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except OSError:
                            pass
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            pass
                    for descriptor in (
                        input_reader,
                        input_writer,
                        result_reader,
                        result_writer,
                        trace_reader,
                        trace_writer,
                    ):
                        if descriptor >= 0:
                            try:
                                os.close(descriptor)
                            except OSError:
                                pass

    def test_all_late_channels_share_one_five_second_deadline(self) -> None:
        """M5-CDX-GATE-001: three late channels consume one bounded window."""

        input_reader, input_writer = _open_private_channel()
        result_reader, result_writer = _open_private_channel()
        trace_reader, trace_writer = _open_private_channel()
        process: subprocess.Popen[bytes] | None = None
        started = 0.0
        try:
            capacity = fcntl.fcntl(input_writer, fcntl.F_SETPIPE_SZ, 4096)
            input_payload = b"S" * (capacity + 1)
            process = subprocess.Popen(
                [
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    (
                        "import os,time\n"
                        "if os.fork()==0:\n"
                        "    time.sleep(8)\n"
                        "    os._exit(0)\n"
                        "os._exit(0)\n"
                    ),
                ],
                cwd="/",
                env={"LANG": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(input_reader, result_writer, trace_writer),
                shell=False,
                start_new_session=True,
            )
            os.close(input_reader)
            input_reader = -1
            os.close(result_writer)
            result_writer = -1
            os.close(trace_writer)
            trace_writer = -1
            owned_input_writer = input_writer
            input_writer = -1
            started = time.monotonic()

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _collect_driver_channels(
                    process,
                    input_descriptor=owned_input_writer,
                    input_payload=input_payload,
                    result_descriptor=result_reader,
                    trace_descriptor=trace_reader,
                )

            elapsed = time.monotonic() - started
            self.assertEqual(
                str(raised.exception),
                "m5_codex_containment_result_channel_invalid",
            )
            self.assertGreaterEqual(elapsed, 4.5)
            self.assertLess(elapsed, 7.5)
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                if process.poll() is None:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
            for descriptor in (
                input_reader,
                input_writer,
                result_reader,
                result_writer,
                trace_reader,
                trace_writer,
            ):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

    def test_driver_deadline_kills_and_reaps_the_real_process_group(self) -> None:
        """M5-CDX-GATE-001: row one wins on one short absolute deadline."""

        input_reader, input_writer = _open_private_channel()
        result_reader, result_writer = _open_private_channel()
        trace_reader, trace_writer = _open_private_channel()
        control_reader, control_writer = os.pipe2(os.O_CLOEXEC)
        process: subprocess.Popen[bytes] | None = None
        descendant_pidfd = -1
        transferred = (-1, -1, -1)
        started = 0.0
        try:
            source = (
                "import os,sys,time\n"
                "input_fd,result_fd,trace_fd,control_fd=map(int,sys.argv[1:5])\n"
                "child=os.fork()\n"
                "if child == 0:\n"
                "    os.close(control_fd)\n"
                "    time.sleep(30)\n"
                "    os._exit(0)\n"
                "os.write(control_fd,str(child).encode('ascii'))\n"
                "os.close(control_fd)\n"
                "time.sleep(30)\n"
            )
            process = subprocess.Popen(
                [
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    source,
                    str(input_reader),
                    str(result_writer),
                    str(trace_writer),
                    str(control_writer),
                ],
                cwd="/",
                env={"LANG": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(
                    input_reader,
                    result_writer,
                    trace_writer,
                    control_writer,
                ),
                shell=False,
                start_new_session=True,
            )
            os.close(input_reader)
            input_reader = -1
            os.close(result_writer)
            result_writer = -1
            os.close(trace_writer)
            trace_writer = -1
            os.close(control_writer)
            control_writer = -1
            descendant_pid = int(os.read(control_reader, 32).decode("ascii"))
            descendant_pidfd = os.pidfd_open(descendant_pid)
            transferred = (input_writer, result_reader, trace_reader)
            input_writer = result_reader = trace_reader = -1
            started = time.monotonic()

            with self.assertRaises(M5CodexContainmentUnavailableV1) as raised:
                containment._collect_driver_channels_until(
                    process,
                    input_descriptor=transferred[0],
                    input_payload=b"selection",
                    result_descriptor=transferred[1],
                    trace_descriptor=transferred[2],
                    driver_deadline_monotonic=started + 0.2,
                )

            elapsed = time.monotonic() - started
            self.assertEqual(
                str(raised.exception),
                "m5_codex_containment_driver_deadline_exceeded",
            )
            self.assertGreaterEqual(elapsed, 0.15)
            self.assertLess(elapsed, 2.0)
            self.assertIsNotNone(process.poll())
            readable, _, _ = select.select([descendant_pidfd], [], [], 2.0)
            self.assertEqual(readable, [descendant_pidfd])
            for descriptor in transferred:
                with self.assertRaises(OSError) as descriptor_error:
                    os.fstat(descriptor)
                self.assertEqual(descriptor_error.exception.errno, errno.EBADF)
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                if process.poll() is None:
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
            for descriptor in (
                input_reader,
                input_writer,
                result_reader,
                result_writer,
                trace_reader,
                trace_writer,
                control_reader,
                control_writer,
                descendant_pidfd,
                *transferred,
            ):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

    def test_private_channel_has_no_path_and_preserves_real_kernel_bytes(self) -> None:
        """M5-CDX-GATE-001: private transport is an inherited kernel channel."""

        payload = Path("/proc/sys/kernel/random/boot_id").read_bytes()
        reader, writer = _open_private_channel()
        try:
            self.assertRegex(
                os.readlink(f"/proc/self/fd/{reader}"), r"^pipe:\[[0-9]+\]$"
            )
            _write_private_channel(writer, payload, maximum=4096)
            os.close(writer)
            writer = -1
            self.assertEqual(
                _read_private_channel(reader, maximum=4096),
                payload,
            )
        finally:
            if writer >= 0:
                os.close(writer)
            os.close(reader)

    def test_driver_drains_a_reduced_capacity_input_channel_after_launch(
        self,
    ) -> None:
        """M5-CDX-GATE-001: a full selector pipe cannot block before launch."""

        payload = (
            Path("/proc/cpuinfo").read_bytes() + Path("/proc/self/maps").read_bytes()
        )[:8192]
        result_payload = _driver_result_payload("passed")
        input_reader, input_writer = _open_private_channel()
        result_reader, result_writer = _open_private_channel()
        trace_reader, trace_writer = _open_private_channel()
        try:
            capacity = fcntl.fcntl(input_writer, fcntl.F_SETPIPE_SZ, 4096)
            self.assertGreater(len(payload), capacity)
            _write_private_channel(result_writer, result_payload, maximum=4096)
            os.close(result_writer)
            result_writer = -1
            process = subprocess.Popen(
                ["/usr/bin/tee", f"/proc/self/fd/{trace_writer}"],
                cwd="/",
                env={"LANG": "C.UTF-8"},
                stdin=input_reader,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(trace_writer,),
                shell=False,
                start_new_session=True,
            )
            os.close(input_reader)
            input_reader = -1
            os.close(trace_writer)
            trace_writer = -1
            owned_input_writer = input_writer
            input_writer = -1
            owned_result_reader = result_reader
            result_reader = -1
            owned_trace_reader = trace_reader
            trace_reader = -1

            returncode, observed_result, observed_trace = _collect_driver_channels(
                process,
                input_descriptor=owned_input_writer,
                input_payload=payload,
                result_descriptor=owned_result_reader,
                trace_descriptor=owned_trace_reader,
            )

            self.assertEqual(returncode, 0)
            self.assertEqual(observed_result, result_payload)
            self.assertEqual(observed_trace, payload)
        finally:
            for descriptor in (
                input_reader,
                input_writer,
                result_reader,
                result_writer,
                trace_reader,
                trace_writer,
            ):
                if descriptor >= 0:
                    os.close(descriptor)

    def test_inherited_workspace_fd_survives_path_substitution(self) -> None:
        """M5-CDX-GATE-001: launch cwd remains the captured workspace inode."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            workspace = root / "workspace"
            workspace.mkdir(mode=0o700)
            descriptor = os.open(
                workspace,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            original = root / "original"
            workspace.rename(original)
            workspace.mkdir(mode=0o700)
            try:
                process = _start_containment_process(
                    [
                        "/usr/bin/python3",
                        "-c",
                        "from pathlib import Path; Path('marker').touch(mode=0o600)",
                    ],
                    cwd=Path(f"/proc/self/fd/{descriptor}"),
                    environment={"LANG": "C.UTF-8"},
                    pass_fds=(descriptor,),
                )
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertTrue((original / "marker").is_file())
                self.assertFalse((workspace / "marker").exists())
            finally:
                os.close(descriptor)

    def test_managed_profile_tree_rejects_a_real_symlink(self) -> None:
        """M5-CDX-GATE-001: profile metadata cannot redirect provider paths."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            outside = root / "outside"
            outside.mkdir(mode=0o700)
            (managed / "redirect").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _managed_profile_tree_digest(managed)

            self.assertEqual(
                str(raised.exception), "m5_codex_containment_profile_tree_invalid"
            )

    def test_managed_profile_tree_rejects_a_real_hardlink(self) -> None:
        """M5-CDX-GATE-001: a managed file cannot alias an outside inode."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            outside = root / "outside"
            outside.write_bytes(b"private")
            outside.chmod(0o600)
            os.link(outside, managed / "alias")

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _managed_profile_tree_digest(managed)

            self.assertEqual(
                str(raised.exception), "m5_codex_containment_profile_tree_invalid"
            )

    def test_managed_profile_tree_accepts_enclosed_provider_modes(self) -> None:
        """M5-CDX-GATE-001: private roots contain ordinary provider modes."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            cache = managed / "cache"
            cache.mkdir(mode=0o755)
            plugins = managed / "plugins"
            plugins.mkdir(mode=0o775)
            files = {
                managed / "read-only": 0o444,
                managed / "owner-state": 0o600,
                cache / "metadata": 0o644,
                plugins / "shared-metadata": 0o664,
                plugins / "launcher": 0o755,
            }
            for path, mode in files.items():
                path.write_bytes(b"provider metadata")
                path.chmod(mode)

            before = _managed_profile_tree_digest(managed)
            (cache / "metadata").chmod(0o664)
            after = _managed_profile_tree_digest(managed)

            self.assertRegex(before, _DIGEST)
            self.assertRegex(after, _DIGEST)
            self.assertNotEqual(before, after)

    def test_managed_profile_tree_rejects_special_permission_bits(self) -> None:
        """M5-CDX-GATE-001: special permission bits cannot enter evidence."""

        for mode in (0o4600, 0o2600, 0o1600):
            with tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                root.chmod(0o700)
                managed = root / "managed"
                managed.mkdir(mode=0o700)
                state = managed / "state"
                state.write_bytes(b"provider metadata")
                state.chmod(mode)

                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    _managed_profile_tree_digest(managed)

                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_profile_tree_invalid",
                )

    def test_managed_profile_tree_rejects_a_real_fifo(self) -> None:
        """M5-CDX-GATE-001: only regular files and directories are admitted."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            os.mkfifo(managed / "channel", mode=0o600)

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _managed_profile_tree_digest(managed)

            self.assertEqual(
                str(raised.exception), "m5_codex_containment_profile_tree_invalid"
            )

    def test_managed_profile_tree_rejects_owner_unsearchable_directory(self) -> None:
        """M5-CDX-GATE-001: every nested directory remains traversable."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            blocked = managed / "blocked"
            blocked.mkdir(mode=0o400)
            try:
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    _managed_profile_tree_digest(managed)
            finally:
                blocked.chmod(0o700)

            self.assertEqual(
                str(raised.exception), "m5_codex_containment_profile_tree_invalid"
            )

    def test_managed_profile_tree_rejects_nonprivate_selected_root(self) -> None:
        """M5-CDX-GATE-001: the selected enclosing root remains owner-only."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o755)

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _managed_profile_tree_digest(managed)

            self.assertEqual(
                str(raised.exception), "m5_codex_containment_profile_tree_invalid"
            )

    def test_managed_profile_tree_rejects_a_real_walk_error(self) -> None:
        """M5-CDX-GATE-001: an incomplete filesystem walk fails closed."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            state = managed / "state"
            state.write_bytes(b"provider metadata")
            state.chmod(0o600)
            original_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
            constrained_limit = (
                32
                if original_limit[0] == resource.RLIM_INFINITY
                else min(original_limit[0], 32)
            )
            descriptors: list[int] = []
            exhausted_errno: int | None = None
            outcome: str | None = None
            try:
                resource.setrlimit(
                    resource.RLIMIT_NOFILE,
                    (constrained_limit, original_limit[1]),
                )
                try:
                    while True:
                        descriptors.append(
                            os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
                        )
                except OSError as error:
                    exhausted_errno = error.errno
                try:
                    _managed_profile_tree_digest(managed)
                except M5CodexContainmentErrorV1 as error:
                    outcome = str(error)
            finally:
                for descriptor in descriptors:
                    os.close(descriptor)
                resource.setrlimit(resource.RLIMIT_NOFILE, original_limit)

            self.assertEqual(exhausted_errno, errno.EMFILE)
            self.assertEqual(outcome, "m5_codex_containment_profile_tree_invalid")

    def test_managed_profile_tree_rejects_more_than_ten_thousand_entries(
        self,
    ) -> None:
        """M5-CDX-GATE-001: an oversized real profile tree fails closed."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            for index in range(10_001):
                (managed / f"{index:05d}").touch(mode=0o600, exist_ok=False)

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _managed_profile_tree_digest(managed)

            self.assertEqual(
                str(raised.exception), "m5_codex_containment_profile_tree_invalid"
            )

    def test_managed_profile_tree_rejects_overlong_relative_path(self) -> None:
        """M5-CDX-GATE-001: an overlong real relative path fails closed."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            names: list[str] = []
            descriptors = [
                os.open(managed, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            ]
            try:
                for index in range(17):
                    name = f"{index:02d}" + ("x" * 239)
                    os.mkdir(name, mode=0o700, dir_fd=descriptors[-1])
                    descriptor = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
                        dir_fd=descriptors[-1],
                    )
                    names.append(name)
                    descriptors.append(descriptor)

                self.assertGreater(len(os.fsencode(Path(*names))), 4096)
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    _managed_profile_tree_digest(managed)

                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_profile_tree_invalid",
                )
            finally:
                for index in range(len(names) - 1, -1, -1):
                    os.close(descriptors[index + 1])
                    os.rmdir(names[index], dir_fd=descriptors[index])
                os.close(descriptors[0])

    def test_inode_bound_chmod_target_stays_pinned_through_post_scan(self) -> None:
        """M5-CDX-GATE-001: a real idempotent chmod is inode-bound."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            runtime = managed / "runtime"
            runtime.mkdir(mode=0o755)
            target = runtime / "prepared"
            target.mkdir(mode=0o700)

            snapshot = getattr(containment, "_managed_profile_tree_snapshot", None)
            open_root = getattr(containment, "_open_pinned_profile_root", None)
            open_target = getattr(
                containment,
                "_open_inode_bound_chmod_target",
                None,
            )
            validate_target = getattr(
                containment,
                "_validate_inode_bound_chmod",
                None,
            )
            self.assertTrue(callable(snapshot), "profile snapshot seam is required")
            self.assertTrue(callable(open_root), "pinned root seam is required")
            self.assertTrue(callable(open_target), "inode target seam is required")
            self.assertTrue(
                callable(validate_target), "post-scan validator is required"
            )

            before = snapshot(managed)
            root_descriptor, root_identity = open_root(managed)
            target_descriptor = -1
            try:
                before_ctime = target.stat().st_ctime_ns
                for _ in range(10):
                    os.chmod(target, 0o700)
                    if target.stat().st_ctime_ns > before_ctime:
                        break
                    time.sleep(0.001)
                self.assertGreater(target.stat().st_ctime_ns, before_ctime)
                target_descriptor, walked = open_target(
                    root_descriptor,
                    ("runtime", "prepared"),
                    before,
                )
                after = snapshot(managed, expected_root_identity=root_identity)
                validate_target(
                    target_descriptor,
                    ("runtime", "prepared"),
                    walked,
                    before,
                    after,
                )
            finally:
                if target_descriptor >= 0:
                    os.close(target_descriptor)
                os.close(root_descriptor)

    def test_inode_bound_walk_rejects_real_path_replacement(self) -> None:
        """M5-CDX-GATE-001: target, ancestor, symlink, and root swaps fail."""

        snapshot = containment._managed_profile_tree_snapshot
        open_root = containment._open_pinned_profile_root
        open_target = containment._open_inode_bound_chmod_target
        for replacement in ("target", "ancestor", "symlink", "root"):
            with (
                self.subTest(replacement=replacement),
                tempfile.TemporaryDirectory() as raw,
            ):
                root = Path(raw)
                root.chmod(0o700)
                managed = root / "managed"
                managed.mkdir(mode=0o700)
                runtime = managed / "runtime"
                runtime.mkdir(mode=0o755)
                target = runtime / "prepared"
                target.mkdir(mode=0o700)
                before = snapshot(managed)
                root_descriptor, root_identity = open_root(managed)
                try:
                    if replacement == "target":
                        target.rename(runtime / "old-target")
                        target.mkdir(mode=0o700)
                    elif replacement == "ancestor":
                        runtime.rename(managed / "old-runtime")
                        runtime.mkdir(mode=0o755)
                        target = runtime / "prepared"
                        target.mkdir(mode=0o700)
                    elif replacement == "symlink":
                        target.rename(runtime / "old-target")
                        target.symlink_to(
                            runtime / "old-target", target_is_directory=True
                        )
                    else:
                        managed.rename(root / "old-managed")
                        managed.mkdir(mode=0o700)

                    with self.assertRaises(M5CodexContainmentErrorV1):
                        if replacement == "root":
                            snapshot(
                                managed,
                                expected_root_identity=root_identity,
                            )
                        else:
                            open_target(
                                root_descriptor,
                                ("runtime", "prepared"),
                                before,
                            )
                finally:
                    os.close(root_descriptor)

    def test_inode_bound_post_validation_rejects_unchanged_or_wrong_metadata(
        self,
    ) -> None:
        """M5-CDX-GATE-001: ctime, mode, owner, and device stay closed."""

        snapshot = containment._managed_profile_tree_snapshot
        open_root = containment._open_pinned_profile_root
        open_target = containment._open_inode_bound_chmod_target
        validate = containment._validate_inode_bound_chmod
        for mutation in ("unchanged", "mode", "owner", "device"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                root.chmod(0o700)
                managed = root / "managed"
                managed.mkdir(mode=0o700)
                runtime = managed / "runtime"
                runtime.mkdir(mode=0o755)
                target = runtime / "prepared"
                target.mkdir(mode=0o700)
                before = snapshot(managed)
                root_descriptor, root_identity = open_root(managed)
                target_descriptor = -1
                try:
                    if mutation == "mode":
                        target.chmod(0o755)
                        with self.assertRaises(M5CodexContainmentErrorV1):
                            open_target(
                                root_descriptor,
                                ("runtime", "prepared"),
                                before,
                            )
                        continue
                    target_descriptor, walked = open_target(
                        root_descriptor,
                        ("runtime", "prepared"),
                        before,
                    )
                    after = snapshot(
                        managed,
                        expected_root_identity=root_identity,
                    )
                    if mutation in {"owner", "device"}:
                        system = Path("/proc" if mutation == "device" else "/").stat()
                        identities = list(after.directories)
                        selected = identities[-1]
                        identity_type = type(selected)
                        identities[-1] = identity_type(
                            selected.relative_parts,
                            system.st_dev if mutation == "device" else selected.device,
                            selected.inode,
                            system.st_uid
                            if mutation == "owner"
                            else selected.owner_uid,
                            selected.mode,
                            selected.changed_ns,
                        )
                        after = type(after)(after.digest, tuple(identities))
                    with self.assertRaises(M5CodexContainmentErrorV1):
                        validate(
                            target_descriptor,
                            ("runtime", "prepared"),
                            walked,
                            before,
                            after,
                        )
                finally:
                    if target_descriptor >= 0:
                        os.close(target_descriptor)
                    os.close(root_descriptor)

    def test_inode_bound_walk_uses_rolling_descriptors_without_leaks(self) -> None:
        """M5-CDX-GATE-001: a deep target needs only root/current/next fds."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            parts = tuple(f"d{index:02d}" for index in range(40))
            current = managed
            for part in parts:
                current /= part
                current.mkdir(mode=0o700)
            before = containment._managed_profile_tree_snapshot(managed)
            root_descriptor, _identity = containment._open_pinned_profile_root(managed)
            target_descriptor = -1
            original_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
            baseline = len(os.listdir("/proc/self/fd"))
            try:
                constrained = (
                    baseline + 3
                    if original_limit[0] == resource.RLIM_INFINITY
                    else min(original_limit[0], baseline + 3)
                )
                resource.setrlimit(
                    resource.RLIMIT_NOFILE,
                    (constrained, original_limit[1]),
                )
                target_descriptor, walked = containment._open_inode_bound_chmod_target(
                    root_descriptor,
                    parts,
                    before,
                )
                self.assertEqual(len(walked), len(parts))
                descriptor_flags = fcntl.fcntl(root_descriptor, fcntl.F_GETFD)
                self.assertTrue(descriptor_flags & fcntl.FD_CLOEXEC)
            finally:
                resource.setrlimit(resource.RLIMIT_NOFILE, original_limit)
                if target_descriptor >= 0:
                    os.close(target_descriptor)
                os.close(root_descriptor)
            self.assertLessEqual(len(os.listdir("/proc/self/fd")), baseline - 1)

    def test_pinned_descriptor_close_failure_is_sanitized(self) -> None:
        """M5-CDX-GATE-001: pin resource failures cannot produce evidence."""

        descriptor = os.open(
            "/",
            os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC,
        )
        os.close(descriptor)

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            containment._close_pinned_descriptor_v1(descriptor)

        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_path_mutator_unverifiable",
        )


class M5CodexContainmentLiveTests(unittest.TestCase):
    def test_real_authenticated_identity_and_quota_are_contained(self) -> None:
        """M5-CDX-GATE-001: trace both production operations for one real owner."""

        missing = tuple(name for name in _LIVE_SELECTORS if not os.environ.get(name))
        if missing:
            self.skipTest("BLOCKED: m5_codex_containment_live_selectors_required")

        owner_root = Path(os.environ["AGENTMONITOR_TEST_OWNER_DATA_ROOT"])
        account_id = os.environ["AGENTMONITOR_TEST_CODEX_ACCOUNT_ID"]
        managed_profiles_root = owner_root / "profiles" / "codex"
        managed_profile_root = (
            managed_profiles_root
            / hashlib.sha256(account_id.encode("utf-8")).hexdigest()
        )

        evidence = verify_codex_managed_profile_containment_v1(
            owner_data_root=owner_root,
            account_id=account_id,
            managed_profiles_root=managed_profiles_root,
            managed_profile_root=managed_profile_root,
            revision=os.environ["AGENTMONITOR_M5_OWNER_IMPLEMENTATION_REVISION"],
            service_pid=int(os.environ["AGENTMONITOR_M5_OWNER_SERVICE_PID"]),
            service_start_time_ticks=int(
                os.environ["AGENTMONITOR_M5_OWNER_SERVICE_START_TIME_TICKS"]
            ),
        )

        self.assertIsInstance(evidence, M5CodexContainmentEvidenceV1)
        self.assertIsNotNone(_DIGEST.fullmatch(evidence.evidence_digest))
        self.assertGreater(evidence.provider_access_count, 0)
        self.assertGreater(evidence.provider_write_count, 0)
        self.assertEqual(evidence.default_profile_access_count, 0)
        self.assertEqual(evidence.default_profile_write_count, 0)
        rendered = repr(evidence)
        self.assertNotIn(account_id, rendered)
        self.assertNotIn("/", rendered)


if __name__ == "__main__":
    unittest.main()
