"""Local recovery against a real migrated installation, PTY, and service lock."""

import asyncio
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
from agentmonitor.adapters.persistence.identity_access.sqlite.api_tokens import (
    SqliteIdentityAccessApiTokenRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.sessions import (
    SqliteIdentityAccessSessionRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application, serve_loopback
from agentmonitor.contracts.identity_access_v1 import (
    ApiTokenCredentialIssueV1,
    SecretInputV1,
    SessionCredentialIssueV1,
    TokenCallerProofV1,
)
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.identity_access.application.api_tokens import (
    CreateApiTokenV1,
    ResolveBearerTokenV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
    ResolveBrowserSessionV1,
)

MODULE = "agentmonitor.composition.iam_operator"


def _operator_environment() -> dict[str, str]:
    return {"PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}


def _run_recovery_pty(root: Path, new_password: bytes | None) -> tuple[int, bytes]:
    child, master = pty.fork()
    if child == 0:
        os.execve(
            sys.executable,
            [sys.executable, "-m", MODULE, "recover", "--data-root", str(root)],
            _operator_environment(),
        )
    captured = bytearray()
    sent = 0
    status: int | None = None
    deadline = time.monotonic() + 12
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    chunk = b""
                captured.extend(chunk)
                if len(captured) > 8192:
                    break
                if (
                    new_password is not None
                    and sent == 0
                    and b"Enter dashboard password:" in captured
                ):
                    os.write(master, new_password + b"\n")
                    sent = 1
                if (
                    new_password is not None
                    and sent == 1
                    and b"Confirm dashboard password:" in captured
                ):
                    os.write(master, new_password + b"\n")
                    sent = 2
            completed, result = os.waitpid(child, os.WNOHANG)
            if completed:
                status = result
                break
        if status is None:
            os.kill(child, signal.SIGTERM)
            _, status = os.waitpid(child, 0)
    finally:
        os.close(master)
    return os.waitstatus_to_exitcode(status), bytes(captured)


def _installation(root: Path) -> tuple[DatabaseRefV1, str, str, str]:
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    migrate_to_head(reference)
    old_password = secrets.token_urlsafe(32)
    created = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(old_password), correlation_id="recovery-test-bootstrap")
    assert created.code == "created"
    sessions = SqliteIdentityAccessSessionRepositoryV1(reference)
    issued_session = AuthenticateAdministratorV1(sessions, Argon2PasswordV1())(
        SecretInputV1(old_password), correlation_id="recovery-test-login"
    )
    assert isinstance(issued_session, SessionCredentialIssueV1)
    caller = TokenCallerProofV1(
        "browser_session",
        SecretInputV1(issued_session.session_credential),
        SecretInputV1(issued_session.csrf_credential),
        SecretInputV1(issued_session.csrf_credential),
    )
    tokens = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issued_token = CreateApiTokenV1(tokens)(
        caller,
        name="recovery-test-token",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="recovery_test_issue_0001",
        correlation_id="recovery-test-token",
    )
    assert isinstance(issued_token, ApiTokenCredentialIssueV1)
    return (
        reference,
        old_password,
        issued_session.session_credential,
        issued_token.bearer_credential,
    )


def test_recovery_invalidates_populated_credentials_and_audits(tmp_path: Path) -> None:
    reference, old_password, session_credential, bearer_credential = _installation(
        tmp_path
    )
    new_password = secrets.token_urlsafe(32)
    status, output = _run_recovery_pty(tmp_path, new_password.encode("ascii"))
    success_marker_seen = b"administrator_recovered" in output
    plaintext_not_echoed = new_password.encode("ascii") not in output
    assert status == 0
    assert success_marker_seen is True
    assert plaintext_not_echoed is True
    assert (tmp_path / ".agentmonitor-service.lock").is_file()

    sessions = SqliteIdentityAccessSessionRepositoryV1(reference)
    tokens = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    assert (
        ResolveBrowserSessionV1(sessions)(
            SecretInputV1(session_credential), correlation_id="recovery-old-session"
        ).code
        == "dashboard_authentication_required"
    )
    assert (
        ResolveBearerTokenV1(tokens)(
            SecretInputV1(bearer_credential), correlation_id="recovery-old-token"
        ).code
        == "dashboard_authentication_required"
    )
    old_login = AuthenticateAdministratorV1(sessions, Argon2PasswordV1())(
        SecretInputV1(old_password), correlation_id="recovery-old-password"
    )
    assert old_login.code == "invalid_credentials"
    new_login = AuthenticateAdministratorV1(sessions, Argon2PasswordV1())(
        SecretInputV1(new_password), correlation_id="recovery-new-password"
    )
    assert isinstance(new_login, SessionCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            recovery_event = connection.exec_driver_sql(
                "SELECT aggregate_count, outcome_code, correlation_id "
                "FROM iam_security_audit_event "
                "WHERE event_type='administrator_recovered'"
            ).one()
            invalidated_sessions = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_browser_session "
                "WHERE revocation_reason='local_recovery' "
                "AND credential_digest IS NULL "
                "AND csrf_digest IS NULL"
            ).scalar_one()
            invalidated_tokens = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_api_token "
                "WHERE revocation_reason='local_recovery' "
                "AND verification_digest IS NULL"
            ).scalar_one()
    assert invalidated_sessions == 1
    assert invalidated_tokens == 1
    assert tuple(recovery_event) == (2, "recovered", "local-tty-recovery")


def test_unsafe_service_lock_symlink_refuses_before_password_prompt(
    tmp_path: Path,
) -> None:
    reference, _, _, _ = _installation(tmp_path)
    target = tmp_path / "unrelated-owner-file"
    target.write_bytes(b"preserve-this-file")
    target.chmod(0o600)
    (tmp_path / ".agentmonitor-service.lock").symlink_to(target)
    before = reference._path.read_bytes()
    status, output = _run_recovery_pty(tmp_path, None)
    password_prompt_absent = b"Enter dashboard password:" not in output
    target_unchanged = target.read_bytes() == b"preserve-this-file"
    database_unchanged = reference._path.read_bytes() == before
    assert status == 2
    assert password_prompt_absent is True
    assert target_unchanged is True
    assert database_unchanged is True


def test_recovery_password_policy_denial_preserves_existing_credentials(
    tmp_path: Path,
) -> None:
    reference, old_password, session_credential, bearer_credential = _installation(
        tmp_path
    )
    status, output = _run_recovery_pty(tmp_path, b"short")
    policy_denial_seen = b"password_policy_violation" in output
    plaintext_not_echoed = b"short" not in output
    assert status == 2
    assert policy_denial_seen is True
    assert plaintext_not_echoed is True
    assert (
        ResolveBrowserSessionV1(SqliteIdentityAccessSessionRepositoryV1(reference))(
            SecretInputV1(session_credential), correlation_id="recovery-policy-session"
        ).code
        == "authenticated"
    )
    assert (
        ResolveBearerTokenV1(SqliteIdentityAccessApiTokenRepositoryV1(reference))(
            SecretInputV1(bearer_credential), correlation_id="recovery-policy-token"
        ).code
        == "authenticated"
    )
    valid_login = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(old_password), correlation_id="recovery-policy-password")
    assert isinstance(valid_login, SessionCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            count = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_security_audit_event "
                "WHERE event_type='administrator_recovered'"
            ).scalar_one()
    assert count == 0


