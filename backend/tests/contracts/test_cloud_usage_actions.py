"""Pure owner intent and replay identity; no constructed provider I/O."""

from dataclasses import replace
from datetime import timedelta
from typing import Any, cast

import pytest
from agentmonitor.contracts.cloud_usage_actions_v1 import CloudUsageCollectCommandV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.contracts.test_cloud_budget_run_contract import NOW, _context


def _command() -> CloudUsageCollectCommandV1:
    from agentmonitor.contracts import cloud_usage_actions_v1 as contract

    return contract.CloudUsageCollectCommandV1(
        account_id=OpaqueIdV1("pure-cloud-account"),
        resource_id=OpaqueIdV1("pure-cloud-resource"),
        expected_account_version=2,
        expected_target_version=7,
        principal_id=OpaqueIdV1("pure-owner"),
        command_id=OpaqueIdV1("pure-owner-command"),
        requested_at=NOW,
        report_context=_context(),
    )


def test_cloud_manual_intent_preserves_selected_context() -> None:
    command = _command()
    assert command.report_context == _context()
    assert command.CONTRACT_VERSION == "2.5.0"


@pytest.mark.parametrize(
    "field", ["expected_account_version", "expected_target_version"]
)
@pytest.mark.parametrize("value", [0, -1, True, "1"])
def test_cloud_manual_rejects_invalid_versions(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="cloud_usage_command_invalid"):
        replace(
            _command(), **cast(dict[str, Any], {field: value})
        )  # malformed domain input


def test_cloud_manual_rejects_future_interval() -> None:
    with pytest.raises(ValueError, match="cloud_usage_command_invalid"):
        replace(_command(), requested_at=NOW - timedelta(seconds=1))


def test_cloud_manual_identifiers_retry_same_intent_and_conflict_on_change() -> None:
    from agentmonitor.composition.cloud_usage_actions import cloud_usage_identifiers

    first = cloud_usage_identifiers(_command())
    retry = cloud_usage_identifiers(
        replace(_command(), requested_at=NOW + timedelta(seconds=1))
    )
    assert first == retry
    changed = cloud_usage_identifiers(
        replace(_command(), report_context=_context(scope="team"))
    )
    assert first.run_id == changed.run_id
    assert first.schedule_id != changed.schedule_id
    assert first.idempotency_key_digest != changed.idempotency_key_digest
    other = cloud_usage_identifiers(
        replace(_command(), principal_id=OpaqueIdV1("pure-other-owner"))
    )
    assert other.run_id != first.run_id


def test_manual_usage_admission_is_owner_bound_and_keeps_shared_budget_scope() -> None:
    from agentmonitor.composition.cloud_usage_actions import build_manual_usage_run
    from agentmonitor.composition.ollama_usage_run import build_ollama_usage_run

    from backend.tests.contracts.test_cloud_budget_run_contract import _graph, _service

    command = _command()
    run = build_manual_usage_run(
        command, graph=_graph(), service=_service(), registry_revision=10
    )
    scheduled = build_ollama_usage_run(
        graph=_graph(),
        service=_service(),
        context=_context(),
        registry_revision=10,
        scheduler_instance_id=OpaqueIdV1("pure-scheduler"),
        run_id=OpaqueIdV1("pure-run"),
        request_id=OpaqueIdV1("pure-request"),
        requested_at=NOW,
    )
    assert run.deadline_at == command.requested_at + timedelta(seconds=120)
    assert run.trigger == "manual"
    assert run.request_auth_method == "browser_cookie"
    assert run.request_principal_id == command.principal_id
    assert run.report_context == command.report_context
    assert run.budget_scope_digest == scheduled.budget_scope_digest
    assert run.target_key_digest != scheduled.target_key_digest
    assert run.schedule_id != scheduled.schedule_id
    assert run.idempotency_key_digest is not None
    retry = build_manual_usage_run(
        replace(command, requested_at=NOW + timedelta(seconds=1)),
        graph=_graph(),
        service=_service(),
        registry_revision=10,
    )
    assert retry.run_id == run.run_id
    assert retry.request_digest == run.request_digest


def test_manual_usage_admission_rejects_wrong_graph_and_stale_native_window() -> None:
    from agentmonitor.composition.cloud_usage_actions import build_manual_usage_run

    from backend.tests.contracts.test_cloud_budget_run_contract import _graph, _service

    for command in (
        replace(_command(), resource_id=OpaqueIdV1("wrong-resource")),
        replace(_command(), expected_target_version=9),
    ):
        with pytest.raises(ValueError, match="cloud_usage_target_changed"):
            build_manual_usage_run(
                command, graph=_graph(), service=_service(), registry_revision=10
            )
    with pytest.raises(
        ValueError, match="ollama_usage_interval_no_longer_dispatchable"
    ):
        build_manual_usage_run(
            replace(_command(), requested_at=NOW + timedelta(days=1)),
            graph=_graph(),
            service=_service(),
            registry_revision=10,
        )
