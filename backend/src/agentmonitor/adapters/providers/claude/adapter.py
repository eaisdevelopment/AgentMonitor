"""Production Claude adapter for the exact accepted subscription quota lane."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.providers.claude.authentication.identity import (
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import ClaudeInstallationV1
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_ID,
    CLAUDE_ADAPTER_VERSION,
    CLAUDE_PARSER_VERSION,
    CLAUDE_QUOTA_DECISION_REFERENCE,
    M0_MAPPING_DIGEST,
    build_claude_manifest,
)
from agentmonitor.adapters.providers.claude.subscription.mapper import (
    map_subscription_quota,
)
from agentmonitor.adapters.providers.claude.subscription.source import (
    ClaudeUsageSourceFailure,
    collect_usage_once,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    AdapterDescriptorV1,
    CapabilityManifestV1,
    CapabilitySchemaVersionV1,
    CollectionOutcomeV1,
    DiscoveredAccountCandidateV1,
    DiscoveredInstallationV1,
    DiscoveryCandidatesV1,
    DiscoveryOutcomeV1,
    MissingFieldV1,
    ProviderOperationRequestHeaderV1,
    ProviderTargetV1,
    RetryAdviceV1,
    SanitizedWarningV1,
    SourcePolicyV1,
)
from agentmonitor.contracts.providers.claude.subscription_quota.v1.schema import (
    ClaudeSubscriptionQuotaV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    ResolveAndInvokeProviderCapabilityV1,
)


class ClaudeAdapterV1:
    """Statically composed, no-fallback Claude subscription adapter."""

    def __init__(
        self,
        installation: ClaudeInstallationV1,
        *,
        managed_profile_root: Path | None = None,
        expected_identity_fingerprint: str | None = None,
    ) -> None:
        self._installation = installation
        self._managed_profile_root = managed_profile_root
        self._expected_identity_fingerprint = expected_identity_fingerprint
        self._manifest = build_claude_manifest()
        self._gateway = ResolveAndInvokeProviderCapabilityV1[ClaudeSubscriptionQuotaV1](
            approved_mapping_digest=M0_MAPPING_DIGEST
        )

    @property
    def descriptor(self) -> AdapterDescriptorV1:
        return self._manifest.descriptor

    @property
    def manifest(self) -> CapabilityManifestV1:
        return self._manifest

    def collect_subscription_quota(
        self, request: ProviderOperationRequestHeaderV1
    ) -> CollectionOutcomeV1[ClaudeSubscriptionQuotaV1]:
        """Resolve the exact tuple before the single live invocation."""
        return self._gateway(
            manifest=self._manifest,
            request=request,
            provider_version=self._installation.provider_version,
            platform_id=self._installation.platform_id,
            invoke=self._collect_resolved,
        )

    def __call__(self, request: ProviderOperationRequestHeaderV1) -> DiscoveryOutcomeV1:
        """Discover one opaque account candidate from a fresh real quota read.

        The subscription values are deliberately discarded here. The caller
        receives only the owner-supplied opaque target and the verified local
        installation, and M02 still requires an explicit owner confirmation
        before it can create an account.
        """
        outcome = self.collect_subscription_quota(request)
        if outcome.state not in {"success", "partial"}:
            if outcome.error is None:
                raise ValueError("claude_discovery_outcome_invalid")
            error = outcome.error
            if outcome.state == "unsupported":
                return DiscoveryOutcomeV1.failure(
                    state="unsupported", code=error.code, retry=error.retry
                )
            if outcome.state == "unverified_provider_version":
                return DiscoveryOutcomeV1.failure(
                    state="unverified_provider_version",
                    code=error.code,
                    retry=error.retry,
                )
            if outcome.state == "reauthentication_required":
                return DiscoveryOutcomeV1.failure(
                    state="reauthentication_required",
                    code=error.code,
                    retry=error.retry,
                )
            if outcome.state == "authorization_insufficient":
                return DiscoveryOutcomeV1.failure(
                    state="authorization_insufficient",
                    code=error.code,
                    retry=error.retry,
                )
            if outcome.state == "provider_unavailable":
                return DiscoveryOutcomeV1.failure(
                    state="provider_unavailable", code=error.code, retry=error.retry
                )
            if outcome.state == "rate_limited":
                return DiscoveryOutcomeV1.failure(
                    state="rate_limited", code=error.code, retry=error.retry
                )
            if outcome.state == "invalid_provider_data":
                return DiscoveryOutcomeV1.failure(
                    state="invalid_provider_data", code=error.code, retry=error.retry
                )
            if outcome.state == "deadline_exceeded":
                return DiscoveryOutcomeV1.failure(
                    state="deadline_exceeded", code=error.code, retry=error.retry
                )
            if outcome.state == "blocked_user_action_required":
                return DiscoveryOutcomeV1.failure(
                    state="blocked_user_action_required",
                    code=error.code,
                    retry=error.retry,
                )
            if outcome.state == "internal_adapter_error":
                return DiscoveryOutcomeV1.failure(
                    state="internal_adapter_error", code=error.code, retry=error.retry
                )
            raise ValueError("claude_discovery_outcome_invalid")
        if request.target.account_ref is None or outcome.provenance is None:
            return DiscoveryOutcomeV1.failure(
                state="invalid_provider_data",
                code="claude_discovery_target_incomplete",
                retry=RetryAdviceV1("never"),
            )
        candidates = DiscoveryCandidatesV1(
            installations=(
                DiscoveredInstallationV1(
                    provider_key="claude",
                    installation_ref=self._installation.installation_ref,
                    product_version=self._installation.provider_version,
                    platform_id=self._installation.platform_id,
                    provenance=outcome.provenance,
                ),
            ),
            accounts=(
                DiscoveredAccountCandidateV1(
                    candidate_ref=request.target.account_ref,
                    installation_ref=self._installation.installation_ref,
                    evidence_strength="owner_confirmation_required",
                    owner_confirmation_required=True,
                    provenance=outcome.provenance,
                ),
            ),
        )
        return DiscoveryOutcomeV1.success(candidates, outcome.provenance)

    def discover_owner_confirmed_default(
        self,
        *,
        operation_id: str,
        correlation_id: str,
        account_ref: str,
        profile_ref: str,
        resource_ref: str,
    ) -> DiscoveryOutcomeV1:
        """Invoke discovery for the exact owner-approved opaque target tuple."""
        return self(
            self.subscription_request(
                operation_id=operation_id,
                correlation_id=correlation_id,
                installation_ref=self._installation.installation_ref.value,
                account_ref=account_ref,
                profile_ref=profile_ref,
                resource_ref=resource_ref,
                requested_at=datetime.now(UTC),
            )
        )

    def subscription_request(
        self,
        *,
        operation_id: str,
        correlation_id: str,
        installation_ref: str,
        account_ref: str,
        profile_ref: str,
        resource_ref: str,
        requested_at: datetime,
    ) -> ProviderOperationRequestHeaderV1:
        """Build the exact admitted quota request without exposing locators."""
        return ProviderOperationRequestHeaderV1(
            operation_id=OpaqueIdV1(operation_id),
            correlation_id=OpaqueIdV1(correlation_id),
            provider_key="claude",
            capability_id="subscription.quota",
            capability_schema_version=CapabilitySchemaVersionV1(1, 0),
            target=ProviderTargetV1(
                provider_key="claude",
                installation_ref=OpaqueIdV1(installation_ref),
                account_ref=OpaqueIdV1(account_ref),
                profile_ref=OpaqueIdV1(profile_ref),
                resource_ref=OpaqueIdV1(resource_ref),
                profile_protection="managed"
                if self._managed_profile_root is not None
                else "protected_default",
            ),
            requested_at=requested_at,
            deadline_ms=30_000,
            source_policy=SourcePolicyV1(
                policy_ref=OpaqueIdV1("claude-usage-source-policy"),
                source_ids=(self._manifest.declarations[0].sources[0].source_id,),
                approved_fallbacks=(),
                experimental_grant_ref=None,
            ),
            access_grant_refs=(
                OpaqueIdV1(
                    "claude-managed-profile-read-only"
                    if self._managed_profile_root is not None
                    else "claude-default-profile-read-only"
                ),
            ),
        )

    def _collect_resolved(
        self, request: ProviderOperationRequestHeaderV1
    ) -> CollectionOutcomeV1[ClaudeSubscriptionQuotaV1]:
        expected_protection = (
            "managed" if self._managed_profile_root is not None else "protected_default"
        )
        if request.target.profile_protection != expected_protection:
            return CollectionOutcomeV1.failure(
                state="invalid_provider_data",
                code="claude_profile_target_mismatch",
                retry=RetryAdviceV1("never"),
            )
        if request.target.account_ref is None or request.target.resource_ref is None:
            return CollectionOutcomeV1.failure(
                state="invalid_provider_data",
                code="claude_quota_target_incomplete",
                retry=RetryAdviceV1("never"),
            )
        identity_before = None
        if self._managed_profile_root is not None:
            identity_before = read_default_profile_identity_v1(
                self._installation, managed_profile_root=self._managed_profile_root
            )
            if identity_before is None or (
                self._expected_identity_fingerprint is not None
                and identity_before.fingerprint != self._expected_identity_fingerprint
            ):
                return CollectionOutcomeV1.failure(
                    state="blocked_user_action_required",
                    code="claude_managed_identity_mismatch",
                    retry=RetryAdviceV1("after_user_action"),
                )
        result = collect_usage_once(
            self._installation.executable_for_adapter,
            deadline_ms=request.deadline_ms,
            managed_profile_root=self._managed_profile_root,
        )
        if isinstance(result, ClaudeUsageSourceFailure):
            retry = {
                "reauthentication_required": "after_reauthentication",
                "authorization_insufficient": "after_user_action",
                "provider_unavailable": "never",
                "invalid_provider_data": "never",
                "deadline_exceeded": "never",
                "blocked_user_action_required": "after_user_action",
            }[result.state]
            return CollectionOutcomeV1.failure(
                state=result.state,
                code=result.code,
                retry=RetryAdviceV1(retry),  # type: ignore[arg-type]
            )
        if self._managed_profile_root is not None:
            identity_after = read_default_profile_identity_v1(
                self._installation, managed_profile_root=self._managed_profile_root
            )
            if (
                identity_before is None
                or identity_after is None
                or identity_before.fingerprint != identity_after.fingerprint
            ):
                return CollectionOutcomeV1.failure(
                    state="blocked_user_action_required",
                    code="claude_managed_identity_changed",
                    retry=RetryAdviceV1("after_user_action"),
                )
        value = map_subscription_quota(
            result,
            account_ref=request.target.account_ref,
            resource_ref=request.target.resource_ref,
        )
        provenance = ObservationProvenanceV1(
            provider_key="claude",
            capability_id="subscription.quota",
            capability_schema_version="1.0",
            adapter_id=CLAUDE_ADAPTER_ID,
            adapter_version=CLAUDE_ADAPTER_VERSION,
            provider_protocol_version="1.0.0",
            source_id=request.source_policy.source_ids[0],
            source_class="supported_cli",
            mechanism_version="1",
            parser_version=CLAUDE_PARSER_VERSION,
            provider_version=self._installation.provider_version,
            provider_version_availability=FieldAvailabilityV1("available"),
            observed_at=result.observed_at,
            observed_at_availability=FieldAvailabilityV1("available"),
            collected_at=result.collected_at,
            freshness_deadline=result.observed_at + timedelta(minutes=5),
            freshness_availability=FieldAvailabilityV1("available"),
            freshness_policy_id="claude-usage-five-minute-v1",
            precision="rounded",
            confidence="confirmed",
            confidence_reason_code="provider_reported_usage_view",
            value_kind="provider_reported",
            is_experimental=False,
            fallback_lineage=(),
            warnings=result.omission_codes,
            operation_id=request.operation_id,
            correlation_id=request.correlation_id,
            decision_reference=CLAUDE_QUOTA_DECISION_REFERENCE,
            derivation_method=None,
            input_observation_ids=(),
        )
        if result.omission_codes:
            return CollectionOutcomeV1.partial(
                value,
                omissions=tuple(
                    MissingFieldV1(
                        code,
                        FieldAvailabilityV1(
                            "unknown"
                            if code == "claude_current_session_not_reported"
                            else "unsupported"
                        ),
                    )
                    for code in result.omission_codes
                ),
                warnings=tuple(
                    SanitizedWarningV1(code) for code in result.omission_codes
                ),
                provenance=provenance,
            )
        return CollectionOutcomeV1.success(value, provenance)
