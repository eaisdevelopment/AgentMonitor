"""Exhaustive pure-policy assertions selected by the M3 mutation gate.

Inputs are constructed typed domain values.  This suite performs no I/O and
contains no test double; each expected tuple is a published policy decision.
"""

import sys
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend/src"))

from agentmonitor.contracts.capacity_v1 import CapacityHealthPolicyV1
from agentmonitor.contracts.common_quantity_v1 import CanonicalDecimalV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.runtime_observation_v1 import (
    ApprovedStrongCorrelationRuleV1,
    CorrelationEvidenceInputV1,
    InvalidRuntimeObservationV1,
    RuntimeStallPolicyViewV1,
    RuntimeStateEvidenceSummaryV1,
    SessionIdentityV1,
)
from agentmonitor.modules.capacity.domain.health import (
    CapacityConstraintInputV1,
    classify_capacity_health,
)
from agentmonitor.modules.runtime_observation.application.correlation import (
    decide_session_correlation,
)
from agentmonitor.modules.runtime_observation.application.state import (
    evaluate_possible_stall,
    select_effective_stall_policy,
)

_AS_OF = datetime(2026, 9, 24, 12, tzinfo=UTC)
_CAPACITY_POLICY = CapacityHealthPolicyV1(
    policy_id="capacity-health-v1",
    policy_version="1.0.0",
    constrained_remaining_ratio=CanonicalDecimalV1("3", 1),
    critical_remaining_ratio=CanonicalDecimalV1("15", 2),
)


def _capacity(
    window_id: str,
    ratio: str | None,
    freshness: str = "fresh",
    *,
    constraining: bool = True,
) -> CapacityConstraintInputV1:
    return CapacityConstraintInputV1(
        window_id=window_id,
        remaining_ratio=(
            None if ratio is None else CanonicalDecimalV1.from_decimal(Decimal(ratio))
        ),
        freshness=freshness,  # type: ignore[arg-type]
        is_constraining=constraining,
    )


def _capacity_result(result: object) -> tuple[object, ...]:
    return (
        result.state,  # type: ignore[attr-defined]
        result.completeness,  # type: ignore[attr-defined]
        result.freshness,  # type: ignore[attr-defined]
        result.constraining_window_id,  # type: ignore[attr-defined]
        result.policy_id,  # type: ignore[attr-defined]
        result.policy_version,  # type: ignore[attr-defined]
        result.explanation_codes,  # type: ignore[attr-defined]
    )


