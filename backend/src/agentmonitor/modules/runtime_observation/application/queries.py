"""Read-only M06 process/session/history/tree application ports."""

from datetime import datetime, timedelta
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
    SessionTopologySnapshotV1,
    SessionTreeNodeV1,
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
    def get_session_topology(
        self,
        root_session_id: OpaqueIdV1,
        as_of: datetime,
        source_limit: int,
    ) -> tuple[SessionTopologySnapshotV1, bool]: ...


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


def build_session_tree_v1(
    snapshot: SessionTopologySnapshotV1,
    root_session_id: OpaqueIdV1,
    *,
    as_of: datetime,
    depth_limit: int,
    node_limit: int,
    source_truncated: bool = False,
) -> SessionTreeViewV1:
    """Build one bounded tree solely from current, unambiguous strong evidence."""

    if (
        as_of.utcoffset() != timedelta(0)
        or type(depth_limit) is not int
        or not 1 <= depth_limit <= 32
        or type(node_limit) is not int
        or not 1 <= node_limit <= 200
        or type(source_truncated) is not bool
    ):
        raise ValueError("runtime_query_invalid")

    facts = {fact.session.session_id: fact for fact in snapshot.sessions}
    if len(facts) != len(snapshot.sessions):
        raise ValueError("runtime_topology_duplicate_session")
    if root_session_id not in facts:
        raise AgentSessionNotFoundV1()

    processes = {process.process_id: process for process in snapshot.processes}
    if len(processes) != len(snapshot.processes):
        raise ValueError("runtime_topology_duplicate_process")

    current_pid_index: dict[tuple[str, str, int], list[AgentProcessRecordV1]] = {}
    for process in snapshot.processes:
        if process.presence == "running":
            key = (
                process.identity.platform_source,
                process.identity.platform_scope_id,
                process.identity.pid,
            )
            current_pid_index.setdefault(key, []).append(process)

    process_sessions: dict[OpaqueIdV1, list[OpaqueIdV1]] = {}
    for session_id, fact in facts.items():
        if fact.evidence_state == "eligible" and fact.primary_process_id is not None:
            process_sessions.setdefault(fact.primary_process_id, []).append(session_id)

    parents: dict[OpaqueIdV1, OpaqueIdV1] = {}
    orphan_reasons: dict[OpaqueIdV1, str] = {}
    for session_id, fact in facts.items():
        process_id = fact.primary_process_id
        if fact.evidence_state != "eligible" or process_id is None:
            orphan_reasons[session_id] = fact.reason_code
            continue
        if len(process_sessions.get(process_id, ())) != 1:
            orphan_reasons[session_id] = "session_process_link_ambiguous"
            continue
        linked_process = processes.get(process_id)
        if linked_process is None:
            orphan_reasons[session_id] = "linked_process_unobserved"
            continue
        if linked_process.presence != "running":
            orphan_reasons[session_id] = "linked_process_not_current"
            continue
        if (
            linked_process.parent_pid.state != "present"
            or linked_process.parent_pid.value is None
        ):
            orphan_reasons[session_id] = (
                linked_process.parent_pid.reason_code or "parent_process_unavailable"
            )
            continue
        parent_key = (
            linked_process.identity.platform_source,
            linked_process.identity.platform_scope_id,
            linked_process.parent_pid.value,
        )
        parent_processes = current_pid_index.get(parent_key, ())
        if not parent_processes:
            orphan_reasons[session_id] = "parent_process_unobserved"
            continue
        if len(parent_processes) != 1:
            orphan_reasons[session_id] = "parent_process_ambiguous"
            continue
        parent_sessions = process_sessions.get(parent_processes[0].process_id, ())
        if not parent_sessions:
            orphan_reasons[session_id] = "parent_session_unobserved"
            continue
        if len(parent_sessions) != 1:
            orphan_reasons[session_id] = "parent_session_ambiguous"
            continue
        parent_session_id = parent_sessions[0]
        if parent_session_id == session_id:
            orphan_reasons[session_id] = "hierarchy_self_cycle"
            continue
        parents[session_id] = parent_session_id

    # A functional parent graph can contain only disjoint cycles. Reject every
    # edge in a cycle before building children so no successful view cycles.
    cycle_members: set[OpaqueIdV1] = set()
    for start in tuple(parents):
        order: list[OpaqueIdV1] = []
        positions: dict[OpaqueIdV1, int] = {}
        current = start
        while current in parents and current not in positions:
            positions[current] = len(order)
            order.append(current)
            current = parents[current]
        if current in positions:
            cycle_members.update(order[positions[current] :])
    for session_id in cycle_members:
        parents.pop(session_id, None)
        orphan_reasons[session_id] = "hierarchy_cycle"

    children: dict[OpaqueIdV1, list[OpaqueIdV1]] = {}
    for child_id, parent_id in parents.items():
        children.setdefault(parent_id, []).append(child_id)
    for child_ids in children.values():
        child_ids.sort(key=lambda value: value.value)

    reachable: list[tuple[OpaqueIdV1, int]] = []
    queue: list[tuple[OpaqueIdV1, int]] = [(root_session_id, 0)]
    seen: set[OpaqueIdV1] = set()
    while queue:
        session_id, depth = queue.pop(0)
        if session_id in seen:
            continue
        seen.add(session_id)
        reachable.append((session_id, depth))
        queue.extend((child_id, depth + 1) for child_id in children.get(session_id, ()))

    included = [
        (session_id, depth) for session_id, depth in reachable if depth <= depth_limit
    ][:node_limit]
    excluded_count = len(reachable) - len(included)
    included_ids = {session_id for session_id, _depth in included}
    nodes = tuple(
        SessionTreeNodeV1(
            session=facts[session_id].session,
            parent_session_id=parents.get(session_id),
            child_session_ids=tuple(
                child_id
                for child_id in children.get(session_id, ())
                if child_id in included_ids
            ),
            orphan_reason=orphan_reasons.get(session_id),
        )
        for session_id, _depth in included
    )
    reason_codes = tuple(
        sorted(
            {
                *({"tree_bound_reached"} if excluded_count else set()),
                *({"topology_source_bound_reached"} if source_truncated else set()),
            }
        )
    )
    return SessionTreeViewV1(
        root_session_id=root_session_id,
        as_of=as_of,
        nodes=nodes,
        included_count=len(nodes),
        excluded_count=excluded_count,
        unknown_count=sum(node.orphan_reason is not None for node in nodes),
        partial=bool(reason_codes),
        reason_codes=reason_codes,
    )


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
        try:
            snapshot, source_truncated = self._repository.get_session_topology(
                root_session_id, as_of, node_limit
            )
            return build_session_tree_v1(
                snapshot,
                root_session_id,
                as_of=as_of,
                depth_limit=depth_limit,
                node_limit=node_limit,
                source_truncated=source_truncated,
            )
        except AgentSessionNotFoundV1:
            raise
        except ValueError as error:
            if str(error) == "runtime_subject_not_found":
                raise AgentSessionNotFoundV1() from None
            raise RuntimeQueryUnavailableV1("runtime_query_unavailable") from None
