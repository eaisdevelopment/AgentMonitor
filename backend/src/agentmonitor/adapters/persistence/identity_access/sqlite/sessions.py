"""M01 session/throttle repository over real owner-only, file-backed SQLite."""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    IdentityAccessRepositoryErrorV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    AuthenticationFailureV1,
    BrowserSessionResolutionV1,
    CsrfDecisionV1,
    PrincipalV1,
    SessionCredentialIssueV1,
    SessionMutationOutcomeV1,
    SessionSummaryV1,
)
from agentmonitor.modules.identity_access.application.authorization import (
    BROWSER_PERMISSIONS_V1,
)
from agentmonitor.modules.identity_access.application.errors import (
    PasswordHasherUnavailableV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    SessionPasswordHasherPortV1,
    SessionQueryErrorV1,
)
from agentmonitor.modules.identity_access.application.throttle import (
    LoginThrottleStateV1,
    after_failed_login,
    after_successful_login,
    retry_after_seconds,
)
from agentmonitor.modules.identity_access.domain.policy import (
    idempotency_receipt_expired,
    password_creation_error,
    session_deadlines,
    session_expired,
    session_state,
    should_touch_session,
    valid_correlation_id,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

_SESSION_WIRE = re.compile(r"am-s1\.([A-Za-z0-9_-]{22})\.([A-Za-z0-9_-]{43})\Z")
_CSRF_WIRE = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_DIGEST_WIRE = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_DUMMY_DIGEST = "0" * 64
_BUCKET = "installation_global"


def _text(instant: datetime) -> str:
    return instant.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _time(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.utcoffset() != timedelta(0):
            raise ValueError("non_utc_persisted_time")
        return instant
    except (AttributeError, TypeError, ValueError):
        raise IdentityAccessRepositoryErrorV1() from None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _stored_digest(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or _DIGEST_WIRE.fullmatch(value) is None:
        raise IdentityAccessRepositoryErrorV1() from None
    return value


def _audit(
    connection: Connection,
    *,
    event_type: str,
    outcome_code: str,
    instant: datetime,
    correlation_id: str,
    actor_id: str | None,
    target_type: str,
    target_id: str | None,
    aggregate_count: int | None = None,
) -> str:
    event_id = secrets.token_urlsafe(24)
    connection.exec_driver_sql(
        "INSERT INTO iam_security_audit_event "
        "(event_id, event_type, occurred_at, recorded_at, actor_principal_id, "
        "authentication_method, target_type, target_id, outcome_code, "
        "correlation_id, schema_version, aggregate_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
        (
            event_id,
            event_type,
            _text(instant),
            _text(instant),
            actor_id,
            "browser_session" if actor_id is not None else None,
            target_type,
            target_id,
            outcome_code,
            correlation_id,
            aggregate_count,
        ),
    )
    return event_id


def _throttle_state(connection: Connection, instant: datetime) -> LoginThrottleStateV1:
    row = connection.exec_driver_sql(
        "SELECT window_started_at, failure_count, consecutive_lock_count, "
        "locked_until FROM iam_login_throttle WHERE bucket_id=?",
        (_BUCKET,),
    ).one_or_none()
    if row is None:
        return LoginThrottleStateV1(instant, 0, 0, None)
    if (
        type(row[1]) is not int
        or type(row[2]) is not int
        or not 0 <= row[1] <= 2_147_483_647
        or not 0 <= row[2] <= 2_147_483_647
    ):
        raise IdentityAccessRepositoryErrorV1() from None
    return LoginThrottleStateV1(
        _time(row[0]), row[1], row[2], _time(row[3]) if row[3] is not None else None
    )


def _save_throttle(
    connection: Connection, state: LoginThrottleStateV1, instant: datetime
) -> None:
    connection.exec_driver_sql(
        "INSERT INTO iam_login_throttle "
        "(bucket_id, window_started_at, failure_count, consecutive_lock_count, "
        "locked_until, updated_at, record_version) VALUES (?, ?, ?, ?, ?, ?, 1) "
        "ON CONFLICT(bucket_id) DO UPDATE SET "
        "window_started_at=excluded.window_started_at, "
        "failure_count=excluded.failure_count, "
        "consecutive_lock_count=excluded.consecutive_lock_count, "
        "locked_until=excluded.locked_until, updated_at=excluded.updated_at, "
        "record_version=record_version+1",
        (
            _BUCKET,
            _text(state.window_started_at),
            state.failure_count,
            state.consecutive_lock_count,
            _text(state.locked_until) if state.locked_until else None,
            _text(instant),
        ),
    )


def _summary(row: RowMapping, *, current: bool, as_of: datetime) -> SessionSummaryV1:
    session_id = row["session_id"]
    issued = _time(row["issued_at"])
    last_activity = _time(row["last_activity_at"])
    idle = _time(row["idle_expires_at"])
    absolute = _time(row["absolute_expires_at"])
    state: Literal["active", "expired", "revoked"] = session_state(
        as_of,
        idle,
        absolute,
        _time(row["revoked_at"]) if row["revoked_at"] is not None else None,
        row["revocation_reason"],
    )
    return SessionSummaryV1(
        OpaqueIdV1(session_id),
        issued,
        last_activity,
        idle,
        absolute,
        state,
        current,
        row["record_version"],
    )


def _csrf_valid(row: RowMapping, cookie: str | None, header: str | None) -> bool:
    if (
        cookie is None
        or header is None
        or _CSRF_WIRE.fullmatch(cookie) is None
        or _CSRF_WIRE.fullmatch(header) is None
    ):
        return False
    if not hmac.compare_digest(cookie, header):
        return False
    stored = _stored_digest(row["csrf_digest"])
    return stored is not None and hmac.compare_digest(_digest(cookie), stored)


def _active(row: RowMapping | None, instant: datetime) -> bool:
    if row is None or row["revoked_at"] is not None:
        return False
    credential_digest = _stored_digest(row["credential_digest"])
    csrf_digest = _stored_digest(row["csrf_digest"])
    return (
        credential_digest is not None
        and csrf_digest is not None
        and not session_expired(
            instant,
            _time(row["idle_expires_at"]),
            _time(row["absolute_expires_at"]),
        )
    )


def _expire_if_due(
    connection: Connection,
    row: RowMapping | None,
    instant: datetime,
    correlation_id: str,
) -> bool:
    """Durably terminalize the first observed expired session in this write txn."""
    if row is None or row["revoked_at"] is not None:
        return False
    if not session_expired(
        instant,
        _time(row["idle_expires_at"]),
        _time(row["absolute_expires_at"]),
    ):
        return False
    connection.exec_driver_sql(
        "UPDATE iam_browser_session SET revoked_at=?, "
        "revocation_reason='expired', credential_digest=NULL, "
        "csrf_digest=NULL, record_version=record_version+1 "
        "WHERE session_id=? AND revoked_at IS NULL",
        (_text(instant), row["session_id"]),
    )
    _audit(
        connection,
        event_type="browser_session_expired",
        outcome_code="expired",
        instant=instant,
        correlation_id=correlation_id,
        actor_id=None,
        target_type="session",
        target_id=row["session_id"],
    )
    return True


def _issue_session(
    connection: Connection, administrator_id: str, instant: datetime
) -> SessionCredentialIssueV1:
    session_id = secrets.token_urlsafe(24)
    selector = secrets.token_urlsafe(16)
    credential = f"am-s1.{selector}.{secrets.token_urlsafe(32)}"
    csrf = secrets.token_urlsafe(32)
    idle, absolute = session_deadlines(instant)
    connection.exec_driver_sql(
        "INSERT INTO iam_browser_session "
        "(session_id, administrator_id, credential_selector, credential_digest, "
        "csrf_digest, issued_at, last_activity_at, idle_expires_at, "
        "absolute_expires_at, record_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (
            session_id,
            administrator_id,
            selector,
            _digest(credential),
            _digest(csrf),
            _text(instant),
            _text(instant),
            _text(idle),
            _text(absolute),
        ),
    )
    summary = SessionSummaryV1(
        OpaqueIdV1(session_id), instant, instant, idle, absolute, "active", True, 1
    )
    principal = PrincipalV1(
        OpaqueIdV1(administrator_id),
        "browser_session",
        OpaqueIdV1(session_id),
        BROWSER_PERMISSIONS_V1,
        instant,
        instant,
        absolute,
    )
    return SessionCredentialIssueV1(summary, principal, credential, csrf)


def _actor_row(
    connection: Connection,
    session_id: str,
    cookie: str | None,
    header: str | None,
    instant: datetime,
    correlation_id: str,
) -> tuple[RowMapping | None, SessionMutationOutcomeV1 | None]:
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM iam_browser_session WHERE session_id=?", (session_id,)
        )
        .mappings()
        .one_or_none()
    )
    _expire_if_due(connection, row, instant, correlation_id)
    if not _active(row, instant):
        return None, SessionMutationOutcomeV1("dashboard_authentication_required")
    assert row is not None
    if not _csrf_valid(row, cookie, header):
        return None, SessionMutationOutcomeV1("csrf_validation_failed")
    return row, None


