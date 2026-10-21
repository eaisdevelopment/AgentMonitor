"""Pure trace policy and real-owner tests for M5 Codex containment evidence."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import inspect
import os
import re
import resource
import subprocess
import tempfile
import unittest
from pathlib import Path

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


class M5CodexContainmentPolicyTests(unittest.TestCase):
    def test_provider_writes_inside_managed_profile_are_counted(self) -> None:
        """M5-CDX-GATE-001: exact child writes remain inside the selected root."""

        managed = Path("/owner/profiles/codex/opaque")
        executable = Path(
            "/home/owner/.codex/packages/standalone/releases/0.160.0/bin/codex"
        )
        trace = "\n".join(
            (
                '100 execve("/usr/bin/python3", ["python3"], 0x0) = 0',
                f'101 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'101 openat(AT_FDCWD, "{executable}", O_RDONLY) = 3<{executable}>',
                f'102 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                f'102 openat(AT_FDCWD, "{managed}/state.sqlite", O_RDWR|O_CREAT, 0600) = 4<{managed}/state.sqlite>',
                "102 clone(child_stack=NULL, flags=SIGCHLD) = 103",
                '103 mkdir("runtime", 0700) = 0',
                f'104 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                f'104 newfstatat(AT_FDCWD, "{managed}/auth.json", {{st_mode=S_IFREG|0600}}, 0) = 0',
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 2)
        self.assertGreaterEqual(summary.provider_access_count, 5)
        self.assertEqual(summary.default_profile_access_count, 0)
        self.assertEqual(summary.default_profile_write_count, 0)

    def test_default_profile_read_fails_closed(self) -> None:
        """M5-CDX-GATE-001: even a metadata read of default auth is rejected."""

        executable = Path("/opt/codex/bin/codex")
        trace = "\n".join(
            (
                f'200 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'201 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                '201 newfstatat(AT_FDCWD, "/home/owner/.codex/auth.json", {}, 0) = 0',
                f'202 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
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
                f'250 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'251 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                f'252 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
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
                f'300 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'301 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                "301 clone3({flags=CLONE_VM}, 88) = 302",
                '302 openat(AT_FDCWD, "/tmp/codex-state", O_WRONLY|O_CREAT, 0600) = 5</tmp/codex-state>',
                f'303 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
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
                f'350 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'351 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                "351 clone(child_stack=NULL, flags=SIGCHLD <unfinished ...>",
                '352 openat(AT_FDCWD, "/tmp/escaped", O_WRONLY|O_CREAT, 0600) = 5</tmp/escaped>',
                "351 <... clone resumed>) = 352",
                f'353 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
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
                f'401 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'402 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                f'402 openat(AT_FDCWD, "{managed}/state", O_RDWR|O_CREAT, 0600) = 4<{managed}/state>',
                f'403 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_write_count, 1)

    def test_pre_exec_driver_filesystem_activity_is_not_attributed(self) -> None:
        """M5-CDX-GATE-001: a child becomes a provider only at exact exec."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                '500 chdir("/tmp/agentmonitor-codex-version") = 0',
                '500 openat(AT_FDCWD, "/tmp/driver-state", O_WRONLY|O_CREAT, 0600) = 4</tmp/driver-state>',
                f'500 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                '501 chdir("/owner/private-driver") = 0',
                f'501 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                f'501 openat(AT_FDCWD, "{managed}/state", O_RDWR|O_CREAT, 0600) = 4<{managed}/state>',
                f'502 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 1)

    def test_exited_provider_pid_is_not_attributed_after_reuse(self) -> None:
        """M5-CDX-GATE-001: process exit closes its provider attribution epoch."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                f'550 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                "550 exit_group(0) = ?",
                f'551 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                "551 exit_group(0) = ?",
                '551 openat(AT_FDCWD, "/tmp/reused-pid-state", O_WRONLY|O_CREAT, 0600) = 4</tmp/reused-pid-state>',
                f'552 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
            )
        )

        summary = evaluate_codex_trace_policy_v1(
            trace,
            provider_executable=executable,
            managed_profile_root=managed,
            default_codex_roots=(Path("/home/owner/.codex"),),
        )

        self.assertEqual(summary.provider_execution_count, 3)
        self.assertEqual(summary.provider_write_count, 0)

    def test_numeric_dirfd_relative_write_fails_closed(self) -> None:
        """M5-CDX-GATE-001: an unresolved dirfd cannot imply managed scope."""

        executable = Path("/opt/codex/bin/codex")
        managed = Path("/owner/profiles/codex/opaque")
        trace = "\n".join(
            (
                f'600 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'601 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                '601 openat(9</outside>, "escaped", O_WRONLY|O_CREAT, 0600) = 5</outside/escaped>',
                f'602 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
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
                f'700 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'701 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                f'701 openat(AT_FDCWD</outside>, "{managed}/link/state", O_WRONLY|O_CREAT, 0600) = 5</outside/state>',
                f'702 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
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
                f'750 execve("{executable}", ["codex", "--version"], 0x0) = 0',
                f'751 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
                f'751 truncate("{managed}/possible-link", 0) = 0',
                f'752 execve("{executable}", ["codex", "app-server", "stdio://"], 0x0) = 0',
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
        result_payload = Path("/proc/sys/kernel/random/boot_id").read_bytes()
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

            returncode, observed_result, observed_trace = _collect_driver_channels(
                process,
                input_descriptor=owned_input_writer,
                input_payload=payload,
                result_descriptor=result_reader,
                trace_descriptor=trace_reader,
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
