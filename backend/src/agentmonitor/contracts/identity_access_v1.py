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


class TokenCallerProofV1:
    """Transient M01 caller proof, reverified in each token DB transaction."""

    CONTRACT_ID: ClassVar[str] = "CTR-IAM-006"
    OWNER: ClassVar[str] = "PLAN-M01"
    __slots__ = ("method", "credential", "csrf_cookie", "csrf_header")

    def __init__(
        self,
        method: AuthenticationMethodV1,
        credential: SecretInputV1,
        csrf_cookie: SecretInputV1 | None = None,
        csrf_header: SecretInputV1 | None = None,
    ) -> None:
        if method not in ("browser_session", "api_bearer") or not isinstance(
            credential, SecretInputV1
        ):
            raise ValueError("token_caller_proof_invalid")
        if method == "api_bearer" and (
            csrf_cookie is not None or csrf_header is not None
        ):
            raise ValueError("token_caller_proof_ambiguous")
        self.method = method
        self.credential = credential
        self.csrf_cookie = csrf_cookie
        self.csrf_header = csrf_header

    def __repr__(self) -> str:
        return "<TokenCallerProofV1 redacted>"

    def __str__(self) -> str:
        return "<TokenCallerProofV1 redacted>"

    def __getstate__(self) -> NoReturn:
        raise TypeError("token_caller_proof_not_serializable")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("token_caller_proof_not_serializable")


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


class SessionCredentialIssueV1:
    """One-time browser credentials; deliberately not a TechnicalValueV1."""

    CONTRACT_ID: ClassVar[str] = "CTR-IAM-007"
    OWNER: ClassVar[str] = "PLAN-M01"
    __slots__ = ("session", "principal", "_session_credential", "_csrf_credential")
    code: Literal["authenticated"] = "authenticated"

    def __init__(
        self,
        session: SessionSummaryV1,
        principal: PrincipalV1,
        session_credential: str,
        csrf_credential: str,
    ) -> None:
        self.session = session
        self.principal = principal
        self._session_credential = session_credential
        self._csrf_credential = csrf_credential

    @property
    def session_credential(self) -> str:
        return self._session_credential

    @property
    def csrf_credential(self) -> str:
        return self._csrf_credential

    def __repr__(self) -> str:
        return "<SessionCredentialIssueV1 redacted>"

    def __str__(self) -> str:
        return "<SessionCredentialIssueV1 redacted>"

    def __getstate__(self) -> NoReturn:
        raise TypeError("session_issue_not_serializable")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("session_issue_not_serializable")


@dataclass(frozen=True, slots=True)
class AuthenticationFailureV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-004"
    OWNER: ClassVar[str] = "PLAN-M01"
    code: Literal[
        "invalid_credentials",
        "login_throttled",
        "iam_setup_required",
        "iam_repository_unavailable",
    ]
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            self.code == "login_throttled"
            and (
                type(self.retry_after_seconds) is not int
                or not 1 <= self.retry_after_seconds <= 900
            )
        ) or (self.code != "login_throttled" and self.retry_after_seconds is not None):
            raise ValueError("authentication_retry_pair_invalid")


@dataclass(frozen=True, slots=True)
class BrowserSessionResolutionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-003"
    OWNER: ClassVar[str] = "PLAN-M01"
    code: Literal["authenticated", "dashboard_authentication_required"]
    principal: PrincipalV1 | None
    session: SessionSummaryV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.code == "authenticated":
            valid = (
                self.principal is not None
                and self.session is not None
                and self.principal.authentication_method == "browser_session"
                and self.principal.credential_id == self.session.session_id
            )
        else:
            valid = self.principal is None and self.session is None
        if not valid:
            raise ValueError("session_resolution_pair_invalid")


@dataclass(frozen=True, slots=True)
class CsrfDecisionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-003"
    OWNER: ClassVar[str] = "PLAN-M01"
    code: Literal["valid", "csrf_validation_failed"]


