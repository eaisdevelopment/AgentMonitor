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
import stat
import subprocess
import sys
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
_ARG0_ALIASES = (
    "apply_patch",
    "applypatch",
    "codex-linux-sandbox",
    "codex-execve-wrapper",
)
_ARG0_IDENTITY_SESSION = _TRACE_MANAGED_ROOT / "tmp" / "arg0" / "codex-arg0A1b2C3"
_ARG0_QUOTA_SESSION = _TRACE_MANAGED_ROOT / "tmp" / "arg0" / "codex-arg0D4e5F6"
_ARG0_LOCK_NAME = ".lock"
_ARG0_LOCK_FLAGS = "O_RDWR|O_CREAT|O_LARGEFILE|O_CLOEXEC"


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
    include_arg0: bool = True,
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
    trace = "\n".join(lines)
    return _add_arg0_lifecycle(trace) if include_arg0 else trace


def _arg0_link_lines(pid: int, session: Path) -> tuple[str, ...]:
    return tuple(
        f'{pid} symlink("{_TRACE_EXECUTABLE}", "{session / alias}") = 0'
        for alias in _ARG0_ALIASES
    )


def _arg0_cleanup_lines(
    pid: int,
    session: Path,
    *,
    aliases: tuple[str, ...] = _ARG0_ALIASES,
) -> tuple[str, ...]:
    return tuple(f'{pid} unlinkat(9<{session}>, "{alias}", 0) = 0' for alias in aliases)


def _arg0_session_and_lock_lines(pid: int, session: Path) -> tuple[str, str]:
    lock = session / _ARG0_LOCK_NAME
    return (
        f'{pid} mkdir("{session}", 0777) = 0',
        f'{pid} open("{lock}", {_ARG0_LOCK_FLAGS}, 0666) = 7<{lock}>',
    )


def _arg0_lock_cleanup_line(pid: int, session: Path) -> str:
    return f'{pid} unlinkat(9<{session}>, "{_ARG0_LOCK_NAME}", 0) = 0'


def _add_arg0_lifecycle(trace: str) -> str:
    """Build the exact session, lock, and four-alias Codex 0.160 lifecycle."""

    identity_session = _ARG0_IDENTITY_SESSION
    quota_session = _ARG0_QUOTA_SESSION
    trace = trace.replace(
        _trace_app_server_exec(200, _TRACE_EXECUTABLE),
        "\n".join(
            (
                _trace_app_server_exec(200, _TRACE_EXECUTABLE),
                *_arg0_session_and_lock_lines(200, identity_session),
                *_arg0_link_lines(200, identity_session),
            )
        ),
        1,
    )
    trace = trace.replace(
        "201 exit_group(0) = ?",
        "\n".join(
            (
                *_arg0_cleanup_lines(201, identity_session)[:3],
                _arg0_lock_cleanup_line(201, identity_session),
                *_arg0_cleanup_lines(201, identity_session)[3:],
                (
                    f"201 unlinkat(8<{identity_session.parent}>, "
                    f'"{identity_session.name}", AT_REMOVEDIR) = 0'
                ),
                "201 exit_group(0) = ?",
            )
        ),
        1,
    )
    trace = trace.replace(
        _trace_app_server_exec(300, _TRACE_EXECUTABLE),
        "\n".join(
            (
                _trace_app_server_exec(300, _TRACE_EXECUTABLE),
                *_arg0_session_and_lock_lines(300, quota_session),
                *_arg0_link_lines(300, quota_session),
            )
        ),
        1,
    )
    trace = trace.replace(
        "301 exit_group(0) = ?\n300 exit_group(0) = ?",
        "\n".join(
            (
                "301 exit_group(0) = ?",
                *_arg0_cleanup_lines(
                    300,
                    quota_session,
                    aliases=tuple(reversed(_ARG0_ALIASES)),
                )[:3],
                _arg0_lock_cleanup_line(300, quota_session),
                *_arg0_cleanup_lines(
                    300,
                    quota_session,
                    aliases=tuple(reversed(_ARG0_ALIASES)),
                )[3:],
                (
                    f"300 unlinkat(8<{quota_session.parent}>, "
                    f'"{quota_session.name}", AT_REMOVEDIR) = 0'
                ),
                "300 exit_group(0) = ?",
            )
        ),
        1,
    )
    return trace


def _arg0_lifecycle_trace() -> str:
    return _two_operation_chmod_trace()


def _trace_with_ftruncates(
    identity_record: str,
    quota_record: str,
) -> str:
    """Insert one descriptor-bound record into each provider lineage."""

    identity_anchor = f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
    quota_anchor = f'301 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
    return (
        _two_operation_chmod_trace()
        .replace(identity_anchor, f"{identity_anchor}\n201 {identity_record}", 1)
        .replace(quota_anchor, f"{quota_anchor}\n301 {quota_record}", 1)
    )


