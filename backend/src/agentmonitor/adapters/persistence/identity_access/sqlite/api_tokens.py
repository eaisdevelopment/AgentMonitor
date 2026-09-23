"""M01 token and safe IAM-audit repository over migrated owner-only SQLite."""

import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta
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
    ApiTokenCredentialIssueV1,
    ApiTokenMutationOutcomeV1,
    ApiTokenSummaryV1,
    BearerTokenResolutionV1,
    IamSecurityEventViewV1,
    PrincipalV1,
    TokenCallerProofV1,
)
from agentmonitor.modules.identity_access.application.api_tokens import (
    TokenQueryErrorV1,
)
from agentmonitor.modules.identity_access.domain.policy import (
    M2_ISSUABLE_SCOPES,
    canonical_token_name,
    idempotency_receipt_expired,
    may_issue_scopes,
    may_manage_token,
    session_expired,
    token_deadline,
    token_should_touch,
    token_state,
    valid_correlation_id,
)
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

_TOKEN_WIRE = re.compile(r"am1\.([A-Za-z0-9_-]{22})\.([A-Za-z0-9_-]{43})\Z")
_SESSION_WIRE = re.compile(r"am-s1\.([A-Za-z0-9_-]{22})\.([A-Za-z0-9_-]{43})\Z")
_CSRF_WIRE = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_RECEIPT_KEY = re.compile(r"[A-Za-z0-9_-]{16,128}\Z")
_DIGEST_WIRE = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_CODE = re.compile(r"[a-z_]{1,64}\Z")
_DUMMY_DIGEST = "0" * 64
_ACTIVE_TOKEN_CAP = 64


def _text(instant: datetime) -> str:
    return instant.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _time(value: object) -> datetime:
    if type(value) is not str:
        raise IdentityAccessRepositoryErrorV1() from None
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.utcoffset() != timedelta(0):
            raise ValueError("persisted_time_not_utc")
        return instant
    except ValueError:
        raise IdentityAccessRepositoryErrorV1() from None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _stored_digest(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or _DIGEST_WIRE.fullmatch(value) is None:
        raise IdentityAccessRepositoryErrorV1() from None
    return value


def _canonical_segment(value: str, byte_count: int) -> bool:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error):
        return False
    return len(raw) == byte_count and (
        base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") == value
    )


def _wire_parts(value: str, pattern: re.Pattern[str]) -> tuple[str, str] | None:
    if len(value) > 512:
        return None
    match = pattern.fullmatch(value)
    if match is None:
        return None
    selector, secret = match.groups()
    if not _canonical_segment(selector, 16) or not _canonical_segment(secret, 32):
        return None
    return selector, secret


def _validate_correlation(correlation_id: str) -> None:
    if not valid_correlation_id(correlation_id):
        raise IdentityAccessRepositoryErrorV1() from None


def _audit(
    connection: Connection,
    *,
    event_type: str,
    outcome_code: str,
    instant: datetime,
    correlation_id: str,
    actor_id: str | None,
    authentication_method: str | None,
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
            authentication_method,
            target_type,
            target_id,
            outcome_code,
            correlation_id,
            aggregate_count,
        ),
    )
    return event_id


def _scope_tuple(connection: Connection, token_id: str) -> tuple[str, ...]:
    rows = connection.exec_driver_sql(
        "SELECT scope_key FROM iam_api_token_scope WHERE api_token_id=? "
        "ORDER BY scope_key",
        (token_id,),
    ).all()
    scopes = tuple(row[0] for row in rows)
    if not scopes or any(
        type(scope) is not str or scope not in M2_ISSUABLE_SCOPES for scope in scopes
    ):
        raise IdentityAccessRepositoryErrorV1() from None
    return scopes


def _token_row(connection: Connection, token_id: str) -> RowMapping | None:
    return (
        connection.exec_driver_sql(
            "SELECT * FROM iam_api_token WHERE api_token_id=?", (token_id,)
        )
        .mappings()
        .one_or_none()
    )


