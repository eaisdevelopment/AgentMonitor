"""Production Claude adapter for the exact accepted subscription quota lane."""

from datetime import timedelta

from agentmonitor.adapters.providers.claude.installation import ClaudeInstallationV1
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_ID,
    CLAUDE_ADAPTER_VERSION,
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
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.provider_system_v1 import (
    AdapterDescriptorV1,
    CapabilityManifestV1,
    CollectionOutcomeV1,
    ProviderOperationRequestHeaderV1,
    RetryAdviceV1,
)
from agentmonitor.contracts.providers.claude.subscription_quota.v1.schema import (
    ClaudeSubscriptionQuotaV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    ResolveAndInvokeProviderCapabilityV1,
)


class ClaudeAdapterV1:
    """Statically composed, no-fallback Claude subscription adapter."""

    def __init__(self, installation: ClaudeInstallationV1) -> None:
        self._installation = installation
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

    def _collect_resolved(
        self, request: ProviderOperationRequestHeaderV1
    ) -> CollectionOutcomeV1[ClaudeSubscriptionQuotaV1]:
        if request.target.account_ref is None or request.target.resource_ref is None:
            return CollectionOutcomeV1.failure(
                state="invalid_provider_data",
                code="claude_quota_target_incomplete",
                retry=RetryAdviceV1("never"),
            )
        result = collect_usage_once(
            self._installation.executable_for_adapter,
            deadline_ms=request.deadline_ms,
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
            parser_version="1.0.0",
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
            warnings=(),
            operation_id=request.operation_id,
            correlation_id=request.correlation_id,
            decision_reference="M0-M3-CLAUDE-ACCEPTANCE-001",
            derivation_method=None,
            input_observation_ids=(),
        )
        return CollectionOutcomeV1.success(value, provenance)
