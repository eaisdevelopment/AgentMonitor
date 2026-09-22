"""ST-PROV-001: provider-neutral protocol and fail-closed negotiation."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_provenance_v1 import (
    FallbackAttemptV1,
    ObservationProvenanceV1,
)
from agentmonitor.contracts.common_v1 import (
    FieldAvailabilityV1,
    OpaqueIdV1,
    TechnicalValueV1,
)
from agentmonitor.contracts.provider_system_v1 import (
    AdapterDescriptorV1,
    AuthHealthObservationV1,
    CapabilityDeclarationV1,
    CapabilityManifestV1,
    CapabilitySchemaRangeV1,
    CapabilitySchemaVersionV1,
    CollectionConstraintV1,
    CollectionOutcomeV1,
    IdentityComparisonV1,
    InvalidCollectionOutcome,
    InvalidProviderContract,
    MissingFieldV1,
    ProtocolVersionRangeV1,
    ProviderOperationRequestHeaderV1,
    ProviderSourceV1,
    ProviderTargetV1,
    ProviderVersionRuleV1,
    RetryAdviceV1,
    SanitizedWarningV1,
    SourcePolicyV1,
    SourceTransitionV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    ResolveAndInvokeProviderCapabilityV1,
    validate_collection_outcome_v1,
)
from agentmonitor.modules.provider_system.domain.protocol import (
    ProviderCatalogV1,
    resolve_capability,
)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
MAPPING_DIGEST = "82e2acc24dfa5b35d1778ee8e245b00fed567c4f20402293cd2ec16dcd4d8b24"


@dataclass(frozen=True, slots=True)
class SafeValueV1(TechnicalValueV1):
    """A typed pure-domain payload; it is not provider telemetry."""

    label: str


def source(
    *,
    source_id: str = "claude.usage.ax-screen-reader.v1",
    capability_id: str = "subscription.quota",
    source_class: str = "supported_cli",
    is_experimental: bool = False,
) -> ProviderSourceV1:
    return ProviderSourceV1(
        source_id=source_id,
        provider_key="claude",
        capability_id=capability_id,
        source_class=source_class,  # type: ignore[arg-type]
        stability="supported",
        mechanism_version="1",
        credential_role="provider_managed_profile",
        side_effect_class="read_only",
        evidence_reference="M0-M03-CLAUDE-001",
        is_experimental=is_experimental,
    )


def constraints() -> CollectionConstraintV1:
    return CollectionConstraintV1(
        deadline_ms=30_000,
        minimum_interval_ms=300_000,
        maximum_concurrency=1,
        automatic_retry_count=0,
        provider_request_count=None,
        provider_request_count_availability=FieldAvailabilityV1("unknown"),
    )


def declaration(
    *,
    capability_id: str = "subscription.quota",
    decision: str = "supported",
    sources: tuple[ProviderSourceV1, ...] | None = None,
    provider_versions: tuple[str, ...] = ("2.1.278",),
    schema_major: int = 1,
    port_type: str | None = "SubscriptionQuotaPortV1",
) -> CapabilityDeclarationV1:
    declared_sources = (
        (source(capability_id=capability_id),) if sources is None else sources
    )
    return CapabilityDeclarationV1(
        capability_id=capability_id,
        schema_versions=CapabilitySchemaRangeV1(
            CapabilitySchemaVersionV1(schema_major, 0),
            CapabilitySchemaVersionV1(schema_major, 0),
        ),
        decision=decision,  # type: ignore[arg-type]
        stability="supported" if decision == "supported" else "unknown",
        reason_code=f"m0_{decision}",
        evidence_reference="M0-M03-CLAUDE-001",
        port_type=port_type,
        output_schema="ProviderQuotaInputV1" if port_type else None,
        sources=declared_sources,
        provider_version_rule=ProviderVersionRuleV1(
            rule_id="claude-code-exact-v1",
            scheme="opaque_exact",
            verified_versions=provider_versions,
        ),
        constraints=constraints(),
        side_effect_class="read_only",
        platforms=("linux-x86_64",),
    )


def manifest(
    *declarations: CapabilityDeclarationV1,
    protocol_minimum: str = "1.0.0",
    protocol_maximum: str = "1.0.0",
    build_identity: str = "agentmonitor-claude-v1",
) -> CapabilityManifestV1:
    declared = declarations or (declaration(),)
    return CapabilityManifestV1(
        descriptor=AdapterDescriptorV1(
            adapter_id="agentmonitor.claude",
            adapter_version="1.0.0",
            provider_key="claude",
            protocol_versions=ProtocolVersionRangeV1(
                protocol_minimum, protocol_maximum
            ),
            build_identity=build_identity,
        ),
        manifest_schema_version="1.0.0",
        declarations=declared,
        m0_mapping_id="M0-M03-CLAUDE-001",
        m0_mapping_version="1.0.0",
        m0_mapping_digest=MAPPING_DIGEST,
    )


def provenance(
    *,
    source_class: str = "supported_cli",
    provider_version: str | None = "2.1.278",
    parser_version: str | None = None,
    freshness_state: str = "available",
) -> ObservationProvenanceV1:
    return ObservationProvenanceV1(
        provider_key="claude",
        capability_id="subscription.quota",
        capability_schema_version="1.0",
        adapter_id="agentmonitor.claude",
        adapter_version="1.0.0",
        provider_protocol_version="1.0.0",
        source_id="claude.usage.ax-screen-reader.v1",
        source_class=source_class,  # type: ignore[arg-type]
        mechanism_version="1",
        parser_version=parser_version,
        provider_version=provider_version,
        provider_version_availability=FieldAvailabilityV1(
            "available" if provider_version else "unknown"
        ),
        observed_at=NOW,
        observed_at_availability=FieldAvailabilityV1("available"),
        collected_at=NOW + timedelta(seconds=1),
        freshness_deadline=(
            NOW + timedelta(minutes=5) if freshness_state == "available" else None
        ),
        freshness_availability=FieldAvailabilityV1(freshness_state),  # type: ignore[arg-type]
        freshness_policy_id="claude-usage-five-minute-v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="provider_reported",
        value_kind="provider_reported",
        is_experimental=False,
        fallback_lineage=(),
        warnings=(),
        operation_id=OpaqueIdV1("operation-1"),
        correlation_id=OpaqueIdV1("correlation-1"),
        decision_reference="M0-M03-CLAUDE-001",
        derivation_method=None,
        input_observation_ids=(),
    )


def request_header(
    *, source_ids: tuple[str, ...] = ("claude.usage.ax-screen-reader.v1",)
) -> ProviderOperationRequestHeaderV1:
    return ProviderOperationRequestHeaderV1(
        operation_id=OpaqueIdV1("operation-1"),
        correlation_id=OpaqueIdV1("correlation-1"),
        provider_key="claude",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        target=ProviderTargetV1(
            provider_key="claude",
            installation_ref=OpaqueIdV1("installation-1"),
            account_ref=OpaqueIdV1("account-1"),
            profile_ref=OpaqueIdV1("profile-1"),
            resource_ref=None,
            profile_protection="managed",
        ),
        requested_at=NOW,
        deadline_ms=30_000,
        source_policy=SourcePolicyV1(
            policy_ref=OpaqueIdV1("source-policy-1"),
            source_ids=source_ids,
            approved_fallbacks=(),
            experimental_grant_ref=None,
        ),
        access_grant_refs=(OpaqueIdV1("subprocess-grant-1"),),
    )


@pytest.mark.parametrize(
    "capability_id",
    ["", "Subscription.Quota", "subscription/quota", "subscription..quota", "x" * 129],
)
def test_capability_identifier_rejects_malformed_or_unbounded_values(
    capability_id: str,
) -> None:
    """M03-PURE-001: capability identifiers are bounded and grammatical."""
    with pytest.raises(InvalidProviderContract, match="capability_id_invalid"):
        declaration(capability_id=capability_id)


@pytest.mark.parametrize(
    "decision", ["supported", "experimental", "deferred", "unsupported", "unknown"]
)
def test_discovery_decisions_remain_distinct(decision: str) -> None:
    """M03-PURE-002: discovery decisions retain their exact meaning."""
    invokable = decision in {"supported", "experimental"}
    item = declaration(
        decision=decision,
        sources=(
            (
                source(
                    source_class=(
                        "experimental_private_or_browser"
                        if decision == "experimental"
                        else "supported_cli"
                    ),
                    is_experimental=decision == "experimental",
                ),
            )
            if invokable
            else ()
        ),
        port_type="SubscriptionQuotaPortV1" if invokable else None,
    )
    assert item.decision == decision


@pytest.mark.parametrize(
    "state", ["unsupported", "unavailable", "unknown", "missing", "stale"]
)
def test_field_availability_states_are_not_collapsed(state: str) -> None:
    """M03-PURE-003: runtime availability states are not collapsed."""
    assert FieldAvailabilityV1(state).state == state  # type: ignore[arg-type]


def test_same_protocol_major_and_schema_resolve_deterministically() -> None:
    """M03-PURE-004: a verified same-major tuple resolves deterministically."""
    first = resolve_capability(
        manifest(),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=request_header().source_policy,
    )
    second = resolve_capability(
        manifest(),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=request_header().source_policy,
    )
    assert first == second
    assert first.code == "resolved"


def test_protocol_major_mismatch_is_rejected() -> None:
    """M03-PURE-005: incompatible protocol majors fail before invocation."""
    result = resolve_capability(
        manifest(protocol_minimum="2.0.0", protocol_maximum="2.2.0"),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=request_header().source_policy,
    )
    assert result.code == "protocol_incompatible"


def test_manifest_rejects_duplicate_capability_declarations() -> None:
    """M03-PURE-006: one manifest cannot declare a capability twice."""
    duplicate = declaration()
    with pytest.raises(InvalidProviderContract, match="manifest_duplicate_capability"):
        manifest(duplicate, duplicate)


def test_supported_declaration_requires_constraints_source_and_typed_port() -> None:
    """M03-PURE-007: an invokable declaration is structurally complete."""
    with pytest.raises(
        InvalidProviderContract, match="invokable_declaration_incomplete"
    ):
        declaration(sources=(), port_type=None)


def test_opaque_provider_versions_are_never_ordered_semantically() -> None:
    """M03-PURE-008: opaque versions use exact evidence, never ordering."""
    exact = declaration(provider_versions=("10",))
    assert (
        resolve_capability(
            manifest(exact),
            approved_mapping_digest=MAPPING_DIGEST,
            host_protocol_version="1.0.0",
            capability_id="subscription.quota",
            capability_schema_version=CapabilitySchemaVersionV1(1, 0),
            provider_version="2",
            platform_id="linux-x86_64",
            source_policy=request_header().source_policy,
        ).code
        == "provider_version_unverified"
    )


def test_capability_schema_major_mismatch_does_not_resolve() -> None:
    """M03-PURE-009: incompatible capability schema majors do not resolve."""
    result = resolve_capability(
        manifest(),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(2, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=request_header().source_policy,
    )
    assert result.code == "capability_schema_incompatible"


def test_unverified_provider_version_is_rejected_before_invocation() -> None:
    """M03-PURE-010: provider version drift is rejected before port I/O."""
    calls = 0

    def invoke(_: ProviderOperationRequestHeaderV1) -> CollectionOutcomeV1[SafeValueV1]:
        nonlocal calls
        calls += 1
        return CollectionOutcomeV1.success(SafeValueV1("safe"), provenance())

    result: CollectionOutcomeV1[SafeValueV1] = ResolveAndInvokeProviderCapabilityV1[
        SafeValueV1
    ](approved_mapping_digest=MAPPING_DIGEST)(
        manifest=manifest(),
        request=request_header(),
        provider_version="new-unknown",
        platform_id="linux-x86_64",
        invoke=invoke,
    )
    assert result.state == "unverified_provider_version"
    assert calls == 0


def test_source_policy_requires_declared_order_and_explicit_fallback() -> None:
    """M03-PURE-011/013: source order and fallback require approval."""
    primary = source()
    secondary = source(
        source_id="claude.usage.local-metadata.v1",
        source_class="approved_local_metadata",
    )
    item = declaration(sources=(primary, secondary))
    undeclared_chain = SourcePolicyV1(
        OpaqueIdV1("policy"),
        (secondary.source_id, primary.source_id),
        (),
        None,
    )
    assert (
        resolve_capability(
            manifest(item),
            approved_mapping_digest=MAPPING_DIGEST,
            host_protocol_version="1.0.0",
            capability_id="subscription.quota",
            capability_schema_version=CapabilitySchemaVersionV1(1, 0),
            provider_version="2.1.278",
            platform_id="linux-x86_64",
            source_policy=undeclared_chain,
        ).code
        == "source_policy_unapproved"
    )


def test_experimental_source_requires_scoped_grant() -> None:
    """M03-PURE-012: experimental sources require an explicit grant."""
    experimental = source(
        source_id="claude.usage.experimental.v1",
        source_class="experimental_private_or_browser",
        is_experimental=True,
    )
    item = declaration(decision="experimental", sources=(experimental,))
    result = resolve_capability(
        manifest(item),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=SourcePolicyV1(
            OpaqueIdV1("policy"), (experimental.source_id,), (), None
        ),
    )
    assert result.code == "capability_disabled"


def test_mapping_digest_mismatch_is_rejected_before_resolution() -> None:
    """M03-PURE-006/010: only the accepted M0 mapping may resolve."""
    result = resolve_capability(
        replace(manifest(), m0_mapping_digest="a" * 64),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=request_header().source_policy,
    )
    assert result.code == "mapping_binding_invalid"


@pytest.mark.parametrize("drift", ["protocol", "schema"])
def test_protocol_or_schema_drift_never_invokes_the_port(drift: str) -> None:
    """M03-PURE-005/009: protocol/schema drift is pre-I/O failure."""
    calls = 0

    def invoke(_: ProviderOperationRequestHeaderV1) -> CollectionOutcomeV1[SafeValueV1]:
        nonlocal calls
        calls += 1
        return CollectionOutcomeV1.success(SafeValueV1("safe"), provenance())

    current_manifest = (
        manifest(protocol_minimum="2.0.0", protocol_maximum="2.0.0")
        if drift == "protocol"
        else manifest()
    )
    current_request = (
        request_header()
        if drift == "protocol"
        else replace(
            request_header(),
            capability_schema_version=CapabilitySchemaVersionV1(2, 0),
        )
    )
    outcome: CollectionOutcomeV1[SafeValueV1] = ResolveAndInvokeProviderCapabilityV1[
        SafeValueV1
    ](approved_mapping_digest=MAPPING_DIGEST)(
        manifest=current_manifest,
        request=current_request,
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        invoke=invoke,
    )
    assert outcome.state == "unverified_provider_version"
    assert calls == 0


def test_approved_source_chain_selects_only_the_first_exact_source() -> None:
    """M03-PURE-011: an approved chain resolves its exact primary source."""
    primary = source()
    secondary = source(
        source_id="claude.usage.local-metadata.v1",
        source_class="approved_local_metadata",
    )
    current = declaration(sources=(primary, secondary))
    policy = SourcePolicyV1(
        OpaqueIdV1("source-policy"),
        (primary.source_id, secondary.source_id),
        (
            SourceTransitionV1(
                primary.source_id,
                secondary.source_id,
                ("provider_unavailable",),
            ),
        ),
        None,
    )
    result = resolve_capability(
        manifest(current),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=policy,
    )
    assert result.code == "resolved"
    assert result.selected_source == primary


def test_source_chain_without_approved_transition_is_rejected() -> None:
    """M03-PURE-011/013: a listed source is not implicit fallback authority."""
    primary = source()
    secondary = source(
        source_id="claude.usage.local-metadata.v1",
        source_class="approved_local_metadata",
    )
    policy = SourcePolicyV1(
        OpaqueIdV1("source-policy"),
        (primary.source_id, secondary.source_id),
        (),
        None,
    )
    result = resolve_capability(
        manifest(declaration(sources=(primary, secondary))),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=policy,
    )
    assert result.code == "source_policy_unapproved"


@pytest.mark.parametrize(
    "failure_codes",
    [(), ("",), ("provider_unavailable", "provider_unavailable")],
)
def test_source_transition_rejects_empty_or_invalid_failure_codes(
    failure_codes: tuple[str, ...],
) -> None:
    """M03-PURE-013: fallback authority requires closed safe failure codes."""
    with pytest.raises(
        InvalidProviderContract, match="source_transition_failure_codes_invalid"
    ):
        SourceTransitionV1(
            "claude.usage.ax-screen-reader.v1",
            "claude.usage.local-metadata.v1",
            failure_codes,
        )


def test_approved_fallback_accepts_exact_actual_source_and_lineage() -> None:
    """M03-PURE-013: approved fallback preserves exact source lineage."""
    primary = source()
    secondary = source(
        source_id="claude.usage.local-metadata.v1",
        source_class="approved_local_metadata",
    )
    policy = SourcePolicyV1(
        OpaqueIdV1("source-policy"),
        (primary.source_id, secondary.source_id),
        (
            SourceTransitionV1(
                primary.source_id,
                secondary.source_id,
                ("provider_unavailable",),
            ),
        ),
        None,
    )
    request = replace(request_header(), source_policy=policy)
    resolution = resolve_capability(
        manifest(declaration(sources=(primary, secondary))),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id=request.capability_id,
        capability_schema_version=request.capability_schema_version,
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=policy,
    )
    fallback_provenance = replace(
        provenance(),
        source_id=secondary.source_id,
        source_class=secondary.source_class,
        parser_version="1",
        fallback_lineage=(
            FallbackAttemptV1(primary.source_id, "provider_unavailable"),
        ),
    )
    outcome = CollectionOutcomeV1.success(SafeValueV1("safe"), fallback_provenance)
    validated = validate_collection_outcome_v1(
        resolution=resolution,
        request=request,
        provider_version="2.1.278",
        outcome=outcome,
    )
    assert validated == outcome


def test_fallback_without_prior_failure_code_is_rejected() -> None:
    """M03-PURE-013: missing or mismatched fallback evidence is rejected."""
    primary = source()
    secondary = source(
        source_id="claude.usage.local-metadata.v1",
        source_class="approved_local_metadata",
    )
    policy = SourcePolicyV1(
        OpaqueIdV1("source-policy"),
        (primary.source_id, secondary.source_id),
        (
            SourceTransitionV1(
                primary.source_id,
                secondary.source_id,
                ("provider_unavailable",),
            ),
        ),
        None,
    )
    request = replace(request_header(), source_policy=policy)
    resolution = resolve_capability(
        manifest(declaration(sources=(primary, secondary))),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id=request.capability_id,
        capability_schema_version=request.capability_schema_version,
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=policy,
    )
    for invalid_lineage in (
        (),
        (FallbackAttemptV1(primary.source_id, "rate_limited"),),
        (FallbackAttemptV1("unapproved.source", "provider_unavailable"),),
    ):
        incomplete_provenance = replace(
            provenance(),
            source_id=secondary.source_id,
            source_class=secondary.source_class,
            parser_version="1",
            fallback_lineage=invalid_lineage,
        )
        validated = validate_collection_outcome_v1(
            resolution=resolution,
            request=request,
            provider_version="2.1.278",
            outcome=CollectionOutcomeV1.success(
                SafeValueV1("safe"), incomplete_provenance
            ),
        )
        assert validated.state == "invalid_provider_data"
        assert validated.error is not None
        assert validated.error.code == "provider_outcome_provenance_mismatch"


def test_actual_source_cannot_silently_differ_from_negotiation() -> None:
    """M03-PURE-013: pure outcome validation rejects source substitution."""
    primary = source()
    secondary = source(
        source_id="claude.usage.local-metadata.v1",
        source_class="approved_local_metadata",
    )
    current_manifest = manifest(declaration(sources=(primary, secondary)))
    request = request_header()
    resolution = resolve_capability(
        current_manifest,
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id=request.capability_id,
        capability_schema_version=request.capability_schema_version,
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=request.source_policy,
    )
    actual = replace(
        provenance(),
        source_id=secondary.source_id,
        source_class=secondary.source_class,
        parser_version="1",
    )
    outcome = validate_collection_outcome_v1(
        resolution=resolution,
        request=request,
        provider_version="2.1.278",
        outcome=CollectionOutcomeV1.success(SafeValueV1("safe"), actual),
    )
    assert outcome.state == "invalid_provider_data"
    assert outcome.error is not None
    assert outcome.error.code == "provider_outcome_provenance_mismatch"


@pytest.mark.parametrize("raw", ["raw", b"raw", object()])
def test_outcome_rejects_every_untyped_raw_payload(raw: object) -> None:
    """M03-PURE-014: raw strings, bytes, and objects are not typed payloads."""
    with pytest.raises(InvalidCollectionOutcome, match="typed_payload_required"):
        CollectionOutcomeV1.success(raw, provenance())  # type: ignore[type-var]


def test_closed_outcome_rejects_missing_or_multiple_variants() -> None:
    """M03-PURE-014: exactly one complete outcome variant is permitted."""
    with pytest.raises(
        InvalidCollectionOutcome, match="collection_outcome_variant_invalid"
    ):
        CollectionOutcomeV1[SafeValueV1]("success", None, None, (), (), None)
    failure: CollectionOutcomeV1[SafeValueV1] = CollectionOutcomeV1.failure(
        state="unsupported",
        code="unsupported",
        retry=RetryAdviceV1("never"),
    )
    error = failure.error
    with pytest.raises(
        InvalidCollectionOutcome, match="collection_outcome_variant_invalid"
    ):
        CollectionOutcomeV1[SafeValueV1](
            "success",
            SafeValueV1("safe"),
            provenance(),
            (),
            (),
            error,
        )


def test_success_without_provenance_is_rejected() -> None:
    """M03-PURE-017: successful values always carry provenance."""
    with pytest.raises(
        InvalidCollectionOutcome, match="collection_outcome_variant_invalid"
    ):
        CollectionOutcomeV1[SafeValueV1](
            "success", SafeValueV1("safe"), None, (), (), None
        )


def test_stale_freshness_requires_an_expired_deadline() -> None:
    """M03-PURE-018: stale evidence cannot carry a future freshness deadline."""
    stale = replace(
        provenance(),
        freshness_deadline=NOW,
        freshness_availability=FieldAvailabilityV1("stale"),
    )
    assert stale.freshness_availability.state == "stale"
    with pytest.raises(ValueError, match="provenance_stale_time_invalid"):
        replace(
            provenance(),
            freshness_availability=FieldAvailabilityV1("stale"),
        )


def test_experimental_source_resolves_with_exact_scoped_grant() -> None:
    """M03-PURE-012: an explicit grant enables only its requested source."""
    experimental = source(
        source_id="claude.usage.experimental.v1",
        source_class="experimental_private_or_browser",
        is_experimental=True,
    )
    policy = SourcePolicyV1(
        OpaqueIdV1("experimental-policy"),
        (experimental.source_id,),
        (),
        OpaqueIdV1("experimental-grant"),
    )
    result = resolve_capability(
        manifest(declaration(decision="experimental", sources=(experimental,))),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=policy,
    )
    assert result.code == "resolved"
    assert result.selected_source == experimental


def test_provenance_enum_and_derivation_relationships_are_closed() -> None:
    """M03-PURE-020: precision/confidence/value-kind relationships are closed."""
    with pytest.raises(ValueError, match="unsupported-field-state"):
        replace(provenance(), precision="approximate")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unsupported-field-state"):
        replace(provenance(), confidence="certain")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="provenance_derived_inputs_required"):
        replace(provenance(), value_kind="derived")


def test_request_header_rejects_unsafe_or_ambiguous_context() -> None:
    """CTR-PROV-001/004: every request has bounded, matching safe context."""
    with pytest.raises(
        InvalidProviderContract, match="request_target_provider_mismatch"
    ):
        replace(request_header(), provider_key="codex")
    with pytest.raises(InvalidProviderContract, match="request_access_grant_required"):
        replace(request_header(), access_grant_refs=())
    with pytest.raises(ValueError, match="timestamp-must-be-aware-utc"):
        replace(request_header(), requested_at=NOW.replace(tzinfo=None))


def test_manifest_requires_at_least_one_declaration_and_known_side_effect() -> None:
    """M03-PURE-006/007: empty or unclassified manifests fail closed."""
    with pytest.raises(InvalidProviderContract, match="manifest_declarations_required"):
        replace(manifest(), declarations=())
    with pytest.raises(ValueError, match="unsupported-field-state"):
        replace(
            declaration(),
            side_effect_class="write_anywhere",  # type: ignore[arg-type]
        )


def test_supported_schema_minor_inside_declared_range_resolves() -> None:
    """M03-PURE-009: mutually supported schema minor versions resolve."""
    current = replace(
        declaration(),
        schema_versions=CapabilitySchemaRangeV1(
            CapabilitySchemaVersionV1(1, 0),
            CapabilitySchemaVersionV1(1, 2),
        ),
    )
    result = resolve_capability(
        manifest(current),
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 1),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=request_header().source_policy,
    )
    assert result.code == "resolved"


def test_outcome_rejects_generic_dictionary_payload() -> None:
    """M03-PURE-014: a generic payload cannot enter the closed outcome."""
    with pytest.raises(InvalidCollectionOutcome, match="typed_payload_required"):
        CollectionOutcomeV1.success(  # type: ignore[type-var]
            {"raw": "forbidden"}, provenance()
        )


def test_partial_requires_omissions_warnings_and_provenance() -> None:
    """M03-PURE-015: partial requires typed omissions, warnings, evidence."""
    for omissions, warnings, evidence in (
        ((), (SanitizedWarningV1("safe_warning"),), provenance()),
        (
            (MissingFieldV1("reset_at", FieldAvailabilityV1("missing")),),
            (),
            provenance(),
        ),
        (
            (MissingFieldV1("reset_at", FieldAvailabilityV1("missing")),),
            (SanitizedWarningV1("safe_warning"),),
            None,
        ),
    ):
        with pytest.raises(InvalidCollectionOutcome, match="partial_outcome_invalid"):
            CollectionOutcomeV1.partial(
                SafeValueV1("safe"),
                omissions=omissions,
                warnings=warnings,
                provenance=evidence,
            )


@pytest.mark.parametrize(
    ("state", "retry"),
    [
        ("unsupported", "never"),
        ("provider_unavailable", "after_delay"),
        ("reauthentication_required", "after_reauthentication"),
        ("unverified_provider_version", "after_version_review"),
    ],
)
def test_failure_states_and_retry_dispositions_remain_distinct(
    state: str, retry: str
) -> None:
    """M03-PURE-016: material failure states remain distinct."""
    delay_seconds = 30 if retry == "after_delay" else None
    outcome: CollectionOutcomeV1[SafeValueV1] = CollectionOutcomeV1.failure(
        state=state,  # type: ignore[arg-type]
        code=f"safe_{state}",
        retry=RetryAdviceV1(retry, delay_seconds=delay_seconds),  # type: ignore[arg-type]
    )
    assert outcome.error is not None
    assert (outcome.state, outcome.error.retry.disposition) == (state, retry)


def test_provenance_requires_version_time_freshness_and_confidence() -> None:
    """M03-PURE-017/018/020: mandatory provenance relationships hold."""
    with pytest.raises(ValueError, match="provenance_provider_version_pair_invalid"):
        replace(
            provenance(),
            provider_version=None,
            provider_version_availability=FieldAvailabilityV1("available"),
        )
    with pytest.raises(ValueError, match="provenance_time_order_invalid"):
        replace(provenance(), collected_at=NOW - timedelta(seconds=1))
    with pytest.raises(ValueError, match="provenance_freshness_pair_invalid"):
        replace(
            provenance(),
            freshness_deadline=None,
            freshness_availability=FieldAvailabilityV1("available"),
        )


def test_local_metadata_success_requires_parser_and_provider_versions() -> None:
    """M03-PURE-019: local success cannot omit parser/version evidence."""
    local = provenance(source_class="approved_local_metadata", parser_version=None)
    with pytest.raises(InvalidCollectionOutcome, match="local_provenance_incomplete"):
        CollectionOutcomeV1.success(SafeValueV1("safe"), local)
    partial = CollectionOutcomeV1.partial(
        SafeValueV1("safe"),
        omissions=(MissingFieldV1("parser_version", FieldAvailabilityV1("missing")),),
        warnings=(SanitizedWarningV1("local_parser_version_missing"),),
        provenance=local,
    )
    assert partial.state == "partial"


def test_local_metadata_missing_provider_version_requires_partial_omission() -> None:
    """M03-PURE-019: local unknown provider version is explicit partial data."""
    local = provenance(
        source_class="approved_local_metadata",
        provider_version=None,
        parser_version="1",
    )
    with pytest.raises(InvalidCollectionOutcome, match="local_provenance_incomplete"):
        CollectionOutcomeV1.success(SafeValueV1("safe"), local)
    partial = CollectionOutcomeV1.partial(
        SafeValueV1("safe"),
        omissions=(MissingFieldV1("provider_version", FieldAvailabilityV1("unknown")),),
        warnings=(SanitizedWarningV1("provider_version_unknown"),),
        provenance=local,
    )
    assert partial.state == "partial"


@pytest.mark.parametrize(
    "state",
    [
        "healthy",
        "refreshing",
        "expiring",
        "reauthentication_required",
        "revoked_or_disabled",
        "wrong_account_detected",
        "unknown",
    ],
)
def test_all_authentication_health_states_round_trip(state: str) -> None:
    """M03-PURE-021: all seven authentication states remain distinct."""
    identity = (
        IdentityComparisonV1("mismatched", "strong_provider_id")
        if state == "wrong_account_detected"
        else IdentityComparisonV1("matched", "strong_provider_id")
    )
    observation = AuthHealthObservationV1(
        state=state,  # type: ignore[arg-type]
        provenance=provenance(),
        expires_at=None,
        expiry_precision="unknown",
        reason_code=f"auth_{state}",
        identity=identity,
    )
    assert observation.state == state


def test_provider_unavailability_is_not_an_auth_unknown_observation() -> None:
    """M03-PURE-022: provider failure is not an auth observation."""
    unavailable: CollectionOutcomeV1[SafeValueV1] = CollectionOutcomeV1.failure(
        state="provider_unavailable",
        code="provider_temporarily_unavailable",
        retry=RetryAdviceV1("after_delay", delay_seconds=30),
    )
    assert unavailable.state == "provider_unavailable"
    assert unavailable.value is None


@pytest.mark.parametrize("comparison", ["mismatched", "unresolved"])
def test_nonmatching_identity_cannot_authorize_association(comparison: str) -> None:
    """M03-PURE-023: mismatched/unresolved identity cannot auto-associate."""
    identity = IdentityComparisonV1(comparison, "owner_confirmation_required")  # type: ignore[arg-type]
    assert identity.may_associate_automatically is False


def test_strong_matching_identity_may_authorize_association() -> None:
    """M03-PURE-023: only a matching strong identity can auto-associate."""
    identity = IdentityComparisonV1("matched", "strong_provider_id")
    assert identity.may_associate_automatically is True


def test_auth_expiry_requires_non_unknown_precision() -> None:
    """M03-PURE-024: a known expiry cannot claim unknown precision."""
    with pytest.raises(InvalidProviderContract, match="auth_expiry_precision_invalid"):
        AuthHealthObservationV1(
            state="expiring",
            provenance=provenance(),
            expires_at=NOW + timedelta(hours=1),
            expiry_precision="unknown",
            reason_code="auth_expiring",
            identity=IdentityComparisonV1("matched", "strong_provider_id"),
        )
    with pytest.raises(InvalidProviderContract, match="auth_expiry_precision_invalid"):
        AuthHealthObservationV1(
            state="healthy",
            provenance=provenance(),
            expires_at=None,
            expiry_precision="estimated",
            reason_code="auth_healthy",
            identity=IdentityComparisonV1("matched", "strong_provider_id"),
        )


def test_exact_registration_replay_is_idempotent_and_conflict_is_isolated() -> None:
    """M03-PURE-031/032: exact replay is safe; conflicting reuse is not."""
    catalog = ProviderCatalogV1(
        host_protocol_version="1.0.0",
        approved_mapping_digest=MAPPING_DIGEST,
    )
    original = manifest()
    first = catalog.register(original, factory_identity="claude-factory-v1")
    replay = catalog.register(original, factory_identity="claude-factory-v1")
    conflict = catalog.register(
        manifest(build_identity="different-build"),
        factory_identity="different-factory",
    )
    assert first.code == "registered"
    assert replay.code == "already_registered"
    assert replay.registration == first.registration
    assert conflict.code == "registration_conflict"
    assert catalog.get("claude", "agentmonitor.claude") == first.registration


def test_incompatible_capability_does_not_disable_compatible_capability() -> None:
    """M03-PURE-033: one schema mismatch does not disable another port."""
    quota = declaration()
    runtime = declaration(
        capability_id="local.process.correlation",
        sources=(
            source(
                source_id="linux.proc.process.v1",
                capability_id="local.process.correlation",
                source_class="approved_local_metadata",
            ),
        ),
        schema_major=2,
        port_type="LocalProcessCorrelationPortV1",
    )
    current = manifest(quota, runtime)
    policy = request_header().source_policy
    quota_result = resolve_capability(
        current,
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="subscription.quota",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=policy,
    )
    runtime_result = resolve_capability(
        current,
        approved_mapping_digest=MAPPING_DIGEST,
        host_protocol_version="1.0.0",
        capability_id="local.process.correlation",
        capability_schema_version=CapabilitySchemaVersionV1(1, 0),
        provider_version="2.1.278",
        platform_id="linux-x86_64",
        source_policy=SourcePolicyV1(
            OpaqueIdV1("runtime-policy"), ("linux.proc.process.v1",), (), None
        ),
    )
    assert quota_result.code == "resolved"
    assert runtime_result.code == "capability_schema_incompatible"


def test_retry_metadata_cannot_contradict_failure_state() -> None:
    """M03-PURE-034: retry advice must agree with the outcome state."""
    with pytest.raises(InvalidCollectionOutcome, match="retry_disposition_invalid"):
        CollectionOutcomeV1.failure(
            state="unsupported",
            code="not_supported",
            retry=RetryAdviceV1("after_delay", delay_seconds=30),
        )


@pytest.mark.parametrize(
    ("state", "retry"),
    [
        ("rate_limited", RetryAdviceV1("never")),
        ("blocked_user_action_required", RetryAdviceV1("never")),
        ("provider_unavailable", RetryAdviceV1("after_reauthentication")),
    ],
)
def test_additional_failure_states_reject_contradictory_retry(
    state: str, retry: RetryAdviceV1
) -> None:
    """M03-PURE-034: retry policy remains closed across failure families."""
    with pytest.raises(InvalidCollectionOutcome, match="retry_disposition_invalid"):
        CollectionOutcomeV1.failure(
            state=state,  # type: ignore[arg-type]
            code="safe_failure",
            retry=retry,
        )


def test_retry_delay_metadata_is_present_only_for_delayed_retry() -> None:
    """M03-PURE-034: delay value and disposition are inseparable."""
    with pytest.raises(InvalidProviderContract, match="retry_delay_pair_invalid"):
        RetryAdviceV1("after_delay")
    with pytest.raises(InvalidProviderContract, match="retry_delay_pair_invalid"):
        RetryAdviceV1("never", delay_seconds=30)
