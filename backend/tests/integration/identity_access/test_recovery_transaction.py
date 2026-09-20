"""M01 local recovery transaction over real migrated file-backed SQLite."""

import secrets
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
)


def test_recovery_changes_verifier_and_audits_atomically(tmp_path: Path) -> None:
    ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(ref)
    repository = SqliteIdentityAccessRepositoryV1(ref)
    hasher = Argon2PasswordV1()
    previous = secrets.token_urlsafe(32)
    current = secrets.token_urlsafe(32)
    created = BootstrapAdministratorV1(repository, hasher)(
        SecretInputV1(previous), correlation_id="recovery-setup"
    )
    assert created.code == "created"
    result = repository.recover_administrator(
        hasher.hash(current), hasher.POLICY_VERSION, "local-recovery"
    )
    assert result.code == "recovered"
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            material = connection.exec_driver_sql(
                "SELECT password_phc, record_version FROM iam_administrator"
            ).one()
            events = (
                connection.exec_driver_sql(
                    "SELECT event_type FROM iam_security_audit_event "
                    "ORDER BY occurred_at"
                )
                .scalars()
                .all()
            )
            active_sessions = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_browser_session WHERE revoked_at IS NULL"
            ).scalar_one()
            active_tokens = connection.exec_driver_sql(
                "SELECT count(*) FROM iam_api_token WHERE revoked_at IS NULL"
            ).scalar_one()
    previous_matches = hasher.verify(material[0], previous)
    current_matches = hasher.verify(material[0], current)
    assert previous_matches is False
    assert current_matches is True
    assert material[1] == 2
    assert events == ["administrator_initialized", "administrator_recovered"]
    assert active_sessions == 0
    assert active_tokens == 0
