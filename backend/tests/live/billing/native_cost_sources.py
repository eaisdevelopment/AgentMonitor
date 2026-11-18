"""Alternate real test callbacks; official transport, production normalization.

Caller must own the production worker/admission/credential/budget/commit fences.
No execution at import, credentials lookup, retries, provider mutation or raw
response retention. Source admission artifacts establish the exact native units.
"""

from __future__ import annotations

import http.client
import ssl
import time
from datetime import UTC, datetime
from typing import cast

from agentmonitor.adapters.providers.claude.anthropic_api import policy as ap
from agentmonitor.adapters.providers.claude.anthropic_api import source as anthropic
from agentmonitor.adapters.providers.claude.anthropic_api.usage_policy import (
    build_analytics_report,
)
from agentmonitor.adapters.providers.codex.openai_api import policy as op
from agentmonitor.adapters.providers.codex.openai_api import source as openai
from agentmonitor.contracts.capacity_v1 import BudgetCostBucketV1, BudgetReportInputV1

from backend.tests.live.billing.native_cost_comparison import (
    CostScalar,
    NormalizedCost,
    compare_cost_scalars,
    comparison_disposition,
    native_amount,
)

# Independent allowlist from contracts/provider-system/*-analytics-v1.1.json.
_ANTHROPIC_NATIVE_GROUP = {
    "workspace": "workspace_id",
    "api_key_id": "api_key_id",
    "model": "model",
    "token_category": "token_type",
}
_OPENAI_NATIVE_GROUP = {"project": "project_id", "api_key_id": "api_key_id"}


def _stamp(value: object, provider: str) -> datetime:
    if provider == "anthropic" and type(value) is str:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if provider == "openai" and type(value) is int:
        return datetime.fromtimestamp(value, UTC)
    raise ValueError("native_cost_comparison_fields_invalid")


def _scalar(
    provider: str,
    start: object,
    end: object,
    amount: object,
    currency: object,
    grouping: tuple[str, ...],
    dimension: object,
) -> CostScalar:
    if (
        type(currency) is not str
        or dimension is not None
        and type(dimension) is not str
    ):
        raise ValueError("native_cost_comparison_fields_invalid")
    return CostScalar(
        _stamp(start, provider),
        _stamp(end, provider),
        native_amount(provider, amount),
        currency,
        ((grouping[0], dimension),) if grouping else (),
    )


def _checked_report(
    provider: str,
    request: ap.AnthropicCostRequestV1 | op.OpenAICostRequestV1,
    report: BudgetReportInputV1,
    native: list[CostScalar],
    *,
    exhausted: bool,
    requests: int,
    witness: dict[str, object],
) -> bool:
    """No disputed report may reach the ordinary production commit callback."""
    witness.update(
        requests=requests,
        pages_exhausted=exhausted,
        qualified_zero=False,
        currency=report.currency,
    )
    try:
        if (
            report.subject != request.subject
            or report.binding_id != request.binding.binding_id
            or report.binding_generation != request.binding.generation
            or report.scope_id != request.scope_id
            or report.scope_evidence != request.scope_evidence
            or report.scope_generation != request.scope_generation
            or report.grouping != request.grouping
            or report.requested_period != request.period
            or report.source_id
            != (ap.SOURCE_ID if provider == "anthropic" else op.SOURCE_ID)
            or report.usage_buckets
        ):
            raise ValueError("native_cost_comparison_context_invalid")
        rows = tuple(
            NormalizedCost(
                row.period.start,
                row.period.end,
                int(row.amount.amount.coefficient),
                row.amount.amount.scale,
                row.amount.currency,
                tuple((item.kind, item.value) for item in row.dimensions),
            )
            for row in report.cost_buckets
        )
        count = compare_cost_scalars(
            provider,
            tuple(native),
            rows,
            request.period.start,
            request.period.end,
            request.grouping,
        )
    except (ValueError, TypeError, KeyError, OverflowError):
        witness.update(
            comparison_state="mismatch",
            comparison_reason="native_cost_comparison_mismatch",
            compared_rows=0,
        )
        return False
    complete = (
        exhausted
        and report.completeness == "complete"
        and report.covered_period == request.period
    )
    comparison_state, comparison_reason, qualified_zero = comparison_disposition(
        provider,
        count,
        complete=complete,
        exhausted=exhausted,
        currency=report.currency,
        cost_basis=report.cost_basis,
        empty_means_zero=report.empty_means_zero,
    )
    witness.update(
        comparison_state=comparison_state,
        comparison_reason=comparison_reason,
        compared_rows=count,
        qualified_zero=qualified_zero,
        cost_basis=report.cost_basis,
        source_data_through=None
        if report.source_data_through is None
        else report.source_data_through.isoformat(),
    )
    return True


