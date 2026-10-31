"""Current-password change atomically rotates browser credentials on real DB."""

import secrets

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
    ChangeAdministratorPasswordV1,
    ResolveBrowserSessionV1,
)


def test_password_change_revokes_all_old_sessions_and_issues_fresh_binding(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    hasher = Argon2PasswordV1()
    login = AuthenticateAdministratorV1(repository, hasher)
    actor = login(SecretInputV1(owner_credential), correlation_id="change-actor")
    other = login(SecretInputV1(owner_credential), correlation_id="change-other")
    assert isinstance(actor, SessionCredentialIssueV1)
    assert isinstance(other, SessionCredentialIssueV1)
    replacement = secrets.token_urlsafe(32)
    changed = ChangeAdministratorPasswordV1(repository, hasher)(
        actor.session.session_id,
        actor.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(owner_credential),
        SecretInputV1(replacement),
        idempotency_key="change_password_key_0001",
        correlation_id="change-success",
    )
    assert isinstance(changed, SessionCredentialIssueV1)
    resolve = ResolveBrowserSessionV1(repository)
    assert resolve(
        SecretInputV1(actor.session_credential), correlation_id="change-old-actor"
    ).code == ("dashboard_authentication_required")
    assert resolve(
        SecretInputV1(other.session_credential), correlation_id="change-old-other"
    ).code == ("dashboard_authentication_required")
    assert (
        resolve(
            SecretInputV1(changed.session_credential),
            correlation_id="change-new-resolve",
        ).code
        == "authenticated"
    )
    assert (
        login(SecretInputV1(owner_credential), correlation_id="change-old-denied").code
        == "invalid_credentials"
    )
    assert isinstance(
        login(SecretInputV1(replacement), correlation_id="change-new-accepted"),
        SessionCredentialIssueV1,
    )
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT record_version FROM iam_administrator"
                ).scalar_one()
                == 2
            )


def test_password_change_wrong_current_value_does_not_revoke_session(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    hasher = Argon2PasswordV1()
    actor = AuthenticateAdministratorV1(repository, hasher)(
        SecretInputV1(owner_credential), correlation_id="change-wrong-actor"
    )
    assert isinstance(actor, SessionCredentialIssueV1)
    denied = ChangeAdministratorPasswordV1(repository, hasher)(
        actor.session.session_id,
        actor.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(secrets.token_urlsafe(32)),
        SecretInputV1(secrets.token_urlsafe(32)),
        idempotency_key="change_password_key_0002",
        correlation_id="change-wrong-denied",
    )
    assert denied.code == "invalid_credentials"
    assert (
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(actor.session_credential),
            correlation_id="change-wrong-resolve",
        ).code
        == "authenticated"
    )


def test_password_change_key_replay_never_reissues_secret_or_mutates_again(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    hasher = Argon2PasswordV1()
    login = AuthenticateAdministratorV1(repository, hasher)
    actor = login(SecretInputV1(owner_credential), correlation_id="replay-actor")
    assert isinstance(actor, SessionCredentialIssueV1)
    replacement = secrets.token_urlsafe(32)
    change = ChangeAdministratorPasswordV1(repository, hasher)
    first = change(
        actor.session.session_id,
        actor.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(owner_credential),
        SecretInputV1(replacement),
        idempotency_key="change_password_replay_01",
        correlation_id="replay-first",
    )
    assert isinstance(first, SessionCredentialIssueV1)
    old_actor_denial = change(
        actor.session.session_id,
        actor.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(owner_credential),
        SecretInputV1("short"),
        idempotency_key="change_password_replay_01",
        correlation_id="replay-old-actor",
    )
    assert old_actor_denial.code == "dashboard_authentication_required"
    replay = change(
        first.session.session_id,
        first.session.record_version,
        SecretInputV1(first.csrf_credential),
        SecretInputV1(first.csrf_credential),
        SecretInputV1(replacement),
        SecretInputV1("short"),
        idempotency_key="change_password_replay_01",
        correlation_id="replay-new-actor",
    )
    assert replay.code == "one_time_secret_not_replayable"
    assert not isinstance(replay, SessionCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT record_version FROM iam_administrator"
                ).scalar_one()
                == 2
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_browser_session"
                ).scalar_one()
                == 2
            )
            receipt = connection.exec_driver_sql(
                "SELECT idempotency_key_digest, request_fingerprint "
                "FROM iam_idempotency_record WHERE operation_key='change_password'"
            ).one()
            assert len(receipt[0]) == 64
            assert receipt[1] is None
            filenames = [
                reference._path,
                *(
                    reference._path.with_name(reference._path.name + suffix)
                    for suffix in ("-wal", "-shm", "-journal")
                ),
            ]
            raw_artifacts = [path.read_bytes() for path in filenames if path.exists()]
            forbidden = (
                owner_credential,
                replacement,
                actor.session_credential,
                actor.csrf_credential,
                first.session_credential,
                first.csrf_credential,
                "change_password_replay_01",
            )
            absent = all(
                value.encode("ascii") not in artifact
                for value in forbidden
                for artifact in raw_artifacts
            )
            assert absent is True


def test_wrong_current_password_change_uses_durable_global_throttle(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    hasher = Argon2PasswordV1()
    actor = AuthenticateAdministratorV1(repository, hasher)(
        SecretInputV1(owner_credential), correlation_id="change-throttle-actor"
    )
    assert isinstance(actor, SessionCredentialIssueV1)
    change = ChangeAdministratorPasswordV1(repository, hasher)
    wrong_current = SecretInputV1(secrets.token_urlsafe(32))
    replacement = SecretInputV1(secrets.token_urlsafe(32))
    outcomes = [
        change(
            actor.session.session_id,
            actor.session.record_version,
            SecretInputV1(actor.csrf_credential),
            SecretInputV1(actor.csrf_credential),
            wrong_current,
            replacement,
            idempotency_key=f"change_throttle_key_{index:04d}",
            correlation_id=f"change-throttle-{index}",
        )
        for index in range(5)
    ]
    assert [outcome.code for outcome in outcomes] == [
        "invalid_credentials",
        "invalid_credentials",
        "invalid_credentials",
        "invalid_credentials",
        "login_throttled",
    ]
    blocked = change(
        actor.session.session_id,
        actor.session.record_version,
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(actor.csrf_credential),
        SecretInputV1(owner_credential),
        replacement,
        idempotency_key="change_throttle_key_correct",
        correlation_id="change-throttle-correct-denied",
    )
    assert blocked.code == "login_throttled"
    assert (
        ResolveBrowserSessionV1(repository)(
            SecretInputV1(actor.session_credential),
            correlation_id="change-throttle-resolve",
        ).code
        == "authenticated"
    )
