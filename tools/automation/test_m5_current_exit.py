"""Fail-closed guards for the current-revision V1-M5 exit gate."""

from __future__ import annotations

import json
import os
import signal
import stat
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.automation.implementations import auto_m5_current_exit
from tools.automation.implementations.auto_m3_current_exit import (
    M3CurrentExitErrorV1,
    ServiceLaunchV1,
)
from tools.automation.implementations.auto_m5_current_exit import (
    ALERT_WITNESS_BASENAME,
    BROWSER_CHECKS,
    CODEX_ADAPTER_VERSION,
    CODEX_MAPPING_DIGEST,
    CODEX_MAPPING_ID,
    CODEX_PARSER_VERSION,
    CODEX_PROVIDER_VERSION,
    CODEX_SCHEMA_BUNDLE_DIGEST,
    LOCAL_ROUTINES,
    OWNER_OUTCOMES_BASENAME,
    PRE_SERVICE_ROUTINES,
    QUOTA_WITNESS_BASENAME,
    RECEIPT_BASENAME,
    RECEIPT_DIRECTORY_NAME,
    REQUIRED_LANES,
    STORY_ARTIFACTS,
    STORY_AUTOMATION_TEST_IDS,
    STORY_NODE_TEST_PATHS,
    STORY_PYTEST_FLAGS,
    STORY_TEST_PATHS,
    M5CurrentExitErrorV1,
    M5CurrentExitFailedV1,
    SelectedServiceV1,
    _digest_values,
    _node_test_count_v1,
    _read_private_json_v1,
    _validate_node_test_inventory_v1,
    _validate_pytest_report_inventory_v1,
    build_passed_receipt_v1,
    read_alert_witness_v1,
    read_owner_outcomes_v1,
    validate_authoritative_quota_v1,
    validate_codex_transition_v1,
    write_private_receipt_v1,
)
from tools.automation.implementations.m5_codex_quota_witness import (
    M5CodexQuotaWitnessErrorV1,
    ValidatedQuotaWitnessV1,
    read_quota_witness_v1,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION = "a" * 40
DIGEST_A = "b" * 64
DIGEST_B = "c" * 64
DIGEST_C = "d" * 64
DIGEST_D = "e" * 64
DIGEST_E = "f" * 64
STARTED = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)


def _start_receipt_writer_and_stop_after_create(
    path: Path, receipt: dict[str, object]
) -> int:
    """Stop a real child writer while its newly created inode is still open."""

    pid = os.fork()
    if pid == 0:
        try:
            write_private_receipt_v1(path, receipt)
        except M5CurrentExitFailedV1:
            os._exit(23)
        except M5CurrentExitErrorV1:
            os._exit(25)
        except BaseException:  # noqa: BLE001 - child must map every failure to status.
            os._exit(24)
        os._exit(0)

    deadline = time.monotonic() + 10
    try:
        while not path.exists():
            completed, status = os.waitpid(pid, os.WNOHANG)
            if completed:
                pytest.fail(
                    "receipt writer exited before its created path could be inspected: "
                    f"{status}"
                )
            if time.monotonic() >= deadline:
                pytest.fail("receipt writer did not create its target in time")
            time.sleep(0.0001)
        os.kill(pid, signal.SIGSTOP)
        completed, status = os.waitpid(pid, os.WUNTRACED)
        assert completed == pid
        assert os.WIFSTOPPED(status)
        return pid
    except BaseException:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
        raise


def _resume_receipt_writer(pid: int) -> int:
    os.kill(pid, signal.SIGCONT)
    completed, status = os.waitpid(pid, 0)
    assert completed == pid
    assert os.WIFEXITED(status)
    return os.WEXITSTATUS(status)


def _lane_evidence() -> dict[str, str]:
    return {lane: f"{lane}_passed" for lane in REQUIRED_LANES}


def _outcomes() -> dict[str, object]:
    return {
        "schema": "agentmonitor.m5-owner-outcomes.v2",
        "implementation_revision": REVISION,
        "service_pid": 321,
        "service_start_time_ticks": 654,
        "owner_confirmed_at": "2026-10-07T10:00:00Z",
        "owner_confirmation": True,
        "outcomes": [
            {
                "account_id": "account-one",
                "alias": "Private owner one",
                "disposition": "verified",
            },
            {
                "account_id": "account-two",
                "alias": "Private owner two",
                "disposition": "verified",
            },
            {
                "account_id": "account-three",
                "alias": "Private owner three",
                "disposition": "owner_unavailable",
                "reason": "owner_login_unavailable",
            },
            {
                "account_id": "account-four",
                "alias": "Private owner four",
                "disposition": "owner_unavailable",
                "reason": "owner_login_unavailable",
            },
        ],
    }


def _private_json(directory: Path, name: str, document: object) -> Path:
    path = directory / name
    path.write_text(json.dumps(document), encoding="utf-8")
    path.chmod(0o600)
    return path


def _selected_service() -> SelectedServiceV1:
    return SelectedServiceV1(
        321,
        654,
        ServiceLaunchV1(
            ("python", "-m", "agentmonitor.composition.bootstrap"),
            Path("/owner/service.env"),
            Path("/owner"),
            "127.0.0.1",
            43110,
        ),
    )