def _token_summary(
    connection: Connection, row: RowMapping, instant: datetime
) -> ApiTokenSummaryV1:
    selector = row["public_selector"]
    if (
        type(selector) is not str
        or len(selector) != 22
        or not _canonical_segment(selector, 16)
        or row["safe_prefix"] != selector[:8]
    ):
        raise IdentityAccessRepositoryErrorV1() from None
    digest = _stored_digest(row["verification_digest"])
    if (row["revoked_at"] is None) != (digest is not None):
        raise IdentityAccessRepositoryErrorV1() from None
    issued = _time(row["issued_at"])
    expires = _time(row["expires_at"])
    revoked = _time(row["revoked_at"]) if row["revoked_at"] is not None else None
    last_used = _time(row["last_used_at"]) if row["last_used_at"] is not None else None
    state = token_state(instant, expires, revoked, row["revocation_reason"])
    try:
        return ApiTokenSummaryV1(
            OpaqueIdV1(row["api_token_id"]),
            row["name"],
            row["safe_prefix"],
            _scope_tuple(connection, row["api_token_id"]),
            issued,
            expires,
            last_used,
            revoked,
            row["revocation_reason"],
            (
                OpaqueIdV1(row["rotated_from_token_id"])
                if row["rotated_from_token_id"] is not None
                else None
            ),
            (
                OpaqueIdV1(row["replacement_token_id"])
                if row["replacement_token_id"] is not None
                else None
            ),
            state,
            row["record_version"],
        )
    except (TypeError, ValueError):
        raise IdentityAccessRepositoryErrorV1() from None


def _expire_token(
    connection: Connection,
    row: RowMapping | None,
    instant: datetime,
    correlation_id: str,
) -> bool:
    if row is None or row["revoked_at"] is not None:
        return False
    if instant < _time(row["expires_at"]):
        return False
    connection.exec_driver_sql(
        "UPDATE iam_api_token SET revoked_at=?, revocation_reason='expired', "
        "verification_digest=NULL, record_version=record_version+1 "
        "WHERE api_token_id=? AND revoked_at IS NULL",
        (_text(instant), row["api_token_id"]),
    )
    _audit(
        connection,
        event_type="api_token_expired",
        outcome_code="expired",
        instant=instant,
        correlation_id=correlation_id,
        actor_id=None,
        authentication_method=None,
        target_type="api_token",
        target_id=row["api_token_id"],
    )
    return True


def _expire_session(
    connection: Connection,
    row: RowMapping | None,
    instant: datetime,
    correlation_id: str,
) -> bool:
    if row is None or row["revoked_at"] is not None:
        return False
    if not session_expired(
        instant, _time(row["idle_expires_at"]), _time(row["absolute_expires_at"])
    ):
        return False
    connection.exec_driver_sql(
        "UPDATE iam_browser_session SET revoked_at=?, revocation_reason='expired', "
        "credential_digest=NULL, csrf_digest=NULL, "
        "record_version=record_version+1 "
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
        authentication_method=None,
        target_type="session",
        target_id=row["session_id"],
    )
    return True


def _session_csrf_valid(
    row: RowMapping, cookie: str | None, header: str | None
) -> bool:
    if (
        cookie is None
        or header is None
        or _CSRF_WIRE.fullmatch(cookie) is None
        or _CSRF_WIRE.fullmatch(header) is None
        or not hmac.compare_digest(cookie, header)
    ):
        return False
    stored = _stored_digest(row["csrf_digest"])
    return stored is not None and hmac.compare_digest(_digest(cookie), stored)


class _Authority:
    __slots__ = ("administrator_id", "method", "credential_id", "scopes", "expires_at")

    def __init__(
        self,
        administrator_id: str,
        method: Literal["browser_session", "api_bearer"],
        credential_id: str,
        scopes: frozenset[str],
        expires_at: datetime,
    ) -> None:
        self.administrator_id = administrator_id
        self.method = method
        self.credential_id = credential_id
        self.scopes = scopes
        self.expires_at = expires_at