def collect_anthropic_cost_with_comparison(
    request: ap.AnthropicCostRequestV1,
    *,
    authorization: anthropic.AnthropicCostAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
    witness: dict[str, object],
) -> anthropic.AnthropicCostResultV1:
    """One bounded real report collection, independently checking every cost row."""
    if type(request) is not ap.AnthropicCostRequestV1:
        raise ValueError("anthropic_cost_request_required")
    witness.update(
        comparison_state="not_run",
        comparison_reason="native_cost_source_unavailable",
        compared_rows=0,
        pages_exhausted=False,
        requests=0,
        qualified_zero=False,
    )
    if authorization is None:
        return anthropic.AnthropicCostResultV1(
            "authorization_unavailable",
            "anthropic_cost_authorization_unavailable",
            None,
            0,
        )
    rows: list[BudgetCostBucketV1] = []
    native: list[CostScalar] = []
    seen: set[str] = set()
    cursors: set[str] = set()
    cursor: str | None = None
    refreshed: datetime | None = None
    requests = normalized_bytes = 0
    page: dict[str, object] | None = None
    exhausted = False
    try:
        deadline = ap.bounded_deadline(
            time.monotonic(), deadline_monotonic, ap.REPORT_SECONDS
        )
        with anthropic.request_deadline(deadline):
            pass
        for page_index in range(ap.MAX_REQUESTS):
            requests += 1
            page = anthropic._read_page(request, cursor, authorization, deadline)
            if set(page) != {"data", "has_more", "next_page", "data_refreshed_at"}:
                raise ValueError("anthropic_cost_page_invalid")
            data = page["data"]
            if (
                not isinstance(data, list)
                or len(rows) + len(data) > ap.MAX_ROWS
                or type(page["has_more"]) is not bool
            ):
                raise ValueError("anthropic_cost_page_limits_invalid")
            watermark = (
                None
                if page["data_refreshed_at"] is None
                else anthropic._timestamp(page["data_refreshed_at"])
            )
            if page_index and watermark != refreshed or watermark is None and data:
                raise ValueError("anthropic_cost_snapshot_invalid")
            refreshed = watermark
            for value in data:
                row = anthropic._bucket(value, request)
                if row.bucket_key in seen:
                    raise ValueError("anthropic_analytics_duplicate_bucket")
                normalized_bytes += 1024
                if (
                    len(rows) >= ap.MAX_ROWS
                    or normalized_bytes > ap.MAX_NORMALIZED_BYTES
                ):
                    raise ValueError("anthropic_analytics_normalized_too_large")
                seen.add(row.bucket_key)
                rows.append(row)
                # Production parser has validated the shape; extraction uses
                # only allowlisted scalars, independently of cents_to_usd.
                item = cast(dict[str, object], value)
                cost = cast(dict[str, object], item["cost"])
                group = cast(dict[str, object], item["group"])
                try:
                    native.append(
                        _scalar(
                            "anthropic",
                            item["starting_at"],
                            item["ending_at"],
                            cost["amount"],
                            cost["currency"],
                            request.grouping,
                            group.get(_ANTHROPIC_NATIVE_GROUP[request.grouping[0]])
                            if request.grouping
                            else None,
                        )
                    )
                except (ValueError, TypeError, KeyError, OverflowError):
                    witness.update(
                        comparison_state="mismatch",
                        comparison_reason="native_cost_extraction_invalid",
                        requests=requests,
                    )
                    return anthropic.AnthropicCostResultV1(
                        "invalid_provider_data",
                        "anthropic_cost_data_invalid",
                        None,
                        requests,
                        200,
                    )
            next_page = page["next_page"]
            if page["has_more"]:
                if type(next_page) is not str or next_page in cursors:
                    raise ValueError("anthropic_cost_pagination_invalid")
                ap.request_path(request, next_page)
                cursors.add(next_page)
                cursor = next_page
            else:
                if next_page is not None:
                    raise ValueError("anthropic_cost_pagination_invalid")
                exhausted = True
            page.clear()
            page = None
            ap.bounded_deadline(time.monotonic(), deadline, ap.REPORT_SECONDS)
            if exhausted:
                break
        report = build_analytics_report(
            request,
            rows,
            refreshed,
            None if exhausted else "page_budget_exceeded",
            datetime.now(UTC),
        )
        ap.bounded_deadline(time.monotonic(), deadline, ap.REPORT_SECONDS)
        if not _checked_report(
            "anthropic",
            request,
            report,
            native,
            exhausted=exhausted,
            requests=requests,
            witness=witness,
        ):
            return anthropic.AnthropicCostResultV1(
                "invalid_provider_data",
                "anthropic_cost_data_invalid",
                None,
                requests,
                200,
            )
        state: anthropic.State = (
            "success" if report.completeness == "complete" else "partial"
        )
        return anthropic.AnthropicCostResultV1(
            state,
            "anthropic_cost_" + (state if exhausted else "page_budget_exceeded"),
            report,
            requests,
            200,
        )
    except anthropic._SourceFailure as failure:
        return anthropic.AnthropicCostResultV1(
            failure.state,
            "anthropic_cost_" + failure.state,
            None,
            requests,
            failure.status,
            failure.retry,
        )
    except TimeoutError:
        state = "deadline_exceeded"
    except (ssl.SSLError, OSError, http.client.HTTPException):
        state = "provider_unavailable"
    except anthropic._WorkerRequired:
        state = "worker_required"
    except (ValueError, RecursionError):
        state = "invalid_provider_data"
    except Exception:
        state = "internal_error"
    finally:
        if page is not None:
            page.clear()
        witness["requests"] = requests
    suffix = {
        "provider_unavailable": "transport_unavailable",
        "worker_required": "dedicated_worker_required",
        "invalid_provider_data": "data_invalid",
    }.get(state, state)
    return anthropic.AnthropicCostResultV1(
        state, "anthropic_cost_" + suffix, None, requests
    )


