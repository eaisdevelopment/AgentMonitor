"""M01 V1 safe published values and deliberately non-serializable secret input."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, NoReturn, SupportsIndex

from agentmonitor.contracts.common_v1 import OpaqueIdV1, TechnicalValueV1

AuthenticationMethodV1 = Literal["browser_session", "api_bearer"]
InitializationStatusV1 = Literal["uninitialized", "initialized", "incompatible"]


class SecretInputV1:
    """Transient credential input; never place it in a technical value or log."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("secret_input_invalid")
        self._value = value

    def __repr__(self) -> str:
        return "<SecretInputV1 redacted>"

    def __str__(self) -> str:
        return "<SecretInputV1 redacted>"

    def __getstate__(self) -> NoReturn:
        raise TypeError("secret_input_not_serializable")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("secret_input_not_serializable")

    def reveal_for_verification(self) -> str:
        """Only the M01 application/approved adapter may consume this value."""
        return self._value


@dataclass(frozen=True, slots=True)
class PrincipalV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-001"
    OWNER: ClassVar[str] = "PLAN-M01"
    principal_id: OpaqueIdV1
    authentication_method: AuthenticationMethodV1
    credential_id: OpaqueIdV1 | None
    effective_permissions: tuple[str, ...]
    issued_at: datetime
    authenticated_at: datetime
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class PermissionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-001"
    OWNER: ClassVar[str] = "PLAN-M01"
    key: str
    description: str


@dataclass(frozen=True, slots=True)
class AuthorizationDecisionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-002"
    OWNER: ClassVar[str] = "PLAN-M01"
    allowed: bool
    reason_code: str
    required_permission: str
    principal_id: OpaqueIdV1
    correlation_id: OpaqueIdV1


@dataclass(frozen=True, slots=True)
class IamInitializationStateV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-004"
    OWNER: ClassVar[str] = "PLAN-M01"
    state: InitializationStatusV1
    policy_version: str | None
    schema_revision: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (self.state == "initialized") != (self.policy_version is not None):
            raise ValueError("iam_initialization_policy_pair_invalid")


@dataclass(frozen=True, slots=True)
class BootstrapAdministratorOutcomeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-004"
    OWNER: ClassVar[str] = "PLAN-M01"
    code: Literal[
        "created",
        "password_policy_violation",
        "administrator_already_initialized",
        "iam_repository_unavailable",
    ]
    administrator_id: OpaqueIdV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (self.code == "created") != (self.administrator_id is not None):
            raise ValueError("bootstrap_outcome_id_pair_invalid")


@dataclass(frozen=True, slots=True)
class RecoverAdministratorOutcomeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-004"
    OWNER: ClassVar[str] = "PLAN-M01"
    code: Literal[
        "recovered",
        "password_policy_violation",
        "iam_setup_required",
        "iam_repository_unavailable",
    ]
    administrator_id: OpaqueIdV1 | None
    revoked_session_count: int
    revoked_token_count: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (self.code == "recovered") != (self.administrator_id is not None):
            raise ValueError("recovery_outcome_id_pair_invalid")
        if (
            type(self.revoked_session_count) is not int
            or type(self.revoked_token_count) is not int
            or self.revoked_session_count < 0
            or self.revoked_token_count < 0
            or (
                self.code != "recovered"
                and (self.revoked_session_count != 0 or self.revoked_token_count != 0)
            )
        ):
            raise ValueError("recovery_outcome_count_invalid")


@dataclass(frozen=True, slots=True)
class SessionSummaryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-005"
    OWNER: ClassVar[str] = "PLAN-M01"
    session_id: OpaqueIdV1
    issued_at: datetime
    last_activity_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    state: Literal["active", "expired", "revoked"]
    is_current: bool
    record_version: int


@dataclass(frozen=True, slots=True)
class ApiTokenSummaryV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-007"
    OWNER: ClassVar[str] = "PLAN-M01"
    api_token_id: OpaqueIdV1
    name: str
    safe_prefix: str
    scopes: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    revocation_reason: str | None
    rotated_from_token_id: OpaqueIdV1 | None
    replacement_token_id: OpaqueIdV1 | None
    state: Literal["active", "expired", "revoked", "rotated"]
    record_version: int


@dataclass(frozen=True, slots=True)
class IamSecurityEventViewV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-008"
    OWNER: ClassVar[str] = "PLAN-M01"
    event_id: OpaqueIdV1
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    actor_principal_id: OpaqueIdV1 | None
    authentication_method: AuthenticationMethodV1 | None
    target_type: str | None
    target_id: OpaqueIdV1 | None
    outcome_code: str
    reason_code: str | None
    correlation_id: OpaqueIdV1
    schema_version: int
    aggregate_count: int | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        # This first V1 producer publishes only bootstrap/recovery. Later M01
        # Stories extend this registry deliberately with reviewed safe codes.
        current_events = {
            "administrator_initialized": "created",
            "administrator_recovered": "recovered",
        }
        if (
            current_events.get(self.event_type) != self.outcome_code
            or self.target_type != "administrator"
            or self.target_id is None
            or self.reason_code is not None
            or self.authentication_method is not None
            or self.actor_principal_id is not None
        ):
            raise ValueError("iam_audit_code_invalid")
        if self.schema_version != 1 or (
            self.aggregate_count is not None
            and (type(self.aggregate_count) is not int or self.aggregate_count < 0)
        ):
            raise ValueError("iam_audit_metadata_invalid")


@dataclass(frozen=True, slots=True)
class IamHealthV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-008"
    OWNER: ClassVar[str] = "PLAN-M01"
    repository_reachable: bool
    initialization: InitializationStatusV1
    policy_compatible: bool
    schema_revision: str
    retention_health: Literal["not_run", "healthy", "degraded"]
