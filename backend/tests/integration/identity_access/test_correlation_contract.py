"""Frozen P01 request IDs cross M01 real SQLite ports and safe audit unchanged."""

import secrets
from pathlib import Path

import pytest
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
from agentmonitor.contracts.identity_access_v1 import (
    ApiTokenCredentialIssueV1,
    SecretInputV1,
    SessionCredentialIssueV1,
    TokenCallerProofV1,
)
from agentmonitor.modules.identity_access.application.api_tokens import (
    CreateApiTokenV1,
    ListApiTokensV1,
    ListIamSecurityEventsV1,
    ResolveBearerTokenV1,
    RevokeApiTokenV1,
    RotateApiTokenV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)
from agentmonitor.modules.identity_access.application.errors import (
    IamRepositoryUnavailableV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
    ListSessionsV1,
    LogoutSessionV1,
    ResolveBrowserSessionV1,
    VerifyCsrfV1,
)

FROZEN_REQUEST_ID = "a.b:c"


def test_bootstrap_preserves_valid_request_id_and_rejects_non_ascii(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    owner_password = secrets.token_urlsafe(32)
    repository = SqliteIdentityAccessRepositoryV1(reference)
    hasher = Argon2PasswordV1()
    bootstrap = BootstrapAdministratorV1(repository, hasher)
    with pytest.raises(IamRepositoryUnavailableV1):
        bootstrap(SecretInputV1(owner_password), correlation_id="é")
    created = bootstrap(SecretInputV1(owner_password), correlation_id=FROZEN_REQUEST_ID)
    assert created.code == "created"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_administrator"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT correlation_id FROM iam_security_audit_event "
                    "WHERE event_type='administrator_initialized'"
                ).scalar_one()
                == FROZEN_REQUEST_ID
            )
    replacement_phc = hasher.hash(secrets.token_urlsafe(32))
    with pytest.raises(IamRepositoryUnavailableV1):
        repository.recover_administrator(replacement_phc, hasher.POLICY_VERSION, "é")
    recovered = repository.recover_administrator(
        replacement_phc, hasher.POLICY_VERSION, FROZEN_REQUEST_ID
    )
    assert recovered.code == "recovered"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT correlation_id FROM iam_security_audit_event "
                    "WHERE event_type='administrator_recovered'"
                ).scalar_one()
                == FROZEN_REQUEST_ID
            )


def test_login_token_and_audit_ports_preserve_valid_request_id(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_password = real_iam_installation
    session_repository = SqliteIdentityAccessSessionRepositoryV1(reference)
    login = AuthenticateAdministratorV1(session_repository, Argon2PasswordV1())
    with pytest.raises(IamRepositoryUnavailableV1):
        login(SecretInputV1(owner_password), correlation_id="é")
    issued_session = login(
        SecretInputV1(owner_password), correlation_id=FROZEN_REQUEST_ID
    )
    assert isinstance(issued_session, SessionCredentialIssueV1)
    resolved_session = ResolveBrowserSessionV1(session_repository)(
        SecretInputV1(issued_session.session_credential),
        correlation_id=FROZEN_REQUEST_ID,
    )
    assert resolved_session.code == "authenticated"
    assert resolved_session.principal is not None
    assert (
        VerifyCsrfV1(session_repository)(
            issued_session.session.session_id,
            SecretInputV1(issued_session.csrf_credential),
            SecretInputV1(issued_session.csrf_credential),
            correlation_id=FROZEN_REQUEST_ID,
        ).code
        == "valid"
    )
    assert (
        len(
            ListSessionsV1(session_repository)(
                resolved_session.principal, correlation_id=FROZEN_REQUEST_ID
            )
        )
        == 1
    )
    actor = TokenCallerProofV1(
        "browser_session",
        SecretInputV1(issued_session.session_credential),
        SecretInputV1(issued_session.csrf_credential),
        SecretInputV1(issued_session.csrf_credential),
    )
    token_repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    create_token = CreateApiTokenV1(token_repository)
    with pytest.raises(IamRepositoryUnavailableV1):
        create_token(
            actor,
            name="diagnostics",
            scopes=("read:diagnostics",),
            lifetime_seconds=None,
            idempotency_key="correlation_invalid_0001",
            correlation_id="é",
        )
    issued_token = create_token(
        actor,
        name="diagnostics",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="correlation_valid_00001",
        correlation_id=FROZEN_REQUEST_ID,
    )
    assert isinstance(issued_token, ApiTokenCredentialIssueV1)
    resolved_token = ResolveBearerTokenV1(token_repository)(
        SecretInputV1(issued_token.bearer_credential),
        correlation_id=FROZEN_REQUEST_ID,
    )
    assert resolved_token.code == "authenticated"
    assert resolved_token.token is not None
    listed_tokens = ListApiTokensV1(token_repository)(
        actor, correlation_id=FROZEN_REQUEST_ID
    )
    assert len(listed_tokens) == 1
    rotated = RotateApiTokenV1(token_repository)(
        actor,
        issued_token.token.api_token_id,
        resolved_token.token.record_version,
        idempotency_key="correlation_rotate_0001",
        correlation_id=FROZEN_REQUEST_ID,
    )
    assert isinstance(rotated, ApiTokenCredentialIssueV1)
    assert (
        RevokeApiTokenV1(token_repository)(
            actor,
            rotated.token.api_token_id,
            rotated.token.record_version,
            correlation_id=FROZEN_REQUEST_ID,
        ).code
        == "revoked"
    )
    with pytest.raises(IamRepositoryUnavailableV1):
        ListIamSecurityEventsV1(token_repository)(actor, correlation_id="é")
    events = ListIamSecurityEventsV1(token_repository)(
        actor, correlation_id=FROZEN_REQUEST_ID
    )
    by_type = {event.event_type: event for event in events}
    assert {
        "login_succeeded",
        "api_token_created",
        "api_token_rotated",
        "api_token_revoked",
    } <= by_type.keys()
    assert all(
        by_type[kind].correlation_id.value == FROZEN_REQUEST_ID
        for kind in (
            "login_succeeded",
            "api_token_created",
            "api_token_rotated",
            "api_token_revoked",
        )
    )
    assert (
        LogoutSessionV1(session_repository)(
            issued_session.session.session_id,
            issued_session.session.record_version,
            SecretInputV1(issued_session.csrf_credential),
            SecretInputV1(issued_session.csrf_credential),
            correlation_id=FROZEN_REQUEST_ID,
        ).code
        == "revoked"
    )
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_api_token"
                ).scalar_one()
                == 2
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT correlation_id FROM iam_security_audit_event "
                    "WHERE event_type='browser_session_revoked'"
                ).scalar_one()
                == FROZEN_REQUEST_ID
            )
