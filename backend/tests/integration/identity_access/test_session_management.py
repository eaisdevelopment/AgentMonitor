"""M01 browser-only list and transactional revocation against real SQLite."""

import secrets
import time

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
    ChangeAdministratorPasswordV1,
    ListSessionsV1,
    LogoutSessionV1,
    ResolveBrowserSessionV1,
    RevokeAllSessionsV1,
    RevokeSessionV1,
    SessionQueryErrorV1,
)


def test_real_touched_active_sessions_distinguish_stale_preconditions(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_password = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    hasher = Argon2PasswordV1()
    login = AuthenticateAdministratorV1(repository, hasher)
    logout_target = login(
        SecretInputV1(owner_password), correlation_id="precondition-logout-login"
    )
    revoke_target = login(
        SecretInputV1(owner_password), correlation_id="precondition-revoke-login"
    )
    actor = login(
        SecretInputV1(owner_password), correlation_id="precondition-actor-login"
    )
    assert isinstance(logout_target, SessionCredentialIssueV1)
    assert isinstance(revoke_target, SessionCredentialIssueV1)
    assert isinstance(actor, SessionCredentialIssueV1)

    started = time.monotonic()
    time.sleep(60.1)
    assert time.monotonic() - started >= 60
    resolve = ResolveBrowserSessionV1(repository)
    touched_logout = resolve(
        SecretInputV1(logout_target.session_credential),
        correlation_id="precondition-touch-logout",
    )
    touched_revoke = resolve(
        SecretInputV1(revoke_target.session_credential),
        correlation_id="precondition-touch-revoke",
    )
    touched_actor = resolve(
        SecretInputV1(actor.session_credential),
        correlation_id="precondition-touch-actor",
    )
    for before, after in (
        (logout_target, touched_logout),
        (revoke_target, touched_revoke),
        (actor, touched_actor),
    ):
        assert after.code == "authenticated"
        assert after.session is not None
        assert after.session.record_version > before.session.record_version

    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            before_state = (
                connection.exec_driver_sql(
                    "SELECT record_version FROM iam_administrator"
                ).scalar_one(),
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_browser_session WHERE revoked_at IS NULL"
                ).scalar_one(),
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_security_audit_event"
                ).scalar_one(),
                tuple(
                    connection.exec_driver_sql(
                        "SELECT session_id, record_version, revoked_at "
                        "FROM iam_browser_session ORDER BY session_id"
                    ).all()
                ),
            )

    replacement = secrets.token_urlsafe(32)
    stale_logout = LogoutSessionV1(repository)(
        logout_target.session.session_id,
        logout_target.session.record_version,
        SecretInputV1(logout_target.csrf_credential),
        SecretInputV1(logout_target.csrf_credential),
        correlation_id="precondition-stale-logout",
    )
    stale_revoke = RevokeSessionV1(repository)(
        actor.session.session_id,
        revoke_target.session.session_id,
        revoke_target.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        correlation_id="precondition-stale-revoke",
    )
    change_password = ChangeAdministratorPasswordV1(repository, hasher)
    stale_change = change_password(
        actor.session.session_id,
        actor.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(owner_password),
        SecretInputV1(replacement),
        idempotency_key="session_precondition_change_0001",
        correlation_id="precondition-stale-change",
    )
    assert (stale_logout.code, stale_revoke.code, stale_change.code) == (
        "precondition_failed",
        "precondition_failed",
        "precondition_failed",
    )
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            after_state = (
                connection.exec_driver_sql(
                    "SELECT record_version FROM iam_administrator"
                ).scalar_one(),
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_browser_session WHERE revoked_at IS NULL"
                ).scalar_one(),
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_security_audit_event"
                ).scalar_one(),
                tuple(
                    connection.exec_driver_sql(
                        "SELECT session_id, record_version, revoked_at "
                        "FROM iam_browser_session ORDER BY session_id"
                    ).all()
                ),
            )
    assert after_state == before_state

    assert touched_logout.session is not None
    assert (
        LogoutSessionV1(repository)(
            logout_target.session.session_id,
            touched_logout.session.record_version,
            SecretInputV1(logout_target.csrf_credential),
            SecretInputV1(logout_target.csrf_credential),
            correlation_id="precondition-current-logout",
        ).code
        == "revoked"
    )
    assert touched_revoke.session is not None
    assert (
        RevokeSessionV1(repository)(
            actor.session.session_id,
            revoke_target.session.session_id,
            touched_revoke.session.record_version,
            SecretInputV1(actor.csrf_credential),
            SecretInputV1(actor.csrf_credential),
            correlation_id="precondition-current-revoke",
        ).code
        == "revoked"
    )
    repeated_revoke = RevokeSessionV1(repository)(
        actor.session.session_id,
        revoke_target.session.session_id,
        revoke_target.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        correlation_id="precondition-repeat-target-revoke",
    )
    assert repeated_revoke.code == "revoked"
    assert repeated_revoke.affected_count == 0
    assert touched_actor.session is not None
    changed = change_password(
        actor.session.session_id,
        touched_actor.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(owner_password),
        SecretInputV1(replacement),
        idempotency_key="session_precondition_change_0001",
        correlation_id="precondition-current-change",
    )
    assert isinstance(changed, SessionCredentialIssueV1)
    assert (
        LogoutSessionV1(repository)(
            logout_target.session.session_id,
            touched_logout.session.record_version,
            SecretInputV1(logout_target.csrf_credential),
            SecretInputV1(logout_target.csrf_credential),
            correlation_id="precondition-terminal-logout",
        ).code
        == "dashboard_authentication_required"
    )
    assert (
        change_password(
            changed.session.session_id,
            changed.session.record_version,
            SecretInputV1(changed.csrf_credential),
            SecretInputV1(changed.csrf_credential),
            SecretInputV1(replacement),
            SecretInputV1(secrets.token_urlsafe(32)),
            idempotency_key="session_precondition_change_0001",
            correlation_id="precondition-replay-change",
        ).code
        == "one_time_secret_not_replayable"
    )


