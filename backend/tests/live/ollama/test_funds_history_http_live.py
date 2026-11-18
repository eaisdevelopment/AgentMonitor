"""Pinned balance history from genuine retained observations over real HTTP/IAM."""

from __future__ import annotations

import asyncio
import http.cookiejar
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import CapacityHistoryQueryV1, QuotaWindowViewV2
from agentmonitor.modules.capacity.application.queries import (
    ListCapacityHistoryV1,
    ListQuotaWindowsV1,
)

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
)
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def test_real_funds_history_pins_cutoff_component_and_cursor(tmp_path: Path) -> None:
    """No seeded values: select a real balance series and preserve its exact points."""
    iam_root = tmp_path / "iam"
    iam_root.mkdir(mode=0o700)
    app, credential = _installation(iam_root)
    data_root = tmp_path / "retained"
    data_root.mkdir(mode=0o700)
    reference = _private_real_copy(data_root)
    capacity = SqliteCapacityRepositoryV1(reference)
    history = ListCapacityHistoryV1(capacity)
    now = datetime.now(UTC)
    selected = None
    for account in SqliteRegistryRepositoryV1(reference).list_accounts(
        provider_key="ollama", page_size=100
    ):
        for window in ListQuotaWindowsV1(capacity)(account.account_id, as_of=now):
            if not isinstance(window, QuotaWindowViewV2) or window.window_key not in {
                "ollama_included_credits",
                "ollama_purchased_credits",
            }:
                continue
            query = CapacityHistoryQueryV1(
                account.account_id,
                window.subject.resource_id,
                window.window_id,
                "remaining",
                "poll_snapshot",
                now - timedelta(days=30),
                now,
                now,
                200,
                None,
                None,
                None,
            )
            points = history(query).items
            if len(points) >= 3 and any(
                point.value.value is not None for point in points
            ):
                selected = (window, query, points)
                break
        if selected is not None:
            break
    assert selected is not None, "genuine_retained_fund_series_required"
    window, query, points = selected
    # Choose an actual storage cutoff; later stored facts must stay excluded.
    cutoff = points[len(points) // 2].stored_at
    query = replace(query, as_of=cutoff)
    expected = history(query).items
    assert len(expected) > 1, "genuine_fund_history_continuation_required"
    app.state.observation_ports = replace(
        app.state.observation_ports, list_capacity_history=history
    )
    selection = {
        "subject_id": query.subject_id.value,
        "resource_id": query.resource_id.value if query.resource_id else "",
        "window_id": window.window_id.value,
        "metric": "remaining",
        "series_kind": "poll_snapshot",
        "from": query.range_start.isoformat(),
        "before": query.range_before.isoformat(),
        "as_of": cutoff.isoformat(),
        "limit": "1",
    }

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
            route = "/api/v1/capacity/history/v2?"
            first = await asyncio.to_thread(
                _request, origin, "GET", route + urlencode(selection), cookies=jar
            )
            assert first[0] == 200
            payload = json.loads(first[2])
            assert (
                datetime.fromisoformat(
                    payload["availability"]["as_of"].replace("Z", "+00:00")
                )
                == cutoff
            )
            cursor = payload["page"]["next_cursor"]
            assert cursor is not None
            for changes in (
                {"as_of": now.isoformat()},
                {"as_of": ""},
                {"window_id": "absent"},
                {"resource_id": "absent"},
            ):
                mismatched = await asyncio.to_thread(
                    _request,
                    origin,
                    "GET",
                    route + urlencode(selection | changes | {"cursor": cursor}),
                    cookies=jar,
                )
                assert mismatched[0] in {400, 422}, "history_cursor_crossed_selection"
            second = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                route + urlencode(selection | {"cursor": cursor}),
                cookies=jar,
            )
            assert second[0] == 200
            second_payload = json.loads(second[2])
            for actual, fact in zip(
                payload["items"] + second_payload["items"], expected[:2], strict=True
            ):
                assert actual["observation_id"] == fact.observation_id.value
                assert actual["window_id"] == window.window_id.value
                assert actual["subject"]["resource_id"] == selection["resource_id"]
                assert actual["window_key"] == window.window_key
                assert actual["provenance"]["source_id"] == "ollama.cloud.balance.v1"
                assert (
                    datetime.fromisoformat(actual["stored_at"].replace("Z", "+00:00"))
                    <= cutoff
                )
                if fact.value.value is None:
                    assert actual["value"]["value"] is None
                else:
                    quantity = fact.value.value
                    assert actual["value"]["value"] == {
                        "coefficient": quantity.amount.coefficient,
                        "scale": quantity.amount.scale,
                        "unit": quantity.unit,
                    }
            before_first = min(point.stored_at for point in points) - timedelta(
                microseconds=1
            )
            empty = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                route + urlencode(selection | {"as_of": before_first.isoformat()}),
                cookies=jar,
            )
            assert empty[0] == 200 and json.loads(empty[2])["items"] == []

    asyncio.run(exercise())
