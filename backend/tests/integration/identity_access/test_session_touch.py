"""Real elapsed-time concurrent touch; no clock or timeout override."""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
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
    ResolveBrowserSessionV1,
)


def test_two_real_requests_after_elapsed_minute_coalesce_to_one_durable_touch(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    issued = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="touch-login"
    )
    assert isinstance(issued, SessionCredentialIssueV1)
    target = issued.session.last_activity_at + timedelta(seconds=60, milliseconds=100)
    remaining = (target - datetime.now(UTC)).total_seconds()
    if remaining > 0:
        time.sleep(remaining)

    def resolve(index: int) -> str:
        result = ResolveBrowserSessionV1(
            SqliteIdentityAccessSessionRepositoryV1(reference)
        )(
            SecretInputV1(issued.session_credential),
            correlation_id=f"touch-resolve-{index}",
        )
        return result.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(resolve, (1, 2)))
    assert results == ["authenticated", "authenticated"]
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT last_activity_at, idle_expires_at, absolute_expires_at, "
                "record_version FROM iam_browser_session WHERE session_id=?",
                (issued.session.session_id.value,),
            ).one()
    last_activity = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
    idle = datetime.fromisoformat(row[1].replace("Z", "+00:00"))
    absolute = datetime.fromisoformat(row[2].replace("Z", "+00:00"))
    assert last_activity >= target - timedelta(milliseconds=100)
    assert idle == absolute == issued.session.absolute_expires_at
    assert absolute == issued.session.issued_at + timedelta(seconds=86400)
    assert row[3] == 2
