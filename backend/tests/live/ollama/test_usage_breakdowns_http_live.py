"""Allocated breakdown route over unchanged genuine grouped facts and real IAM."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import pytest
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.api.v1.schemas.budgets import BudgetHistoryWireV1
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.foundation.application import LifecycleHooksV1

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def _check(condition: bool, code: str) -> None:
    if not condition:
        pytest.fail(code, pytrace=False)


def test_genuine_grouped_breakdown_pages_and_context_over_real_http(
    tmp_path: Path,
) -> None:
    data, iam = tmp_path / "data", tmp_path / "iam"
    data.mkdir(mode=0o700)
    iam.mkdir(mode=0o700)
    reference = _private_real_copy(data)
    reports = SqliteBudgetReportRepositoryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    now = datetime.now(UTC)
    stored = None
    cursor = None
    for _ in range(20):
        batch = runs.list_runs("ollama", None, now, 500, cursor)
        for run in batch:
            if (
                not isinstance(run, BudgetCollectionRunViewV1)
                or run.report_id is None
                or run.account_id is None
            ):
                continue
            candidate = reports.get_report(run.account_id, run.report_id)
            if (
                candidate is not None
                and candidate.report.grouping == ("model",)
                and len(candidate.report.cost_buckets)
                + len(candidate.report.usage_buckets)
                > 1
            ):
                stored = candidate
                break
        if stored is not None or len(batch) < 500:
            break
        cursor = batch[-1].run_id.value
    _check(stored is not None, "genuine_retained_model_report_required")
    assert stored is not None
    report = stored.report
    assert (
        report.subject.account_id is not None and report.subject.resource_id is not None
    )
    account_id, resource_id = (
        report.subject.account_id.value,
        report.subject.resource_id.value,
    )
    config = data / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    readers = create_iam_application(config, data, lifecycle=LifecycleHooksV1())
    readers.state.lifecycle.hooks = replace(readers.state.lifecycle.hooks, tasks=())
    app, credential = _installation(iam)
    app.state.lifecycle.hooks = replace(app.state.lifecycle.hooks, tasks=())
    app.state.observation_ports = readers.state.observation_ports
    selection = {
        "account_id": account_id,
        "report_id": stored.report_id.value,
        "period_start": report.requested_period.start.isoformat(),
        "period_end": report.requested_period.end.isoformat(),
        "as_of": now.isoformat(),
        "limit": "1",
    }
    route = f"/api/v1/budgets/{resource_id}/usage-breakdowns?"
    history_route = f"/api/v1/budgets/{resource_id}/history?"
    query = {**selection, "dimension_kind": "model"}
    expected = {("cost", row.bucket_key): row for row in report.cost_buckets} | {
        ("usage", row.bucket_key): row for row in report.usage_buckets
    }

    async def exercise() -> None:
        jar = http.cookiejar.CookieJar()
        async with _running(app) as origin:
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
                cookies=jar,
            )
            _check(login[0] == 204, "breakdowns_test_authentication_failed")
            first = await asyncio.to_thread(
                _request, origin, "GET", route + urlencode(query), cookies=jar
            )
            _check(
                first[0] == 200,
                f"genuine_usage_breakdowns_endpoint_status_{first[0]}",
            )
            payload = BudgetHistoryWireV1.model_validate_json(first[2])
            first_payload = payload
            seen: set[tuple[str, str]] = set()
            cursors: set[str] = set()
            for _ in range(len(expected) + 1):
                _check(
                    payload.report.report_id == stored.report_id.value
                    and payload.report.account_id == account_id
                    and payload.report.resource_id == resource_id
                    and payload.report.grouping == ["model"]
                    and payload.report.requested_period.start
                    == report.requested_period.start
                    and payload.report.requested_period.end
                    == report.requested_period.end
                    and payload.as_of == now
                    and payload.availability.state == "available",
                    "breakdowns_report_context_changed",
                )
                _check(
                    payload.report == first_payload.report
                    and payload.reported_spend == first_payload.reported_spend,
                    "breakdowns_paging_metadata_changed",
                )
                _check(len(payload.items) == 1, "breakdowns_page_bound_changed")
                for item in payload.items:
                    row = item.cost if item.kind == "cost" else item.usage
                    _check(row is not None, "breakdowns_fact_missing")
                    assert row is not None
                    key = item.kind, row.bucket_key
                    _check(
                        key in expected and key not in seen,
                        "breakdowns_fact_identity_changed",
                    )
                    original = expected[key]
                    seen.add(key)
                    _check(
                        row.period.start == original.period.start
                        and row.period.end == original.period.end
                        and [(d.kind, d.value, d.is_remainder) for d in row.dimensions]
                        == [
                            (d.kind, d.value, d.is_remainder)
                            for d in original.dimensions
                        ],
                        "breakdowns_dimension_or_period_changed",
                    )
                    if item.cost is not None:
                        from agentmonitor.contracts.capacity_v1 import (
                            BudgetCostBucketV1,
                        )

                        _check(
                            isinstance(original, BudgetCostBucketV1),
                            "breakdowns_fact_kind_changed",
                        )
                        assert isinstance(original, BudgetCostBucketV1)
                        _check(
                            item.cost.amount.coefficient
                            == original.amount.amount.coefficient
                            and item.cost.amount.scale == original.amount.amount.scale
                            and item.cost.amount.currency == original.amount.currency
                            and item.cost.kind == original.kind,
                            "breakdowns_exact_cost_changed",
                        )
                    else:
                        from agentmonitor.contracts.capacity_v1 import (
                            BudgetUsageBucketV1,
                        )

                        assert item.usage is not None
                        _check(
                            isinstance(original, BudgetUsageBucketV1),
                            "breakdowns_fact_kind_changed",
                        )
                        assert isinstance(original, BudgetUsageBucketV1)
                        _check(
                            item.usage.quantity.coefficient
                            == original.quantity.amount.coefficient
                            and item.usage.quantity.scale
                            == original.quantity.amount.scale
                            and item.usage.quantity.unit == original.quantity.unit,
                            "breakdowns_exact_usage_changed",
                        )
                next_cursor = payload.page.next_cursor
                if next_cursor is None:
                    break
                _check(next_cursor not in cursors, "breakdowns_cursor_repeated")
                cursors.add(next_cursor)
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    route + urlencode({**query, "cursor": next_cursor}),
                    cookies=jar,
                )
                _check(response[0] == 200, "breakdowns_continuation_failed")
                payload = BudgetHistoryWireV1.model_validate_json(response[2])
            _check(
                seen == set(expected) and payload.page.next_cursor is None,
                "breakdowns_source_set_incomplete",
            )
            history = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                history_route + urlencode(selection),
                cookies=jar,
            )
            _check(history[0] == 200, "breakdowns_history_control_unavailable")
            history_cursor = BudgetHistoryWireV1.model_validate_json(
                history[2]
            ).page.next_cursor
            _check(
                history_cursor is not None
                and first_payload.page.next_cursor is not None,
                "breakdowns_cursor_evidence_missing",
            )
            cases = (
                (
                    route + urlencode({**query, "dimension_kind": "workspace"}),
                    400,
                    "invalid_filter",
                ),
                (route + urlencode(selection), 422, "invalid_request_fields"),
                (
                    route + urlencode({**query, "account_id": "absent-account"}),
                    404,
                    None,
                ),
                (route + urlencode({**query, "report_id": "absent-report"}), 404, None),
                (
                    route
                    + urlencode(
                        {
                            **query,
                            "period_start": (
                                report.requested_period.start - timedelta(days=1)
                            ).isoformat(),
                            "period_end": (
                                report.requested_period.end - timedelta(days=1)
                            ).isoformat(),
                        }
                    ),
                    404,
                    None,
                ),
                (
                    route + urlencode({**query, "cursor": history_cursor}),
                    400,
                    "cursor_query_mismatch",
                ),
                (
                    history_route
                    + urlencode(
                        {**selection, "cursor": first_payload.page.next_cursor}
                    ),
                    400,
                    "cursor_query_mismatch",
                ),
            )
            for case_index, (path, status, code) in enumerate(cases):
                response = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                _check(
                    response[0] == status,
                    f"breakdowns_invalid_selection_not_refused_case_{case_index}",
                )
                if code is not None:
                    _check(
                        json.loads(response[2]).get("code") == code,
                        f"breakdowns_refusal_code_changed_case_{case_index}",
                    )
            unauthorized = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                route + urlencode(query),
                headers={"Origin": origin},
            )
            _check(unauthorized[0] == 401, "breakdowns_unauthorized_read_allowed")
            schema = app.openapi()
            _check(
                schema["paths"]["/api/v1/budgets/{budget_id}/usage-breakdowns"]["get"][
                    "operationId"
                ]
                == "capacity_list_usage_breakdowns_v1",
                "breakdowns_operation_identity_changed",
            )
            _check(
                reports.get_report(report.subject.account_id, stored.report_id)
                == stored,
                "breakdowns_source_mutated",
            )
            print(
                f"M7 BREAKDOWNS HTTP: PASSED facts={len(seen)} "
                f"pages={len(cursors) + 1} provider_requests=0"
            )

    asyncio.run(exercise())
