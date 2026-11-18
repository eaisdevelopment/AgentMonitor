"""Real metadata commits during built Overview reads of a genuine private copy."""

import asyncio
import re
import sys
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import CodeType

import pytest
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.capacity.application.budget_overview import (
    ListBudgetOverviewV1,
)
from agentmonitor.modules.registry.application.accounts import EditAccountCommandV1

from backend.tests.integration.api.test_iam_http import _running
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


@pytest.mark.parametrize("changes", [1, 2])
def test_genuine_registry_race_has_one_bounded_browser_retry(
    tmp_path: Path, changes: int
) -> None:
    reference = _private_real_copy(tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    account = next(
        item
        for item in registry.list_accounts(page_size=200)
        if item.lifecycle != "archived"
    )
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
    app.state.lifecycle.hooks = replace(app.state.lifecycle.hooks, tasks=())
    committed = 0
    failed = False

    def after_inventory(code: CodeType, offset: int, result: object) -> None:
        nonlocal account, committed, failed
        if committed >= changes:
            return
        committed += 1
        # Monitoring observes the real read, then executes a real M02 command.
        # No callable/response is replaced. Only this disposable database changes;
        # only name casing changes; group, profiles and credentials stay intact.
        try:
            previous = account
            account = registry.edit_account(
                EditAccountCommandV1(
                    account_id=account.account_id,
                    expected_version=account.record_version,
                    principal_id=OpaqueIdV1("isolated-registry-race-verifier"),
                    command_id=OpaqueIdV1(uuid.uuid4().hex),
                    action="rename",
                    requested_at=datetime.now(UTC),
                    friendly_name=account.friendly_name.swapcase(),
                )
            )
            if account.record_version != previous.record_version + 1:
                failed = True
        except Exception:
            failed = True

    async def exercise() -> None:
        async with _running(app) as origin:
            process = await asyncio.create_subprocess_exec(
                "node",
                "frontend/tests/browser/m7/overview_registry_race.mjs",
                origin,
                str(changes),
                cwd=Path(__file__).resolve().parents[4],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                output, _ = await asyncio.wait_for(process.communicate(), timeout=45)
            finally:
                if process.returncode is None:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=10)
            assert not failed and committed == changes, (
                "real_metadata_change_not_observed"
            )
            expected = (
                f"M7 REGISTRY RACE BROWSER: PASSED changes={changes} reads=2\n".encode()
            )
            if process.returncode != 0 or output != expected:
                failure = re.fullmatch(
                    rb"M7 REGISTRY RACE BROWSER: FAILED ([a-z_]+)\n", output
                )
                pytest.fail(
                    "registry_race_browser_"
                    + (failure.group(1).decode() if failure else "protocol"),
                    pytrace=False,
                )

    monitor = sys.monitoring
    identity = 4
    code = ListBudgetOverviewV1._inventory.__code__
    monitor.use_tool_id(identity, "m7-isolated-registry-race")
    try:
        monitor.register_callback(identity, monitor.events.PY_RETURN, after_inventory)
        monitor.set_local_events(identity, code, monitor.events.PY_RETURN)
        asyncio.run(exercise())
    finally:
        monitor.set_local_events(identity, code, 0)
        monitor.free_tool_id(identity)