def _receipt_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{16,128}\Z", key) is None:
        raise ValueError("idempotency_key_invalid") from None
    return _digest(key)


def _receipt(
    connection: Connection,
    principal_id: str,
    operation: str,
    key_digest: str,
    instant: datetime,
    correlation_id: str,
) -> tuple[str | None, str | None] | None:
    row = connection.exec_driver_sql(
        "SELECT request_fingerprint, resource_id, expires_at "
        "FROM iam_idempotency_record WHERE principal_id=? "
        "AND operation_key=? AND idempotency_key_digest=?",
        (principal_id, operation, key_digest),
    ).one_or_none()
    if row is None:
        return None
    if idempotency_receipt_expired(instant, _time(row[2])):
        connection.exec_driver_sql(
            "DELETE FROM iam_idempotency_record WHERE principal_id=? "
            "AND operation_key=? AND idempotency_key_digest=?",
            (principal_id, operation, key_digest),
        )
        _audit(
            connection,
            event_type="idempotency_receipt_reclaimed",
            outcome_code="reclaimed",
            instant=instant,
            correlation_id=correlation_id,
            actor_id=principal_id,
            target_type="administrator",
            target_id=principal_id,
            aggregate_count=1,
        )
        return None
    return _stored_digest(row[0]), row[1]


