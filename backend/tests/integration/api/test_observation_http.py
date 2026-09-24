"""M3 observation resources over real loopback HTTP and file SQLite."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
import secrets
from pathlib import Path

import pytest

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)

OPERATION_MATRIX = {
    ("/api/v1/accounts", "get"): (
        "registry_list_accounts_v1",
        "read:accounts",
        "ListAccountsV1",
        "AccountPageV1",
    ),
    ("/api/v1/provider-installations", "get"): (
        "registry_list_provider_installations_v1",
        "read:accounts",
        "ListProviderInstallationsV1",
        "ProviderInstallationPageV1",
    ),
    ("/api/v1/providers/{provider_key}/capabilities", "get"): (
        "provider_get_capabilities_v1",
        "read:status",
        "GetProviderCapabilitiesV1",
        "ProviderCapabilityDeclarationPageV1",
    ),
    ("/api/v1/collection-runs", "get"): (
        "collection_list_runs_v1",
        "read:telemetry",
        "ListCollectionRunsV1",
        "CollectionRunPageV1",
    ),
    ("/api/v1/accounts/{account_id}/capacity", "get"): (
        "capacity_get_account_v1",
        "read:telemetry",
        "GetAccountCapacityV1",
        "AccountCapacityViewV1",
    ),
    ("/api/v1/accounts/{account_id}/quotas", "get"): (
        "capacity_list_quota_windows_v1",
        "read:telemetry",
        "ListQuotaWindowsV1",
        "QuotaWindowPageV1",
    ),
    ("/api/v1/capacity/history", "get"): (
        "capacity_list_history_v1",
        "read:telemetry",
        "ListCapacityHistoryV1",
        "CapacityHistoryPageV1",
    ),
    ("/api/v1/processes", "get"): (
        "runtime_list_processes_v1",
        "read:telemetry",
        "ListAgentProcessesV1",
        "AgentProcessPageV1",
    ),
    ("/api/v1/process-metrics", "get"): (
        "runtime_list_process_metrics_v1",
        "read:telemetry",
        "ListAgentProcessesV1",
        "AgentProcessMetricPageV1",
    ),
    ("/api/v1/sessions", "get"): (
        "runtime_list_sessions_v1",
        "read:telemetry",
        "ListAgentSessionsV1",
        "AgentSessionPageV1",
    ),
    ("/api/v1/sessions/{session_id}/tree", "get"): (
        "runtime_get_session_tree_v1",
        "read:telemetry",
        "GetSessionTreeV1",
        "SessionTreeViewV1",
    ),
    ("/api/v1/sessions/{session_id}", "get"): (
        "runtime_get_session_v1",
        "read:telemetry",
        "GetAgentSessionV1",
        "AgentSessionViewV1",
    ),
}


def _runtime_path(template: str) -> str:
    path = (
        template.replace("{provider_key}", "claude")
        .replace("{account_id}", "not-enrolled")
        .replace("{session_id}", "not-observed")
    )
    if path == "/api/v1/capacity/history":
        return (
            path
            + "?subject_id=not-enrolled&metric=remaining_ratio"
            + "&series_kind=poll_snapshot&from=2026-01-01T00:00:00Z"
            + "&before=2026-01-02T00:00:00Z"
        )
    return path


RUNTIME_PATHS = tuple(_runtime_path(path) for path, _method in OPERATION_MATRIX)


def test_observation_openapi_publishes_exact_approved_m3_policy() -> None:
    from agentmonitor.composition.bootstrap import create_iam_schema_application

    schema = create_iam_schema_application().openapi()
    assert "dashboard_get_overview_v1" not in {
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
    }
    for key, (identifier, permission, port, response_model) in OPERATION_MATRIX.items():
        path, method = key
        operation = schema["paths"][path][method]
        assert operation["operationId"] == identifier
        assert operation["x-agentmonitor-auth-profile"] == "cookie_or_bearer"
        assert operation["x-agentmonitor-required-permission"] == permission
        assert operation["x-agentmonitor-application-port"] == port
        assert operation["x-agentmonitor-replay-policy"] == "safe_query_repeat"
        assert operation["x-agentmonitor-error-schema"] == "SafeProblemV1"
        assert operation["security"] == [
            {"BrowserSessionCookieV1": []},
            {"BearerTokenV1": []},
        ]
        assert operation["responses"]["200"]["content"]["application/json"][
            "schema"
        ] == {"$ref": f"#/components/schemas/{response_model}"}

    provider_parameter = schema["paths"][
        "/api/v1/providers/{provider_key}/capabilities"
    ]["get"]["parameters"][0]
    assert provider_parameter["name"] == "provider_key"
    assert provider_parameter["in"] == "path"
    assert provider_parameter["schema"]["maxLength"] == 64
    assert provider_parameter["schema"]["pattern"] == "^[a-z][a-z0-9_-]{0,63}$"
    session_parameters = {
        parameter["name"]: parameter
        for parameter in schema["paths"]["/api/v1/sessions"]["get"]["parameters"]
    }
    assert session_parameters["account_id"]["in"] == "query"
    account_selector_schema = next(
        item
        for item in session_parameters["account_id"]["schema"]["anyOf"]
        if item.get("type") == "string"
    )
    assert account_selector_schema["maxLength"] == 256
    process_metrics = {
        "parent_pid",
        "user_cpu_ticks",
        "system_cpu_ticks",
        "resident_pages",
        "thread_count",
        "kernel_state",
        "clock_ticks_per_second",
        "page_size_bytes",
    }
    process_schema = schema["components"]["schemas"]["AgentProcessViewV1"]
    assert process_metrics.isdisjoint(process_schema["properties"])
    metric_schema = schema["components"]["schemas"]["AgentProcessMetricViewV1"]
    assert process_metrics <= metric_schema["properties"].keys()
    assert process_metrics <= set(metric_schema["required"])


@pytest.mark.parametrize("path", RUNTIME_PATHS)
def test_each_observation_resource_authenticates_before_lookup(
    tmp_path: Path, path: str
) -> None:
    app, _credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            denied = await asyncio.to_thread(_request, origin, "GET", path)
            assert denied[0] == 401
            assert json.loads(denied[2])["code"] == "dashboard_authentication_required"
            assert denied[1]["X-Correlation-ID"]
            assert denied[1]["X-Content-Type-Options"] == "nosniff"

    asyncio.run(exercise())


def test_observation_resources_preserve_fresh_database_truth(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
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
            expected_empty = {
                "/api/v1/accounts": "available",
                "/api/v1/provider-installations": "available",
                "/api/v1/collection-runs": "available",
                "/api/v1/processes": "available",
                "/api/v1/process-metrics": "available",
                "/api/v1/sessions": "available",
                "/api/v1/accounts/not-enrolled/capacity": "unavailable",
                "/api/v1/accounts/not-enrolled/quotas": "unavailable",
            }
            for path, availability in expected_empty.items():
                response = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert response[0] == 200, (path, response[2])
                payload = json.loads(response[2])
                assert payload["availability"]["state"] == availability
                assert payload.get("items", ()) == []

    asyncio.run(exercise())


def test_real_process_metrics_reach_authenticated_http_without_losing_semantics(
    tmp_path: Path,
) -> None:
    """FR-DISC-002/API-HTTP: current real procfs facts survive T2 and T3."""
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.adapters.persistence.runtime_observation.sqlite import (
        repository as runtime_repository,
    )
    from agentmonitor.modules.runtime_observation.application.commit import (
        CommitRuntimeCollectionOutcomeV1,
    )

    from backend.tests.runtime_observation.integration.test_real_linux_commit import (
        _request as real_runtime_request,
    )

    app, credential = _installation(tmp_path)
    runtime_request = real_runtime_request("api-real-runtime-metrics")
    CommitRuntimeCollectionOutcomeV1(
        runtime_repository.SqliteRuntimeObservationRepositoryV1(
            DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
        )
    )(runtime_request)
    snapshots = {
        (item.identity.pid, item.identity.start_time_ticks): item
        for item in runtime_request.payload.process_snapshots
    }

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            response = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/process-metrics?limit=200",
                cookies=jar,
            )
            assert response[0] == 200, response[2]
            payload = json.loads(response[2])
            assert payload["items"]
            for item in payload["items"]:
                snapshot = snapshots[
                    (item["identity"]["pid"], item["identity"]["start_time_ticks"])
                ]
                for field in (
                    "parent_pid",
                    "user_cpu_ticks",
                    "system_cpu_ticks",
                    "resident_pages",
                    "thread_count",
                ):
                    expected = getattr(snapshot, field)
                    assert item[field] == {
                        "state": expected.state,
                        "value": expected.value,
                        "unit": expected.unit,
                        "reason_code": expected.reason_code,
                    }
                assert item["kernel_state"] == {
                    "state": snapshot.kernel_state.state,
                    "value": snapshot.kernel_state.value,
                    "reason_code": snapshot.kernel_state.reason_code,
                }
                assert item["clock_ticks_per_second"] == snapshot.clock_ticks_per_second
                assert item["page_size_bytes"] == snapshot.page_size_bytes
                expected_observed_at = snapshot.observed_at.isoformat().replace(
                    "+00:00", "Z"
                )
                assert item["last_observed_at"] == expected_observed_at

    asyncio.run(exercise())


def test_capabilities_come_from_registered_m03_manifest(tmp_path: Path) -> None:
    from agentmonitor.adapters.providers.claude.manifest import build_claude_manifest

    app, credential = _installation(tmp_path)
    manifest = build_claude_manifest()

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            response = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/providers/claude/capabilities",
                cookies=jar,
            )
            assert response[0] == 200
            payload = json.loads(response[2])
            assert payload["provider_key"] == manifest.descriptor.provider_key
            assert payload["adapter_version"] == manifest.descriptor.adapter_version
            assert [item["capability_id"] for item in payload["items"]] == [
                item.capability_id for item in manifest.declarations
            ]
            assert [item["support_state"] for item in payload["items"]] == [
                item.decision for item in manifest.declarations
            ]
            missing = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/providers/not-registered/capabilities",
                cookies=jar,
            )
            assert missing[0] == 404
            assert json.loads(missing[2])["code"] == ("provider_capabilities_not_found")

    asyncio.run(exercise())


def test_provider_capability_selector_is_bounded_and_closed(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            cases = (
                ("A" * 65, 422),
                ("%C3%A9", 422),
                ("claude%3Aother", 422),
                ("claude%2Fother", 404),
                ("", 404),
            )
            for selector, expected_status in cases:
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    f"/api/v1/providers/{selector}/capabilities",
                    cookies=jar,
                )
                assert response[0] == expected_status, (selector, response[2])
                assert response[0] != 500

    asyncio.run(exercise())


def test_sessions_accept_account_scope_without_inventing_matches(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            response = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/sessions?account_id=not-enrolled",
                cookies=jar,
            )
            assert response[0] == 200, response[2]
            payload = json.loads(response[2])
            assert payload["items"] == []
            assert payload["availability"]["state"] == "available"

    asyncio.run(exercise())


def test_observation_permissions_and_bounded_lists(tmp_path: Path) -> None:
    app, credential = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            csrf = _session_cookies(jar)["agentmonitor_csrf"]

            async def issue(scope: str) -> str:
                response = await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/api-tokens",
                    body={"name": scope, "scopes": [scope]},
                    headers={
                        "Origin": origin,
                        "X-CSRF-Token": csrf,
                        "Idempotency-Key": secrets.token_urlsafe(18),
                    },
                    cookies=jar,
                )
                assert response[0] == 201
                return str(json.loads(response[2])["bearer_credential"])

            tokens = {
                scope: await issue(scope)
                for scope in (
                    "read:accounts",
                    "read:status",
                    "read:telemetry",
                    "read:diagnostics",
                )
            }
            for (template, _method), (
                _identifier,
                permission,
                _port,
                _model,
            ) in OPERATION_MATRIX.items():
                path = _runtime_path(template)
                denied = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    path,
                    headers={"Authorization": "Bearer " + tokens["read:diagnostics"]},
                )
                assert denied[0] == 403, path
                allowed = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    path,
                    headers={"Authorization": "Bearer " + tokens[permission]},
                )
                assert allowed[0] in {200, 404}, (path, allowed[2])

            for path in (
                "/api/v1/accounts",
                "/api/v1/collection-runs",
                "/api/v1/process-metrics",
                "/api/v1/processes",
                "/api/v1/sessions",
            ):
                for limit in (0, 201, 501):
                    response = await asyncio.to_thread(
                        _request, origin, "GET", f"{path}?limit={limit}", cookies=jar
                    )
                    assert response[0] == 422, (path, limit)

            for path in (
                "/api/v1/accounts",
                "/api/v1/collection-runs",
                "/api/v1/process-metrics",
                "/api/v1/processes",
                "/api/v1/sessions",
            ):
                response = await asyncio.to_thread(
                    _request, origin, "GET", f"{path}?bogus=1", cookies=jar
                )
                assert response[0] == 400, path
                assert json.loads(response[2])["code"] == "invalid_filter"

            for path in (
                "/api/v1/accounts/%20/capacity",
                "/api/v1/accounts/%20/quotas",
                "/api/v1/sessions/%20",
            ):
                response = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                assert response[0] == 400, path
                assert json.loads(response[2])["code"] == "invalid_filter"

    asyncio.run(exercise())
