"""Published M01 bearer/token ports; SQLite owns proof revalidation and writes."""

from datetime import UTC, datetime
from typing import Protocol

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    ApiTokenCredentialIssueV1,
    ApiTokenMutationOutcomeV1,
    ApiTokenSummaryV1,
    BearerTokenResolutionV1,
    IamSecurityEventViewV1,
    SecretInputV1,
    TokenCallerProofV1,
)


class TokenQueryErrorV1(RuntimeError):
    """Safe query denial; never includes a submitted credential or DB value."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class IdentityAccessApiTokenRepositoryPortV1(Protocol):
    def resolve_bearer(
        self, credential: str, correlation_id: str, instant: datetime
    ) -> BearerTokenResolutionV1: ...

    def list_tokens(
        self,
        caller: TokenCallerProofV1,
        limit: int,
        cursor: str | None,
        correlation_id: str,
        instant: datetime,
    ) -> tuple[ApiTokenSummaryV1, ...]: ...

    def create_token(
        self,
        caller: TokenCallerProofV1,
        name: str,
        scopes: tuple[str, ...],
        lifetime_seconds: int | None,
        idempotency_key: str,
        correlation_id: str,
        instant: datetime,
    ) -> ApiTokenCredentialIssueV1 | ApiTokenMutationOutcomeV1: ...

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
    ) -> ApiTokenCredentialIssueV1 | ApiTokenMutationOutcomeV1: ...

    def revoke_token(
        self,
        caller: TokenCallerProofV1,
        target_id: str,
        target_version: int,
        correlation_id: str,
        instant: datetime,
    ) -> ApiTokenMutationOutcomeV1: ...

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
    ) -> tuple[IamSecurityEventViewV1, ...]: ...


class ResolveBearerTokenV1:
    def __init__(self, repository: IdentityAccessApiTokenRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, credential: SecretInputV1, *, correlation_id: str
    ) -> BearerTokenResolutionV1:
        return self._repository.resolve_bearer(
            credential.reveal_for_verification(), correlation_id, datetime.now(UTC)
        )


class ListApiTokensV1:
    def __init__(self, repository: IdentityAccessApiTokenRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        caller: TokenCallerProofV1,
        *,
        limit: int = 50,
        cursor: str | None = None,
        correlation_id: str,
    ) -> tuple[ApiTokenSummaryV1, ...]:
        return self._repository.list_tokens(
            caller, limit, cursor, correlation_id, datetime.now(UTC)
        )


class CreateApiTokenV1:
    def __init__(self, repository: IdentityAccessApiTokenRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        caller: TokenCallerProofV1,
        *,
        name: str,
        scopes: tuple[str, ...],
        lifetime_seconds: int | None,
        idempotency_key: str,
        correlation_id: str,
    ) -> ApiTokenCredentialIssueV1 | ApiTokenMutationOutcomeV1:
        return self._repository.create_token(
            caller,
            name,
            scopes,
            lifetime_seconds,
            idempotency_key,
            correlation_id,
            datetime.now(UTC),
        )


class RotateApiTokenV1:
    def __init__(self, repository: IdentityAccessApiTokenRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        caller: TokenCallerProofV1,
        target_id: OpaqueIdV1,
        target_version: int,
        *,
        name: str | None = None,
        scopes: tuple[str, ...] | None = None,
        lifetime_seconds: int | None = None,
        idempotency_key: str,
        correlation_id: str,
        presented_target_id: OpaqueIdV1 | None = None,
    ) -> ApiTokenCredentialIssueV1 | ApiTokenMutationOutcomeV1:
        return self._repository.rotate_token(
            caller,
            target_id.value,
            target_version,
            name,
            scopes,
            lifetime_seconds,
            idempotency_key,
            correlation_id,
            datetime.now(UTC),
            presented_target_id=(
                presented_target_id.value if presented_target_id is not None else None
            ),
        )


class RevokeApiTokenV1:
    def __init__(self, repository: IdentityAccessApiTokenRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        caller: TokenCallerProofV1,
        target_id: OpaqueIdV1,
        target_version: int,
        *,
        correlation_id: str,
    ) -> ApiTokenMutationOutcomeV1:
        return self._repository.revoke_token(
            caller,
            target_id.value,
            target_version,
            correlation_id,
            datetime.now(UTC),
        )


class ListIamSecurityEventsV1:
    def __init__(self, repository: IdentityAccessApiTokenRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self,
        caller: TokenCallerProofV1,
        *,
        limit: int = 50,
        cursor: str | None = None,
        event_type: str | None = None,
        outcome: str | None = None,
        occurred_from: datetime | None = None,
        occurred_before: datetime | None = None,
        correlation_id: str,
    ) -> tuple[IamSecurityEventViewV1, ...]:
        return self._repository.list_security_events(
            caller,
            limit,
            cursor,
            event_type,
            outcome,
            occurred_from,
            occurred_before,
            correlation_id,
            datetime.now(UTC),
        )
