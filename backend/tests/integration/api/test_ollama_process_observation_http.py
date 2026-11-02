"""Current and persisted real Ollama process facts cross authenticated HTTP."""

import asyncio
import http.cookiejar
import json
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)


def test_real_ollama_processes_reach_authenticated_runtime_views(
    tmp_path: Path,
) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.composition.linux_runtime_monitoring import (
        run_ollama_runtime_collection,
    )
    from agentmonitor.composition.ollama_installation_reconciliation import (
        reconcile_ollama_installation_v1,
    )

    app, credential = _installation(tmp_path)
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    reconciliation = reconcile_ollama_installation_v1(reference)
    run_ollama_runtime_collection(tmp_path)

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

            persisted = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/processes?provider_key=ollama",
                cookies=jar,
            )
            assert persisted[0] == 200
            persisted_payload = json.loads(persisted[2])
            assert persisted_payload["availability"]["state"] == "available"
            assert persisted_payload["items"]
            assert all(
                item["provider_key"] == "ollama"
                and item["installation_id"]
                == reconciliation.provider_installation_id.value
                and item["provenance"]["source_id"] == "linux.proc.process.v1"
                for item in persisted_payload["items"]
            )

            current = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/process-locations",
                cookies=jar,
            )
            assert current[0] == 200
            current_payload = json.loads(current[2])
            ollama = [
                item
                for item in current_payload["items"]
                if item["provider_key"] == "ollama"
            ]
            assert ollama
            assert all(
                item["account_correlation"] == "unresolved"
                and item["account_association"] is None
                for item in ollama
            )

    asyncio.run(exercise())
