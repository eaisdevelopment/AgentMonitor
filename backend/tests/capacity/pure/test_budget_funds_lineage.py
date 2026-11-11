"""Pure DTO lineage checks; no provider payloads or I/O ports are constructed."""

from dataclasses import replace
from datetime import timedelta

import pytest
from agentmonitor.adapters.providers.ollama.api.funds_projection import project_funds
from agentmonitor.composition import budget_funds
from agentmonitor.contracts.collection_control_v1 import CollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1

from backend.tests.providers.ollama.pure.test_funds_projection import NOW, _window


def _run() -> CollectionRunViewV1:
    window = _window()
    return CollectionRunViewV1(
        run_id=window.collection_run_id,
        schedule_id=OpaqueIdV1("pure-schedule"),
        provider_key="ollama",
        account_id=window.subject.account_id,
        resource_id=window.subject.resource_id,
        capability_id="subscription.quota",
        state="succeeded",
        source_id=window.provenance.source_id,
        adapter_version=window.provenance.adapter_version,
        provider_version=None,
        target_generation=2,
        fencing_token=1,
        requested_at=NOW - timedelta(seconds=2),
        started_at=NOW - timedelta(seconds=1),
        completed_at=NOW,
        deadline_at=NOW + timedelta(minutes=1),
        duration_ms=1000,
        payload_digest="a" * 64,
        outcome_code="succeeded",
        error_code=None,
        observation_ids=(window.current_observation_id,),
    )


def _binding() -> ActiveCredentialBindingRefV1:
    return ActiveCredentialBindingRefV1(
        OpaqueIdV1("pure-account"), OpaqueIdV1("amcb_" + "a" * 32), 2
    )


def test_current_generation_requires_the_actual_committed_observation() -> None:
    component = project_funds(_window(), as_of=NOW)
    assert component is not None
    assert budget_funds.funds_match_active_binding(
        component, _binding(), _run(), as_of=NOW
    )
    assert not budget_funds.funds_match_active_binding(
        component, replace(_binding(), generation=3), _run(), as_of=NOW
    )
    assert not budget_funds.funds_match_active_binding(
        component, None, _run(), as_of=NOW
    )
    assert not budget_funds.funds_match_active_binding(
        component, _binding(), None, as_of=NOW
    )


@pytest.mark.parametrize(
    "run",
    [
        replace(_run(), run_id=OpaqueIdV1("other-run")),
        replace(_run(), account_id=OpaqueIdV1("other-account")),
        replace(_run(), resource_id=OpaqueIdV1("other-resource")),
        replace(_run(), provider_key="other-provider"),
        replace(_run(), source_id="other.source.v1"),
        replace(_run(), capability_id="api.usage"),
        replace(_run(), target_generation=1),
        replace(_run(), observation_ids=(OpaqueIdV1("other-observation"),)),
        replace(_run(), completed_at=NOW + timedelta(seconds=1)),
    ],
)
def test_unproven_funds_are_not_current(run: CollectionRunViewV1) -> None:
    component = project_funds(_window(), as_of=NOW)
    assert component is not None
    assert not budget_funds.funds_match_active_binding(
        component, _binding(), run, as_of=NOW
    )