@dataclass(frozen=True, slots=True)
class SessionMutationOutcomeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-005"
    OWNER: ClassVar[str] = "PLAN-M01"
    code: Literal[
        "revoked",
        "dashboard_authentication_required",
        "csrf_validation_failed",
        "credential_state_conflict",
        "precondition_failed",
        "session_not_found",
        "one_time_secret_not_replayable",
        "idempotency_key_reused",
        "invalid_credentials",
        "login_throttled",
        "password_policy_violation",
    ]
    affected_count: int = 0
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.affected_count) is not int
            or self.affected_count < 0
            or (self.code != "revoked" and self.affected_count != 0)
        ):
            raise ValueError("session_mutation_count_invalid")
        if (
            self.code == "login_throttled"
            and (
                type(self.retry_after_seconds) is not int
                or not 1 <= self.retry_after_seconds <= 900
            )
        ) or (self.code != "login_throttled" and self.retry_after_seconds is not None):
            raise ValueError("session_mutation_retry_invalid")


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

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        try:
            name_size = len(self.name.encode("utf-8"))
        except (AttributeError, UnicodeEncodeError):
            raise ValueError("token_summary_invalid") from None
        if (
            type(self.name) is not str
            or self.name.strip() != self.name
            or not 1 <= len(self.name) <= 80
            or name_size > 256
            or not self.name.isprintable()
            or type(self.safe_prefix) is not str
            or len(self.safe_prefix) != 8
            or not self.safe_prefix.isascii()
            or not all(char.isalnum() or char in "_-" for char in self.safe_prefix)
            or type(self.scopes) is not tuple
            or not self.scopes
            or self.scopes != tuple(sorted(set(self.scopes)))
            or not set(self.scopes) <= {"read:diagnostics", "write:tokens"}
            or type(self.record_version) is not int
            or self.record_version < 1
            or not isinstance(self.issued_at, datetime)
            or not isinstance(self.expires_at, datetime)
            or not 3600
            <= (self.expires_at - self.issued_at).total_seconds()
            <= 31_536_000
        ):
            raise ValueError("token_summary_invalid")
        if self.revoked_at is None:
            if self.revocation_reason is not None or self.state in {
                "revoked",
                "rotated",
            }:
                raise ValueError("token_summary_invalid")
        elif (
            (self.revocation_reason == "expired" and self.state != "expired")
            or (self.revocation_reason == "rotation" and self.state != "rotated")
            or (
                self.revocation_reason in {"administrator", "local_recovery"}
                and self.state != "revoked"
            )
            or self.revocation_reason
            not in {"expired", "rotation", "administrator", "local_recovery"}
        ):
            raise ValueError("token_summary_invalid")


class ApiTokenCredentialIssueV1:
    """One-time bearer secret; never a serializable technical value."""

    CONTRACT_ID: ClassVar[str] = "CTR-IAM-007"
    OWNER: ClassVar[str] = "PLAN-M01"
    __slots__ = ("code", "token", "_bearer_credential")

    def __init__(
        self,
        code: Literal["created", "rotated"],
        token: ApiTokenSummaryV1,
        bearer_credential: str,
    ) -> None:
        if token.state != "active":
            raise ValueError("token_issue_state_invalid")
        self.code = code
        self.token = token
        self._bearer_credential = bearer_credential

    @property
    def bearer_credential(self) -> str:
        return self._bearer_credential

    def __repr__(self) -> str:
        return "<ApiTokenCredentialIssueV1 redacted>"

    def __str__(self) -> str:
        return "<ApiTokenCredentialIssueV1 redacted>"

    def __getstate__(self) -> NoReturn:
        raise TypeError("token_issue_not_serializable")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("token_issue_not_serializable")


@dataclass(frozen=True, slots=True)
class BearerTokenResolutionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-006"
    OWNER: ClassVar[str] = "PLAN-M01"
    code: Literal["authenticated", "dashboard_authentication_required"]
    principal: PrincipalV1 | None
    token: ApiTokenSummaryV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.code == "authenticated":
            valid = (
                self.principal is not None
                and self.token is not None
                and self.principal.authentication_method == "api_bearer"
                and self.principal.credential_id == self.token.api_token_id
                and self.principal.effective_permissions == self.token.scopes
                and self.principal.expires_at == self.token.expires_at
                and self.token.state == "active"
            )
        else:
            valid = self.principal is None and self.token is None
        if not valid:
            raise ValueError("bearer_resolution_pair_invalid")


