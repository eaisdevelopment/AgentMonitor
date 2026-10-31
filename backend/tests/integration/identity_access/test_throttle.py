"""Global throttle survives real SQLite repository reopen."""

import secrets
from concurrent.futures import ThreadPoolExecutor

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
    AuthenticationFailureV1,
    SecretInputV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
)


def test_five_real_wrong_passwords_lock_and_reopen_preserves_lock(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    login = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )
    wrong_input = SecretInputV1(secrets.token_urlsafe(32))
    outcomes = [
        login(wrong_input, correlation_id=f"throttle-failure-{index}")
        for index in range(5)
    ]
    assert [item.code for item in outcomes] == [
        "invalid_credentials",
        "invalid_credentials",
        "invalid_credentials",
        "invalid_credentials",
        "login_throttled",
    ]
    reopened = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )
    blocked = reopened(
        SecretInputV1(owner_credential), correlation_id="throttle-correct-locked"
    )
    assert isinstance(blocked, AuthenticationFailureV1)
    assert blocked.code == "login_throttled"
    assert blocked.retry_after_seconds is not None
    assert 1 <= blocked.retry_after_seconds <= 30
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT failure_count, consecutive_lock_count, locked_until "
                "FROM iam_login_throttle WHERE bucket_id='installation_global'"
            ).one()
            assert row[0] == 5
            assert row[1] == 1
            assert row[2] is not None
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_browser_session"
                ).scalar_one()
                == 0
            )


def test_concurrent_real_failures_cannot_lose_global_lock_transition(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, _ = real_iam_installation
    candidate = SecretInputV1(secrets.token_urlsafe(32))

    def attempt(index: int) -> str:
        login = AuthenticateAdministratorV1(
            SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
        )
        return login(candidate, correlation_id=f"parallel-failure-{index}").code

    with ThreadPoolExecutor(max_workers=6) as executor:
        outcomes = list(executor.map(attempt, range(6)))
    assert outcomes.count("invalid_credentials") == 4
    assert outcomes.count("login_throttled") == 2
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT failure_count, consecutive_lock_count "
                "FROM iam_login_throttle WHERE bucket_id='installation_global'"
            ).one()
            assert tuple(row) == (5, 1)
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_security_audit_event "
                    "WHERE event_type='login_throttle_activated'"
                ).scalar_one()
                == 1
            )


@pytest.mark.parametrize("column", ["failure_count", "consecutive_lock_count"])
def test_noninteger_persisted_throttle_counter_fails_closed(
    real_iam_installation: tuple[DatabaseRefV1, str], column: str
) -> None:
    reference, _ = real_iam_installation
    login = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )
    wrong = SecretInputV1(secrets.token_urlsafe(32))
    assert login(wrong, correlation_id="throttle-corrupt-first").code == (
        "invalid_credentials"
    )
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                f"UPDATE iam_login_throttle SET {column}='broken' "
                "WHERE bucket_id='installation_global'"
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1) as failure:
        login(wrong, correlation_id="throttle-corrupt-again")
    assert str(failure.value) == "iam_repository_unavailable"


def test_empty_persisted_lock_deadline_cannot_bypass_live_lock(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    login = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )
    wrong = SecretInputV1(secrets.token_urlsafe(32))
    outcomes = [
        login(wrong, correlation_id=f"empty-lock-failure-{index}") for index in range(5)
    ]
    assert outcomes[-1].code == "login_throttled"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE iam_login_throttle SET locked_until='' "
                "WHERE bucket_id='installation_global'"
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1) as failure:
        login(
            SecretInputV1(owner_credential),
            correlation_id="empty-lock-correct-denied",
        )
    assert str(failure.value) == "iam_repository_unavailable"
