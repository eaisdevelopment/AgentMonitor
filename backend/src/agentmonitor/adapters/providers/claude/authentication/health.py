"""Read-only Claude authentication health over the accepted ``/usage`` source.

The source deliberately reports only whether the authenticated Claude shell can
produce its allowlisted usage view.  It does not infer account identity from a
display name and it never accepts a profile path, credential, or raw provider
payload.  Managed-profile reauthentication is a separate, fail-closed module.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from agentmonitor.adapters.providers.claude.installation import ClaudeInstallationV1
from agentmonitor.adapters.providers.claude.manifest import (
    CLAUDE_ADAPTER_ID,
    CLAUDE_ADAPTER_VERSION,
    CLAUDE_PARSER_VERSION,
    CLAUDE_USAGE_SOURCE_ID,
)
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1
from agentmonitor.contracts.provider_system_v1 import (
    AuthHealthObservationV1,
    AuthHealthOutcomeV1,
    IdentityComparisonV1,
    ProviderOperationRequestHeaderV1,
    RetryAdviceV1,
)

if TYPE_CHECKING:
    from agentmonitor.adapters.providers.claude.subscription.source import (
        ClaudeUsageSourceFailure,
    )


def _failure_outcome(failure: "ClaudeUsageSourceFailure") -> AuthHealthOutcomeV1:
    retry = {
        "reauthentication_required": "after_reauthentication",
        "authorization_insufficient": "after_user_action",
        "provider_unavailable": "never",
        "invalid_provider_data": "never",
        "deadline_exceeded": "never",
        "blocked_user_action_required": "after_user_action",
    }[failure.state]
    return AuthHealthOutcomeV1.failure(
        state=failure.state,
        code=failure.code,
        retry=RetryAdviceV1(retry),  # type: ignore[arg-type]
    )


def _provenance(
    installation: ClaudeInstallationV1,
    request: ProviderOperationRequestHeaderV1,
    *,
    observed_at: datetime,
    collected_at: datetime,
) -> ObservationProvenanceV1:
    return ObservationProvenanceV1(
        provider_key="claude",
        capability_id="authentication.health",
        capability_schema_version="1.0",
        adapter_id=CLAUDE_ADAPTER_ID,
        adapter_version=CLAUDE_ADAPTER_VERSION,
        provider_protocol_version="1.0.0",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        source_class="supported_cli",
        mechanism_version="1",
        parser_version=CLAUDE_PARSER_VERSION,
        provider_version=installation.provider_version,
        provider_version_availability=FieldAvailabilityV1("available"),
        observed_at=observed_at,
        observed_at_availability=FieldAvailabilityV1("available"),
        collected_at=collected_at,
        freshness_deadline=observed_at + timedelta(minutes=5),
        freshness_availability=FieldAvailabilityV1("available"),
        freshness_policy_id="claude-auth-health-five-minute-v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="provider_usage_view_opened",
        value_kind="provider_reported",
        is_experimental=False,
        fallback_lineage=(),
        warnings=(),
        operation_id=request.operation_id,
        correlation_id=request.correlation_id,
        decision_reference="M0-M3-CLAUDE-EVIDENCE-001",
        derivation_method=None,
        input_observation_ids=(),
    )


@dataclass(frozen=True, slots=True)
class ClaudeAuthenticationHealthV1:
    """Invoke one real, bounded, read-only default-profile health observation."""

    installation: ClaudeInstallationV1

    def __call__(
        self, request: ProviderOperationRequestHeaderV1
    ) -> AuthHealthOutcomeV1:
        if (
            request.provider_key != "claude"
            or request.target.provider_key != "claude"
            or request.capability_id != "authentication.health"
            or request.target.profile_protection != "protected_default"
            or tuple(request.source_policy.source_ids) != (CLAUDE_USAGE_SOURCE_ID,)
        ):
            return AuthHealthOutcomeV1.failure(
                state="unsupported",
                code="claude_auth_health_target_unsupported",
                retry=RetryAdviceV1("never"),
            )
        from agentmonitor.adapters.providers.claude.subscription.source import (
            ClaudeUsageSourceFailure,
            collect_usage_once,
        )

        result = collect_usage_once(
            self.installation.executable_for_adapter,
            deadline_ms=request.deadline_ms,
        )
        if isinstance(result, ClaudeUsageSourceFailure):
            return _failure_outcome(result)
        provenance = _provenance(
            self.installation,
            request,
            observed_at=result.observed_at,
            collected_at=result.collected_at,
        )
        return AuthHealthOutcomeV1.success(
            AuthHealthObservationV1(
                state="healthy",
                provenance=provenance,
                expires_at=None,
                expiry_precision="unknown",
                reason_code="claude_usage_view_opened",
                identity=IdentityComparisonV1(
                    "unresolved", "identity_assertion_unavailable"
                ),
            ),
            provenance,
        )
