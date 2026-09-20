"""ST-IAM-002 real file-backed browser-session lifecycle."""

import json
import pickle
import secrets

import pytest
from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    IdentityAccessRepositoryErrorV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.sessions import (
    SqliteIdentityAccessSessionRepositoryV1,
)
from agentmonitor.contracts.identity_access_v1 import (
    SecretInputV1,
    SessionCredentialIssueV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
    LogoutSessionV1,
    ResolveBrowserSessionV1,
)


def test_fresh_login_is_digest_only_and_revocation_survives_reopen(
    real_iam_installation: tuple[DatabaseRefV1, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    first = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="session-first"
    )
    second = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="session-second"
    )
    assert isinstance(first, SessionCredentialIssueV1)
    assert isinstance(second, SessionCredentialIssueV1)
    assert first.session.session_id != second.session.session_id
    resolved = ResolveBrowserSessionV1(repository)(
        SecretInputV1(first.session_credential), correlation_id="session-resolve"
    )
    assert resolved.code == "authenticated"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT credential_selector, credential_digest, csrf_digest "
                "FROM iam_browser_session"
            ).all()
            assert len(rows) == 2
            assert all(len(row[1]) == 64 and len(row[2]) == 64 for row in rows)
            paths = [reference._path]
            paths.extend(
                reference._path.with_name(reference._path.name + suffix)
                for suffix in ("-wal", "-shm", "-journal")
            )
            assert paths[1].exists(), "real_sqlite_wal_not_present_during_scan"
            artifact_bytes = [path.read_bytes() for path in paths if path.exists()]
            secrets_absent = all(
                value.encode("ascii") not in artifact
                for value in (
                    owner_credential,
                    first.session_credential,
                    first.csrf_credential,
                    second.session_credential,
                    second.csrf_credential,
                )
                for artifact in artifact_bytes
            )
            assert secrets_absent is True
            logs_safe = all(
                value not in caplog.text
                for value in (
                    owner_credential,
                    first.session_credential,
                    first.csrf_credential,
                    second.session_credential,
                    second.csrf_credential,
                )
            )
            assert logs_safe is True
    assert "redacted" in repr(first)
    with pytest.raises(TypeError, match="session_issue_not_serializable"):
        pickle.dumps(first)
    with pytest.raises(TypeError):
        json.dumps(first)
    logout = LogoutSessionV1(repository)(
        first.session.session_id,
        first.session.record_version,
        SecretInputV1(first.csrf_credential),
        SecretInputV1(first.csrf_credential),
        correlation_id="session-logout",
    )
    assert logout.code == "revoked"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            terminal = connection.exec_driver_sql(
                "SELECT revoked_at, revocation_reason, credential_digest, "
                "csrf_digest FROM iam_browser_session WHERE session_id=?",
                (first.session.session_id.value,),
            ).one()
    assert terminal[0] is not None
    assert terminal[1:] == ("logout", None, None)
    reopened = SqliteIdentityAccessSessionRepositoryV1(reference)
    assert (
        ResolveBrowserSessionV1(reopened)(
            SecretInputV1(first.session_credential), correlation_id="session-old-denied"
        ).code
        == "dashboard_authentication_required"
    )
    assert (
        ResolveBrowserSessionV1(reopened)(
            SecretInputV1(second.session_credential),
            correlation_id="session-second-resolved",
        ).code
        == "authenticated"
    )


def test_malformed_and_unknown_credentials_share_one_safe_outcome(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, _ = real_iam_installation
    resolve = ResolveBrowserSessionV1(
        SqliteIdentityAccessSessionRepositoryV1(reference)
    )
    unknown = resolve(
        SecretInputV1(f"am-s1.{secrets.token_urlsafe(16)}.{secrets.token_urlsafe(32)}"),
        correlation_id="session-unknown",
    )
    random_value = resolve(
        SecretInputV1(secrets.token_urlsafe(48)), correlation_id="session-malformed"
    )
    assert unknown.code == random_value.code == "dashboard_authentication_required"


def test_malformed_persisted_session_time_fails_with_safe_repository_code(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    issued = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="corrupt-time-login"
    )
    assert isinstance(issued, SessionCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE iam_browser_session SET idle_expires_at='malformed' "
                "WHERE session_id=?",
                (issued.session.session_id.value,),
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1) as failure:
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(issued.session_credential),
            correlation_id="session-corrupt-time",
        )
    assert str(failure.value) == "iam_repository_unavailable"


def test_nontext_persisted_session_digest_fails_closed_without_raw_type_error(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    issued = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="digest-corrupt-login"
    )
    assert isinstance(issued, SessionCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE iam_browser_session SET credential_digest=? WHERE session_id=?",
                (bytes.fromhex("01" * 32), issued.session.session_id.value),
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1) as failure:
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(issued.session_credential),
            correlation_id="digest-corrupt-resolve",
        )
    assert str(failure.value) == "iam_repository_unavailable"