def collect_openai_cost_with_comparison(
    request: op.OpenAICostRequestV1,
    *,
    authorization: openai.OpenAICostAuthorizationV1 | None,
    deadline_monotonic: float | None = None,
    witness: dict[str, object],
) -> openai.OpenAICostResultV1:
    """One official paginated cost read; missing amount never becomes zero."""
    if type(request) is not op.OpenAICostRequestV1:
        raise ValueError("openai_cost_request_required")
    witness.update(
        comparison_state="not_run",
        comparison_reason="native_cost_source_unavailable",
        compared_rows=0,
        pages_exhausted=False,
        requests=0,
        qualified_zero=False,
    )
    if authorization is None:
        return openai.OpenAICostResultV1(
            "authorization_unavailable",
            "openai_cost_authorization_unavailable",
            None,
            0,
        )
    rows: list[BudgetCostBucketV1] = []
    native: list[CostScalar] = []
    seen: set[datetime] = set()
    row_keys: set[str] = set()
    omissions: set[str] = set()
    cursors: set[str] = set()
    cursor: str | None = None
    requests = normalized_bytes = 0
    page: dict[str, object] | None = None
    exhausted = False
    try:
        deadline = op.bounded_deadline(
            time.monotonic(), deadline_monotonic, op.REPORT_SECONDS
        )
        with openai.request_deadline(deadline):
            pass
        for _page_index in range(op.MAX_REQUESTS):
            requests += 1
            page = openai._read_page(request, cursor, authorization, deadline)
            if (
                set(page) != {"object", "data", "has_more", "next_page"}
                or page["object"] != "page"
            ):
                raise ValueError("openai_cost_page_invalid")
            data = page["data"]
            if (
                not isinstance(data, list)
                or len(seen) + len(data) > op.MAX_ROWS
                or type(page["has_more"]) is not bool
            ):
                raise ValueError("openai_cost_page_limits_invalid")
            for value in data:
                period, batch, unavailable = openai._bucket(
                    value, request, op.MAX_ROWS - len(rows)
                )
                if period.start in seen:
                    raise ValueError("openai_cost_duplicate_bucket")
                normalized_bytes += 512
                if normalized_bytes > op.MAX_NORMALIZED_BYTES:
                    raise ValueError("openai_cost_normalized_too_large")
                seen.add(period.start)
                for row in batch:
                    if (
                        not isinstance(row, BudgetCostBucketV1)
                        or row.bucket_key in row_keys
                    ):
                        raise ValueError("openai_report_duplicate_row")
                    normalized_bytes += 1024
                    if (
                        len(rows) >= op.MAX_ROWS
                        or normalized_bytes > op.MAX_NORMALIZED_BYTES
                    ):
                        raise ValueError("openai_report_normalized_too_large")
                    row_keys.add(row.bucket_key)
                    rows.append(row)
                if unavailable:
                    omissions.add("monetary_fields_unavailable")
                item = cast(dict[str, object], value)
                results = cast(list[dict[str, object]], item["results"])
                for result in results:
                    amount = result.get("amount")
                    if not isinstance(amount, dict) or set(amount) != {
                        "value",
                        "currency",
                    }:
                        continue
                    try:
                        native.append(
                            _scalar(
                                "openai",
                                item["start_time"],
                                item["end_time"],
                                amount["value"],
                                amount["currency"],
                                request.grouping,
                                result.get(_OPENAI_NATIVE_GROUP[request.grouping[0]])
                                if request.grouping
                                else None,
                            )
                        )
                    except (ValueError, TypeError, KeyError, OverflowError):
                        witness.update(
                            comparison_state="mismatch",
                            comparison_reason="native_cost_extraction_invalid",
                            requests=requests,
                        )
                        return openai.OpenAICostResultV1(
                            "invalid_provider_data",
                            "openai_cost_data_invalid",
                            None,
                            requests,
                            200,
                        )
            next_page = page["next_page"]
            if page["has_more"]:
                if type(next_page) is not str or next_page in cursors:
                    raise ValueError("openai_cost_pagination_invalid")
                op.request_path(request, next_page)
                cursors.add(next_page)
                cursor = next_page
            else:
                if next_page is not None:
                    raise ValueError("openai_cost_pagination_invalid")
                exhausted = True
            page.clear()
            page = None
            op.bounded_deadline(time.monotonic(), deadline, op.REPORT_SECONDS)
            if exhausted:
                break
        if not exhausted:
            omissions.add("page_budget_exceeded")
        report = openai._report(
            request, rows, seen, omissions, collected_at=datetime.now(UTC)
        )
        op.bounded_deadline(time.monotonic(), deadline, op.REPORT_SECONDS)
        if not _checked_report(
            "openai",
            request,
            report,
            native,
            exhausted=exhausted,
            requests=requests,
            witness=witness,
        ):
            return openai.OpenAICostResultV1(
                "invalid_provider_data", "openai_cost_data_invalid", None, requests, 200
            )
        state: openai.State = (
            "success" if report.completeness == "complete" else "partial"
        )
        reason = (
            "openai_cost_page_budget_exceeded"
            if not exhausted
            else "openai_cost_monetary_unavailable"
            if not rows
            else "openai_cost_" + state
        )
        return openai.OpenAICostResultV1(state, reason, report, requests, 200)
    except openai._SourceFailure as failure:
        return openai.OpenAICostResultV1(
            failure.state,
            "openai_cost_" + failure.state,
            None,
            requests,
            failure.status,
            failure.retry,
        )
    except TimeoutError:
        state = "deadline_exceeded"
    except (ssl.SSLError, OSError, http.client.HTTPException):
        state = "provider_unavailable"
    except openai._WorkerRequired:
        state = "worker_required"
    except (ValueError, RecursionError):
        state = "invalid_provider_data"
    except Exception:
        state = "internal_error"
    finally:
        if page is not None:
            page.clear()
        witness["requests"] = requests
    suffix = {
        "provider_unavailable": "transport_unavailable",
        "worker_required": "dedicated_worker_required",
        "invalid_provider_data": "data_invalid",
    }.get(state, state)
    return openai.OpenAICostResultV1(state, "openai_cost_" + suffix, None, requests)
