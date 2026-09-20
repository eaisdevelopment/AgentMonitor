"""Real SQLite audit-insert failure rolls back the complete login transaction."""

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
)


def test_actual_sqlite_audit_insert_abort_rolls_back_session_and_throttle(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    login = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )
    first = login(SecretInputV1(owner_credential), correlation_id="audit-before-fault")
    assert isinstance(first, SessionCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            baseline = tuple(
                connection.exec_driver_sql(query).scalar_one()
                for query in (
                    "SELECT count(*) FROM iam_browser_session",
                    "SELECT count(*) FROM iam_security_audit_event",
                    "SELECT record_version FROM iam_login_throttle "
                    "WHERE bucket_id='installation_global'",
                )
            )
            connection.exec_driver_sql(
                "CREATE TRIGGER reject_login_audit "
                "BEFORE INSERT ON iam_security_audit_event "
                "WHEN NEW.event_type='login_succeeded' "
                "BEGIN SELECT RAISE(ABORT, 'audit_insert_refused'); END"
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1) as denied:
        login(SecretInputV1(owner_credential), correlation_id="audit-after-fault")
    assert str(denied.value) == "iam_repository_unavailable"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            after = tuple(
                connection.exec_driver_sql(query).scalar_one()
                for query in (
                    "SELECT count(*) FROM iam_browser_session",
                    "SELECT count(*) FROM iam_security_audit_event",
                    "SELECT record_version FROM iam_login_throttle "
                    "WHERE bucket_id='installation_global'",
                )
            )
            trigger_exists = connection.exec_driver_sql(
                "SELECT count(*) FROM sqlite_schema WHERE type='trigger' "
                "AND name='reject_login_audit'"
            ).scalar_one()
    assert trigger_exists == 1
    assert after == baseline
