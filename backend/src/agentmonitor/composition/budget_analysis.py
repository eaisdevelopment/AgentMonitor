"""Route stored, receipt-validated provenance to its source-owned policy."""

from agentmonitor.adapters.providers.ollama.api.policy import report_source_evidence
from agentmonitor.contracts.budget_forecast_v1 import (
    BudgetReportProvenancePortV1,
    BudgetSourceEvidenceV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1


class StoredBudgetSourceEvidenceV1:
    """Unsupported or unavailable lineage cannot assert financial semantics."""

    def __init__(self, provenance: BudgetReportProvenancePortV1) -> None:
        self._provenance = provenance

    def __call__(self, report: BudgetReportViewV1) -> BudgetSourceEvidenceV1 | None:
        try:
            provenance = self._provenance(
                report.report.subject.account_id, report.report_id
            )
        except ValueError:
            return None
        if provenance is None:
            return None
        return report_source_evidence(report, provenance)