@pytest.mark.parametrize(
    ("inputs", "reauthentication_required", "expected"),
    (
        (
            (_capacity("exhausted", "0"),),
            True,
            (
                "reauthentication_required",
                "unknown",
                "freshness_unknown",
                None,
                "capacity-health-v1",
                "1.0.0",
                ("provider_reauthentication_required",),
            ),
        ),
        (
            (),
            False,
            (
                "unknown",
                "unknown",
                "freshness_unknown",
                None,
                "capacity-health-v1",
                "1.0.0",
                ("no_trustworthy_constraint",),
            ),
        ),
        (
            (_capacity("ignored", "0", constraining=False),),
            False,
            (
                "unknown",
                "unknown",
                "freshness_unknown",
                None,
                "capacity-health-v1",
                "1.0.0",
                ("no_trustworthy_constraint",),
            ),
        ),
        (
            (_capacity("conflict", None, "conflicted"),),
            False,
            (
                "unknown",
                "partial",
                "conflicted",
                None,
                "capacity-health-v1",
                "1.0.0",
                ("no_trustworthy_constraint",),
            ),
        ),
        (
            (_capacity("stale", None, "stale"),),
            False,
            (
                "unknown",
                "partial",
                "stale",
                None,
                "capacity-health-v1",
                "1.0.0",
                ("no_trustworthy_constraint",),
            ),
        ),
        (
            (_capacity("unknown", None),),
            False,
            (
                "unknown",
                "partial",
                "freshness_unknown",
                None,
                "capacity-health-v1",
                "1.0.0",
                ("no_trustworthy_constraint",),
            ),
        ),
        (
            (_capacity("zero", "0"),),
            False,
            (
                "exhausted",
                "complete",
                "fresh",
                "zero",
                "capacity-health-v1",
                "1.0.0",
                ("lowest_remaining_ratio",),
            ),
        ),
        (
            (_capacity("critical", "0.15"),),
            False,
            (
                "critical",
                "complete",
                "fresh",
                "critical",
                "capacity-health-v1",
                "1.0.0",
                ("lowest_remaining_ratio",),
            ),
        ),
        (
            (_capacity("constrained", "0.30"),),
            False,
            (
                "constrained",
                "complete",
                "fresh",
                "constrained",
                "capacity-health-v1",
                "1.0.0",
                ("lowest_remaining_ratio",),
            ),
        ),
        (
            (_capacity("available", "0.31"),),
            False,
            (
                "available",
                "complete",
                "fresh",
                "available",
                "capacity-health-v1",
                "1.0.0",
                ("lowest_remaining_ratio",),
            ),
        ),
        (
            (
                _capacity("larger", "0.80"),
                _capacity("smallest", "0.20"),
            ),
            False,
            (
                "constrained",
                "complete",
                "fresh",
                "smallest",
                "capacity-health-v1",
                "1.0.0",
                ("lowest_remaining_ratio",),
            ),
        ),
        (
            (_capacity("available", "0.80"), _capacity("missing", None)),
            False,
            (
                "unknown",
                "partial",
                "freshness_unknown",
                None,
                "capacity-health-v1",
                "1.0.0",
                ("incomplete_constraints",),
            ),
        ),
        (
            (_capacity("critical", "0.10"), _capacity("missing", None)),
            False,
            (
                "critical",
                "partial",
                "freshness_unknown",
                "critical",
                "capacity-health-v1",
                "1.0.0",
                ("incomplete_constraints",),
            ),
        ),
    ),
)
def test_capacity_health_policy_decisions_are_exact(
    inputs: tuple[CapacityConstraintInputV1, ...],
    reauthentication_required: bool,
    expected: tuple[object, ...],
) -> None:
    result = classify_capacity_health(
        inputs,
        policy=_CAPACITY_POLICY,
        is_reauthentication_required=reauthentication_required,
    )

    assert _capacity_result(result) == expected


def _state(
    state: str = "working",
    certainty: str = "definitive",
    *,
    freshness_deadline: datetime = _AS_OF + timedelta(minutes=1),
) -> RuntimeStateEvidenceSummaryV1:
    return RuntimeStateEvidenceSummaryV1(
        session_id=OpaqueIdV1("session-one"),
        state=state,  # type: ignore[arg-type]
        certainty=certainty,  # type: ignore[arg-type]
        reason_code="approved-state-evidence",
        observed_at=_AS_OF - timedelta(minutes=1),
        freshness_deadline=freshness_deadline,
        evidence_ids=(OpaqueIdV1("evidence-one"),),
    )


def _stall_policy(
    *,
    policy_id: str = "global-policy",
    scope_kind: str = "global",
    scope_id: str = "global",
    enabled: bool = True,
    threshold_seconds: int = 600,
) -> RuntimeStallPolicyViewV1:
    return RuntimeStallPolicyViewV1(
        policy_id=OpaqueIdV1(policy_id),
        policy_version=7,
        scope_kind=scope_kind,  # type: ignore[arg-type]
        scope_id=scope_id,
        threshold_seconds=threshold_seconds,
        enabled=enabled,
    )


def _stall_result(result: object) -> tuple[object, ...]:
    return (
        result.session_id,  # type: ignore[attr-defined]
        result.evaluation_state,  # type: ignore[attr-defined]
        result.certainty,  # type: ignore[attr-defined]
        result.reason_code,  # type: ignore[attr-defined]
        result.evaluated_at,  # type: ignore[attr-defined]
        result.effective_since,  # type: ignore[attr-defined]
        result.elapsed_seconds,  # type: ignore[attr-defined]
        result.threshold_seconds,  # type: ignore[attr-defined]
        result.policy_id,  # type: ignore[attr-defined]
        result.policy_version,  # type: ignore[attr-defined]
    )