def _alert_witness() -> dict[str, object]:
    return {
        "schema": "agentmonitor.m5-alert-witness.v2",
        "implementation_revision": REVISION,
        "service_source_revision": REVISION,
        "service_pid": 321,
        "service_start_time_ticks": 654,
        "service_started_at": "2026-10-07T09:59:00Z",
        "service_checked_at": "2026-10-07T10:03:30Z",
        "service_versions_digest": DIGEST_A,
        "provider_key": "codex",
        "account_id": "account-one",
        "source_id": "codex.app-server.account-rate-limits-read.v2",
        "provider_version": CODEX_PROVIDER_VERSION,
        "adapter_id": "agentmonitor.codex",
        "adapter_version": CODEX_ADAPTER_VERSION,
        "parser_version": CODEX_PARSER_VERSION,
        "mapping_id": CODEX_MAPPING_ID,
        "mapping_digest": CODEX_MAPPING_DIGEST,
        "schema_bundle_digest": CODEX_SCHEMA_BUNDLE_DIGEST,
        "alert_record_version": 4,
        "alert_aggregate_sequence": 4,
        "opened_at": "2026-10-07T10:00:00Z",
        "deduplicated_at": "2026-10-07T10:01:00Z",
        "owner_action_at": "2026-10-07T10:02:00Z",
        "recovered_at": "2026-10-07T10:03:00Z",
        "recorded_at": "2026-10-07T10:04:00Z",
        "owner_action": "acknowledged",
        "opened": True,
        "deduplicated": True,
        "browser_presented": True,
        "recovered": True,
        "source_proven_opening": True,
        "source_proven_deduplication": True,
        "source_proven_recovery": True,
        "source_event_digest": DIGEST_B,
        "source_observation_digest": DIGEST_C,
        "opening_observation_digest": DIGEST_D,
        "deduplication_observation_digest": "0" * 64,
        "recovery_observation_digest": "1" * 64,
        "source_delivery_receipt_digest": "2" * 64,
        "alert_history_digest": "3" * 64,
        "owner_action_receipt_digest": "4" * 64,
        "registry_digest_scope": "all-public-registry-fields-v1",
        "registry_digest_before": DIGEST_E,
        "registry_digest_after": DIGEST_E,
    }


def _preflight() -> dict[str, object]:
    return {
        "event": "m5_codex_preflight",
        "service_revision": REVISION,
        "account_count": 4,
        "verified_count": 2,
        "owner_unavailable_count": 2,
        "current_history_count": 2,
        "fresh_after_restart_count": 0,
        "process_count": 5,
        "process_scan_truncated": False,
        "mutations": 0,
        "provider_version": CODEX_PROVIDER_VERSION,
        "adapter_version": CODEX_ADAPTER_VERSION,
        "parser_version": CODEX_PARSER_VERSION,
        "schema_bundle_digest": CODEX_SCHEMA_BUNDLE_DIGEST,
        "mapping_id": CODEX_MAPPING_ID,
        "mapping_digest": CODEX_MAPPING_DIGEST,
        "provider_health": "healthy",
        "fleet_metadata_digest": DIGEST_A,
        "identity_set_digest": DIGEST_B,
        "collection_run_set_digest": DIGEST_C,
        "quota_value_set_digest": "5" * 64,
        "history_value_set_digest": "4" * 64,
        "process_set_digest": DIGEST_D,
        "registry_digest": DIGEST_E,
    }


def _witness() -> dict[str, object]:
    return {
        **_preflight(),
        "event": "m5_codex_witness",
        "fresh_after_restart_count": 2,
        "process_scan_truncated": True,
        "collection_run_set_digest": "0" * 64,
        "history_value_set_digest": "9" * 64,
    }


def _quota_witness() -> ValidatedQuotaWitnessV1:
    return ValidatedQuotaWitnessV1(
        digest="6" * 64,
        account_count=2,
        window_count=4,
        identity_set_digest=DIGEST_B,
        collection_run_set_digest=DIGEST_C,
        quota_value_set_digest="5" * 64,
        history_value_set_digest="4" * 64,
        owner_observation_digest="7" * 64,
        registry_graph_digest="8" * 64,
    )


def _quota_document(recorded_at: datetime) -> dict[str, object]:
    return {
        "schema": "agentmonitor.m5-quota-witness.v1",
        "implementation_revision": REVISION,
        "service_source_revision": REVISION,
        "service_pid": 321,
        "service_start_time_ticks": 654,
        "recorded_at": recorded_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "owner_confirmation": "interactive_terminal",
        "provider_key": "codex",
        "provider_version": CODEX_PROVIDER_VERSION,
        "source_id": "codex.app-server.account-rate-limits-read.v2",
        "account_count": 2,
        "window_count": 4,
        "owner_outcomes_digest": DIGEST_A,
        "identity_set_digest": DIGEST_B,
        "collection_run_set_digest": DIGEST_C,
        "quota_value_set_digest": DIGEST_D,
        "owner_observation_digest": DIGEST_E,
        "rendered_value_set_digest": DIGEST_D,
        "history_value_set_digest": "0" * 64,
        "browser_proof_digest": "1" * 64,
        "registry_graph_digest_before": "2" * 64,
        "registry_graph_digest_after": "2" * 64,
        "browser_registry_digest_before": "3" * 64,
        "browser_registry_digest_after": "3" * 64,
    }


