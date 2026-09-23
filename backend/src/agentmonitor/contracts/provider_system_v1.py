"""Provider-neutral V1 contracts; provider behavior stays in adapters."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import (
    ClassVar,
    Literal,
    Protocol,
    Self,
    runtime_checkable,
)

from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    TechnicalValueV1,
)

CapabilityDecisionStateV1 = Literal[
    "supported", "experimental", "deferred", "unsupported", "unknown"
]
StabilityV1 = Literal[
    "documented", "supported", "local_undocumented", "experimental", "unknown"
]
SideEffectClassV1 = Literal["read_only", "managed_profile_write", "unknown"]
ProfileProtectionV1 = Literal["protected_default", "managed", "unknown"]
OutcomeStateV1 = Literal[
    "success",
    "partial",
    "unsupported",
    "unverified_provider_version",
    "reauthentication_required",
    "authorization_insufficient",
    "provider_unavailable",
    "rate_limited",
    "invalid_provider_data",
    "deadline_exceeded",
    "blocked_user_action_required",
    "internal_adapter_error",
]
FailureOutcomeStateV1 = Literal[
    "unsupported",
    "unverified_provider_version",
    "reauthentication_required",
    "authorization_insufficient",
    "provider_unavailable",
    "rate_limited",
    "invalid_provider_data",
    "deadline_exceeded",
    "blocked_user_action_required",
    "internal_adapter_error",
]
RetryDispositionV1 = Literal[
    "never",
    "after_delay",
    "after_reauthentication",
    "after_user_action",
    "after_version_review",
    "unknown",
]
IdentityComparisonStateV1 = Literal["matched", "mismatched", "unresolved"]
AuthHealthStateV1 = Literal[
    "healthy",
    "refreshing",
    "expiring",
    "reauthentication_required",
    "revoked_or_disabled",
    "wrong_account_detected",
    "unknown",
]
ReauthStateV1 = Literal[
    "requested",
    "awaiting_owner_action",
    "verifying",
    "succeeded",
    "wrong_account_detected",
    "failed",
    "cancelled",
    "expired",
]
ProviderVersionStateV1 = Literal["available", "unknown", "unavailable"]
ProviderVersionSchemeV1 = Literal["opaque_exact", "semantic_exact", "date_exact"]
CompatibilityStateV1 = Literal[
    "compatible", "incompatible", "unverified", "unsupported", "disabled"
]
OutboxDeliveryStateV1 = Literal["pending", "claimed", "delivered"]

_CAPABILITY_ID = re.compile(r"[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*){1,5}\Z")
_SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class InvalidProviderContract(ValueError):
    """A published provider value violates a V1 invariant."""


class InvalidCollectionOutcome(InvalidProviderContract):
    """A provider operation outcome is impossible, unsafe, or incomplete."""


def _bounded_token(value: object, *, maximum: int = 128) -> bool:
    return (
        type(value) is str
        and value == value.strip()
        and 1 <= len(value) <= maximum
        and value.isprintable()
    )


def _validate_capability_id(value: object) -> None:
    if (
        type(value) is not str
        or len(value) > 128
        or _CAPABILITY_ID.fullmatch(value) is None
    ):
        raise InvalidProviderContract("capability_id_invalid")


def _semver(value: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(value)
    if match is None:
        raise InvalidProviderContract("semantic_version_invalid")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class CapabilitySchemaVersionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    major: int
    minor: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.major) is not int
            or type(self.minor) is not int
            or self.major < 1
            or self.minor < 0
        ):
            raise InvalidProviderContract("capability_schema_version_invalid")


@dataclass(frozen=True, slots=True)
class CapabilitySchemaRangeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    minimum: CapabilitySchemaVersionV1
    maximum: CapabilitySchemaVersionV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.minimum.major != self.maximum.major or (
            self.minimum.major,
            self.minimum.minor,
        ) > (self.maximum.major, self.maximum.minor):
            raise InvalidProviderContract("capability_schema_range_invalid")

    def includes(self, version: CapabilitySchemaVersionV1) -> bool:
        return version.major == self.minimum.major and (
            self.minimum.minor <= version.minor <= self.maximum.minor
        )


@dataclass(frozen=True, slots=True)
class ProtocolVersionRangeV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-001"
    OWNER: ClassVar[str] = "PLAN-M03"

    minimum: str
    maximum: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        minimum = _semver(self.minimum)
        maximum = _semver(self.maximum)
        if minimum[0] != maximum[0] or minimum > maximum:
            raise InvalidProviderContract("protocol_version_range_invalid")

    def includes(self, version: str) -> bool:
        candidate = _semver(version)
        minimum = _semver(self.minimum)
        maximum = _semver(self.maximum)
        return candidate[0] == minimum[0] and minimum <= candidate <= maximum


@dataclass(frozen=True, slots=True)
class ProviderVersionRuleV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    rule_id: str
    scheme: Literal["opaque_exact", "semantic_exact", "date_exact"]
    verified_versions: tuple[str, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded_token(self.rule_id) or not self.verified_versions:
            raise InvalidProviderContract("provider_version_rule_invalid")
        if self.verified_versions != tuple(
            sorted(set(self.verified_versions))
        ) or not all(_bounded_token(value) for value in self.verified_versions):
            raise InvalidProviderContract("provider_version_rule_invalid")
        if self.scheme == "semantic_exact":
            for value in self.verified_versions:
                _semver(value)

    def verifies(self, provider_version: str) -> bool:
        """Exact evidence membership is required for every V1 scheme."""
        return provider_version in self.verified_versions


@dataclass(frozen=True, slots=True)
class CollectionConstraintV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    deadline_ms: int
    minimum_interval_ms: int
    maximum_concurrency: int
    automatic_retry_count: int
    provider_request_count: int | None
    provider_request_count_availability: FieldAvailabilityV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            type(self.deadline_ms) is not int
            or not 1 <= self.deadline_ms <= 300_000
            or type(self.minimum_interval_ms) is not int
            or self.minimum_interval_ms < 0
            or type(self.maximum_concurrency) is not int
            or not 1 <= self.maximum_concurrency <= 64
            or type(self.automatic_retry_count) is not int
            or not 0 <= self.automatic_retry_count <= 10
        ):
            raise InvalidProviderContract("collection_constraint_invalid")
        count_is_available = (
            self.provider_request_count_availability.state == "available"
        )
        if (self.provider_request_count is not None) != count_is_available or (
            self.provider_request_count is not None
            and (
                type(self.provider_request_count) is not int
                or self.provider_request_count < 0
            )
        ):
            raise InvalidProviderContract("provider_request_count_pair_invalid")


@dataclass(frozen=True, slots=True)
class ProviderSourceV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-003"
    OWNER: ClassVar[str] = "PLAN-M03"

    source_id: str
    provider_key: str
    capability_id: str
    source_class: Literal[
        "documented_api",
        "supported_cli",
        "approved_local_metadata",
        "experimental_private_or_browser",
    ]
    stability: StabilityV1
    mechanism_version: str
    credential_role: str
    side_effect_class: SideEffectClassV1
    evidence_reference: str
    is_experimental: bool

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _validate_capability_id(self.capability_id)
        for value in (
            self.source_id,
            self.provider_key,
            self.mechanism_version,
            self.credential_role,
            self.evidence_reference,
        ):
            if not _bounded_token(value):
                raise InvalidProviderContract("provider_source_invalid")
        if type(self.is_experimental) is not bool or self.is_experimental != (
            self.source_class == "experimental_private_or_browser"
        ):
            raise InvalidProviderContract("provider_source_experimental_invalid")


@dataclass(frozen=True, slots=True)
class CapabilityDeclarationV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    capability_id: str
    schema_versions: CapabilitySchemaRangeV1
    decision: CapabilityDecisionStateV1
    stability: StabilityV1
    reason_code: str
    evidence_reference: str
    port_type: str | None
    output_schema: str | None
    sources: tuple[ProviderSourceV1, ...]
    provider_version_rule: ProviderVersionRuleV1
    constraints: CollectionConstraintV1
    side_effect_class: SideEffectClassV1
    platforms: tuple[str, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _validate_capability_id(self.capability_id)
        if not _bounded_token(self.reason_code) or not _bounded_token(
            self.evidence_reference
        ):
            raise InvalidProviderContract("capability_declaration_invalid")
        is_invokable = self.decision in {"supported", "experimental"}
        if is_invokable != bool(self.port_type and self.output_schema and self.sources):
            raise InvalidProviderContract("invokable_declaration_incomplete")
        if self.port_type is not None and not _bounded_token(self.port_type):
            raise InvalidProviderContract("capability_port_type_invalid")
        if self.output_schema is not None and not _bounded_token(self.output_schema):
            raise InvalidProviderContract("capability_output_schema_invalid")
        source_keys = tuple(source.source_id for source in self.sources)
        if len(source_keys) != len(set(source_keys)) or any(
            source.provider_key == "" or source.capability_id != self.capability_id
            for source in self.sources
        ):
            raise InvalidProviderContract("capability_source_invalid")
        if self.decision == "experimental" and not all(
            source.is_experimental for source in self.sources
        ):
            raise InvalidProviderContract("experimental_declaration_invalid")
        if (
            not self.platforms
            or self.platforms != tuple(sorted(set(self.platforms)))
            or not all(_bounded_token(value) for value in self.platforms)
        ):
            raise InvalidProviderContract("capability_platform_invalid")


@dataclass(frozen=True, slots=True)
class AdapterDescriptorV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    adapter_id: str
    adapter_version: str
    provider_key: str
    protocol_versions: ProtocolVersionRangeV1
    build_identity: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        for value in (
            self.adapter_id,
            self.provider_key,
            self.build_identity,
        ):
            if not _bounded_token(value):
                raise InvalidProviderContract("adapter_descriptor_invalid")
        _semver(self.adapter_version)


@dataclass(frozen=True, slots=True)
class CapabilityManifestV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    descriptor: AdapterDescriptorV1
    manifest_schema_version: str
    declarations: tuple[CapabilityDeclarationV1, ...]
    m0_mapping_id: str
    m0_mapping_version: str
    m0_mapping_digest: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _semver(self.manifest_schema_version)
        _semver(self.m0_mapping_version)
        if (
            not _bounded_token(self.m0_mapping_id)
            or _SHA256.fullmatch(self.m0_mapping_digest) is None
        ):
            raise InvalidProviderContract("manifest_mapping_binding_invalid")
        if not self.declarations:
            raise InvalidProviderContract("manifest_declarations_required")
        capability_ids = tuple(item.capability_id for item in self.declarations)
        if len(capability_ids) != len(set(capability_ids)):
            raise InvalidProviderContract("manifest_duplicate_capability")
        if any(
            source.provider_key != self.descriptor.provider_key
            for item in self.declarations
            for source in item.sources
        ):
            raise InvalidProviderContract("manifest_provider_scope_invalid")


@dataclass(frozen=True, slots=True)
class ProviderTargetV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-001"
    OWNER: ClassVar[str] = "PLAN-M03"

    provider_key: str
    installation_ref: OpaqueIdV1
    account_ref: OpaqueIdV1 | None
    profile_ref: OpaqueIdV1 | None
    resource_ref: OpaqueIdV1 | None
    profile_protection: ProfileProtectionV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded_token(self.provider_key):
            raise InvalidProviderContract("provider_target_invalid")


@dataclass(frozen=True, slots=True)
class SourceTransitionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-003"
    OWNER: ClassVar[str] = "PLAN-M03"

    from_source_id: str
    to_source_id: str
    permitted_failure_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _bounded_token(self.from_source_id)
            or not _bounded_token(self.to_source_id)
            or self.from_source_id == self.to_source_id
        ):
            raise InvalidProviderContract("source_transition_invalid")
        if (
            not self.permitted_failure_codes
            or self.permitted_failure_codes
            != tuple(sorted(set(self.permitted_failure_codes)))
            or not all(_bounded_token(code) for code in self.permitted_failure_codes)
        ):
            raise InvalidProviderContract("source_transition_failure_codes_invalid")


@dataclass(frozen=True, slots=True)
class SourcePolicyV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-003"
    OWNER: ClassVar[str] = "PLAN-M03"

    policy_ref: OpaqueIdV1
    source_ids: tuple[str, ...]
    approved_fallbacks: tuple[SourceTransitionV1, ...]
    experimental_grant_ref: OpaqueIdV1 | None

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not self.source_ids
            or len(self.source_ids) != len(set(self.source_ids))
            or not all(_bounded_token(value) for value in self.source_ids)
        ):
            raise InvalidProviderContract("source_policy_invalid")


@dataclass(frozen=True, slots=True)
class ProviderOperationRequestHeaderV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-004"
    OWNER: ClassVar[str] = "PLAN-M03"

    operation_id: OpaqueIdV1
    correlation_id: OpaqueIdV1
    provider_key: str
    capability_id: str
    capability_schema_version: CapabilitySchemaVersionV1
    target: ProviderTargetV1
    requested_at: datetime
    deadline_ms: int
    source_policy: SourcePolicyV1
    access_grant_refs: tuple[OpaqueIdV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _validate_capability_id(self.capability_id)
        if self.provider_key != self.target.provider_key:
            raise InvalidProviderContract("request_target_provider_mismatch")
        if type(self.deadline_ms) is not int or not 1 <= self.deadline_ms <= 300_000:
            raise InvalidProviderContract("request_deadline_invalid")
        if not self.access_grant_refs:
            raise InvalidProviderContract("request_access_grant_required")


@dataclass(frozen=True, slots=True)
class MissingFieldV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-004"
    OWNER: ClassVar[str] = "PLAN-M03"

    code: str
    availability: FieldAvailabilityV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded_token(self.code) or self.availability.state == "available":
            raise InvalidProviderContract("missing_field_invalid")


@dataclass(frozen=True, slots=True)
class SanitizedWarningV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-004"
    OWNER: ClassVar[str] = "PLAN-M03"

    code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded_token(self.code):
            raise InvalidProviderContract("sanitized_warning_invalid")


@dataclass(frozen=True, slots=True)
class RetryAdviceV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-004"
    OWNER: ClassVar[str] = "PLAN-M03"

    disposition: RetryDispositionV1
    delay_seconds: int | None = None
    delay_precision: Literal["exact", "estimated", "unknown"] = "unknown"

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        has_delay = self.disposition == "after_delay"
        if has_delay != (self.delay_seconds is not None) or (
            self.delay_seconds is not None
            and (type(self.delay_seconds) is not int or self.delay_seconds < 1)
        ):
            raise InvalidProviderContract("retry_delay_pair_invalid")
        if not has_delay and self.delay_precision != "unknown":
            raise InvalidProviderContract("retry_precision_invalid")


@dataclass(frozen=True, slots=True)
class SafeProviderErrorV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-004"
    OWNER: ClassVar[str] = "PLAN-M03"

    code: str
    retry: RetryAdviceV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded_token(self.code):
            raise InvalidCollectionOutcome("provider_error_code_invalid")


@dataclass(frozen=True, slots=True)
class CollectionOutcomeV1[ResultT: TechnicalValueV1](TechnicalValueV1):
    """Closed provider operation outcome with typed payload and no raw escape."""

    CONTRACT_ID: ClassVar[str] = "CTR-PROV-004"
    OWNER: ClassVar[str] = "PLAN-M03"

    state: OutcomeStateV1
    value: ResultT | None
    provenance: ObservationProvenanceV1 | None
    omissions: tuple[MissingFieldV1, ...]
    warnings: tuple[SanitizedWarningV1, ...]
    error: SafeProviderErrorV1 | None

    def __post_init__(self) -> None:
        if self.value is not None and not isinstance(self.value, TechnicalValueV1):
            raise InvalidCollectionOutcome("typed_payload_required")
        TechnicalValueV1.__post_init__(self)
        if self.state == "success":
            valid = (
                self.value is not None
                and self.provenance is not None
                and not self.omissions
                and not self.warnings
                and self.error is None
            )
        elif self.state == "partial":
            valid = (
                self.value is not None
                and self.provenance is not None
                and bool(self.omissions)
                and bool(self.warnings)
                and self.error is None
            )
        else:
            valid = (
                self.value is None
                and self.provenance is None
                and not self.omissions
                and not self.warnings
                and self.error is not None
            )
        if not valid:
            code = (
                "partial_outcome_invalid"
                if self.state == "partial"
                else "collection_outcome_variant_invalid"
            )
            raise InvalidCollectionOutcome(code)
        if self.state in {"success", "partial"}:
            assert self.provenance is not None
            missing_local_versions = tuple(
                code
                for code, is_missing in (
                    ("provider_version", self.provenance.provider_version is None),
                    ("parser_version", self.provenance.parser_version is None),
                )
                if is_missing
            )
            if (
                self.provenance.source_class == "approved_local_metadata"
                and missing_local_versions
            ):
                omission_codes = {item.code for item in self.omissions}
                if self.state != "partial" or not set(missing_local_versions) <= (
                    omission_codes
                ):
                    raise InvalidCollectionOutcome("local_provenance_incomplete")
        if self.error is not None:
            allowed_retry = {
                "unsupported": {"never"},
                "unverified_provider_version": {"after_version_review", "never"},
                "reauthentication_required": {"after_reauthentication", "never"},
                "authorization_insufficient": {"after_user_action", "never"},
                "provider_unavailable": {"after_delay", "unknown", "never"},
                "rate_limited": {"after_delay"},
                "invalid_provider_data": {"never", "after_version_review"},
                "deadline_exceeded": {"unknown", "never"},
                "blocked_user_action_required": {"after_user_action"},
                "internal_adapter_error": {"unknown", "never"},
            }
            if self.error.retry.disposition not in allowed_retry[self.state]:
                raise InvalidCollectionOutcome("retry_disposition_invalid")

    @classmethod
    def success(cls, value: ResultT, provenance: ObservationProvenanceV1) -> Self:
        return cls("success", value, provenance, (), (), None)

    @classmethod
    def partial(
        cls,
        value: ResultT,
        *,
        omissions: tuple[MissingFieldV1, ...],
        warnings: tuple[SanitizedWarningV1, ...],
        provenance: ObservationProvenanceV1 | None,
    ) -> Self:
        return cls("partial", value, provenance, omissions, warnings, None)

    @classmethod
    def failure(
        cls,
        *,
        state: FailureOutcomeStateV1,
        code: str,
        retry: RetryAdviceV1,
    ) -> Self:
        return cls(state, None, None, (), (), SafeProviderErrorV1(code, retry))


@dataclass(frozen=True, slots=True)
class IdentityComparisonV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-006"
    OWNER: ClassVar[str] = "PLAN-M03"

    state: IdentityComparisonStateV1
    evidence_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded_token(self.evidence_code):
            raise InvalidProviderContract("identity_comparison_invalid")

    @property
    def may_associate_automatically(self) -> bool:
        return self.state == "matched"


@dataclass(frozen=True, slots=True)
class AuthHealthObservationV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-006"
    OWNER: ClassVar[str] = "PLAN-M03"

    state: AuthHealthStateV1
    provenance: ObservationProvenanceV1
    expires_at: datetime | None
    expiry_precision: Literal["exact", "rounded", "estimated", "unknown"]
    reason_code: str
    identity: IdentityComparisonV1

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded_token(self.reason_code):
            raise InvalidProviderContract("auth_reason_invalid")
        if self.expires_at is not None and self.expiry_precision == "unknown":
            raise InvalidProviderContract("auth_expiry_precision_invalid")
        if self.expires_at is None and self.expiry_precision != "unknown":
            raise InvalidProviderContract("auth_expiry_precision_invalid")
        if (
            self.state == "wrong_account_detected"
            and self.identity.state != "mismatched"
        ):
            raise InvalidProviderContract("auth_identity_state_invalid")


@dataclass(frozen=True, slots=True)
class ReauthFlowV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-007"
    OWNER: ClassVar[str] = "PLAN-M03"

    flow_id: OpaqueIdV1
    state: ReauthStateV1
    target_profile_protection: ProfileProtectionV1
    identity: IdentityComparisonV1
    expires_at: datetime
    owner_action: Literal["none", "open_browser", "enter_device_code"]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if self.target_profile_protection != "managed":
            raise InvalidProviderContract("reauth_profile_not_managed")
        if self.state == "succeeded" and self.identity.state != "matched":
            raise InvalidProviderContract("reauth_identity_state_invalid")
        if (
            self.state == "wrong_account_detected"
            and self.identity.state != "mismatched"
        ):
            raise InvalidProviderContract("reauth_identity_state_invalid")


@dataclass(frozen=True, slots=True)
class DiscoveredInstallationV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-005"
    OWNER: ClassVar[str] = "PLAN-M03"

    provider_key: str
    installation_ref: OpaqueIdV1
    product_version: str | None
    platform_id: str
    provenance: ObservationProvenanceV1


@dataclass(frozen=True, slots=True)
class DiscoveredAccountCandidateV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-005"
    OWNER: ClassVar[str] = "PLAN-M03"

    candidate_ref: OpaqueIdV1
    installation_ref: OpaqueIdV1
    evidence_strength: Literal["strong", "owner_confirmation_required", "unresolved"]
    owner_confirmation_required: bool
    provenance: ObservationProvenanceV1


@dataclass(frozen=True, slots=True)
class DiscoveryCandidatesV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-005"
    OWNER: ClassVar[str] = "PLAN-M03"

    installations: tuple[DiscoveredInstallationV1, ...]
    accounts: tuple[DiscoveredAccountCandidateV1, ...]


class DiscoveryOutcomeV1(CollectionOutcomeV1[DiscoveryCandidatesV1]):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-005"
    OWNER: ClassVar[str] = "PLAN-M03"


class AuthHealthOutcomeV1(CollectionOutcomeV1[AuthHealthObservationV1]):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-006"
    OWNER: ClassVar[str] = "PLAN-M03"


@dataclass(frozen=True, slots=True)
class CompatibilityAssessmentInputV1(TechnicalValueV1):
    """Canonical safe input for one immutable compatibility assessment."""

    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    registration_id: OpaqueIdV1
    provider_key: str
    adapter_id: str
    adapter_version: str
    protocol_version: str
    installation_id: OpaqueIdV1 | None
    capability_id: str
    capability_schema_version: str
    source_id: str | None
    provider_version_value: str | None
    provider_version_state: ProviderVersionStateV1
    version_scheme: ProviderVersionSchemeV1 | None
    version_rule_id: str | None
    compatibility_state: CompatibilityStateV1
    reason_code: str
    manifest_schema_version: str
    manifest_fingerprint: str
    assessed_at: datetime
    valid_until: datetime | None
    correlation_id: OpaqueIdV1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.assessed_at, datetime)
            or self.assessed_at.utcoffset() != timedelta(0)
            or (
                self.valid_until is not None
                and (
                    not isinstance(self.valid_until, datetime)
                    or self.valid_until.utcoffset() != timedelta(0)
                )
            )
        ):
            raise InvalidProviderContract("compatibility_timestamp_invalid")
        TechnicalValueV1.__post_init__(self)
        _validate_capability_id(self.capability_id)
        bounded_values = (
            (self.registration_id.value, 64),
            (self.provider_key, 64),
            (self.adapter_id, 128),
            (self.adapter_version, 32),
            (self.protocol_version, 32),
            (self.capability_schema_version, 32),
            (self.reason_code, 128),
            (self.manifest_schema_version, 32),
            (self.correlation_id.value, 64),
        )
        if any(
            not _bounded_token(value, maximum=maximum)
            for value, maximum in bounded_values
        ):
            raise InvalidProviderContract("compatibility_assessment_invalid")
        if self.installation_id is not None and not _bounded_token(
            self.installation_id.value, maximum=64
        ):
            raise InvalidProviderContract("compatibility_assessment_invalid")
        if self.source_id is not None and not _bounded_token(
            self.source_id, maximum=128
        ):
            raise InvalidProviderContract("compatibility_assessment_invalid")
        if _SHA256.fullmatch(self.manifest_fingerprint) is None:
            raise InvalidProviderContract("compatibility_manifest_fingerprint_invalid")
        available = self.provider_version_state == "available"
        version_values = (
            self.provider_version_value,
            self.version_scheme,
            self.version_rule_id,
        )
        if available != all(value is not None for value in version_values):
            raise InvalidProviderContract("compatibility_version_pair_invalid")
        if not available and any(value is not None for value in version_values):
            raise InvalidProviderContract("compatibility_version_pair_invalid")
        if available and (
            not _bounded_token(self.provider_version_value, maximum=64)
            or not _bounded_token(self.version_scheme, maximum=32)
            or not _bounded_token(self.version_rule_id, maximum=128)
        ):
            raise InvalidProviderContract("compatibility_version_pair_invalid")
        if self.valid_until is not None and self.valid_until < self.assessed_at:
            raise InvalidProviderContract("compatibility_validity_invalid")


@dataclass(frozen=True, slots=True)
class CompatibilityAssessmentViewV1(TechnicalValueV1):
    """Persisted immutable assessment plus current/supersession metadata."""

    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    assessment_id: OpaqueIdV1
    registration_id: OpaqueIdV1
    provider_key: str
    adapter_id: str
    adapter_version: str
    protocol_version: str
    installation_id: OpaqueIdV1 | None
    capability_id: str
    capability_schema_version: str
    source_id: str | None
    provider_version_value: str | None
    provider_version_state: ProviderVersionStateV1
    version_scheme: ProviderVersionSchemeV1 | None
    version_rule_id: str | None
    compatibility_state: CompatibilityStateV1
    reason_code: str
    manifest_schema_version: str
    manifest_fingerprint: str
    input_fingerprint: str
    assessed_at: datetime
    valid_until: datetime | None
    supersedes_assessment_id: OpaqueIdV1 | None
    correlation_id: OpaqueIdV1
    is_current: bool
    record_version: int

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if (
            not _bounded_token(self.assessment_id.value, maximum=64)
            or _SHA256.fullmatch(self.input_fingerprint) is None
            or type(self.is_current) is not bool
            or type(self.record_version) is not int
            or self.record_version < 1
        ):
            raise InvalidProviderContract("compatibility_assessment_view_invalid")
        CompatibilityAssessmentInputV1(
            registration_id=self.registration_id,
            provider_key=self.provider_key,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            protocol_version=self.protocol_version,
            installation_id=self.installation_id,
            capability_id=self.capability_id,
            capability_schema_version=self.capability_schema_version,
            source_id=self.source_id,
            provider_version_value=self.provider_version_value,
            provider_version_state=self.provider_version_state,
            version_scheme=self.version_scheme,
            version_rule_id=self.version_rule_id,
            compatibility_state=self.compatibility_state,
            reason_code=self.reason_code,
            manifest_schema_version=self.manifest_schema_version,
            manifest_fingerprint=self.manifest_fingerprint,
            assessed_at=self.assessed_at,
            valid_until=self.valid_until,
            correlation_id=self.correlation_id,
        )


@dataclass(frozen=True, slots=True)
class ProviderSystemOutboxEventV1(TechnicalValueV1):
    """Safe bounded event metadata owned by the M03 transactional outbox."""

    CONTRACT_ID: ClassVar[str] = "CTR-PROV-002"
    OWNER: ClassVar[str] = "PLAN-M03"

    event_id: OpaqueIdV1
    event_type: str
    assessment_id: OpaqueIdV1
    registration_id: OpaqueIdV1
    provider_key: str
    capability_id: str
    compatibility_state: CompatibilityStateV1
    reason_code: str
    correlation_id: OpaqueIdV1
    producer_sequence: int
    occurred_at: datetime
    recorded_at: datetime
    delivery_state: OutboxDeliveryStateV1
    available_at: datetime
    claimed_at: datetime | None
    delivered_at: datetime | None
    attempt_count: int

    def __post_init__(self) -> None:
        timestamps = (
            self.occurred_at,
            self.recorded_at,
            self.available_at,
            self.claimed_at,
            self.delivered_at,
        )
        if any(
            value is not None
            and (not isinstance(value, datetime) or value.utcoffset() != timedelta(0))
            for value in timestamps
        ):
            raise InvalidProviderContract("provider_system_outbox_timestamp_invalid")
        TechnicalValueV1.__post_init__(self)
        _validate_capability_id(self.capability_id)
        if (
            not _bounded_token(self.event_id.value, maximum=64)
            or not _bounded_token(self.event_type, maximum=64)
            or not _bounded_token(self.assessment_id.value, maximum=64)
            or not _bounded_token(self.registration_id.value, maximum=64)
            or not _bounded_token(self.provider_key, maximum=64)
            or not _bounded_token(self.reason_code, maximum=128)
            or not _bounded_token(self.correlation_id.value, maximum=64)
            or type(self.producer_sequence) is not int
            or self.producer_sequence < 1
            or type(self.attempt_count) is not int
            or self.attempt_count < 0
        ):
            raise InvalidProviderContract("provider_system_outbox_event_invalid")
        if (
            self.recorded_at < self.occurred_at
            or self.available_at < self.recorded_at
            or (self.claimed_at is not None and self.claimed_at < self.available_at)
            or (
                self.delivered_at is not None
                and (self.claimed_at is None or self.delivered_at < self.claimed_at)
            )
        ):
            raise InvalidProviderContract("provider_system_outbox_timeline_invalid")
        state_is_valid = (
            (
                self.delivery_state == "pending"
                and self.claimed_at is None
                and self.delivered_at is None
            )
            or (
                self.delivery_state == "claimed"
                and self.claimed_at is not None
                and self.delivered_at is None
                and self.attempt_count > 0
            )
            or (
                self.delivery_state == "delivered"
                and self.claimed_at is not None
                and self.delivered_at is not None
                and self.attempt_count > 0
            )
        )
        if not state_is_valid:
            raise InvalidProviderContract("provider_system_outbox_state_invalid")


ExtensionScalarV1 = str | int | bool | Decimal | datetime | None


@dataclass(frozen=True, slots=True)
class ExtensionFieldV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-008"
    OWNER: ClassVar[str] = "PLAN-M03"

    name: str
    value: ExtensionScalarV1


@dataclass(frozen=True, slots=True)
class SafeProviderExtensionV1(TechnicalValueV1):
    CONTRACT_ID: ClassVar[str] = "CTR-PROV-008"
    OWNER: ClassVar[str] = "PLAN-M03"

    provider_key: str
    capability_id: str
    schema_name: str
    schema_major: int
    schema_minor: int
    values: tuple[ExtensionFieldV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        _validate_capability_id(self.capability_id)
        names = tuple(item.name for item in self.values)
        if (
            not _bounded_token(self.provider_key)
            or not _bounded_token(self.schema_name)
            or type(self.schema_major) is not int
            or self.schema_major < 1
            or type(self.schema_minor) is not int
            or self.schema_minor < 0
            or len(names) != len(set(names))
        ):
            raise InvalidProviderContract("provider_extension_invalid")


@runtime_checkable
class ProviderCapabilityPortV1[RequestT, ResultT: TechnicalValueV1](Protocol):
    def __call__(self, request: RequestT) -> CollectionOutcomeV1[ResultT]: ...


class InstallationDiscoveryPortV1(
    ProviderCapabilityPortV1[ProviderOperationRequestHeaderV1, DiscoveryCandidatesV1],
    Protocol,
): ...


class AccountDiscoveryPortV1(
    ProviderCapabilityPortV1[ProviderOperationRequestHeaderV1, DiscoveryCandidatesV1],
    Protocol,
): ...


class AuthenticationHealthPortV1(
    ProviderCapabilityPortV1[ProviderOperationRequestHeaderV1, AuthHealthObservationV1],
    Protocol,
): ...


class SubscriptionQuotaPortV1[ResultT: TechnicalValueV1](
    ProviderCapabilityPortV1[ProviderOperationRequestHeaderV1, ResultT],
    Protocol,
): ...


class LocalSessionDiscoveryPortV1[ResultT: TechnicalValueV1](
    ProviderCapabilityPortV1[ProviderOperationRequestHeaderV1, ResultT],
    Protocol,
): ...


class LocalSessionMetricsPortV1[ResultT: TechnicalValueV1](
    ProviderCapabilityPortV1[ProviderOperationRequestHeaderV1, ResultT],
    Protocol,
): ...


class LocalProcessCorrelationPortV1[ResultT: TechnicalValueV1](
    ProviderCapabilityPortV1[ProviderOperationRequestHeaderV1, ResultT],
    Protocol,
): ...


@runtime_checkable
class ProviderAdapterV1(Protocol):
    @property
    def descriptor(self) -> AdapterDescriptorV1: ...

    @property
    def manifest(self) -> CapabilityManifestV1: ...
