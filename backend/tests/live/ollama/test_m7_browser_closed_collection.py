"""Prospective installed scheduling after closing only a test-owned window."""

import hashlib
import json
import os
import re
import subprocess
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.contracts.collection_recovery_v1 import CollectionRecoveryRunV1

ROOT = Path(__file__).resolve().parents[4]
MAX_OBSERVATION_SECONDS = 1200


def _quota_progress(
    runs: tuple[CollectionRecoveryRunV1, ...],
    provider: str,
    closed_at: datetime,
    observed_at: datetime,
) -> CollectionRecoveryRunV1 | None:
    from tools.automation.implementations.m6_recovery_interval import (
        _committed_in_interval,
    )

    return _committed_in_interval(
        tuple(
            run
            for run in runs
            if run.provider_key == provider
            and closed_at < run.requested_at <= run.completed_at <= observed_at
        ),
        closed_at,
    )


def _prospective_metadata(
    metadata: Mapping[str, object], closed_at: datetime, prior_ids: frozenset[str]
) -> bool:
    try:
        requested_at = datetime.fromisoformat(str(metadata["request_time"]))
        return (
            isinstance(metadata["run_id"], str)
            and metadata["run_id"] not in prior_ids
            and metadata["trigger_kind"] == metadata["request_trigger"] == "scheduled"
            and metadata["request_auth_method"] == "internal_scheduler"
            and requested_at.utcoffset() == timedelta(0)
            and requested_at > closed_at
        )
    except (KeyError, ValueError, TypeError):
        return False


def _require(condition: bool, code: str) -> None:
    if not condition:
        pytest.fail(code, pytrace=False)


