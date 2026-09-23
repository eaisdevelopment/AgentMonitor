"""Production provider collection composition; construction performs no I/O."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.providers.claude.adapter import ClaudeAdapterV1
from agentmonitor.adapters.providers.claude.installation import ClaudeInstallationV1
from agentmonitor.adapters.providers.claude.subscription.mapper import (
    map_claude_quota_to_capacity,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityCommitReceiptV1,
    CapacityCommitStatusV1,
    ProviderQuotaInputV1,
)
from agentmonitor.contracts.collection_control_v1 import (
    CollectionCommitReceiptV1,
    CollectionFailedV1,
    CollectionOutcomeCommitV1,
    CollectionRunAdmissionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import ProviderOperationRequestHeaderV1
from agentmonitor.contracts.providers.claude.subscription_quota.v1.schema import (
    ClaudeSubscriptionQuotaV1,
)
from agentmonitor.modules.capacity.application.commit import (
    CommitCapacityCollectionOutcomeV1,
)
from agentmonitor.modules.capacity.application.ingest import (
    PrepareCapacityCollectionOutcomeV1,
)
from agentmonitor.modules.capacity.application.queries import (
    GetAccountCapacityV1,
    GetCapacityHealthV1,
    GetCollectionCommitStatusV1,
    ListQuotaWindowsV1,
)
from agentmonitor.modules.collection_control.application.executor import (
    ExecuteCollectionRunV1,
)
from agentmonitor.modules.collection_control.application.runner import (
    RequestManualCollectionV1,
    RunOneCollectionV1,
)


class _SingleCapacityOutcomeSinkV1:
    """One composed M05 sink shared by normal execution and crash recovery."""

    def __init__(
        self,
        commit: CommitCapacityCollectionOutcomeV1,
        get_status: GetCollectionCommitStatusV1,
    ) -> None:
        self._commit = commit
        self._get_status = get_status

    def commit(
        self, request: CollectionOutcomeCommitV1[ProviderQuotaInputV1]
    ) -> CollectionCommitReceiptV1:
        return self._commit.commit(request)

    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> CapacityCommitStatusV1:
        return self._get_status(run_id, capability_id)


@dataclass(frozen=True, slots=True)
class ClaudeQuotaCollectionRouteV1:
    """The one production Claude quota collector and its one M05 sink."""

    adapter: ClaudeAdapterV1
    request_manual: RequestManualCollectionV1
    run_one: RunOneCollectionV1[ClaudeSubscriptionQuotaV1, ProviderQuotaInputV1]
    capacity_commit: CommitCapacityCollectionOutcomeV1
    get_commit_status: GetCollectionCommitStatusV1
    get_account_capacity: GetAccountCapacityV1
    list_quota_windows: ListQuotaWindowsV1
    get_capacity_health: GetCapacityHealthV1
    _prepare: PrepareCapacityCollectionOutcomeV1[ClaudeSubscriptionQuotaV1]
    _executor: ExecuteCollectionRunV1[ClaudeSubscriptionQuotaV1, ProviderQuotaInputV1]

    def collect_once(
        self,
        admission: CollectionRunAdmissionV1,
        provider_request: ProviderOperationRequestHeaderV1,
        *,
        started_at: datetime,
        completed_at: datetime | Callable[[], datetime],
    ) -> CapacityCommitReceiptV1 | CollectionFailedV1:
        """Execute the real adapter only after M04 durably admits the run."""
        if (
            admission.provider_key != "claude"
            or provider_request.provider_key != admission.provider_key
            or provider_request.capability_id != admission.capability_id
            or provider_request.correlation_id != admission.correlation_id
            or provider_request.target.installation_ref != admission.installation_id
            or provider_request.target.account_ref != admission.account_id
            or provider_request.target.profile_ref != admission.profile_id
            or provider_request.target.resource_ref != admission.resource_id
        ):
            raise ValueError("claude_collection_route_identity_mismatch")
        result = self.run_one(
            admission,
            lambda: self.adapter.collect_subscription_quota(provider_request),
            self._prepare,
            started_at=started_at,
            completed_at=completed_at,
        )
        if isinstance(result, CollectionFailedV1):
            return result
        if not isinstance(result, CapacityCommitReceiptV1):
            raise ValueError("claude_capacity_receipt_type_invalid")
        return result

    def recover_commit(
        self,
        admission: CollectionRunAdmissionV1,
        *,
        completed_at: datetime,
    ) -> CapacityCommitReceiptV1 | CollectionFailedV1:
        """Reconcile one committing run without calling the Claude adapter."""
        result = self._executor.recover_commit(
            admission,
            completed_at=completed_at,
        )
        if isinstance(result, CollectionFailedV1):
            return result
        if not isinstance(result, CapacityCommitReceiptV1):
            raise ValueError("claude_capacity_receipt_type_invalid")
        return result


def compose_claude_quota_collection(
    reference: DatabaseRefV1,
    installation: ClaudeInstallationV1,
) -> ClaudeQuotaCollectionRouteV1:
    """Wire the real Claude adapter to one digest-validating M05 sink."""
    collection_repository = SqliteCollectionRepositoryV1(reference)
    capacity_repository = SqliteCapacityRepositoryV1(reference)
    capacity_commit = CommitCapacityCollectionOutcomeV1(capacity_repository)
    get_commit_status = GetCollectionCommitStatusV1(capacity_repository)
    sink = _SingleCapacityOutcomeSinkV1(capacity_commit, get_commit_status)
    executor = ExecuteCollectionRunV1[ClaudeSubscriptionQuotaV1, ProviderQuotaInputV1](
        collection_repository,
        sink,
    )
    prepare = PrepareCapacityCollectionOutcomeV1[ClaudeSubscriptionQuotaV1](
        map_claude_quota_to_capacity
    )
    return ClaudeQuotaCollectionRouteV1(
        adapter=ClaudeAdapterV1(installation),
        request_manual=RequestManualCollectionV1(collection_repository),
        run_one=RunOneCollectionV1(executor),
        capacity_commit=capacity_commit,
        get_commit_status=get_commit_status,
        get_account_capacity=GetAccountCapacityV1(capacity_repository),
        list_quota_windows=ListQuotaWindowsV1(capacity_repository),
        get_capacity_health=GetCapacityHealthV1(capacity_repository),
        _prepare=prepare,
        _executor=executor,
    )