def test_running_service_lock_refuses_recovery_before_password_prompt(
    tmp_path: Path,
) -> None:
    reference, old_password, session_credential, bearer_credential = _installation(
        tmp_path
    )
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())

    async def exercise() -> None:
        stop = asyncio.Event()
        ready: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        server = asyncio.create_task(
            serve_loopback(
                app, host="127.0.0.1", port=0, ready=ready.set_result, stop=stop
            )
        )
        try:
            await asyncio.wait_for(ready, timeout=8)
            # The service already owns flock; a brief synchronous PTY child
            # avoids forking from a worker thread while that lock is held.
            status, output = _run_recovery_pty(tmp_path, None)
            lock_denial_seen = b"service_lock_occupied" in output
            password_prompt_absent = b"Enter dashboard password:" not in output
            assert status == 2
            assert lock_denial_seen is True
            assert password_prompt_absent is True
        finally:
            stop.set()
            await asyncio.wait_for(server, timeout=8)

    asyncio.run(exercise())
    assert (
        ResolveBrowserSessionV1(SqliteIdentityAccessSessionRepositoryV1(reference))(
            SecretInputV1(session_credential), correlation_id="recovery-locked-session"
        ).code
        == "authenticated"
    )
    assert (
        ResolveBearerTokenV1(SqliteIdentityAccessApiTokenRepositoryV1(reference))(
            SecretInputV1(bearer_credential), correlation_id="recovery-locked-token"
        ).code
        == "authenticated"
    )
    assert (
        AuthenticateAdministratorV1(
            SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
        )(SecretInputV1(old_password), correlation_id="recovery-locked-password").code
        != "invalid_credentials"
    )


def test_recovery_refuses_noninteractive_and_password_arguments(tmp_path: Path) -> None:
    reference, _, _, _ = _installation(tmp_path)
    before = reference._path.read_bytes()
    redirected = subprocess.run(
        [sys.executable, "-m", MODULE, "recover", "--data-root", str(tmp_path)],
        input="",
        capture_output=True,
        text=True,
        env=_operator_environment(),
        timeout=10,
        check=False,
    )
    with_argument = subprocess.run(
        [
            sys.executable,
            "-m",
            MODULE,
            "recover",
            "--data-root",
            str(tmp_path),
            "--password=forbidden",
        ],
        capture_output=True,
        text=True,
        env=_operator_environment(),
        timeout=10,
        check=False,
    )
    redirected_status_seen = redirected.stdout == "controlling_tty_required\n"
    argument_denial_seen = with_argument.stdout == "invalid_operator_arguments\n"
    database_unchanged = reference._path.read_bytes() == before
    assert redirected.returncode == 2
    assert redirected_status_seen is True
    assert with_argument.returncode == 2
    assert argument_denial_seen is True
    assert database_unchanged is True
