"""M03-owned V1 observation provenance shared by typed provider outcomes."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal

from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    TechnicalValueV1,
)

SourceClassV1 = Literal[
    "documented_api",
    "supported_cli",
    "approved_local_metadata",
    "experimental_private_or_browser",
]
PrecisionV1 = Literal["exact", "rounded", "range", "estimated", "unknown"]
ConfidenceV1 = Literal["confirmed", "high", "medium", "low", "unknown"]
ValueKindV1 = Literal[
    "authoritative", "provider_reported", "derived", "heuristic", "unknown"
]


def _bounded_text(value: object, *, maximum: int = 128) -> bool:
    return (
        type(value) is str
        and value == value.strip()
        and 1 <= len(value) <= maximum
        and value.isprintable()
    )


def _available_pair(value: object | None, availability: FieldAvailabilityV1) -> bool:
    return (value is not None) == (availability.state in {"available", "stale"})


@dataclass(frozen=True, slots=True)
class FallbackAttemptV1(TechnicalValueV1):
    """One safe failed-source reason authorizing the next approved source."""

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-004"
    OWNER: ClassVar[str] = "PLAN-M03"

    source_id: str
    failure_code: str

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        if not _bounded_text(self.source_id) or not _bounded_text(self.failure_code):
            raise ValueError("fallback_attempt_invalid")


@dataclass(frozen=True, slots=True)
class ObservationProvenanceV1(TechnicalValueV1):
    """Complete safe lineage for one provider observation.

    The contract carries only allowlisted identifiers and classifications. Raw
    provider output, paths, identity, credentials, and content have no field.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-COMMON-004"
    OWNER: ClassVar[str] = "PLAN-M03"

    provider_key: str
    capability_id: str
    capability_schema_version: str
    adapter_id: str
    adapter_version: str
    provider_protocol_version: str
    source_id: str
    source_class: SourceClassV1
    mechanism_version: str
    parser_version: str | None
    provider_version: str | None
    provider_version_availability: FieldAvailabilityV1
    observed_at: datetime | None
    observed_at_availability: FieldAvailabilityV1
    collected_at: datetime
    freshness_deadline: datetime | None
    freshness_availability: FieldAvailabilityV1
    freshness_policy_id: str
    precision: PrecisionV1
    confidence: ConfidenceV1
    confidence_reason_code: str
    value_kind: ValueKindV1
    is_experimental: bool
    fallback_lineage: tuple[FallbackAttemptV1, ...]
    warnings: tuple[str, ...]
    operation_id: OpaqueIdV1
    correlation_id: OpaqueIdV1
    decision_reference: str
    derivation_method: str | None
    input_observation_ids: tuple[OpaqueIdV1, ...]

    def __post_init__(self) -> None:
        TechnicalValueV1.__post_init__(self)
        required_text = (
            self.provider_key,
            self.capability_id,
            self.capability_schema_version,
            self.adapter_id,
            self.adapter_version,
            self.provider_protocol_version,
            self.source_id,
            self.mechanism_version,
            self.freshness_policy_id,
            self.confidence_reason_code,
            self.decision_reference,
        )
        if not all(_bounded_text(value) for value in required_text):
            raise ValueError("provenance_identifier_invalid")
        if self.parser_version is not None and not _bounded_text(self.parser_version):
            raise ValueError("provenance_parser_version_invalid")
        if self.provider_version is not None and not _bounded_text(
            self.provider_version
        ):
            raise ValueError("provenance_provider_version_invalid")
        if not _available_pair(
            self.provider_version, self.provider_version_availability
        ):
            raise ValueError("provenance_provider_version_pair_invalid")
        if not _available_pair(self.observed_at, self.observed_at_availability):
            raise ValueError("provenance_observed_at_pair_invalid")
        if not _available_pair(self.freshness_deadline, self.freshness_availability):
            raise ValueError("provenance_freshness_pair_invalid")
        if self.observed_at is not None and self.collected_at < self.observed_at:
            raise ValueError("provenance_time_order_invalid")
        if (
            self.freshness_deadline is not None
            and self.observed_at is not None
            and self.freshness_deadline < self.observed_at
        ):
            raise ValueError("provenance_freshness_time_invalid")
        if (
            self.freshness_availability.state == "stale"
            and self.freshness_deadline is not None
            and self.freshness_deadline > self.collected_at
        ):
            raise ValueError("provenance_stale_time_invalid")
        if type(self.is_experimental) is not bool:
            raise TypeError("provenance_experimental_flag_invalid")
        if (
            len(self.fallback_lineage) > 16
            or not all(
                isinstance(item, FallbackAttemptV1) for item in self.fallback_lineage
            )
            or len({item.source_id for item in self.fallback_lineage})
            != len(self.fallback_lineage)
        ):
            raise ValueError("provenance_fallback_invalid")
        if (
            len(self.warnings) > 16
            or len(set(self.warnings)) != len(self.warnings)
            or not all(_bounded_text(value) for value in self.warnings)
        ):
            raise ValueError("provenance_warning_invalid")
        has_derivation = self.derivation_method is not None
        if has_derivation != bool(self.input_observation_ids):
            raise ValueError("provenance_derivation_pair_invalid")
        if self.value_kind == "derived" and not has_derivation:
            raise ValueError("provenance_derived_inputs_required")
        if self.value_kind != "derived" and has_derivation:
            raise ValueError("provenance_nonderived_inputs_forbidden")
        if self.derivation_method is not None and not _bounded_text(
            self.derivation_method
        ):
            raise ValueError("provenance_derivation_method_invalid")