@pytest.mark.parametrize(
    ("current", "progress", "policy", "presence", "expected"),
    (
        (
            _state(),
            _AS_OF - timedelta(hours=1),
            _stall_policy(enabled=False),
            "running",
            ("not_stalled", "definitive", "stall_policy_disabled", None, None),
        ),
        (
            _state(freshness_deadline=_AS_OF),
            _AS_OF - timedelta(seconds=599),
            _stall_policy(),
            "running",
            (
                "not_stalled",
                "definitive",
                "stall_threshold_not_reached",
                None,
                599,
            ),
        ),
        (
            _state(freshness_deadline=_AS_OF - timedelta(microseconds=1)),
            _AS_OF - timedelta(hours=1),
            _stall_policy(),
            "running",
            ("not_evaluable", "unknown", "state_evidence_stale", None, None),
        ),
        (
            _state(),
            _AS_OF,
            _stall_policy(),
            "running",
            (
                "not_stalled",
                "definitive",
                "stall_threshold_not_reached",
                None,
                0,
            ),
        ),
        (
            _state(),
            _AS_OF - timedelta(hours=1),
            _stall_policy(),
            "unknown",
            ("not_evaluable", "unknown", "current_presence_unknown", None, None),
        ),
        (
            _state(),
            _AS_OF - timedelta(hours=1),
            _stall_policy(),
            "exited",
            ("not_stalled", "definitive", "current_presence_terminal", None, None),
        ),
        (
            _state("unknown", "unknown"),
            _AS_OF - timedelta(hours=1),
            _stall_policy(),
            "running",
            ("not_evaluable", "unknown", "runtime_state_unknown", None, None),
        ),
        (
            _state("waiting_for_input", "inferred"),
            _AS_OF - timedelta(hours=1),
            _stall_policy(),
            "running",
            (
                "not_evaluable",
                "unknown",
                "definitive_exclusion_evidence_required",
                None,
                None,
            ),
        ),
        (
            _state("waiting_for_permission"),
            _AS_OF - timedelta(hours=1),
            _stall_policy(),
            "running",
            ("not_stalled", "definitive", "observable_wait_excluded", None, None),
        ),
        (
            _state("quota_or_rate_limited", "inferred"),
            _AS_OF - timedelta(hours=1),
            _stall_policy(),
            "running",
            (
                "not_evaluable",
                "unknown",
                "definitive_exclusion_evidence_required",
                None,
                None,
            ),
        ),
        (
            _state("provider_or_network_error"),
            _AS_OF - timedelta(hours=1),
            _stall_policy(),
            "running",
            ("not_stalled", "definitive", "runtime_state_excluded", None, None),
        ),
        (
            _state(),
            None,
            _stall_policy(),
            "running",
            ("not_evaluable", "unknown", "progress_evidence_missing", None, None),
        ),
        (
            _state(),
            _AS_OF + timedelta(seconds=1),
            _stall_policy(),
            "running",
            ("not_evaluable", "unknown", "progress_evidence_invalid", None, None),
        ),
        (
            _state(),
            datetime(2026, 9, 24, 13, tzinfo=timezone(timedelta(hours=1))),
            _stall_policy(),
            "running",
            ("not_evaluable", "unknown", "progress_evidence_invalid", None, None),
        ),
        (
            _state(),
            _AS_OF - timedelta(seconds=599),
            _stall_policy(),
            "running",
            (
                "not_stalled",
                "definitive",
                "stall_threshold_not_reached",
                None,
                599,
            ),
        ),
        (
            _state(),
            _AS_OF - timedelta(seconds=600),
            _stall_policy(),
            "running",
            (
                "possible_stall",
                "inferred",
                "stall_threshold_reached",
                _AS_OF - timedelta(seconds=600),
                600,
            ),
        ),
    ),
)
def test_stall_policy_decisions_are_exact(
    current: RuntimeStateEvidenceSummaryV1,
    progress: datetime | None,
    policy: RuntimeStallPolicyViewV1,
    presence: str,
    expected: tuple[object, ...],
) -> None:
    result = evaluate_possible_stall(
        current=current,
        progress_observed_at=progress,
        as_of=_AS_OF,
        policy=policy,
        presence=presence,  # type: ignore[arg-type]
    )

    assert _stall_result(result) == (
        OpaqueIdV1("session-one"),
        *expected[:3],
        _AS_OF,
        *expected[3:],
        policy.threshold_seconds,
        policy.policy_id,
        policy.policy_version,
    )


