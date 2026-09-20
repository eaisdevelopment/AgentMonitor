"""M01 bearer lifecycle against real migrated, owner-only SQLite and Argon2."""

import hashlib
import hmac
import json
import pickle
import re
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.api_tokens import (
    SqliteIdentityAccessApiTokenRepositoryV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    IdentityAccessRepositoryErrorV1,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.sessions import (
    SqliteIdentityAccessSessionRepositoryV1,
)
from agentmonitor.contracts.identity_access_v1 import (
    ApiTokenCredentialIssueV1,
    ApiTokenMutationOutcomeV1,
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
    TokenQueryErrorV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
)


def test_create_token_is_one_time_and_survives_repository_reopen(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    login = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(owner_credential), correlation_id="token-owner-login")
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
        name="diagnostic",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="token_create_key_0001",
        correlation_id="token-create",
    )
    assert isinstance(issued, ApiTokenCredentialIssueV1)
    assert issued.token.name == "diagnostic"
    assert issued.token.scopes == ("read:diagnostics",)
    assert issued.token.state == "active"
    wire_shape = (
        re.fullmatch(
            r"am1\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}", issued.bearer_credential
        )
        is not None
    )
    assert wire_shape is True
    assert "redacted" in repr(issued)
    with pytest.raises(TypeError, match="token_issue_not_serializable"):
        pickle.dumps(issued)
    with pytest.raises(TypeError):
        json.dumps(issued)
    reopened = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    resolved = ResolveBearerTokenV1(reopened)(
        SecretInputV1(issued.bearer_credential), correlation_id="token-resolve"
    )
    assert resolved.code == "authenticated"
    assert resolved.principal is not None
    assert resolved.principal.effective_permissions == ("read:diagnostics",)
    listed = ListApiTokensV1(reopened)(actor, correlation_id="token-list")
    assert len(listed) == 1
    assert listed[0].api_token_id == issued.token.api_token_id


def _owner_actor(reference: DatabaseRefV1, owner_credential: str) -> TokenCallerProofV1:
    login = AuthenticateAdministratorV1(
        SqliteIdentityAccessSessionRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(owner_credential), correlation_id="token-owner-login")
    assert isinstance(login, SessionCredentialIssueV1)
    return TokenCallerProofV1(
        "browser_session",
        SecretInputV1(login.session_credential),
        SecretInputV1(login.csrf_credential),
        SecretInputV1(login.csrf_credential),
    )


@pytest.mark.parametrize("action", ("rotate", "revoke"))
def test_stale_active_token_version_is_precondition_not_terminal_conflict(
    real_iam_installation: tuple[DatabaseRefV1, str], action: str
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issued = CreateApiTokenV1(repository)(
        actor,
        name="versioned target",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="active_version_setup_0001",
        correlation_id="active-version-setup",
    )
    assert isinstance(issued, ApiTokenCredentialIssueV1)
    touched = ResolveBearerTokenV1(repository)(
        SecretInputV1(issued.bearer_credential),
        correlation_id="active-version-real-touch",
    )
    assert touched.code == "authenticated"
    assert touched.token is not None
    assert touched.token.record_version > issued.token.record_version
    if action == "rotate":
        stale = RotateApiTokenV1(repository)(
            actor,
            issued.token.api_token_id,
            issued.token.record_version,
            idempotency_key="active_version_rotate_0001",
            correlation_id="active-version-stale-rotate",
        )
    else:
        stale = RevokeApiTokenV1(repository)(
            actor,
            issued.token.api_token_id,
            issued.token.record_version,
            correlation_id="active-version-stale-revoke",
        )
    assert isinstance(stale, ApiTokenMutationOutcomeV1)
    assert stale.code == "precondition_failed"
    assert stale.api_token_id is None
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT record_version, revoked_at, verification_digest "
                "FROM iam_api_token WHERE api_token_id=?",
                (issued.token.api_token_id.value,),
            ).one()
            assert row[0] == touched.token.record_version
            assert row[1] is None
            assert len(row[2]) == 64
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_security_audit_event "
                    "WHERE event_type IN ('api_token_rotated', 'api_token_revoked')"
                ).scalar_one()
                == 0
            )
    if action == "rotate":
        accepted = RotateApiTokenV1(repository)(
            actor,
            issued.token.api_token_id,
            touched.token.record_version,
            idempotency_key="active_version_rotate_0001",
            correlation_id="active-version-current-rotate",
        )
        assert isinstance(accepted, ApiTokenCredentialIssueV1)
        assert accepted.code == "rotated"
    else:
        accepted = RevokeApiTokenV1(repository)(
            actor,
            issued.token.api_token_id,
            touched.token.record_version,
            correlation_id="active-version-current-revoke",
        )
        assert accepted.code == "revoked"
        repeated = RevokeApiTokenV1(repository)(
            actor,
            issued.token.api_token_id,
            issued.token.record_version,
            correlation_id="active-version-repeat-revoke",
        )
        assert repeated.code == "revoked"


