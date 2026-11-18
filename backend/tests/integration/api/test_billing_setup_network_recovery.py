"""Actual Chrome transport loss during setup, with an empty real installation."""

import asyncio
from pathlib import Path

from backend.tests.integration.api.test_iam_http import _installation, _running


def test_billing_setup_recovers_after_real_browser_transport_loss(
    tmp_path: Path,
) -> None:
    app, password = _installation(tmp_path)

    async def exercise() -> None:
        async with _running(app) as origin:
            child = await asyncio.create_subprocess_exec(
                "node",
                "frontend/tests/browser/m7/setup_network_recovery.mjs",
                origin,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                output, _ = await asyncio.wait_for(
                    child.communicate(password.encode()), timeout=60
                )
            finally:
                if child.returncode is None:
                    child.terminate()
                    await asyncio.wait_for(child.wait(), timeout=10)
            assert (
                child.returncode == 0
                and output == b"M7 SETUP NETWORK RECOVERY: PASSED\n"
            ), "real_billing_setup_transport_recovery_failed"

    asyncio.run(exercise())
