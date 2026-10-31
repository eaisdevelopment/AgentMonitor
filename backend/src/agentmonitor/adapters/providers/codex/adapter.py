"""Exact-version Codex managed-profile subscription adapter."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.providers.codex.authentication.identity import (
    CodexIdentityFailure,
    read_managed_profile_identity_v1,
)
from agentmonitor.adapters.providers.codex.installation import CodexInstallationV1
from agentmonitor.adapters.providers.codex.manifest import (
    CODEX_ADAPTER_ID,
    CODEX_ADAPTER_VERSION,
    CODEX_APP_SERVER_MECHANISM_VERSION,
    CODEX_PARSER_VERSION,
    CODEX_RATE_LIMITS_SOURCE_ID,
    M0_MAPPING_DIGEST,
    M0_MAPPING_ID,
    build_codex_manifest,
)
from agentmonitor.adapters.providers.codex.subscription.mapper import (
    map_subscription_quota,
)
from agentmonitor.adapters.providers.codex.subscription.source import (
    CodexRateLimitsFailure,
    collect_rate_limits_once_v1,
)
from agentmonitor.adapters.providers.codex.transport import CodexAppServerFailure
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    AdapterDescriptorV1,
    CapabilityManifestV1,
    CapabilitySchemaVersionV1,
    CollectionOutcomeV1,
    ObservedProfileIdentityV1,
    ProviderOperationRequestHeaderV1,
    ProviderTargetV1,
    RetryAdviceV1,
    SourcePolicyV1,
)
from agentmonitor.contracts.providers.codex.subscription_quota.v1.schema import (
    CodexSubscriptionQuotaV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    ResolveAndInvokeProviderCapabilityV1,
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CodexFailureStateV1 = Literal[
    "unverified_provider_version",
    "reauthentication_required",
    "provider_unavailable",
    "invalid_provider_data",
    "deadline_exceeded",
    "blocked_user_action_required",
    "internal_adapter_error",
]

_PROTOCOL_FAILURES = frozenset(
    {
        "codex_app_server_initialize_invalid",
        "codex_app_server_json_depth_exceeded",
        "codex_app_server_message_limit_exceeded",
        "codex_app_server_notification_rejected",
        "codex_app_server_output_too_large",
        "codex_app_server_protocol_invalid",
        "codex_app_server_unexpected_response",
    }
)
_LOCAL_TARGET_FAILURES = frozenset(
    {
        "codex_app_server_request_invalid",
        "codex_managed_profile_unavailable",
        "codex_managed_profile_unsafe",
    }
)


def classify_codex_app_server_failure_v1(
    code: str,
) -> tuple[_CodexFailureStateV1, RetryAdviceV1]:
    """Map one sanitized transport code without inspecting provider text."""
    if code == "codex_app_server_deadline_exceeded":
        return "deadline_exceeded", RetryAdviceV1("never")
    if code == "codex_executable_changed":
        return "unverified_provider_version", RetryAdviceV1("after_version_review")
    if code == "codex_managed_authentication_required":
        return "reauthentication_required", RetryAdviceV1("after_reauthentication")
    if code in _PROTOCOL_FAILURES:
        return "invalid_provider_data", RetryAdviceV1("after_version_review")
    if code in _LOCAL_TARGET_FAILURES:
        return "invalid_provider_data", RetryAdviceV1("never")
    if code in {
        "codex_app_server_cleanup_failed",
        "codex_app_server_pipe_unavailable",
        "codex_app_server_request_failed",
        "codex_app_server_unavailable",
    }:
        return "provider_unavailable", RetryAdviceV1(
            "after_delay", delay_seconds=300, delay_precision="estimated"
        )
    return "internal_adapter_error", RetryAdviceV1("unknown")


class _VerifiedIdentityReceiptSlotV1:
    """Pure one-shot binding for the final identity from one quota request."""

    def __init__(self) -> None:
        self._receipt: (
            tuple[OpaqueIdV1, OpaqueIdV1, ObservedProfileIdentityV1] | None
        ) = None

    def clear(self) -> None:
        self._receipt = None

    def put(
        self,
        operation_id: OpaqueIdV1,
        correlation_id: OpaqueIdV1,
        identity: ObservedProfileIdentityV1,
    ) -> None:
        self._receipt = (operation_id, correlation_id, identity)

    def take(
        self,
        operation_id: OpaqueIdV1,
        correlation_id: OpaqueIdV1,
    ) -> ObservedProfileIdentityV1 | None:
        receipt = self._receipt
        self._receipt = None
        if (
            receipt is None
            or receipt[0] != operation_id
            or receipt[1] != correlation_id
        ):
            return None
        return receipt[2]


class CodexAdapterV1:
    """No-fallback subscription adapter for one verified managed profile."""

    def __init__(
        self,
        installation: CodexInstallationV1,
        *,
        managed_profiles_root: Path,
        managed_profile_root: Path,
        expected_identity_fingerprint: str | None = None,
        identity_matches: Callable[[ObservedProfileIdentityV1], bool] | None = None,
        installation_ref: OpaqueIdV1,
        account_ref: OpaqueIdV1,
        profile_ref: OpaqueIdV1,
        resource_ref: OpaqueIdV1,
        access_grant_ref: OpaqueIdV1,
    ) -> None:
        if (
            identity_matches is None
            and (
                type(expected_identity_fingerprint) is not str
                or _SHA256.fullmatch(expected_identity_fingerprint) is None
            )
        ) or (
            identity_matches is not None and expected_identity_fingerprint is not None
        ):
            raise ValueError("codex_expected_identity_invalid")
        if not all(
            isinstance(value, OpaqueIdV1)
            for value in (
                installation_ref,
                account_ref,
                profile_ref,
                resource_ref,
                access_grant_ref,
            )
        ):
            raise TypeError("codex_target_binding_invalid")
        self._installation = installation
        self._managed_profiles_root = managed_profiles_root
        self._managed_profile_root = managed_profile_root
        self._expected_identity_fingerprint = expected_identity_fingerprint
        self._identity_matches = identity_matches
        self._account_ref = account_ref
        self._resource_ref = resource_ref
        self._manifest = build_codex_manifest()
        self._target = ProviderTargetV1(
            provider_key="codex",
            installation_ref=installation_ref,
            account_ref=account_ref,
            profile_ref=profile_ref,
            resource_ref=resource_ref,
            profile_protection="managed",
        )
        self._source_policy = SourcePolicyV1(
            policy_ref=OpaqueIdV1("codex-rate-limits-source-policy"),
            source_ids=(CODEX_RATE_LIMITS_SOURCE_ID,),
            approved_fallbacks=(),
            experimental_grant_ref=OpaqueIdV1(
                "codex-app-server-0-160-0-experimental-grant"
            ),
        )
        self._access_grant_refs = (access_grant_ref,)
        self._verified_identity_receipts = _VerifiedIdentityReceiptSlotV1()
        self._gateway = ResolveAndInvokeProviderCapabilityV1[CodexSubscriptionQuotaV1](
            approved_mapping_digest=M0_MAPPING_DIGEST
        )

    @property
    def descriptor(self) -> AdapterDescriptorV1:
        return self._manifest.descriptor

    @property
    def manifest(self) -> CapabilityManifestV1:
        return self._manifest

    def take_verified_identity(
        self,
        *,
        operation_id: OpaqueIdV1,
        correlation_id: OpaqueIdV1,
    ) -> ObservedProfileIdentityV1 | None:
        """Consume the final identity from one exact successful quota request."""
        return self._verified_identity_receipts.take(operation_id, correlation_id)

    def subscription_request(
        self,
        *,
        operation_id: str,
        correlation_id: str,
        requested_at: datetime,
    ) -> ProviderOperationRequestHeaderV1:
        """Build the one admitted experimental managed-profile request."""
        return ProviderOperationRequestHeaderV1(
            operation_id=OpaqueIdV1(operation_id),
            correlation_id=OpaqueIdV1(correlation_id),
            provider_key="codex",
            capability_id="subscription.quota",
            capability_schema_version=CapabilitySchemaVersionV1(1, 0),
            target=self._target,
            requested_at=requested_at,
            deadline_ms=30_000,
            source_policy=self._source_policy,
            access_grant_refs=self._access_grant_refs,
        )

    def collect_subscription_quota(
        self, request: ProviderOperationRequestHeaderV1
    ) -> CollectionOutcomeV1[CodexSubscriptionQuotaV1]:
        """Resolve the exact tuple before any provider-owned child is started."""
        self._verified_identity_receipts.clear()
        return self._gateway(
            manifest=self._manifest,
            request=request,
            provider_version=self._installation.provider_version,
            platform_id=self._installation.platform_id,
            invoke=self._collect_resolved,
        )

    def _collect_resolved(
        self, request: ProviderOperationRequestHeaderV1
    ) -> CollectionOutcomeV1[CodexSubscriptionQuotaV1]:
        if (
            request.provider_key != "codex"
            or request.capability_id != "subscription.quota"
            or request.capability_schema_version != CapabilitySchemaVersionV1(1, 0)
            or request.target != self._target
            or request.deadline_ms != 30_000
            or request.source_policy != self._source_policy
            or request.access_grant_refs != self._access_grant_refs
        ):
            return self._failure(
                "invalid_provider_data",
                "codex_request_binding_mismatch",
                RetryAdviceV1("never"),
            )
        operation_deadline = time.monotonic() + request.deadline_ms / 1000
        try:
            identity_before = read_managed_profile_identity_v1(
                self._installation,
                managed_profiles_root=self._managed_profiles_root,
                managed_profile_root=self._managed_profile_root,
                deadline_monotonic=operation_deadline,
            )
        except CodexAppServerFailure as error:
            state, retry = classify_codex_app_server_failure_v1(error.code)
            return self._failure(state, error.code, retry)
        except CodexIdentityFailure:
            return self._failure(
                "invalid_provider_data",
                "codex_identity_invalid",
                RetryAdviceV1("after_version_review"),
            )
        if identity_before is None:
            return self._failure(
                "reauthentication_required",
                "codex_managed_authentication_required",
                RetryAdviceV1("after_reauthentication"),
            )
        try:
            identity_before_matches = (
                identity_before.fingerprint == self._expected_identity_fingerprint
                if self._identity_matches is None
                else self._identity_matches(identity_before)
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return self._failure(
                "internal_adapter_error",
                "codex_identity_binding_unavailable",
                RetryAdviceV1("unknown"),
            )
        if not identity_before_matches:
            return self._failure(
                "blocked_user_action_required",
                "codex_managed_identity_mismatch",
                RetryAdviceV1("after_user_action"),
            )

        try:
            source = collect_rate_limits_once_v1(
                self._installation,
                managed_profiles_root=self._managed_profiles_root,
                managed_profile_root=self._managed_profile_root,
                expected_identity_fingerprint=identity_before.fingerprint,
                deadline_monotonic=operation_deadline,
            )
            observed_at = datetime.now(UTC)
            identity_after = read_managed_profile_identity_v1(
                self._installation,
                managed_profiles_root=self._managed_profiles_root,
                managed_profile_root=self._managed_profile_root,
                deadline_monotonic=operation_deadline,
            )
        except CodexRateLimitsFailure as error:
            if error.code == "codex_quota_identity_mismatch":
                return self._failure(
                    "blocked_user_action_required",
                    error.code,
                    RetryAdviceV1("after_user_action"),
                )
            return self._failure(
                "invalid_provider_data",
                error.code,
                RetryAdviceV1("after_version_review"),
            )
        except CodexAppServerFailure as error:
            state, retry = classify_codex_app_server_failure_v1(error.code)
            return self._failure(state, error.code, retry)
        except CodexIdentityFailure:
            return self._failure(
                "invalid_provider_data",
                "codex_identity_invalid",
                RetryAdviceV1("after_version_review"),
            )
        if (
            identity_after is None
            or identity_after.fingerprint != identity_before.fingerprint
        ):
            return self._failure(
                "blocked_user_action_required",
                "codex_managed_identity_changed",
                RetryAdviceV1("after_user_action"),
            )
        try:
            identity_after_matches = (
                identity_after.fingerprint == self._expected_identity_fingerprint
                if self._identity_matches is None
                else self._identity_matches(identity_after)
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return self._failure(
                "internal_adapter_error",
                "codex_identity_binding_unavailable",
                RetryAdviceV1("unknown"),
            )
        if not identity_after_matches:
            return self._failure(
                "blocked_user_action_required",
                "codex_managed_identity_changed",
                RetryAdviceV1("after_user_action"),
            )

        collected_at = datetime.now(UTC)
        value = map_subscription_quota(
            source,
            account_ref=self._account_ref,
            resource_ref=self._resource_ref,
        )
        provenance = ObservationProvenanceV1(
            provider_key="codex",
            capability_id="subscription.quota",
            capability_schema_version="1.0",
            adapter_id=CODEX_ADAPTER_ID,
            adapter_version=CODEX_ADAPTER_VERSION,
            provider_protocol_version="1.0.0",
            source_id=CODEX_RATE_LIMITS_SOURCE_ID,
            source_class="experimental_private_or_browser",
            mechanism_version=CODEX_APP_SERVER_MECHANISM_VERSION,
            parser_version=CODEX_PARSER_VERSION,
            provider_version=self._installation.provider_version,
            provider_version_availability=FieldAvailabilityV1("available"),
            observed_at=observed_at,
            observed_at_availability=FieldAvailabilityV1("available"),
            collected_at=collected_at,
            freshness_deadline=observed_at + timedelta(minutes=5),
            freshness_availability=FieldAvailabilityV1("available"),
            freshness_policy_id="codex-rate-limits-five-minute-v1",
            precision="exact",
            confidence="confirmed",
            confidence_reason_code="provider_reported_rate_limit_windows",
            value_kind="provider_reported",
            is_experimental=True,
            fallback_lineage=(),
            warnings=(),
            operation_id=request.operation_id,
            correlation_id=request.correlation_id,
            decision_reference=M0_MAPPING_ID,
            derivation_method=None,
            input_observation_ids=(),
        )
        outcome = CollectionOutcomeV1.success(value, provenance)
        self._verified_identity_receipts.put(
            request.operation_id,
            request.correlation_id,
            identity_after,
        )
        return outcome

    @staticmethod
    def _failure(
        state: _CodexFailureStateV1,
        code: str,
        retry: RetryAdviceV1,
    ) -> CollectionOutcomeV1[CodexSubscriptionQuotaV1]:
        return CollectionOutcomeV1.failure(
            state=state,
            code=code,
            retry=retry,
        )
