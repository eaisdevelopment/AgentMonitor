"""Route stored, receipt-validated provenance to its source-owned policy."""

from agentmonitor.adapters.providers.claude.anthropic_api.analysis_policy import (
    report_source_evidence as anthropic_source_evidence,
)
from agentmonitor.adapters.providers.codex.openai_api.analysis_policy import (
    report_source_evidence as openai_source_evidence,
)
from agentmonitor.adapters.providers.ollama.api.policy import (
    report_source_evidence as ollama_source_evidence,
)
from agentmonitor.contracts.budget_forecast_v1 import (
    BudgetReportProvenancePortV1,
    BudgetSourceEvidenceV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1


def resolve_report_source_evidence(
    report: BudgetReportViewV1, provenance: ObservationProvenanceV1
) -> BudgetSourceEvidenceV1 | None:
    """Route pure semantics; each adapter validates its exact source lineage."""
    provider = report.report.subject.provider_key
    if provider == "claude":
        return anthropic_source_evidence(report, provenance)
    if provider == "codex":
        return openai_source_evidence(report, provenance)
    if provider == "ollama":
        return ollama_source_evidence(report, provenance)
    return None


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
        return resolve_report_source_evidence(report, provenance)