@dataclass(frozen=True, slots=True)
class ApiTokenMutationOutcomeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-IAM-006"
    OWNER: ClassVar[str] = "PLAN-M01"
    code: Literal[
        "revoked",
        "dashboard_authentication_required",
        "csrf_validation_failed",
        "permission_denied",
        "scope_escalation_denied",
        "token_policy_violation",
        "api_token_not_found",
        "credential_state_conflict",
        "precondition_failed",
        "one_time_secret_not_replayable",
        "idempotency_key_reused",
        "active_token_limit_reached",
    ]
    api_token_id: OpaqueIdV1 | None = None
    record_version: int | None = None
    state: Literal["active", "expired", "revoked", "rotated"] | None = None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        has_all = (
            self.api_token_id is not None
            and type(self.record_version) is int
            and self.record_version > 0
            and self.state is not None
        )
        has_none = (
            self.api_token_id is None
            and self.record_version is None
            and self.state is None
        )
        if not (
            (self.code in {"revoked", "one_time_secret_not_replayable"} and has_all)
            or (
                self.code not in {"revoked", "one_time_secret_not_replayable"}
                and has_none
            )
        ):
            raise ValueError("token_mutation_metadata_pair_invalid")


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
        # Each event has one reviewed safe shape. No open text/payload field is
        # accepted through this public audit projection.
        current_events: dict[str, tuple[str, str, bool, bool, bool]] = {
            # outcome, target type, actor present, target present, count present
            "administrator_initialized": (
                "created",
                "administrator",
                False,
                True,
                False,
            ),
            "administrator_recovered": (
                "recovered",
                "administrator",
                False,
                True,
                True,
            ),
            "login_succeeded": ("authenticated", "session", True, True, False),
            "login_throttle_activated": (
                "login_throttled",
                "installation",
                False,
                False,
                True,
            ),
            "browser_session_revoked": ("revoked", "session", True, True, False),
            "browser_session_expired": ("expired", "session", False, True, False),
            "other_browser_sessions_revoked": (
                "revoked",
                "administrator",
                True,
                True,
                True,
            ),
            "administrator_password_changed": (
                "changed",
                "administrator",
                True,
                True,
                False,
            ),
            "idempotency_receipt_reclaimed": (
                "reclaimed",
                "administrator",
                True,
                True,
                True,
            ),
            "api_token_created": ("created", "api_token", True, True, False),
            "api_token_rotated": ("rotated", "api_token", True, True, False),
            "api_token_revoked": ("revoked", "api_token", True, True, False),
            "api_token_expired": ("expired", "api_token", False, True, False),
        }
        expected = current_events.get(self.event_type)
        bearer_actor_events = {
            "api_token_created",
            "api_token_rotated",
            "api_token_revoked",
            "idempotency_receipt_reclaimed",
        }
        if (
            expected is None
            or self.outcome_code != expected[0]
            or self.target_type != expected[1]
            or (self.actor_principal_id is not None) != expected[2]
            or (self.target_id is not None) != expected[3]
            or (self.aggregate_count is not None) != expected[4]
            or self.reason_code is not None
            or (
                self.authentication_method
                not in (
                    ("browser_session", "api_bearer")
                    if self.event_type in bearer_actor_events
                    else ("browser_session",)
                )
                if expected[2]
                else self.authentication_method is not None
            )
            or (
                self.event_type
                in {
                    "other_browser_sessions_revoked",
                    "administrator_password_changed",
                    "idempotency_receipt_reclaimed",
                }
                and self.actor_principal_id != self.target_id
            )
        ):
            raise ValueError("iam_audit_code_invalid")
        if (
            self.schema_version != 1
            or (
                self.aggregate_count is not None
                and (type(self.aggregate_count) is not int or self.aggregate_count < 0)
            )
            or (
                self.event_type == "login_throttle_activated"
                and (self.aggregate_count is None or self.aggregate_count < 5)
            )
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
