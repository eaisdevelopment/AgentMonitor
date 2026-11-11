"""Pure admission checks for the normalized budget report commit envelope."""

from agentmonitor.contracts.capacity_v1 import (
    BudgetCollectionInputV1,
    BudgetReportInputV1,
)
from agentmonitor.modules.capacity.domain.budget_codec import (
    MAX_REPORT_BYTES,
    budget_report_digest,
    encode_budget_provenance,
    encode_budget_report,
)

BUDGET_PAYLOAD_SCHEMA = "budget.report.v1"
BUDGET_CAPABILITY_SCHEMA = "2.0.0"


class BudgetCommitError(ValueError):
    """Closed commit failure without input values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def budget_report_payload_digest(report: BudgetReportInputV1) -> str:
    """Expose M05's canonical report digest without leaking its codec boundary."""
    return budget_report_digest(report)


def validate_budget_commit(request: BudgetCollectionInputV1) -> str:
    """Return canonical report text only when envelope and lineage agree.

    This is not credential or scope authorization. Persistence must invoke its
    real transaction-bound M02 fence before replay or insertion.
    """
    if not isinstance(request, BudgetCollectionInputV1):
        raise BudgetCommitError("budget_commit_type_invalid")
    if request.payload_schema != BUDGET_PAYLOAD_SCHEMA:
        raise BudgetCommitError("budget_payload_schema_invalid")
    report = request.payload
    encoded = encode_budget_report(report)
    if budget_report_payload_digest(report) != request.payload_digest:
        raise BudgetCommitError("budget_digest_mismatch")
    provenance = request.provenance
    encode_budget_provenance(provenance)
    if (
        provenance.provider_key != report.subject.provider_key
        or provenance.capability_id != request.capability_id
        or provenance.capability_schema_version != BUDGET_CAPABILITY_SCHEMA
        or provenance.source_id != report.source_id
        or provenance.collected_at != report.collected_at
    ):
        raise BudgetCommitError("budget_provenance_mismatch")
    complete = (
        report.completeness == "complete"
        and report.covered_period == report.requested_period
    )
    if request.terminal_state != ("succeeded" if complete else "partial"):
        raise BudgetCommitError("budget_terminal_state_mismatch")
    return encoded


def budget_history_page_count(sizes: tuple[int, ...], limit: int) -> int:
    """Choose a prefix before materializing JSON, capped by both rows and bytes."""
    if (
        type(limit) is not int
        or not 1 <= limit <= 200
        or len(sizes) > limit + 1
        or any(
            type(size) is not int or not 2 <= size <= MAX_REPORT_BYTES for size in sizes
        )
    ):
        raise BudgetCommitError("budget_history_sizes_invalid")
    total = 0
    count = 0
    for size in sizes:
        if count >= limit or total + size > MAX_REPORT_BYTES:
            break
        total += size
        count += 1
    return count
