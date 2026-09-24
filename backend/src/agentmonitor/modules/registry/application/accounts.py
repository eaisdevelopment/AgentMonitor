"""M02 account confirmation and normalized profile/resource graph use cases."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.contracts.registry_v1 import (
    AccountResourceViewV1,
    AccountViewV1,
    ConfirmProviderIdentityFingerprintCommandV1,
    MonitoringProfileViewV1,
    PrivateProfileLocatorRefV1,
    ProfileCompatibilityStateV1,
    ProfileManagementStateV1,
    ProfilePurposeV1,
    ProviderIdentityResolutionV1,
    RegistryScopeKindV1,
    RegistryScopeSnapshotV1,
    ResolveProviderIdentityFingerprintQueryV1,
    ResourceKindV1,
)
from agentmonitor.contracts.registry_v1 import (
    ConfirmIdentityAssociationCommandV1 as ConfirmIdentityAssociationCommandV1,
)
from agentmonitor.contracts.registry_v1 import (
    ConfirmIdentityAssociationV1 as ConfirmIdentityAssociationPortV1,
)
from agentmonitor.contracts.registry_v1 import (
    RegisterAccountV1 as RegisterAccountPortV1,
)
from agentmonitor.modules.registry.domain import account as account_policy

RegistryPolicyErrorV1 = account_policy.RegistryPolicyErrorV1
decide_account_monitoring = account_policy.decide_account_monitoring
decide_candidate_evidence_transition = (
    account_policy.decide_candidate_evidence_transition
)
decide_command_replay = account_policy.decide_command_replay
decide_provider_identity_confirmation = (
    account_policy.decide_provider_identity_confirmation
)
ensure_candidate_confirmation_is_current = (
    account_policy.ensure_candidate_confirmation_is_current
)
safe_registry_event_projection = account_policy.safe_registry_event_projection


class RegistryQueryUnavailableV1(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EnrollMonitoringGraphCommandV1:
    """Internal command containing a deliberately non-serializable locator."""

    command_id: OpaqueIdV1
    principal_id: OpaqueIdV1
    account_id: OpaqueIdV1
    provider_installation_id: OpaqueIdV1
    purpose: ProfilePurposeV1
    profile_locator_ref: PrivateProfileLocatorRefV1
    locator_fingerprint: str
    management_state: ProfileManagementStateV1
    compatibility_state: ProfileCompatibilityStateV1
    is_protected_default: bool
    resource_kind: ResourceKindV1
    parent_resource_id: OpaqueIdV1 | None
    requested_at: datetime

    def __post_init__(self) -> None:
        if (
            len(self.locator_fingerprint) != 64
            or any(
                value not in "0123456789abcdef" for value in self.locator_fingerprint
            )
            or type(self.is_protected_default) is not bool
            or self.is_protected_default
            != (self.management_state == "provider_default")
            or self.requested_at.utcoffset() != timedelta(0)
        ):
            raise ValueError("registry_monitoring_graph_command_invalid")


class AccountRepositoryPortV1(Protocol):
    def confirm_identity(
        self, command: ConfirmIdentityAssociationCommandV1
    ) -> AccountViewV1: ...

    def confirm_provider_identity_fingerprint(
        self, command: ConfirmProviderIdentityFingerprintCommandV1
    ) -> ProviderIdentityResolutionV1: ...

    def resolve_provider_identity_fingerprint(
        self, query: ResolveProviderIdentityFingerprintQueryV1
    ) -> ProviderIdentityResolutionV1: ...

    def enroll_monitoring_graph(
        self, command: EnrollMonitoringGraphCommandV1
    ) -> tuple[MonitoringProfileViewV1, AccountResourceViewV1]: ...

    def list_accounts(
        self,
        provider_key: str | None = None,
        page_size: int = 100,
        after_key: str | None = None,
    ) -> tuple[AccountViewV1, ...]: ...

    def list_monitoring_profiles(
        self, account_id: OpaqueIdV1
    ) -> tuple[MonitoringProfileViewV1, ...]: ...

    def list_account_resources(
        self, account_id: OpaqueIdV1
    ) -> tuple[AccountResourceViewV1, ...]: ...

    def get_registry_scope_snapshot(
        self, scope_kind: RegistryScopeKindV1, scope_id: OpaqueIdV1 | None
    ) -> RegistryScopeSnapshotV1: ...


class ConfirmIdentityAssociationV1(ConfirmIdentityAssociationPortV1):
    def __init__(self, repository: AccountRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self, command: ConfirmIdentityAssociationCommandV1) -> AccountViewV1:
        return self._repository.confirm_identity(command)


class ConfirmProviderIdentityFingerprintV1:
    """Owner-only seam; no implicit account selection is available."""

    def __init__(self, repository: AccountRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, command: ConfirmProviderIdentityFingerprintCommandV1
    ) -> ProviderIdentityResolutionV1:
        return self._repository.confirm_provider_identity_fingerprint(command)


class ResolveProviderIdentityFingerprintV1:
    """Side-effect-free exact identity resolution for approved consumers."""

    def __init__(self, repository: AccountRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, query: ResolveProviderIdentityFingerprintQueryV1
    ) -> ProviderIdentityResolutionV1:
        return self._repository.resolve_provider_identity_fingerprint(query)


class EnrollMonitoringGraphV1:
    def __init__(self, repository: AccountRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, command: EnrollMonitoringGraphCommandV1
    ) -> tuple[MonitoringProfileViewV1, AccountResourceViewV1]:
        return self._repository.enroll_monitoring_graph(command)


class ListAccountsV1:
    def __init__(self, repository: AccountRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self, provider_key: str | None = None) -> tuple[AccountViewV1, ...]:
        return self._repository.list_accounts(provider_key)

    def page(
        self,
        provider_key: str | None,
        *,
        as_of: datetime,
        limit: int,
        after_key: str | None = None,
    ) -> QueryPageV1[AccountViewV1]:
        try:
            rows = self._repository.list_accounts(provider_key, limit + 1, after_key)
        except ValueError:
            raise RegistryQueryUnavailableV1("registry_query_unavailable") from None
        has_more = len(rows) > limit
        items = rows[:limit]
        return QueryPageV1(
            items,
            limit,
            has_more,
            items[-1].account_id.value if has_more else None,
            QueryAvailabilityV1("available", "registry_query_complete", as_of),
        )


class RegisterAccountV1(ConfirmIdentityAssociationV1, RegisterAccountPortV1):
    """Register only through the reviewed discovery-candidate confirmation path."""


class ListMonitoringProfilesV1:
    def __init__(self, repository: AccountRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self, account_id: OpaqueIdV1) -> tuple[MonitoringProfileViewV1, ...]:
        return self._repository.list_monitoring_profiles(account_id)


class ListAccountResourcesV1:
    def __init__(self, repository: AccountRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(self, account_id: OpaqueIdV1) -> tuple[AccountResourceViewV1, ...]:
        return self._repository.list_account_resources(account_id)


class AlertScopeAndSubjectQueryV1:
    def __init__(self, repository: AccountRepositoryPortV1) -> None:
        self._repository = repository

    def __call__(
        self, scope_kind: RegistryScopeKindV1, scope_id: OpaqueIdV1 | None = None
    ) -> RegistryScopeSnapshotV1:
        if (scope_kind == "global") != (scope_id is None):
            raise ValueError("registry_scope_invalid")
        return self._repository.get_registry_scope_snapshot(scope_kind, scope_id)