def test_catalog_selects_exact_m5_gate_and_closed_lanes() -> None:
    catalog = tomllib.loads((ROOT / "tools/automation/routines.toml").read_text())
    archive = next(
        item
        for item in catalog["routines"]
        if item["id"] == "AUTO-M5-ARCHIVE-PREREQUISITES"
    )
    producer = next(
        item for item in catalog["routines"] if item["id"] == "AUTO-M5-OWNER-OUTCOMES"
    )
    quota = next(
        item for item in catalog["routines"] if item["id"] == "AUTO-M5-QUOTA-WITNESS"
    )
    routine = next(item for item in catalog["routines"] if item["id"] == "AUTO-M5-EXIT")

    assert archive["status"] == "operational"
    assert archive["implementation_command"] == [
        "backend/.venv/bin/python",
        "-m",
        "tools.automation.implementations.m5_prerequisite_archive",
    ]
    assert producer["status"] == "operational"
    assert producer["implementation_command"] == [
        "backend/.venv/bin/python",
        "-m",
        "tools.automation.implementations.m5_owner_outcomes",
    ]
    assert quota["status"] == "operational"
    assert quota["implementation_command"] == [
        "backend/.venv/bin/python",
        "-m",
        "tools.automation.implementations.m5_codex_quota_witness",
    ]
    assert routine["status"] == "operational"
    assert routine["implementation_command"] == [
        "backend/.venv/bin/python",
        "-m",
        "tools.automation.implementations.auto_m5_current_exit",
    ]
    assert PRE_SERVICE_ROUTINES == (("build", "AUTO-BUILD"),)
    assert BROWSER_CHECKS == (
        ("alerts_browser", "tools/ui/verify_m4_alerts.mjs"),
        ("operations_browser", "tools/ui/verify_m4_operations.mjs"),
    )
    assert LOCAL_ROUTINES == (
        ("planning", "AUTO-PLAN-CHECK"),
        ("quality", "AUTO-QUALITY"),
        ("mutation", "AUTO-MUTATION"),
        ("documentation", "AUTO-DOCS-CHECK"),
        ("git_preflight", "AUTO-GIT-PREFLIGHT"),
    )
    assert STORY_PYTEST_FLAGS == (
        "-c",
        "backend/pyproject.toml",
        "--rootdir=.",
        "-o",
        "junit_family=legacy",
        "-q",
        "--tb=short",
        "-p",
        "tools.automation.pytest_no_skip",
        "--import-mode=importlib",
    )
    assert STORY_NODE_TEST_PATHS == (
        "tools/ui/test_m5_codex_policy.mjs",
        "frontend/tests/pure/alert-presentation.mjs",
        "frontend/tests/pure/provider-account-presentation.mjs",
        "frontend/tests/pure/quota-reset-presentation.mjs",
    )
    assert auto_m5_current_exit.STORY_NODE_TEST_COUNT == 19
    assert auto_m5_current_exit.STORY_NODE_TEST_INVENTORY_SHA256 == (
        "556bfd17af977e243e3a9c6c9b1372382cb1eaacfc46dd5136af736c4c76b41b"
    )
    assert auto_m5_current_exit.STORY_PYTEST_TEST_COUNT == 387
    assert auto_m5_current_exit.STORY_PYTEST_TEST_INVENTORY_SHA256 == (
        "95fbb92c42123a3b12fda276112c03a9659e7ca4abd540e054ea71aeabed074a"
    )
    assert STORY_AUTOMATION_TEST_IDS == (
        "tools/automation/test_run.py::AutomationRoutineTests::test_m5_prerequisite_archive_without_selection_never_moves_files",
        "tools/automation/test_run.py::AutomationRoutineTests::test_m5_owner_outcomes_without_real_selectors_never_writes_file",
        "tools/automation/test_run.py::AutomationRoutineTests::test_m5_alert_witness_without_real_selectors_never_writes_receipt",
        "tools/automation/test_run.py::AutomationRoutineTests::test_m5_quota_witness_without_real_selectors_never_writes_receipt",
        "tools/automation/test_run.py::AutomationRoutineTests::test_m5_exit_without_real_selectors_never_claims_completion",
        "tools/automation/test_run.py::AutomationRoutineTests::test_real_catalog_defines_every_mandatory_routine",
    )
    assert "tools/automation/test_m5_prerequisite_archive.py" in STORY_TEST_PATHS
    assert "tools/automation/test_m5_owner_outcomes.py" in STORY_TEST_PATHS
    assert "tools/automation/test_m5_codex_alert_witness.py" in STORY_TEST_PATHS
    assert "tools/automation/test_m5_codex_mutation_policies.py" in STORY_TEST_PATHS
    assert "tools/automation/test_m5_codex_containment.py" in STORY_TEST_PATHS
    assert "backend/tests/integration/api/test_provider_connection_routes.py" in (
        STORY_TEST_PATHS
    )
    assert auto_m5_current_exit.STORY_BROWSER_SCENARIOS == ("account_beyond_page",)
    assert "backend/tests/integration/foundation/test_source_revision.py" in (
        STORY_TEST_PATHS
    )
    assert "backend/tests/integration/provider_system/test_compatibility.py" in (
        STORY_TEST_PATHS
    )
    assert {
        "backend/tests/integration/api/test_openapi_policy.py",
        "backend/tests/integration/api/test_operations_routes.py",
        "backend/tests/operations/pure/test_diagnostic_policy.py",
    }.issubset(STORY_TEST_PATHS)
    assert auto_m5_current_exit.DEPENDENCY_ROUTINES == ("AUTO-M3-TEST",)
    assert {
        "tools/automation/implementations/m5_completion_lock.py",
        "tools/automation/implementations/m5_prerequisite_archive.py",
        "tools/automation/test_m5_prerequisite_archive.py",
        "tools/automation/implementations/m5_owner_outcomes.py",
        "tools/automation/test_m5_owner_outcomes.py",
        "tools/automation/implementations/m5_codex_alert_witness.py",
        "tools/automation/test_m5_codex_alert_witness.py",
        "tools/automation/test_m5_codex_mutation_policies.py",
        "backend/tests/integration/foundation/test_source_revision.py",
        "tools/automation/implementations/m5_codex_admission.py",
        "tools/automation/test_m5_codex_admission.py",
        "tools/automation/implementations/m5_codex_containment.py",
        "tools/automation/test_m5_codex_containment.py",
        "tools/automation/implementations/m5_codex_quota_witness.py",
        "tools/automation/test_m5_codex_quota_witness.py",
        "tools/automation/test_run.py",
        "tools/ui/verify_m5_codex_quota_reconciliation.mjs",
        "tools/ui/verify_m5_codex_alert_lifecycle.mjs",
        "frontend/tests/browser/p02/run_browser.py",
        "frontend/tests/browser/p02/account_beyond_page.mjs",
        "tools/ui/m5_registry_pages.mjs",
    }.issubset(STORY_ARTIFACTS)

    changed = auto_m5_current_exit._translated_service_error_v1(
        M3CurrentExitErrorV1("m3_current_service_process_invalid"),
        pre_restart=True,
    )
    assert type(changed) is M5CurrentExitErrorV1
    assert str(changed) == "m5_current_service_selection_changed"
    for reason in (
        "m3_current_service_stop_failed",
        "m3_current_service_start_failed",
        "m3_current_service_restore_failed",
    ):
        failed = auto_m5_current_exit._translated_service_error_v1(
            M3CurrentExitErrorV1(reason),
            pre_restart=True,
        )
        assert type(failed) is M5CurrentExitFailedV1
        assert str(failed) == "m5_current_service_restart_failed"
    receipt_failed = auto_m5_current_exit._translated_service_error_v1(
        M3CurrentExitErrorV1("m3_current_service_changed"),
        pre_restart=False,
    )
    assert type(receipt_failed) is M5CurrentExitFailedV1
    assert str(receipt_failed) == "m5_current_service_receipt_binding_failed"
    dirty = auto_m5_current_exit._translated_checkout_error_v1(
        M3CurrentExitErrorV1("m3_current_checkout_not_clean")
    )
    assert type(dirty) is M5CurrentExitErrorV1
    assert str(dirty) == "m5_current_checkout_not_clean"
    for reason in ("m3_current_git_read_failed", "m3_current_git_revision_invalid"):
        git_failed = auto_m5_current_exit._translated_checkout_error_v1(
            M3CurrentExitErrorV1(reason)
        )
        assert type(git_failed) is M5CurrentExitFailedV1
        assert str(git_failed) == "m5_current_git_revision_failed"


