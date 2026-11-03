"""Pure policy checks for direct, single-command M6 evidence selection."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from tools.automation.implementations.m6_direct_evidence import (
    DIRECT_EXECUTABLE_SELECTION_V1,
    BoundaryCheckV1,
    DirectM6FactsV1,
    LocalModelHostEvidenceV1,
    classify_direct_m6_evidence_v1,
    direct_bundle_v1,
)
from tools.automation.implementations.m6_exit_policy import evaluate_evidence_bundle_v1

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
        0,
        0,
        "2026-11-02T12:00:00Z",
    ),
)


def _complete_facts() -> DirectM6FactsV1:
    from tools.automation.implementations.m6_authoritative_evidence import (
        AuthoritativeComparisonV1,
    )

    official = AuthoritativeComparisonV1(
        "agentmonitor.m6_authoritative_comparison.v1",
        "1.0.0",
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


def test_direct_policy_can_pass_the_original_external_catalog() -> None:
    outcomes = classify_direct_m6_evidence_v1(_complete_facts())

    assert set(outcomes) == {
        *(f"M6-A{index:02}" for index in range(1, 10)),
        *(f"ST-OLL-{index:03}" for index in range(1, 6)),
    }
    assert {item.status for item in outcomes.values()} == {"passed"}
    assert outcomes["M6-A06"].declared_limitations == ("sampled_process_coverage",)
    assert outcomes["M6-A07"].declared_limitations == (
        "sampled_dashboard_and_collection_continuity",
    )
    assert outcomes["ST-OLL-005"].declared_limitations == (
        "sampled_process_coverage",
        "sampled_dashboard_and_collection_continuity",
    )
    assert all(item.test_count > 0 for item in outcomes.values())


def test_every_python_evidence_command_disables_bytecode_writes() -> None:
    commands = dict(DIRECT_EXECUTABLE_SELECTION_V1)

    assert commands["local_inventory"][1] == "-B"
    assert commands["source_security"][1] == "-B"
    assert commands["database_snapshot"][0:3] == (
        "/usr/bin/env",
        "PYTHONPATH=backend/src",
        "PYTHONDONTWRITEBYTECODE=1",
    )
    assert "-B" in commands["database_snapshot"]


def test_absent_real_cloud_state_does_not_hide_local_results() -> None:
    facts = replace(
        _complete_facts(),
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

    assert outcomes["M6-A02"].status == "passed"
    assert outcomes["M6-A06"].status == "passed"
    assert outcomes["M6-A08"].status == "passed"
    assert outcomes["ST-OLL-001"].status == "passed"
    assert outcomes["ST-OLL-002"].status == "passed"
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


def test_a_second_available_machine_is_required_for_local_acceptance() -> None:
    outcomes = classify_direct_m6_evidence_v1(
        replace(
            _complete_facts(),
            registered_local_installations=1,
            observed_local_installations=1,
            observed_model_hosts=1,
            model_host_evidence=HOSTS[:1],
        )
    )

    assert outcomes["M6-A02"].status == "not_run"
    assert outcomes["M6-A02"].reason_code == "second_local_host_not_observed"
    assert outcomes["ST-OLL-002"].status == "not_run"


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
    assert len(bundle["evidence"]) == 14


def test_direct_bundle_preserves_exact_not_run_reason() -> None:
    from tools.automation.test_m6_exit import _catalog

    recorded = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
    outcomes = classify_direct_m6_evidence_v1(
        replace(
            _complete_facts(),
            registered_local_installations=1,
            observed_local_installations=1,
            observed_model_hosts=1,
            model_host_evidence=HOSTS[:1],
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

    assert evaluation.acceptance["M6-A02"] == "not_run"
    assert "second_local_host_not_observed" not in evaluation.reason_codes
    row = next(item for item in bundle["acceptance"] if item["id"] == "M6-A02")
    assert row["reason_code"] == "second_local_host_not_observed"


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


def test_unavailable_browser_stays_not_run_with_process_observations() -> None:
    facts = replace(
        _complete_facts(),
        process_browser=BoundaryCheckV1(
            "not_run", 0, reason_code="signed_in_dashboard_unavailable"
        ),
    )

    outcome = classify_direct_m6_evidence_v1(facts)["M6-A06"]

    assert outcome.status == "not_run"
    assert outcome.reason_code == "signed_in_dashboard_unavailable"


def test_disappeared_process_stays_not_run_after_database_observation() -> None:
    facts = replace(
        _complete_facts(),
        process_browser=BoundaryCheckV1(
            "not_run", 0, reason_code="real_ollama_process_unavailable"
        ),
    )

    outcome = classify_direct_m6_evidence_v1(facts)["M6-A06"]

    assert outcome.status == "not_run"
    assert outcome.reason_code == "real_ollama_process_unavailable"


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
