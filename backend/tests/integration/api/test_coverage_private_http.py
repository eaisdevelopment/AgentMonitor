"""M6-COV-HTTP-01: real HTTP over a migrated private copy and real owner session."""

import asyncio
from dataclasses import replace
from pathlib import Path

from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.foundation.application import LifecycleHooksV1

from backend.tests.integration.api.test_iam_http import _running
from backend.tests.integration.registry.test_coverage_persistence import (
    ActualCoverageRegistry,
)

pytest_plugins = ("backend.tests.integration.registry.test_coverage_persistence",)


def test_private_real_coverage_http_and_editor(
    actual_registry: ActualCoverageRegistry, tmp_path: Path
) -> None:
    """Reuse real IAM cookie in browser; no login/credential extraction or seeding."""
    reference, _registry, _account, _graph = actual_registry
    root = tmp_path
    config = root / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, root, lifecycle=LifecycleHooksV1())
    # This HTTP-only composition has actual repositories/IAM/transport. Omit
    # background collection tasks so testing registry CRUD cannot contact providers.
    # No replacement task, fake port or production-only branch is introduced.
    runtime = app.state.lifecycle
    runtime.hooks = replace(runtime.hooks, tasks=())

    async def exercise() -> None:
        async with _running(app) as origin:
            process = await asyncio.create_subprocess_exec(
                "node",
                "frontend/tests/browser/m6/coverage_private_http.mjs",
                origin,
                cwd=Path(__file__).resolve().parents[4],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            output, _ = await asyncio.wait_for(process.communicate(), timeout=90)
            # Browser emits only closed test names/status codes, never identifiers,
            # cookies, returned registry objects or submitted request payloads.
            assert process.returncode == 0, output.decode("ascii", errors="replace")

    asyncio.run(exercise())
