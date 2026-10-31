"""Real-system tests for the independent Codex 0.160.0 admission verifier."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.automation.implementations.m5_codex_admission import (
    M5CodexAdmissionErrorV1,
    M5CodexAdmissionEvidenceV1,
    M5CodexAdmissionUnavailableV1,
    _executable_identity,
    _resolve_executable,
    _start_admission_process,
    _validate_strace_executable,
    verify_codex_admission_v1,
)


class M5CodexAdmissionTests(unittest.TestCase):
    def test_unsupported_platform_is_typed_unavailable(self) -> None:
        """M5-CDX-GATE-001: unsupported hosts block rather than fail admission."""

        with self.assertRaises(M5CodexAdmissionUnavailableV1) as raised:
            _resolve_executable(
                system_name="Darwin",
                machine_name="arm64",
                search_path="/usr/bin:/bin",
            )

        self.assertEqual(str(raised.exception), "m5_codex_platform_unverified")

    def test_missing_executable_is_typed_unavailable(self) -> None:
        """M5-CDX-GATE-001: an absent real executable is a blocked prerequisite."""

        with (
            tempfile.TemporaryDirectory() as raw,
            self.assertRaises(M5CodexAdmissionUnavailableV1) as raised,
        ):
            _resolve_executable(
                system_name="Linux",
                machine_name="x86_64",
                search_path=raw,
            )

        self.assertEqual(str(raised.exception), "m5_codex_executable_unavailable")

    def test_missing_strace_is_typed_unavailable(self) -> None:
        """M5-CDX-GATE-001: the required real tracer is a blocked prerequisite."""

        with tempfile.TemporaryDirectory() as raw:
            missing = Path(raw) / "strace"
            with self.assertRaises(M5CodexAdmissionUnavailableV1) as raised:
                _validate_strace_executable(missing)

        self.assertEqual(str(raised.exception), "m5_codex_strace_unavailable")

    def test_popen_unavailable_is_typed_unavailable(self) -> None:
        """M5-CDX-GATE-001: an OS launch refusal is not a deterministic mismatch."""

        with (
            tempfile.TemporaryDirectory() as raw,
            self.assertRaises(M5CodexAdmissionUnavailableV1) as raised,
        ):
            _start_admission_process(
                ["/proc/self/status"],
                cwd=Path(raw),
                environment={"LANG": "C.UTF-8"},
                stdout=subprocess.DEVNULL,
            )

        self.assertEqual(str(raised.exception), "m5_codex_command_unavailable")

    def test_unsafe_executable_remains_a_deterministic_admission_failure(self) -> None:
        """M5-CDX-GATE-001: an observed unsafe binary is a failed invariant."""

        with tempfile.TemporaryDirectory() as raw:
            executable = Path(raw) / "codex"
            executable.touch(mode=0o777)
            executable.chmod(0o777)
            with self.assertRaises(M5CodexAdmissionErrorV1) as raised:
                _executable_identity(executable)

        self.assertIs(type(raised.exception), M5CodexAdmissionErrorV1)
        self.assertEqual(str(raised.exception), "m5_codex_executable_invalid")

    def test_real_installed_codex_matches_exact_discovery_and_mapping_evidence(
        self,
    ) -> None:
        """M5-CDX-GATE-001: regenerate the admitted schemas without profile access."""

        evidence = verify_codex_admission_v1()

        self.assertIsInstance(evidence, M5CodexAdmissionEvidenceV1)
        self.assertEqual(evidence.provider_version, "0.160.0")
        self.assertEqual(evidence.schema_count, 4)
        self.assertFalse(evidence.experimental_schema_mode)
        self.assertEqual(
            evidence.schema_bundle_digest,
            "36bd8e1d76b12b89b06446a85c45e957945eb8cb63b05061264c3dec97f625da",
        )
        self.assertEqual(
            evidence.mapping_digest,
            "417c46ba301f9c4217c606beed52be93c9bf497da9ca5b99ca4b1993167688d3",
        )
        self.assertEqual(evidence.default_profile_access_count, 0)
        self.assertEqual(evidence.default_profile_write_count, 0)
        self.assertNotIn("/", repr(evidence))


if __name__ == "__main__":
    unittest.main()
