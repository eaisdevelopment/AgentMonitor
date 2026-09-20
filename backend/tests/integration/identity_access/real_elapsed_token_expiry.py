"""Opt-in one-hour live token-expiry gate; never part of the fast test suite.

Run explicitly with:
  backend/.venv/bin/python -m pytest \
    backend/tests/integration/identity_access/real_elapsed_token_expiry.py -q

This test waits for the frozen 3,600-second minimum on the real wall clock.
"""

import time

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.api_tokens import (
    SqliteIdentityAccessApiTokenRepositoryV1,
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
    ResolveBearerTokenV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
)


def test_actual_minimum_expiry_is_terminal_and_audited_once(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    login = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(owner_credential), correlation_id="real-expiry-owner")
    assert isinstance(login, SessionCredentialIssueV1)
    actor = TokenCallerProofV1(
        "browser_session",
        SecretInputV1(login.session_credential),
        SecretInputV1(login.csrf_credential),
        SecretInputV1(login.csrf_credential),
    )
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issued = CreateApiTokenV1(repository)(
        actor,
        name="real minimum expiry",
        scopes=("read:diagnostics",),
        lifetime_seconds=3600,
        idempotency_key="real_expiry_key_0001",
        correlation_id="real-expiry-create",
    )
    assert isinstance(issued, ApiTokenCredentialIssueV1)
    started = time.monotonic()
    time.sleep(3601)
    assert time.monotonic() - started >= 3600
    reopened = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    for correlation in ("real-elapsed-expiry", "real-elapsed-expiry-repeat"):
        denied = ResolveBearerTokenV1(reopened)(
            SecretInputV1(issued.bearer_credential), correlation_id=correlation
        )
        assert denied.code == "dashboard_authentication_required"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT verification_digest, revoked_at, revocation_reason "
                "FROM iam_api_token WHERE api_token_id=?",
                (issued.token.api_token_id.value,),
            ).one()
            assert row[0] is None
            assert row[1] is not None
            assert row[2] == "expired"
            audit = connection.exec_driver_sql(
                "SELECT correlation_id FROM iam_security_audit_event "
                "WHERE event_type='api_token_expired' AND target_id=?",
                (issued.token.api_token_id.value,),
            ).all()
            assert len(audit) == 1
            assert audit[0][0] == "real-elapsed-expiry"
