"""Pure policy checks for direct, single-command M6 evidence selection."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.capacity_v1 import CapacityAlertAvailabilityV1
from agentmonitor.modules.alerting.domain.policy import builtin_rule

from backend.tests.alerting.pure.test_capacity_mapper import NOW, fact
from tools.automation.implementations.m6_direct_evidence import (
    DIRECT_EXECUTABLE_SELECTION_V1,
    BoundaryCheckV1,
    CloudOrganizationScopeV1,
    CloudScopeEvidenceV1,
    DirectM6FactsV1,
    LocalModelHostEvidenceV1,
    classify_direct_m6_evidence_v1,
    cloud_reference_digest_v1,
    direct_bundle_v1,
)
from tools.automation.implementations.m6_exit_policy import evaluate_evidence_bundle_v1
from tools.automation.implementations.m6_real_snapshot import (
    _alert_window_requirement,
    _unique_alert_event_keys,
)

PASSED = BoundaryCheckV1("passed", 1)
HOSTS = (
    LocalModelHostEvidenceV1(
        "local_loopback",
        "ollama_loopback_127_0_0_1_11434",
        "1.2.3",
        0,
        0,
        "2026-11-02T12:00:00Z",
    ),
    LocalModelHostEvidenceV1(
        "second_machine",
        "ollama_owner_configured_second_host",
        "1.2.3",
        1,
        0,
        "2026-11-02T12:00:00Z",
    ),
)


def _scope(shared: bool = False) -> CloudScopeEvidenceV1:
    targets = ("a" * 64,) if shared else ("a" * 64, "b" * 64)
    rows = tuple(
        CloudOrganizationScopeV1(
            cloud_reference_digest_v1("organization", organization),
            "shared" if shared and index else "account",
            cloud_reference_digest_v1(
                "account", "account-a" if shared or index == 0 else "account-b"
            ),
            targets[0 if shared else index],
            1,
        )
        for index, organization in enumerate(("org-a", "org-b"))
    )
    return CloudScopeEvidenceV1(
        rows, targets, targets, targets, 1, "2026-11-03T12:00:00Z", True
    )


def _complete_facts() -> DirectM6FactsV1:
    from tools.automation.implementations.m6_authoritative_evidence import (
        AuthoritativeComparisonV1,
    )

    official = AuthoritativeComparisonV1(
        "agentmonitor.m6_authoritative_comparison.v1",
        "1.1.0",
        "passed",
        "official_usage_compared",
        "a" * 40,
        2,
        "b" * 64,
        "c" * 64,
        "2026-11-03T12:00:00Z",
        "2026-11-03T12:00:10Z",
        "2026-11-03T12:00:09Z",
        "2026-11-03T11:59:00Z",
    )
    from tools.automation.implementations.m6_recovery_evidence import (
        RecoveryIntervalEvidenceV1,
    )

    interval = RecoveryIntervalEvidenceV1(
        "agentmonitor.m6_recovery_interval.v1",
        "1.0.0",
        "passed",
        "m6_recovery_observed",
        "a" * 40,
        "b" * 32,
        1,
        1,
        2,
        "c" * 64,
        "2026-11-03T12:00:00+00:00",
        "2026-11-03T12:01:00+00:00",
        ("2026-11-03T12:00:10+00:00", "2026-11-03T12:01:00+00:00"),
        (("claude", "run-claude"), ("codex", "run-codex")),
        (("run-failed", "run-recovered"),),
    )
    return DirectM6FactsV1(
        local_admission=PASSED,
        local_inventory=PASSED,
        account_admin_browser=PASSED,
        cloud_capacity_browser=PASSED,
        capacity_history_browser=PASSED,
        process_browser=PASSED,
        dashboard_continuity_browser=PASSED,
        source_security=PASSED,
        database_snapshot=PASSED,
        cloud_scope_evidence=_scope(),
        authoritative_comparison=PASSED,
        authoritative_observation=official,
        recovery_interval=interval,
        recovery_observation=PASSED,
        active_ollama_accounts=2,
        registered_local_installations=2,
        observed_local_installations=2,
        observed_model_hosts=2,
        model_host_evidence=HOSTS,
        active_cloud_targets=2,
        owner_confirmed_cloud_targets=2,
        owner_confirmed_required_scopes=2,
        verified_cloud_targets=2,
        current_balance_targets=2,
        authoritative_balance_reconciled_targets=2,
        history_targets=2,
        history_lineage_reconciled_targets=2,
        configured_alert_targets=2,
        alerted_targets=2,
        process_observation_count=2,
        natural_recovery_targets=1,
        cross_provider_continuity_targets=1,
    )


def test_direct_policy_can_pass_the_cloud_external_catalog() -> None:
    outcomes = classify_direct_m6_evidence_v1(_complete_facts())

    assert set(outcomes) == {
        *(f"M6-A{index:02}" for index in (1, 3, 4, 5, 7, 8, 9)),
        *(f"ST-OLL-{index:03}" for index in (1, 3, 4, 5)),
    }
    assert {item.status for item in outcomes.values()} == {"passed"}
    assert outcomes["M6-A07"].declared_limitations == (
        "sampled_dashboard_and_collection_continuity",
    )

    assert outcomes["ST-OLL-005"].declared_limitations == (
        "sampled_dashboard_and_collection_continuity",
    )
    assert all(item.test_count > 0 for item in outcomes.values())


def test_balance_comparison_preserves_unavailable_reset_limitation() -> None:
    facts = _complete_facts()
    proof = replace(
        facts.authoritative_observation,
        reset_unavailable_targets=1,
        reason_code="official_usage_balances_compared_reset_unavailable",
    )
    outcomes = classify_direct_m6_evidence_v1(
        replace(facts, authoritative_observation=proof)
    )
    assert outcomes["M6-A04"].status == "passed"
    assert (
        "official_reset_comparison_unavailable"
        in outcomes["M6-A04"].declared_limitations
    )


def test_counts_alone_cannot_prove_the_intended_organization_selection() -> None:
    outcomes = classify_direct_m6_evidence_v1(
        replace(_complete_facts(), cloud_scope_evidence=None)
    )
    assert outcomes["M6-A03"].status == "not_run"
    assert outcomes["M6-A03"].reason_code == "intended_cloud_scope_not_selected"


def test_two_owner_scopes_may_reference_one_real_cloud_target() -> None:
    facts = replace(
        _complete_facts(),
        cloud_scope_evidence=_scope(True),
        active_ollama_accounts=1,
        active_cloud_targets=1,
        owner_confirmed_cloud_targets=1,
        owner_confirmed_required_scopes=2,
        verified_cloud_targets=1,
        current_balance_targets=1,
        authoritative_balance_reconciled_targets=1,
        history_targets=1,
        history_lineage_reconciled_targets=1,
    )
    assert facts.owner_confirmed_required_scopes == 2


def test_every_python_evidence_command_disables_bytecode_writes() -> None:
    commands = dict(DIRECT_EXECUTABLE_SELECTION_V1)

    assert "local_inventory" not in commands
    assert commands["source_security"][0:3] == (
        "/usr/bin/env",
        "PYTHONPATH=backend/src",
        "PYTHONDONTWRITEBYTECODE=1",
    )
    assert commands["source_security"][4] == "-B"
    assert (
        "backend/tests/adapters/providers/claude/test_usage_failure_cadence.py"
        in commands["source_security"]
    )
    assert commands["database_snapshot"][0:3] == (
        "/usr/bin/env",
        "PYTHONPATH=backend/src",
        "PYTHONDONTWRITEBYTECODE=1",
    )
    assert "-B" in commands["database_snapshot"]
    assert (
        "backend/tests/collection_control/domain/test_ollama_latest_source_signal.py"
        in commands["source_security"]
    )


def test_absent_real_cloud_state_preserves_security_and_continuity_results() -> None:
    facts = replace(
        _complete_facts(),
        cloud_scope_evidence=None,
        active_ollama_accounts=0,
        active_cloud_targets=0,
        owner_confirmed_cloud_targets=0,
        owner_confirmed_required_scopes=0,
        verified_cloud_targets=0,
        current_balance_targets=0,
        authoritative_balance_reconciled_targets=0,
        history_targets=0,
        history_lineage_reconciled_targets=0,
        configured_alert_targets=0,
        alerted_targets=0,
        natural_recovery_targets=0,
        cross_provider_continuity_targets=0,
        recovery_interval=None,
        recovery_observation=BoundaryCheckV1(
            "not_run", 0, reason_code="recovery_interval_not_observed"
        ),
    )

    outcomes = classify_direct_m6_evidence_v1(facts)

    assert outcomes["M6-A08"].status == "passed"
    assert outcomes["ST-OLL-001"].status == "passed"
    assert outcomes["M6-A03"].status == "not_run"
    assert outcomes["M6-A04"].status == "not_run"
    assert outcomes["ST-OLL-003"].status == "not_run"
    assert outcomes["ST-OLL-005"].status == "not_run"


def test_real_boundary_failure_is_failed_not_absent() -> None:
    facts = replace(
        _complete_facts(),
        source_security=BoundaryCheckV1("failed", 1),
    )

    outcomes = classify_direct_m6_evidence_v1(facts)

    assert outcomes["M6-A09"].status == "failed"
    assert outcomes["ST-OLL-001"].status == "failed"
    assert outcomes["ST-OLL-005"].status == "failed"


def test_no_alert_is_required_when_no_real_rule_targets_ollama() -> None:
    outcomes = classify_direct_m6_evidence_v1(
        replace(
            _complete_facts(),
            configured_alert_targets=0,
            alerted_targets=0,
        )
    )

    assert outcomes["M6-A05"].status == "passed"


def test_missing_history_does_not_erase_a_reconciled_current_balance() -> None:
    outcomes = classify_direct_m6_evidence_v1(
        replace(
            _complete_facts(),
            capacity_history_browser=BoundaryCheckV1(
                "not_run", 0, reason_code="real_ollama_history_unavailable"
            ),
            history_targets=0,
            history_lineage_reconciled_targets=0,
        )
    )

    assert outcomes["M6-A04"].status == "passed"
    assert outcomes["M6-A05"].status == "not_run"


def test_internal_capacity_lineage_never_substitutes_for_provider_comparison() -> None:
    outcomes = classify_direct_m6_evidence_v1(
        replace(
            _complete_facts(),
            authoritative_balance_reconciled_targets=0,
        )
    )

    assert outcomes["M6-A04"].status == "not_run"
    assert outcomes["M6-A04"].reason_code == (
        "authoritative_cloud_balance_not_observed"
    )
    assert outcomes["M6-A05"].status == "not_run"


def test_unbound_historical_runs_never_substitute_for_exact_recovery() -> None:
    outcomes = classify_direct_m6_evidence_v1(
        replace(
            _complete_facts(),
            natural_recovery_targets=0,
            cross_provider_continuity_targets=0,
            recovery_interval=None,
            recovery_observation=BoundaryCheckV1(
                "not_run", 0, reason_code="recovery_interval_not_observed"
            ),
        )
    )

    assert outcomes["M6-A07"].status == "not_run"
    assert outcomes["M6-A07"].reason_code == ("recovery_interval_not_observed")


def test_direct_bundle_uses_one_shared_artifact_without_producer_receipts() -> None:
    from tools.automation.test_m6_exit import _catalog

    recorded = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
    outcomes = classify_direct_m6_evidence_v1(_complete_facts())
    bundle = direct_bundle_v1(
        outcomes,
        catalog=_catalog(),
        artifact_path=".agentmonitor-local/m6-evidence/direct-a.json",
        artifact_sha256="b" * 64,
        implementation_revision="a" * 40,
        catalog_sha256="c" * 64,
        recorded_at=recorded,
    )

    assert {item["path"] for item in bundle["evidence"]} == {
        ".agentmonitor-local/m6-evidence/direct-a.json"
    }
    assert {item["producer_id"] for item in bundle["evidence"]} == {"AUTO-M6-EXIT"}
    assert len(bundle["evidence"]) == 11


def test_direct_bundle_preserves_exact_not_run_reason() -> None:
    from tools.automation.test_m6_exit import _catalog

    recorded = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
    outcomes = classify_direct_m6_evidence_v1(
        replace(
            _complete_facts(),
            cloud_scope_evidence=None,
        )
    )
    bundle = direct_bundle_v1(
        outcomes,
        catalog=_catalog(),
        artifact_path=".agentmonitor-local/m6-evidence/direct-a.json",
        artifact_sha256="b" * 64,
        implementation_revision="a" * 40,
        catalog_sha256="c" * 64,
        recorded_at=recorded,
    )
    evaluation = evaluate_evidence_bundle_v1(
        bundle,
        catalog=_catalog(),
        expected_revision="a" * 40,
        expected_catalog_sha256="c" * 64,
        now=recorded,
    )

    assert evaluation.acceptance["M6-A03"] == "not_run"
    assert "intended_cloud_scope_not_selected" not in evaluation.reason_codes
    row = next(item for item in bundle["acceptance"] if item["id"] == "M6-A03")
    assert row["reason_code"] == "intended_cloud_scope_not_selected"


def test_direct_bundle_rejects_a_different_catalog_policy_digest() -> None:
    from tools.automation.test_m6_exit import _catalog

    catalog = _catalog()
    catalog["selectors"][0]["selection_sha256"] = "f" * 64

    try:
        direct_bundle_v1(
            classify_direct_m6_evidence_v1(_complete_facts()),
            catalog=catalog,
            artifact_path=".agentmonitor-local/m6-evidence/direct-a.json",
            artifact_sha256="b" * 64,
            implementation_revision="a" * 40,
            catalog_sha256="c" * 64,
            recorded_at=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert str(error) == "m6_direct_catalog_policy_mismatch"
    else:
        raise AssertionError("changed direct policy digest was accepted")


def test_unavailable_dashboard_session_does_not_become_a_missing_capacity_ui() -> None:
    facts = replace(
        _complete_facts(),
        cloud_capacity_browser=BoundaryCheckV1(
            "not_run", 0, reason_code="signed_in_dashboard_unavailable"
        ),
    )

    outcomes = classify_direct_m6_evidence_v1(facts)

    for scope_id in ("M6-A04", "M6-A05", "M6-A09"):
        assert outcomes[scope_id].status == "not_run"
        assert outcomes[scope_id].reason_code == "signed_in_dashboard_unavailable"


def test_authenticated_missing_capacity_ui_remains_a_failure() -> None:
    facts = replace(
        _complete_facts(),
        cloud_capacity_browser=BoundaryCheckV1(
            "not_run", 0, reason_code="real_ollama_balance_unavailable"
        ),
    )

    outcomes = classify_direct_m6_evidence_v1(facts)

    for scope_id in ("M6-A04", "M6-A05", "M6-A09"):
        assert outcomes[scope_id].status == "failed"
        assert outcomes[scope_id].reason_code == "ollama_capacity_ui_missing"


def test_blocked_dashboard_capacity_check_stays_blocked() -> None:
    facts = replace(
        _complete_facts(),
        cloud_capacity_browser=BoundaryCheckV1(
            "blocked", 0, reason_code="dashboard_registry_changed_concurrently"
        ),
    )

    outcomes = classify_direct_m6_evidence_v1(facts)

    for scope_id in ("M6-A04", "M6-A05", "M6-A09"):
        assert outcomes[scope_id].status == "blocked"
        assert outcomes[scope_id].reason_code == (
            "dashboard_registry_changed_concurrently"
        )


def test_recovery_counts_without_actual_interval_are_not_evidence() -> None:
    facts = replace(
        _complete_facts(),
        recovery_interval=None,
        recovery_observation=BoundaryCheckV1(
            "not_run", 0, reason_code="recovery_interval_not_observed"
        ),
    )
    outcomes = classify_direct_m6_evidence_v1(facts)
    assert outcomes["M6-A07"].status == "not_run"


def test_invalid_recovery_producer_is_not_hidden_by_positive_counts() -> None:
    facts = replace(
        _complete_facts(),
        recovery_observation=BoundaryCheckV1(
            "failed", 1, reason_code="m6_recovery_producer_invalid"
        ),
    )
    assert classify_direct_m6_evidence_v1(facts)["M6-A07"].status == "failed"


def test_counts_without_an_official_comparison_cannot_pass_a04() -> None:
    assert (
        classify_direct_m6_evidence_v1(
            replace(_complete_facts(), authoritative_observation=None)
        )["M6-A04"].status
        == "not_run"
    )


def test_official_comparison_count_must_exactly_match_reconciled_targets() -> None:
    facts = _complete_facts()
    proof = facts.authoritative_observation
    assert proof is not None
    for compared_targets in (1, 3):
        outcome = classify_direct_m6_evidence_v1(
            replace(
                facts,
                authoritative_observation=replace(
                    proof, compared_targets=compared_targets
                ),
            )
        )["M6-A04"]
        assert outcome.status == "not_run"


def test_current_healthy_configured_targets_need_no_invented_alert() -> None:
    outcomes = classify_direct_m6_evidence_v1(
        replace(_complete_facts(), alerted_targets=0, alert_no_transition_targets=2)
    )
    assert outcomes["M6-A05"].status == "passed"


def test_unproven_configured_target_still_requires_real_evidence() -> None:
    outcomes = classify_direct_m6_evidence_v1(
        replace(_complete_facts(), alerted_targets=0, alert_no_transition_targets=1)
    )
    assert outcomes["M6-A05"].status == "not_run"


def test_no_transition_count_cannot_double_count_real_alerted_target() -> None:
    with pytest.raises(ValueError, match="m6_direct_fact_relationship_invalid"):
        replace(_complete_facts(), alert_no_transition_targets=1)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("3100", "none"), ("3000", "transition"), ("1500", "transition")],
)
def test_only_threshold_crossing_requires_a_transition(
    value: str, expected: str
) -> None:
    assert (
        _alert_window_requirement(
            fact(value), builtin_rule("capacity_remaining"), False, False, NOW
        )
        == expected
    )


def test_recovery_of_an_open_alert_still_requires_actual_transition() -> None:
    assert (
        _alert_window_requirement(
            fact("9000"), builtin_rule("capacity_remaining"), True, False, NOW
        )
        == "transition"
    )


def test_matching_current_alert_must_still_prove_deduplication() -> None:
    assert (
        _alert_window_requirement(
            fact("9000"), builtin_rule("capacity_remaining"), False, True, NOW
        )
        == "transition"
    )


def test_fresh_nonconstraining_window_needs_no_initial_transition() -> None:
    source = replace(
        fact(),
        availability="unavailable",
        remaining_basis_points=None,
        exhausted=None,
        denominator_kind="unknown",
        reason_code="capacity_nonconstraining",
    )
    assert (
        _alert_window_requirement(
            source, builtin_rule("capacity_remaining"), False, False, NOW
        )
        == "none"
    )
    assert (
        _alert_window_requirement(
            source, builtin_rule("capacity_remaining"), True, False, NOW
        )
        == "transition"
    )


@pytest.mark.parametrize("state", ["stale", "unknown", "unsupported", "unavailable"])
def test_unevaluable_reading_cannot_prove_no_transition(
    state: CapacityAlertAvailabilityV1,
) -> None:
    source = replace(
        fact(),
        availability=state,
        remaining_basis_points=None,
        exhausted=None,
        denominator_kind="unknown",
    )
    assert (
        _alert_window_requirement(
            source, builtin_rule("capacity_remaining"), False, False, NOW
        )
        == "unavailable"
    )


def test_expired_current_reading_cannot_prove_no_transition() -> None:
    assert (
        _alert_window_requirement(
            fact("9000"),
            builtin_rule("capacity_remaining"),
            False,
            False,
            NOW + timedelta(minutes=10),
        )
        == "unavailable"
    )


def test_same_capacity_event_can_have_two_distinct_window_alerts() -> None:
    assert _unique_alert_event_keys(
        (("rule", "window_one", "event"), ("rule", "window_two", "event"))
    )


def test_repeated_same_window_rule_and_event_is_still_duplicate() -> None:
    assert not _unique_alert_event_keys(
        (("rule", "window_one", "event"), ("rule", "window_one", "event"))
    )


def _controlled_facts():
    from tools.automation.implementations.m6_controlled_recovery_evidence import (
        build_controlled_recovery_evidence_v1,
    )
    from tools.automation.test_m6_controlled_recovery_evidence import arguments

    return replace(
        _complete_facts(),
        recovery_interval=None,
        recovery_observation=BoundaryCheckV1(
            "not_run", 0, reason_code="m6_recovery_current_natural_failure_absent"
        ),
        natural_recovery_targets=0,
        controlled_recovery_targets=1,
        controlled_recovery_interval=build_controlled_recovery_evidence_v1(
            **arguments()
        ),
        controlled_recovery_observation=PASSED,
    )


def test_controlled_recovery_satisfies_a07_without_claiming_natural_failure():
    facts = _controlled_facts()
    outcomes = classify_direct_m6_evidence_v1(facts)
    assert outcomes["M6-A07"].status == "passed"
    assert outcomes["ST-OLL-005"].status == "passed"
    assert facts.natural_recovery_targets == 0
    assert (
        "provider_side_401_403_429_not_observed"
        in outcomes["M6-A07"].declared_limitations
    )
    assert (
        "provider_side_401_403_429_not_observed"
        in outcomes["ST-OLL-005"].declared_limitations
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"controlled_recovery_interval": None},
        {"controlled_recovery_targets": 0},
        {"natural_recovery_targets": 1},
        {"cross_provider_continuity_targets": 0},
        {
            "controlled_recovery_observation": BoundaryCheckV1(
                "failed", 1, reason_code="m6_controlled_recovery_producer_invalid"
            )
        },
        {
            "recovery_observation": BoundaryCheckV1(
                "failed", 1, reason_code="m6_recovery_producer_invalid"
            )
        },
    ],
)
def test_controlled_receipt_cannot_hide_invalid_or_incomplete_evidence(changes):
    facts = replace(_controlled_facts(), **changes)
    assert classify_direct_m6_evidence_v1(facts)["M6-A07"].status == "failed"


def test_controlled_count_without_receipt_cannot_bypass_natural_path():
    facts = replace(_complete_facts(), controlled_recovery_targets=1)
    assert classify_direct_m6_evidence_v1(facts)["M6-A07"].status == "failed"


def test_attempted_controlled_unavailability_keeps_its_specific_reason():
    facts = replace(
        _controlled_facts(),
        controlled_recovery_targets=0,
        controlled_recovery_interval=None,
        cross_provider_continuity_targets=0,
        controlled_recovery_observation=BoundaryCheckV1(
            "not_run", 0, reason_code="m6_controlled_target_unavailable"
        ),
    )
    outcome = classify_direct_m6_evidence_v1(facts)["M6-A07"]
    assert outcome.status == "not_run"
    assert outcome.reason_code == "m6_controlled_target_unavailable"
