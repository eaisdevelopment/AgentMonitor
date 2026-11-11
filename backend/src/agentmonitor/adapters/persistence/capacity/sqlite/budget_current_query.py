"""Bounded M05 current-report metadata selection; no SQL financial arithmetic."""

from agentmonitor.contracts.capacity_v1 import BudgetCurrentQueryV1, BudgetReportViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_codec import MAX_REPORT_BYTES, utc_text

# Account, resource, scope epoch and requested period are fixed by the query.
# The remaining partition is exactly budget_reports._same_context: subject,
# scope ID, source/category/basis, grouping and currency. Binding generation and
# scope evidence do not change historical money identity. Only metadata enters
# the window sort; the canonical report bodies are loaded after bounds checks.
CURRENT_REPORT_METADATA_SQL = """
WITH eligible AS (
    SELECT report_id, collected_at, stored_at,
           length(CAST(canonical_report_json AS BLOB)) AS report_bytes,
           json_array(
               json_extract(canonical_report_json,'$.subject'),
               json_extract(canonical_report_json,'$.scope_id'),
               json_extract(canonical_report_json,'$.source_id'),
               json_extract(canonical_report_json,'$.source_category'),
               json_extract(canonical_report_json,'$.cost_basis'),
               json_extract(canonical_report_json,'$.grouping'),
               json_extract(canonical_report_json,'$.currency')
           ) AS context_key,
           CASE WHEN json_extract(canonical_report_json,'$.completeness')='complete'
                AND json_extract(canonical_report_json,'$.covered_period.start')
                    = requested_start
                AND json_extract(canonical_report_json,'$.covered_period.end')
                    = requested_end
                THEN 1 ELSE 0 END AS is_complete
    FROM capacity_budget_report
    WHERE account_id=? AND resource_id=? AND requested_start=? AND requested_end=?
      AND json_extract(canonical_report_json,'$.scope_generation')=?
      AND collected_at<=? AND stored_at<=?
), ranked AS (
    SELECT report_id, report_bytes, context_key, is_complete,
           row_number() OVER (
               PARTITION BY context_key
               ORDER BY collected_at DESC, stored_at DESC, report_id DESC
           ) AS attempt_rank,
           row_number() OVER (
               PARTITION BY context_key,is_complete
               ORDER BY collected_at DESC, stored_at DESC, report_id DESC
           ) AS completeness_rank
    FROM eligible
)
SELECT context_key,
       max(CASE WHEN attempt_rank=1 THEN report_id END) AS latest_id,
       max(CASE WHEN attempt_rank=1 THEN report_bytes END) AS latest_bytes,
       max(CASE WHEN is_complete=1 AND completeness_rank=1
           THEN report_id END) AS current_id,
       max(CASE WHEN is_complete=1 AND completeness_rank=1
           THEN report_bytes END) AS current_bytes
FROM ranked
WHERE attempt_rank=1 OR (is_complete=1 AND completeness_rank=1)
GROUP BY context_key
ORDER BY context_key
LIMIT ?
"""


def bounded_current_report_ids(
    references: tuple[tuple[OpaqueIdV1, int], ...],
) -> tuple[OpaqueIdV1, ...] | None:
    """Deduplicate current/attempt IDs before applying the 16MiB read ceiling.

    None means overflow, never an empty successful subtotal. Context count is
    checked first by the caller; at most two references per 200 contexts remain.
    """
    if len(references) > 400:
        return None
    sizes: dict[OpaqueIdV1, int] = {}
    for identity, size in references:
        if (
            not isinstance(identity, OpaqueIdV1)
            or type(size) is not int
            or not 2 <= size <= MAX_REPORT_BYTES
            or identity in sizes
            and sizes[identity] != size
        ):
            raise ValueError("budget_current_metadata_invalid")
        sizes[identity] = size
    if sum(sizes.values()) > MAX_REPORT_BYTES:
        return None
    return tuple(sizes)


def validate_current_report_load(
    query: BudgetCurrentQueryV1,
    view: BudgetReportViewV1,
    *,
    selected_id: OpaqueIdV1,
    selected_bytes: int,
    canonical_text: str,
    collected_at: str,
) -> None:
    """Check the selected metadata against the decoded immutable body."""
    report = view.report
    if (
        view.report_id != selected_id
        or type(selected_bytes) is not int
        or len(canonical_text.encode("utf-8")) != selected_bytes
        or report.subject.account_id != query.account_id
        or report.subject.resource_id != query.resource_id
        or report.scope_generation != query.scope_generation
        or report.requested_period != query.period
        or report.collected_at > query.as_of
        or view.stored_at > query.as_of
        or utc_text(report.collected_at) != collected_at
    ):
        raise ValueError("budget_current_metadata_invalid")