def test_list_and_target_revoke_require_active_actor_and_same_session_csrf(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    login = AuthenticateAdministratorV1(repository, Argon2PasswordV1())
    actor = login(SecretInputV1(owner_credential), correlation_id="manage-actor")
    target = login(SecretInputV1(owner_credential), correlation_id="manage-target")
    assert isinstance(actor, SessionCredentialIssueV1)
    assert isinstance(target, SessionCredentialIssueV1)
    listed = ListSessionsV1(repository)(
        actor.principal, correlation_id="manage-list-all"
    )
    assert len(listed) == 2
    first_page = ListSessionsV1(repository)(
        actor.principal, limit=1, correlation_id="manage-list-first"
    )
    next_page = ListSessionsV1(repository)(
        actor.principal,
        limit=1,
        cursor=first_page[0].session_id.value,
        correlation_id="manage-list-next",
    )
    assert len(first_page) == len(next_page) == 1
    assert first_page[0].session_id != next_page[0].session_id
    assert {item.session_id for item in listed} == {
        actor.session.session_id,
        target.session.session_id,
    }
    revoked = RevokeSessionV1(repository)(
        actor.session.session_id,
        target.session.session_id,
        target.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        correlation_id="manage-revoke",
    )
    assert revoked.code == "revoked"
    assert (
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(target.session_credential),
            correlation_id="manage-target-denied",
        ).code
        == "dashboard_authentication_required"
    )
    assert (
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(actor.session_credential), correlation_id="manage-actor-valid"
        ).code
        == "authenticated"
    )
    with pytest.raises(SessionQueryErrorV1) as denied:
        ListSessionsV1(repository)(target.principal, correlation_id="manage-stale-list")
    assert denied.value.code == "dashboard_authentication_required"


def test_session_page_rejects_oversized_cursor_before_database_query(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    actor = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="cursor-actor"
    )
    assert isinstance(actor, SessionCredentialIssueV1)
    with pytest.raises(SessionQueryErrorV1) as denied:
        ListSessionsV1(repository)(
            actor.principal, cursor="x" * 513, correlation_id="cursor-invalid"
        )
    assert denied.value.code == "session_cursor_invalid"


