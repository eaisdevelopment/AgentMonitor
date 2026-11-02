"""Pure completion policy and repository catalog checks for AUTO-M6-EXIT."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.automation.implementations.auto_m6_exit import (
    PROJECT_BACKEND_VENV,
    M6ExitErrorV1,
    _artifact_parts,
    _open_directory_chain,
    _print_result,
    _terminate_process_group,
    _unlink_created_receipt,
)
from tools.automation.implementations.m6_direct_evidence import (
    direct_policy_hashes_v1,
)
from tools.automation.implementations.m6_exit_policy import (
    ACCEPTANCE_IDS,
    SELECTOR_REQUIREMENTS,
    STORY_IDS,
    assemble_selector_bundle_v1,
    build_passed_receipt_v1,
    evaluate_evidence_bundle_v1,
    external_scope_status_v1,
    validate_catalog_v1,
    validate_existing_passed_receipt_v1,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION = "a" * 40
DIGEST = "b" * 64
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def _catalog(*, frozen: bool = True) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_type": "agentmonitor.m6_exit_catalog.v1",
        "milestone_id": "V1-M6",
        "acceptance_ids": list(ACCEPTANCE_IDS),
        "story_ids": list(STORY_IDS),
        "required_checks": [
            "AUTO-BUILD",
            "AUTO-M6-LOCAL-ADMIT",
            "AUTO-QUALITY",
            "AUTO-DOCS-CHECK",
            "AUTO-PLAN-CHECK",
        ],
        "selectors": [
            {
                "scope_id": scope_id,
                "selector_id": selector_id,
                "boundary": boundary,
                "producer_command_id": producer_command_id,
                "producer_version": "1.0.0",
                "selection_policy_id": selection_policy_id,
                "source_versions_policy_id": source_versions_policy_id,
                "selection_sha256": direct_policy_hashes_v1(
                    scope_id, selection_policy_id, source_versions_policy_id
                )[0]
                if frozen
                else None,
                "source_versions_sha256": direct_policy_hashes_v1(
                    scope_id, selection_policy_id, source_versions_policy_id
                )[1]
                if frozen
                else None,
                "required_limitations": list(required_limitations),
            }
            for (
                scope_id,
                selector_id,
                boundary,
                producer_command_id,
                required_limitations,
                selection_policy_id,
                source_versions_policy_id,
            ) in SELECTOR_REQUIREMENTS
        ],
    }


def _selector(scope_id: str, *, status: str = "passed") -> dict[str, object]:
    requirement = next(item for item in SELECTOR_REQUIREMENTS if item[0] == scope_id)
    selection, source_versions = direct_policy_hashes_v1(
        scope_id, requirement[5], requirement[6]
    )
    evidence = {
        "evidence_id": "E-" + requirement[1],
        "path": "docs/evidence/m6-completion-boundaries.json",
        "sha256": DIGEST,
        "scope_ids": [scope_id],
        "result": status,
        "producer_id": requirement[3],
        "producer_version": "1.0.0",
        "exit_code": 0 if status == "passed" else 1 if status == "failed" else 3,
        "test_count": 1,
        "skip_count": 0,
        "implementation_revision": REVISION,
        "observed_at": "2026-11-02T11:50:00Z",
        "valid_until": "2026-11-02T12:10:00Z",
    }
    return {
        "schema_version": "1.0.0",
        "record_type": "agentmonitor.m6_selector_receipt.v1",
        "selector_id": requirement[1],
        "boundary": requirement[2],
        "selection_policy_id": requirement[5],
        "source_versions_policy_id": requirement[6],
        "selection_sha256": selection,
        "source_versions_sha256": source_versions,
        "evidence": evidence,
        "reason_code": None if status == "passed" else "real_boundary_not_available",
        "declared_limitations": list(requirement[4]),
    }


def _bundle(*, status: str = "passed") -> dict[str, object]:
    receipts = (
        ()
        if status == "not_run"
        else tuple(
            _selector(scope_id, status=status)
            for scope_id in (item[0] for item in SELECTOR_REQUIREMENTS)
        )
    )
    return assemble_selector_bundle_v1(
        receipts,
        catalog=_catalog(),
        producer_statuses=_producer_statuses(status),
        expected_revision=REVISION,
        catalog_sha256=DIGEST,
        recorded_at=NOW,
    )


def _producer_statuses(
    status: str = "not_run", *, passed_selector: str | None = None
) -> dict[str, str]:
    values = {item[1]: status for item in SELECTOR_REQUIREMENTS}
    if passed_selector is not None:
        values[passed_selector] = "passed"
    return values


def test_repository_catalog_is_exact_and_versioned() -> None:
    catalog = json.loads(
        (ROOT / "tools/automation/m6-exit-catalog-v1.json").read_text(encoding="utf-8")
    )

    assert validate_catalog_v1(catalog) == ()
    assert catalog == _catalog()
    selector_scopes = {item["scope_id"] for item in catalog["selectors"]}
    assert "M6-A10" not in selector_scopes


def test_directory_chain_rejects_an_intermediate_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    os.symlink(target.name, tmp_path / "alias")

    with (
        pytest.raises(M6ExitErrorV1, match="m6_directory_chain_invalid"),
        _open_directory_chain(("alias",), private=False, root_path=tmp_path),
    ):
        pass


def test_artifact_parts_reject_parent_traversal_before_io() -> None:
    with pytest.raises(M6ExitErrorV1, match="m6_evidence_path_invalid"):
        _artifact_parts("docs/evidence/../../.env")


def test_receipt_cleanup_never_unlinks_a_replacement(tmp_path: Path) -> None:
    original = tmp_path / "receipt.json"
    original.write_text("original", encoding="utf-8")
    created = os.open(original, os.O_RDONLY)
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        original.unlink()
        original.write_text("replacement", encoding="utf-8")
        assert not _unlink_created_receipt(
            directory,
            original.name,
            created_fd=created,
        )
    finally:
        os.close(created)
        os.close(directory)
    assert original.read_text(encoding="utf-8") == "replacement"


def test_timeout_cleanup_terminates_the_real_process_group() -> None:
    script = (
        "import subprocess,sys,time;"
        "subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']);"
        "time.sleep(60)"
    )
    process = subprocess.Popen([sys.executable, "-c", script], start_new_session=True)
    time.sleep(0.1)

    assert _terminate_process_group(process)


def test_canonical_dispatcher_registers_operational_m6_exit() -> None:
    routines = tomllib.loads(
        (ROOT / "tools/automation/routines.toml").read_text(encoding="utf-8")
    )["routines"]
    routine = next(item for item in routines if item["id"] == "AUTO-M6-EXIT")

    assert routine["status"] == "operational"
    assert routine["implementation_command"] == [
        "python3",
        "-m",
        "tools.automation.implementations.auto_m6_exit",
    ]
    assert routine["blockers"] == []


def test_gate_never_uses_the_sealed_release_runtime_as_a_build_tool() -> None:
    assert PROJECT_BACKEND_VENV == Path(
        "/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv"
    )
    assert "/releases/" not in str(PROJECT_BACKEND_VENV)


def test_m6_exit_owns_direct_selector_checks_without_fourteen_subroutines() -> None:
    routines = tomllib.loads(
        (ROOT / "tools/automation/routines.toml").read_text(encoding="utf-8")
    )["routines"]
    routine_ids = {item["id"] for item in routines}
    catalog = json.loads(
        (ROOT / "tools/automation/m6-exit-catalog-v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert not any(item.startswith("AUTO-M6-EVIDENCE-") for item in routine_ids)
    assert {item["producer_command_id"] for item in catalog["selectors"]} == {
        "AUTO-M6-EXIT"
    }
    assert all(item["selection_sha256"] is not None for item in catalog["selectors"])
    assert all(
        item["source_versions_sha256"] is not None for item in catalog["selectors"]
    )


def test_success_output_is_explicitly_technical_not_milestone_completion(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _print_result(
        status="passed",
        revision=REVISION,
        catalog_digest=DIGEST,
        evidence_digest="c" * 64,
        acceptance={
            **{key: "passed" for key in ACCEPTANCE_IDS[:-1]},
            "M6-A10": "not_run",
        },
        stories={key: "passed" for key in STORY_IDS},
        checks={key: "passed" for key in _catalog()["required_checks"]},
        reason_codes=(),
        evidence_count=len(SELECTOR_REQUIREMENTS),
        declared_limitations=("sampled_process_coverage",),
        receipt_path=".agentmonitor-local/m6-exit-receipts/receipt.json",
    )

    output = capsys.readouterr().out
    assert '"record_type":"agentmonitor.m6_technical_exit_result.v1"' in output
    assert "M6 TECHNICAL EXIT: PASSED" in output
    assert "\nM6 EXIT: PASSED" not in output


def test_complete_exact_technical_policy_preserves_pending_owner_review() -> None:
    pending = evaluate_evidence_bundle_v1(
        _bundle(),
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert pending.overall_status == "not_run"
    assert pending.acceptance["M6-A10"] == "not_run"
    assert external_scope_status_v1(pending) == "passed"
    assert pending.reason_codes == ()
    assert set(pending.acceptance) == set(ACCEPTANCE_IDS)
    assert set(pending.stories) == set(STORY_IDS)


def test_selector_receipts_require_an_executed_cataloged_producer() -> None:
    bundle = assemble_selector_bundle_v1(
        tuple(_selector(item[0]) for item in SELECTOR_REQUIREMENTS),
        catalog=_catalog(),
        producer_statuses=_producer_statuses("passed"),
        expected_revision=REVISION,
        catalog_sha256=DIGEST,
        recorded_at=NOW,
    )
    result = evaluate_evidence_bundle_v1(
        bundle,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )

    assert result.overall_status == "not_run"
    assert external_scope_status_v1(result) == "passed"
    empty = assemble_selector_bundle_v1(
        (),
        catalog=_catalog(),
        producer_statuses=_producer_statuses(),
        expected_revision=REVISION,
        catalog_sha256=DIGEST,
        recorded_at=NOW,
    )
    missing = evaluate_evidence_bundle_v1(
        empty,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert missing.overall_status == "not_run"

    with pytest.raises(ValueError, match="m6_selector_receipt_outcome_invalid"):
        assemble_selector_bundle_v1(
            (_selector("M6-A01"),),
            catalog=_catalog(),
            producer_statuses=_producer_statuses(),
            expected_revision=REVISION,
            catalog_sha256=DIGEST,
            recorded_at=NOW,
        )

    with pytest.raises(ValueError, match="m6_selector_selection_not_frozen"):
        assemble_selector_bundle_v1(
            (_selector("M6-A01"),),
            catalog=_catalog(frozen=False),
            producer_statuses=_producer_statuses(passed_selector="M6-SEL-A01"),
            expected_revision=REVISION,
            catalog_sha256=DIGEST,
            recorded_at=NOW,
        )

    overclaim = _selector("M6-A01")
    overclaim_evidence = overclaim["evidence"]
    assert isinstance(overclaim_evidence, dict)
    overclaim_evidence["scope_ids"] = [*ACCEPTANCE_IDS, *STORY_IDS]
    with pytest.raises(ValueError, match="m6_selector_receipt_outcome_invalid"):
        assemble_selector_bundle_v1(
            (overclaim,),
            catalog=_catalog(),
            producer_statuses=_producer_statuses(passed_selector="M6-SEL-A01"),
            expected_revision=REVISION,
            catalog_sha256=DIGEST,
            recorded_at=NOW,
        )


def test_sampled_process_coverage_must_be_disclosed() -> None:
    selector = _selector("M6-A06")
    selector["declared_limitations"] = []

    with pytest.raises(ValueError, match="m6_selector_receipt_limitations_missing"):
        assemble_selector_bundle_v1(
            (selector,),
            catalog=_catalog(),
            producer_statuses=_producer_statuses(passed_selector="M6-SEL-A06"),
            expected_revision=REVISION,
            catalog_sha256=DIGEST,
            recorded_at=NOW,
        )

    bundle = _bundle()
    bundle["declared_limitations"] = []
    evaluated = evaluate_evidence_bundle_v1(
        bundle,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert evaluated.overall_status == "failed"
    assert "m6_sampled_process_limitation_missing" in evaluated.reason_codes


def test_missing_and_explicit_not_run_evidence_stay_not_run() -> None:
    missing = _bundle()
    acceptance = missing["acceptance"]
    assert isinstance(acceptance, list)
    missing["acceptance"] = acceptance[:-1]
    result = evaluate_evidence_bundle_v1(
        missing,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert result.overall_status == "not_run"
    assert result.acceptance["M6-A10"] == "not_run"
    assert "m6_acceptance_evidence_missing" in result.reason_codes

    not_run = _bundle(status="not_run")
    result = evaluate_evidence_bundle_v1(
        not_run,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert result.overall_status == "not_run"


def test_failure_block_and_staleness_are_not_collapsed_into_not_run() -> None:
    failed = evaluate_evidence_bundle_v1(
        _bundle(status="failed"),
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert failed.overall_status == "failed"

    blocked = evaluate_evidence_bundle_v1(
        _bundle(status="blocked"),
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert blocked.overall_status == "blocked"

    stale = _bundle()
    evidence = stale["evidence"]
    assert isinstance(evidence, list) and isinstance(evidence[0], dict)
    evidence[0]["valid_until"] = (
        (NOW - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    )
    result = evaluate_evidence_bundle_v1(
        stale,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert result.overall_status == "blocked"
    assert "m6_evidence_stale" in result.reason_codes


def test_skipped_or_wrong_revision_evidence_cannot_pass() -> None:
    skipped = _bundle()
    evidence = skipped["evidence"]
    assert isinstance(evidence, list) and isinstance(evidence[0], dict)
    evidence[0]["skip_count"] = 1
    result = evaluate_evidence_bundle_v1(
        skipped,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert result.overall_status == "blocked"
    assert "m6_required_scenario_skipped" in result.reason_codes

    zero_tests = _bundle()
    zero_test_evidence = zero_tests["evidence"]
    assert isinstance(zero_test_evidence, list) and isinstance(
        zero_test_evidence[0], dict
    )
    zero_test_evidence[0]["test_count"] = 0
    result = evaluate_evidence_bundle_v1(
        zero_tests,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert result.overall_status == "failed"
    assert "m6_required_scenario_missing" in result.reason_codes

    wrong = _bundle()
    wrong["implementation_revision"] = "c" * 40
    result = evaluate_evidence_bundle_v1(
        wrong,
        catalog=_catalog(),
        expected_revision=REVISION,
        expected_catalog_sha256=DIGEST,
        now=NOW,
    )
    assert result.overall_status == "blocked"
    assert "m6_evidence_revision_mismatch" in result.reason_codes


def test_passed_receipt_contains_only_counts_digests_and_safe_outcomes() -> None:
    required_checks = _catalog()["required_checks"]
    assert isinstance(required_checks, list)
    receipt = build_passed_receipt_v1(
        implementation_revision=REVISION,
        catalog_sha256=DIGEST,
        direct_evidence_sha256="c" * 64,
        selection_sha256="d" * 64,
        source_versions_sha256="e" * 64,
        completed_at=NOW,
        evidence_count=len(SELECTOR_REQUIREMENTS),
        required_checks=tuple(required_checks),
        declared_limitations=("sampled_process_coverage",),
    )

    assert receipt["status"] == "passed"
    assert receipt["record_type"] == "agentmonitor.m6_technical_exit_receipt.v1"
    assert receipt["technical_acceptance_count"] == 9
    assert receipt["pending_acceptance_ids"] == ["M6-A10"]
    assert receipt["story_count"] == 5
    assert receipt["evidence_count"] == len(SELECTOR_REQUIREMENTS)
    assert receipt["declared_limitations"] == ["sampled_process_coverage"]
    assert "accounts" not in receipt
    assert "identity" not in receipt

    with pytest.raises(ValueError, match="m6_receipt_input_invalid"):
        build_passed_receipt_v1(
            implementation_revision=REVISION,
            catalog_sha256=DIGEST,
            direct_evidence_sha256="c" * 64,
            selection_sha256="d" * 64,
            source_versions_sha256="e" * 64,
            completed_at=NOW,
            evidence_count=len(SELECTOR_REQUIREMENTS) - 1,
            required_checks=tuple(required_checks),
            declared_limitations=("sampled_process_coverage",),
        )

    prior = dict(receipt)
    prior["completed_at"] = "2026-11-02T11:59:00Z"
    assert validate_existing_passed_receipt_v1(prior, expected=receipt, now=NOW) == ()

    prior["unexpected"] = "field"
    assert validate_existing_passed_receipt_v1(prior, expected=receipt, now=NOW) == (
        "m6_receipt_shape_invalid",
    )