def test_gate_admission_constants_match_the_codex_manifest() -> None:
    source_root = str(ROOT / "backend/src")
    sys.path.insert(0, source_root)
    try:
        from agentmonitor.adapters.providers.codex.manifest import (
            CODEX_ADAPTER_VERSION as MANIFEST_ADAPTER_VERSION,
        )
        from agentmonitor.adapters.providers.codex.manifest import (
            CODEX_PARSER_VERSION as MANIFEST_PARSER_VERSION,
        )
        from agentmonitor.adapters.providers.codex.manifest import (
            CODEX_PROVIDER_VERSION as MANIFEST_PROVIDER_VERSION,
        )
        from agentmonitor.adapters.providers.codex.manifest import (
            CODEX_RATE_LIMITS_SOURCE_ID as MANIFEST_RATE_LIMITS_SOURCE_ID,
        )
        from agentmonitor.adapters.providers.codex.manifest import (
            CODEX_SCHEMA_BUNDLE_DIGEST as MANIFEST_SCHEMA_BUNDLE_DIGEST,
        )
        from agentmonitor.adapters.providers.codex.manifest import (
            M0_MAPPING_DIGEST as MANIFEST_MAPPING_DIGEST,
        )
        from agentmonitor.adapters.providers.codex.manifest import (
            M0_MAPPING_ID as MANIFEST_MAPPING_ID,
        )
    finally:
        sys.path.remove(source_root)

    assert (
        CODEX_PROVIDER_VERSION,
        CODEX_ADAPTER_VERSION,
        CODEX_PARSER_VERSION,
        auto_m5_current_exit.CODEX_RATE_LIMITS_SOURCE_ID,
        CODEX_MAPPING_ID,
        CODEX_MAPPING_DIGEST,
        CODEX_SCHEMA_BUNDLE_DIGEST,
    ) == (
        MANIFEST_PROVIDER_VERSION,
        MANIFEST_ADAPTER_VERSION,
        MANIFEST_PARSER_VERSION,
        MANIFEST_RATE_LIMITS_SOURCE_ID,
        MANIFEST_MAPPING_ID,
        MANIFEST_MAPPING_DIGEST,
        MANIFEST_SCHEMA_BUNDLE_DIGEST,
    )


def test_node_policy_summary_requires_executed_tests_and_zero_skips() -> None:
    passed = """TAP version 13
# tests 4
# pass 4
# fail 0
# cancelled 0
# skipped 0
# todo 0
"""
    assert _node_test_count_v1(passed) == 4

    skipped = passed.replace("# pass 4", "# pass 3").replace(
        "# skipped 0", "# skipped 1"
    )
    with pytest.raises(
        M5CurrentExitFailedV1, match="m5_current_browser_policy_skipped"
    ):
        _node_test_count_v1(skipped)
    empty = passed.replace("# tests 4", "# tests 0").replace("# pass 4", "# pass 0")
    with pytest.raises(
        M5CurrentExitFailedV1,
        match="m5_current_browser_policy_report_invalid",
    ):
        _node_test_count_v1(empty)


def test_exact_test_inventories_reject_removed_or_renamed_cases(
    tmp_path: Path,
) -> None:
    node = """TAP version 13
# Subtest: alpha
ok 1 - alpha
# Subtest: beta
ok 2 - beta
1..2
# tests 2
# pass 2
# fail 0
# cancelled 0
# skipped 0
# todo 0
"""
    node_digest = _digest_values(["alpha", "beta"])
    assert (
        _validate_node_test_inventory_v1(
            node,
            expected_count=2,
            expected_digest=node_digest,
        )
        == 2
    )
    with pytest.raises(
        M5CurrentExitFailedV1,
        match="m5_current_browser_policy_inventory_invalid",
    ):
        _validate_node_test_inventory_v1(
            node.replace("beta", "renamed"),
            expected_count=2,
            expected_digest=node_digest,
        )

    report = tmp_path / "results.xml"
    report.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite tests="2" skipped="0">