def test_bulk_revoke_is_idempotent_and_keeps_current_session(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    login = AuthenticateAdministratorV1(repository, Argon2PasswordV1())
    current = login(SecretInputV1(owner_credential), correlation_id="bulk-current")
    other = login(SecretInputV1(owner_credential), correlation_id="bulk-other")
    assert isinstance(current, SessionCredentialIssueV1)
    assert isinstance(other, SessionCredentialIssueV1)
    revoke = RevokeAllSessionsV1(repository)
    first = revoke(
        current.session.session_id,
        SecretInputV1(current.csrf_credential),
        SecretInputV1(current.csrf_credential),
        idempotency_key="bulk_revoke_key_0001",
        correlation_id="bulk-first",
    )
    replay = revoke(
        current.session.session_id,
        SecretInputV1(current.csrf_credential),
        SecretInputV1(current.csrf_credential),
        idempotency_key="bulk_revoke_key_0001",
        correlation_id="bulk-replay",
    )
    assert first.code == replay.code == "revoked"
    assert first.affected_count == 1
    assert replay.affected_count == 1
    fresh_actor = login(
        SecretInputV1(owner_credential), correlation_id="bulk-fresh-actor"
    )
    assert isinstance(fresh_actor, SessionCredentialIssueV1)
    reused = revoke(
        fresh_actor.session.session_id,
        SecretInputV1(fresh_actor.csrf_credential),
        SecretInputV1(fresh_actor.csrf_credential),
        idempotency_key="bulk_revoke_key_0001",
        correlation_id="bulk-reused-different-actor",
    )
    assert reused.code == "idempotency_key_reused"
    assert (
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(current.session_credential),
            correlation_id="bulk-current-resolve",
        ).code
        == "authenticated"
    )
    assert (
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(other.session_credential), correlation_id="bulk-other-denied"
        ).code
        == "dashboard_authentication_required"
    )


def test_nontext_persisted_receipt_fingerprint_fails_closed(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    actor = AuthenticateAdministratorV1(repository, Argon2PasswordV1())(
        SecretInputV1(owner_credential), correlation_id="receipt-corrupt-login"
    )
    assert isinstance(actor, SessionCredentialIssueV1)
    revoke = RevokeAllSessionsV1(repository)
    first = revoke(
        actor.session.session_id,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        idempotency_key="receipt_corrupt_key_0001",
        correlation_id="receipt-corrupt-first",
    )
    assert first.code == "revoked"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE iam_idempotency_record SET request_fingerprint=? "
                "WHERE operation_key='revoke_other_sessions'",
                (bytes.fromhex("01" * 32),),
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1) as failure:
        revoke(
            actor.session.session_id,
            SecretInputV1(actor.csrf_credential),
            SecretInputV1(actor.csrf_credential),
            idempotency_key="receipt_corrupt_key_0001",
            correlation_id="receipt-corrupt-replay",
        )
    assert str(failure.value) == "iam_repository_unavailable"


def test_target_revoke_rechecks_actor_csrf_and_target_version_atomically(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    login = AuthenticateAdministratorV1(repository, Argon2PasswordV1())
    actor = login(SecretInputV1(owner_credential), correlation_id="negative-actor")
    target = login(SecretInputV1(owner_credential), correlation_id="negative-target")
    assert isinstance(actor, SessionCredentialIssueV1)
    assert isinstance(target, SessionCredentialIssueV1)
    revoke = RevokeSessionV1(repository)
    wrong_csrf = revoke(
        actor.session.session_id,
        target.session.session_id,
        target.session.record_version,
        SecretInputV1(target.csrf_credential),
        SecretInputV1(target.csrf_credential),
        correlation_id="negative-cross-csrf",
    )
    assert wrong_csrf.code == "csrf_validation_failed"
    mismatched_version = revoke(
        actor.session.session_id,
        target.session.session_id,
        target.session.record_version + 1,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        correlation_id="negative-version",
    )
    assert mismatched_version.code == "precondition_failed"
    assert (
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(target.session_credential),
            correlation_id="negative-target-still-active",
        ).code
        == "authenticated"
    )
