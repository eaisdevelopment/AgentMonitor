"""Real HTTP reads of a private genuine report snapshot; no provider calls."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


@pytest.mark.parametrize("require_money", (False, True), ids=("history", "money"))
def test_genuine_history_pages_and_compact_summary_over_real_http(
    tmp_path: Path,
    require_money: bool,
) -> None:
    """Read genuine stored facts through production ports and an isolated IAM server."""
    from dataclasses import replace
    from datetime import UTC, datetime, timedelta

    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
        SqliteCapacityRepositoryV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
        SqliteBillingConnectionRepositoryV1,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
        SqliteCloudCredentialRegistryV1,
        SqliteCredentialBindingsV1,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.repository import (
        SqliteRegistryRepositoryV1,
    )
    from agentmonitor.composition.bootstrap import create_iam_application
    from agentmonitor.composition.budget_analysis import StoredBudgetSourceEvidenceV1
    from agentmonitor.composition.budget_funds import StoredAccountBudgetFundsV1
    from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1
    from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
    from agentmonitor.foundation.application import LifecycleHooksV1
    from agentmonitor.modules.capacity.application.budget_forecast import (
        GetBudgetForecastV1,
    )
    from agentmonitor.modules.capacity.application.budget_history import (
        ListBudgetHistoryV1,
    )
    from agentmonitor.modules.capacity.application.budget_queries import (
        GetAccountBudgetCurrentV1,
    )
    from agentmonitor.modules.capacity.application.budget_selected import (
        GetSelectedBudgetReportV1,
    )
    from agentmonitor.modules.capacity.application.queries import ListQuotaWindowsV1
    from agentmonitor.modules.registry.application.accounts import (
        CapacityScopeMembershipQueryV2,
        GetAccountV1,
    )
    from agentmonitor.modules.registry.domain.credential_binding import (
        resolve_active_credential_binding,
    )

    from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
        _private_real_copy,
    )

    iam_path = tmp_path / "iam"
    iam_path.mkdir(mode=0o700)
    app, credential = _installation(iam_path)
    data_path = tmp_path / "real-readings"
    data_path.mkdir(mode=0o700)
    reference = _private_real_copy(data_path)
    registry = SqliteRegistryRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    bindings = SqliteCredentialBindingsV1(reference)
    now = datetime.now(UTC)
    genuine = []
    for run in runs.list_runs("ollama", None, now, 500):
        if (
            not isinstance(run, BudgetCollectionRunViewV1)
            or run.report_id is None
            or run.account_id is None
        ):
            continue
        report = reports.get_report(run.account_id, run.report_id)
        if (
            report is not None
            and len(report.report.cost_buckets) + len(report.report.usage_buckets) > 1
            and (
                not require_money
                or report.report.cost_buckets
                and report.report.completeness == "complete"
                and report.report.currency is not None
                and not report.report.grouping
            )
        ):
            genuine.append(report)
    assert genuine, (
        "genuine_stored_complete_monetary_report_required"
        if require_money
        else "genuine_stored_report_with_daily_facts_required"
    )
    stored = min(genuine, key=lambda item: (item.stored_at, item.report_id.value))

    def active_binding(account_id: OpaqueIdV1) -> ActiveCredentialBindingRefV1 | None:
        return resolve_active_credential_binding(bindings.read(account_id))

    from agentmonitor.modules.capacity.application.budget_reports import (
        ListBudgetReportsV1,
    )

    selected = GetSelectedBudgetReportV1(GetAccountV1(registry), reports)
    budget_funds = StoredAccountBudgetFundsV1(
        CapacityScopeMembershipQueryV2(registry),
        ListQuotaWindowsV1(SqliteCapacityRepositoryV1(reference)),
        active_binding=active_binding,
        get_run=runs.get_run,
    )
    current = GetAccountBudgetCurrentV1(
        SqliteBillingConnectionRepositoryV1(reference),
        reports,
        runs,
        budget_funds,
        active_binding=active_binding,
        cloud_target=SqliteCloudCredentialRegistryV1(reference).read_monitoring_target,
    )
    # Both sides are actual production services. IAM uses fresh private state;
    # financial readers use an unchanged private backup of genuine stored data.
    app.state.observation_ports = replace(
        app.state.observation_ports,
        get_account_budget_current=current,
        get_selected_budget_report=selected,
        list_budget_history=ListBudgetHistoryV1(selected),
        get_budget_forecast=GetBudgetForecastV1(
            selected,
            StoredBudgetSourceEvidenceV1(reports.get_report_provenance),
            budget_funds,
        ),
        list_budget_reports=ListBudgetReportsV1(GetAccountV1(registry), reports),
    )
    account_id = stored.report.subject.account_id.value
    resource_id = stored.report.subject.resource_id.value
    selection = {
        "account_id": account_id,
        "report_id": stored.report_id.value,
        "period_start": stored.report.requested_period.start.isoformat(),
        "period_end": stored.report.requested_period.end.isoformat(),
        "as_of": now.isoformat(),
    }
    route = f"/api/v1/budgets/{resource_id}/history?"
    query = {**selection, "limit": "1"}

    async def exercise() -> None:
        jars = [http.cookiejar.CookieJar(), http.cookiejar.CookieJar()]
        async with _running(app) as origin:
            for jar in jars:
                login = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
                assert login[0] == 204
            jar = jars[0]
            if require_money:
                # This is an actual retained source report, pinned to when it
                # was stored. It is not a fresh provider observation.
                forecast_selection = {
                    **selection,
                    "as_of": stored.stored_at.isoformat(),
                }
                forecast_url = (
                    f"/api/v1/budgets/{resource_id}/forecast?"
                    + urllib.parse.urlencode(forecast_selection)
                )
                reading = await asyncio.to_thread(
                    _request, origin, "GET", forecast_url, cookies=jar
                )
                assert reading[0] == 200, "genuine_monetary_forecast_endpoint_missing"
                analysis = json.loads(reading[2])
                assert analysis["report"]["report_id"] == stored.report_id.value
                assert "cost_buckets" not in analysis["report"]
                assert "usage_buckets" not in analysis["report"]
                assert analysis["as_of"] == stored.stored_at.isoformat().replace(
                    "+00:00", "Z"
                )
                rate = analysis["rate"]
                assert rate is not None, "genuine_daily_rate_missing"
                cutoff = stored.stored_at.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                sample = [
                    row
                    for row in stored.report.cost_buckets
                    if cutoff - timedelta(days=7) <= row.period.start
                    and row.period.end <= cutoff
                ]
                assert len(sample) >= 3
                assert all(row.kind == "charge" for row in sample)
                assert rate["covered_seconds"] == len(sample) * 86400
                assert rate["day_count"] == len(sample)
                expected = sum(
                    int(row.amount.amount.coefficient)
                    * 10 ** (18 - row.amount.amount.scale)
                    for row in sample
                )
                assert (
                    int(rate["cost"]["coefficient"])
                    * 10 ** (18 - rate["cost"]["scale"])
                    == expected
                )
                assert rate["cost"]["currency"] == stored.report.currency
                assert set(rate["input_bucket_keys"]) == {
                    row.bucket_key for row in sample
                }
                assert rate["input_report_ids"] == [stored.report_id.value]
                assert analysis["exhaustion_at"] is None
                assert analysis["exhaustion_reason"] != "exhaustion_estimated"
                repeated = await asyncio.to_thread(
                    _request, origin, "GET", forecast_url, cookies=jar
                )
                assert repeated[0] == 200 and json.loads(repeated[2]) == analysis
                unauthenticated = await asyncio.to_thread(
                    _request, origin, "GET", forecast_url
                )
                assert unauthenticated[0] == 401
                invalid = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    forecast_url + "&cursor=forbidden",
                    cookies=jar,
                )
                assert invalid[0] == 400
            full = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/budgets/{resource_id}?" + urllib.parse.urlencode(selection),
                cookies=jar,
            )
            assert full[0] == 200
            full_payload = json.loads(full[2])
            report = full_payload["report"]
            if require_money:
                # Independent integer arithmetic over genuine stored facts; no
                # production total/formatting helper supplies the expectation.
                source = stored.report
                assert source.cost_buckets
                assert report["currency"] == source.currency
                assert report["source_id"] == source.source_id
                assert report["source_category"] == source.source_category
                assert report["cost_basis"] == source.cost_basis
                assert report["scope_generation"] == source.scope_generation
                expected_atoms = sum(
                    int(bucket.amount.amount.coefficient)
                    * 10 ** (18 - bucket.amount.amount.scale)
                    for bucket in source.cost_buckets
                )
                total = full_payload["reported_spend"]["total"]
                assert total is not None, "genuine_cost_total_missing"
                assert total["currency"] == source.currency
                assert (
                    int(total["coefficient"]) * 10 ** (18 - total["scale"])
                    == expected_atoms
                ), "genuine_cost_total_inexact"
                assert all(
                    bucket.amount.currency == source.currency
                    for bucket in source.cost_buckets
                )
                by_key = {bucket.bucket_key: bucket for bucket in source.cost_buckets}
                for wire in report["cost_buckets"]:
                    original_cost = by_key[wire["bucket_key"]]
                    assert wire["amount"] == {
                        "coefficient": original_cost.amount.amount.coefficient,
                        "scale": original_cost.amount.amount.scale,
                        "currency": original_cost.amount.currency,
                    }
            expected_metadata = {
                key: value
                for key, value in report.items()
                if key not in {"cost_buckets", "usage_buckets"}
            }
            expected_metadata.update(
                cost_bucket_count=len(report["cost_buckets"]),
                usage_bucket_count=len(report["usage_buckets"]),
            )
            discovery_query = {
                key: value for key, value in selection.items() if key != "report_id"
            }
            discovery_route = f"/api/v1/budgets/{resource_id}/reports?"
            discovered = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                discovery_route
                + urllib.parse.urlencode({**discovery_query, "limit": "1"}),
                cookies=jar,
            )
            assert discovered[0] == 200, "report_discovery_genuine_http_failed"
            discovery_page = json.loads(discovered[2])
            assert discovery_page["account_id"] == account_id
            assert discovery_page["resource_id"] == resource_id
            assert discovery_page["availability"]["state"] == "available"
            assert len(discovery_page["items"]) == 1
            discovered_report = discovery_page["items"][0]
            original = reports.get_report(
                OpaqueIdV1(account_id), OpaqueIdV1(discovered_report["report_id"])
            )
            assert original is not None
            assert (
                discovered_report["scope_generation"]
                == original.report.scope_generation
            )
            assert discovered_report["scope_id"] == (
                original.report.scope_id.value if original.report.scope_id else None
            )
            assert (
                "cost_buckets" not in discovered_report
                and "usage_buckets" not in discovered_report
            )
            assert (
                "binding_id" not in discovered[2].decode()
                and "binding_generation" not in discovered[2].decode()
            )
            cutoff = stored.stored_at - timedelta(microseconds=1)
            earlier = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                discovery_route
                + urllib.parse.urlencode(
                    {**discovery_query, "as_of": cutoff.isoformat()}
                ),
                cookies=jar,
            )
            assert earlier[0] == 200
            assert all(
                datetime.fromisoformat(item["stored_at"].replace("Z", "+00:00"))
                <= cutoff
                for item in json.loads(earlier[2])["items"]
            ), "report_discovery_leaked_future_snapshot"
            next_cursor = discovery_page["page"]["next_cursor"]
            assert next_cursor is not None, "multiple_genuine_revisions_required"
            next_query = {**discovery_query, "limit": "1", "cursor": next_cursor}
            following_report = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                discovery_route + urllib.parse.urlencode(next_query),
                cookies=jar,
            )
            assert following_report[0] == 200
            assert (
                json.loads(following_report[2])["items"][0]["report_id"]
                != discovered_report["report_id"]
            )
            for changes in (
                {"account_id": "other"},
                {"limit": "2"},
                {"as_of": (now + timedelta(seconds=1)).isoformat()},
            ):
                mismatch = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    discovery_route + urllib.parse.urlencode({**next_query, **changes}),
                    cookies=jar,
                )
                assert mismatch[0] == 400
                assert json.loads(mismatch[2])["code"] == "cursor_query_mismatch"
            other_caller = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                discovery_route + urllib.parse.urlencode(next_query),
                cookies=jars[1],
            )
            assert other_caller[0] == 400
            assert json.loads(other_caller[2])["code"] == "cursor_query_mismatch"
            assert report["report_id"] == stored.report_id.value
            assert len(report["cost_buckets"]) == len(stored.report.cost_buckets)
            assert len(report["usage_buckets"]) == len(stored.report.usage_buckets)
            first = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                route + urllib.parse.urlencode(query),
                cookies=jar,
            )
            assert first[0] == 200, "genuine_budget_history_http_failed"
            first_payload = json.loads(first[2])
            page = first_payload
            rows = []
            while True:
                assert page["report"] == expected_metadata
                assert page["reported_spend"] == full_payload["reported_spend"]
                assert page["availability"]["state"] == "available"
                assert len(page["items"]) == 1
                rows.extend(page["items"])
                assert len(rows) <= len(report["cost_buckets"]) + len(
                    report["usage_buckets"]
                )
                if not page["page"]["has_more"]:
                    break
                following = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    route
                    + urllib.parse.urlencode(
                        {**query, "cursor": page["page"]["next_cursor"]}
                    ),
                    cookies=jar,
                )
                assert following[0] == 200
                page = json.loads(following[2])
            expected_rows = [
                {"kind": "cost", "cost": row, "usage": None}
                for row in report["cost_buckets"]
            ] + [
                {"kind": "usage", "cost": None, "usage": row}
                for row in report["usage_buckets"]
            ]

            def row_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
                value = row["cost"] or row["usage"]
                return (
                    value["period"]["start"],
                    value["period"]["end"],
                    row["kind"],
                    value["bucket_key"],
                )

            assert [
                {key: row[key] for key in ("kind", "cost", "usage")} for row in rows
            ] == sorted(expected_rows, key=row_key)
            for row in rows:
                chart = row["chart"]
                assert chart is not None, "genuine_daily_chart_point_missing"
                assert row["chart_unavailable_reason"] is None
                assert len(chart["series_key"]) == 64
                assert 0 <= chart["magnitude_basis_points"] <= 10000
                bucket = row["cost"] or row["usage"]
                exact = bucket["amount"] if row["cost"] else bucket["quantity"]
                coefficient = int(exact["coefficient"])
                assert chart["direction"] == (
                    "zero"
                    if coefficient == 0
                    else "negative"
                    if coefficient < 0
                    else "positive"
                )
                assert (chart["magnitude_basis_points"] == 0) == (coefficient == 0)
            assert (
                "binding_id" not in first[2].decode()
                and "binding_generation" not in first[2].decode()
            )
            cursor = first_payload["page"]["next_cursor"]
            assert isinstance(cursor, str)
            continuation = route + urllib.parse.urlencode({**query, "cursor": cursor})
            other_caller = await asyncio.to_thread(
                _request, origin, "GET", continuation, cookies=jars[1]
            )
            assert other_caller[0] == 400
            assert json.loads(other_caller[2])["code"] == "cursor_query_mismatch"
            for changes in (
                {"report_id": "other"},
                {"account_id": "other"},
                {"limit": "2"},
                {"as_of": (now + timedelta(seconds=1)).isoformat()},
            ):
                mismatch = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    route
                    + urllib.parse.urlencode({**query, "cursor": cursor, **changes}),
                    cookies=jar,
                )
                assert mismatch[0] == 400
                assert json.loads(mismatch[2])["code"] == "cursor_query_mismatch"
            wrong_resource = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/budgets/other/history?"
                + urllib.parse.urlencode({**query, "cursor": cursor}),
                cookies=jar,
            )
            assert wrong_resource[0] == 400
            assert json.loads(wrong_resource[2])["code"] == "cursor_query_mismatch"
            for changes in (
                {"report_id": "not-retained"},
                {"account_id": "not-enrolled"},
            ):
                missing = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    route + urllib.parse.urlencode({**query, **changes}),
                    cookies=jar,
                )
                assert missing[0] == 404
                assert json.loads(missing[2])["code"] == "budget_report_not_found"

            account_query = urllib.parse.urlencode(
                {
                    key: value
                    for key, value in selection.items()
                    if key not in {"account_id", "report_id"}
                }
            )
            old = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{account_id}/api-capacity?" + account_query,
                cookies=jar,
            )
            summary = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{account_id}/budgets?" + account_query,
                cookies=jar,
            )
            assert old[0] == summary[0] == 200
            old_data, compact = json.loads(old[2]), json.loads(summary[2])
            for key in ("account_id", "period", "as_of", "availability", "funds"):
                assert compact[key] == old_data[key]
            actual_reports = 0
            for kind in ("resources", "cloud_resources"):
                assert len(compact[kind]) == len(old_data[kind])
                for original, shortened in zip(
                    old_data[kind], compact[kind], strict=True
                ):
                    assert {
                        key: value
                        for key, value in original.items()
                        if key != "reports"
                    } == {
                        key: value
                        for key, value in shortened.items()
                        if key != "reports"
                    }
                    for old_selection, compact_selection in zip(
                        original["reports"], shortened["reports"], strict=True
                    ):
                        for name in ("current", "latest_attempt"):
                            source, small = old_selection[name], compact_selection[name]
                            if source is None:
                                assert small is None
                            else:
                                actual_reports += 1
                                assert small == {
                                    **{
                                        key: value
                                        for key, value in source.items()
                                        if key not in {"cost_buckets", "usage_buckets"}
                                    },
                                    "cost_bucket_count": len(source["cost_buckets"]),
                                    "usage_bucket_count": len(source["usage_buckets"]),
                                }
            assert actual_reports > 0
            assert len(summary[2]) < len(old[2])
        # A real service restart changes its signing key; no fake clock or signer.
        restarted = create_iam_application(
            iam_path / "isolated.env", iam_path, lifecycle=LifecycleHooksV1()
        )
        restarted.state.observation_ports = app.state.observation_ports
        async with _running(restarted) as origin:
            invalidated = await asyncio.to_thread(
                _request, origin, "GET", continuation, cookies=jars[0]
            )
            assert invalidated[0] == 400
            assert json.loads(invalidated[2])["code"] == "invalid_cursor"

    asyncio.run(exercise())