<testcase name="test_alpha"
 file="tools/automation/test_alpha.py" />
<testcase name="test_beta[value]"
 file="backend/tests/example.py" />
</testsuite></testsuites>
""",
        encoding="utf-8",
    )
    pytest_digest = _digest_values(
        [
            "backend/tests/example.py::test_beta[value]",
            "tools/automation/test_alpha.py::test_alpha",
        ]
    )
    assert _validate_pytest_report_inventory_v1(
        report,
        expected_count=2,
        expected_digest=pytest_digest,
    ) == (2, 0)
    report.write_text(
        report.read_text(encoding="utf-8").replace('skipped="0"', 'skipped="1"'),
        encoding="utf-8",
    )
    with pytest.raises(M5CurrentExitFailedV1, match="m5_current_story_suite_skipped"):
        _validate_pytest_report_inventory_v1(
            report,
            expected_count=2,
            expected_digest=pytest_digest,
        )
    report.write_text(
        report.read_text(encoding="utf-8").replace('skipped="1"', 'skipped="0"'),
        encoding="utf-8",
    )
    report.write_text(
        report.read_text(encoding="utf-8").replace("test_beta", "test_renamed"),
        encoding="utf-8",
    )
    with pytest.raises(
        M5CurrentExitFailedV1,
        match="m5_current_story_inventory_invalid",
    ):
        _validate_pytest_report_inventory_v1(
            report,
            expected_count=2,
            expected_digest=pytest_digest,
        )


def test_owner_outcomes_require_four_unique_private_closed_rows() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        path = _private_json(root, OWNER_OUTCOMES_BASENAME, _outcomes())

        selected = read_owner_outcomes_v1(
            path,
            expected_revision=REVISION,
            selected_service=_selected_service(),
            now=STARTED + timedelta(minutes=5),
        )

        assert selected.verified_count == 2
        assert selected.owner_unavailable_count == 2
        assert selected.account_count == 4
        assert len(selected.digest) == 64
        assert selected.primary_verified_account_id == "account-one"


@pytest.mark.parametrize(
    "change",
    (
        "extra",
        "unresolved",
        "duplicate_account",
        "duplicate_alias",
        "forbidden_identity_fingerprint",
    ),
)
def test_owner_outcomes_reject_extra_unresolved_and_duplicates(change: str) -> None:
    document = _outcomes()
    rows = document["outcomes"]
    assert isinstance(rows, list)
    if change == "extra":
        rows[0]["email"] = "private@example.invalid"
    elif change == "unresolved":
        rows[0] = {
            "account_id": "account-one",
            "alias": "Private owner one",
            "disposition": "unresolved",
            "reason": "unknown",
        }
    elif change == "duplicate_account":
        rows[3]["account_id"] = rows[0]["account_id"]
    elif change == "duplicate_alias":
        rows[3]["alias"] = " private OWNER one "
    else:
        rows[1]["identity_fingerprint"] = "1" * 64
    with tempfile.TemporaryDirectory() as raw:
        path = _private_json(Path(raw), OWNER_OUTCOMES_BASENAME, document)
        with pytest.raises(
            M5CurrentExitErrorV1, match="m5_current_owner_outcomes_invalid"
        ):
            read_owner_outcomes_v1(
                path,
                expected_revision=REVISION,
                selected_service=_selected_service(),
                now=STARTED + timedelta(minutes=5),
            )


@pytest.mark.parametrize(
    ("change", "now"),
    (
        ({"implementation_revision": "0" * 40}, STARTED + timedelta(minutes=5)),
        ({"service_pid": 322}, STARTED + timedelta(minutes=5)),
        ({"service_start_time_ticks": 655}, STARTED + timedelta(minutes=5)),
        ({"owner_confirmation": False}, STARTED + timedelta(minutes=5)),
        ({"owner_confirmed_at": "2026-09-01T10:00:00Z"}, STARTED),
        ({"owner_confirmed_at": "2026-10-07T10:10:00Z"}, STARTED),
    ),
)
def test_owner_outcomes_reject_wrong_context_or_stale_confirmation(
    change: dict[str, object], now: datetime
) -> None:
    document = {**_outcomes(), **change}
    with tempfile.TemporaryDirectory() as raw:
        path = _private_json(Path(raw), OWNER_OUTCOMES_BASENAME, document)
        with pytest.raises(
            M5CurrentExitErrorV1, match="m5_current_owner_outcomes_invalid"
        ):
            read_owner_outcomes_v1(
                path,
                expected_revision=REVISION,
                selected_service=_selected_service(),
                now=now,
            )


def test_owner_outcomes_reject_public_or_symlinked_files() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        path = _private_json(root, OWNER_OUTCOMES_BASENAME, _outcomes())
        path.chmod(0o644)
        with pytest.raises(
            M5CurrentExitErrorV1, match="m5_current_owner_outcomes_invalid"
        ):
            read_owner_outcomes_v1(
                path,
                expected_revision=REVISION,
                selected_service=_selected_service(),
                now=STARTED + timedelta(minutes=5),
            )
        path.unlink()
        target = _private_json(root, "target.json", _outcomes())
        path.symlink_to(target)
        with pytest.raises(
            M5CurrentExitErrorV1, match="m5_current_owner_outcomes_invalid"
        ):
            read_owner_outcomes_v1(
                path,
                expected_revision=REVISION,
                selected_service=_selected_service(),
                now=STARTED + timedelta(minutes=5),
            )


@pytest.mark.parametrize(
    ("target", "mode"),
    (("file", 0o400), ("parent", 0o750)),
)
def test_private_json_reader_requires_exact_owner_only_modes(
    tmp_path: Path, target: str, mode: int
) -> None:
    tmp_path.chmod(0o700)
    path = _private_json(tmp_path, ALERT_WITNESS_BASENAME, _alert_witness())
    (path if target == "file" else tmp_path).chmod(mode)

    with pytest.raises(M5CurrentExitErrorV1, match="m5_current_alert_witness_invalid"):
        _read_private_json_v1(
            path,
            expected_basename=ALERT_WITNESS_BASENAME,
            error_code="m5_current_alert_witness_invalid",
        )


def test_private_json_reader_rejects_a_symlinked_parent(tmp_path: Path) -> None:
    private_parent = tmp_path / "private"
    private_parent.mkdir(mode=0o700)
    path = _private_json(private_parent, ALERT_WITNESS_BASENAME, _alert_witness())
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(private_parent, target_is_directory=True)

    with pytest.raises(M5CurrentExitErrorV1, match="m5_current_alert_witness_invalid"):
        _read_private_json_v1(
            linked_parent / path.name,
            expected_basename=ALERT_WITNESS_BASENAME,
            error_code="m5_current_alert_witness_invalid",
        )


def test_private_json_reader_rejects_a_hard_linked_file(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = _private_json(tmp_path, ALERT_WITNESS_BASENAME, _alert_witness())
    os.link(path, tmp_path / "second-name.json")

    with pytest.raises(M5CurrentExitErrorV1, match="m5_current_alert_witness_invalid"):
        _read_private_json_v1(
            path,
            expected_basename=ALERT_WITNESS_BASENAME,
            error_code="m5_current_alert_witness_invalid",
        )


def test_alert_witness_binds_revision_service_lineage_and_owner_action() -> None:
    with tempfile.TemporaryDirectory() as raw:
        path = _private_json(Path(raw), ALERT_WITNESS_BASENAME, _alert_witness())
        witness = read_alert_witness_v1(
            path,
            expected_revision=REVISION,
            selected_service=_selected_service(),
            verified_account_ids=frozenset({"account-one", "account-two"}),
            now=STARTED + timedelta(minutes=5),
        )

        assert len(witness.digest) == 64
        assert witness.owner_action == "acknowledged"
        assert witness.registry_digest == DIGEST_E

        changed = _alert_witness()
        changed["registry_digest_after"] = DIGEST_A
        path.unlink()
        _private_json(Path(raw), ALERT_WITNESS_BASENAME, changed)
        with pytest.raises(
            M5CurrentExitErrorV1, match="m5_current_alert_witness_invalid"
        ):
            read_alert_witness_v1(
                path,
                expected_revision=REVISION,
                selected_service=_selected_service(),
                verified_account_ids=frozenset({"account-one", "account-two"}),
                now=STARTED + timedelta(minutes=5),
            )


def test_alert_witness_rejects_stale_wrong_service_and_unavailable_account() -> None:
    cases = []
    stale = _alert_witness()
    stale["recorded_at"] = "2026-09-01T10:04:00Z"
    cases.append(stale)
    wrong_service = _alert_witness()
    wrong_service["service_start_time_ticks"] = 655
    cases.append(wrong_service)
    wrong_account = _alert_witness()
    wrong_account["account_id"] = "account-three"
    cases.append(wrong_account)
    for document in cases:
        with tempfile.TemporaryDirectory() as raw:
            path = _private_json(Path(raw), ALERT_WITNESS_BASENAME, document)
            with pytest.raises(
                M5CurrentExitErrorV1, match="m5_current_alert_witness_invalid"
            ):
                read_alert_witness_v1(
                    path,
                    expected_revision=REVISION,
                    selected_service=_selected_service(),
                    verified_account_ids=frozenset({"account-one", "account-two"}),
                    now=STARTED + timedelta(minutes=5),
                )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("service_source_revision", "9" * 40),
        ("source_proven_opening", False),
        ("source_proven_deduplication", False),
        ("service_versions_digest", "not-a-digest"),
        ("alert_aggregate_sequence", 5),
        ("service_checked_at", "2026-10-07T10:02:30Z"),
        ("registry_digest_scope", "partial-registry-fields"),
    ),
)
def test_alert_witness_rejects_incomplete_v2_integrity(
    field: str, value: object
) -> None:
    document = _alert_witness()
    document[field] = value
    with tempfile.TemporaryDirectory() as raw:
        path = _private_json(Path(raw), ALERT_WITNESS_BASENAME, document)
        with pytest.raises(
            M5CurrentExitErrorV1, match="m5_current_alert_witness_invalid"
        ):
            read_alert_witness_v1(
                path,
                expected_revision=REVISION,
                selected_service=_selected_service(),
                verified_account_ids=frozenset({"account-one", "account-two"}),
                now=STARTED + timedelta(minutes=5),
            )


@pytest.mark.parametrize("field", ("service_pid", "service_start_time_ticks"))
def test_alert_witness_rejects_floats_for_service_integer_fields(field: str) -> None:
    document = _alert_witness()
    document[field] = float(document[field])  # type: ignore[arg-type]
    with tempfile.TemporaryDirectory() as raw:
        path = _private_json(Path(raw), ALERT_WITNESS_BASENAME, document)
        with pytest.raises(
            M5CurrentExitErrorV1, match="m5_current_alert_witness_invalid"
        ):
            read_alert_witness_v1(
                path,
                expected_revision=REVISION,
                selected_service=_selected_service(),
                verified_account_ids=frozenset({"account-one", "account-two"}),
                now=STARTED + timedelta(minutes=5),
            )


def test_codex_transition_requires_all_live_evidence() -> None:
    result = validate_codex_transition_v1(
        _preflight(), _witness(), expected_revision=REVISION
    )
    assert result == (
        DIGEST_A,
        DIGEST_B,
        "0" * 64,
        DIGEST_D,
        DIGEST_E,
        2,
        2,
        5,
        True,
    )

    for field, value, reason in (
        ("fleet_metadata_digest", DIGEST_B, "m5_current_fleet_metadata_changed"),
        ("collection_run_set_digest", DIGEST_C, "m5_current_collection_not_fresh"),
        ("fresh_after_restart_count", 1, "m5_current_codex_witness_invalid"),
        ("process_count", 4, "m5_current_codex_witness_invalid"),
        ("registry_digest", DIGEST_A, "m5_current_registry_changed"),
        ("provider_version", "0.161.0", "m5_current_codex_witness_invalid"),
        ("service_revision", "9" * 40, "m5_current_codex_witness_invalid"),
    ):
        witness = _witness()
        witness[field] = value
        with pytest.raises(M5CurrentExitErrorV1, match=reason):
            validate_codex_transition_v1(
                _preflight(), witness, expected_revision=REVISION
            )


def test_main_browser_witness_rejects_fields_outside_exact_contract() -> None:
    witness = _witness()
    assert len(witness) == 24
    witness["unexpected_private_field"] = "must-not-cross-boundary"

    with pytest.raises(M5CurrentExitFailedV1, match="m5_current_codex_witness_invalid"):
        validate_codex_transition_v1(_preflight(), witness, expected_revision=REVISION)


def test_main_browser_transition_requires_fresh_history_observation_lineage() -> None:
    witness = _witness()
    witness["history_value_set_digest"] = _preflight()["history_value_set_digest"]

    with pytest.raises(M5CurrentExitErrorV1, match="m5_current_history_not_fresh"):
        validate_codex_transition_v1(_preflight(), witness, expected_revision=REVISION)


@pytest.mark.parametrize(
    "field",
    (
        "account_count",
        "verified_count",
        "owner_unavailable_count",
        "current_history_count",
        "fresh_after_restart_count",
        "process_count",
        "mutations",
    ),
)
def test_main_browser_witness_rejects_booleans_for_integer_fields(field: str) -> None:
    preflight = _preflight()
    witness = _witness()
    if field in {
        "verified_count",
        "current_history_count",
        "fresh_after_restart_count",
    }:
        witness.update(
            verified_count=1,
            owner_unavailable_count=3,
            current_history_count=1,
            fresh_after_restart_count=1,
        )
    witness[field] = field != "mutations"

    with pytest.raises(M5CurrentExitErrorV1, match="m5_current_codex_witness_invalid"):
        validate_codex_transition_v1(preflight, witness, expected_revision=REVISION)


def test_quota_witness_is_rejected_at_the_receipt_completion_time(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    recorded_at = STARTED
    path = _private_json(tmp_path, QUOTA_WITNESS_BASENAME, _quota_document(recorded_at))
    initially_valid = read_quota_witness_v1(
        path,
        expected_revision=REVISION,
        service_pid=321,
        service_start_time_ticks=654,
        owner_outcomes_digest=DIGEST_A,
        verified_account_count=2,
        now=recorded_at + timedelta(minutes=14, seconds=59),
    )
    assert initially_valid.account_count == 2

    with pytest.raises(M5CodexQuotaWitnessErrorV1, match="m5_quota_witness_invalid"):
        auto_m5_current_exit._read_current_quota_witness_v1(
            path,
            expected_revision=REVISION,
            service_pid=321,
            service_start_time_ticks=654,
            owner_outcomes_digest=DIGEST_A,
            verified_account_count=2,
            now=recorded_at + timedelta(minutes=15, microseconds=1),
        )


def test_authoritative_quota_binds_preflight_and_post_restart_values() -> None:
    quota = _quota_witness()
    validate_authoritative_quota_v1(quota, _preflight(), _witness())

    for phase, field, value, reason in (
        (
            "preflight",
            "identity_set_digest",
            DIGEST_A,
            "m5_current_authoritative_quota_mismatch",
        ),
        (
            "preflight",
            "collection_run_set_digest",
            DIGEST_A,
            "m5_current_authoritative_quota_mismatch",
        ),
        (
            "preflight",
            "quota_value_set_digest",
            DIGEST_A,
            "m5_current_authoritative_quota_mismatch",
        ),
        (
            "witness",
            "quota_value_set_digest",
            DIGEST_A,
            "m5_current_authoritative_quota_changed",
        ),
    ):
        preflight = _preflight()
        witness = _witness()
        (preflight if phase == "preflight" else witness)[field] = value
        with pytest.raises(M5CurrentExitErrorV1, match=reason):
            validate_authoritative_quota_v1(quota, preflight, witness)


def test_authoritative_quota_binds_recomputed_browser_history_to_preflight() -> None:
    quota = SimpleNamespace(
        account_count=2,
        identity_set_digest=DIGEST_B,
        collection_run_set_digest=DIGEST_C,
        quota_value_set_digest="5" * 64,
        history_value_set_digest="4" * 64,
    )
    preflight = _preflight()
    preflight["history_value_set_digest"] = DIGEST_A

    with pytest.raises(
        M5CurrentExitErrorV1, match="m5_current_authoritative_quota_mismatch"
    ):
        validate_authoritative_quota_v1(quota, preflight, _witness())  # type: ignore[arg-type]


def test_m5_receipt_is_sanitized_exact_and_create_once() -> None:
    receipt = build_passed_receipt_v1(
        implementation_revision=REVISION,
        started_at=STARTED,
        completed_at=STARTED + timedelta(minutes=8),
        owner_outcomes_digest=DIGEST_A,
        alert_witness_digest=DIGEST_B,
        quota_witness_digest="6" * 64,
        quota_value_set_digest="5" * 64,
        quota_history_value_set_digest="4" * 64,
        post_restart_history_value_set_digest="9" * 64,
        owner_observation_digest="7" * 64,
        registry_graph_digest="8" * 64,
        containment_evidence_digest="1" * 64,
        containment_provider_access_count=12,
        containment_provider_write_count=2,
        containment_default_profile_access_count=0,
        containment_default_profile_write_count=0,
        quota_window_count=4,
        fleet_metadata_digest=DIGEST_C,
        identity_set_digest=DIGEST_D,
        collection_run_set_digest=DIGEST_E,
        process_set_digest="0" * 64,
        verified_count=2,
        owner_unavailable_count=2,
        process_count=5,
        process_scan_truncated=True,
        test_count=150,
        lane_evidence=_lane_evidence(),
    )
    serialized = json.dumps(receipt)
    assert receipt["status"] == "passed"
    assert receipt["skips"] == []
    assert receipt["account_count"] == 4
    assert receipt["process_count"] == 5
    assert receipt["process_scan_completeness"] == "partial"
    assert receipt["provider_version"] == CODEX_PROVIDER_VERSION
    assert receipt["quota_witness_digest"] == "6" * 64
    assert receipt["quota_window_count"] == 4
    assert receipt["quota_history_value_set_digest"] == "4" * 64
    assert receipt["post_restart_history_value_set_digest"] == "9" * 64
    assert receipt["containment_evidence_digest"] == "1" * 64
    assert receipt["containment_provider_access_count"] == 12
    assert receipt["containment_provider_write_count"] == 2
    assert receipt["containment_default_profile_access_count"] == 0
    assert receipt["containment_default_profile_write_count"] == 0
    assert "authenticated_containment" in REQUIRED_LANES
    assert QUOTA_WITNESS_BASENAME == "m5-quota-witness.json"
    assert "account-one" not in serialized
    assert "Private owner" not in serialized
    assert {item["lane_id"] for item in receipt["required_lanes"]} == set(
        REQUIRED_LANES
    )

    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / RECEIPT_DIRECTORY_NAME
        directory.mkdir(mode=0o700)
        path = directory / RECEIPT_BASENAME
        write_private_receipt_v1(path, receipt)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert json.loads(path.read_text(encoding="utf-8")) == receipt
        with pytest.raises(
            M5CurrentExitErrorV1, match="m5_current_receipt_path_invalid"
        ):
            write_private_receipt_v1(path, receipt)


def test_m5_receipt_keeps_exact_owner_only_mode_under_restrictive_umask() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / RECEIPT_DIRECTORY_NAME
        directory.mkdir(mode=0o700)
        path = directory / RECEIPT_BASENAME
        previous_umask = os.umask(0o077)
        try:
            write_private_receipt_v1(path, {"status": "passed"})
        finally:
            os.umask(previous_umask)

        metadata = path.lstat()
        assert stat.S_ISREG(metadata.st_mode)
        assert metadata.st_uid == os.getuid()
        assert stat.S_IMODE(metadata.st_mode) == 0o600
        assert metadata.st_nlink == 1


def test_m5_receipt_rejects_a_hardlink_added_during_write() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / RECEIPT_DIRECTORY_NAME
        directory.mkdir(mode=0o700)
        path = directory / RECEIPT_BASENAME
        retained_inode = directory / "retained-created-inode"
        receipt: dict[str, object] = {"padding": "x" * (64 * 1024 * 1024)}

        pid = _start_receipt_writer_and_stop_after_create(path, receipt)
        os.link(path, retained_inode)
        exit_code = _resume_receipt_writer(pid)

        assert exit_code == 23
        assert not path.exists()
        assert retained_inode.exists()
        assert retained_inode.stat().st_nlink == 1


def test_m5_receipt_never_unlinks_an_attacker_replacement() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / RECEIPT_DIRECTORY_NAME
        directory.mkdir(mode=0o700)
        path = directory / RECEIPT_BASENAME
        displaced_inode = directory / "displaced-created-inode"
        replacement = b"attacker replacement must remain\n"
        receipt: dict[str, object] = {"padding": "x" * (64 * 1024 * 1024)}

        pid = _start_receipt_writer_and_stop_after_create(path, receipt)
        path.rename(displaced_inode)
        path.write_bytes(replacement)
        path.chmod(0o600)
        exit_code = _resume_receipt_writer(pid)

        assert exit_code == 23
        assert path.read_bytes() == replacement
        assert displaced_inode.exists()


def test_m5_receipt_rejects_missing_lane_and_nonrepresentative_process_count() -> None:
    lanes = _lane_evidence()
    lanes.pop("codex_browser")
    for process_count in (4, 7):
        with pytest.raises(M5CurrentExitFailedV1):
            build_passed_receipt_v1(
                implementation_revision=REVISION,
                started_at=STARTED,
                completed_at=STARTED,
                owner_outcomes_digest=DIGEST_A,
                alert_witness_digest=DIGEST_B,
                quota_witness_digest="6" * 64,
                quota_value_set_digest="5" * 64,
                quota_history_value_set_digest="4" * 64,
                post_restart_history_value_set_digest="9" * 64,
                owner_observation_digest="7" * 64,
                registry_graph_digest="8" * 64,
                containment_evidence_digest="1" * 64,
                containment_provider_access_count=12,
                containment_provider_write_count=2,
                containment_default_profile_access_count=0,
                containment_default_profile_write_count=0,
                quota_window_count=4,
                fleet_metadata_digest=DIGEST_C,
                identity_set_digest=DIGEST_D,
                collection_run_set_digest=DIGEST_E,
                process_set_digest="0" * 64,
                verified_count=2,
                owner_unavailable_count=2,
                process_count=process_count,
                process_scan_truncated=False,
                test_count=150,
                lane_evidence=lanes,
            )