def _authorize_caller(
    connection: Connection,
    caller: TokenCallerProofV1,
    instant: datetime,
    correlation_id: str,
    *,
    required_permission: str,
    mutation: bool,
) -> tuple[_Authority | None, str | None]:
    credential = caller.credential.reveal_for_verification()
    if caller.method == "browser_session":
        parts = _wire_parts(credential, _SESSION_WIRE)
        if parts is None:
            return None, "dashboard_authentication_required"
        row = (
            connection.exec_driver_sql(
                "SELECT * FROM iam_browser_session WHERE credential_selector=?",
                (parts[0],),
            )
            .mappings()
            .one_or_none()
        )
        stored = (
            _stored_digest(row["credential_digest"])
            if row is not None and row["revoked_at"] is None
            else _DUMMY_DIGEST
        )
        matches = hmac.compare_digest(_digest(credential), stored or _DUMMY_DIGEST)
        if _expire_session(connection, row, instant, correlation_id):
            return None, "dashboard_authentication_required"
        if row is None or not matches or row["revoked_at"] is not None:
            return None, "dashboard_authentication_required"
        if (
            _stored_digest(row["credential_digest"]) is None
            or _stored_digest(row["csrf_digest"]) is None
        ):
            return None, "dashboard_authentication_required"
        if mutation and not _session_csrf_valid(
            row,
            (
                caller.csrf_cookie.reveal_for_verification()
                if caller.csrf_cookie is not None
                else None
            ),
            (
                caller.csrf_header.reveal_for_verification()
                if caller.csrf_header is not None
                else None
            ),
        ):
            return None, "csrf_validation_failed"
        if required_permission not in {
            "write:tokens",
            "read:accounts",
            "read:diagnostics",
            "read:status",
            "read:telemetry",
        }:
            return None, "permission_denied"
        return (
            _Authority(
                row["administrator_id"],
                "browser_session",
                row["session_id"],
                M2_ISSUABLE_SCOPES,
                _time(row["absolute_expires_at"]),
            ),
            None,
        )
    parts = _wire_parts(credential, _TOKEN_WIRE)
    if parts is None:
        return None, "dashboard_authentication_required"
    row = (
        connection.exec_driver_sql(
            "SELECT * FROM iam_api_token WHERE public_selector=?", (parts[0],)
        )
        .mappings()
        .one_or_none()
    )
    stored = (
        _stored_digest(row["verification_digest"])
        if row is not None and row["revoked_at"] is None
        else _DUMMY_DIGEST
    )
    matches = hmac.compare_digest(_digest(credential), stored or _DUMMY_DIGEST)
    if _expire_token(connection, row, instant, correlation_id):
        return None, "dashboard_authentication_required"
    if row is None or not matches or row["revoked_at"] is not None or stored is None:
        return None, "dashboard_authentication_required"
    scopes = frozenset(_scope_tuple(connection, row["api_token_id"]))
    if required_permission not in scopes:
        return None, "permission_denied"
    return (
        _Authority(
            row["administrator_id"],
            "api_bearer",
            row["api_token_id"],
            scopes,
            _time(row["expires_at"]),
        ),
        None,
    )


def _receipt_digest(key: str) -> str:
    if _RECEIPT_KEY.fullmatch(key) is None:
        raise ValueError("idempotency_key_invalid") from None
    return _digest(key)


def _issuer_context(authority: _Authority) -> str:
    return _digest(
        f"{authority.administrator_id}:{authority.method}:{authority.credential_id}"
    )


def _request_fingerprint(*parts: object) -> str:
    canonical = json.dumps(parts, ensure_ascii=True, separators=(",", ":"))
    return _digest(canonical)


def _receipt(
    connection: Connection,
    issuer_context: str,
    operation: str,
    key_digest: str,
    instant: datetime,
    correlation_id: str,
    authority: _Authority,
) -> tuple[str, str] | None:
    row = connection.exec_driver_sql(
        "SELECT request_fingerprint, resource_id, expires_at "
        "FROM iam_idempotency_record WHERE principal_id=? "
        "AND operation_key=? AND idempotency_key_digest=?",
        (issuer_context, operation, key_digest),
    ).one_or_none()
    if row is None:
        return None
    if idempotency_receipt_expired(instant, _time(row[2])):
        connection.exec_driver_sql(
            "DELETE FROM iam_idempotency_record WHERE principal_id=? "
            "AND operation_key=? AND idempotency_key_digest=?",
            (issuer_context, operation, key_digest),
        )
        _audit(
            connection,
            event_type="idempotency_receipt_reclaimed",
            outcome_code="reclaimed",
            instant=instant,
            correlation_id=correlation_id,
            actor_id=authority.administrator_id,
            authentication_method=authority.method,
            target_type="administrator",
            target_id=authority.administrator_id,
            aggregate_count=1,
        )
        return None
    fingerprint = _stored_digest(row[0])
    if (
        fingerprint is None
        or type(row[1]) is not str
        or _SAFE_ID.fullmatch(row[1]) is None
    ):
        raise IdentityAccessRepositoryErrorV1() from None
    return fingerprint, row[1]


def _save_receipt(
    connection: Connection,
    issuer_context: str,
    operation: str,
    key_digest: str,
    fingerprint: str,
    resource_id: str,
    instant: datetime,
) -> None:
    connection.exec_driver_sql(
        "INSERT INTO iam_idempotency_record "
        "(idempotency_id, principal_id, operation_key, idempotency_key_digest, "
        "request_fingerprint, state, resource_id, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, 'committed', ?, ?, ?)",
        (
            secrets.token_urlsafe(24),
            issuer_context,
            operation,
            key_digest,
            fingerprint,
            resource_id,
            _text(instant),
            _text(instant + timedelta(seconds=86400)),
        ),
    )


