"""Page one immutable report's exact facts without filling gaps or combining units."""

import hashlib
import json
import re
from datetime import datetime

from agentmonitor.contracts.budget_query_v1 import (
    BudgetHistoryQueryV1,
    BudgetHistoryResultV1,
    BudgetHistoryRowV1,
    BudgetSelectedReportV1,
)
from agentmonitor.contracts.common_v1 import QueryAvailabilityV1, QueryPageV1
from agentmonitor.modules.capacity.domain.budget_account_spend import (
    matches_selected_report,
)
from agentmonitor.modules.capacity.domain.budget_codec import (
    budget_report_digest,
    utc_text,
)

# At most 10,000 report facts means the last continuation offset is 9,999.
_CURSOR = re.compile(r"v1_([0-9a-f]{56})_([1-9][0-9]{0,3})\Z")


def _order(row: BudgetHistoryRowV1) -> tuple[datetime, datetime, str, str]:
    bucket = row.cost if row.cost is not None else row.usage
    assert bucket is not None
    return bucket.period.start, bucket.period.end, row.kind, bucket.bucket_key


def _fingerprint(selected: BudgetSelectedReportV1, query: BudgetHistoryQueryV1) -> str:
    values = (
        "budget-daily-history-v1",
        query.account_id.value,
        query.resource_id.value,
        query.report_id.value,
        utc_text(query.period.start),
        utc_text(query.period.end),
        utc_text(query.as_of),
        query.limit,
        utc_text(selected.report.stored_at),
        budget_report_digest(selected.report.report),
    )
    return hashlib.sha224(
        json.dumps(values, separators=(",", ":")).encode()
    ).hexdigest()


def history_result(
    selected: BudgetSelectedReportV1, query: BudgetHistoryQueryV1
) -> BudgetHistoryResultV1:
    """The caller reauthorizes the retained selection on every page.

    Cursor lifetime belongs to the HTTP cursor envelope. A removed report is
    absent at that read boundary; neither expiry nor a correction selects a
    replacement here. The internal key also pins the immutable body and cutoff.
    """
    if (
        selected.as_of != query.as_of
        or selected.reported_spend.report_id != query.report_id
        or not matches_selected_report(
            selected.report,
            account_id=query.account_id,
            resource_id=query.resource_id,
            report_id=query.report_id,
            period=query.period,
            as_of=query.as_of,
        )
    ):
        raise ValueError("budget_history_context_invalid")
    report = selected.report.report
    rows = tuple(
        sorted(
            (
                *(
                    BudgetHistoryRowV1("cost", cost, None)
                    for cost in report.cost_buckets
                ),
                *(
                    BudgetHistoryRowV1("usage", None, usage)
                    for usage in report.usage_buckets
                ),
            ),
            key=_order,
        )
    )
    fingerprint = _fingerprint(selected, query)
    offset = 0
    if query.after_key is not None:
        match = (
            _CURSOR.fullmatch(query.after_key) if type(query.after_key) is str else None
        )
        if match is None or match[1] != fingerprint:
            raise ValueError("budget_history_cursor_invalid")
        offset = int(match[2])
        if not 0 < offset < len(rows):
            raise ValueError("budget_history_cursor_invalid")
    end = min(offset + query.limit, len(rows))
    has_more = end < len(rows)
    return BudgetHistoryResultV1(
        selected.report,
        selected.reported_spend,
        selected.as_of,
        QueryPageV1(
            rows[offset:end],
            query.limit,
            has_more,
            f"v1_{fingerprint}_{end}" if has_more else None,
            QueryAvailabilityV1("available", "budget_daily_history_read", query.as_of),
        ),
    )
