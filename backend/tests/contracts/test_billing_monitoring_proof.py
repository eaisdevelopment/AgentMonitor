"""Pure lineage policy; constructed records never cross an I/O boundary."""

from dataclasses import replace
from datetime import timedelta

import pytest
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionCommitStatusV1,
    BudgetCollectionReceiptV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import BillingAccessTargetV1
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)

from backend.tests.contracts.test_anthropic_billing_run import NOW, _report, _target


def _evidence() -> tuple[
    BillingAccessTargetV1,
    BudgetCollectionRunViewV1,
    BudgetCollectionCommitStatusV1,
    BudgetReportViewV1,
]:
    target = _target()
    report = _report()
    digest = budget_report_payload_digest(report)
    stored = NOW + timedelta(seconds=3)
    receipt = BudgetCollectionReceiptV1(
        run_id=OpaqueIdV1("run"),
        target_generation=1,
        capability_id="api.cost",
        payload_schema="budget.report.v1",
        payload_digest=digest,
        consumer_key="capacity",
        consumer_version="1.0.0",
        report_id=OpaqueIdV1("report"),
        fact_ids=(),
        stored_at=stored,
        receipt_version=1,
    )
    run = BudgetCollectionRunViewV1(
        run_id=receipt.run_id,
        schedule_id=OpaqueIdV1("schedule"),
        provider_key="claude",
        account_id=target.connection.account_id,
        resource_id=target.connection.resource_id,
        capability_id="api.cost",
        state="succeeded",
        source_id=report.source_id,
        adapter_version="1.0.0",
        provider_version=None,
        target_generation=1,
        fencing_token=1,
        requested_at=NOW,
        started_at=NOW,
        completed_at=stored,
        deadline_at=NOW + timedelta(seconds=120),
        duration_ms=3000,
        payload_digest=digest,
        outcome_code="succeeded",
        error_code=None,
        observation_ids=(),
        report_id=receipt.report_id,
    )
    return (
        target,
        run,
        BudgetCollectionCommitStatusV1("committed", receipt),
        BudgetReportViewV1(receipt.report_id, report, stored),
    )


def test_current_generation_receipt_and_report_are_required() -> None:
    from agentmonitor.composition.billing_monitoring import monitoring_proof

    target, run, commit, report = _evidence()
    instant = NOW + timedelta(seconds=4)
    proof = monitoring_proof(target, target, run, commit, report, instant)
    assert proof.report_id == report.report_id and proof.run_id == run.run_id
    # Disabling monitoring changes the connection version, not provider access.
    changed = replace(target, connection=replace(target.connection, record_version=6))
    assert (
        monitoring_proof(changed, target, run, commit, report, instant).current_target
        == changed
    )
    for invalid in (
        replace(target, binding=replace(target.binding, generation=8)),
        replace(target, connection=replace(target.connection, scope_generation=4)),
        replace(target, connection=replace(target.connection, scope_id="different")),
        replace(
            target,
            connection=replace(target.connection, resource_id=OpaqueIdV1("other")),
        ),
    ):
        with pytest.raises(
            ValueError, match="billing_monitoring_verification_required"
        ):
            monitoring_proof(invalid, target, run, commit, report, instant)
    receipt = commit.receipt
    assert receipt is not None
    for invalid_commit in (
        BudgetCollectionCommitStatusV1("not_committed", None),
        replace(commit, receipt=replace(receipt, report_id=OpaqueIdV1("other"))),
        replace(commit, receipt=replace(receipt, payload_digest="0" * 64)),
    ):
        with pytest.raises(
            ValueError, match="billing_monitoring_verification_required"
        ):
            monitoring_proof(target, target, run, invalid_commit, report, instant)
    with pytest.raises(ValueError, match="billing_monitoring_verification_required"):
        monitoring_proof(target, target, run, commit, report, NOW)


@pytest.mark.parametrize(
    "failure", ["run_source", "run_report", "receipt_run", "partial", "digest", "empty"]
)
def test_lineage_or_coverage_failure_is_not_access_verification(failure: str) -> None:
    from agentmonitor.composition.billing_monitoring import monitoring_proof

    target, run, commit, report = _evidence()
    receipt = commit.receipt
    assert receipt is not None
    if failure == "run_source":
        run = replace(run, source_id="other-source")
    elif failure == "run_report":
        run = replace(run, report_id=OpaqueIdV1("other-report"))
    elif failure == "receipt_run":
        commit = replace(
            commit, receipt=replace(receipt, run_id=OpaqueIdV1("other-run"))
        )
    elif failure == "partial":
        run = replace(run, state="partial", outcome_code="partial")
    elif failure == "digest":
        report = replace(report, report=replace(report.report, cost_buckets=()))
    else:
        # Genuine complete empty coverage qualifies without manufactured facts.
        report = replace(report, report=replace(report.report, cost_buckets=()))
        digest = budget_report_payload_digest(report.report)
        commit = replace(commit, receipt=replace(receipt, payload_digest=digest))
        run = replace(run, payload_digest=digest)
        assert (
            monitoring_proof(
                target, target, run, commit, report, NOW + timedelta(seconds=4)
            ).report_id
            == report.report_id
        )
        return
    with pytest.raises(ValueError, match="billing_monitoring_verification_required"):
        monitoring_proof(
            target, target, run, commit, report, NOW + timedelta(seconds=4)
        )
