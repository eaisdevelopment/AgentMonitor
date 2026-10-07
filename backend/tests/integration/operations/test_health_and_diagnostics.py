"""M4-OPS-DB: real migrated SQLite and production M08 composition.

This suite uses the production startup and leaf readers. No health result is
constructed or substituted by the test.
"""

import asyncio
import http.cookiejar
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.adapters.providers.codex.adapter import CodexAdapterV1
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import (
    COMPONENT_KEYS_V1,
    OperationsQueryRequestV1,
)
from agentmonitor.modules.operations.application.service import OperationsServiceV1

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_real_operational_leaves_keep_optional_gaps_visible(tmp_path: Path) -> None:
    app, _credential = _installation(tmp_path)
    service = app.state.operations_ports
    assert isinstance(service, OperationsServiceV1)

    async def exercise() -> None:
        async with _running(app):
            now = datetime.now(UTC)
            correlation = OpaqueIdV1("m4-operations-real-sqlite")
            request = OperationsQueryRequestV1(
                now, now + timedelta(seconds=2), correlation, "administrator"
            )
            liveness = service.get_liveness(now, correlation)
            health = await service.get_health(request)
            readiness = await service.get_readiness(request)
            diagnostics = await service.get_diagnostic_summary(request)

            assert liveness.state == "healthy"
            assert liveness.correlation_id == correlation
            components = {item.component_key: item for item in health.components}
            assert set(components) == COMPONENT_KEYS_V1
            for key in (
                "foundation",
                "configuration",
                "database",
                "identity_access",
                "registry",
                "provider.codex",
            ):
                assert components[key].outcome == "available"
                sample = components[key].sample
                assert sample is not None
                assert sample.state == "healthy"
                if key == "provider.codex":
                    assert sample.component_version == "0.160.0"
            # Absent optional producer leaves are reported, never counted as
            # healthy zeroes or silently omitted from the manifest.
            for key in (
                "provider_system",
                "capacity",
                "runtime_observation",
                "alerting",
                "provider.claude",
            ):
                assert components[key].outcome == "unavailable"
                assert components[key].sample is None
            assert health.state == "degraded"
            assert readiness.state == "ready"
            assert readiness.blocker_component_keys == ()
            assert diagnostics.health.correlation_id == correlation
            assert diagnostics.readiness.correlation_id == correlation
            assert diagnostics.versions.schema_version.source == "schema_port"
            assert diagnostics.versions.schema_version.value is not None
            with sqlite3.connect(
                (tmp_path / "agentmonitor.db").as_uri() + "?mode=ro", uri=True
            ) as connection:
                actual_revision = connection.execute(
                    "SELECT version_num FROM alembic_version"
                ).fetchone()
            assert actual_revision is not None
            assert diagnostics.versions.schema_version.value == actual_revision[0]
            assert diagnostics.versions.application_version.value is not None
            assert diagnostics.configuration_presence == ()

    asyncio.run(exercise())


def test_real_codex_source_failure_isolated_from_healthy_service(
    tmp_path: Path,
) -> None:
    """M5-CDX-OPS-001: one real failed source leaves HTTP and Codex health live."""

    app, credential = _installation(tmp_path)
    profiles_root = tmp_path / "profiles" / "codex"
    managed_root = profiles_root / ("failure-isolation-" + uuid.uuid4().hex)
    profiles_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    profiles_root.chmod(0o700)
    managed_root.mkdir(mode=0o700)
    root_mtime_before = managed_root.stat().st_mtime_ns
    installation = discover_default_installation()
    suffix = uuid.uuid4().hex
    adapter = CodexAdapterV1(
        installation,
        managed_profiles_root=profiles_root,
        managed_profile_root=managed_root,
        identity_matches=lambda _identity: False,
        installation_ref=installation.installation_ref,
        account_ref=OpaqueIdV1("failure-account-" + suffix),
        profile_ref=OpaqueIdV1("failure-profile-" + suffix),
        resource_ref=OpaqueIdV1("failure-resource-" + suffix),
        access_grant_ref=OpaqueIdV1("codex-managed-profile-auth-maintenance"),
    )
    requested_at = datetime.now(UTC)
    request = adapter.subscription_request(
        operation_id="failure-operation-" + suffix,
        correlation_id="failure-correlation-" + suffix,
        requested_at=requested_at,
    )

    async def exercise() -> None:
        async with _running(app) as origin:
            cookies = http.cookiejar.CookieJar()
            login = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
                cookies=cookies,
            )
            assert login[0] == 204
            before = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/operations/health",
                cookies=cookies,
            )
            assert before[0] == 200

            failed = await asyncio.to_thread(
                adapter.collect_subscription_quota, request
            )

            assert failed.state == "reauthentication_required"
            assert failed.value is None and failed.provenance is None
            assert failed.error is not None
            assert failed.error.code == "codex_managed_authentication_required"
            after_health, liveness, capabilities = await asyncio.gather(
                asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/operations/health",
                    cookies=cookies,
                ),
                asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/operations/liveness",
                    cookies=cookies,
                ),
                asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    "/api/v1/providers/codex/capabilities",
                    cookies=cookies,
                ),
            )
            assert after_health[0] == liveness[0] == capabilities[0] == 200
            assert json.loads(liveness[2])["state"] == "healthy"
            health = json.loads(after_health[2])
            codex = next(
                item
                for item in health["components"]
                if item["component_key"] == "provider.codex"
            )
            assert codex["outcome"] == "available"
            assert codex["sample"]["state"] == "healthy"
            assert codex["sample"]["component_version"] == "0.160.0"
            provider = json.loads(capabilities[2])
            assert provider["provider_key"] == "codex"
            assert provider["adapter_version"] == "1.0.1"

    asyncio.run(exercise())
    assert tuple(managed_root.iterdir()) == ()
    assert managed_root.stat().st_mtime_ns == root_mtime_before
