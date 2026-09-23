"""Read-only M06 process/session/history/tree application ports."""

from datetime import datetime
from typing import Protocol

from agentmonitor.contracts.common_v1 import (
    OpaqueIdV1,
    QueryAvailabilityV1,
    QueryPageV1,
)
from agentmonitor.contracts.runtime_observation_v1 import (
    AgentProcessRecordV1,
    AgentSessionRecordV1,
    ProcessHistoryEntryV1,
    RuntimeCommitStatusV1,
    SessionTreeViewV1,
)


class AgentSessionNotFoundV1(ValueError):
    def __init__(self) -> None:
        super().__init__("runtime_subject_not_found")


class RuntimeQueryUnavailableV1(RuntimeError):
    pass


class RuntimeQueryRepositoryV1(Protocol):
    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> RuntimeCommitStatusV1: ...
    def list_processes(
        self,
        provider_key: str | None,
        as_of: datetime,
        page_size: int,
        after_key: str | None = None,
    ) -> tuple[AgentProcessRecordV1, ...]: ...
    def list_process_history(
        self, process_id: OpaqueIdV1, as_of: datetime, page_size: int
    ) -> tuple[ProcessHistoryEntryV1, ...]: ...
    def list_sessions(
        self,
        provider_key: str | None,
        as_of: datetime,
        page_size: int,
        after_key: str | None = None,
        account_id: OpaqueIdV1 | None = None,
    ) -> tuple[AgentSessionRecordV1, ...]: ...
    def get_session(
        self, session_id: OpaqueIdV1, as_of: datetime
    ) -> AgentSessionRecordV1: ...
    def get_session_tree(
        self,
        root_session_id: OpaqueIdV1,
        as_of: datetime,
        depth_limit: int,
        node_limit: int,
    ) -> SessionTreeViewV1: ...


class GetRuntimeCommitStatusV1:
    def __init__(self, repository: RuntimeQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(self, run_id: OpaqueIdV1, capability_id: str) -> RuntimeCommitStatusV1:
        return self._repository.get_commit_status(run_id, capability_id)


class ListAgentProcessesV1:
    def __init__(self, repository: RuntimeQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, *, provider_key: str | None, as_of: datetime, page_size: int = 100
    ) -> tuple[AgentProcessRecordV1, ...]:
        return self._repository.list_processes(provider_key, as_of, page_size)

    def page(
        self,
        *,
        provider_key: str | None,
        as_of: datetime,
        limit: int = 50,
        after_key: str | None = None,
    ) -> QueryPageV1[AgentProcessRecordV1]:
        try:
            rows = self._repository.list_processes(
                provider_key, as_of, limit + 1, after_key
            )
        except ValueError:
            raise RuntimeQueryUnavailableV1("runtime_query_unavailable") from None
        has_more = len(rows) > limit
        items = rows[:limit]
        return QueryPageV1(
            items,
            limit,
            has_more,
            items[-1].process_id.value if has_more else None,
            QueryAvailabilityV1("available", "runtime_query_complete", as_of),
        )


class ListProcessHistoryV1:
    def __init__(self, repository: RuntimeQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, process_id: OpaqueIdV1, *, as_of: datetime, page_size: int = 100
    ) -> tuple[ProcessHistoryEntryV1, ...]:
        return self._repository.list_process_history(process_id, as_of, page_size)


class ListAgentSessionsV1:
    def __init__(self, repository: RuntimeQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        *,
        provider_key: str | None = None,
        account_id: OpaqueIdV1 | None = None,
        as_of: datetime,
        page_size: int = 100,
    ) -> tuple[AgentSessionRecordV1, ...]:
        return self._repository.list_sessions(
            provider_key, as_of, page_size, account_id=account_id
        )

    def page(
        self,
        *,
        provider_key: str | None = None,
        account_id: OpaqueIdV1 | None = None,
        as_of: datetime,
        limit: int = 50,
        after_key: str | None = None,
    ) -> QueryPageV1[AgentSessionRecordV1]:
        try:
            rows = self._repository.list_sessions(
                provider_key, as_of, limit + 1, after_key, account_id
            )
        except ValueError:
            raise RuntimeQueryUnavailableV1("runtime_query_unavailable") from None
        has_more = len(rows) > limit
        items = rows[:limit]
        return QueryPageV1(
            items,
            limit,
            has_more,
            items[-1].session_id.value if has_more else None,
            QueryAvailabilityV1("available", "runtime_query_complete", as_of),
        )


class GetAgentSessionV1:
    def __init__(self, repository: RuntimeQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self, session_id: OpaqueIdV1, *, as_of: datetime
    ) -> AgentSessionRecordV1:
        try:
            return self._repository.get_session(session_id, as_of)
        except ValueError as error:
            if str(error) == "runtime_subject_not_found":
                raise AgentSessionNotFoundV1() from None
            raise RuntimeQueryUnavailableV1("runtime_query_unavailable") from None


class GetSessionTreeV1:
    def __init__(self, repository: RuntimeQueryRepositoryV1) -> None:
        self._repository = repository

    def __call__(
        self,
        root_session_id: OpaqueIdV1,
        *,
        as_of: datetime,
        depth_limit: int = 8,
        node_limit: int = 200,
    ) -> SessionTreeViewV1:
        return self._repository.get_session_tree(
            root_session_id, as_of, depth_limit, node_limit
        )