def _save_receipt(
    connection: Connection,
    principal_id: str,
    operation: str,
    key_digest: str,
    resource_id: str,
    instant: datetime,
    request_fingerprint: str | None = None,
) -> None:
    connection.exec_driver_sql(
        "INSERT INTO iam_idempotency_record "
        "(idempotency_id, principal_id, operation_key, idempotency_key_digest, "
        "request_fingerprint, state, resource_id, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, 'committed', ?, ?, ?)",
        (
            secrets.token_urlsafe(24),
            principal_id,
            operation,
            key_digest,
            request_fingerprint,
            resource_id,
            _text(instant),
            _text(instant + timedelta(seconds=86400)),
        ),
    )


class SqliteIdentityAccessSessionRepositoryV1:
    """All login/session transitions are atomic with their safe IAM audit facts."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def authenticate(
        self,
        candidate: str,
        hasher: SessionPasswordHasherPortV1,
        correlation_id: str,
        instant: datetime,
    ) -> SessionCredentialIssueV1 | AuthenticationFailureV1:
        if not valid_correlation_id(correlation_id):
            raise IdentityAccessRepositoryErrorV1() from None
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    administrator = connection.exec_driver_sql(
                        "SELECT administrator_id, password_phc, hash_policy_version "
                        "FROM iam_administrator LIMIT 1"
                    ).one_or_none()
                    if administrator is None:
                        connection.rollback()
                        return AuthenticationFailureV1("iam_setup_required")
                    if administrator[2] != "argon2id-rfc9106-low-memory-v1":
                        connection.rollback()
                        return AuthenticationFailureV1("iam_repository_unavailable")
                    throttle = _throttle_state(connection, instant)
                    remaining = retry_after_seconds(throttle, instant)
                    if remaining:
                        connection.rollback()
                        return AuthenticationFailureV1("login_throttled", remaining)
                    # The port is an admitted Argon2 adapter. A bounded candidate
                    # is verified exactly once inside this serialized attempt.
                    matched = hasher.verify(administrator[1], candidate)
                    if not matched:
                        updated = after_failed_login(throttle, instant)
                        _save_throttle(connection, updated, instant)
                        remaining = retry_after_seconds(updated, instant)
                        if remaining:
                            _audit(
                                connection,
                                event_type="login_throttle_activated",
                                outcome_code="login_throttled",
                                instant=instant,
                                correlation_id=correlation_id,
                                actor_id=None,
                                target_type="installation",
                                target_id=None,
                                aggregate_count=updated.failure_count,
                            )
                        connection.commit()
                        return (
                            AuthenticationFailureV1("login_throttled", remaining)
                            if remaining
                            else AuthenticationFailureV1("invalid_credentials")
                        )
                    if hasher.needs_rehash(administrator[1]):
                        refreshed_phc = hasher.hash(candidate)
                        connection.exec_driver_sql(
                            "UPDATE iam_administrator SET password_phc=?, "
                            "hash_policy_version=?, updated_at=?, "
                            "record_version=record_version+1 WHERE singleton_key=1",
                            (refreshed_phc, hasher.POLICY_VERSION, _text(instant)),
                        )
                    _save_throttle(
                        connection, after_successful_login(throttle, instant), instant
                    )
                    issue = _issue_session(connection, administrator[0], instant)
                    _audit(
                        connection,
                        event_type="login_succeeded",
                        outcome_code="authenticated",
                        instant=instant,
                        correlation_id=correlation_id,
                        actor_id=administrator[0],
                        target_type="session",
                        target_id=issue.session.session_id.value,
                    )
                    connection.commit()
                    return issue
        except (SqlitePolicyError, SQLAlchemyError, PasswordHasherUnavailableV1):
            raise IdentityAccessRepositoryErrorV1() from None

    def resolve(
        self, credential: str, correlation_id: str, instant: datetime
    ) -> BrowserSessionResolutionV1:
        denial = BrowserSessionResolutionV1(
            "dashboard_authentication_required", None, None
        )
        if not valid_correlation_id(correlation_id):
            raise IdentityAccessRepositoryErrorV1() from None
        if len(credential) > 512 or _SESSION_WIRE.fullmatch(credential) is None:
            return denial
        selector = credential.split(".", 2)[1]
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM iam_browser_session "
                            "WHERE credential_selector=?",
                            (selector,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    stored_digest = (
                        _stored_digest(row["credential_digest"])
                        if row is not None and row["revoked_at"] is None
                        else _DUMMY_DIGEST
                    )
                    matches = hmac.compare_digest(
                        _digest(credential), stored_digest or _DUMMY_DIGEST
                    )
                    if _expire_if_due(connection, row, instant, correlation_id):
                        connection.commit()
                        return denial
                    if not matches or not _active(row, instant):
                        connection.rollback()
                        return denial
                    assert row is not None
                    persisted_activity = _time(row["last_activity_at"])
                    if should_touch_session(instant, persisted_activity):
                        idle, _ = session_deadlines(
                            instant,
                            persisted_activity_at=persisted_activity,
                            persisted_idle_expires_at=_time(row["idle_expires_at"]),
                            absolute_expires_at=_time(row["absolute_expires_at"]),
                        )
                        connection.exec_driver_sql(
                            "UPDATE iam_browser_session SET last_activity_at=?, "
                            "idle_expires_at=?, record_version=record_version+1 "
                            "WHERE session_id=? AND revoked_at IS NULL",
                            (_text(instant), _text(idle), row["session_id"]),
                        )
                        row = (
                            connection.exec_driver_sql(
                                "SELECT * FROM iam_browser_session WHERE session_id=?",
                                (row["session_id"],),
                            )
                            .mappings()
                            .one()
                        )
                    summary = _summary(row, current=True, as_of=instant)
                    principal = PrincipalV1(
                        OpaqueIdV1(row["administrator_id"]),
                        "browser_session",
                        summary.session_id,
                        BROWSER_PERMISSIONS_V1,
                        summary.issued_at,
                        instant,
                        summary.absolute_expires_at,
                    )
                    connection.commit()
                    return BrowserSessionResolutionV1(
                        "authenticated", principal, summary
                    )
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def verify_csrf(
        self,
        session_id: str,
        cookie: str | None,
        header: str | None,
        correlation_id: str,
        instant: datetime,
    ) -> CsrfDecisionV1:
        if not valid_correlation_id(correlation_id):
            raise IdentityAccessRepositoryErrorV1() from None
        if _SAFE_ID.fullmatch(session_id) is None:
            return CsrfDecisionV1("csrf_validation_failed")
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM iam_browser_session WHERE session_id=?",
                            (session_id,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if _expire_if_due(connection, row, instant, correlation_id):
                        connection.commit()
                        return CsrfDecisionV1("csrf_validation_failed")
                    decision = CsrfDecisionV1(
                        "valid"
                        if row is not None
                        and _active(row, instant)
                        and _csrf_valid(row, cookie, header)
                        else "csrf_validation_failed"
                    )
                    connection.commit()
                    return decision
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def logout(
        self,
        session_id: str,
        version: int,
        cookie: str | None,
        header: str | None,
        correlation_id: str,
        instant: datetime,
    ) -> SessionMutationOutcomeV1:
        if not valid_correlation_id(correlation_id):
            raise IdentityAccessRepositoryErrorV1() from None
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM iam_browser_session WHERE session_id=?",
                            (session_id,),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if _expire_if_due(connection, row, instant, correlation_id):
                        connection.commit()
                        return SessionMutationOutcomeV1(
                            "dashboard_authentication_required"
                        )
                    if not _active(row, instant):
                        connection.rollback()
                        return SessionMutationOutcomeV1(
                            "dashboard_authentication_required"
                        )
                    assert row is not None
                    if not _csrf_valid(row, cookie, header):
                        connection.rollback()
                        return SessionMutationOutcomeV1("csrf_validation_failed")
                    if row["record_version"] != version:
                        connection.rollback()
                        return SessionMutationOutcomeV1("precondition_failed")
                    connection.exec_driver_sql(
                        "UPDATE iam_browser_session SET revoked_at=?, "
                        "revocation_reason='logout', credential_digest=NULL, "
                        "csrf_digest=NULL, record_version=record_version+1 "
                        "WHERE session_id=?",
                        (_text(instant), session_id),
                    )
                    _audit(
                        connection,
                        event_type="browser_session_revoked",
                        outcome_code="revoked",
                        instant=instant,
                        correlation_id=correlation_id,
                        actor_id=row["administrator_id"],
                        target_type="session",
                        target_id=session_id,
                    )
                    connection.commit()
                    return SessionMutationOutcomeV1("revoked", 1)
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def list_sessions(
        self,
        administrator_id: str,
        current_session_id: str,
        limit: int,
        cursor: str | None,
        correlation_id: str,
    ) -> tuple[SessionSummaryV1, ...]:
        """Bounded keyset page; caller supplies an authenticated browser principal."""
        if not valid_correlation_id(correlation_id):
            raise IdentityAccessRepositoryErrorV1() from None
        if not 1 <= limit <= 200:
            raise ValueError("session_list_limit_invalid")
        instant = datetime.now(UTC)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    actor = (
                        connection.exec_driver_sql(
                            "SELECT * FROM iam_browser_session WHERE session_id=? "
                            "AND administrator_id=?",
                            (current_session_id, administrator_id),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if _expire_if_due(connection, actor, instant, correlation_id):
                        connection.commit()
                        raise SessionQueryErrorV1("dashboard_authentication_required")
                    if not _active(actor, instant):
                        raise SessionQueryErrorV1("dashboard_authentication_required")
                    if cursor is None:
                        rows = (
                            connection.exec_driver_sql(
                                "SELECT * FROM iam_browser_session "
                                "WHERE administrator_id=? "
                                "ORDER BY issued_at DESC, session_id DESC LIMIT ?",
                                (administrator_id, limit),
                            )
                            .mappings()
                            .all()
                        )
                    else:
                        cursor_row = connection.exec_driver_sql(
                            "SELECT issued_at FROM iam_browser_session "
                            "WHERE session_id=? AND administrator_id=?",
                            (cursor, administrator_id),
                        ).one_or_none()
                        if cursor_row is None:
                            raise SessionQueryErrorV1("session_cursor_invalid")
                        rows = (
                            connection.exec_driver_sql(
                                "SELECT * FROM iam_browser_session "
                                "WHERE administrator_id=? "
                                "AND (issued_at < ? OR "
                                "(issued_at = ? AND session_id < ?)) "
                                "ORDER BY issued_at DESC, session_id DESC LIMIT ?",
                                (
                                    administrator_id,
                                    cursor_row[0],
                                    cursor_row[0],
                                    cursor,
                                    limit,
                                ),
                            )
                            .mappings()
                            .all()
                        )
                    summaries: list[SessionSummaryV1] = []
                    for row in rows:
                        if _expire_if_due(connection, row, instant, correlation_id):
                            row = (
                                connection.exec_driver_sql(
                                    "SELECT * FROM iam_browser_session "
                                    "WHERE session_id=?",
                                    (row["session_id"],),
                                )
                                .mappings()
                                .one()
                            )
                        summaries.append(
                            _summary(
                                row,
                                current=row["session_id"] == current_session_id,
                                as_of=instant,
                            )
                        )
                    connection.commit()
                    return tuple(summaries)
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def revoke_session(
        self,
        actor_session_id: str,
        target_session_id: str,
        target_version: int,
        cookie: str | None,
        header: str | None,
        correlation_id: str,
        instant: datetime,
    ) -> SessionMutationOutcomeV1:
        if not valid_correlation_id(correlation_id):
            raise IdentityAccessRepositoryErrorV1() from None
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    actor, denial = _actor_row(
                        connection,
                        actor_session_id,
                        cookie,
                        header,
                        instant,
                        correlation_id,
                    )
                    if denial is not None:
                        connection.commit()
                        return denial
                    assert actor is not None
                    target = (
                        connection.exec_driver_sql(
                            "SELECT * FROM iam_browser_session WHERE session_id=? "
                            "AND administrator_id=?",
                            (target_session_id, actor["administrator_id"]),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if target is None:
                        connection.rollback()
                        return SessionMutationOutcomeV1("session_not_found")
                    if _expire_if_due(connection, target, instant, correlation_id):
                        connection.commit()
                        return SessionMutationOutcomeV1("revoked", 0)
                    if target["revoked_at"] is not None:
                        connection.rollback()
                        return SessionMutationOutcomeV1("revoked", 0)
                    if target["record_version"] != target_version:
                        connection.rollback()
                        return SessionMutationOutcomeV1("precondition_failed")
                    connection.exec_driver_sql(
                        "UPDATE iam_browser_session SET revoked_at=?, "
                        "revocation_reason='administrator', credential_digest=NULL, "
                        "csrf_digest=NULL, record_version=record_version+1 "
                        "WHERE session_id=? AND revoked_at IS NULL",
                        (_text(instant), target_session_id),
                    )
                    _audit(
                        connection,
                        event_type="browser_session_revoked",
                        outcome_code="revoked",
                        instant=instant,
                        correlation_id=correlation_id,
                        actor_id=actor["administrator_id"],
                        target_type="session",
                        target_id=target_session_id,
                    )
                    connection.commit()
                    return SessionMutationOutcomeV1("revoked", 1)
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def revoke_other_sessions(
        self,
        actor_session_id: str,
        cookie: str | None,
        header: str | None,
        idempotency_key: str,
        correlation_id: str,
        instant: datetime,
    ) -> SessionMutationOutcomeV1:
        key_digest = _receipt_key(idempotency_key)
        if not valid_correlation_id(correlation_id):
            raise IdentityAccessRepositoryErrorV1() from None
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    actor, denial = _actor_row(
                        connection,
                        actor_session_id,
                        cookie,
                        header,
                        instant,
                        correlation_id,
                    )
                    if denial is not None:
                        connection.commit()
                        return denial
                    assert actor is not None
                    admin_id = actor["administrator_id"]
                    fingerprint = _digest(actor_session_id)
                    receipt = _receipt(
                        connection,
                        admin_id,
                        "revoke_other_sessions",
                        key_digest,
                        instant,
                        correlation_id,
                    )
                    if receipt is not None:
                        if not hmac.compare_digest(receipt[0] or "", fingerprint):
                            connection.rollback()
                            return SessionMutationOutcomeV1("idempotency_key_reused")
                        count = connection.exec_driver_sql(
                            "SELECT aggregate_count FROM iam_security_audit_event "
                            "WHERE event_id=? AND "
                            "event_type='other_browser_sessions_revoked'",
                            (receipt[1],),
                        ).scalar_one_or_none()
                        connection.rollback()
                        if type(count) is not int or count < 0:
                            raise IdentityAccessRepositoryErrorV1() from None
                        return SessionMutationOutcomeV1("revoked", count)
                    changed = connection.exec_driver_sql(
                        "UPDATE iam_browser_session SET revoked_at=?, "
                        "revocation_reason='administrator', credential_digest=NULL, "
                        "csrf_digest=NULL, record_version=record_version+1 "
                        "WHERE administrator_id=? AND session_id<>? "
                        "AND revoked_at IS NULL",
                        (_text(instant), admin_id, actor_session_id),
                    ).rowcount
                    event_id = _audit(
                        connection,
                        event_type="other_browser_sessions_revoked",
                        outcome_code="revoked",
                        instant=instant,
                        correlation_id=correlation_id,
                        actor_id=admin_id,
                        target_type="administrator",
                        target_id=admin_id,
                        aggregate_count=changed,
                    )
                    _save_receipt(
                        connection,
                        admin_id,
                        "revoke_other_sessions",
                        key_digest,
                        event_id,
                        instant,
                        fingerprint,
                    )
                    connection.commit()
                    return SessionMutationOutcomeV1("revoked", changed)
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def change_password(
        self,
        actor_session_id: str,
        actor_version: int,
        cookie: str | None,
        header: str | None,
        current_candidate: str,
        new_candidate: str,
        hasher: SessionPasswordHasherPortV1,
        idempotency_key: str,
        correlation_id: str,
        instant: datetime,
    ) -> SessionCredentialIssueV1 | SessionMutationOutcomeV1:
        key_digest = _receipt_key(idempotency_key)
        if not valid_correlation_id(correlation_id):
            raise IdentityAccessRepositoryErrorV1() from None
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    actor, denial = _actor_row(
                        connection,
                        actor_session_id,
                        cookie,
                        header,
                        instant,
                        correlation_id,
                    )
                    if denial is not None:
                        connection.commit()
                        return denial
                    assert actor is not None
                    admin_id = actor["administrator_id"]
                    if (
                        _receipt(
                            connection,
                            admin_id,
                            "change_password",
                            key_digest,
                            instant,
                            correlation_id,
                        )
                        is not None
                    ):
                        connection.rollback()
                        return SessionMutationOutcomeV1(
                            "one_time_secret_not_replayable"
                        )
                    if password_creation_error(new_candidate) is not None:
                        connection.rollback()
                        return SessionMutationOutcomeV1("password_policy_violation")
                    if actor["record_version"] != actor_version:
                        connection.rollback()
                        return SessionMutationOutcomeV1("precondition_failed")
                    admin = connection.exec_driver_sql(
                        "SELECT password_phc, record_version, hash_policy_version "
                        "FROM iam_administrator WHERE administrator_id=?",
                        (admin_id,),
                    ).one_or_none()
                    if admin is None or admin[2] != hasher.POLICY_VERSION:
                        connection.rollback()
                        raise IdentityAccessRepositoryErrorV1() from None
                    throttle = _throttle_state(connection, instant)
                    remaining = retry_after_seconds(throttle, instant)
                    if remaining:
                        connection.rollback()
                        return SessionMutationOutcomeV1(
                            "login_throttled", retry_after_seconds=remaining
                        )
                    if not hasher.verify(admin[0], current_candidate):
                        updated = after_failed_login(throttle, instant)
                        _save_throttle(connection, updated, instant)
                        remaining = retry_after_seconds(updated, instant)
                        if remaining:
                            _audit(
                                connection,
                                event_type="login_throttle_activated",
                                outcome_code="login_throttled",
                                instant=instant,
                                correlation_id=correlation_id,
                                actor_id=None,
                                target_type="installation",
                                target_id=None,
                                aggregate_count=updated.failure_count,
                            )
                        connection.commit()
                        return (
                            SessionMutationOutcomeV1(
                                "login_throttled", retry_after_seconds=remaining
                            )
                            if remaining
                            else SessionMutationOutcomeV1("invalid_credentials")
                        )
                    _save_throttle(
                        connection, after_successful_login(throttle, instant), instant
                    )
                    replacement_phc = hasher.hash(new_candidate)
                    connection.exec_driver_sql(
                        "UPDATE iam_administrator SET password_phc=?, "
                        "hash_policy_version=?, password_changed_at=?, updated_at=?, "
                        "record_version=record_version+1 WHERE administrator_id=? "
                        "AND record_version=?",
                        (
                            replacement_phc,
                            hasher.POLICY_VERSION,
                            _text(instant),
                            _text(instant),
                            admin_id,
                            admin[1],
                        ),
                    )
                    connection.exec_driver_sql(
                        "UPDATE iam_browser_session SET revoked_at=?, "
                        "revocation_reason='password_change', credential_digest=NULL, "
                        "csrf_digest=NULL, record_version=record_version+1 "
                        "WHERE administrator_id=? AND revoked_at IS NULL",
                        (_text(instant), admin_id),
                    )
                    issue = _issue_session(connection, admin_id, instant)
                    _save_receipt(
                        connection,
                        admin_id,
                        "change_password",
                        key_digest,
                        issue.session.session_id.value,
                        instant,
                    )
                    _audit(
                        connection,
                        event_type="administrator_password_changed",
                        outcome_code="changed",
                        instant=instant,
                        correlation_id=correlation_id,
                        actor_id=admin_id,
                        target_type="administrator",
                        target_id=admin_id,
                    )
                    connection.commit()
                    return issue
        except (SqlitePolicyError, SQLAlchemyError, PasswordHasherUnavailableV1):
            raise IdentityAccessRepositoryErrorV1() from None
