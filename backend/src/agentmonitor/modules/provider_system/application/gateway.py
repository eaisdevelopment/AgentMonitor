"""Pure validation gateway around an already supplied typed provider port."""

from collections.abc import Callable

from agentmonitor.contracts import provider_system_v1 as provider_contracts
from agentmonitor.contracts.common_v1 import TechnicalValueV1
from agentmonitor.modules.provider_system.domain.protocol import (
    CapabilityResolutionV1,
    manifest_fingerprint,
    resolve_capability,
)


def get_manifest_fingerprint_v1(
    manifest: provider_contracts.CapabilityManifestV1,
) -> str:
    """Publish the canonical M03 manifest digest through application scope."""
    return manifest_fingerprint(manifest)


def _invalid_outcome[ResultT: TechnicalValueV1](
    code: str,
) -> provider_contracts.CollectionOutcomeV1[ResultT]:
    return provider_contracts.CollectionOutcomeV1.failure(
        state="invalid_provider_data",
        code=code,
        retry=provider_contracts.RetryAdviceV1("never"),
    )


def validate_collection_outcome_v1[ResultT: TechnicalValueV1](
    *,
    resolution: CapabilityResolutionV1,
    request: provider_contracts.ProviderOperationRequestHeaderV1,
    provider_version: str,
    outcome: provider_contracts.CollectionOutcomeV1[ResultT],
) -> provider_contracts.CollectionOutcomeV1[ResultT]:
    """Validate a constructed typed envelope against its pure resolution."""
    if resolution.code != "resolved" or resolution.selected_source is None:
        return _invalid_outcome("unresolved_outcome_validation")
    if outcome.state in {"success", "partial"}:
        provenance = outcome.provenance
        assert provenance is not None
        assert resolution.declaration is not None
        assert resolution.source_policy is not None
        policy_source_ids = resolution.source_policy.source_ids
        try:
            actual_source_position = policy_source_ids.index(provenance.source_id)
            actual_source = next(
                source
                for source in resolution.declaration.sources
                if source.source_id == provenance.source_id
            )
        except (StopIteration, ValueError):
            return _invalid_outcome("provider_outcome_provenance_mismatch")
        expected_fallback_sources = policy_source_ids[:actual_source_position]
        fallback_lineage_matches = len(provenance.fallback_lineage) == len(
            expected_fallback_sources
        )
        if fallback_lineage_matches:
            transitions = {
                (transition.from_source_id, transition.to_source_id): transition
                for transition in resolution.source_policy.approved_fallbacks
            }
            for position, fallback_attempt in enumerate(provenance.fallback_lineage):
                transition = transitions.get(
                    (
                        expected_fallback_sources[position],
                        policy_source_ids[position + 1],
                    )
                )
                if (
                    fallback_attempt.source_id != expected_fallback_sources[position]
                    or transition is None
                    or fallback_attempt.failure_code
                    not in transition.permitted_failure_codes
                ):
                    fallback_lineage_matches = False
                    break
        if (
            provenance.provider_key != request.provider_key
            or provenance.capability_id != request.capability_id
            or provenance.source_class != actual_source.source_class
            or provenance.mechanism_version != actual_source.mechanism_version
            or provenance.is_experimental != actual_source.is_experimental
            or not fallback_lineage_matches
            or provenance.provider_version != provider_version
            or provenance.operation_id != request.operation_id
            or provenance.correlation_id != request.correlation_id
        ):
            return _invalid_outcome("provider_outcome_provenance_mismatch")
    return outcome


class ResolveAndInvokeProviderCapabilityV1[ResultT: TechnicalValueV1]:
    """Fail closed before invoking a typed port, then validate its envelope."""

    def __init__(self, *, approved_mapping_digest: str) -> None:
        self._approved_mapping_digest = approved_mapping_digest

    def __call__(
        self,
        *,
        manifest: provider_contracts.CapabilityManifestV1,
        request: provider_contracts.ProviderOperationRequestHeaderV1,
        provider_version: str,
        platform_id: str,
        invoke: Callable[
            [provider_contracts.ProviderOperationRequestHeaderV1],
            provider_contracts.CollectionOutcomeV1[ResultT],
        ],
    ) -> provider_contracts.CollectionOutcomeV1[ResultT]:
        if request.provider_key != manifest.descriptor.provider_key:
            return _invalid_outcome("request_provider_mismatch")
        resolution = resolve_capability(
            manifest,
            approved_mapping_digest=self._approved_mapping_digest,
            host_protocol_version="1.0.0",
            capability_id=request.capability_id,
            capability_schema_version=request.capability_schema_version,
            provider_version=provider_version,
            platform_id=platform_id,
            source_policy=request.source_policy,
        )
        if resolution.code != "resolved":
            return self._resolution_failure(resolution.code)
        assert resolution.declaration is not None
        assert resolution.selected_source is not None
        if request.deadline_ms > resolution.declaration.constraints.deadline_ms:
            return _invalid_outcome("request_deadline_exceeds_manifest")
        try:
            outcome = invoke(request)
        except Exception:
            return provider_contracts.CollectionOutcomeV1.failure(
                state="internal_adapter_error",
                code="adapter_boundary_exception",
                retry=provider_contracts.RetryAdviceV1("unknown"),
            )
        return validate_collection_outcome_v1(
            resolution=resolution,
            request=request,
            provider_version=provider_version,
            outcome=outcome,
        )

    @staticmethod
    def _resolution_failure(
        code: str,
    ) -> provider_contracts.CollectionOutcomeV1[ResultT]:
        mapping = {
            "provider_version_unverified": (
                "unverified_provider_version",
                "after_version_review",
            ),
            "unsupported": ("unsupported", "never"),
            "capability_disabled": ("unsupported", "never"),
            "capability_not_declared": ("unsupported", "never"),
            "source_policy_unapproved": ("unsupported", "never"),
            "protocol_incompatible": (
                "unverified_provider_version",
                "after_version_review",
            ),
            "capability_schema_incompatible": (
                "unverified_provider_version",
                "after_version_review",
            ),
            "platform_unsupported": ("unsupported", "never"),
            "mapping_binding_invalid": ("invalid_provider_data", "never"),
        }
        state, retry = mapping[code]
        return provider_contracts.CollectionOutcomeV1.failure(
            state=state,  # type: ignore[arg-type]
            code=code,
            retry=provider_contracts.RetryAdviceV1(retry),  # type: ignore[arg-type]
        )
