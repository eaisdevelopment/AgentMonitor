"""Pure fail-closed M06 runtime state and possible-stall policy."""

from __future__ import annotations

from datetime import datetime, timedelta

from agentmonitor.contracts.runtime_observation_v1 import (
    InvalidRuntimeObservationV1,
    PossibleStallEvaluationV1,
    PresenceStateV1,
    RuntimeStallPolicyViewV1,
    RuntimeStateCertaintyV1,
    RuntimeStateEvidenceSummaryV1,
    StallEvaluationStateV1,
)

_WAITING_STATES = frozenset({"waiting_for_input", "waiting_for_permission"})
_EXCLUDED_STATES = frozenset(
    {
        "quota_or_rate_limited",
        "reauthentication_required",
        "provider_or_network_error",
        "exited_successfully",
        "crashed",
        "possibly_stuck",
    }
)


def evaluate_possible_stall(
    *,
    current: RuntimeStateEvidenceSummaryV1,
    progress_observed_at: datetime | None,
    as_of: datetime,
    policy: RuntimeStallPolicyViewV1,
    presence: PresenceStateV1,
) -> PossibleStallEvaluationV1:
    """Evaluate only coherent fresh evidence; missing inputs remain not evaluable."""

    if as_of.utcoffset() != timedelta(0):
        raise InvalidRuntimeObservationV1("runtime_stall_evaluation_time_invalid")
    if not policy.enabled:
        return _result(
            current,
            as_of,
            policy,
            "not_stalled",
            "definitive",
            "stall_policy_disabled",
        )
    if current.freshness_deadline < as_of:
        return _result(
            current,
            as_of,
            policy,
            "not_evaluable",
            "unknown",
            "state_evidence_stale",
        )
    if presence == "unknown":
        return _result(
            current,
            as_of,
            policy,
            "not_evaluable",
            "unknown",
            "current_presence_unknown",
        )
    if presence == "exited":
        return _result(
            current,
            as_of,
            policy,
            "not_stalled",
            "definitive",
            "current_presence_terminal",
        )
    if current.state == "unknown" or current.certainty == "unknown":
        return _result(
            current,
            as_of,
            policy,
            "not_evaluable",
            "unknown",
            "runtime_state_unknown",
        )
    if current.state in _WAITING_STATES:
        if current.certainty != "definitive":
            return _result(
                current,
                as_of,
                policy,
                "not_evaluable",
                "unknown",
                "definitive_exclusion_evidence_required",
            )
        return _result(
            current,
            as_of,
            policy,
            "not_stalled",
            "definitive",
            "observable_wait_excluded",
        )
    if current.state in _EXCLUDED_STATES:
        if current.certainty != "definitive":
            return _result(
                current,
                as_of,
                policy,
                "not_evaluable",
                "unknown",
                "definitive_exclusion_evidence_required",
            )
        return _result(
            current,
            as_of,
            policy,
            "not_stalled",
            "definitive",
            "runtime_state_excluded",
        )
    if progress_observed_at is None:
        return _result(
            current,
            as_of,
            policy,
            "not_evaluable",
            "unknown",
            "progress_evidence_missing",
        )
    if progress_observed_at.utcoffset() != timedelta(0) or progress_observed_at > as_of:
        return _result(
            current,
            as_of,
            policy,
            "not_evaluable",
            "unknown",
            "progress_evidence_invalid",
        )

    elapsed = int((as_of - progress_observed_at).total_seconds())
    if elapsed < policy.threshold_seconds:
        return _result(
            current,
            as_of,
            policy,
            "not_stalled",
            "definitive",
            "stall_threshold_not_reached",
            elapsed_seconds=elapsed,
        )
    return _result(
        current,
        as_of,
        policy,
        "possible_stall",
        "inferred",
        "stall_threshold_reached",
        effective_since=progress_observed_at,
        elapsed_seconds=elapsed,
    )


def select_effective_stall_policy(
    policies: tuple[RuntimeStallPolicyViewV1, ...],
    *,
    account_id: str | None,
    provider_key: str | None,
    organization_id: str | None,
) -> RuntimeStallPolicyViewV1:
    """Resolve account > provider > organization > global without guessing."""

    scopes = (
        ("account", account_id),
        ("provider", provider_key),
        ("organization", organization_id),
        ("global", "global"),
    )
    for scope_kind, scope_id in scopes:
        if scope_id is None:
            continue
        matches = tuple(
            policy
            for policy in policies
            if policy.scope_kind == scope_kind and policy.scope_id == scope_id
        )
        if len(matches) > 1:
            raise InvalidRuntimeObservationV1("runtime_stall_policy_conflict")
        if matches:
            return matches[0]
    raise InvalidRuntimeObservationV1("runtime_stall_policy_missing")


def _result(
    current: RuntimeStateEvidenceSummaryV1,
    as_of: datetime,
    policy: RuntimeStallPolicyViewV1,
    evaluation_state: StallEvaluationStateV1,
    certainty: RuntimeStateCertaintyV1,
    reason_code: str,
    *,
    effective_since: datetime | None = None,
    elapsed_seconds: int | None = None,
) -> PossibleStallEvaluationV1:
    return PossibleStallEvaluationV1(
        session_id=current.session_id,
        evaluation_state=evaluation_state,
        certainty=certainty,
        reason_code=reason_code,
        evaluated_at=as_of,
        effective_since=effective_since,
        elapsed_seconds=elapsed_seconds,
        threshold_seconds=policy.threshold_seconds,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
    )
