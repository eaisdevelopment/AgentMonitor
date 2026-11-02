"""Production lifespan owns optional Ollama process collection safely."""

import asyncio
import http.cookiejar
import json
import os
import sqlite3
import stat
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

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

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
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


def test_optional_ollama_failure_backoff_survives_collector_restart(
    tmp_path: Path,
) -> None:
    from agentmonitor.composition.ollama_runtime_collection import (
        OllamaRuntimeCollectorV1,
    )

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    database = tmp_path / "agentmonitor.db"
    unavailable = tmp_path / "agentmonitor.unavailable"
    database.rename(unavailable)

    first = OllamaRuntimeCollectorV1(reference, data_root=tmp_path)
    assert first.tick() == "ollama_runtime_unavailable"
    state_file = tmp_path / ".ollama-runtime-collector-v1.json"
    assert stat.S_IMODE(state_file.stat().st_mode) == 0o600
    unavailable.rename(database)

    restarted = OllamaRuntimeCollectorV1(reference, data_root=tmp_path)
    assert restarted.tick() == "ollama_runtime_backoff"


def test_unexpected_output_failure_does_not_terminate_optional_collector(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    (tmp_path / "agentmonitor.db").rename(tmp_path / "agentmonitor.unavailable")
    source_root = Path(__file__).resolve().parents[3] / "src"
    script = "\n".join(
        (
            "import asyncio",
            "import sys",
            "from pathlib import Path",
            f"sys.path.insert(0, {str(source_root)!r})",
            "from agentmonitor.adapters.persistence._shared.sqlite.core.policy "
            "import DatabaseRefV1",
            "from agentmonitor.composition.ollama_runtime_collection "
            "import OllamaRuntimeCollectorV1",
            f"root = Path({str(tmp_path)!r})",
            "reference = DatabaseRefV1(root / 'agentmonitor.db', root)",
            "asyncio.run(OllamaRuntimeCollectorV1(reference, data_root=root).run())",
        )
    )
    process = subprocess.Popen(  # noqa: S603 - current test interpreter and fixed code
        [sys.executable, "-I", "-c", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=tmp_path,
        env={
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        },
        start_new_session=True,
    )
    assert process.stdout is not None
    process.stdout.close()
    try:
        deadline = time.monotonic() + 1.5
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert process.poll() is None
    finally:
        if process.poll() is None:
            os.killpg(process.pid, 15)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, 9)
                process.wait(timeout=3)


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
