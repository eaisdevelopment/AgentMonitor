"""Actual session audit rows project through the closed published M01 view."""

from datetime import datetime

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.sessions import (
    SqliteIdentityAccessSessionRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    IamSecurityEventViewV1,
    SecretInputV1,
    SessionCredentialIssueV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
    LogoutSessionV1,
)


def test_real_login_and_logout_audit_rows_have_published_safe_views(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    issued = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="event-projection-login"
    )
    assert isinstance(issued, SessionCredentialIssueV1)
    assert (
        LogoutSessionV1(repository)(
            issued.session.session_id,
            issued.session.record_version,
            SecretInputV1(issued.csrf_credential),
            SecretInputV1(issued.csrf_credential),
            correlation_id="event-projection-logout",
        ).code
        == "revoked"
    )
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT event_id, event_type, occurred_at, recorded_at, "
                "actor_principal_id, authentication_method, target_type, target_id, "
                "outcome_code, reason_code, correlation_id, schema_version, "
                "aggregate_count FROM iam_security_audit_event "
                "WHERE event_type IN ('login_succeeded', 'browser_session_revoked') "
                "ORDER BY occurred_at, event_id"
            ).all()
    views = [
        IamSecurityEventViewV1(
            OpaqueIdV1(row[0]),
            row[1],
            datetime.fromisoformat(row[2].replace("Z", "+00:00")),
            datetime.fromisoformat(row[3].replace("Z", "+00:00")),
            OpaqueIdV1(row[4]) if row[4] is not None else None,
            row[5],
            row[6],
            OpaqueIdV1(row[7]) if row[7] is not None else None,
            row[8],
            row[9],
            OpaqueIdV1(row[10]),
            row[11],
            row[12],
        )
        for row in rows
    ]
    assert {view.event_type for view in views} == {
        "login_succeeded",
        "browser_session_revoked",
    }
    assert {view.event_type: view.correlation_id.value for view in views} == {
        "login_succeeded": "event-projection-login",
        "browser_session_revoked": "event-projection-logout",
    }