def test_rotated_terminal_target_keeps_state_conflict_for_revoke(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issued = CreateApiTokenV1(repository)(
        actor,
        name="terminal target",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="terminal_precondition_setup_0001",
        correlation_id="terminal-precondition-setup",
    )
    assert isinstance(issued, ApiTokenCredentialIssueV1)
    rotated = RotateApiTokenV1(repository)(
        actor,
        issued.token.api_token_id,
        issued.token.record_version,
        idempotency_key="terminal_precondition_rotate_0001",
        correlation_id="terminal-precondition-rotate",
    )
    assert isinstance(rotated, ApiTokenCredentialIssueV1)
    denied = RevokeApiTokenV1(repository)(
        actor,
        issued.token.api_token_id,
        issued.token.record_version,
        correlation_id="terminal-precondition-revoke",
    )
    assert denied.code == "credential_state_conflict"


def test_revoked_terminal_target_keeps_state_conflict_for_rotate(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issued = CreateApiTokenV1(repository)(
        actor,
        name="revoked target",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="revoked_precondition_setup_0001",
        correlation_id="revoked-precondition-setup",
    )
    assert isinstance(issued, ApiTokenCredentialIssueV1)
    revoked = RevokeApiTokenV1(repository)(
        actor,
        issued.token.api_token_id,
        issued.token.record_version,
        correlation_id="revoked-precondition-revoke",
    )
    assert revoked.code == "revoked"
    denied = RotateApiTokenV1(repository)(
        actor,
        issued.token.api_token_id,
        issued.token.record_version,
        idempotency_key="revoked_precondition_rotate_0001",
        correlation_id="revoked-precondition-rotate",
    )
    assert isinstance(denied, ApiTokenMutationOutcomeV1)
    assert denied.code == "credential_state_conflict"


def test_rotation_revoke_and_safe_replay_are_durable(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    predecessor = CreateApiTokenV1(repository)(
        actor,
        name="predecessor",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="token_rotation_setup_0001",
        correlation_id="token-rotation-setup",
    )
    assert isinstance(predecessor, ApiTokenCredentialIssueV1)
    successor = RotateApiTokenV1(repository)(
        actor,
        predecessor.token.api_token_id,
        predecessor.token.record_version,
        idempotency_key="token_rotation_key_0001",
        correlation_id="token-rotation",
    )
    assert isinstance(successor, ApiTokenCredentialIssueV1)
    assert successor.code == "rotated"
    assert successor.token.rotated_from_token_id == predecessor.token.api_token_id
    denied = ResolveBearerTokenV1(repository)(
        SecretInputV1(predecessor.bearer_credential), correlation_id="old-denied"
    )
    assert denied.code == "dashboard_authentication_required"
    replay = RotateApiTokenV1(repository)(
        actor,
        predecessor.token.api_token_id,
        predecessor.token.record_version,
        idempotency_key="token_rotation_key_0001",
        correlation_id="token-rotation-replay",
    )
    assert isinstance(replay, ApiTokenMutationOutcomeV1)
    assert replay.code == "one_time_secret_not_replayable"
    assert replay.api_token_id == successor.token.api_token_id
    assert replay.state == "active"
    reused = RotateApiTokenV1(repository)(
        actor,
        predecessor.token.api_token_id,
        predecessor.token.record_version,
        name="different metadata",
        idempotency_key="token_rotation_key_0001",
        correlation_id="token-rotation-reused",
    )
    assert isinstance(reused, ApiTokenMutationOutcomeV1)
    assert reused.code == "idempotency_key_reused"
    revoked = RevokeApiTokenV1(repository)(
        actor,
        successor.token.api_token_id,
        successor.token.record_version,
        correlation_id="token-revoke",
    )
    assert revoked.code == "revoked"
    assert revoked.state == "revoked"
    repeated = RevokeApiTokenV1(repository)(
        actor,
        successor.token.api_token_id,
        successor.token.record_version,
        correlation_id="token-revoke-repeat",
    )
    assert repeated.code == "revoked"
    assert repeated.record_version == revoked.record_version
    reopened = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    assert (
        ResolveBearerTokenV1(reopened)(
            SecretInputV1(successor.bearer_credential),
            correlation_id="successor-denied",
        ).code
        == "dashboard_authentication_required"
    )
    events = ListIamSecurityEventsV1(reopened)(actor, correlation_id="token-audit-list")
    event_types = {event.event_type for event in events}
    assert {
        "api_token_created",
        "api_token_rotated",
        "api_token_revoked",
    } <= event_types
    assert sum(event.event_type == "api_token_revoked" for event in events) == 1


def test_mutations_recheck_csrf_and_bearer_attenuation_in_same_database(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    wrong_csrf = TokenCallerProofV1(
        "browser_session",
        actor.credential,
        SecretInputV1("not-the-csrf"),
        SecretInputV1("not-the-csrf"),
    )
    refused = CreateApiTokenV1(repository)(
        wrong_csrf,
        name="must not exist",
        scopes=("write:tokens",),
        lifetime_seconds=None,
        idempotency_key="wrong_csrf_key_0001",
        correlation_id="wrong-csrf",
    )
    assert isinstance(refused, ApiTokenMutationOutcomeV1)
    assert refused.code == "csrf_validation_failed"
    assert ListApiTokensV1(repository)(actor, correlation_id="empty-after-csrf") == ()
    parent = CreateApiTokenV1(repository)(
        actor,
        name="parent",
        scopes=("write:tokens",),
        lifetime_seconds=7200,
        idempotency_key="bearer_parent_key_0001",
        correlation_id="create-parent",
    )
    assert isinstance(parent, ApiTokenCredentialIssueV1)
    bearer = TokenCallerProofV1("api_bearer", SecretInputV1(parent.bearer_credential))
    escalated = CreateApiTokenV1(repository)(
        bearer,
        name="not allowed",
        scopes=("read:diagnostics",),
        lifetime_seconds=3600,
        idempotency_key="bearer_escalate_key_0001",
        correlation_id="bearer-escalate",
    )
    assert isinstance(escalated, ApiTokenMutationOutcomeV1)
    assert escalated.code == "scope_escalation_denied"
    too_long = CreateApiTokenV1(repository)(
        bearer,
        name="too long",
        scopes=("write:tokens",),
        lifetime_seconds=7200,
        idempotency_key="bearer_lifetime_key_0001",
        correlation_id="bearer-lifetime",
    )
    assert isinstance(too_long, ApiTokenMutationOutcomeV1)
    assert too_long.code == "scope_escalation_denied"
    child = CreateApiTokenV1(repository)(
        bearer,
        name="child",
        scopes=("write:tokens",),
        lifetime_seconds=3600,
        idempotency_key="bearer_child_key_0001",
        correlation_id="bearer-child",
    )
    assert isinstance(child, ApiTokenCredentialIssueV1)
    with pytest.raises(TokenQueryErrorV1) as audit_denied:
        ListIamSecurityEventsV1(repository)(bearer, correlation_id="no-audit-scope")
    assert audit_denied.value.code == "permission_denied"
    revoked = RevokeApiTokenV1(repository)(
        actor,
        parent.token.api_token_id,
        parent.token.record_version,
        correlation_id="revoke-parent",
    )
    assert revoked.code == "revoked"
    stale = CreateApiTokenV1(repository)(
        bearer,
        name="stale",
        scopes=("write:tokens",),
        lifetime_seconds=3600,
        idempotency_key="bearer_stale_key_0001",
        correlation_id="bearer-stale",
    )
    assert isinstance(stale, ApiTokenMutationOutcomeV1)
    assert stale.code == "dashboard_authentication_required"
    assert len(ListApiTokensV1(repository)(actor, correlation_id="no-stale-write")) == 2


def test_create_receipt_is_one_time_and_isolated_by_authenticated_issuer(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    first_actor = _owner_actor(reference, owner_credential)
    second_actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issue = CreateApiTokenV1(repository)(
        first_actor,
        name="first issuer",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="shared_issuer_key_0001",
        correlation_id="issuer-first",
    )
    assert isinstance(issue, ApiTokenCredentialIssueV1)
    replay = CreateApiTokenV1(repository)(
        first_actor,
        name="first issuer",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="shared_issuer_key_0001",
        correlation_id="issuer-replay",
    )
    assert isinstance(replay, ApiTokenMutationOutcomeV1)
    assert replay.code == "one_time_secret_not_replayable"
    assert replay.api_token_id == issue.token.api_token_id
    assert replay.record_version == issue.token.record_version
    changed = CreateApiTokenV1(repository)(
        first_actor,
        name="changed",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="shared_issuer_key_0001",
        correlation_id="issuer-changed",
    )
    assert isinstance(changed, ApiTokenMutationOutcomeV1)
    assert changed.code == "idempotency_key_reused"
    other = CreateApiTokenV1(repository)(
        second_actor,
        name="first issuer",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="shared_issuer_key_0001",
        correlation_id="issuer-second",
    )
    assert isinstance(other, ApiTokenCredentialIssueV1)
    assert other.token.api_token_id != issue.token.api_token_id


def test_distinct_active_bearer_issuers_never_share_one_create_receipt(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    first = CreateApiTokenV1(repository)(
        actor,
        name="first issuer",
        scopes=("write:tokens",),
        lifetime_seconds=None,
        idempotency_key="bearer_issuer_one_0001",
        correlation_id="bearer-issuer-one",
    )
    second = CreateApiTokenV1(repository)(
        actor,
        name="second issuer",
        scopes=("write:tokens",),
        lifetime_seconds=None,
        idempotency_key="bearer_issuer_two_0001",
        correlation_id="bearer-issuer-two",
    )
    assert isinstance(first, ApiTokenCredentialIssueV1)
    assert isinstance(second, ApiTokenCredentialIssueV1)
    first_actor = TokenCallerProofV1(
        "api_bearer", SecretInputV1(first.bearer_credential)
    )
    second_actor = TokenCallerProofV1(
        "api_bearer", SecretInputV1(second.bearer_credential)
    )
    child = CreateApiTokenV1(repository)(
        first_actor,
        name="same metadata",
        scopes=("write:tokens",),
        lifetime_seconds=3600,
        idempotency_key="shared_bearer_key_0001",
        correlation_id="first-bearer-child",
    )
    assert isinstance(child, ApiTokenCredentialIssueV1)
    replay = CreateApiTokenV1(repository)(
        first_actor,
        name="same metadata",
        scopes=("write:tokens",),
        lifetime_seconds=3600,
        idempotency_key="shared_bearer_key_0001",
        correlation_id="first-bearer-replay",
    )
    assert isinstance(replay, ApiTokenMutationOutcomeV1)
    assert replay.code == "one_time_secret_not_replayable"
    assert replay.api_token_id == child.token.api_token_id
    separate = CreateApiTokenV1(repository)(
        second_actor,
        name="same metadata",
        scopes=("write:tokens",),
        lifetime_seconds=3600,
        idempotency_key="shared_bearer_key_0001",
        correlation_id="second-bearer-child",
    )
    assert isinstance(separate, ApiTokenCredentialIssueV1)
    assert separate.token.api_token_id != child.token.api_token_id


def test_active_cap_and_competing_rotations_commit_at_most_one_successor(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    tokens: list[ApiTokenCredentialIssueV1] = []
    for index in range(63):
        created = CreateApiTokenV1(repository)(
            actor,
            name=f"cap {index}",
            scopes=("write:tokens",),
            lifetime_seconds=None,
            idempotency_key=f"cap_create_token_{index:04d}",
            correlation_id=f"cap-create-{index}",
        )
        assert isinstance(created, ApiTokenCredentialIssueV1)
        tokens.append(created)

    def final_create(
        index: int,
    ) -> ApiTokenCredentialIssueV1 | ApiTokenMutationOutcomeV1:
        return CreateApiTokenV1(SqliteIdentityAccessApiTokenRepositoryV1(reference))(
            actor,
            name=f"concurrent {index}",
            scopes=("write:tokens",),
            lifetime_seconds=None,
            idempotency_key=f"cap_parallel_create_{index:04d}",
            correlation_id=f"cap-parallel-{index}",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(final_create, (1, 2)))
    assert sum(isinstance(result, ApiTokenCredentialIssueV1) for result in results) == 1
    assert (
        sum(
            isinstance(result, ApiTokenMutationOutcomeV1)
            and result.code == "active_token_limit_reached"
            for result in results
        )
        == 1
    )
    assert (
        len(ListApiTokensV1(repository)(actor, limit=200, correlation_id="cap-list"))
        == 64
    )
    predecessor = tokens[0]

    def compete(index: int) -> ApiTokenCredentialIssueV1 | ApiTokenMutationOutcomeV1:
        return RotateApiTokenV1(SqliteIdentityAccessApiTokenRepositoryV1(reference))(
            actor,
            predecessor.token.api_token_id,
            predecessor.token.record_version,
            idempotency_key=f"cap_parallel_rotation_{index:04d}",
            correlation_id=f"cap-rotation-{index}",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        rotations = tuple(pool.map(compete, (1, 2)))
    assert (
        sum(isinstance(result, ApiTokenCredentialIssueV1) for result in rotations) == 1
    )
    assert (
        sum(
            isinstance(result, ApiTokenMutationOutcomeV1)
            and result.code == "credential_state_conflict"
            for result in rotations
        )
        == 1
    )
    listed = ListApiTokensV1(repository)(
        actor, limit=200, correlation_id="cap-after-rotation"
    )
    assert len(listed) == 65
    assert sum(token.state == "active" for token in listed) == 64


def test_token_and_idempotency_secrets_are_absent_from_live_sqlite_artifacts(
    real_iam_installation: tuple[DatabaseRefV1, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    key = "artifact_secret_key_0001"
    issue = CreateApiTokenV1(repository)(
        actor,
        name="artifact scan",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key=key,
        correlation_id="token-artifact-scan",
    )
    assert isinstance(issue, ApiTokenCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            stored = connection.exec_driver_sql(
                "SELECT public_selector, safe_prefix, verification_digest "
                "FROM iam_api_token "
                "WHERE api_token_id=?",
                (issue.token.api_token_id.value,),
            ).one()
            assert len(stored[0]) == 22
            assert stored[1] == stored[0][:8]
            assert len(stored[2]) == 64
            digest_matches = hmac.compare_digest(
                stored[2],
                hashlib.sha256(issue.bearer_credential.encode("ascii")).hexdigest(),
            )
            assert digest_matches is True
            paths = [
                reference._path,
                *(
                    reference._path.with_name(reference._path.name + suffix)
                    for suffix in ("-wal", "-shm", "-journal")
                ),
            ]
            assert paths[1].exists(), "real_sqlite_wal_not_present_during_scan"
            artifacts = [path.read_bytes() for path in paths if path.exists()]
            forbidden = (
                owner_credential,
                actor.credential.reveal_for_verification(),
                actor.csrf_cookie.reveal_for_verification()
                if actor.csrf_cookie
                else "",
                issue.bearer_credential,
                issue.bearer_credential.rsplit(".", 1)[1],
                key,
            )
            assert all(
                value.encode("ascii") not in artifact
                for value in forbidden
                if value
                for artifact in artifacts
            )
            assert all(value not in caplog.text for value in forbidden if value)


def test_token_create_and_receipt_roll_back_when_real_audit_insert_fails(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "CREATE TRIGGER fail_token_audit BEFORE INSERT ON "
                "iam_security_audit_event WHEN NEW.event_type='api_token_created' "
                "BEGIN SELECT RAISE(FAIL, 'audit_insert_blocked'); END"
            )
            connection.commit()
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    with pytest.raises(IdentityAccessRepositoryErrorV1):
        CreateApiTokenV1(repository)(
            actor,
            name="must roll back",
            scopes=("read:diagnostics",),
            lifetime_seconds=None,
            idempotency_key="audit_rollback_key_0001",
            correlation_id="token-audit-rollback",
        )
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_api_token"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_idempotency_record "
                    "WHERE operation_key='create_api_token'"
                ).scalar_one()
                == 0
            )


@pytest.mark.parametrize("action", ("rotate", "revoke"))
def test_token_terminal_transition_rolls_back_on_real_audit_insert_failure(
    real_iam_installation: tuple[DatabaseRefV1, str], action: str
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issue = CreateApiTokenV1(repository)(
        actor,
        name="rollback target",
        scopes=("write:tokens",),
        lifetime_seconds=None,
        idempotency_key="terminal_setup_key_0001",
        correlation_id="terminal-setup",
    )
    assert isinstance(issue, ApiTokenCredentialIssueV1)
    event_type = "api_token_rotated" if action == "rotate" else "api_token_revoked"
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "CREATE TRIGGER fail_terminal_audit BEFORE INSERT ON "
                "iam_security_audit_event WHEN NEW.event_type='" + event_type + "' "
                "BEGIN SELECT RAISE(FAIL, 'audit_insert_blocked'); END"
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1):
        if action == "rotate":
            RotateApiTokenV1(repository)(
                actor,
                issue.token.api_token_id,
                issue.token.record_version,
                idempotency_key="terminal_rotate_key_0001",
                correlation_id="terminal-rotate-fault",
            )
        else:
            RevokeApiTokenV1(repository)(
                actor,
                issue.token.api_token_id,
                issue.token.record_version,
                correlation_id="terminal-revoke-fault",
            )
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            row = connection.exec_driver_sql(
                "SELECT verification_digest, revoked_at, replacement_token_id "
                "FROM iam_api_token WHERE api_token_id=?",
                (issue.token.api_token_id.value,),
            ).one()
            assert len(row[0]) == 64
            assert row[1] is None
            assert row[2] is None
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_api_token"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_security_audit_event WHERE event_type=?",
                    (event_type,),
                ).scalar_one()
                == 0
            )


def test_safe_audit_query_is_bounded_filtered_and_rechecks_bearer(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    diagnostic = CreateApiTokenV1(repository)(
        actor,
        name="audit reader",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="audit_reader_key_0001",
        correlation_id="audit-reader-create",
    )
    assert isinstance(diagnostic, ApiTokenCredentialIssueV1)
    bearer = TokenCallerProofV1(
        "api_bearer", SecretInputV1(diagnostic.bearer_credential)
    )
    first = ListIamSecurityEventsV1(repository)(
        bearer, limit=1, correlation_id="audit-first-page"
    )
    second = ListIamSecurityEventsV1(repository)(
        bearer,
        limit=1,
        cursor=first[0].event_id.value,
        correlation_id="audit-second-page",
    )
    assert len(first) == len(second) == 1
    assert first[0].event_id != second[0].event_id
    filtered = ListIamSecurityEventsV1(repository)(
        bearer, event_type="api_token_created", correlation_id="audit-filtered"
    )
    assert len(filtered) == 1
    assert filtered[0].correlation_id.value == "audit-reader-create"
    assert filtered[0].event_type == "api_token_created"
    revoked = RevokeApiTokenV1(repository)(
        actor,
        diagnostic.token.api_token_id,
        diagnostic.token.record_version,
        correlation_id="audit-reader-revoke",
    )
    assert revoked.code == "revoked"
    with pytest.raises(TokenQueryErrorV1) as stale:
        ListIamSecurityEventsV1(repository)(bearer, correlation_id="audit-reader-stale")
    assert stale.value.code == "dashboard_authentication_required"


def test_authenticated_replay_precedes_new_child_lifetime_check_after_real_elapsed_time(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issuer = CreateApiTokenV1(repository)(
        actor,
        name="short issuer",
        scopes=("write:tokens",),
        lifetime_seconds=3608,
        idempotency_key="short_issuer_key_0001",
        correlation_id="short-issuer-create",
    )
    assert isinstance(issuer, ApiTokenCredentialIssueV1)
    bearer = TokenCallerProofV1("api_bearer", SecretInputV1(issuer.bearer_credential))
    child = CreateApiTokenV1(repository)(
        bearer,
        name="short child",
        scopes=("write:tokens",),
        lifetime_seconds=3600,
        idempotency_key="short_child_key_0001",
        correlation_id="short-child-create",
    )
    assert isinstance(child, ApiTokenCredentialIssueV1)
    successor = RotateApiTokenV1(repository)(
        bearer,
        child.token.api_token_id,
        child.token.record_version,
        lifetime_seconds=3600,
        idempotency_key="short_rotation_key_0001",
        correlation_id="short-child-rotation",
    )
    assert isinstance(successor, ApiTokenCredentialIssueV1)
    started = time.monotonic()
    time.sleep(9)
    assert time.monotonic() - started >= 8
    create_replay = CreateApiTokenV1(repository)(
        bearer,
        name="short child",
        scopes=("write:tokens",),
        lifetime_seconds=3600,
        idempotency_key="short_child_key_0001",
        correlation_id="short-child-replay",
    )
    assert isinstance(create_replay, ApiTokenMutationOutcomeV1)
    assert create_replay.code == "one_time_secret_not_replayable"
    assert create_replay.api_token_id == child.token.api_token_id
    rotate_replay = RotateApiTokenV1(repository)(
        bearer,
        child.token.api_token_id,
        child.token.record_version,
        lifetime_seconds=3600,
        idempotency_key="short_rotation_key_0001",
        correlation_id="short-rotation-replay",
    )
    assert isinstance(rotate_replay, ApiTokenMutationOutcomeV1)
    assert rotate_replay.code == "one_time_secret_not_replayable"
    assert rotate_replay.api_token_id == successor.token.api_token_id


@pytest.mark.parametrize(
    ("column", "value"),
    (("name", "unsafe\nlabel"), ("verification_digest", None)),
)
def test_altered_persisted_token_row_fails_closed_at_public_summary(
    real_iam_installation: tuple[DatabaseRefV1, str], column: str, value: str | None
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issued = CreateApiTokenV1(repository)(
        actor,
        name="safe label",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="corrupt_token_key_0001",
        correlation_id="corrupt-token-create",
    )
    assert isinstance(issued, ApiTokenCredentialIssueV1)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                f"UPDATE iam_api_token SET {column}=? WHERE api_token_id=?",
                (value, issued.token.api_token_id.value),
            )
            connection.commit()
    with pytest.raises(IdentityAccessRepositoryErrorV1):
        ListApiTokensV1(repository)(actor, correlation_id="corrupt-token-list")


def test_unknown_malformed_and_revoked_bearers_share_generic_denial(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issued = CreateApiTokenV1(repository)(
        actor,
        name="generic denial",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="generic_denial_key_0001",
        correlation_id="generic-denial-create",
    )
    assert isinstance(issued, ApiTokenCredentialIssueV1)
    revoked = RevokeApiTokenV1(repository)(
        actor,
        issued.token.api_token_id,
        issued.token.record_version,
        correlation_id="generic-denial-revoke",
    )
    assert revoked.code == "revoked"
    unknown = f"am1.{secrets.token_urlsafe(16)}.{secrets.token_urlsafe(32)}"
    wrong_version = "am2." + issued.bearer_credential.removeprefix("am1.")
    codes = tuple(
        ResolveBearerTokenV1(repository)(
            SecretInputV1(candidate), correlation_id=f"generic-denial-{index}"
        ).code
        for index, candidate in enumerate(
            (issued.bearer_credential, unknown, wrong_version, "am1.invalid")
        )
    )
    assert codes == ("dashboard_authentication_required",) * 4


def test_two_real_resolves_after_sixty_seconds_coalesce_one_persisted_touch(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    issued = CreateApiTokenV1(repository)(
        actor,
        name="touch",
        scopes=("read:diagnostics",),
        lifetime_seconds=None,
        idempotency_key="token_touch_key_0001",
        correlation_id="token-touch-create",
    )
    assert isinstance(issued, ApiTokenCredentialIssueV1)
    initial = ResolveBearerTokenV1(repository)(
        SecretInputV1(issued.bearer_credential), correlation_id="token-touch-initial"
    )
    assert initial.code == "authenticated"
    assert initial.token is not None
    assert initial.token.last_used_at is not None
    first_version = initial.token.record_version
    first_activity = initial.token.last_used_at
    started = time.monotonic()
    time.sleep(60.1)
    assert time.monotonic() - started >= 60

    def resolve(index: int) -> str:
        result = ResolveBearerTokenV1(
            SqliteIdentityAccessApiTokenRepositoryV1(reference)
        )(
            SecretInputV1(issued.bearer_credential),
            correlation_id=f"token-touch-concurrent-{index}",
        )
        return result.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert tuple(pool.map(resolve, (1, 2))) == ("authenticated", "authenticated")
    current = ListApiTokensV1(SqliteIdentityAccessApiTokenRepositoryV1(reference))(
        actor, correlation_id="token-touch-final"
    )
    assert len(current) == 1
    assert current[0].record_version == first_version + 1
    assert current[0].last_used_at is not None
    assert current[0].last_used_at >= first_activity + timedelta(seconds=60)
    assert current[0].last_used_at < current[0].expires_at


def test_altered_persisted_audit_row_fails_closed_at_event_projection(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, owner_credential = real_iam_installation
    actor = _owner_actor(reference, owner_credential)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "UPDATE iam_security_audit_event SET outcome_code='invalid' "
                "WHERE event_type='administrator_initialized'"
            )
            connection.commit()
    repository = SqliteIdentityAccessApiTokenRepositoryV1(reference)
    with pytest.raises(IdentityAccessRepositoryErrorV1):
        ListIamSecurityEventsV1(repository)(
            actor, correlation_id="corrupt-audit-projection"
        )
