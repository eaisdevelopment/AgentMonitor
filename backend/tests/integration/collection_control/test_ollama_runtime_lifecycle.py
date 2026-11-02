"""Production lifespan owns optional Ollama process collection safely."""

import asyncio
import http.cookiejar
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)


def test_production_lifespan_reconciles_and_collects_real_ollama(
    tmp_path: Path,
) -> None:
    app, credential = _installation(tmp_path)
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    collection = SqliteCollectionRepositoryV1(reference)

    async def exercise() -> None:
        async with _running(app) as origin:
            deadline = asyncio.get_running_loop().time() + 12
            runs = ()
            installations = ()
            while asyncio.get_running_loop().time() < deadline:
                installations = registry.list_provider_installations("ollama")
                runs = collection.list_runs("ollama", None, datetime.now(UTC), 20)
                if installations and any(
                    run.state in {"succeeded", "partial"} for run in runs
                ):
                    break
                await asyncio.sleep(0.05)

            assert len(installations) == 1
            assert installations[0].presence_state == "present"
            assert any(run.state in {"succeeded", "partial"} for run in runs)
            assert app.state.lifecycle.task_failures == ()

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
            response = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/process-metrics?provider_key=ollama&limit=200",
                cookies=jar,
            )
            assert response[0] == 200
            payload = json.loads(response[2])
            assert payload["items"]
            assert all(item["provider_key"] == "ollama" for item in payload["items"])

    asyncio.run(exercise())


def test_optional_ollama_failure_backs_off_without_hot_looping(
    tmp_path: Path,
) -> None:
    from agentmonitor.composition.ollama_runtime_collection import (
        OllamaRuntimeCollectorV1,
    )

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    collector = OllamaRuntimeCollectorV1(reference, data_root=tmp_path)
    database = tmp_path / "agentmonitor.db"
    unavailable = tmp_path / "agentmonitor.unavailable"
    database.rename(unavailable)

    assert collector.tick() == "ollama_runtime_unavailable"
    assert collector.tick() == "ollama_runtime_backoff"


def test_real_ollama_collector_reuses_registry_and_schedule_between_ticks(
    tmp_path: Path,
) -> None:
    from agentmonitor.composition.ollama_runtime_collection import (
        OllamaRuntimeCollectorV1,
    )

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    collector = OllamaRuntimeCollectorV1(reference, data_root=tmp_path)
    registry = SqliteRegistryRepositoryV1(reference)
    collection = SqliteCollectionRepositoryV1(reference)

    assert collector.tick() in {"ollama_runtime_collected", "ollama_runtime_partial"}
    installations = registry.list_provider_installations("ollama")
    runs = collection.list_runs("ollama", None, datetime.now(UTC), 20)
    assert len(installations) == 1
    assert len(runs) == 1
    assert runs[0].schedule_id.value == "ollama-linux-runtime-scheduled"
    with sqlite3.connect(tmp_path / "agentmonitor.db") as database:
        admission = database.execute(
            "SELECT r.trigger_kind,q.request_auth_method,q.principal_id,"
            "q.idempotency_key_digest FROM collection_run r "
            "JOIN collection_request q ON q.request_id=r.primary_request_id "
            "WHERE r.run_id=?",
            (runs[0].run_id.value,),
        ).fetchone()
    assert admission == ("scheduled", "internal_scheduler", None, None)

    assert collector.tick() == "ollama_runtime_waiting"
    assert registry.list_provider_installations("ollama") == installations
    assert collection.list_runs("ollama", None, datetime.now(UTC), 20) == runs
