"""ST-IAM-002 session-bound CSRF using real migrated SQLite."""

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
    VerifyCsrfV1,
)


def test_csrf_cookie_header_and_database_binding_are_required(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    login = AuthenticateAdministratorV1(repository, Argon2PasswordV1())
    first = login(SecretInputV1(owner_credential), correlation_id="csrf-first")
    second = login(SecretInputV1(owner_credential), correlation_id="csrf-second")
    assert isinstance(first, SessionCredentialIssueV1)
    assert isinstance(second, SessionCredentialIssueV1)
    verify = VerifyCsrfV1(repository)
    assert (
        verify(
            second.session.session_id,
            SecretInputV1(second.csrf_credential),
            SecretInputV1(second.csrf_credential),
            correlation_id="csrf-valid",
        ).code
        == "valid"
    )
    assert verify(
        second.session.session_id, None, None, correlation_id="csrf-missing"
    ).code == ("csrf_validation_failed")
    assert (
        verify(
            second.session.session_id,
            SecretInputV1(first.csrf_credential),
            SecretInputV1(first.csrf_credential),
            correlation_id="csrf-cross-session",
        ).code
        == "csrf_validation_failed"
    )
    assert (
        verify(
            second.session.session_id,
            SecretInputV1(second.csrf_credential),
            SecretInputV1(first.csrf_credential),
            correlation_id="csrf-mismatch",
        ).code
        == "csrf_validation_failed"
    )


def test_corrupt_unrevoked_row_without_session_digest_cannot_pass_csrf(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    issued = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="csrf-corrupt-login"
    )
    assert isinstance(issued, SessionCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE iam_browser_session SET credential_digest=NULL "
                "WHERE session_id=?",
                (issued.session.session_id.value,),
            )
            connection.commit()
    decision = VerifyCsrfV1(repository)(
        issued.session.session_id,
        SecretInputV1(issued.csrf_credential),
        SecretInputV1(issued.csrf_credential),
        correlation_id="csrf-corrupt-check",
    )
    assert decision.code == "csrf_validation_failed"


def test_nonascii_persisted_csrf_digest_fails_closed_without_raw_type_error(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    issued = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="csrf-digest-corrupt-login"
    )
    assert isinstance(issued, SessionCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE iam_browser_session SET csrf_digest=? WHERE session_id=?",
                ("é" * 64, issued.session.session_id.value),
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1) as failure:
        VerifyCsrfV1(repository)(
            issued.session.session_id,
            SecretInputV1(issued.csrf_credential),
            SecretInputV1(issued.csrf_credential),
            correlation_id="csrf-digest-corrupt-check",
        )
    assert str(failure.value) == "iam_repository_unavailable"
