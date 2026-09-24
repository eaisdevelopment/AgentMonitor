"""Pure CTR-RUN-003 topology policy tests; these tests perform no I/O."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    AgentProcessRecordV1,
    AgentSessionRecordV1,
    ProcessCodeFieldV1,
    ProcessIdentityV1,
    ProcessLabelFieldV1,
    ProcessMetricFieldV1,
    SessionIdentityV1,
    SessionTopologyFactV1,
    SessionTopologySnapshotV1,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    build_session_tree_v1,
)

AS_OF = datetime(2026, 9, 24, 12, tzinfo=UTC)


def _provenance() -> ObservationProvenanceV1:
    return ObservationProvenanceV1(
        provider_key="claude",
        capability_id="local.process.observation",
        capability_schema_version="1.0",
        adapter_id="agentmonitor.test",
        adapter_version="1.0.0",
        provider_protocol_version="1.0.0",
        source_id="linux.proc.process.v1",
        source_class="approved_local_metadata",
        mechanism_version="1.0.0",
        parser_version="1.0.0",
        provider_version="2.1.280",
        provider_version_availability=FieldAvailabilityV1("available"),
        observed_at=AS_OF - timedelta(seconds=1),
        observed_at_availability=FieldAvailabilityV1("available"),
        collected_at=AS_OF - timedelta(seconds=1),
        freshness_deadline=AS_OF + timedelta(minutes=1),
        freshness_availability=FieldAvailabilityV1("available"),
        freshness_policy_id="runtime-one-minute-v1",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="exact_test_evidence",
        value_kind="authoritative",
        is_experimental=False,
        fallback_lineage=(),
        warnings=(),
        operation_id=OpaqueIdV1("operation-opaque"),
        correlation_id=OpaqueIdV1("correlation-opaque"),
        decision_reference="REF-M06-PURE-004",
        derivation_method=None,
        input_observation_ids=(),
    )


def _process(identifier: str, pid: int, parent_pid: int) -> AgentProcessRecordV1:
    missing = ProcessMetricFieldV1("not_requested", None, None, "field_not_requested")
    return AgentProcessRecordV1(
        process_id=OpaqueIdV1(identifier),
        identity=ProcessIdentityV1("linux.proc.process.v1", "boot-scope", pid, pid),
        provider_key="claude",
        installation_id="installation-opaque",
        executable_label=ProcessLabelFieldV1("present", "claude", None),
        parent_pid=ProcessMetricFieldV1("present", parent_pid, "pid", None),
        user_cpu_ticks=missing,
        system_cpu_ticks=missing,
        resident_pages=missing,
        thread_count=missing,
        kernel_state=ProcessCodeFieldV1("present", "S", None),
        clock_ticks_per_second=100,
        page_size_bytes=4096,
        provenance=_provenance(),
        first_observed_at=AS_OF - timedelta(seconds=1),
        last_observed_at=AS_OF - timedelta(seconds=1),
        presence="running",
        current_snapshot_id=OpaqueIdV1(f"snapshot-{identifier}"),
        revision=1,
    )


def _session(identifier: str) -> AgentSessionRecordV1:
    return AgentSessionRecordV1(
        session_id=OpaqueIdV1(identifier),
        identity=SessionIdentityV1(
            "claude", "installation-opaque", "otel.session.id", identifier
        ),
        provenance=_provenance(),
        first_observed_at=AS_OF - timedelta(seconds=1),
        last_observed_at=AS_OF - timedelta(seconds=1),
        correlation_state="unresolved",
        account_id=None,
        revision=1,
    )


def _eligible(session_id: str, process_id: str) -> SessionTopologyFactV1:
    return SessionTopologyFactV1(
        _session(session_id),
        OpaqueIdV1(process_id),
        "eligible",
        "session_process_link_strong",
    )


def test_strong_current_process_ancestry_builds_bounded_tree_without_guessing() -> None:
    """M06-PURE-004/005/014: exact ancestry and bounds remain explicit."""

    snapshot = SessionTopologySnapshotV1(
        sessions=(
            _eligible("session-root", "process-root"),
            _eligible("session-child", "process-child"),
            _eligible("session-grandchild", "process-grandchild"),
        ),
        processes=(
            _process("process-root", 10, 1),
            _process("process-child", 11, 10),
            _process("process-grandchild", 12, 11),
        ),
    )

    complete = build_session_tree_v1(
        snapshot,
        OpaqueIdV1("session-root"),
        as_of=AS_OF,
        depth_limit=8,
        node_limit=200,
    )
    assert [node.session.session_id.value for node in complete.nodes] == [
        "session-root",
        "session-child",
        "session-grandchild",
    ]
    assert complete.nodes[1].parent_session_id == OpaqueIdV1("session-root")
    assert complete.nodes[2].parent_session_id == OpaqueIdV1("session-child")
    assert complete.included_count == 3
    assert complete.excluded_count == 0
    assert complete.unknown_count == 1
    assert complete.nodes[0].orphan_reason == "parent_process_unobserved"

    bounded = build_session_tree_v1(
        snapshot,
        OpaqueIdV1("session-root"),
        as_of=AS_OF,
        depth_limit=1,
        node_limit=200,
    )
    assert bounded.included_count == 2
    assert bounded.excluded_count == 1
    assert bounded.partial is True
    assert bounded.reason_codes == ("tree_bound_reached",)
    returned_ids = {node.session.session_id for node in bounded.nodes}
    assert all(
        child_id in returned_ids
        for node in bounded.nodes
        for child_id in node.child_session_ids
    )

    source_bounded = build_session_tree_v1(
        snapshot,
        OpaqueIdV1("session-root"),
        as_of=AS_OF,
        depth_limit=8,
        node_limit=200,
        source_truncated=True,
    )
    assert source_bounded.partial is True
    assert source_bounded.reason_codes == ("topology_source_bound_reached",)


def test_ambiguous_and_cyclic_process_evidence_never_produces_an_edge() -> None:
    """M06-PURE-004/005: ambiguity and cycles remain visible as orphans."""

    ambiguous = SessionTopologySnapshotV1(
        sessions=(
            SessionTopologyFactV1(
                _session("session-root"),
                None,
                "excluded",
                "session_process_link_ambiguous",
            ),
        ),
        processes=(),
    )
    ambiguous_tree = build_session_tree_v1(
        ambiguous,
        OpaqueIdV1("session-root"),
        as_of=AS_OF,
        depth_limit=8,
        node_limit=200,
    )
    assert ambiguous_tree.nodes[0].parent_session_id is None
    assert ambiguous_tree.nodes[0].orphan_reason == "session_process_link_ambiguous"
    assert ambiguous_tree.unknown_count == 1

    cycle = SessionTopologySnapshotV1(
        sessions=(
            _eligible("session-root", "process-root"),
            _eligible("session-child", "process-child"),
        ),
        processes=(
            _process("process-root", 10, 11),
            _process("process-child", 11, 10),
        ),
    )
    cycle_tree = build_session_tree_v1(
        cycle,
        OpaqueIdV1("session-root"),
        as_of=AS_OF,
        depth_limit=8,
        node_limit=200,
    )
    assert cycle_tree.included_count == 1
    assert cycle_tree.nodes[0].parent_session_id is None
    assert cycle_tree.nodes[0].orphan_reason == "hierarchy_cycle"
