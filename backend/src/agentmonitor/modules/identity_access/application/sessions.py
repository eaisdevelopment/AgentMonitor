"""M01 browser authentication ports; adapter owns DB and crypto I/O."""

import re
from datetime import UTC, datetime
from typing import Protocol

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    AuthenticationFailureV1,
    BrowserSessionResolutionV1,
    CsrfDecisionV1,
    PrincipalV1,
    SecretInputV1,
    SessionCredentialIssueV1,
    SessionMutationOutcomeV1,
    SessionSummaryV1,
)


class SessionQueryErrorV1(RuntimeError):
    """Safe M01 query denial with a stable code and no stored-row details."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SessionPasswordHasherPortV1(Protocol):
    POLICY_VERSION: str

    def hash(self, candidate: str) -> str: ...

    def verify(self, encoded: str, candidate: str) -> bool: ...

    def needs_rehash(self, encoded: str) -> bool: ...


class IdentityAccessSessionRepositoryPortV1(Protocol):
    def authenticate(
        self,
        candidate: str,
        hasher: SessionPasswordHasherPortV1,
        correlation_id: str,
        instant: datetime,
    ) -> SessionCredentialIssueV1 | AuthenticationFailureV1: ...

    def resolve(
        self, credential: str, correlation_id: str, instant: datetime
    ) -> BrowserSessionResolutionV1: ...

    def verify_csrf(
        self,
        session_id: str,
        cookie: str | None,
        header: str | None,
        correlation_id: str,
        instant: datetime,
    ) -> CsrfDecisionV1: ...

    def logout(
        self,
        session_id: str,
        version: int,
        cookie: str | None,
        header: str | None,
        correlation_id: str,
        instant: datetime,
    ) -> SessionMutationOutcomeV1: ...

    def list_sessions(
        self,
        administrator_id: str,
        current_session_id: str,
        limit: int,
        cursor: str | None,
        correlation_id: str,
    ) -> tuple[SessionSummaryV1, ...]: ...

    def revoke_session(
        self,
        actor_session_id: str,
        target_session_id: str,
        target_version: int,
        cookie: str | None,
        header: str | None,
        correlation_id: str,
        instant: datetime,
    ) -> SessionMutationOutcomeV1: ...

    def revoke_other_sessions(
        self,
        actor_session_id: str,
        cookie: str | None,
        header: str | None,
        idempotency_key: str,
        correlation_id: str,
        instant: datetime,
    ) -> SessionMutationOutcomeV1: ...

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
    ) -> SessionCredentialIssueV1 | SessionMutationOutcomeV1: ...


class AuthenticateAdministratorV1:
    """Fresh password login. Every success issues new nonserializable credentials."""

    def __init__(
        self,
        repository: IdentityAccessSessionRepositoryPortV1,
        hasher: SessionPasswordHasherPortV1,
    ) -> None:
        self._repository = repository
        self._hasher = hasher

    def __call__(
        self, password: SecretInputV1, *, correlation_id: str
    ) -> SessionCredentialIssueV1 | AuthenticationFailureV1:
        return self._repository.authenticate(
            password.reveal_for_verification(),
            self._hasher,
            correlation_id,
            datetime.now(UTC),
        )


class ResolveBrowserSessionV1:
    def __init__(self, repository: IdentityAccessSessionRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, credential: SecretInputV1, *, correlation_id: str
    ) -> BrowserSessionResolutionV1:
        return self._repository.resolve(
            credential.reveal_for_verification(), correlation_id, datetime.now(UTC)
        )


class VerifyCsrfV1:
    def __init__(self, repository: IdentityAccessSessionRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        session_id: OpaqueIdV1,
        cookie: SecretInputV1 | None,
        header: SecretInputV1 | None,
        *,
        correlation_id: str,
    ) -> CsrfDecisionV1:
        return self._repository.verify_csrf(
            session_id.value,
            cookie.reveal_for_verification() if cookie is not None else None,
            header.reveal_for_verification() if header is not None else None,
            correlation_id,
            datetime.now(UTC),
        )


class LogoutSessionV1:
    def __init__(self, repository: IdentityAccessSessionRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        session_id: OpaqueIdV1,
        version: int,
        cookie: SecretInputV1 | None,
        header: SecretInputV1 | None,
        *,
        correlation_id: str,
    ) -> SessionMutationOutcomeV1:
        return self._repository.logout(
            session_id.value,
            version,
            cookie.reveal_for_verification() if cookie is not None else None,
            header.reveal_for_verification() if header is not None else None,
            correlation_id,
            datetime.now(UTC),
        )


class ListSessionsV1:
    """Browser-only bounded own-session query."""

    def __init__(self, repository: IdentityAccessSessionRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        principal: PrincipalV1,
        *,
        limit: int = 50,
        cursor: str | None = None,
        correlation_id: str,
    ) -> tuple[SessionSummaryV1, ...]:
        if (
            principal.authentication_method != "browser_session"
            or "write:sessions" not in principal.effective_permissions
            or principal.credential_id is None
        ):
            raise PermissionError("permission_denied")
        if not 1 <= limit <= 200:
            raise ValueError("session_list_limit_invalid")
        if (
            cursor is not None
            and re.fullmatch(r"[A-Za-z0-9_-]{1,64}\Z", cursor) is None
        ):
            raise SessionQueryErrorV1("session_cursor_invalid")
        return self._repository.list_sessions(
            principal.principal_id.value,
            principal.credential_id.value,
            limit,
            cursor,
            correlation_id,
        )


class RevokeSessionV1:
    """Target session and current actor proof are rechecked in one transaction."""

    def __init__(self, repository: IdentityAccessSessionRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        actor_session_id: OpaqueIdV1,
        target_session_id: OpaqueIdV1,
        target_version: int,
        cookie: SecretInputV1 | None,
        header: SecretInputV1 | None,
        *,
        correlation_id: str,
    ) -> SessionMutationOutcomeV1:
        return self._repository.revoke_session(
            actor_session_id.value,
            target_session_id.value,
            target_version,
            cookie.reveal_for_verification() if cookie is not None else None,
            header.reveal_for_verification() if header is not None else None,
            correlation_id,
            datetime.now(UTC),
        )


class RevokeAllSessionsV1:
    """Revoke other sessions, preserving the authenticated current binding."""

    def __init__(self, repository: IdentityAccessSessionRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        actor_session_id: OpaqueIdV1,
        cookie: SecretInputV1 | None,
        header: SecretInputV1 | None,
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> SessionMutationOutcomeV1:
        return self._repository.revoke_other_sessions(
            actor_session_id.value,
            cookie.reveal_for_verification() if cookie is not None else None,
            header.reveal_for_verification() if header is not None else None,
            idempotency_key,
            correlation_id,
            datetime.now(UTC),
        )


class ChangeAdministratorPasswordV1:
    """Credential-changing use case; session issue is one-time and non-replayable."""

    def __init__(
        self,
        repository: IdentityAccessSessionRepositoryPortV1,
        hasher: SessionPasswordHasherPortV1,
    ) -> None:
        self._repository = repository
        self._hasher = hasher

    def __call__(
        self,
        actor_session_id: OpaqueIdV1,
        actor_version: int,
        cookie: SecretInputV1 | None,
        header: SecretInputV1 | None,
        current_password: SecretInputV1,
        new_password: SecretInputV1,
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> SessionCredentialIssueV1 | SessionMutationOutcomeV1:
        return self._repository.change_password(
            actor_session_id.value,
            actor_version,
            cookie.reveal_for_verification() if cookie is not None else None,
            header.reveal_for_verification() if header is not None else None,
            current_password.reveal_for_verification(),
            new_password.reveal_for_verification(),
            self._hasher,
            idempotency_key,
            correlation_id,
            datetime.now(UTC),
        )
