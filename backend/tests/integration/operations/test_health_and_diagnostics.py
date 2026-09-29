"""M4-OPS-DB: real migrated SQLite and production M08 composition.

This suite uses the production startup and leaf readers. No health result is
constructed or substituted by the test.
"""

import asyncio
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import (
    COMPONENT_KEYS_V1,
    OperationsQueryRequestV1,
)
from agentmonitor.modules.operations.application.service import OperationsServiceV1

from backend.tests.integration.api.test_iam_http import _installation, _running


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
            ):
                assert components[key].outcome == "available"
                sample = components[key].sample
                assert sample is not None
                assert sample.state == "healthy"
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
