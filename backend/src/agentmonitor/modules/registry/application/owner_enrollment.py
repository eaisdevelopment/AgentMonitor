"""Owner-assisted M02 enrollment for one sanitized M03 discovery outcome."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import DiscoveryOutcomeV1
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    ConfirmIdentityAssociationCommandV1,
    DiscoveryCandidateViewV1,
    DiscoveryReconciliationViewV1,
    MonitoringProfileViewV1,
    PrivateProfileLocatorRefV1,
)
from agentmonitor.modules.registry.application.accounts import (
    AccountRepositoryPortV1,
    ConfirmIdentityAssociationV1,
    EnrollMonitoringGraphCommandV1,
    EnrollMonitoringGraphV1,
)
from agentmonitor.modules.registry.application.discovery import (
    DiscoveryRepositoryPortV1,
    ReconcileProviderDiscoveryV1,
)


class OwnerEnrollmentRepositoryV1(
    AccountRepositoryPortV1, DiscoveryRepositoryPortV1, Protocol
):
    pass


@dataclass(frozen=True, slots=True)
class OwnerConfirmedMonitoringGraphV1:
    reconciliation: DiscoveryReconciliationViewV1
    candidate_before_confirmation: DiscoveryCandidateViewV1
    account: AccountViewV1
    profile: MonitoringProfileViewV1
    resource: AccountResourceViewV1


class EnrollOwnerConfirmedDiscoveryV1:
    """Reconcile, explicitly confirm, and idempotently enroll one candidate."""

    def __init__(self, repository: OwnerEnrollmentRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        outcome: DiscoveryOutcomeV1,
        *,
        reconciled_at: datetime,
        command_id: str,
        principal_id: str,
        expected_provider_key: str,
        friendly_name: str,
        profile_locator: str,
        enrollment_command_id: str,
    ) -> OwnerConfirmedMonitoringGraphV1:
        if (
            outcome.state not in {"success", "partial"}
            or outcome.value is None
            or len(outcome.value.accounts) != 1
            or not outcome.value.accounts[0].owner_confirmation_required
            or not expected_provider_key
        ):
            raise ValueError("registry_owner_discovery_invalid")
        reconciliation = ReconcileProviderDiscoveryV1(self._repository)(
            outcome, reconciled_at=reconciled_at
        )
        candidates = tuple(
            candidate
            for candidate in reconciliation.candidates
            if candidate.provider_key == expected_provider_key
            and candidate.last_seen_at == reconciled_at
        )
        if len(candidates) != 1:
            raise ValueError("registry_owner_discovery_ambiguous")
        candidate = candidates[0]
        principal = OpaqueIdV1(principal_id)
        account = ConfirmIdentityAssociationV1(self._repository)(
            ConfirmIdentityAssociationCommandV1(
                command_id=OpaqueIdV1(command_id),
                principal_id=principal,
                candidate_id=candidate.candidate_id,
                expected_candidate_record_version=candidate.record_version,
                friendly_name=friendly_name,
                organization_id=None,
                evidence_set_digest=candidate.evidence_set_digest,
                requested_at=reconciled_at,
            )
        )
        profile, resource = EnrollMonitoringGraphV1(self._repository)(
            EnrollMonitoringGraphCommandV1(
                command_id=OpaqueIdV1(enrollment_command_id),
                principal_id=principal,
                account_id=account.account_id,
                provider_installation_id=candidate.provider_installation_id,
                purpose="subscription",
                profile_locator_ref=PrivateProfileLocatorRefV1(profile_locator),
                locator_fingerprint=hashlib.sha256(
                    profile_locator.encode("utf-8")
                ).hexdigest(),
                management_state="provider_default",
                compatibility_state="compatible",
                is_protected_default=True,
                resource_kind="subscription_pool",
                parent_resource_id=None,
                requested_at=reconciled_at,
            )
        )
        return OwnerConfirmedMonitoringGraphV1(
            reconciliation,
            candidate,
            account,
            profile,
            resource,
        )
