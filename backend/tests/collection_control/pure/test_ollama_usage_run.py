"""Pure usage-run construction; invented metadata never crosses I/O."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.registry_v1 import CloudMonitoringTargetV1

from backend.tests.contracts.test_cloud_budget_run_contract import (
    NOW,
    _context,
    _graph,
    _service,
)


def _build(
    *,
    graph: CloudMonitoringTargetV1 | None = None,
    context: CloudBudgetReportContextV1 | None = None,
    requested_at: datetime = NOW,
) -> CloudBudgetCollectionRunAdmissionV1:
    from agentmonitor.composition import ollama_usage_run
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    return ollama_usage_run.build_ollama_usage_run(
        graph=graph or _graph(),
        service=_service(),
        context=context or _context(),
        registry_revision=10,
        scheduler_instance_id=OpaqueIdV1("pure-worker"),
        run_id=OpaqueIdV1("pure-run"),
        request_id=OpaqueIdV1("pure-request"),
        requested_at=requested_at,
    )


def test_usage_run_preserves_real_graph_and_completed_interval() -> None:
    run = _build()
    assert run.cloud_target == _graph()
    assert run.service_target == _service()
    assert run.profile_id == _graph().profile_id
    assert run.report_context == _context()
    assert run.budget_units == run.budget_limit_units == 1
    assert run.capability_id == "api.usage"
    assert run.payload_schema == "budget.report.v1"
    assert run.deadline_at == NOW + timedelta(seconds=60)
    assert run.manifest_fingerprint != run.service_target.manifest_fingerprint


def test_ranges_have_distinct_schedule_and_budget_identity() -> None:
    first = _build()
    thirty = _build(
        context=_context(range_key="30d", interval_start=NOW - timedelta(days=30))
    )
    assert first.schedule_id != thirty.schedule_id
    assert first.budget_scope_digest != thirty.budget_scope_digest
    assert first.operation_family != thirty.operation_family
    later = _build(requested_at=NOW + timedelta(seconds=1))
    assert later.schedule_id == first.schedule_id
    assert later.request_digest != first.request_digest


def test_rotation_preserves_schedule_but_captures_new_generation() -> None:
    graph = _graph()
    changed = replace(
        graph, binding=replace(graph.binding, generation=5), record_version=8
    )
    old, new = _build(), _build(graph=changed)
    assert old.schedule_id == new.schedule_id
    assert old.target_key_digest == new.target_key_digest
    assert new.target_generation == 5
    assert old.request_digest != new.request_digest


def test_stale_native_interval_rejected_before_dispatch() -> None:
    from agentmonitor.composition.ollama_usage_run import usage_request_for_run

    run = _build()
    assert usage_request_for_run(run, dispatched_at=NOW).period.end == NOW
    with pytest.raises(
        ValueError, match="ollama_usage_interval_no_longer_dispatchable"
    ):
        usage_request_for_run(run, dispatched_at=NOW + timedelta(days=1))
