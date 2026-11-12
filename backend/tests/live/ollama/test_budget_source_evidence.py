"""Real immutable provenance over private SQLite; no source replay or requests."""

from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.live.ollama.test_budget_monetary_persistence import (
    _monetary_report,
    _require,
)
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_genuine_monetary_source_evidence_is_bound_and_survives_reopen(
    tmp_path: Path,
) -> None:
    reference = _private_real_copy(tmp_path)
    run, stored = _monetary_report(reference)
    repository = SqliteBudgetReportRepositoryV1(reference)
    account = stored.report.subject.account_id
    provenance = repository.get_report_provenance(account, stored.report_id)
    _require(provenance is not None, "genuine_report_provenance_required")
    assert provenance is not None
    _require(
        provenance.operation_id == run.run_id
        and provenance.source_id == stored.report.source_id
        and provenance.collected_at == stored.report.collected_at,
        "genuine_report_provenance_lineage_changed",
    )
    _require(
        repository.get_report_provenance(
            OpaqueIdV1("not-the-report-account"), stored.report_id
        )
        is None,
        "report_provenance_cross_account_disclosure",
    )
    _require(
        repository.get_report_provenance(account, OpaqueIdV1("absent-report")) is None,
        "absent_report_provenance_invented",
    )
    from agentmonitor.composition.budget_analysis import StoredBudgetSourceEvidenceV1

    evidence = StoredBudgetSourceEvidenceV1(repository.get_report_provenance)(stored)
    _require(evidence is not None, "genuine_monetary_source_evidence_required")
    assert evidence is not None
    _require(
        evidence.report_id == stored.report_id
        and evidence.disjoint_costs
        and evidence.corrections_resolved
        and not evidence.zero_day_coverage
        and evidence.cost_freshness_deadline is None,
        "genuine_source_semantics_changed",
    )
    reopened = SqliteBudgetReportRepositoryV1(
        DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    )
    _require(
        reopened.get_report_provenance(account, stored.report_id) == provenance
        and StoredBudgetSourceEvidenceV1(reopened.get_report_provenance)(stored)
        == evidence,
        "genuine_source_evidence_changed_on_reopen",
    )
