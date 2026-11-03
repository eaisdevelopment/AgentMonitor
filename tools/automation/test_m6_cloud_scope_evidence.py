"""Pure scope policy; constructed facts never cross an I/O boundary."""

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_coverage_v1 import (
    OrganizationProviderCoverageSelectionV1,
    OrganizationProviderCoverageSnapshotV1,
    OrganizationProviderCoverageV1,
)

from tools.automation.implementations.m6_direct_evidence import (
    classify_direct_m6_evidence_v1,
    cloud_reference_digest_v1,
    parse_cloud_scope_evidence_v1,
)
from tools.automation.implementations.m6_real_snapshot import (
    cloud_scope_evidence_from_registry_v1,
)
from tools.automation.test_m6_direct_evidence import _complete_facts, _scope

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


def _record(organization="org-a", *, shared=False):
    return OrganizationProviderCoverageV1(
        OpaqueIdV1("coverage-" + organization),
        OpaqueIdV1(organization),
        "ollama",
        "shared" if shared else "account",
        OpaqueIdV1("account-a"),
        OpaqueIdV1("org-a"),
        None,
        "owner_asserted",
        OpaqueIdV1("principal"),
        NOW,
        1,
        4,
        None,
        None,
    )


def _snapshot(items):
    return OrganizationProviderCoverageSnapshotV1(
        OrganizationProviderCoverageSelectionV1(
            (OpaqueIdV1("org-a"), OpaqueIdV1("org-b")), "ollama"
        ),
        items,
        4,
        "complete",
        NOW,
    )


def test_real_contract_projection_keeps_two_scopes_and_one_target() -> None:
    target = "a" * 64
    evidence = cloud_scope_evidence_from_registry_v1(
        _snapshot((_record(), _record("org-b", shared=True))),
        {OpaqueIdV1("account-a"): target},
        {target},
        {target},
    )
    assert len(evidence.scopes) == 2
    assert evidence.owner_confirmed_scopes == 2
    assert evidence.active_target_sha256s == (target,)
    assert evidence.scopes[1].disposition == "shared"
    payload = json.loads(json.dumps(evidence.as_json()))
    assert (
        parse_cloud_scope_evidence_v1(
            payload, expected_organization_ids=("org-a", "org-b")
        )
        == evidence
    )


def test_missing_declared_scope_survives_projection() -> None:
    evidence = cloud_scope_evidence_from_registry_v1(
        _snapshot((_record(),)), {}, set(), set()
    )
    assert len(evidence.scopes) == 2
    assert evidence.scopes[1].disposition == "missing"
    assert evidence.owner_confirmed_scopes == 0


def test_unavailable_is_not_live_quota_evidence() -> None:
    scope = _scope()
    unavailable = replace(
        scope.scopes[1],
        disposition="unavailable",
        account_sha256=None,
        target_sha256=None,
        reason_code="subscription_unavailable",
    )
    evidence = replace(scope, scopes=(scope.scopes[0], unavailable))
    facts = replace(
        _complete_facts(),
        cloud_scope_evidence=evidence,
        owner_confirmed_required_scopes=1,
    )
    outcomes = classify_direct_m6_evidence_v1(facts)
    assert outcomes["M6-A03"].reason_code == "required_cloud_scope_unavailable"
    assert all(
        outcomes[key].status == "not_run"
        for key in ("M6-A03", "M6-A04", "M6-A05", "M6-A09")
    )
    assert facts.active_cloud_targets == 2


def test_shared_one_target_can_pass_cloud_criteria_with_real_proof_shape() -> None:
    facts = _complete_facts()
    facts = replace(
        facts,
        cloud_scope_evidence=_scope(True),
        active_ollama_accounts=1,
        active_cloud_targets=1,
        owner_confirmed_cloud_targets=1,
        verified_cloud_targets=1,
        current_balance_targets=1,
        authoritative_balance_reconciled_targets=1,
        history_targets=1,
        history_lineage_reconciled_targets=1,
        authoritative_observation=replace(
            facts.authoritative_observation, compared_targets=1
        ),
    )
    outcomes = classify_direct_m6_evidence_v1(facts)
    assert all(
        outcomes[key].status == "passed"
        for key in ("M6-A03", "M6-A04", "M6-A05", "M6-A09")
    )


def test_undeclared_extra_active_target_stays_in_the_live_denominator() -> None:
    scope = _scope()
    scope = replace(
        scope,
        active_target_sha256s=(*scope.active_target_sha256s, "c" * 64),
        owner_confirmed_target_sha256s=(
            *scope.owner_confirmed_target_sha256s,
            "c" * 64,
        ),
    )
    facts = replace(
        _complete_facts(),
        cloud_scope_evidence=scope,
        active_cloud_targets=3,
        active_ollama_accounts=3,
        owner_confirmed_cloud_targets=3,
    )
    outcomes = classify_direct_m6_evidence_v1(facts)
    assert outcomes["M6-A03"].status == "passed"
    assert outcomes["M6-A04"].status == "not_run"
    with pytest.raises(ValueError, match="m6_direct_scope_count_mismatch"):
        replace(facts, active_cloud_targets=2, owner_confirmed_cloud_targets=2)


@pytest.mark.parametrize(
    "change",
    ("drop", "duplicate", "wrong_selection", "extra_field", "wrong_type", "bad_digest"),
)
def test_closed_parser_rejects_malformed_or_changed_selection(change) -> None:
    payload = json.loads(json.dumps(_scope().as_json()))
    expected = ("org-a", "org-b")
    if change == "drop":
        payload["scopes"].pop()
    elif change == "duplicate":
        payload["scopes"][1] = payload["scopes"][0]
    elif change == "wrong_selection":
        expected = ("org-a", "org-c")
    elif change == "extra_field":
        payload["provider_proven"] = True
    elif change == "wrong_type":
        payload["scopes"][0]["disposition"] = []
    else:
        payload["active_target_sha256s"] = [[]]
    with pytest.raises(ValueError):
        parse_cloud_scope_evidence_v1(payload, expected_organization_ids=expected)


def test_parser_cannot_merge_different_accounts_into_one_target() -> None:
    scope = _scope()
    second = replace(scope.scopes[1], target_sha256=scope.scopes[0].target_sha256)
    with pytest.raises(ValueError):
        replace(scope, scopes=(scope.scopes[0], second))


def test_invalidated_owner_statement_remains_visible_and_unproven() -> None:
    scope = _scope()
    invalidated = replace(
        scope.scopes[1],
        disposition="invalidated",
        target_sha256=None,
        reason_code="account_reassigned",
        record_version=2,
    )
    evidence = replace(scope, scopes=(scope.scopes[0], invalidated))
    facts = replace(
        _complete_facts(),
        cloud_scope_evidence=evidence,
        owner_confirmed_required_scopes=1,
    )
    assert classify_direct_m6_evidence_v1(facts)["M6-A03"].status == "not_run"


def test_reference_digests_have_distinct_domains() -> None:
    assert cloud_reference_digest_v1(
        "organization", "same"
    ) != cloud_reference_digest_v1("account", "same")
