"""Pure M06 state/stall policy tests over constructed typed values."""

from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    InvalidRuntimeObservationV1,
    RuntimeStallPolicyViewV1,
    RuntimeStateEvidenceSummaryV1,
)
from agentmonitor.modules.runtime_observation.application.state import (
    evaluate_possible_stall,
    select_effective_stall_policy,
)

_AS_OF = datetime(2026, 9, 22, 12, 10, tzinfo=UTC)


def _state(
    state: str,
    certainty: str,
    *,
    observed_at: datetime | None = None,
    freshness_deadline: datetime | None = None,
) -> RuntimeStateEvidenceSummaryV1:
    return RuntimeStateEvidenceSummaryV1(
        session_id=OpaqueIdV1("session-opaque"),
        state=state,  # type: ignore[arg-type]
        certainty=certainty,  # type: ignore[arg-type]
        reason_code="approved_state_evidence",
        observed_at=observed_at or (_AS_OF - timedelta(minutes=1)),
        freshness_deadline=freshness_deadline or (_AS_OF + timedelta(minutes=1)),
        evidence_ids=(OpaqueIdV1("evidence-opaque"),),
    )


def _policy(
    *,
    policy_id: str = "global-stall-policy",
    scope_kind: str = "global",
    scope_id: str = "global",
    threshold_seconds: int = 600,
) -> RuntimeStallPolicyViewV1:
    return RuntimeStallPolicyViewV1(
        policy_id=OpaqueIdV1(policy_id),
        policy_version=1,
        scope_kind=scope_kind,  # type: ignore[arg-type]
        scope_id=scope_id,
        threshold_seconds=threshold_seconds,
        enabled=True,
    )


def test_missing_progress_is_not_possible_stall() -> None:
    result = evaluate_possible_stall(
        current=_state("working", "definitive"),
        progress_observed_at=None,
        as_of=_AS_OF,
        policy=_policy(),
        presence="running",
    )

    assert result.evaluation_state == "not_evaluable"
    assert result.reason_code == "progress_evidence_missing"
    assert result.elapsed_seconds is None


def test_observable_wait_is_excluded_from_possible_stall() -> None:
    result = evaluate_possible_stall(
        current=_state("waiting_for_permission", "definitive"),
        progress_observed_at=_AS_OF - timedelta(hours=1),
        as_of=_AS_OF,
        policy=_policy(),
        presence="running",
    )

    assert result.evaluation_state == "not_stalled"
    assert result.reason_code == "observable_wait_excluded"


def test_exact_default_threshold_is_only_an_inferred_possible_stall() -> None:
    result = evaluate_possible_stall(
        current=_state("working", "definitive"),
        progress_observed_at=_AS_OF - timedelta(seconds=600),
        as_of=_AS_OF,
        policy=_policy(),
        presence="running",
    )

    assert result.evaluation_state == "possible_stall"
    assert result.certainty == "inferred"
    assert result.elapsed_seconds == 600
    assert result.threshold_seconds == 600


def test_stale_or_unknown_state_is_not_evaluable() -> None:
    stale = evaluate_possible_stall(
        current=_state(
            "working",
            "definitive",
            freshness_deadline=_AS_OF - timedelta(microseconds=1),
        ),
        progress_observed_at=_AS_OF - timedelta(hours=1),
        as_of=_AS_OF,
        policy=_policy(),
        presence="running",
    )
    unknown = evaluate_possible_stall(
        current=_state("unknown", "unknown"),
        progress_observed_at=_AS_OF - timedelta(hours=1),
        as_of=_AS_OF,
        policy=_policy(),
        presence="running",
    )

    assert (stale.evaluation_state, stale.reason_code) == (
        "not_evaluable",
        "state_evidence_stale",
    )
    assert (unknown.evaluation_state, unknown.reason_code) == (
        "not_evaluable",
        "runtime_state_unknown",
    )


def test_approved_normalized_state_vocabulary_is_exact() -> None:
    for state in (
        "quota_or_rate_limited",
        "reauthentication_required",
        "provider_or_network_error",
    ):
        assert _state(state, "definitive").state == state

    for obsolete in (
        "quota_rate_limited",
        "authentication_required",
        "provider_error",
        "network_error",
    ):
        with pytest.raises(
            InvalidRuntimeObservationV1, match="runtime_state_evidence_invalid"
        ):
            _state(obsolete, "definitive")


def test_naive_evaluation_time_is_rejected_with_a_typed_safe_error() -> None:
    with pytest.raises(
        InvalidRuntimeObservationV1,
        match="runtime_stall_evaluation_time_invalid",
    ):
        evaluate_possible_stall(
            current=_state("working", "definitive"),
            progress_observed_at=None,
            as_of=datetime(2026, 9, 22, 12, 10),
            policy=_policy(),
            presence="running",
        )


def test_inferred_wait_does_not_become_a_definitive_exclusion() -> None:
    result = evaluate_possible_stall(
        current=_state("waiting_for_input", "inferred"),
        progress_observed_at=_AS_OF - timedelta(hours=1),
        as_of=_AS_OF,
        policy=_policy(),
        presence="running",
    )

    assert result.evaluation_state == "not_evaluable"
    assert result.certainty == "unknown"
    assert result.reason_code == "definitive_exclusion_evidence_required"


def test_missing_current_presence_is_not_evaluable() -> None:
    result = evaluate_possible_stall(
        current=_state("working", "definitive"),
        progress_observed_at=_AS_OF - timedelta(hours=1),
        as_of=_AS_OF,
        policy=_policy(),
        presence="unknown",
    )

    assert result.evaluation_state == "not_evaluable"
    assert result.reason_code == "current_presence_unknown"


def test_effective_policy_precedence_is_account_then_provider_then_global() -> None:
    global_policy = _policy()
    provider_policy = _policy(
        policy_id="provider-policy",
        scope_kind="provider",
        scope_id="claude",
        threshold_seconds=900,
    )
    account_policy = _policy(
        policy_id="account-policy",
        scope_kind="account",
        scope_id="account-opaque",
        threshold_seconds=1200,
    )

    account = select_effective_stall_policy(
        (global_policy, provider_policy, account_policy),
        account_id="account-opaque",
        provider_key="claude",
        organization_id=None,
    )
    provider = select_effective_stall_policy(
        (global_policy, provider_policy, account_policy),
        account_id=None,
        provider_key="claude",
        organization_id=None,
    )

    assert account.policy_id == OpaqueIdV1("account-policy")
    assert provider.policy_id == OpaqueIdV1("provider-policy")