def _issue_token(
    connection: Connection,
    administrator_id: str,
    name: str,
    scopes: tuple[str, ...],
    expires_at: datetime,
    instant: datetime,
    *,
    code: Literal["created", "rotated"],
    predecessor_id: str | None = None,
) -> ApiTokenCredentialIssueV1:
    token_id = secrets.token_urlsafe(24)
    selector = secrets.token_urlsafe(16)
    credential = f"am1.{selector}.{secrets.token_urlsafe(32)}"
    connection.exec_driver_sql(
        "INSERT INTO iam_api_token "
        "(api_token_id, administrator_id, name, public_selector, safe_prefix, "
        "verification_digest, issued_at, expires_at, rotated_from_token_id, "
        "record_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (
            token_id,
            administrator_id,
            name,
            selector,
            selector[:8],
            _digest(credential),
            _text(instant),
            _text(expires_at),
            predecessor_id,
        ),
    )
    for scope in scopes:
        connection.exec_driver_sql(
            "INSERT INTO iam_api_token_scope (api_token_id, scope_key) VALUES (?, ?)",
            (token_id, scope),
        )
    summary = _token_summary(connection, _token_row(connection, token_id), instant)  # type: ignore[arg-type]
    return ApiTokenCredentialIssueV1(code, summary, credential)


def _replay_summary(
    connection: Connection,
    row: RowMapping,
    instant: datetime,
    correlation_id: str,
) -> tuple[ApiTokenSummaryV1, bool]:
    expired = _expire_token(connection, row, instant, correlation_id)
    if expired:
        refreshed = _token_row(connection, row["api_token_id"])
        assert refreshed is not None
        row = refreshed
    return _token_summary(connection, row, instant), expired


