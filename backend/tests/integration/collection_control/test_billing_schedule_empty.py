"""Real empty registry scheduling, without constructed provider authority."""

import time
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)


def test_empty_registry_does_not_create_scheduled_runs_or_service_target(
    tmp_path: Path,
) -> None:
    from agentmonitor.composition.billing_schedule import BillingScheduleV1

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    assert (
        BillingScheduleV1(reference).enqueue_due(
            deadline_monotonic=time.monotonic() + 30
        )
        is None
    )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for table in (
                "reg_account",
                "reg_provider_access_target",
                "collection_run",
                "collection_schedule",
                "collection_budget_reservation",
            ):
                assert (
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                    == 0
                )


def test_actual_pending_inventory_is_not_enabled_by_scheduler(tmp_path: Path) -> None:
    import asyncio
    import http.cookiejar
    import json
    import secrets

    from agentmonitor.composition.billing_collection import BillingCollectionV1
    from agentmonitor.composition.billing_schedule import BillingScheduleV1

    from backend.tests.integration.api.test_iam_http import (
        _installation,
        _request,
        _running,
        _session_cookies,
    )

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
            headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body={
                    "provider_key": "claude",
                    "friendly_name": "Unconnected billing " + secrets.token_urlsafe(8),
                    "organization_id": None,
                    "initial_connection_purpose": "api",
                },
                headers=headers,
                cookies=jar,
            )
            assert created[0] == 201
            account_id = json.loads(created[2])["account_id"]
            connection = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                f"/api/v1/accounts/{account_id}/billing-connections",
                body={"scope_id": None},
                headers={
                    **headers,
                    "Idempotency-Key": secrets.token_urlsafe(24),
                    "If-Match": created[1]["ETag"],
                },
                cookies=jar,
            )
            assert connection[0] == 201
            reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
            assert (
                BillingScheduleV1(reference).enqueue_due(
                    deadline_monotonic=time.monotonic() + 30
                )
                is None
            )
            # Actual no-work worker traverses recovery, claim, inventory and exits.
            # The isolated application's real empty configuration contains no key.
            assert (
                BillingCollectionV1(
                    tmp_path,
                    credential_env_file=tmp_path / "isolated.env",
                    deadline_monotonic=time.monotonic() + 30,
                ).run()
                == 0
            )
            status = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                f"/api/v1/accounts/{account_id}/billing-connections",
                cookies=jar,
            )
            assert status[0] == 200
            assert (
                json.loads(status[2])["connections"][0]["monitoring_preference"]
                == "disabled"
            )
            with open_sqlite_database(reference, "runtime_read_only") as handle:
                with handle.connect() as database:
                    for table in (
                        "collection_budget_run",
                        "reg_provider_access_target",
                    ):
                        assert (
                            database.exec_driver_sql(
                                f"SELECT count(*) FROM {table}"
                            ).scalar_one()
                            == 0
                        )

    asyncio.run(exercise())
