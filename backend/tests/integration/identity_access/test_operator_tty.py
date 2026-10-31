"""ST-IAM-001 local operator boundary on a real Linux controlling PTY."""

import os
import pty
import secrets
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
    GetIamInitializationStateV1,
)

MODULE = "agentmonitor.composition.iam_operator"


def _environment() -> dict[str, str]:
    return {"PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}


def test_operator_refuses_redirected_input_and_password_arguments(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    before = ref._path.read_bytes()
    redirected = subprocess.run(
        [sys.executable, "-m", MODULE, "bootstrap", "--data-root", str(tmp_path)],
        input="",
        capture_output=True,
        text=True,
        env=_environment(),
        timeout=10,
        check=False,
    )
    rejected_argv = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "bootstrap",
            "--data-root",
            str(tmp_path),
            "--password=forbidden-argument",
        ],
        input="",
        capture_output=True,
        text=True,
        env=_environment(),
        timeout=10,
        check=False,
    )
    assert redirected.returncode == 2
    assert redirected.stdout == "controlling_tty_required\n"
    assert rejected_argv.returncode == 2
    assert rejected_argv.stdout == "invalid_operator_arguments\n"
    assert rejected_argv.stderr == ""
    assert ref._path.read_bytes() == before


def _read_until(master: int, marker: bytes, captured: bytearray) -> bool:
    deadline = time.monotonic() + 8
    while marker not in captured and time.monotonic() < deadline:
        ready, _, _ = select.select([master], [], [], 0.2)
        if ready:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                return False
            if not chunk:
                return False
            captured.extend(chunk)
            if len(captured) > 8192:
                return False
    return marker in captured


def test_real_controlling_tty_bootstrap_hides_input_and_initializes_once(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    owner_input = secrets.token_urlsafe(32).encode("ascii")
    child, master = pty.fork()
    if child == 0:
        os.execve(
            sys.executable,
            [sys.executable, "-m", MODULE, "bootstrap", "--data-root", str(tmp_path)],
            _environment(),
        )
    captured = bytearray()
    reaped = False
    try:
        first_prompt = _read_until(master, b"Enter dashboard password:", captured)
        if first_prompt:
            os.write(master, owner_input + b"\n")
        second_prompt = _read_until(master, b"Confirm dashboard password:", captured)
        if second_prompt:
            os.write(master, owner_input + b"\n")
        reached_result = _read_until(master, b"administrator_initialized", captured)
        deadline = time.monotonic() + 3
        status: int | None = None
        while status is None and time.monotonic() < deadline:
            completed, result = os.waitpid(child, os.WNOHANG)
            if completed:
                status = result
            else:
                time.sleep(0.05)
        if status is None:
            os.kill(child, signal.SIGTERM)
            _, status = os.waitpid(child, 0)
        reaped = True
    finally:
        if not reaped:
            os.kill(child, signal.SIGTERM)
            os.waitpid(child, 0)
        os.close(master)
    plaintext_not_echoed = owner_input not in captured
    assert first_prompt is True
    assert second_prompt is True
    assert reached_result is True
    assert os.waitstatus_to_exitcode(status) == 0
    assert plaintext_not_echoed is True

    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            administrator_count = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_administrator"
            ).scalar_one()
            audit_count = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_security_audit_event"
            ).scalar_one()
    assert administrator_count == 1
    assert audit_count == 1

    repeated_child, repeated_master = pty.fork()
    if repeated_child == 0:
        os.execve(
            sys.executable,
            [sys.executable, "-m", MODULE, "bootstrap", "--data-root", str(tmp_path)],
            _environment(),
        )
    repeated_output = bytearray()
    repeated_reaped = False
    try:
        rejected = _read_until(
            repeated_master, b"administrator_already_initialized", repeated_output
        )
        deadline = time.monotonic() + 3
        completed = 0
        repeated_status = 0
        while not completed and time.monotonic() < deadline:
            completed, repeated_status = os.waitpid(repeated_child, os.WNOHANG)
            if not completed:
                time.sleep(0.05)
        if not completed:
            os.kill(repeated_child, signal.SIGTERM)
            completed, repeated_status = os.waitpid(repeated_child, 0)
        repeated_reaped = True
        assert completed == repeated_child
    finally:
        if not repeated_reaped:
            os.kill(repeated_child, signal.SIGTERM)
            os.waitpid(repeated_child, 0)
        os.close(repeated_master)
    assert rejected is True
    assert os.waitstatus_to_exitcode(repeated_status) == 2
    assert b"Enter dashboard password:" not in repeated_output
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_administrator"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_security_audit_event"
                ).scalar_one()
                == 1
            )


def test_operator_reports_incompatible_iam_without_prompt_or_mutation(
    tmp_path: Path,
) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repository = SqliteIdentityAccessRepositoryV1(ref)
    result = BootstrapAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(secrets.token_urlsafe(32)),
        correlation_id="test-incompatible-operator",
    )
    assert result.code == "created"
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE iam_administrator SET hash_policy_version=? "
                "WHERE singleton_key=1",
                ("unsupported-policy",),
            )
            connection.commit()
            administrator_before = tuple(
                connection.exec_driver_sql(
                    "SELECT password_phc, hash_policy_version, record_version "
                    "FROM iam_administrator"
                ).one()
            )
            audit_count_before = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_security_audit_event"
            ).scalar_one()
    assert GetIamInitializationStateV1(repository)().state == "incompatible"

    child, master = pty.fork()
    if child == 0:
        os.execve(
            sys.executable,
            [sys.executable, "-m", MODULE, "bootstrap", "--data-root", str(tmp_path)],
            _environment(),
        )
    captured = bytearray()
    reaped = False
    try:
        unavailable = _read_until(master, b"iam_repository_unavailable", captured)
        deadline = time.monotonic() + 3
        completed = 0
        status = 0
        while not completed and time.monotonic() < deadline:
            completed, status = os.waitpid(child, os.WNOHANG)
            if not completed:
                time.sleep(0.05)
        if not completed:
            os.kill(child, signal.SIGTERM)
            completed, status = os.waitpid(child, 0)
        reaped = True
    finally:
        if not reaped:
            os.kill(child, signal.SIGTERM)
            os.waitpid(child, 0)
        os.close(master)
    assert unavailable is True
    assert os.waitstatus_to_exitcode(status) == 2
    assert b"administrator_already_initialized" not in captured
    assert b"Enter dashboard password:" not in captured
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            administrator_after = tuple(
                connection.exec_driver_sql(
                    "SELECT password_phc, hash_policy_version, record_version "
                    "FROM iam_administrator"
                ).one()
            )
            audit_count_after = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_security_audit_event"
            ).scalar_one()
    administrator_unchanged = administrator_after == administrator_before
    assert administrator_unchanged is True
    assert audit_count_after == audit_count_before