def _window(revision: str, phase: str, selection: dict[str, str]) -> datetime:
    process = subprocess.Popen(
        [
            "/usr/bin/node",
            "frontend/tests/browser/m7/verify_controlled_window.mjs",
            revision,
            phase,
        ],
        cwd=ROOT,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(json.dumps(selection) + "\n", timeout=60)
    except subprocess.TimeoutExpired:
        # Give the helper time to close only its owned target before disconnecting.
        process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        pytest.fail("m7_controlled_window_timeout", pytrace=False)
    _require(
        len(stdout) <= 8192 and not stderr,
        "m7_controlled_window_output_invalid",
    )
    try:
        result = json.loads(stdout)
        _require(isinstance(result, dict), "m7_controlled_window_output_invalid")
        if result.get("reason_code") == "authentication_required":
            pytest.fail("authentication_required", pytrace=False)
        _require(
            process.returncode == 0
            and result.get("status") == "passed"
            and result.get("record_type") == "agentmonitor.m7_controlled_window.v1"
            and result.get("source_revision") == revision
            and result.get("phase") == phase
            and result.get("window_closed") is True
            and result.get("unsafe_requests") == 0,
            "m7_controlled_window_proof_failed",
        )
        observed = datetime.fromisoformat(result["observed_at"])
        _require(
            observed.utcoffset() == timedelta(0), "m7_controlled_window_time_invalid"
        )
        return observed
    except (ValueError, KeyError, TypeError):
        pytest.fail("m7_controlled_window_output_invalid", pytrace=False)


def test_new_scheduled_financial_receipt_after_controlled_window_closes() -> None:
    """Run only after root schedules the installed/authenticated browser lane.

    The service continues its ordinary scheduling. This test observes; it never
    calls a collector, acquires a provider lease or changes monitoring/settings.
    Other owner windows, including setup/login, remain entirely outside its scope.
    """
    try:
        _observe_installed()
    except (ValueError, OSError, subprocess.TimeoutExpired):
        pytest.fail("m7_browser_closed_observation_unavailable", pytrace=False)


def _observe_installed() -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.recovery import (
        SqliteCollectionRecoveryQueryV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.adapters.providers.ollama.api.manifest import (
        ADAPTER_ID,
        ADAPTER_VERSION,
        EVIDENCE_REFERENCE,
        PROVIDER_VERSION,
    )
    from agentmonitor.adapters.providers.ollama.api.policy import (
        SOURCE_ID,
        completed_period,
    )
    from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
    from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1
    from agentmonitor.modules.capacity.application.budget_commit import (
        budget_report_payload_digest,
    )

    from backend.tests.live.ollama import (
        test_m7_scheduled_collection_lifecycle as scheduled,
    )
    from tools.automation.implementations.m6_cutover import (
        _FIXED_UNIT,
        _cwd,
        _verify_retained_baseline,
    )
    from tools.automation.implementations.m6_recovery_interval import _identity, _runs

    revision = os.environ.get("AGENTMONITOR_M7_EXPECTED_REVISION", "")
    _require(
        re.fullmatch(r"[a-f0-9]{40}", revision) is not None,
        "m7_expected_installed_revision_required",
    )
    installed, _ = _verify_retained_baseline(Path(_cwd(_FIXED_UNIT)))
    _require(installed == revision, "m7_browser_closed_revision_mismatch")
    identity = _identity()
    reference = DatabaseRefV1(scheduled.LIVE / "agentmonitor.db", scheduled.LIVE)
    authority = scheduled._inventory(reference)
    _require(bool(authority), "m7_current_scheduled_resources_unavailable")
    began = datetime.now(UTC)
    prior_ids = frozenset(
        str(row["run_id"])
        for graph, _ in authority.values()
        for row in scheduled._scheduled_metadata(reference, graph, began)
    )
    initial_resource, (initial_graph, _) = next(iter(authority.items()))
    initial_period = completed_period(began, "7d")
    closed_at = _window(
        revision,
        "close",
        {
            "account_id": initial_graph.account_id.value,
            "resource_id": initial_resource.value,
            "period_start": initial_period.start.isoformat(),
            "period_end": initial_period.end.isoformat(),
            "as_of": began.isoformat(),
        },
    )
    _require(
        began <= closed_at <= datetime.now(UTC), "m7_controlled_window_time_invalid"
    )
    _require(
        _identity() == identity and scheduled._inventory(reference) == authority,
        "m7_browser_closed_authority_changed",
    )
    runs, reports = (
        SqliteCollectionRepositoryV1(reference),
        SqliteBudgetReportRepositoryV1(reference),
    )
    deadline = time.monotonic() + MAX_OBSERVATION_SECONDS
    recovery = SqliteCollectionRecoveryQueryV1(reference)
    quota_progress: dict[str, CollectionRecoveryRunV1] = {}
    while time.monotonic() < deadline:
        _require(_identity() == identity, "m7_browser_closed_service_changed")
        _require(
            scheduled._inventory(reference) == authority,
            "m7_browser_closed_authority_changed",
        )
        observed = datetime.now(UTC)
        for provider in ("claude", "codex"):
            proof = _quota_progress(
                _runs(recovery, provider, closed_at, observed),
                provider,
                closed_at,
                observed,
            )
            if proof is not None:
                quota_progress[provider] = proof
        if len(quota_progress) != 2:
            time.sleep(min(15, max(0, deadline - time.monotonic())))
            continue
        for resource, (graph, service) in authority.items():
            if resource != initial_resource:
                continue
            for metadata in scheduled._scheduled_metadata(
                reference, graph, datetime.now(UTC)
            ):
                if not _prospective_metadata(metadata, closed_at, prior_ids):
                    continue
                run = runs.get_run(OpaqueIdV1(str(metadata["run_id"])))
                _require(
                    isinstance(run, BudgetCollectionRunViewV1),
                    "m7_browser_closed_run_invalid",
                )
                assert isinstance(run, BudgetCollectionRunViewV1)
                captured = runs.get_budget_target(run.run_id)
                _require(
                    isinstance(captured, tuple), "m7_browser_closed_target_invalid"
                )
                assert isinstance(captured, tuple)
                old_graph, old_service, context = captured
                _require(
                    (old_graph, old_service) == (graph, service)
                    and context.scope == "self"
                    and context.grouping == ()
                    and context.range_key in {"7d", "30d"},
                    "m7_browser_closed_context_mismatch",
                )
                _require(
                    run.state == "succeeded"
                    and run.account_id == graph.account_id
                    and run.resource_id == resource
                    and run.target_generation == graph.binding.generation
                    and run.report_id is not None
                    and run.source_id == SOURCE_ID
                    and run.adapter_version == ADAPTER_VERSION
                    and run.provider_version == PROVIDER_VERSION,
                    "m7_browser_closed_run_mismatch",
                )
                assert run.report_id is not None
                stored = reports.get_report(graph.account_id, run.report_id)
                status = reports.get_commit_status(run.run_id, run.capability_id)
                provenance = reports.get_report_provenance(
                    graph.account_id, run.report_id
                )
                _require(
                    stored is not None
                    and status.state == "committed"
                    and status.receipt is not None
                    and provenance is not None,
                    "m7_browser_closed_receipt_missing",
                )
                assert (
                    stored is not None
                    and status.receipt is not None
                    and provenance is not None
                )
                report, receipt = stored.report, status.receipt
                period = BudgetPeriodV1(context.interval_start, context.interval_end)
                _require(
                    period == completed_period(run.requested_at, context.range_key)
                    and report.requested_period == report.covered_period == period
                    and report.completeness == "complete"
                    and report.source_id == SOURCE_ID
                    and report.source_category == "self_requests_and_cost"
                    and report.grouping == ()
                    and report.subject.account_id == graph.account_id
                    and report.subject.resource_id == resource
                    and report.subject.provider_target.target_id
                    == service.access_target_id
                    and report.binding_id == graph.binding.binding_id
                    and report.binding_generation == graph.binding.generation
                    and report.scope_generation == 1
                    and report.scope_id is None
                    and report.scope_evidence == "unresolved"
                    and receipt.run_id == run.run_id
                    and receipt.report_id == run.report_id
                    and receipt.target_generation == run.target_generation
                    and receipt.payload_digest
                    == run.payload_digest
                    == budget_report_payload_digest(report)
                    and receipt.stored_at == stored.stored_at,
                    "m7_browser_closed_report_lineage_mismatch",
                )
                _require(
                    metadata["request_fingerprint"] == metadata["request_digest"]
                    and metadata["linked_run_id"] == run.run_id.value
                    and metadata["request_schedule"]
                    == metadata["schedule_id"]
                    == run.schedule_id.value
                    and metadata["operation_family"]
                    == "collect.ollama.usage." + context.range_key
                    and datetime.fromisoformat(str(metadata["request_time"]))
                    == run.requested_at
                    and datetime.fromisoformat(str(metadata["request_deadline"]))
                    == run.deadline_at,
                    "m7_browser_closed_request_lineage_mismatch",
                )
                _require(
                    provenance.adapter_id == ADAPTER_ID
                    and provenance.adapter_version
                    == provenance.parser_version
                    == ADAPTER_VERSION
                    and provenance.operation_id == run.run_id
                    and provenance.source_id == SOURCE_ID
                    and provenance.decision_reference == EVIDENCE_REFERENCE
                    and run.started_at is not None
                    and run.completed_at is not None,
                    "m7_browser_closed_provenance_mismatch",
                )
                assert run.started_at is not None and run.completed_at is not None
                _require(
                    closed_at
                    < run.requested_at
                    <= run.started_at
                    <= report.collected_at
                    <= stored.stored_at
                    <= run.completed_at
                    <= run.deadline_at,
                    "m7_browser_closed_times_mismatch",
                )
                _require(_identity() == identity, "m7_browser_closed_service_changed")
                installed, _ = _verify_retained_baseline(Path(_cwd(_FIXED_UNIT)))
                _require(installed == revision, "m7_browser_closed_revision_mismatch")
                _window(
                    revision,
                    "reopen",
                    {
                        "account_id": graph.account_id.value,
                        "resource_id": resource.value,
                        "report_id": run.report_id.value,
                        "period_start": period.start.isoformat(),
                        "period_end": period.end.isoformat(),
                        "as_of": datetime.now(UTC).isoformat(),
                    },
                )
                _require(
                    _identity() == identity
                    and scheduled._inventory(reference) == authority,
                    "m7_browser_closed_authority_changed",
                )
                _require(
                    runs.get_run(run.run_id) == run
                    and runs.get_budget_target(run.run_id) == captured
                    and reports.get_report(graph.account_id, run.report_id) == stored
                    and reports.get_commit_status(run.run_id, run.capability_id)
                    == status,
                    "m7_browser_closed_lineage_changed",
                )
                digest = hashlib.sha256(
                    json.dumps(
                        [
                            run.run_id.value,
                            run.report_id.value,
                            receipt.payload_digest,
                            graph.resource_id.value,
                            graph.binding.binding_id.value,
                            graph.binding.generation,
                            context.range_key,
                            [
                                (
                                    provider,
                                    proof.run_id.value,
                                    proof.payload_digest,
                                    [fact.value for fact in proof.observation_ids],
                                )
                                for provider, proof in sorted(quota_progress.items())
                            ],
                        ],
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
                print(
                    json.dumps(
                        {
                            "record_type": (
                                "agentmonitor.m7_browser_closed_collection.v1"
                            ),
                            "status": "passed",
                            "source_revision": revision,
                            "scope": "controlled_dashboard_window_closed",
                            "closed_at": closed_at.isoformat(),
                            "completed_at": run.completed_at.isoformat(),
                            "new_scheduled_runs": 1,
                            "claude_quota_progress": "passed",
                            "codex_quota_progress": "passed",
                            "lineage_sha256": digest,
                            "unsafe_requests": 0,
                            "global_browser_absence_claimed": False,
                        }
                    )
                )
                return
        time.sleep(min(15, max(0, deadline - time.monotonic())))
    if len(quota_progress) != 2:
        pytest.fail("m7_browser_closed_quota_progress_unavailable", pytrace=False)
    pytest.fail(
        "m7_new_scheduled_receipt_not_observed_after_window_closed", pytrace=False
    )


def test_prospective_gate_rejects_old_queued_and_manual_runs() -> None:
    closed = datetime(2026, 11, 12, 12, tzinfo=UTC)
    metadata: dict[str, object] = {
        "run_id": "new-run",
        "trigger_kind": "scheduled",
        "request_trigger": "scheduled",
        "request_auth_method": "internal_scheduler",
        "request_time": (closed + timedelta(seconds=1)).isoformat(),
    }
    assert _prospective_metadata(metadata, closed, frozenset())
    assert not _prospective_metadata(
        dict(metadata, request_time=closed.isoformat()), closed, frozenset()
    )
    assert not _prospective_metadata(
        dict(metadata, trigger_kind="manual"), closed, frozenset()
    )
    assert not _prospective_metadata(
        dict(metadata, request_auth_method="browser_cookie"), closed, frozenset()
    )
    assert not _prospective_metadata(metadata, closed, frozenset({"new-run"}))


def test_quota_progress_requires_new_committed_subscription_facts() -> None:
    from dataclasses import replace

    from agentmonitor.contracts.collection_recovery_v1 import CollectionRecoveryRunV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    closed = datetime(2026, 11, 12, 12, tzinfo=UTC)
    observed = closed + timedelta(minutes=5)
    run = CollectionRecoveryRunV1(
        OpaqueIdV1("quota-run"),
        "claude",
        OpaqueIdV1("account"),
        None,
        None,
        1,
        "subscription.quota",
        "quota-source",
        "1.0.0",
        "a" * 64,
        "quota.v1",
        closed + timedelta(seconds=1),
        observed - timedelta(seconds=1),
        "partial",
        None,
        None,
        None,
        "b" * 64,
        (OpaqueIdV1("fact"),),
    )
    assert _quota_progress((run,), "claude", closed, observed) == run
    for changed in (
        replace(run, requested_at=closed),
        replace(run, provider_key="codex"),
        replace(run, state="failed"),
        replace(run, observation_ids=()),
        replace(run, payload_digest=None),
        replace(run, capability_id="api.usage"),
        replace(run, completed_at=observed + timedelta(seconds=1)),
    ):
        assert _quota_progress((changed,), "claude", closed, observed) is None