class M5CodexContainmentPolicyTests(unittest.TestCase):
    def test_arg0_pre_session_root_setup_precedes_protected_lifecycle(self) -> None:
        """M5-CDX-GATE-001: root setup remains outside the session interval."""

        trace = _arg0_lifecycle_trace()
        arg0_root = _ARG0_IDENTITY_SESSION.parent
        for root_pid, child_pid, session in (
            (200, 201, _ARG0_IDENTITY_SESSION),
            (300, 301, _ARG0_QUOTA_SESSION),
        ):
            old_chmod = f'{child_pid} chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
            session_mkdir = f'{root_pid} mkdir("{session}", 0777) = 0'
            root_setup = "\n".join(
                (
                    f'{root_pid} mkdir("{arg0_root}", 0777) = -1 EEXIST (File exists)',
                    f'{root_pid} chmod("{arg0_root}", 0700) = 0',
                    session_mkdir,
                )
            )
            trace = trace.replace(f"{old_chmod}\n", "", 1).replace(
                session_mkdir,
                root_setup,
                1,
            )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_access_count, 31)
        self.assertEqual(summary.provider_write_count, 28)

    def test_exact_arg0_session_lock_and_alias_lifecycle_is_admitted_once(
        self,
    ) -> None:
        """M5-CDX-GATE-001: the exact Arg0 session lifecycle is bounded."""

        executable = Path(
            "/home/owner/.codex/packages/standalone/releases/0.160.0/bin/codex"
        )
        trace = _arg0_lifecycle_trace().replace(
            os.fspath(_TRACE_EXECUTABLE),
            os.fspath(executable),
        )
        without_parent_removals = "\n".join(
            line for line in trace.splitlines() if "AT_REMOVEDIR" not in line
        )
        without_parents = evaluate_codex_trace_policy_v1(
            without_parent_removals,
            provider_executable=executable,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        rmdir_trace = trace.replace(
            (
                f"201 unlinkat(8<{_ARG0_IDENTITY_SESSION.parent}>, "
                f'"{_ARG0_IDENTITY_SESSION.name}", AT_REMOVEDIR) = 0'
            ),
            f'201 rmdir("{_ARG0_IDENTITY_SESSION}") = 0',
            1,
        ).replace(
            (
                f"300 unlinkat(8<{_ARG0_QUOTA_SESSION.parent}>, "
                f'"{_ARG0_QUOTA_SESSION.name}", AT_REMOVEDIR) = 0'
            ),
            f'300 rmdir("{_ARG0_QUOTA_SESSION}") = 0',
            1,
        )
        rmdir_summary = evaluate_codex_trace_policy_v1(
            rmdir_trace,
            provider_executable=executable,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        reused_session_trace = trace.replace(
            os.fspath(_ARG0_QUOTA_SESSION),
            os.fspath(_ARG0_IDENTITY_SESSION),
        ).replace(
            _ARG0_QUOTA_SESSION.name,
            _ARG0_IDENTITY_SESSION.name,
        )
        reused_session_summary = evaluate_codex_trace_policy_v1(
            reused_session_trace,
            provider_executable=executable,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(without_parents.provider_access_count, 27)
        self.assertEqual(without_parents.provider_write_count, 24)
        self.assertEqual(summary.provider_access_count, 29)
        self.assertEqual(summary.provider_write_count, 26)
        self.assertEqual(rmdir_summary, summary)
        self.assertEqual(reused_session_summary, summary)
        self.assertEqual(summary.default_profile_access_count, 0)
        self.assertEqual(summary.default_profile_write_count, 0)
        self.assertNotIn(os.fspath(executable), repr(summary))
        self.assertNotIn(os.fspath(_ARG0_IDENTITY_SESSION), repr(summary))

    def test_arg0_lock_cleanup_may_interleave_at_each_child_position(self) -> None:
        """M5-CDX-GATE-001: filesystem child enumeration order stays neutral."""

        trace = _arg0_lifecycle_trace()
        session = _ARG0_IDENTITY_SESSION
        lock_cleanup = _arg0_lock_cleanup_line(201, session)
        aliases = _arg0_cleanup_lines(201, session)
        without_lock = trace.replace(f"{lock_cleanup}\n", "", 1)
        for position in range(len(aliases) + 1):
            ordered = (*aliases[:position], lock_cleanup, *aliases[position:])
            candidate = without_lock.replace(
                "\n".join(aliases),
                "\n".join(ordered),
                1,
            )
            with self.subTest(position=position):
                summary = evaluate_codex_trace_policy_v1(
                    candidate,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )
                self.assertEqual(summary.provider_write_count, 26)

    def test_arg0_session_creation_shape_cardinality_and_chronology_close(
        self,
    ) -> None:
        """M5-CDX-GATE-001: each operation freshly creates one exact session."""

        trace = _arg0_lifecycle_trace()
        session = _ARG0_IDENTITY_SESSION
        mkdir = f'200 mkdir("{session}", 0777) = 0'
        lock = session / _ARG0_LOCK_NAME
        lock_open = f'200 open("{lock}", {_ARG0_LOCK_FLAGS}, 0666) = 7<{lock}>'
        identity_exec = _trace_app_server_exec(200, _TRACE_EXECUTABLE)
        first_link = _arg0_link_lines(200, session)[0]
        sibling_session = session.with_name("codex-arg0Z9y8X7")
        other_arg0_entry = session.parent / "other"
        without_mkdir = trace.replace(f"{mkdir}\n", "", 1)
        cases = {
            "missing": without_mkdir,
            "duplicate": trace.replace(mkdir, f"{mkdir}\n{mkdir}", 1),
            "mkdirat": trace.replace(
                mkdir,
                f'mkdirat(AT_FDCWD, "{session}", 0777) = 0'.join(("200 ", "")),
                1,
            ),
            "relative": trace.replace(
                mkdir, mkdir.replace(f'"{session}"', f'"{session.name}"'), 1
            ),
            "leading_double_slash": trace.replace(
                mkdir, mkdir.replace('"/owner', '"//owner'), 1
            ),
            "dot_path": trace.replace(
                mkdir, mkdir.replace("/arg0/codex-", "/arg0/./codex-"), 1
            ),
            "dotdot_path": trace.replace(
                mkdir, mkdir.replace("/arg0/codex-", "/arg0/other/../codex-"), 1
            ),
            "escaped_path": trace.replace(
                mkdir,
                mkdir.replace(
                    f'"{session}"',
                    r'"\057owner/profiles/codex/opaque/tmp/arg0/codex-arg0A1b2C3"',
                ),
                1,
            ),
            "control_path": trace.replace(
                mkdir, mkdir.replace("/codex-arg0A1b2C3", r"/codex-arg0A1b2\001"), 1
            ),
            "wrong_session": trace.replace(
                mkdir, mkdir.replace("codex-arg0A1b2C3", "codex-arg0Z9y8X7"), 1
            ),
            "wrong_mode": trace.replace(mkdir, mkdir.replace("0777", "0700"), 1),
            "failed": trace.replace(
                mkdir, mkdir.replace(" = 0", " = -1 EEXIST (File exists)"), 1
            ),
            "malformed_result": trace.replace(
                mkdir, mkdir.replace(" = 0", " = 0 trailing"), 1
            ),
            "extra_argument": trace.replace(
                mkdir, mkdir.replace(") = 0", ", 0) = 0"), 1
            ),
            "descendant": trace.replace(
                mkdir, mkdir.replace("200 mkdir", "201 mkdir"), 1
            ),
            "descendant_duplicate_eexist": trace.replace(
                first_link,
                f'{first_link}\n201 mkdir("{session}", 0777) = -1 EEXIST (File exists)',
                1,
            ),
            "foreign_operation": without_mkdir.replace(
                _trace_app_server_exec(300, _TRACE_EXECUTABLE),
                (
                    f"{_trace_app_server_exec(300, _TRACE_EXECUTABLE)}\n"
                    f"{mkdir.replace('200 mkdir', '300 mkdir', 1)}"
                ),
                1,
            ),
            "before_operation": without_mkdir.replace(
                identity_exec, f"{mkdir}\n{identity_exec}", 1
            ),
            "after_lock": without_mkdir.replace(lock_open, f"{lock_open}\n{mkdir}", 1),
            "after_alias": without_mkdir.replace(
                first_link, f"{first_link}\n{mkdir}", 1
            ),
            "unfinished": trace.replace(
                mkdir,
                mkdir.removesuffix(") = 0")
                + " <unfinished ...>\n200 <... mkdir resumed>) = 0",
                1,
            ),
            "sibling_create_remove_during_freshness": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 mkdir("{sibling_session}", 0777) = 0\n'
                    f'200 rmdir("{sibling_session}") = 0'
                ),
                1,
            ),
            "failed_wrong_session_during_freshness": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 mkdir("{sibling_session}", 0777) '
                    "= -1 EEXIST (File exists)"
                ),
                1,
            ),
            "other_entry_create_remove_during_freshness": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 mkdir("{other_arg0_entry}", 0777) = 0\n'
                    f'200 rmdir("{other_arg0_entry}") = 0'
                ),
                1,
            ),
            "exact_session_rmdir_during_freshness": trace.replace(
                mkdir,
                f'{mkdir}\n200 rmdir("{session}") = 0',
                1,
            ),
            "failed_exact_session_rmdir_during_freshness": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 rmdir("{session}") '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "failed_exact_session_child_mkdir_during_freshness": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 mkdir("{session / "child"}", 0777) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "failed_exact_session_rename_during_freshness": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 rename("{session}", "{session}.old") '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
        }
        for label, candidate in cases.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1),
            ):
                evaluate_codex_trace_policy_v1(
                    candidate,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )

    def test_arg0_lock_open_shape_cardinality_and_chronology_close(self) -> None:
        """M5-CDX-GATE-001: only one exact root-created regular lock is admitted."""

        trace = _arg0_lifecycle_trace()
        session = _ARG0_IDENTITY_SESSION
        lock = session / _ARG0_LOCK_NAME
        opened = f'200 open("{lock}", {_ARG0_LOCK_FLAGS}, 0666) = 7<{lock}>'
        first_link = _arg0_link_lines(200, session)[0]
        without_open = trace.replace(f"{opened}\n", "", 1)
        variants = {
            "missing": without_open,
            "duplicate": trace.replace(opened, f"{opened}\n{opened}", 1),
            "openat": trace.replace(
                opened, opened.replace('open("', 'openat(AT_FDCWD, "', 1), 1
            ),
            "creat": trace.replace(opened, f'200 creat("{lock}", 0666) = 7<{lock}>', 1),
            "relative": trace.replace(
                opened, opened.replace(f'"{lock}"', f'"{_ARG0_LOCK_NAME}"', 1), 1
            ),
            "leading_double_slash": trace.replace(
                opened, opened.replace('"/owner', '"//owner', 1), 1
            ),
            "wrong_name": trace.replace(
                opened, opened.replace("/.lock", "/lock", 1), 1
            ),
            "wrong_case": trace.replace(
                opened, opened.replace("/.lock", "/.LOCK", 1), 1
            ),
            "nested": trace.replace(
                opened, opened.replace("/.lock", "/nested/.lock", 1), 1
            ),
            "wrong_flags": trace.replace(
                opened, opened.replace("O_RDWR", "O_WRONLY", 1), 1
            ),
            "reordered_flags": trace.replace(
                opened,
                opened.replace(
                    _ARG0_LOCK_FLAGS, "O_CREAT|O_RDWR|O_LARGEFILE|O_CLOEXEC", 1
                ),
                1,
            ),
            "extra_flag": trace.replace(
                opened, opened.replace("O_CLOEXEC", "O_CLOEXEC|O_EXCL", 1), 1
            ),
            "wrong_mode": trace.replace(opened, opened.replace("0666", "0600", 1), 1),
            "failed": trace.replace(
                opened, opened.replace(f"7<{lock}>", "-1 EACCES (Permission denied)"), 1
            ),
            "missing_annotation": trace.replace(
                opened, opened.replace(f"7<{lock}>", "7"), 1
            ),
            "wrong_annotation": trace.replace(
                opened, opened.replace(f"7<{lock}>", f"7<{session / 'other'}>"), 1
            ),
            "deleted_annotation": trace.replace(
                opened, opened.replace(f"7<{lock}>", f"7<{lock} (deleted)>"), 1
            ),
            "descendant": trace.replace(
                opened, opened.replace("200 open", "201 open", 1), 1
            ),
            "foreign_operation": without_open.replace(
                _trace_app_server_exec(300, _TRACE_EXECUTABLE),
                (
                    f"{_trace_app_server_exec(300, _TRACE_EXECUTABLE)}\n"
                    f"{opened.replace('200 open', '300 open', 1)}"
                ),
                1,
            ),
            "after_alias": without_open.replace(
                first_link, f"{first_link}\n{opened}", 1
            ),
            "completion_after_alias": trace.replace(
                opened,
                opened.removesuffix(f") = 7<{lock}>") + " <unfinished ...>",
                1,
            ).replace(
                first_link, f"{first_link}\n200 <... open resumed>) = 7<{lock}>", 1
            ),
            "open_while_mkdir_unfinished": trace.replace(
                f'200 mkdir("{session}", 0777) = 0\n{opened}',
                (
                    f'200 mkdir("{session}", 0777 <unfinished ...>\n{opened}\n'
                    "200 <... mkdir resumed>) = 0"
                ),
                1,
            ),
            "nonregular_mkdir": trace.replace(
                opened, f'200 mkdir("{lock}", 0777) = 0', 1
            ),
            "nonregular_symlink": trace.replace(
                opened, f'200 symlink("{_TRACE_EXECUTABLE}", "{lock}") = 0', 1
            ),
            "nonregular_mknod": trace.replace(
                opened, f'200 mknod("{lock}", S_IFREG|0666) = 0', 1
            ),
        }
        for label, candidate in variants.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1),
            ):
                evaluate_codex_trace_policy_v1(
                    candidate,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )

    def test_arg0_lock_cleanup_shape_cardinality_lineage_and_order_close(self) -> None:
        """M5-CDX-GATE-001: the created lock has one bounded owned cleanup."""

        trace = _arg0_lifecycle_trace()
        session = _ARG0_IDENTITY_SESSION
        lock_cleanup = _arg0_lock_cleanup_line(201, session)
        last_link = _arg0_link_lines(200, session)[-1]
        parent = (
            f'201 unlinkat(8<{session.parent}>, "{session.name}", AT_REMOVEDIR) = 0'
        )
        without_cleanup = trace.replace(f"{lock_cleanup}\n", "", 1)
        cases = {
            "missing": without_cleanup,
            "duplicate": trace.replace(
                lock_cleanup, f"{lock_cleanup}\n{lock_cleanup}", 1
            ),
            "wrong_name": trace.replace(
                lock_cleanup, lock_cleanup.replace('".lock"', '"lock"'), 1
            ),
            "wrong_case": trace.replace(
                lock_cleanup, lock_cleanup.replace('".lock"', '".LOCK"'), 1
            ),
            "nested": trace.replace(
                lock_cleanup, lock_cleanup.replace('".lock"', '"nested/.lock"'), 1
            ),
            "absolute": trace.replace(
                lock_cleanup,
                lock_cleanup.replace('".lock"', f'"{session / _ARG0_LOCK_NAME}"'),
                1,
            ),
            "wrong_flags": trace.replace(
                lock_cleanup, lock_cleanup.replace(", 0) = 0", ", AT_REMOVEDIR) = 0"), 1
            ),
            "failed": trace.replace(
                lock_cleanup,
                lock_cleanup.replace(
                    " = 0", " = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "unresolved_dirfd": trace.replace(
                lock_cleanup, lock_cleanup.replace(f"9<{session}>", "9"), 1
            ),
            "descriptor_zero": trace.replace(
                lock_cleanup,
                lock_cleanup.replace(f"9<{session}>", f"0<{session}>", 1),
                1,
            ),
            "descriptor_one": trace.replace(
                lock_cleanup,
                lock_cleanup.replace(f"9<{session}>", f"1<{session}>", 1),
                1,
            ),
            "descriptor_two": trace.replace(
                lock_cleanup,
                lock_cleanup.replace(f"9<{session}>", f"2<{session}>", 1),
                1,
            ),
            "descriptor_leading_zero": trace.replace(
                lock_cleanup,
                lock_cleanup.replace(f"9<{session}>", f"09<{session}>", 1),
                1,
            ),
            "descriptor_overflow": trace.replace(
                lock_cleanup,
                lock_cleanup.replace(f"9<{session}>", f"1000000<{session}>", 1),
                1,
            ),
            "at_fdcwd": trace.replace(
                lock_cleanup,
                lock_cleanup.replace(f"9<{session}>", f"AT_FDCWD<{session}>", 1),
                1,
            ),
            "escaped_child": trace.replace(
                lock_cleanup, lock_cleanup.replace('".lock"', r'"\056lock"'), 1
            ),
            "wrong_session": trace.replace(
                lock_cleanup,
                lock_cleanup.replace(f"9<{session}>", f"9<{_ARG0_QUOTA_SESSION}>"),
                1,
            ),
            "unattributed": trace.replace(
                lock_cleanup, lock_cleanup.replace("201 unlinkat", "99 unlinkat", 1), 1
            ),
            "foreign_operation": without_cleanup.replace(
                "300 exit_group(0) = ?",
                (
                    f"{lock_cleanup.replace('201 unlinkat', '300 unlinkat', 1)}\n"
                    "300 exit_group(0) = ?"
                ),
                1,
            ),
            "before_aliases_complete": without_cleanup.replace(
                last_link,
                (
                    f"{lock_cleanup.replace('201 unlinkat', '200 unlinkat', 1)}\n"
                    f"{last_link}"
                ),
                1,
            ),
            "session_removed_before_lock": trace.replace(f"{parent}\n", "", 1).replace(
                lock_cleanup, f"{parent}\n{lock_cleanup}", 1
            ),
            "plain_unlink": trace.replace(
                lock_cleanup, f'201 unlink("{session / _ARG0_LOCK_NAME}") = 0', 1
            ),
            "after_actor_exit": without_cleanup.replace(
                "201 exit_group(0) = ?",
                f"201 exit_group(0) = ?\n{lock_cleanup}",
                1,
            ),
            "after_root_exit": without_cleanup.replace(
                "200 exit_group(0) = ?",
                (
                    "200 exit_group(0) = ?\n"
                    f"{lock_cleanup.replace('201 unlinkat', '200 unlinkat', 1)}"
                ),
                1,
            ),
            "completion_after_actor_exit": trace.replace(
                lock_cleanup,
                lock_cleanup.removesuffix(") = 0") + " <unfinished ...>",
                1,
            ).replace(
                "201 exit_group(0) = ?",
                "201 exit_group(0) = ?\n201 <... unlinkat resumed>) = 0",
                1,
            ),
            "completion_after_root_exit": trace.replace(
                lock_cleanup,
                lock_cleanup.replace("201 unlinkat", "200 unlinkat", 1).removesuffix(
                    ") = 0"
                )
                + " <unfinished ...>",
                1,
            ).replace(
                "200 exit_group(0) = ?",
                "200 exit_group(0) = ?\n200 <... unlinkat resumed>) = 0",
                1,
            ),
            "second_failed_cleanup": trace.replace(
                lock_cleanup,
                (
                    f"{lock_cleanup}\n"
                    f"{
                        lock_cleanup.replace(
                            ' = 0', ' = -1 ENOENT (No such file or directory)'
                        )
                    }"
                ),
                1,
            ),
            "parent_invoked_before_cleanup_completion": trace.replace(
                f"{parent}\n", "", 1
            ).replace(
                lock_cleanup,
                (
                    lock_cleanup.removesuffix(") = 0")
                    + f" <unfinished ...>\n{parent}\n"
                    + "201 <... unlinkat resumed>) = 0"
                ),
                1,
            ),
        }
        for label, candidate in cases.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1),
            ):
                evaluate_codex_trace_policy_v1(
                    candidate,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )

    def test_arg0_session_to_lock_open_interval_allows_no_other_write(self) -> None:
        """M5-CDX-GATE-001: fresh-session proof has a closed write interval."""

        trace = _arg0_lifecycle_trace()
        session = _ARG0_IDENTITY_SESSION
        mkdir = f'200 mkdir("{session}", 0777) = 0'
        lock = session / _ARG0_LOCK_NAME
        opened = f'200 open("{lock}", {_ARG0_LOCK_FLAGS}, 0666) = 7<{lock}>'
        sibling_lock = session.with_name("codex-arg0Z9y8X7") / _ARG0_LOCK_NAME
        other_operation_lock = _ARG0_QUOTA_SESSION / _ARG0_LOCK_NAME
        relative_lock = lock.relative_to(_TRACE_MANAGED_ROOT)
        proc_self_root_lock = Path(f"/proc/self/root{lock}")
        proc_thread_root_lock = Path(f"/proc/thread-self/root{lock}")
        proc_pid_root_lock = Path(f"/proc/200/root{lock}")
        proc_other_pid_root_lock = Path(f"/proc/999/root{lock}")
        proc_self_cwd_lock = Path("/proc/self/cwd") / relative_lock
        proc_thread_cwd_lock = Path("/proc/thread-self/cwd") / relative_lock
        proc_pid_cwd_lock = Path("/proc/200/cwd") / relative_lock
        proc_other_pid_cwd_lock = Path("/proc/999/cwd") / relative_lock
        proc_self_task_root_lock = Path(f"/proc/self/task/200/root{lock}")
        proc_pid_task_root_lock = Path(f"/proc/200/task/200/root{lock}")
        proc_fd_lock = Path("/proc/self/fd/9") / _ARG0_LOCK_NAME
        dev_fd_lock = Path("/dev/fd/9") / _ARG0_LOCK_NAME
        proc_root_parent_lock = Path(
            f"/proc/self/root/../{os.fspath(lock).lstrip('/')}"
        )
        proc_self_lock_descriptor = Path("/proc/self/fd/7")
        proc_thread_lock_descriptor = Path("/proc/thread-self/fd/7")
        proc_pid_lock_descriptor = Path("/proc/200/fd/7")
        proc_self_task_lock_descriptor = Path("/proc/self/task/200/fd/7")
        proc_pid_task_lock_descriptor = Path("/proc/200/task/200/fd/7")
        dev_lock_descriptor = Path("/dev/fd/7")
        proc_root_proc_lock_descriptor = Path("/proc/self/root/proc/self/fd/7")
        proc_root_dev_lock_descriptor = Path("/proc/self/root/dev/fd/7")
        proc_task_root_proc_lock_descriptor = Path(
            "/proc/self/task/200/root/proc/self/fd/7"
        )
        proc_pid_root_proc_lock_descriptor = Path("/proc/200/root/proc/200/fd/7")
        proc_lock_descriptor_info = Path("/proc/self/fdinfo/7")
        proc_lock_descriptor_leading_zero = Path("/proc/self/fd/07")
        proc_lock_descriptor_raw_parent = "/proc/self/fd/7/.."
        relative_proc_lock_descriptor = "../../../../proc/self/fd/7"
        relative_dev_lock_descriptor = "../../../../dev/fd/7"
        relative_proc_lock_descriptor_chain = "../../../../proc/self/fd/8/7"
        proc_lock_descriptor_proc_dot = "/proc/./self/fd/7"
        proc_lock_descriptor_actor_dot = "/proc/self/./fd/7"
        proc_lock_descriptor_task_parent = "/proc/self/task/../fd/7"
        dev_lock_descriptor_dev_dot = "/dev/./fd/7"
        raw_lock_child = f"{lock}/child"
        raw_lock_parent = f"{lock}/.."
        raw_lock_parent_sibling = f"{lock}/../other"
        raw_proc_root_lock_child = f"/proc/self/root{lock}/child"
        descriptor_directory_open = (
            '200 open("/proc/self/fd", O_RDONLY|O_DIRECTORY|O_CLOEXEC) '
            "= 8</proc/200/fd>"
        )
        dev_directory_open = (
            '200 open("/dev", O_RDONLY|O_DIRECTORY|O_CLOEXEC) = 8</dev>'
        )
        lock_cleanup = _arg0_lock_cleanup_line(201, session)
        outside = _TRACE_MANAGED_ROOT / "runtime" / "unexpected"
        overlapping_from_before = trace.replace(
            mkdir,
            f'200 mkdir("{outside}", 0700 <unfinished ...>\n{mkdir}',
            1,
        ).replace(opened, f"{opened}\n200 <... mkdir resumed>) = 0", 1)
        overlapping_after_open = trace.replace(
            mkdir,
            f'{mkdir}\n200 mkdir("{outside}", 0700 <unfinished ...>',
            1,
        ).replace(opened, f"{opened}\n200 <... mkdir resumed>) = 0", 1)
        overlapping_lock_descriptor_access = (
            trace.replace(
                _trace_app_server_exec(200, _TRACE_EXECUTABLE),
                (
                    f"{_trace_app_server_exec(200, _TRACE_EXECUTABLE)}\n"
                    "200 clone(child_stack=NULL, "
                    "flags=CLONE_VM|CLONE_FILES|SIGCHLD) = 202"
                ),
                1,
            )
            .replace(
                opened,
                (
                    opened.removesuffix(f") = 7<{lock}>") + " <unfinished ...>\n"
                    '202 newfstatat(AT_FDCWD, "/proc/200/fd/7", 0x0, 0) = 0\n'
                    f"200 <... open resumed>) = 7<{lock}>"
                ),
                1,
            )
            .replace(
                "200 exit_group(0) = ?",
                "202 exit_group(0) = ?\n200 exit_group(0) = ?",
                1,
            )
        )
        cases = {
            "complete_inside": trace.replace(
                mkdir, f'{mkdir}\n200 mkdir("{outside}", 0700) = 0', 1
            ),
            "failed_namespace_inside": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 rename("{outside}", "{outside}.moved") '
                    "= -1 EIO (Input/output error)"
                ),
                1,
            ),
            "failed_mkdir_inside": trace.replace(
                mkdir,
                f'{mkdir}\n200 mkdir("{outside}", 0700) = -1 EIO (Input/output error)',
                1,
            ),
            "failed_mkdirat_inside": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 mkdirat(AT_FDCWD, "{outside}", 0700) '
                    "= -1 EIO (Input/output error)"
                ),
                1,
            ),
            "failed_mknod_inside": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 mknod("{outside}", S_IFREG|0600) '
                    "= -1 EIO (Input/output error)"
                ),
                1,
            ),
            "failed_mknodat_inside": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 mknodat(AT_FDCWD, "{outside}", '
                    "S_IFREG|0600, 0) = -1 EIO (Input/output error)"
                ),
                1,
            ),
            "failed_open_create_inside": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 open("{outside}", O_WRONLY|O_CREAT|O_CLOEXEC, '
                    "0600) = -1 EIO (Input/output error)"
                ),
                1,
            ),
            "failed_openat_create_inside": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 openat(AT_FDCWD, "{outside}", '
                    "O_WRONLY|O_CREAT|O_CLOEXEC, 0600) = -1 EIO (Input/output error)"
                ),
                1,
            ),
            "failed_creat_inside": trace.replace(
                mkdir,
                f'{mkdir}\n200 creat("{outside}", 0600) = -1 EIO (Input/output error)',
                1,
            ),
            "invoked_before": overlapping_from_before,
            "completed_after": overlapping_after_open,
            "descriptor_access_during_unfinished_lock_open": (
                overlapping_lock_descriptor_access
            ),
            "extra_lock_read": trace.replace(
                opened,
                f'{opened}\n200 open("{lock}", O_RDONLY|O_CLOEXEC) = 8<{lock}>',
                1,
            ),
            "raw_lock_child_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{raw_lock_child}", '
                    "0x0, 0) = -1 ENOTDIR (Not a directory)"
                ),
                1,
            ),
            "raw_lock_parent_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{raw_lock_parent}", '
                    "0x0, 0) = -1 ENOTDIR (Not a directory)"
                ),
                1,
            ),
            "raw_lock_parent_sibling_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{raw_lock_parent_sibling}", '
                    "0x0, 0) = -1 ENOTDIR (Not a directory)"
                ),
                1,
            ),
            "raw_proc_root_lock_child_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{raw_proc_root_lock_child}", '
                    "0x0, 0) = -1 ENOTDIR (Not a directory)"
                ),
                1,
            ),
            "sibling_lock_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{sibling_lock}", '
                    "0x0, 0) = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "sibling_lock_read": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{sibling_lock}", O_RDONLY|O_CLOEXEC) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "other_operation_lock_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{other_operation_lock}", '
                    "0x0, 0) = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "other_operation_lock_read": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{other_operation_lock}", '
                    "O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_self_root_metadata_success": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{proc_self_root_lock}", '
                    "0x0, 0) = 0"
                ),
                1,
            ),
            "proc_self_root_metadata_failure": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{proc_self_root_lock}", '
                    "0x0, 0) = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_self_root_read_success": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{proc_self_root_lock}", O_RDONLY|O_CLOEXEC) '
                    f"= 8<{proc_self_root_lock}>"
                ),
                1,
            ),
            "proc_self_root_read_failure": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{proc_self_root_lock}", O_RDONLY|O_CLOEXEC) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_thread_root_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{proc_thread_root_lock}", '
                    "0x0, 0) = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_pid_root_read": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{proc_pid_root_lock}", O_RDONLY|O_CLOEXEC) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_self_cwd_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{proc_self_cwd_lock}", '
                    "0x0, 0) = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_thread_cwd_read": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{proc_thread_cwd_lock}", O_RDONLY|O_CLOEXEC) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_pid_cwd_read": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{proc_pid_cwd_lock}", O_RDONLY|O_CLOEXEC) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_other_pid_root_read": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{proc_other_pid_root_lock}", '
                    "O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_other_pid_cwd_read": trace.replace(
                opened,
                (
                    f'{opened}\n200 open("{proc_other_pid_cwd_lock}", '
                    "O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "proc_self_task_root_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{proc_self_task_root_lock}", '
                    "0x0, 0) = 0"
                ),
                1,
            ),
            "proc_pid_task_root_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{proc_pid_task_root_lock}", '
                    "0x0, 0) = 0"
                ),
                1,
            ),
            "proc_fd_metadata": trace.replace(
                opened,
                f'{opened}\n200 newfstatat(AT_FDCWD, "{proc_fd_lock}", 0x0, 0) = 0',
                1,
            ),
            "dev_fd_metadata": trace.replace(
                opened,
                f'{opened}\n200 newfstatat(AT_FDCWD, "{dev_fd_lock}", 0x0, 0) = 0',
                1,
            ),
            "proc_root_parent_metadata": trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(AT_FDCWD, "{proc_root_parent_lock}", '
                    "0x0, 0) = 0"
                ),
                1,
            ),
            "proc_self_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_self_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_thread_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_thread_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_pid_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_pid_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_self_task_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_self_task_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_pid_task_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_pid_task_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "dev_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{dev_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_root_proc_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_root_proc_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_root_dev_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_root_dev_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_task_root_proc_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_task_root_proc_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_pid_root_proc_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_pid_root_proc_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_lock_descriptor_info_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_lock_descriptor_info}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_lock_descriptor_leading_zero_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_lock_descriptor_leading_zero}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_lock_descriptor_raw_parent_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_lock_descriptor_raw_parent}", 0x0, 0) = 0'
                ),
                1,
            ),
            "relative_proc_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{relative_proc_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "relative_dev_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{relative_dev_lock_descriptor}", 0x0, 0) = 0'
                ),
                1,
            ),
            "relative_proc_lock_descriptor_directory_chain": trace.replace(
                opened,
                (
                    f"{opened}\n{descriptor_directory_open}\n"
                    "200 newfstatat(AT_FDCWD, "
                    f'"{relative_proc_lock_descriptor_chain}", '
                    "0x0, 0) = 0"
                ),
                1,
            ),
            "proc_lock_descriptor_directory_chain": trace.replace(
                opened,
                (
                    f"{opened}\n{descriptor_directory_open}\n"
                    '200 newfstatat(AT_FDCWD, "/proc/self/fd/8/7", '
                    "0x0, 0) = 0"
                ),
                1,
            ),
            "dev_lock_descriptor_directory_chain": trace.replace(
                opened,
                (
                    f"{opened}\n{descriptor_directory_open}\n"
                    '200 newfstatat(AT_FDCWD, "/dev/fd/8/7", 0x0, 0) = 0'
                ),
                1,
            ),
            **{
                f"proc_lock_descriptor_directory_stdio_{name}": trace.replace(
                    opened,
                    (
                        f"{opened.replace('= 7<', f'= {descriptor}<')}\n"
                        f"{dev_directory_open}\n"
                        f'200 newfstatat(AT_FDCWD, "/proc/self/fd/8/{name}", '
                        "0x0, 0) = 0"
                    ),
                    1,
                )
                for descriptor, name in enumerate(("stdin", "stdout", "stderr"))
            },
            **{
                f"dev_lock_descriptor_directory_stdio_{name}": trace.replace(
                    opened,
                    (
                        f"{opened.replace('= 7<', f'= {descriptor}<')}\n"
                        f"{dev_directory_open}\n"
                        f'200 newfstatat(AT_FDCWD, "/dev/fd/8/{name}", '
                        "0x0, 0) = 0"
                    ),
                    1,
                )
                for descriptor, name in enumerate(("stdin", "stdout", "stderr"))
            },
            "proc_lock_descriptor_proc_dot_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_lock_descriptor_proc_dot}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_lock_descriptor_actor_dot_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_lock_descriptor_actor_dot}", 0x0, 0) = 0'
                ),
                1,
            ),
            "proc_lock_descriptor_task_parent_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{proc_lock_descriptor_task_parent}", 0x0, 0) = 0'
                ),
                1,
            ),
            "dev_lock_descriptor_dev_dot_metadata": trace.replace(
                opened,
                (
                    f"{opened}\n200 newfstatat(AT_FDCWD, "
                    f'"{dev_lock_descriptor_dev_dot}", 0x0, 0) = 0'
                ),
                1,
            ),
            "dev_stdin_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened.replace('= 7<', '= 0<')}\n"
                    '200 newfstatat(AT_FDCWD, "/dev/stdin", 0x0, 0) = 0'
                ),
                1,
            ),
            "dev_stdout_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened.replace('= 7<', '= 1<')}\n"
                    '200 newfstatat(AT_FDCWD, "/dev/stdout", 0x0, 0) = 0'
                ),
                1,
            ),
            "dev_stderr_lock_descriptor_metadata": trace.replace(
                opened,
                (
                    f"{opened.replace('= 7<', '= 2<')}\n"
                    '200 newfstatat(AT_FDCWD, "/dev/stderr", 0x0, 0) = 0'
                ),
                1,
            ),
            "lock_descriptor_newfstatat_empty_path": trace.replace(
                opened,
                (f'{opened}\n200 newfstatat(7<{lock}>, "", 0x0, AT_EMPTY_PATH) = 0'),
                1,
            ),
            "lock_descriptor_statx_empty_path": trace.replace(
                opened,
                (
                    f'{opened}\n200 statx(7<{lock}>, "", AT_EMPTY_PATH, '
                    "STATX_BASIC_STATS, 0x0) = 0"
                ),
                1,
            ),
            "lock_descriptor_faccessat2_empty_path": trace.replace(
                opened,
                (f'{opened}\n200 faccessat2(7<{lock}>, "", F_OK, AT_EMPTY_PATH) = 0'),
                1,
            ),
            "lock_descriptor_newfstatat_null_path": trace.replace(
                opened,
                (f"{opened}\n200 newfstatat(7<{lock}>, NULL, 0x0, AT_EMPTY_PATH) = 0"),
                1,
            ),
            "lock_descriptor_statx_null_path": trace.replace(
                opened,
                (
                    f"{opened}\n200 statx(7<{lock}>, NULL, AT_EMPTY_PATH, "
                    "STATX_BASIC_STATS, 0x0) = 0"
                ),
                1,
            ),
            "lock_descriptor_readlinkat_empty_annotated": trace.replace(
                opened,
                (
                    f'{opened}\n200 readlinkat(7<{lock}>, "", 0x0, 4096) '
                    "= -1 EINVAL (Invalid argument)"
                ),
                1,
            ),
            "lock_descriptor_readlinkat_empty_unannotated": trace.replace(
                opened,
                (
                    f'{opened}\n200 readlinkat(7, "", 0x0, 4096) '
                    "= -1 EINVAL (Invalid argument)"
                ),
                1,
            ),
            "lock_annotation_over_other_descriptor_empty_path": trace.replace(
                opened,
                (f'{opened}\n200 newfstatat(8<{lock}>, "", 0x0, AT_EMPTY_PATH) = 0'),
                1,
            ),
            "lock_annotation_over_other_descriptor_direct": trace.replace(
                opened,
                (
                    f"{opened}\n200 fchmod(8<{lock}>, 0600) = -1 EPERM "
                    "(Operation not permitted)"
                ),
                1,
            ),
            "lock_alias_annotation_over_other_descriptor": trace.replace(
                opened,
                (
                    f"{opened}\n200 fchmod(8</proc/self/fd/7>, 0600) "
                    "= -1 EPERM (Operation not permitted)"
                ),
                1,
            ),
            "deleted_lock_annotation_after_cleanup": trace.replace(
                lock_cleanup,
                (
                    f"{lock_cleanup}\n200 fchmod(7<{lock} (deleted)>, 0600) "
                    "= -1 EPERM (Operation not permitted)"
                ),
                1,
            ),
            "lock_metadata_during_freshness": trace.replace(
                mkdir,
                (
                    f'{mkdir}\n200 newfstatat(AT_FDCWD, "{lock}", 0x0, 0) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            "lock_replacement": trace.replace(
                opened, f'{opened}\n200 rename("{lock}", "{session / "moved"}") = 0', 1
            ),
            "lock_ftruncate": trace.replace(
                opened, f"{opened}\n200 ftruncate(7<{lock}>, 0) = 0", 1
            ),
            "failed_lock_descriptor_ftruncate": trace.replace(
                opened,
                (
                    f"{opened}\n200 ftruncate(7<{lock}>, 0) = -1 EPERM "
                    "(Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_fchmod": trace.replace(
                opened,
                (
                    f"{opened}\n200 fchmod(7<{lock}>, 0600) = -1 EPERM "
                    "(Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_fchown": trace.replace(
                opened,
                (
                    f"{opened}\n200 fchown(7<{lock}>, 1000, 1000) = -1 EPERM "
                    "(Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_fallocate": trace.replace(
                opened,
                (
                    f"{opened}\n200 fallocate(7<{lock}>, 0, 0, 1) = -1 EPERM "
                    "(Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_fchdir": trace.replace(
                opened,
                (f"{opened}\n200 fchdir(7<{lock}>) = -1 ENOTDIR (Not a directory)"),
                1,
            ),
            "failed_lock_descriptor_fsetxattr": trace.replace(
                opened,
                (
                    f'{opened}\n200 fsetxattr(0x7, "user.agentmonitor", '
                    '"x", 1, 0) = -1 EPERM (Operation not permitted)'
                ),
                1,
            ),
            "failed_lock_descriptor_fremovexattr": trace.replace(
                opened,
                (
                    f'{opened}\n200 fremovexattr(0x7, "user.agentmonitor") '
                    "= -1 EPERM (Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_ioctl": trace.replace(
                opened,
                (
                    f"{opened}\n200 ioctl(0x7, 0x40086602, 0x0) = -1 EPERM "
                    "(Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_io_uring_enter": trace.replace(
                opened,
                (
                    f"{opened}\n200 io_uring_enter(0x7, 0x1, 0x1, 0x0, "
                    "0x0, 0x0) = -1 EPERM (Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_io_uring_register": trace.replace(
                opened,
                (
                    f"{opened}\n200 io_uring_register(0x7, 0x0, 0x0, 0x0) "
                    "= -1 EPERM (Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_setns": trace.replace(
                opened,
                (
                    f"{opened}\n200 setns(7<{lock}>, CLONE_NEWNS) = -1 EPERM "
                    "(Operation not permitted)"
                ),
                1,
            ),
            "failed_lock_descriptor_fsconfig": trace.replace(
                opened,
                (
                    f"{opened}\n200 fsconfig(7<{lock}>, FSCONFIG_SET_STRING, "
                    '"source", "none", 0) = -1 EPERM (Operation not permitted)'
                ),
                1,
            ),
            "failed_lock_descriptor_fsmount": trace.replace(
                opened,
                (
                    f"{opened}\n200 fsmount(7<{lock}>, 0, 0) = -1 EPERM "
                    "(Operation not permitted)"
                ),
                1,
            ),
            "lock_descriptor_clone3_cgroup_annotation": trace.replace(
                opened,
                (
                    f"{opened}\n200 clone3({{flags=CLONE_INTO_CGROUP, "
                    f"exit_signal=SIGCHLD, cgroup=7<{lock}>}}, 88) = -1 EBADF "
                    "(Bad file descriptor)"
                ),
                1,
            ),
            "lock_descriptor_clone3_cgroup_unannotated": trace.replace(
                opened,
                (
                    f"{opened}\n200 clone3({{flags=CLONE_INTO_CGROUP, "
                    "exit_signal=SIGCHLD, cgroup=7}, 88) = -1 EBADF "
                    "(Bad file descriptor)"
                ),
                1,
            ),
            "lock_descriptor_mount_setattr_userns_annotation": trace.replace(
                opened,
                (
                    f'{opened}\n200 mount_setattr(AT_FDCWD, "{_TRACE_MANAGED_ROOT}", '
                    f"0, {{attr_set=MOUNT_ATTR_IDMAP, userns_fd=7<{lock}>}}, 32) "
                    "= -1 EBADF (Bad file descriptor)"
                ),
                1,
            ),
            "lock_write_through": trace.replace(
                opened,
                (
                    f'{opened}\n200 openat(AT_FDCWD, "{lock}", '
                    f"O_WRONLY|O_TRUNC) = 8<{lock}>"
                ),
                1,
            ),
            "extra_sibling_session": trace.replace(
                _arg0_link_lines(200, session)[0],
                (
                    f"{_arg0_link_lines(200, session)[0]}\n"
                    f'200 mkdir("{session.with_name("codex-arg0Z9y8X7")}", 0777) = 0'
                ),
                1,
            ),
            "extra_sibling_crosses_final_cleanup": trace.replace(
                _arg0_cleanup_lines(201, session)[-1],
                (
                    f'201 mkdir("{session.with_name("codex-arg0Z9y8X7")}", 0777 '
                    "<unfinished ...>\n"
                    f"{_arg0_cleanup_lines(201, session)[-1]}\n"
                    "201 <... mkdir resumed>) = 0"
                ),
                1,
            ),
        }
        for label, candidate in cases.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1),
            ):
                evaluate_codex_trace_policy_v1(
                    candidate,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )
        evaluate_codex_trace_policy_v1(
            trace.replace(
                opened,
                f'{opened}\n200 newfstatat(AT_FDCWD, "/proc/self/fd/8", 0x0, 0) = 0',
                1,
            ),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        evaluate_codex_trace_policy_v1(
            trace.replace(
                opened,
                (
                    f"{opened}\n{descriptor_directory_open}\n200 newfstatat("
                    'AT_FDCWD, "../../../../proc/self/fd/8/9", 0x0, 0) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        evaluate_codex_trace_policy_v1(
            trace.replace(
                opened,
                (
                    f"{opened.replace('= 7<', '= 0<')}\n{dev_directory_open}\n"
                    '200 newfstatat(AT_FDCWD, "/proc/self/fd/8/stdout", '
                    "0x0, 0) = 0"
                ),
                1,
            ),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        evaluate_codex_trace_policy_v1(
            trace.replace(
                opened,
                (
                    f"{opened.replace('= 7<', '= 0<')}\n"
                    '200 newfstatat(AT_FDCWD, "/dev/stdout", 0x0, 0) = 0'
                ),
                1,
            ),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        evaluate_codex_trace_policy_v1(
            trace.replace(
                opened,
                (
                    f'{opened}\n200 newfstatat(8<{_TRACE_MANAGED_ROOT}>, "", '
                    "0x0, AT_EMPTY_PATH) = 0"
                ),
                1,
            ),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        for unrelated_descriptor_record in (
            (f"200 newfstatat(8<{_TRACE_MANAGED_ROOT}>, NULL, 0x0, AT_EMPTY_PATH) = 0"),
            (
                f'200 readlinkat(8<{_TRACE_MANAGED_ROOT}>, "", 0x0, 4096) '
                "= -1 EINVAL (Invalid argument)"
            ),
            '200 newfstatat(AT_FDCWD, "/proc/self/fd/08", 0x0, 0) = 0',
            (
                f"200 ftruncate(8<{_TRACE_MANAGED_ROOT}>, 0) = -1 EPERM "
                "(Operation not permitted)"
            ),
            ("200 ioctl(0x8, 0x40086602, 0x0) = -1 EPERM (Operation not permitted)"),
            (
                "200 io_uring_enter(0x8, 0x1, 0x1, 0x0, 0x0, 0x0) "
                "= -1 EPERM (Operation not permitted)"
            ),
            (
                f"200 setns(8<{_TRACE_MANAGED_ROOT}>, CLONE_NEWNS) = -1 EPERM "
                "(Operation not permitted)"
            ),
            (
                "200 clone3({flags=CLONE_INTO_CGROUP, exit_signal=SIGCHLD, "
                "cgroup=8}, 88) = -1 EBADF (Bad file descriptor)"
            ),
            (
                "200 clone3({flags=SIGCHLD, exit_signal=SIGCHLD, cgroup=7}, "
                "88) = -1 EINVAL (Invalid argument)"
            ),
            (
                f'200 mount_setattr(AT_FDCWD, "{_TRACE_MANAGED_ROOT}", 0, '
                f"{{attr_set=MOUNT_ATTR_IDMAP, userns_fd=8<{_TRACE_MANAGED_ROOT}>}}, "
                "32) = -1 EBADF (Bad file descriptor)"
            ),
        ):
            evaluate_codex_trace_policy_v1(
                trace.replace(
                    opened,
                    f"{opened}\n{unrelated_descriptor_record}",
                    1,
                ),
                provider_executable=_TRACE_EXECUTABLE,
                managed_profile_root=_TRACE_MANAGED_ROOT,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )
        evaluate_codex_trace_policy_v1(
            trace.replace(
                opened,
                (
                    f"{opened}\n{descriptor_directory_open}\n"
                    '200 newfstatat(AT_FDCWD, "/proc/self/fd/8/9", 0x0, 0) '
                    "= -1 ENOENT (No such file or directory)"
                ),
                1,
            ),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            real_lock = Path(temporary_directory) / _ARG0_LOCK_NAME
            lock_descriptor = os.open(real_lock, os.O_RDWR | os.O_CREAT, 0o600)
            directory_descriptor = os.open(
                "/proc/self/fd",
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
            )
            try:
                lock_identity = os.fstat(lock_descriptor)
                for prefix in ("/proc/self/fd", "/dev/fd"):
                    chained_identity = os.stat(
                        f"{prefix}/{directory_descriptor}/{lock_descriptor}"
                    )
                    self.assertEqual(
                        (chained_identity.st_dev, chained_identity.st_ino),
                        (lock_identity.st_dev, lock_identity.st_ino),
                    )
            finally:
                os.close(directory_descriptor)
                os.close(lock_descriptor)
        proof = subprocess.run(
            (
                sys.executable,
                "-c",
                """
import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as temporary_directory:
    lock = Path(temporary_directory) / ".lock"
    lock_fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    os.dup2(lock_fd, 0)
    dev_fd = os.open("/dev", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    expected = os.fstat(0)
    for prefix in ("/proc/self/fd", "/dev/fd"):
        observed = os.stat(f"{prefix}/{dev_fd}/stdin")
        assert (observed.st_dev, observed.st_ino) == (expected.st_dev, expected.st_ino)
""",
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proof.returncode, 0, proof.stderr)

    def test_arg0_creation_shape_and_cardinality_fail_closed(self) -> None:
        """M5-CDX-GATE-001: no create-shape variant widens Arg0 admission."""

        trace = _arg0_lifecycle_trace()
        source = os.fspath(_TRACE_EXECUTABLE)
        session = _ARG0_IDENTITY_SESSION
        first = f'200 symlink("{source}", "{session / _ARG0_ALIASES[0]}") = 0'
        second = f'200 symlink("{source}", "{session / _ARG0_ALIASES[1]}") = 0'
        cases = {
            "missing": trace.replace(f"{first}\n", "", 1),
            "extra": trace.replace(first, f"{first}\n{first}", 1),
            "duplicate": trace.replace(second, first, 1),
            "reordered": trace.replace(
                f"{first}\n{second}",
                f"{second}\n{first}",
                1,
            ),
            "wrong_alias": trace.replace(
                os.fspath(session / _ARG0_ALIASES[0]),
                os.fspath(session / "apply-patch"),
                1,
            ),
            "wrong_source": trace.replace(
                first,
                first.replace(source, "/opt/other/bin/codex", 1),
                1,
            ),
            "other_release_source": trace.replace(
                first,
                first.replace(source, "/opt/codex/releases/0.159.0/bin/codex", 1),
                1,
            ),
            "relative_source": trace.replace(
                first,
                first.replace(source, "codex", 1),
                1,
            ),
            "empty_source": trace.replace(
                first,
                first.replace(f'"{source}"', '""', 1),
                1,
            ),
            "escaped_source": trace.replace(
                first,
                first.replace(f'"{source}"', r'"\057opt/codex/bin/codex"', 1),
                1,
            ),
            "control_source": trace.replace(
                first,
                first.replace(f'"{source}"', r'"/opt/codex\001/bin/codex"', 1),
                1,
            ),
            "noncanonical_source": trace.replace(
                first,
                first.replace(source, "/opt/codex/../codex/bin/codex", 1),
                1,
            ),
            "mixed_parent": trace.replace(
                first,
                first.replace("codex-arg0A1b2C3", "codex-arg0Z9y8X7", 1),
                1,
            ),
            "malformed_session": trace.replace(
                first,
                first.replace("codex-arg0A1b2C3", "codex-arg0A1b2C_", 1),
                1,
            ),
            "short_session": trace.replace(
                os.fspath(session),
                os.fspath(session.with_name("codex-arg0A1b2C")),
            ),
            "long_session": trace.replace(
                os.fspath(session),
                os.fspath(session.with_name("codex-arg0A1b2C3D")),
            ),
            "unicode_session": trace.replace(
                first,
                first.replace("codex-arg0A1b2C3", "codex-arg0A1b2Cé", 1),
                1,
            ),
            "alternate_session_prefix": trace.replace(
                first,
                first.replace("codex-arg0A1b2C3", "Codex-arg0A1b2C3", 1),
                1,
            ),
            "alternate_alias_case": trace.replace(
                first,
                first.replace("/apply_patch", "/Apply_patch", 1),
                1,
            ),
            "relative_destination": trace.replace(
                first,
                first.replace(
                    os.fspath(session / _ARG0_ALIASES[0]),
                    f"tmp/arg0/{session.name}/{_ARG0_ALIASES[0]}",
                    1,
                ),
                1,
            ),
            "default_destination": trace.replace(
                first,
                first.replace(
                    os.fspath(session / _ARG0_ALIASES[0]),
                    f"/home/owner/.codex/tmp/arg0/{session.name}/{_ARG0_ALIASES[0]}",
                    1,
                ),
                1,
            ),
            "outside_destination": trace.replace(
                first,
                first.replace(
                    os.fspath(session / _ARG0_ALIASES[0]),
                    f"/tmp/{session.name}/{_ARG0_ALIASES[0]}",
                    1,
                ),
                1,
            ),
            "dotdot_destination": trace.replace(
                first,
                first.replace("/tmp/arg0/", "/tmp/arg0/../arg0/", 1),
                1,
            ),
            "dot_destination": trace.replace(
                first,
                first.replace("/tmp/arg0/", "/tmp/./arg0/", 1),
                1,
            ),
            "double_slash_destination": trace.replace(
                first,
                first.replace('symlink("/opt', 'symlink("/opt', 1).replace(
                    '", "/owner', '", "//owner', 1
                ),
                1,
            ),
            "empty_destination": trace.replace(
                first,
                first.replace(f'"{session / _ARG0_ALIASES[0]}"', '""', 1),
                1,
            ),
            "escaped_destination": trace.replace(
                first,
                first.replace(
                    f'"{session / _ARG0_ALIASES[0]}"',
                    r'"\057owner/profiles/codex/opaque/tmp/arg0/codex-arg0A1b2C3/apply_patch"',
                    1,
                ),
                1,
            ),
            "control_destination": trace.replace(
                first,
                first.replace("/apply_patch", r"/apply\001patch", 1),
                1,
            ),
            "extra_destination_component": trace.replace(
                first,
                first.replace("/apply_patch", "/extra/apply_patch", 1),
                1,
            ),
            "failed_result": trace.replace(
                first,
                first.replace(" = 0", " = -1 EEXIST (File exists)"),
                1,
            ),
            "malformed_result": trace.replace(
                first,
                first.replace(" = 0", " = 0 trailing"),
                1,
            ),
            "third_argument": trace.replace(
                first,
                first.replace(") = 0", ", 0) = 0"),
                1,
            ),
            "argument_prefix": trace.replace(
                first,
                first.replace("symlink(", 'symlink("prefix", ', 1),
                1,
            ),
            "truncated_token": trace.replace(
                first,
                first.replace(f'{_ARG0_ALIASES[0]}")', f"{_ARG0_ALIASES[0]})", 1),
                1,
            ),
        }
        for label, candidate in cases.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1) as raised,
            ):
                evaluate_codex_trace_policy_v1(
                    candidate,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )
            self.assertIn(
                str(raised.exception),
                {
                    "m5_codex_containment_link_operation_rejected",
                    "m5_codex_containment_trace_invalid",
                    "m5_codex_default_profile_access_detected",
                    "m5_codex_managed_profile_write_escape",
                },
            )
            self.assertNotIn(source, str(raised.exception))
            self.assertNotIn(os.fspath(session), repr(raised.exception))

    def test_arg0_creation_lineage_fail_closed(self) -> None:
        """M5-CDX-GATE-001: only each app-server root creates its aliases."""

        trace = _arg0_lifecycle_trace()
        link = (
            f'200 symlink("{_TRACE_EXECUTABLE}", '
            f'"{_ARG0_IDENTITY_SESSION / _ARG0_ALIASES[0]}") = 0'
        )
        without_link = trace.replace(f"{link}\n", "", 1)
        version_exit = "100 exit_group(0) = ?"
        identity_exec = _trace_app_server_exec(200, _TRACE_EXECUTABLE)
        identity_clone = "200 clone(child_stack=NULL, flags=SIGCHLD) = 201"
        identity_exit = "200 exit_group(0) = ?"
        cases = {
            "version": without_link.replace(
                version_exit,
                f"{link.replace('200 symlink', '100 symlink', 1)}\n{version_exit}",
                1,
            ),
            "unattributed": trace.replace(
                link,
                link.replace("200 symlink", "99 symlink", 1),
                1,
            ),
            "pre_exec": without_link.replace(
                identity_exec,
                f"{link}\n{identity_exec}",
                1,
            ),
            "descendant": without_link.replace(
                identity_clone,
                (f"{identity_clone}\n{link.replace('200 symlink', '201 symlink', 1)}"),
                1,
            ),
            "post_exit": without_link.replace(
                identity_exit,
                f"{identity_exit}\n{link}",
                1,
            ),
            "additional_provider": trace
            + "\n"
            + _trace_app_server_exec(400, _TRACE_EXECUTABLE),
            "overlapping_provider": trace.replace(
                identity_exit,
                f"{_trace_app_server_exec(400, _TRACE_EXECUTABLE)}\n{identity_exit}",
                1,
            ),
        }
        expected = {
            "version": "m5_codex_managed_profile_write_escape",
            "unattributed": "m5_codex_containment_link_operation_rejected",
            "pre_exec": "m5_codex_containment_link_operation_rejected",
            "descendant": "m5_codex_containment_link_operation_rejected",
            "post_exit": "m5_codex_containment_trace_invalid",
            "additional_provider": "m5_codex_containment_trace_invalid",
            "overlapping_provider": "m5_codex_containment_trace_invalid",
        }
        for label, candidate in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        candidate,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(str(raised.exception), expected[label])

    def test_arg0_cleanup_shape_cardinality_and_lineage_fail_closed(self) -> None:
        """M5-CDX-GATE-001: every alias has one exact same-operation cleanup."""

        trace = _arg0_lifecycle_trace()
        session = _ARG0_IDENTITY_SESSION
        alias = _ARG0_ALIASES[0]
        cleanup = f'201 unlinkat(9<{session}>, "{alias}", 0) = 0'
        link = f'200 symlink("{_TRACE_EXECUTABLE}", "{session / alias}") = 0'
        parent = (
            f'201 unlinkat(8<{session.parent}>, "{session.name}", AT_REMOVEDIR) = 0'
        )
        without_cleanup = trace.replace(f"{cleanup}\n", "", 1)
        before_create = without_cleanup.replace(
            link,
            f"{cleanup.replace('201 unlinkat', '200 unlinkat', 1)}\n{link}",
            1,
        )
        after_exit = without_cleanup.replace(
            "200 exit_group(0) = ?",
            (
                "200 exit_group(0) = ?\n"
                f"{cleanup.replace('201 unlinkat', '200 unlinkat', 1)}"
            ),
            1,
        )
        wrong_operation = without_cleanup.replace(
            "300 exit_group(0) = ?",
            (
                f"{cleanup.replace('201 unlinkat', '300 unlinkat', 1)}\n"
                "300 exit_group(0) = ?"
            ),
            1,
        )
        unattributed = trace.replace(
            cleanup,
            cleanup.replace("201 unlinkat", "99 unlinkat", 1),
            1,
        )
        early_parent = trace.replace(f"{parent}\n", "", 1).replace(
            cleanup,
            f"{parent}\n{cleanup}",
            1,
        )
        cases = {
            "missing": without_cleanup,
            "duplicate": trace.replace(cleanup, f"{cleanup}\n{cleanup}", 1),
            "wrong_path": trace.replace(
                cleanup,
                cleanup.replace(f'"{alias}"', '"wrong"', 1),
                1,
            ),
            "wrong_flags": trace.replace(
                cleanup,
                cleanup.replace(", 0) = 0", ", AT_REMOVEDIR) = 0"),
                1,
            ),
            "failed_result": trace.replace(
                cleanup,
                cleanup.replace(" = 0", " = -1 ENOENT (No such file or directory)"),
                1,
            ),
            "unresolved_dirfd": trace.replace(
                cleanup,
                cleanup.replace(f"9<{session}>", "9", 1),
                1,
            ),
            "plain_unlink": trace.replace(
                cleanup,
                f'201 unlink("{session / alias}") = 0',
                1,
            ),
            "before_create": before_create,
            "after_exit": after_exit,
            "wrong_operation": wrong_operation,
            "unattributed": unattributed,
            "parent_removal_too_early": early_parent,
            "duplicate_parent_removal": trace.replace(parent, f"{parent}\n{parent}", 1),
        }
        expected = {
            "missing": "m5_codex_containment_link_operation_rejected",
            "duplicate": "m5_codex_containment_link_operation_rejected",
            "wrong_path": "m5_codex_containment_link_operation_rejected",
            "wrong_flags": "m5_codex_containment_link_operation_rejected",
            "failed_result": "m5_codex_containment_link_operation_rejected",
            "unresolved_dirfd": "m5_codex_containment_trace_invalid",
            "plain_unlink": "m5_codex_containment_link_operation_rejected",
            "before_create": "m5_codex_containment_link_operation_rejected",
            "after_exit": "m5_codex_containment_trace_invalid",
            "wrong_operation": "m5_codex_containment_link_operation_rejected",
            "unattributed": "m5_codex_containment_link_operation_rejected",
            "parent_removal_too_early": (
                "m5_codex_containment_path_mutator_unverifiable"
            ),
            "duplicate_parent_removal": (
                "m5_codex_containment_path_mutator_unverifiable"
            ),
        }
        for label, candidate in cases.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1) as raised,
            ):
                evaluate_codex_trace_policy_v1(
                    candidate,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )
            self.assertEqual(str(raised.exception), expected[label])

    def test_arg0_unfinished_and_resumed_chronology_is_closed(self) -> None:
        """M5-CDX-GATE-001: lifecycle order follows invocation and completion."""

        trace = _arg0_lifecycle_trace()
        session = _ARG0_IDENTITY_SESSION
        alias = _ARG0_ALIASES[0]
        link = f'200 symlink("{_TRACE_EXECUTABLE}", "{session / alias}") = 0'
        final_link = (
            f'200 symlink("{_TRACE_EXECUTABLE}", "{session / _ARG0_ALIASES[-1]}") = 0'
        )
        cleanup = f'201 unlinkat(9<{session}>, "{alias}", 0) = 0'
        valid = trace.replace(
            link,
            link.removesuffix(") = 0")
            + " <unfinished ...>\n200 <... symlink resumed>) = 0",
            1,
        ).replace(
            cleanup,
            cleanup.removesuffix(") = 0")
            + " <unfinished ...>\n201 <... unlinkat resumed>) = 0",
            1,
        )
        summary = evaluate_codex_trace_policy_v1(
            valid,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        self.assertEqual(summary.provider_write_count, 26)

        root_cleanup = cleanup.replace("201 unlinkat", "200 unlinkat", 1)
        cleanup_before_create = trace.replace(f"{cleanup}\n", "", 1).replace(
            link,
            (
                root_cleanup.removesuffix(") = 0")
                + f" <unfinished ...>\n{link}\n"
                + "200 <... unlinkat resumed>) = 0"
            ),
            1,
        )
        cleanup_after_exit = trace.replace(
            cleanup,
            cleanup.removesuffix(") = 0") + " <unfinished ...>",
            1,
        ).replace(
            "200 exit_group(0) = ?",
            "200 exit_group(0) = ?\n201 <... unlinkat resumed>) = 0",
            1,
        )
        cleanup_before_create_completion = trace.replace(
            f"{cleanup}\n",
            "",
            1,
        ).replace(
            link,
            "\n".join(
                (
                    link.removesuffix(") = 0") + " <unfinished ...>",
                    root_cleanup,
                    "200 <... symlink resumed>) = 0",
                )
            ),
            1,
        )
        parent = (
            f'201 unlinkat(8<{session.parent}>, "{session.name}", AT_REMOVEDIR) = 0'
        )
        cleanup_after_executor_exit = (
            trace.replace(
                cleanup,
                cleanup.removesuffix(") = 0") + " <unfinished ...>",
                1,
            )
            .replace(f"{parent}\n", "", 1)
            .replace(
                "201 exit_group(0) = ?",
                "\n".join(
                    (
                        "201 exit_group(0) = ?",
                        "201 <... unlinkat resumed>) = 0",
                        parent.replace("201 unlinkat", "200 unlinkat", 1),
                    )
                ),
                1,
            )
        )
        quota_exec = _trace_app_server_exec(300, _TRACE_EXECUTABLE)
        link_across_operation = trace.replace(
            final_link,
            final_link.removesuffix(") = 0") + " <unfinished ...>",
            1,
        ).replace(
            quota_exec,
            f"{quota_exec}\n200 <... symlink resumed>) = 0",
            1,
        )
        exit_across_next_operation = trace.replace(
            "200 exit_group(0) = ?",
            "200 exit_group(0 <unfinished ...>",
            1,
        ).replace(
            _trace_app_server_exec(300, _TRACE_EXECUTABLE),
            (
                f"{_trace_app_server_exec(300, _TRACE_EXECUTABLE)}\n"
                "200 <... exit_group resumed>) = ?"
            ),
            1,
        )
        version_exec = _trace_version_exec(100, _TRACE_EXECUTABLE)
        version_exec_after_exit = trace.replace(
            version_exec,
            version_exec.removesuffix(") = 0") + " <unfinished ...>",
            1,
        ).replace(
            "100 exit_group(0) = ?",
            "100 exit_group(0) = ?\n100 <... execve resumed>) = 0",
            1,
        )
        cases = {
            "cleanup_invoked_before_create": cleanup_before_create,
            "cleanup_invoked_before_create_completion": (
                cleanup_before_create_completion
            ),
            "cleanup_completes_after_exit": cleanup_after_exit,
            "cleanup_completes_after_executor_exit": cleanup_after_executor_exit,
            "link_resumes_after_next_operation_begins": link_across_operation,
            "operation_exit_completes_after_next_exec": exit_across_next_operation,
            "provider_exec_completes_after_exit": version_exec_after_exit,
        }
        expected = {
            "cleanup_invoked_before_create": (
                "m5_codex_containment_link_operation_rejected"
            ),
            "cleanup_invoked_before_create_completion": (
                "m5_codex_containment_link_operation_rejected"
            ),
            "cleanup_completes_after_exit": (
                "m5_codex_containment_link_operation_rejected"
            ),
            "cleanup_completes_after_executor_exit": (
                "m5_codex_containment_link_operation_rejected"
            ),
            "link_resumes_after_next_operation_begins": (
                "m5_codex_containment_link_operation_rejected"
            ),
            "operation_exit_completes_after_next_exec": (
                "m5_codex_containment_trace_invalid"
            ),
            "provider_exec_completes_after_exit": (
                "m5_codex_containment_trace_invalid"
            ),
        }
        for label, candidate in cases.items():
            with (
                self.subTest(label=label),
                self.assertRaises(M5CodexContainmentErrorV1) as raised,
            ):
                evaluate_codex_trace_policy_v1(
                    candidate,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=_TRACE_MANAGED_ROOT,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )
            self.assertEqual(str(raised.exception), expected[label])

    def test_arg0_transient_namespace_movement_fails_closed(self) -> None:
        """M5-CDX-GATE-001: a later clean tree cannot hide alias movement."""

        trace = _arg0_lifecycle_trace()
        session = _ARG0_IDENTITY_SESSION
        alias = session / _ARG0_ALIASES[0]
        last_link = (
            f'200 symlink("{_TRACE_EXECUTABLE}", "{session / _ARG0_ALIASES[-1]}") = 0'
        )

        def after_creates(*records: str) -> str:
            return trace.replace(
                last_link,
                "\n".join((last_link, *records)),
                1,
            )

        moved = _TRACE_MANAGED_ROOT / "runtime" / "moved-arg0"
        cleanup = f'201 unlinkat(9<{session}>, "{_ARG0_ALIASES[0]}", 0) = 0'
        first_link = f'200 symlink("{_TRACE_EXECUTABLE}", "{alias}") = 0'
        final_clean = after_creates(
            f'200 rename("{alias}", "{moved}") = 0',
        ).replace(
            cleanup,
            f'201 unlinkat(9<{moved.parent}>, "{moved.name}", 0) = 0',
            1,
        )
        movement_after_root_exit = trace.replace(
            first_link,
            f"200 clone(child_stack=NULL, flags=SIGCHLD) = 202\n{first_link}",
            1,
        ).replace(
            "200 exit_group(0) = ?",
            "\n".join(
                (
                    "200 exit_group(0) = ?",
                    f'202 rename("{session}", "{session}.moved") = 0',
                    f'202 rename("{session}.moved", "{session}") = 0',
                    "202 exit_group(0) = ?",
                )
            ),
            1,
        )
        movement_before_first_completion = trace.replace(
            first_link,
            "\n".join(
                (
                    "200 clone(child_stack=NULL, flags=SIGCHLD) = 202",
                    first_link.removesuffix(") = 0") + " <unfinished ...>",
                    f'202 rename("{session}", "{session}.moved") = 0',
                    f'202 rename("{session}.moved", "{session}") = 0',
                    "202 exit_group(0) = ?",
                    "200 <... symlink resumed>) = 0",
                )
            ),
            1,
        )
        relative_movement_during_shared_chdir = after_creates(
            "90 clone(child_stack=NULL, flags=CLONE_FS|SIGCHLD) = 91",
            '90 chdir("/outside" <unfinished ...>',
            (
                f'91 rename("tmp/arg0/{session.name}/{_ARG0_ALIASES[0]}", '
                '"runtime/moved") = 0'
            ),
            (
                '91 rename("runtime/moved", '
                f'"tmp/arg0/{session.name}/{_ARG0_ALIASES[0]}") = 0'
            ),
            "90 <... chdir resumed>) = 0",
            "91 exit_group(0) = ?",
            "90 exit_group(0) = ?",
        )
        double_slash_alias = f"//{os.fspath(alias).lstrip('/')}"
        unattributed_double_slash_movement = after_creates(
            f'90 rename("{double_slash_alias}", "{moved}") = 0',
            f'90 rename("{moved}", "{double_slash_alias}") = 0',
        )
        unattributed_double_slash_open_result = after_creates(
            (
                '90 openat(AT_FDCWD, "/outside/opaque", O_WRONLY|O_TRUNC) '
                f"= 5<{double_slash_alias}>"
            ),
        )
        proc_root_alias = f"/proc/self/root{alias}"
        unattributed_proc_root_movement = after_creates(
            f'90 rename("{proc_root_alias}", "{moved}") = 0',
            f'90 rename("{moved}", "{proc_root_alias}") = 0',
        )
        unattributed_proc_root_writable_open = after_creates(
            (
                f'90 openat(AT_FDCWD, "{proc_root_alias}", O_WRONLY|O_TRUNC) '
                f"= 5<{_TRACE_EXECUTABLE}>"
            ),
        )
        cases = {
            "rename_out_and_back": after_creates(
                f'200 rename("{alias}", "{moved}") = 0',
                f'200 rename("{moved}", "{alias}") = 0',
            ),
            "rename_exchange": after_creates(
                (
                    f'200 renameat2(AT_FDCWD, "{alias}", AT_FDCWD, '
                    f'"{_TRACE_MANAGED_ROOT / "runtime" / "other"}", '
                    "RENAME_EXCHANGE) = 0"
                ),
            ),
            "failed_reported_rename_out_and_back": after_creates(
                (f'200 rename("{alias}", "{moved}") = -1 EIO (Input/output error)'),
                (f'200 rename("{moved}", "{alias}") = -1 EIO (Input/output error)'),
            ),
            "session_parent_rename": after_creates(
                f'200 rename("{session}", "{session}.moved") = 0',
            ),
            "hard_link_alias": after_creates(
                f'200 link("{alias}", "{moved}") = 0',
            ),
            "symlinkat_extra": after_creates(
                f'200 symlinkat("{_TRACE_EXECUTABLE}", AT_FDCWD, "{moved}") = 0',
            ),
            "write_through_alias": after_creates(
                f'200 openat(AT_FDCWD, "{alias}", O_WRONLY|O_TRUNC) = 9<{alias}>',
            ),
            "final_clean_tree_movement": final_clean,
            "movement_after_root_exit": movement_after_root_exit,
            "movement_before_first_completion": movement_before_first_completion,
            "relative_movement_during_shared_chdir": (
                relative_movement_during_shared_chdir
            ),
            "unattributed_double_slash_movement": (unattributed_double_slash_movement),
            "unattributed_double_slash_open_result": (
                unattributed_double_slash_open_result
            ),
            "unattributed_proc_root_movement": unattributed_proc_root_movement,
            "unattributed_proc_root_writable_open": (
                unattributed_proc_root_writable_open
            ),
        }
        expected = {
            "rename_out_and_back": "m5_codex_containment_path_mutator_unverifiable",
            "rename_exchange": "m5_codex_containment_path_mutator_unverifiable",
            "failed_reported_rename_out_and_back": (
                "m5_codex_containment_path_mutator_unverifiable"
            ),
            "session_parent_rename": ("m5_codex_containment_path_mutator_unverifiable"),
            "hard_link_alias": "m5_codex_containment_link_operation_rejected",
            "symlinkat_extra": "m5_codex_managed_profile_write_escape",
            "write_through_alias": ("m5_codex_containment_path_mutator_unverifiable"),
            "final_clean_tree_movement": (
                "m5_codex_containment_link_operation_rejected"
            ),
            "movement_after_root_exit": (
                "m5_codex_containment_path_mutator_unverifiable"
            ),
            "movement_before_first_completion": (
                "m5_codex_containment_path_mutator_unverifiable"
            ),
            "relative_movement_during_shared_chdir": (
                "m5_codex_containment_working_directory_escape"
            ),
            "unattributed_double_slash_movement": (
                "m5_codex_containment_trace_invalid"
            ),
            "unattributed_double_slash_open_result": (
                "m5_codex_containment_trace_invalid"
            ),
            "unattributed_proc_root_movement": (
                "m5_codex_containment_path_mutator_unverifiable"
            ),
            "unattributed_proc_root_writable_open": (
                "m5_codex_containment_path_mutator_unverifiable"
            ),
        }
        for label, candidate in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        candidate,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(str(raised.exception), expected[label])

    def test_arg0_failed_descendant_mkdir_has_no_namespace_effect(self) -> None:
        """M5-CDX-GATE-001: a failed owned mkdir is not a mutation."""

        trace = _arg0_lifecycle_trace()
        clone = "200 clone(child_stack=NULL, flags=SIGCHLD) = 201"
        ancestor = _ARG0_IDENTITY_SESSION.parent
        failed_mkdir = f'201 mkdir("{ancestor}", 0700) = -1 EEXIST (File exists)'
        failed_trace = trace.replace(clone, f"{clone}\n{failed_mkdir}", 1)
        baseline = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        summary = evaluate_codex_trace_policy_v1(
            failed_trace,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(
            summary.provider_access_count,
            baseline.provider_access_count + 1,
        )
        self.assertEqual(
            summary.provider_write_count,
            baseline.provider_write_count + 1,
        )
        successful_trace = failed_trace.replace(
            " = -1 EEXIST (File exists)",
            " = 0",
            1,
        )
        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                successful_trace,
                provider_executable=_TRACE_EXECUTABLE,
                managed_profile_root=_TRACE_MANAGED_ROOT,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )
        self.assertEqual(
            str(raised.exception),
            "m5_codex_containment_path_mutator_unverifiable",
        )

    def test_descriptor_bound_ftruncate_is_counted_for_both_provider_reads(
        self,
    ) -> None:
        """M5-CDX-GATE-001: confined fd truncation is a provider write."""

        identity_target = _TRACE_MANAGED_ROOT / "runtime" / "identity-state"
        quota_target = _TRACE_MANAGED_ROOT / "runtime" / "quota-state"
        trace = _trace_with_ftruncates(
            f"ftruncate(10<{identity_target}>, 0) = 0",
            f"ftruncate(999999<{quota_target}>, 9223372036854775807) = 0",
        )

        baseline = evaluate_codex_trace_policy_v1(
            _two_operation_chmod_trace(),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(
            summary.provider_access_count,
            baseline.provider_access_count + 2,
        )
        self.assertEqual(
            summary.provider_write_count,
            baseline.provider_write_count + 2,
        )

    def test_exact_failed_ftruncate_is_no_effect_but_keeps_chronology(self) -> None:
        """M5-CDX-GATE-001: canonical failed fd calls remain ordered records."""

        target = _TRACE_MANAGED_ROOT / "runtime" / "state"
        failed = f"ftruncate(10<{target}>, 3) = -1 EPERM (Operation not permitted)"
        trace = _trace_with_ftruncates(failed, failed)
        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        self.assertEqual(summary.provider_write_count, 26)

        after_exit = trace.replace(
            "200 exit_group(0) = ?",
            f"200 exit_group(0) = ?\n200 {failed}",
            1,
        )
        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                after_exit,
                provider_executable=_TRACE_EXECUTABLE,
                managed_profile_root=_TRACE_MANAGED_ROOT,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )
        self.assertEqual(str(raised.exception), "m5_codex_containment_trace_invalid")

    def test_ftruncate_argument_and_result_grammar_fails_closed(self) -> None:
        """M5-CDX-GATE-001: fd, target, length, and result are canonical."""

        target = os.fspath(_TRACE_MANAGED_ROOT / "runtime" / "state")
        exact = f"ftruncate(10<{target}>, 3) = 0"
        cases = {
            "descriptor_zero": f"ftruncate(0<{target}>, 3) = 0",
            "descriptor_one": f"ftruncate(1<{target}>, 3) = 0",
            "descriptor_two": f"ftruncate(2<{target}>, 3) = 0",
            "descriptor_overflow": f"ftruncate(1000000<{target}>, 3) = 0",
            "descriptor_leading_zero": f"ftruncate(010<{target}>, 3) = 0",
            "length_leading_zero": f"ftruncate(10<{target}>, 03) = 0",
            "length_negative": f"ftruncate(10<{target}>, -1) = 0",
            "length_overflow": (f"ftruncate(10<{target}>, 9223372036854775808) = 0"),
            "relative": "ftruncate(10<relative/state>, 3) = 0",
            "double_slash": (
                "ftruncate(10</owner//profiles/codex/opaque/state>, 3) = 0"
            ),
            "dotdot": (
                "ftruncate(10</owner/profiles/codex/opaque/runtime/../state>, 3) = 0"
            ),
            "escape": (
                r"ftruncate(10</owner/profiles/codex/opaque/state\134name>, 3) = 0"
            ),
            "delimiter": (
                "ftruncate(10</owner/profiles/codex/opaque/state>name>, 3) = 0"
            ),
            "argument_prefix": (f"ftruncate(AT_FDCWD, 10<{target}>, 3) = 0"),
            "argument_suffix": f"ftruncate(10<{target}>, 3, 0) = 0",
            "control": (
                "ftruncate(10</owner/profiles/codex/opaque/state\rname>, 3) = 0"
            ),
            "result_positive": f"ftruncate(10<{target}>, 3) = 1",
            "result_unknown": f"ftruncate(10<{target}>, 3) = ?",
            "result_restarted": (
                f"ftruncate(10<{target}>, 3) = ? ERESTARTSYS "
                "(To be restarted if SA_RESTART is set)"
            ),
            "result_prefix": f"ftruncate(10<{target}>, 3) = leading 0",
            "result_suffix": f"ftruncate(10<{target}>, 3) = 0 trailing",
            "failed_malformed_args": (
                f"ftruncate(10<{target}>, 03) = -1 EPERM (Operation not permitted)"
            ),
            "failed_malformed_result": f"ftruncate(10<{target}>, 3) = -1 EPERM",
        }
        for label, record in cases.items():
            with self.subTest(label=label):
                trace = _trace_with_ftruncates(record, exact)
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

    def test_ftruncate_unverifiable_and_escape_boundaries_are_specific(self) -> None:
        """M5-CDX-GATE-001: scope failures retain sanitized exact causes."""

        managed_target = _TRACE_MANAGED_ROOT / "runtime" / "state"
        exact = f"ftruncate(10<{managed_target}>, 3) = 0"
        cases = {
            "missing_annotation": (
                "ftruncate(10, 3) = 0",
                "m5_codex_containment_fd_write_unverifiable",
            ),
            "deleted_annotation": (
                f"ftruncate(10<{managed_target} (deleted)>, 3) = 0",
                "m5_codex_containment_fd_write_unverifiable",
            ),
            "failed_missing_annotation": (
                "ftruncate(10, 3) = -1 EBADF (Bad file descriptor)",
                "m5_codex_containment_fd_write_unverifiable",
            ),
            "failed_deleted_annotation": (
                f"ftruncate(10<{managed_target} (deleted)>, 3) = -1 EPERM "
                "(Operation not permitted)",
                "m5_codex_containment_fd_write_unverifiable",
            ),
            "missing_annotation_with_malformed_result": (
                "ftruncate(10, 3) = ?",
                "m5_codex_containment_fd_write_unverifiable",
            ),
            "deleted_annotation_with_malformed_result": (
                f"ftruncate(10<{managed_target} (deleted)>, 3) = ?",
                "m5_codex_containment_fd_write_unverifiable",
            ),
            "default_root": (
                "ftruncate(10</home/owner/.codex/state>, 3) = 0",
                "m5_codex_default_profile_access_detected",
            ),
            "outside_root": (
                "ftruncate(10</tmp/outside>, 3) = 0",
                "m5_codex_managed_profile_write_escape",
            ),
        }
        for label, (record, code) in cases.items():
            with self.subTest(label=label):
                trace = _trace_with_ftruncates(record, exact)
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        trace,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(str(raised.exception), code)

        first_exec = _trace_version_exec(100, _TRACE_EXECUTABLE)
        unattributed = _two_operation_chmod_trace().replace(
            first_exec,
            f"99 {exact}\n{first_exec}",
            1,
        )
        version = _two_operation_chmod_trace().replace(
            "100 exit_group(0) = ?",
            f"100 {exact}\n100 exit_group(0) = ?",
            1,
        )
        for label, trace in {"unattributed": unattributed, "version": version}.items():
            with self.subTest(label=label):
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

    def test_exact_two_app_server_lineage_chmods_are_admitted(self) -> None:
        """M5-CDX-GATE-001: one inode-bound chmod per operation is admitted."""

        summary = evaluate_codex_trace_policy_v1(
            _two_operation_chmod_trace(),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 26)
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
                f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = -1 EPERM '
                "(Operation not permitted)",
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
            "fallocate": "fallocate(9, 0, 0, 1) = 0",
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
            with self.subTest(label=label):
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    evaluate_codex_trace_policy_v1(
                        trace,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=_TRACE_MANAGED_ROOT,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                if label == "fallocate":
                    self.assertEqual(
                        str(raised.exception),
                        "m5_codex_containment_fd_write_unverifiable",
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

    def test_unfinished_shared_chdir_keeps_unambiguous_paths_valid(self) -> None:
        """M5-CDX-GATE-001: absolute and post-completion paths stay provable."""

        first_app_server = _trace_app_server_exec(200, _TRACE_EXECUTABLE)
        trace = _two_operation_chmod_trace().replace(
            first_app_server,
            "90 clone(child_stack=NULL, flags=CLONE_FS|SIGCHLD) = 91\n"
            '90 chdir("/outside" <unfinished ...>\n'
            '91 stat("/outside/absolute", {st_mode=S_IFREG|0600}) = 0\n'
            "90 <... chdir resumed>) = 0\n"
            '91 stat("relative", {st_mode=S_IFREG|0600}) = 0\n'
            "91 exit_group(0) = ?\n"
            "90 exit_group(0) = ?\n"
            f"{first_app_server}",
            1,
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=_TRACE_MANAGED_ROOT,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.default_profile_access_count, 0)
        self.assertEqual(summary.default_profile_write_count, 0)

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
        trace = _two_operation_chmod_trace().replace(
            os.fspath(_TRACE_EXECUTABLE),
            os.fspath(executable),
        )
        trace = (
            trace.replace(
                _trace_version_exec(100, executable),
                "\n".join(
                    (
                        _trace_version_exec(100, executable),
                        f'100 openat(AT_FDCWD, "{executable}", O_RDONLY) '
                        f"= 3<{executable}>",
                    )
                ),
                1,
            )
            .replace(
                _trace_app_server_exec(200, executable),
                "\n".join(
                    (
                        _trace_app_server_exec(200, executable),
                        f'200 openat(AT_FDCWD, "{managed}/state.sqlite", '
                        f"O_RDWR|O_CREAT, 0600) = 4<{managed}/state.sqlite>",
                    )
                ),
                1,
            )
            .replace(
                "200 clone(child_stack=NULL, flags=SIGCHLD) = 201",
                "200 clone(child_stack=NULL, flags=SIGCHLD) = 201\n"
                '201 mkdir("runtime", 0700) = 0',
                1,
            )
            .replace(
                _trace_app_server_exec(300, executable),
                "\n".join(
                    (
                        _trace_app_server_exec(300, executable),
                        f'300 newfstatat(AT_FDCWD, "{managed}/auth.json", '
                        "{st_mode=S_IFREG|0600}, 0) = 0",
                    )
                ),
                1,
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 28)
        self.assertGreaterEqual(summary.provider_access_count, 5)
        self.assertEqual(summary.default_profile_access_count, 0)
        self.assertEqual(summary.default_profile_write_count, 0)

    def test_successful_symlink_uses_only_link_path_for_profile_policy(
        self,
    ) -> None:
        """M5-CDX-GATE-001: payload text cannot mask the global link rejection."""

        managed = Path("/owner/profiles/codex/opaque")
        executable = Path(
            "/home/owner/.codex/packages/standalone/releases/0.160.0/bin/codex"
        )
        release_resource = executable.parent.parent / "codex-path" / "rg"
        managed_link = managed / "temporary" / "rg"
        anchor = f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        baseline_trace = _two_operation_chmod_trace().replace(
            os.fspath(_TRACE_EXECUTABLE),
            os.fspath(executable),
        )
        trace = baseline_trace.replace(
            anchor,
            f'{anchor}\n201 symlink("{release_resource}", "{managed_link}") = 0',
            1,
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
            "m5_codex_containment_link_operation_rejected",
        )

    def test_failed_symlink_is_rejected_without_exposing_its_payload(self) -> None:
        """M5-CDX-GATE-001: failed extra links fail closed and stay private."""

        managed = Path("/owner/profiles/codex/opaque")
        executable = Path(
            "/home/owner/.codex/packages/standalone/releases/0.160.0/bin/codex"
        )
        release_resource = executable.parent.parent / "codex-path" / "rg"
        managed_link = managed / "temporary" / "rg"
        anchor = f'201 chmod("{_TRACE_CHMOD_TARGET}", 0700) = 0'
        baseline_trace = _two_operation_chmod_trace().replace(
            os.fspath(_TRACE_EXECUTABLE),
            os.fspath(executable),
        )
        trace = baseline_trace.replace(
            anchor,
            (
                f'{anchor}\n201 symlink("{release_resource}", "{managed_link}") '
                "= -1 EEXIST (File exists)"
            ),
            1,
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
            "m5_codex_containment_link_operation_rejected",
        )
        self.assertNotIn(os.fspath(release_resource), str(raised.exception))
        self.assertNotIn(os.fspath(release_resource), repr(raised.exception))

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
                '302 openat(AT_FDCWD, "/tmp/codex-state", '
                "O_WRONLY|O_CREAT, 0600) = 5</tmp/codex-state>",
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
                '352 openat(AT_FDCWD, "/tmp/escaped", O_WRONLY|O_CREAT, '
                "0600) = 5</tmp/escaped>",
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
        trace = _two_operation_chmod_trace().replace(
            os.fspath(_TRACE_EXECUTABLE),
            os.fspath(executable),
        )
        trace = trace.replace(
            _trace_version_exec(100, executable),
            (
                '400 openat(AT_FDCWD, "/owner/private/result.json", '
                "O_WRONLY|O_CREAT, 0600) = 3</owner/private/result.json>\n"
                f"{_trace_version_exec(100, executable)}"
            ),
            1,
        ).replace(
            _trace_app_server_exec(200, executable),
            (
                f"{_trace_app_server_exec(200, executable)}\n"
                f'200 openat(AT_FDCWD, "{managed}/state", O_RDWR|O_CREAT, '
                f"0600) = 4<{managed}/state>"
            ),
            1,
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_write_count, 27)

    def test_pre_exec_driver_filesystem_activity_is_not_attributed(self) -> None:
        """M5-CDX-GATE-001: a child becomes a provider only at exact exec."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = _two_operation_chmod_trace().replace(
            os.fspath(_TRACE_EXECUTABLE),
            os.fspath(executable),
        )
        trace = trace.replace(
            _trace_version_exec(100, executable),
            "\n".join(
                (
                    '100 chdir("/tmp/agentmonitor-codex-version") = 0',
                    '100 openat(AT_FDCWD, "/tmp/driver-state", '
                    "O_WRONLY|O_CREAT, 0600) = 4</tmp/driver-state>",
                    _trace_version_exec(100, executable),
                )
            ),
            1,
        ).replace(
            _trace_app_server_exec(200, executable),
            "\n".join(
                (
                    f'200 chdir("{managed}") = 0',
                    _trace_app_server_exec(200, executable),
                    f'200 openat(AT_FDCWD, "{managed}/state", '
                    f"O_RDWR|O_CREAT, 0600) = 4<{managed}/state>",
                )
            ),
            1,
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 27)

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
                '551 openat(AT_FDCWD, "/tmp/reused-pid-state", '
                "O_WRONLY|O_CREAT, 0600) = 4</tmp/reused-pid-state>",
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
        """M5-CDX-GATE-001: an annotated dirfd governs relative unlink scope."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        runtime = managed / "runtime"
        anchor = f'201 chmod("{managed}/runtime/prepared", 0700) = 0'
        confined_trace = _two_operation_chmod_trace().replace(
            anchor,
            f'{anchor}\n201 unlinkat(9<{runtime}>, "stale", 0) = 0',
            1,
        )
        baseline = evaluate_codex_trace_policy_v1(
            _two_operation_chmod_trace(),
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        summary = evaluate_codex_trace_policy_v1(
            confined_trace,
            provider_executable=_TRACE_EXECUTABLE,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )
        self.assertEqual(
            summary.provider_access_count,
            baseline.provider_access_count + 1,
        )
        self.assertEqual(
            summary.provider_write_count,
            baseline.provider_write_count + 1,
        )
        for label, record in {
            "tracked_cwd": 'unlinkat(AT_FDCWD, "runtime/stale", 0) = 0',
            "absolute_ignores_numeric_dirfd": (
                f'unlinkat(9, "{runtime}/stale", 0) = 0'
            ),
            "canonical_failed_result": (
                f'unlinkat(9<{runtime}>, "missing", 0) = -1 ENOENT '
                "(No such file or directory)"
            ),
        }.items():
            with self.subTest(label=label):
                trace = _two_operation_chmod_trace().replace(
                    anchor,
                    f"{anchor}\n201 {record}",
                    1,
                )
                accepted = evaluate_codex_trace_policy_v1(
                    trace,
                    provider_executable=_TRACE_EXECUTABLE,
                    managed_profile_root=managed,
                    default_codex_roots=(Path("/home/owner/.codex"),),
                )
                self.assertEqual(
                    accepted.provider_write_count,
                    baseline.provider_write_count + 1,
                )

        escaped_trace = _two_operation_chmod_trace().replace(
            anchor,
            f'{anchor}\n201 unlinkat(9</outside>, "escaped", 0) = 0',
            1,
        )

        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
            evaluate_codex_trace_policy_v1(
                escaped_trace,
                provider_executable=executable,
                managed_profile_root=managed,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )
        self.assertEqual(
            str(raised.exception),
            "m5_codex_managed_profile_write_escape",
        )
        for label, record, code in (
            (
                "default_profile",
                'unlinkat(9</home/owner/.codex>, "state", 0) = 0',
                "m5_codex_default_profile_access_detected",
            ),
            (
                "protected_target",
                f'unlinkat(9<{runtime}>, "prepared", 0) = 0',
                "m5_codex_containment_path_mutator_unverifiable",
            ),
        ):
            with self.subTest(label=label):
                trace = _two_operation_chmod_trace().replace(
                    anchor,
                    f"{anchor}\n201 {record}",
                    1,
                )
                with self.assertRaises(M5CodexContainmentErrorV1) as rejected:
                    evaluate_codex_trace_policy_v1(
                        trace,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=managed,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(str(rejected.exception), code)

        invalid_records = {
            "missing_annotation": 'unlinkat(9, "stale", 0) = 0',
            "deleted_annotation": (f'unlinkat(9<{runtime} (deleted)>, "stale", 0) = 0'),
            "relative_annotation": 'unlinkat(9<runtime>, "stale", 0) = 0',
            "relative_annotation_absolute_target": (
                f'unlinkat(9<runtime>, "{runtime}/stale", 0) = 0'
            ),
            "cwd_annotation_mismatch": (
                'unlinkat(AT_FDCWD</outside>, "runtime/stale", 0) = 0'
            ),
            "double_slash_annotation": (
                'unlinkat(9</owner//profiles/codex/opaque/runtime>, "stale", 0) = 0'
            ),
            "dotdot_annotation": (
                "unlinkat(9</owner/profiles/codex/opaque/runtime/../runtime>, "
                '"stale", 0) = 0'
            ),
            "escape_annotation": (
                "unlinkat(9</owner/profiles/codex/opaque/runtime\\134name>, "
                '"stale", 0) = 0'
            ),
            "descriptor_two": f'unlinkat(2<{runtime}>, "stale", 0) = 0',
            "descriptor_overflow": (f'unlinkat(1000000<{runtime}>, "stale", 0) = 0'),
            "descriptor_leading_zero": (f'unlinkat(09<{runtime}>, "stale", 0) = 0'),
            "flag_suffix": f'unlinkat(9<{runtime}>, "stale", 0, 0) = 0',
            "target_control": f'unlinkat(9<{runtime}>, "stale\\001name", 0) = 0',
            "target_dot": f'unlinkat(9<{runtime}>, ".", 0) = 0',
            "target_dotdot": f'unlinkat(9<{runtime}>, "..", 0) = 0',
            "failed_target_dot": (
                f'unlinkat(9<{runtime}>, ".", 0) = -1 EINVAL (Invalid argument)'
            ),
            "result_positive": f'unlinkat(9<{runtime}>, "stale", 0) = 1',
            "result_unknown": f'unlinkat(9<{runtime}>, "stale", 0) = ?',
            "result_restarted": (
                f'unlinkat(9<{runtime}>, "stale", 0) = ? ERESTARTSYS '
                "(To be restarted if SA_RESTART is set)"
            ),
            "result_prefix": (f'unlinkat(9<{runtime}>, "stale", 0) = leading 0'),
            "result_suffix": (f'unlinkat(9<{runtime}>, "stale", 0) = 0 trailing'),
            "failed_result_malformed": (
                f'unlinkat(9<{runtime}>, "stale", 0) = -1 ENOENT'
            ),
        }
        for label, record in invalid_records.items():
            with self.subTest(label=label):
                trace = _two_operation_chmod_trace().replace(
                    anchor,
                    f"{anchor}\n201 {record}",
                    1,
                )
                with self.assertRaises(M5CodexContainmentErrorV1) as invalid:
                    evaluate_codex_trace_policy_v1(
                        trace,
                        provider_executable=_TRACE_EXECUTABLE,
                        managed_profile_root=managed,
                        default_codex_roots=(Path("/home/owner/.codex"),),
                    )
                self.assertEqual(
                    str(invalid.exception),
                    "m5_codex_containment_trace_invalid",
                )

        unresolved_openat = _two_operation_chmod_trace().replace(
            anchor,
            (
                f"{anchor}\n"
                '201 openat(9</outside>, "escaped", O_WRONLY|O_CREAT, 0600) '
                "= 5</outside/escaped>"
            ),
            1,
        )
        with self.assertRaises(M5CodexContainmentErrorV1) as unresolved:
            evaluate_codex_trace_policy_v1(
                unresolved_openat,
                provider_executable=_TRACE_EXECUTABLE,
                managed_profile_root=managed,
                default_codex_roots=(Path("/home/owner/.codex"),),
            )
        self.assertEqual(
            str(unresolved.exception),
            "m5_codex_containment_trace_invalid",
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
                f'701 openat(AT_FDCWD</outside>, "{managed}/link/state", '
                "O_WRONLY|O_CREAT, 0600) = 5</outside/state>",
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
    def test_mountinfo_parser_rejects_nested_and_malformed_topology(self) -> None:
        """M5-CDX-GATE-001: proc mount topology is strict and alias-free."""

        managed = Path("/owner/profiles/codex/opaque")
        valid = (
            b"24 24 8:1 / / rw,relatime - ext4 /dev/root rw\n"
            b"25 24 0:5 / /proc rw,nosuid - proc proc rw\n"
            b"27 24 0:6 / /space\\040mount rw - tmpfs tmpfs rw\n"
            b"28 24 0:7 mnt:[4026531841] /run/ns rw - nsfs nsfs rw\n"
        )
        view = containment._parse_mountinfo_v1(
            valid,
            managed_profile_root=managed,
        )
        self.assertEqual(view.covering_mount.mount_id, 24)
        hidden_initramfs_parent = valid.replace(
            b"24 24 8:1 / /",
            b"24 0 8:1 / /",
            1,
        )
        hidden_parent_view = containment._parse_mountinfo_v1(
            hidden_initramfs_parent,
            managed_profile_root=managed,
        )
        self.assertEqual(hidden_parent_view.covering_mount.parent_id, 0)

        cases = {
            "nested_directory_mount": valid
            + b"26 24 8:1 /outside /owner/profiles/codex/opaque/runtime rw "
            b"- ext4 /dev/root rw\n",
            "nested_file_mount": valid
            + b"26 24 8:1 /outside /owner/profiles/codex/opaque/state rw "
            b"- ext4 /dev/root rw\n",
            "selected_root_mount": valid
            + b"26 24 8:1 /outside /owner/profiles/codex/opaque rw "
            b"- ext4 /dev/root rw\n",
            "duplicate_mount_id": valid + b"25 24 0:6 / /sys rw - sysfs sysfs rw\n",
            "duplicate_covering_mountpoint": valid
            + b"26 24 8:2 / / rw - ext4 /dev/other rw\n",
            "bad_escape": (
                b"24 24 8:1 / / rw - ext4 /dev/root rw\n"
                b"26 24 8:1 /bad\\777 /outside rw - ext4 /dev/root rw\n"
            ),
            "relative_root": valid
            + b"29 24 0:8 relative /outside rw - tmpfs tmpfs rw\n",
            "noncanonical_root": valid
            + b"29 24 0:8 /bad/../root /outside rw - tmpfs tmpfs rw\n",
            "double_slash_root": valid
            + b"29 24 0:8 //bad /outside rw - tmpfs tmpfs rw\n",
            "malformed_pseudo_root": valid
            + b"29 24 0:8 mnt:[0] /outside rw - nsfs nsfs rw\n",
            "pseudo_root_wrong_filesystem": valid
            + b"29 24 0:8 mnt:[4026531842] /outside rw - tmpfs tmpfs rw\n",
            "control_in_mount_options": (
                b"24 24 8:1 / / rw\tbad - ext4 /dev/root rw\n"
            ),
            "delete_in_super_options": (b"24 24 8:1 / / rw - ext4 /dev/root rw\x7f\n"),
            "crlf_delimiter": b"24 24 8:1 / / rw - ext4 /dev/root rw\r\n",
            "bare_cr_delimiter": (
                b"24 24 8:1 / / rw - ext4 /dev/root rw\r"
                b"25 24 0:5 / /proc rw - proc proc rw\n"
            ),
            "relative_mountpoint": b"24 24 8:1 / relative rw - ext4 /dev/root rw\n",
            "missing_separator": b"24 24 8:1 / / rw ext4 /dev/root rw\n",
            "empty": b"",
            "no_covering_mount": (b"24 24 8:1 / /unrelated rw - ext4 /dev/root rw\n"),
            "oversized": b"x" * (containment._PROC_MOUNTINFO_LIMIT_BYTES + 1),
        }
        for label, payload in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    containment._parse_mountinfo_v1(
                        payload,
                        managed_profile_root=managed,
                    )
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_mount_topology_unverifiable",
                )

    def test_real_proc_mount_snapshot_matches_a_blocked_child(self) -> None:
        """M5-CDX-GATE-001: the traced process inherits the proved namespace."""

        input_reader, input_writer = _open_private_channel()
        ready_reader, ready_writer = _open_private_channel()
        process: subprocess.Popen[bytes] | None = None
        owned: containment._OwnedDriverProcessV1 | None = None
        tracee_pidfd = -1
        try:
            with tempfile.TemporaryDirectory() as raw:
                managed = Path(raw) / "managed"
                managed.mkdir(mode=0o700)
                current = containment._mount_topology_snapshot_v1(managed)
                source = (
                    "import os,sys\n"
                    "input_fd,ready_fd=map(int,sys.argv[1:3])\n"
                    "os.write(ready_fd,str(os.getpid()).encode('ascii'))\n"
                    "os.close(ready_fd)\n"
                    "os.read(input_fd,1)\n"
                )
                process = _start_containment_process(
                    [
                        "/usr/bin/strace",
                        "--kill-on-exit",
                        "-f",
                        "-qq",
                        "-e",
                        "trace=none",
                        "-e",
                        "signal=none",
                        "-o",
                        os.devnull,
                        "--",
                        "/usr/bin/python3",
                        "-I",
                        "-c",
                        source,
                        str(input_reader),
                        str(ready_writer),
                    ],
                    cwd=managed,
                    environment={
                        "LANG": "C.UTF-8",
                        "LC_ALL": "C.UTF-8",
                        "PATH": "/usr/bin:/bin",
                    },
                    pass_fds=(input_reader, ready_writer),
                )
                owned = containment._bind_owned_driver_process_group_v1(process)
                os.close(input_reader)
                input_reader = -1
                os.close(ready_writer)
                ready_writer = -1

                self.assertFalse(
                    containment._owned_driver_exit_observed_v1(
                        owned,
                        deadline_monotonic=time.monotonic(),
                    )
                )
                self.assertEqual(
                    Path(f"/proc/{process.pid}/exe").resolve(strict=True),
                    Path("/usr/bin/strace").resolve(strict=True),
                )
                readable, _, _ = select.select([ready_reader], [], [], 5.0)
                self.assertEqual(readable, [ready_reader])
                tracee_pid_bytes = os.read(ready_reader, 32)
                self.assertRegex(tracee_pid_bytes, rb"[1-9][0-9]{0,9}\Z")
                tracee_pid = int(tracee_pid_bytes)
                tracee_pidfd = os.pidfd_open(tracee_pid, 0)
                self.assertEqual(os.getpgid(tracee_pid), process.pid)
                self.assertEqual(os.getsid(tracee_pid), process.pid)
                tracee_exited, _, _ = select.select([tracee_pidfd], [], [], 0)
                self.assertEqual(tracee_exited, [])

                child = containment._mount_topology_snapshot_v1(
                    managed,
                    process_id=process.pid,
                    expected_process_start_time_ticks=owned.start_time_ticks,
                )
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    containment._mount_topology_snapshot_v1(
                        managed,
                        process_id=process.pid,
                        expected_process_start_time_ticks=owned.start_time_ticks + 1,
                    )
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_mount_topology_unverifiable",
                )
                self.assertEqual(child, current)

                containment._terminate_and_reap_driver_process_group_v1(owned)
                self.assertEqual(owned.pidfd, -1)
                self.assertIsNotNone(process.returncode)
                tracee_exited, _, _ = select.select([tracee_pidfd], [], [], 2.0)
                self.assertEqual(tracee_exited, [tracee_pidfd])
        finally:
            if owned is not None and owned.pidfd >= 0:
                containment._terminate_and_reap_driver_process_group_v1(owned)
            elif process is not None and process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
            for descriptor in (
                input_reader,
                input_writer,
                ready_reader,
                ready_writer,
                tracee_pidfd,
            ):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

    def test_mount_topology_identity_and_covering_mount_drift_fail_closed(
        self,
    ) -> None:
        """M5-CDX-GATE-001: namespace and active covering mount stay fixed."""

        with tempfile.TemporaryDirectory() as raw:
            managed = Path(raw) / "managed"
            managed.mkdir(mode=0o700)
            current = containment._mount_topology_snapshot_v1(managed)
        snapshot_type = type(current)
        mount_type = type(current.covering_mount)
        namespace_changed = snapshot_type(
            (current.namespace_identity[0], current.namespace_identity[1] + 1),
            current.covering_mount,
        )
        covering_changed = snapshot_type(
            current.namespace_identity,
            mount_type(
                current.covering_mount.mount_id + 1,
                current.covering_mount.parent_id,
                current.covering_mount.device_major,
                current.covering_mount.device_minor,
                current.covering_mount.root,
                current.covering_mount.mount_point,
            ),
        )
        for label, observed in {
            "namespace": namespace_changed,
            "covering_mount": covering_changed,
        }.items():
            with self.subTest(label=label):
                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    containment._require_same_mount_topology_v1(current, observed)
                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_mount_topology_unverifiable",
                )

    def test_real_strace_ftruncate_annotation_is_strict(self) -> None:
        """M5-CDX-GATE-001: real -yy targets pass only without delimiters."""

        source = (
            "import os,sys\n"
            "fd=os.open(sys.argv[1],os.O_RDWR|os.O_CREAT|os.O_CLOEXEC,0o600)\n"
            "os.write(fd,b'abc')\n"
            "os.ftruncate(fd,3)\n"
            "os.close(fd)\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            for label, target in {
                "ordinary": root / "state",
                "delimiter": root / "state>name",
            }.items():
                with self.subTest(label=label):
                    trace_path = root / f"trace-{label}"
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
                            "trace=ftruncate",
                            "-e",
                            "signal=none",
                            "-o",
                            os.fspath(trace_path),
                            "--",
                            "/usr/bin/python3",
                            "-I",
                            "-c",
                            source,
                            os.fspath(target),
                        ],
                        cwd=root,
                        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        timeout=10,
                    )
                    self.assertEqual(process.returncode, 0)
                    lines = tuple(
                        line
                        for line in trace_path.read_text(encoding="utf-8").splitlines()
                        if " ftruncate(" in line
                    )
                    self.assertEqual(len(lines), 1)
                    record = containment._trace_records(lines[0])[0]
                    if label == "ordinary":
                        self.assertEqual(
                            containment._ftruncate_target_v1(record),
                            target,
                        )
                    else:
                        with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                            containment._ftruncate_target_v1(record)
                        self.assertEqual(
                            str(raised.exception),
                            "m5_codex_containment_trace_invalid",
                        )

    def test_real_strace_unlinkat_numeric_dirfd_is_resolved(self) -> None:
        """M5-CDX-GATE-001: real -yy relative unlink has a canonical fd base."""

        source = (
            "import os,sys\n"
            "root=sys.argv[1]\n"
            "target=os.path.join(root,'state')\n"
            "open(target,'xb').close()\n"
            "fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)\n"
            "os.unlink('state',dir_fd=fd)\n"
            "os.close(fd)\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            trace_path = root / "trace"
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
                    "trace=unlinkat",
                    "-e",
                    "signal=none",
                    "-o",
                    os.fspath(trace_path),
                    "--",
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    source,
                    os.fspath(root),
                ],
                cwd=root,
                env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            self.assertEqual(process.returncode, 0)
            self.assertFalse((root / "state").exists())
            lines = tuple(
                line
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if " unlinkat(" in line
            )
            self.assertEqual(len(lines), 1)
            record = containment._trace_records(lines[0])[0]
            self.assertEqual(
                containment._trace_paths(
                    record,
                    working_root=root / "unrelated",
                ),
                (root / "state",),
            )

    def test_real_strace_arg0_session_lock_lifecycle_has_exact_grammar(self) -> None:
        """M5-CDX-GATE-001: Linux exposes the pinned session and lock shape."""

        source = (
            "import ctypes,os,sys\n"
            "libc=ctypes.CDLL(None,use_errno=True)\n"
            "session=os.fsencode(sys.argv[1]+'/codex-arg0A1b2C3')\n"
            "lock=session+b'/.lock'\n"
            "assert libc.syscall(83,ctypes.c_char_p(session),0o777)==0\n"
            "fd=libc.syscall(2,ctypes.c_char_p(lock),2|64|0x8000|0x80000,0o666)\n"
            "assert fd>=0\n"
            "os.close(fd)\n"
            "dirfd=os.open(os.fsdecode(session),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)\n"
            "assert libc.syscall(263,dirfd,ctypes.c_char_p(b'.lock'),0)==0\n"
            "os.close(dirfd)\n"
            "os.rmdir(os.fsdecode(session))\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            trace_path = root / "trace"
            session = root / "codex-arg0A1b2C3"
            lock = session / _ARG0_LOCK_NAME
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
                    "trace=mkdir,open,unlinkat",
                    "-e",
                    "signal=none",
                    "-o",
                    os.fspath(trace_path),
                    "--",
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    source,
                    os.fspath(root),
                ],
                cwd=root,
                env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            self.assertEqual(process.returncode, 0)
            records = containment._trace_records(
                "\n".join(
                    line
                    for line in trace_path.read_text(encoding="utf-8").splitlines()
                    if os.fspath(session) in line or '".lock"' in line
                )
            )
            self.assertEqual(
                tuple(record.call for record in records),
                ("mkdir", "open", "unlinkat"),
            )
            self.assertEqual(records[0].arguments, f'"{session}", 0777')
            self.assertEqual(records[0].result, "0")
            self.assertEqual(
                records[1].arguments,
                f'"{lock}", {_ARG0_LOCK_FLAGS}, 0666',
            )
            self.assertRegex(
                records[1].result, rf"^[0-9]+<{re.escape(os.fspath(lock))}>$"
            )
            self.assertEqual(
                containment._trace_paths(records[2], working_root=root / "other"),
                (lock,),
            )
            self.assertEqual(containment._unlinkat_flags_v1(records[2]), "0")

    def test_real_strace_symlink_direction_and_cleanup_are_exact(self) -> None:
        """M5-CDX-GATE-001: Linux link payload and fd cleanup stay directional."""

        source = (
            "import os,sys\n"
            "root=sys.argv[1]\n"
            "payload=os.path.join(root,'payload')\n"
            "alias=os.path.join(root,'alias')\n"
            "open(payload,'xb').close()\n"
            "os.symlink(payload,alias)\n"
            "fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)\n"
            "os.unlink('alias',dir_fd=fd)\n"
            "os.close(fd)\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            trace_path = root / "trace"
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
                    "trace=symlink,unlinkat",
                    "-e",
                    "signal=none",
                    "-o",
                    os.fspath(trace_path),
                    "--",
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    source,
                    os.fspath(root),
                ],
                cwd=root,
                env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            self.assertEqual(process.returncode, 0)
            self.assertFalse((root / "alias").exists())
            records = containment._trace_records(
                "\n".join(
                    line
                    for line in trace_path.read_text(encoding="utf-8").splitlines()
                    if " symlink(" in line or " unlinkat(" in line
                )
            )
            self.assertEqual(
                tuple(record.call for record in records), ("symlink", "unlinkat")
            )
            payload, created, absolute = containment._symlink_arguments_v1(
                records[0],
                working_root=root / "unrelated",
            )
            self.assertEqual(payload, os.fspath(root / "payload"))
            self.assertEqual(created, root / "alias")
            self.assertTrue(absolute)
            self.assertEqual(
                containment._trace_paths(
                    records[0],
                    working_root=root / "unrelated",
                ),
                (root / "alias",),
            )
            self.assertEqual(
                containment._trace_paths(
                    records[1],
                    working_root=root / "unrelated",
                ),
                (root / "alias",),
            )
            self.assertEqual(containment._unlinkat_flags_v1(records[1]), "0")

    def test_real_isolated_bind_mount_beneath_profile_fails_closed(self) -> None:
        """M5-CDX-GATE-001: a real same-filesystem bind alias is rejected."""

        source = (
            "import pathlib,subprocess,sys,tempfile\n"
            "from tools.automation.implementations.m5_codex_containment "
            "import M5CodexContainmentErrorV1,_mount_topology_snapshot_v1\n"
            "with tempfile.TemporaryDirectory() as raw:\n"
            " root=pathlib.Path(raw)\n"
            " source=root/'outside'\n"
            " managed=root/'managed'\n"
            " target=managed/'nested'\n"
            " source.mkdir(); managed.mkdir(); target.mkdir()\n"
            " mounted=subprocess.run(['/usr/bin/mount','--bind',str(source),"
            "str(target)],stdout=subprocess.DEVNULL,"
            "stderr=subprocess.DEVNULL,check=False)\n"
            " if mounted.returncode != 0: raise SystemExit(4)\n"
            " outcome=6\n"
            " try:\n"
            "  try: _mount_topology_snapshot_v1(managed)\n"
            "  except M5CodexContainmentErrorV1 as error:\n"
            "   outcome=0 if str(error)=="
            "'m5_codex_containment_mount_topology_unverifiable' else 5\n"
            " finally:\n"
            "  unmounted=subprocess.run(['/usr/bin/umount',str(target)],"
            "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,"
            "check=False)\n"
            " if unmounted.returncode != 0: raise SystemExit(7)\n"
            " raise SystemExit(outcome)\n"
        )
        process = subprocess.run(
            [
                "/usr/bin/unshare",
                "--user",
                "--map-root-user",
                "--mount",
                "--fork",
                "--",
                os.fspath(containment._BACKEND_PYTHON),
                "-c",
                source,
            ],
            cwd=containment.ROOT,
            env={
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": os.pathsep.join(
                    (os.fspath(containment.ROOT), os.fspath(containment.BACKEND_SOURCE))
                ),
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )

        self.assertEqual(process.returncode, 0)

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
            closed = descriptors.pop()
            os.close(closed)
            os.environ[variable] = str(closed)
            with self.assertRaises(M5CodexContainmentErrorV1):
                containment._inherited_descriptor(variable)
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

    def test_early_failure_terminates_and_reaps_the_real_driver_group(self) -> None:
        """M5-CDX-GATE-001: pre-channel failure leaves no owned process alive."""

        control_reader, control_writer = os.pipe2(os.O_CLOEXEC)
        leader_pidfd = -1
        descendant_pidfd = -1
        process: subprocess.Popen[bytes] | None = None
        try:
            source = (
                "import os,sys,time\n"
                "control_fd=int(sys.argv[1])\n"
                "child=os.fork()\n"
                "if child == 0:\n"
                " os.close(control_fd)\n"
                " time.sleep(30)\n"
                " os._exit(0)\n"
                "os.write(control_fd,str(child).encode('ascii'))\n"
                "os.close(control_fd)\n"
                "os._exit(0)\n"
            )
            process = subprocess.Popen(
                ["/usr/bin/python3", "-I", "-c", source, str(control_writer)],
                cwd="/",
                env={"LANG": "C.UTF-8"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(control_writer,),
                shell=False,
                start_new_session=True,
            )
            os.close(control_writer)
            control_writer = -1
            leader_pidfd = os.pidfd_open(process.pid)
            descendant_pid = int(os.read(control_reader, 32).decode("ascii"))
            descendant_pidfd = os.pidfd_open(descendant_pid)
            readable, _, _ = select.select([leader_pidfd], [], [], 2.0)
            self.assertEqual(readable, [leader_pidfd])

            containment._terminate_and_reap_driver_process_group_v1(
                process,
                deadline_monotonic=(
                    time.monotonic() + containment._CHANNEL_SETTLEMENT_SECONDS
                ),
            )

            self.assertIsNotNone(process.poll())
            readable, _, _ = select.select([descendant_pidfd], [], [], 2.0)
            self.assertEqual(readable, [descendant_pidfd])
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
                control_reader,
                control_writer,
                leader_pidfd,
                descendant_pidfd,
            ):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

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

    def test_managed_profile_tree_rejects_a_retained_arg0_alias(self) -> None:
        """M5-CDX-GATE-001: an Arg0-shaped alias must be gone after cleanup."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            session = managed / "tmp" / "arg0" / "codex-arg0A1b2C3"
            session.mkdir(parents=True, mode=0o700)
            payload = root / "codex"
            payload.write_bytes(b"provider")
            payload.chmod(0o700)
            (session / "apply_patch").symlink_to(payload)

            with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                _managed_profile_tree_digest(managed)

            self.assertEqual(
                str(raised.exception), "m5_codex_containment_profile_tree_invalid"
            )

    def test_managed_profile_tree_rejects_retained_arg0_regular_children(self) -> None:
        """M5-CDX-GATE-001: no lock or other session child survives cleanup."""

        for child in (_ARG0_LOCK_NAME, "unexpected"):
            with self.subTest(child=child), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                root.chmod(0o700)
                managed = root / "managed"
                managed.mkdir(mode=0o700)
                before = containment._managed_profile_tree_snapshot(managed)
                session = managed / "tmp" / "arg0" / "codex-arg0A1b2C3"
                session.mkdir(parents=True, mode=0o700)
                (session / child).write_bytes(b"")
                (session / child).chmod(0o600)
                after = containment._managed_profile_tree_snapshot(managed)

                with self.assertRaises(M5CodexContainmentErrorV1) as raised:
                    containment._validate_no_new_arg0_children_v1(before, after)

                self.assertEqual(
                    str(raised.exception),
                    "m5_codex_containment_profile_tree_invalid",
                )

    def test_managed_profile_tree_allows_preexisting_or_empty_arg0_sessions(
        self,
    ) -> None:
        """M5-CDX-GATE-001: optional empty cleanup and stale state stay scoped."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            root.chmod(0o700)
            managed = root / "managed"
            managed.mkdir(mode=0o700)
            stale = managed / "tmp" / "arg0" / "codex-arg0A1b2C3"
            stale.mkdir(parents=True, mode=0o700)
            (stale / "preexisting").write_bytes(b"")
            (stale / "preexisting").chmod(0o600)
            before = containment._managed_profile_tree_snapshot(managed)
            empty = stale.with_name("codex-arg0D4e5F6")
            empty.mkdir(mode=0o700)
            after = containment._managed_profile_tree_snapshot(managed)

            containment._validate_no_new_arg0_children_v1(before, after)

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
            managed.chmod(0o755)
            self.assertEqual(stat.S_IMODE(managed.lstat().st_mode), 0o755)

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
                        after = type(after)(
                            after.digest,
                            tuple(identities),
                            after.arg0_child_path_digests,
                        )
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

        from tools.automation.implementations.m5_evidence_migration import (
            current_service_binding_v1,
        )

        revision, service_pid, service_ticks = current_service_binding_v1(
            os.environ,
            (
                os.environ["AGENTMONITOR_M5_OWNER_IMPLEMENTATION_REVISION"],
                int(os.environ["AGENTMONITOR_M5_OWNER_SERVICE_PID"]),
                int(os.environ["AGENTMONITOR_M5_OWNER_SERVICE_START_TIME_TICKS"]),
            ),
        )

        evidence = verify_codex_managed_profile_containment_v1(
            owner_data_root=owner_root,
            account_id=account_id,
            managed_profiles_root=managed_profiles_root,
            managed_profile_root=managed_profile_root,
            revision=revision,
            service_pid=service_pid,
            service_start_time_ticks=service_ticks,
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
