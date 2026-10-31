"""P01 V1 IAM wire schemas; no persistence or provider representation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _ClosedV1(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IamInitializationStateV1(_ClosedV1):
    state: str
    policy_version: str | None
    schema_revision: str


class LoginInputV1(_ClosedV1):
    password: str = Field(min_length=1, max_length=1024, repr=False)


class ChangeAdministratorPasswordInputV1(_ClosedV1):
    current_password: str = Field(min_length=1, max_length=1024, repr=False)
    new_password: str = Field(min_length=1, max_length=1024, repr=False)


class CurrentSessionViewV1(_ClosedV1):
    session_id: str
    issued_at: datetime
    last_activity_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    state: str
    is_current: bool
    record_version: int


class PageMetaV1(_ClosedV1):
    limit: int
    next_cursor: str | None
    has_more: bool


class BrowserSessionPageV1(_ClosedV1):
    items: tuple[CurrentSessionViewV1, ...]
    page: PageMetaV1


class SessionRevocationSummaryV1(_ClosedV1):
    affected_count: int


class CreateApiTokenInputV1(_ClosedV1):
    name: str = Field(min_length=1, max_length=80)
    scopes: tuple[str, ...] = Field(min_length=1, max_length=2)
    lifetime_seconds: int | None = Field(default=None, ge=3600, le=31_536_000)


class RotateApiTokenInputV1(_ClosedV1):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    scopes: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=2)
    lifetime_seconds: int | None = Field(default=None, ge=3600, le=31_536_000)


class ApiTokenSummaryV1(_ClosedV1):
    api_token_id: str
    name: str
    safe_prefix: str
    scopes: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    revocation_reason: str | None
    rotated_from_token_id: str | None
    replacement_token_id: str | None
    state: str
    record_version: int


class ApiTokenPageV1(_ClosedV1):
    items: tuple[ApiTokenSummaryV1, ...]
    page: PageMetaV1


class ApiTokenCredentialIssueV1(_ClosedV1):
    token: ApiTokenSummaryV1
    bearer_credential: str = Field(repr=False)


class IamSecurityEventV1(_ClosedV1):
    event_id: str
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    actor_principal_id: str | None
    authentication_method: str | None
    target_type: str | None
    target_id: str | None
    outcome_code: str
    reason_code: str | None
    correlation_id: str
    schema_version: int
    aggregate_count: int | None


class IamSecurityEventPageV1(_ClosedV1):
    items: tuple[IamSecurityEventV1, ...]
    page: PageMetaV1