@pytest.mark.parametrize(
    "invalid_as_of",
    (
        datetime(2026, 9, 24, 12),  # noqa: DTZ001 - intentional invalid input
        datetime(2026, 9, 24, 13, tzinfo=timezone(timedelta(hours=1))),
    ),
)
def test_stall_policy_rejects_every_non_utc_evaluation_time(
    invalid_as_of: datetime,
) -> None:
    with pytest.raises(
        InvalidRuntimeObservationV1,
    ) as captured:
        evaluate_possible_stall(
            current=_state(),
            progress_observed_at=None,
            as_of=invalid_as_of,
            policy=_stall_policy(),
            presence="running",
        )
    assert captured.value.code == "runtime_stall_evaluation_time_invalid"


@pytest.mark.parametrize(
    ("state", "certainty"),
    (("unknown", "definitive"), ("working", "unknown")),
)
def test_stall_equivalence_precondition_is_contract_enforced(
    state: str, certainty: str
) -> None:
    """The admitted unknown-pair equivalents depend on this exact invariant."""
    with pytest.raises(InvalidRuntimeObservationV1) as captured:
        _state(state, certainty)
    assert captured.value.code == "runtime_state_evidence_invalid"


def test_stall_policy_scope_precedence_and_fail_closed_outcomes_are_exact() -> None:
    global_policy = _stall_policy()
    organization_policy = _stall_policy(
        policy_id="organization-policy",
        scope_kind="organization",
        scope_id="organization-one",
    )
    provider_policy = _stall_policy(
        policy_id="provider-policy",
        scope_kind="provider",
        scope_id="claude",
    )
    account_policy = _stall_policy(
        policy_id="account-policy",
        scope_kind="account",
        scope_id="account-one",
    )
    policies = (
        global_policy,
        organization_policy,
        provider_policy,
        account_policy,
    )

    assert (
        select_effective_stall_policy(
            policies,
            account_id="account-one",
            provider_key="claude",
            organization_id="organization-one",
        )
        is account_policy
    )
    assert (
        select_effective_stall_policy(
            policies,
            account_id=None,
            provider_key="claude",
            organization_id="organization-one",
        )
        is provider_policy
    )
    assert (
        select_effective_stall_policy(
            policies,
            account_id=None,
            provider_key=None,
            organization_id="organization-one",
        )
        is organization_policy
    )
    assert (
        select_effective_stall_policy(
            policies,
            account_id=None,
            provider_key=None,
            organization_id=None,
        )
        is global_policy
    )

    with pytest.raises(
        InvalidRuntimeObservationV1,
    ) as conflict:
        select_effective_stall_policy(
            (provider_policy, provider_policy),
            account_id=None,
            provider_key="claude",
            organization_id=None,
        )
    assert conflict.value.code == "runtime_stall_policy_conflict"
    with pytest.raises(
        InvalidRuntimeObservationV1,
    ) as missing:
        select_effective_stall_policy(
            (),
            account_id="account-one",
            provider_key="claude",
            organization_id="organization-one",
        )
    assert missing.value.code == "runtime_stall_policy_missing"

    wrong_kind_same_id = _stall_policy(
        policy_id="wrong-kind-same-id",
        scope_kind="organization",
        scope_id="claude",
    )
    same_kind_wrong_id = _stall_policy(
        policy_id="same-kind-wrong-id",
        scope_kind="provider",
        scope_id="codex",
    )
    assert (
        select_effective_stall_policy(
            (wrong_kind_same_id, same_kind_wrong_id, global_policy),
            account_id=None,
            provider_key="claude",
            organization_id=None,
        )
        is global_policy
    )