class SqliteIdentityAccessApiTokenRepositoryV1:
    """Short serialized token transitions with safe audit and no plaintext storage."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def resolve_bearer(
        self, credential: str, correlation_id: str, instant: datetime
    ) -> BearerTokenResolutionV1:
        _validate_correlation(correlation_id)
        denial = BearerTokenResolutionV1(
            "dashboard_authentication_required", None, None
        )
        parts = _wire_parts(credential, _TOKEN_WIRE)
        if parts is None:
            return denial
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    row = (
                        connection.exec_driver_sql(
                            "SELECT * FROM iam_api_token WHERE public_selector=?",
                            (parts[0],),
                        )
                        .mappings()
                        .one_or_none()
                    )
                    stored = (
                        _stored_digest(row["verification_digest"])
                        if row is not None and row["revoked_at"] is None
                        else _DUMMY_DIGEST
                    )
                    matches = hmac.compare_digest(
                        _digest(credential), stored or _DUMMY_DIGEST
                    )
                    if _expire_token(connection, row, instant, correlation_id):
                        connection.commit()
                        return denial
                    if row is None or not matches or row["revoked_at"] is not None:
                        connection.rollback()
                        return denial
                    if stored is None:
                        connection.rollback()
                        return denial
                    if token_should_touch(
                        instant,
                        _time(row["last_used_at"])
                        if row["last_used_at"] is not None
                        else None,
                    ):
                        connection.exec_driver_sql(
                            "UPDATE iam_api_token SET last_used_at=?, "
                            "record_version=record_version+1 "
                            "WHERE api_token_id=? AND revoked_at IS NULL",
                            (_text(instant), row["api_token_id"]),
                        )
                        row = _token_row(connection, row["api_token_id"])
                    assert row is not None
                    summary = _token_summary(connection, row, instant)
                    principal = PrincipalV1(
                        OpaqueIdV1(row["administrator_id"]),
                        "api_bearer",
                        summary.api_token_id,
                        summary.scopes,
                        summary.issued_at,
                        instant,
                        summary.expires_at,
                    )
                    connection.commit()
                    return BearerTokenResolutionV1("authenticated", principal, summary)
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def list_tokens(
        self,
        caller: TokenCallerProofV1,
        limit: int,
        cursor: str | None,
        correlation_id: str,
        instant: datetime,
    ) -> tuple[ApiTokenSummaryV1, ...]:
        _validate_correlation(correlation_id)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    authority, denial = _authorize_caller(
                        connection,
                        caller,
                        instant,
                        correlation_id,
                        required_permission="write:tokens",
                        mutation=False,
                    )
                    if denial is not None:
                        connection.commit()
                        raise TokenQueryErrorV1(denial)
                    assert authority is not None
                    if type(limit) is not int or not 1 <= limit <= 200:
                        raise TokenQueryErrorV1("token_list_limit_invalid")
                    if cursor is not None and _SAFE_ID.fullmatch(cursor) is None:
                        raise TokenQueryErrorV1("token_cursor_invalid")
                    cursor_time: str | None = None
                    if cursor is not None:
                        cursor_row = _token_row(connection, cursor)
                        if (
                            cursor_row is None
                            or cursor_row["administrator_id"]
                            != authority.administrator_id
                        ):
                            raise TokenQueryErrorV1("token_cursor_invalid")
                        if authority.method == "api_bearer" and not may_manage_token(
                            authority.scopes,
                            frozenset(_scope_tuple(connection, cursor)),
                        ):
                            raise TokenQueryErrorV1("token_cursor_invalid")
                        cursor_time = cursor_row["issued_at"]
                    params: tuple[object, ...] = (authority.administrator_id,)
                    visibility = ""
                    if authority.method == "api_bearer":
                        held = tuple(sorted(authority.scopes))
                        placeholders = ",".join("?" for _ in held)
                        visibility = (
                            " AND NOT EXISTS (SELECT 1 FROM iam_api_token_scope vs "
                            "WHERE vs.api_token_id=t.api_token_id "
                            f"AND vs.scope_key NOT IN ({placeholders}))"
                        )
                        params += held
                    keyset = ""
                    if cursor is not None:
                        keyset = (
                            " AND (t.issued_at < ? OR "
                            "(t.issued_at = ? AND t.api_token_id < ?))"
                        )
                        params += (cursor_time, cursor_time, cursor)
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT t.* FROM iam_api_token t WHERE t.administrator_id=?"
                            + visibility
                            + keyset
                            + " ORDER BY t.issued_at DESC, t.api_token_id DESC LIMIT ?",
                            params + (limit,),
                        )
                        .mappings()
                        .all()
                    )
                    summaries: list[ApiTokenSummaryV1] = []
                    for row in rows:
                        if _expire_token(connection, row, instant, correlation_id):
                            refreshed = _token_row(connection, row["api_token_id"])
                            assert refreshed is not None
                            summaries.append(
                                _token_summary(connection, refreshed, instant)
                            )
                        else:
                            summaries.append(_token_summary(connection, row, instant))
                    connection.commit()
                    return tuple(summaries)
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def create_token(
        self,
        caller: TokenCallerProofV1,
        name: str,
        scopes: tuple[str, ...],
        lifetime_seconds: int | None,
        idempotency_key: str,
        correlation_id: str,
        instant: datetime,
    ) -> ApiTokenCredentialIssueV1 | ApiTokenMutationOutcomeV1:
        _validate_correlation(correlation_id)
        key_digest = _receipt_digest(idempotency_key)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    authority, denial = _authorize_caller(
                        connection,
                        caller,
                        instant,
                        correlation_id,
                        required_permission="write:tokens",
                        mutation=True,
                    )
                    if denial is not None:
                        connection.commit()
                        return ApiTokenMutationOutcomeV1(denial)  # type: ignore[arg-type]
                    assert authority is not None
                    normalized_name = canonical_token_name(name)
                    try:
                        expires_at = token_deadline(instant, lifetime_seconds)
                    except ValueError:
                        normalized_name = None
                        expires_at = instant
                    requested = frozenset(scopes)
                    if (
                        normalized_name is None
                        or len(requested) != len(scopes)
                        or not requested
                        or not requested <= M2_ISSUABLE_SCOPES
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("token_policy_violation")
                    if not may_issue_scopes(authority.scopes, requested):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("scope_escalation_denied")
                    canonical_scopes = tuple(sorted(requested))
                    fingerprint = _request_fingerprint(
                        normalized_name,
                        canonical_scopes,
                        lifetime_seconds if lifetime_seconds is not None else 7_776_000,
                    )
                    issuer_context = _issuer_context(authority)
                    receipt = _receipt(
                        connection,
                        issuer_context,
                        "create_api_token",
                        key_digest,
                        instant,
                        correlation_id,
                        authority,
                    )
                    if receipt is not None:
                        if not hmac.compare_digest(receipt[0], fingerprint):
                            connection.rollback()
                            return ApiTokenMutationOutcomeV1("idempotency_key_reused")
                        resource = _token_row(connection, receipt[1])
                        if (
                            resource is None
                            or resource["administrator_id"]
                            != authority.administrator_id
                        ):
                            raise IdentityAccessRepositoryErrorV1() from None
                        resource_scopes = frozenset(
                            _scope_tuple(connection, receipt[1])
                        )
                        if authority.method == "api_bearer" and not may_manage_token(
                            authority.scopes, resource_scopes
                        ):
                            connection.rollback()
                            return ApiTokenMutationOutcomeV1("scope_escalation_denied")
                        summary, expired = _replay_summary(
                            connection, resource, instant, correlation_id
                        )
                        if expired:
                            connection.commit()
                        else:
                            connection.rollback()
                        return ApiTokenMutationOutcomeV1(
                            "one_time_secret_not_replayable",
                            summary.api_token_id,
                            summary.record_version,
                            summary.state,
                        )
                    if (
                        authority.method == "api_bearer"
                        and expires_at > authority.expires_at
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("scope_escalation_denied")
                    count = connection.exec_driver_sql(
                        "SELECT count(*) FROM iam_api_token WHERE administrator_id=? "
                        "AND revoked_at IS NULL AND expires_at>?",
                        (authority.administrator_id, _text(instant)),
                    ).scalar_one()
                    if type(count) is not int or count < 0:
                        raise IdentityAccessRepositoryErrorV1() from None
                    if count >= _ACTIVE_TOKEN_CAP:
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("active_token_limit_reached")
                    issue = _issue_token(
                        connection,
                        authority.administrator_id,
                        normalized_name,
                        canonical_scopes,
                        expires_at,
                        instant,
                        code="created",
                    )
                    _save_receipt(
                        connection,
                        issuer_context,
                        "create_api_token",
                        key_digest,
                        fingerprint,
                        issue.token.api_token_id.value,
                        instant,
                    )
                    _audit(
                        connection,
                        event_type="api_token_created",
                        outcome_code="created",
                        instant=instant,
                        correlation_id=correlation_id,
                        actor_id=authority.administrator_id,
                        authentication_method=authority.method,
                        target_type="api_token",
                        target_id=issue.token.api_token_id.value,
                    )
                    connection.commit()
                    return issue
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def rotate_token(
        self,
        caller: TokenCallerProofV1,
        target_id: str,
        target_version: int,
        name: str | None,
        scopes: tuple[str, ...] | None,
        lifetime_seconds: int | None,
        idempotency_key: str,
        correlation_id: str,
        instant: datetime,
        *,
        presented_target_id: str | None = None,
    ) -> ApiTokenCredentialIssueV1 | ApiTokenMutationOutcomeV1:
        _validate_correlation(correlation_id)
        key_digest = _receipt_digest(idempotency_key)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    authority, denial = _authorize_caller(
                        connection,
                        caller,
                        instant,
                        correlation_id,
                        required_permission="write:tokens",
                        mutation=True,
                    )
                    if denial is not None:
                        connection.commit()
                        return ApiTokenMutationOutcomeV1(denial)  # type: ignore[arg-type]
                    assert authority is not None
                    target = (
                        _token_row(connection, target_id)
                        if _SAFE_ID.fullmatch(target_id)
                        else None
                    )
                    if (
                        target is None
                        or target["administrator_id"] != authority.administrator_id
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("api_token_not_found")
                    target_scopes = frozenset(_scope_tuple(connection, target_id))
                    if authority.method == "api_bearer" and not may_manage_token(
                        authority.scopes, target_scopes
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("scope_escalation_denied")
                    chosen_name = canonical_token_name(
                        target["name"] if name is None else name
                    )
                    requested = target_scopes if scopes is None else frozenset(scopes)
                    if (
                        chosen_name is None
                        or not requested
                        or not requested <= M2_ISSUABLE_SCOPES
                        or (scopes is not None and len(requested) != len(scopes))
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("token_policy_violation")
                    try:
                        expires_at = token_deadline(instant, lifetime_seconds)
                    except ValueError:
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("token_policy_violation")
                    if not may_issue_scopes(authority.scopes, requested):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("scope_escalation_denied")
                    canonical_scopes = tuple(sorted(requested))
                    fingerprint = _request_fingerprint(
                        target_id,
                        target_version,
                        chosen_name,
                        canonical_scopes,
                        lifetime_seconds if lifetime_seconds is not None else 7_776_000,
                    )
                    issuer_context = _issuer_context(authority)
                    receipt = _receipt(
                        connection,
                        issuer_context,
                        "rotate_api_token",
                        key_digest,
                        instant,
                        correlation_id,
                        authority,
                    )
                    if receipt is not None:
                        if not hmac.compare_digest(receipt[0], fingerprint):
                            connection.rollback()
                            return ApiTokenMutationOutcomeV1("idempotency_key_reused")
                        resource = _token_row(connection, receipt[1])
                        if (
                            resource is None
                            or resource["administrator_id"]
                            != authority.administrator_id
                        ):
                            raise IdentityAccessRepositoryErrorV1() from None
                        if authority.method == "api_bearer" and not may_manage_token(
                            authority.scopes,
                            frozenset(_scope_tuple(connection, receipt[1])),
                        ):
                            connection.rollback()
                            return ApiTokenMutationOutcomeV1("scope_escalation_denied")
                        summary, expired = _replay_summary(
                            connection, resource, instant, correlation_id
                        )
                        if expired:
                            connection.commit()
                        else:
                            connection.rollback()
                        return ApiTokenMutationOutcomeV1(
                            "one_time_secret_not_replayable",
                            summary.api_token_id,
                            summary.record_version,
                            summary.state,
                        )
                    if presented_target_id is not None and (
                        type(presented_target_id) is not str
                        or _SAFE_ID.fullmatch(presented_target_id) is None
                        or presented_target_id != target_id
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("precondition_failed")
                    if _expire_token(connection, target, instant, correlation_id):
                        connection.commit()
                        return ApiTokenMutationOutcomeV1("credential_state_conflict")
                    if (
                        authority.method == "api_bearer"
                        and expires_at > authority.expires_at
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("scope_escalation_denied")
                    if target["revoked_at"] is not None:
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("credential_state_conflict")
                    if (
                        type(target_version) is not int
                        or target["record_version"] != target_version
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("precondition_failed")
                    count = connection.exec_driver_sql(
                        "SELECT count(*) FROM iam_api_token WHERE administrator_id=? "
                        "AND revoked_at IS NULL AND expires_at>?",
                        (authority.administrator_id, _text(instant)),
                    ).scalar_one()
                    if type(count) is not int or count < 1 or count > _ACTIVE_TOKEN_CAP:
                        raise IdentityAccessRepositoryErrorV1() from None
                    issue = _issue_token(
                        connection,
                        authority.administrator_id,
                        chosen_name,
                        canonical_scopes,
                        expires_at,
                        instant,
                        code="rotated",
                        predecessor_id=target_id,
                    )
                    connection.exec_driver_sql(
                        "UPDATE iam_api_token SET revoked_at=?, "
                        "revocation_reason='rotation', verification_digest=NULL, "
                        "replacement_token_id=?, record_version=record_version+1 "
                        "WHERE api_token_id=? AND record_version=? "
                        "AND revoked_at IS NULL",
                        (
                            _text(instant),
                            issue.token.api_token_id.value,
                            target_id,
                            target_version,
                        ),
                    )
                    _save_receipt(
                        connection,
                        issuer_context,
                        "rotate_api_token",
                        key_digest,
                        fingerprint,
                        issue.token.api_token_id.value,
                        instant,
                    )
                    _audit(
                        connection,
                        event_type="api_token_rotated",
                        outcome_code="rotated",
                        instant=instant,
                        correlation_id=correlation_id,
                        actor_id=authority.administrator_id,
                        authentication_method=authority.method,
                        target_type="api_token",
                        target_id=target_id,
                    )
                    connection.commit()
                    return issue
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def revoke_token(
        self,
        caller: TokenCallerProofV1,
        target_id: str,
        target_version: int,
        correlation_id: str,
        instant: datetime,
    ) -> ApiTokenMutationOutcomeV1:
        _validate_correlation(correlation_id)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    authority, denial = _authorize_caller(
                        connection,
                        caller,
                        instant,
                        correlation_id,
                        required_permission="write:tokens",
                        mutation=True,
                    )
                    if denial is not None:
                        connection.commit()
                        return ApiTokenMutationOutcomeV1(denial)  # type: ignore[arg-type]
                    assert authority is not None
                    target = (
                        _token_row(connection, target_id)
                        if _SAFE_ID.fullmatch(target_id)
                        else None
                    )
                    if (
                        target is None
                        or target["administrator_id"] != authority.administrator_id
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("api_token_not_found")
                    if authority.method == "api_bearer" and not may_manage_token(
                        authority.scopes, frozenset(_scope_tuple(connection, target_id))
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("scope_escalation_denied")
                    if (
                        target["revocation_reason"] == "administrator"
                        and target["revoked_at"] is not None
                    ):
                        summary = _token_summary(connection, target, instant)
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1(
                            "revoked",
                            summary.api_token_id,
                            summary.record_version,
                            summary.state,
                        )
                    if _expire_token(connection, target, instant, correlation_id):
                        connection.commit()
                        return ApiTokenMutationOutcomeV1("credential_state_conflict")
                    if target["revoked_at"] is not None:
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("credential_state_conflict")
                    if (
                        type(target_version) is not int
                        or target["record_version"] != target_version
                    ):
                        connection.rollback()
                        return ApiTokenMutationOutcomeV1("precondition_failed")
                    connection.exec_driver_sql(
                        "UPDATE iam_api_token SET revoked_at=?, "
                        "revocation_reason='administrator', verification_digest=NULL, "
                        "record_version=record_version+1 WHERE api_token_id=? "
                        "AND record_version=? AND revoked_at IS NULL",
                        (_text(instant), target_id, target_version),
                    )
                    updated = _token_row(connection, target_id)
                    assert updated is not None
                    summary = _token_summary(connection, updated, instant)
                    _audit(
                        connection,
                        event_type="api_token_revoked",
                        outcome_code="revoked",
                        instant=instant,
                        correlation_id=correlation_id,
                        actor_id=authority.administrator_id,
                        authentication_method=authority.method,
                        target_type="api_token",
                        target_id=target_id,
                    )
                    connection.commit()
                    return ApiTokenMutationOutcomeV1(
                        "revoked",
                        summary.api_token_id,
                        summary.record_version,
                        summary.state,
                    )
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None

    def list_security_events(
        self,
        caller: TokenCallerProofV1,
        limit: int,
        cursor: str | None,
        event_type: str | None,
        outcome: str | None,
        occurred_from: datetime | None,
        occurred_before: datetime | None,
        correlation_id: str,
        instant: datetime,
    ) -> tuple[IamSecurityEventViewV1, ...]:
        _validate_correlation(correlation_id)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    authority, denial = _authorize_caller(
                        connection,
                        caller,
                        instant,
                        correlation_id,
                        required_permission="read:diagnostics",
                        mutation=False,
                    )
                    if denial is not None:
                        connection.commit()
                        raise TokenQueryErrorV1(denial)
                    assert authority is not None
                    if type(limit) is not int or not 1 <= limit <= 200:
                        raise TokenQueryErrorV1("audit_limit_invalid")
                    if cursor is not None and _SAFE_ID.fullmatch(cursor) is None:
                        raise TokenQueryErrorV1("audit_cursor_invalid")
                    if (
                        event_type is not None
                        and _SAFE_CODE.fullmatch(event_type) is None
                    ):
                        raise TokenQueryErrorV1("audit_filter_invalid")
                    if outcome is not None and _SAFE_CODE.fullmatch(outcome) is None:
                        raise TokenQueryErrorV1("audit_filter_invalid")
                    for boundary in (occurred_from, occurred_before):
                        if boundary is not None and (
                            not isinstance(boundary, datetime)
                            or boundary.utcoffset() != timedelta(0)
                        ):
                            raise TokenQueryErrorV1("audit_filter_invalid")
                    if (
                        occurred_from is not None
                        and occurred_before is not None
                        and occurred_from >= occurred_before
                    ):
                        raise TokenQueryErrorV1("audit_filter_invalid")
                    sql = "SELECT * FROM iam_security_audit_event WHERE 1=1"
                    params: tuple[object, ...] = ()
                    if event_type is not None:
                        sql += " AND event_type=?"
                        params += (event_type,)
                    if outcome is not None:
                        sql += " AND outcome_code=?"
                        params += (outcome,)
                    if occurred_from is not None:
                        sql += " AND occurred_at>=?"
                        params += (_text(occurred_from),)
                    if occurred_before is not None:
                        sql += " AND occurred_at<?"
                        params += (_text(occurred_before),)
                    if cursor is not None:
                        cursor_row = connection.exec_driver_sql(
                            "SELECT occurred_at FROM iam_security_audit_event "
                            "WHERE event_id=?",
                            (cursor,),
                        ).one_or_none()
                        if cursor_row is None:
                            raise TokenQueryErrorV1("audit_cursor_invalid")
                        cursor_time = _time(cursor_row[0])
                        sql += " AND (occurred_at<? OR (occurred_at=? AND event_id<?))"
                        params += (_text(cursor_time), _text(cursor_time), cursor)
                    sql += " ORDER BY occurred_at DESC, event_id DESC LIMIT ?"
                    rows = (
                        connection.exec_driver_sql(sql, params + (limit,))
                        .mappings()
                        .all()
                    )
                    try:
                        events = tuple(
                            IamSecurityEventViewV1(
                                OpaqueIdV1(row["event_id"]),
                                row["event_type"],
                                _time(row["occurred_at"]),
                                _time(row["recorded_at"]),
                                (
                                    OpaqueIdV1(row["actor_principal_id"])
                                    if row["actor_principal_id"] is not None
                                    else None
                                ),
                                row["authentication_method"],
                                row["target_type"],
                                (
                                    OpaqueIdV1(row["target_id"])
                                    if row["target_id"] is not None
                                    else None
                                ),
                                row["outcome_code"],
                                row["reason_code"],
                                OpaqueIdV1(row["correlation_id"]),
                                row["schema_version"],
                                row["aggregate_count"],
                            )
                            for row in rows
                        )
                    except (TypeError, ValueError):
                        raise IdentityAccessRepositoryErrorV1() from None
                    connection.commit()
                    return events
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None