def _correlation_evidence(
    evidence_id: str,
    session: SessionIdentityV1,
    *,
    account_id: str | None,
    rule_id: str = "approved-rule",
    source_id: str = "approved-source",
    source_version: str = "1.0.0",
) -> CorrelationEvidenceInputV1:
    return CorrelationEvidenceInputV1(
        evidence_id=evidence_id,
        session_identity=session,
        evidence_class="strong" if account_id is not None else "weak",
        rule_id=rule_id,
        account_id=account_id,
        observed_at=_AS_OF,
        source_id=source_id,
        source_version=source_version,
        reason_code="approved-safe-evidence",
    )


def _correlation_result(result: object) -> tuple[object, ...]:
    return (
        result.session_identity,  # type: ignore[attr-defined]
        result.state,  # type: ignore[attr-defined]
        result.account_id,  # type: ignore[attr-defined]
        result.evidence_ids,  # type: ignore[attr-defined]
        result.reason_code,  # type: ignore[attr-defined]
    )


def test_correlation_policy_exactly_matches_approved_strong_evidence() -> None:
    session = SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-one",
        identity_kind="provider_session",
        identity_value="session-one",
    )
    other_session = SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-one",
        identity_kind="provider_session",
        identity_value="session-two",
    )
    rule = ApprovedStrongCorrelationRuleV1(
        rule_id="approved-rule",
        source_id="approved-source",
        source_version="1.0.0",
        decision_reference="owner-decision-one",
    )
    evidence = (
        _correlation_evidence("evidence-b", session, account_id="account-one"),
        _correlation_evidence("evidence-a", session, account_id="account-one"),
        _correlation_evidence(
            "evidence-other", other_session, account_id="account-two"
        ),
    )

    result = decide_session_correlation(session, evidence, (rule,))

    assert _correlation_result(result) == (
        session,
        "automatic_matched",
        "account-one",
        ("evidence-a", "evidence-b"),
        "approved_strong_evidence",
    )


def test_correlation_policy_reports_exact_conflict_and_unresolved_outcomes() -> None:
    session = SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-one",
        identity_kind="provider_session",
        identity_value="session-one",
    )
    rule = ApprovedStrongCorrelationRuleV1(
        rule_id="approved-rule",
        source_id="approved-source",
        source_version="1.0.0",
        decision_reference="owner-decision-one",
    )
    conflicting = (
        _correlation_evidence("evidence-b", session, account_id="account-two"),
        _correlation_evidence("evidence-a", session, account_id="account-one"),
    )

    conflict = decide_session_correlation(session, conflicting, (rule,))
    assert _correlation_result(conflict) == (
        session,
        "conflict",
        None,
        ("evidence-a", "evidence-b"),
        "conflicting_strong_evidence",
    )

    unapproved = decide_session_correlation(
        session,
        (_correlation_evidence("evidence-strong", session, account_id="account-one"),),
    )
    assert _correlation_result(unapproved) == (
        session,
        "unresolved",
        None,
        ("evidence-strong",),
        "approved_strong_evidence_required",
    )

    weak = decide_session_correlation(
        session,
        (_correlation_evidence("evidence-weak", session, account_id=None),),
        (rule,),
    )
    assert _correlation_result(weak) == (
        session,
        "unresolved",
        None,
        ("evidence-weak",),
        "strong_evidence_required",
    )


@pytest.mark.parametrize(
    ("evidence_class", "account_id"),
    (("strong", None), ("weak", "account-one")),
)
def test_correlation_equivalence_precondition_is_contract_enforced(
    evidence_class: str, account_id: str | None
) -> None:
    """The admitted strong/account equivalent depends on this exact invariant."""
    session = SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-one",
        identity_kind="provider_session",
        identity_value="session-one",
    )
    with pytest.raises(InvalidRuntimeObservationV1) as captured:
        CorrelationEvidenceInputV1(
            evidence_id="evidence-one",
            session_identity=session,
            evidence_class=evidence_class,  # type: ignore[arg-type]
            rule_id="approved-rule",
            account_id=account_id,
            observed_at=_AS_OF,
            source_id="approved-source",
            source_version="1.0.0",
            reason_code="approved-safe-evidence",
        )
    assert captured.value.code == "runtime_correlation_evidence_invalid"
