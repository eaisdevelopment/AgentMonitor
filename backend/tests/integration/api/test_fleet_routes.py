"""ST-FLEET-003: real owner service protects fleet telemetry HTTP routes."""

import http.client
import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlsplit

from backend.tests.integration.collection_control.fleet_support import (
    selected_owner_fleet,
)


def test_real_fleet_routes_require_dashboard_authentication() -> None:
    selected = selected_owner_fleet()
    origin = os.environ.get("AGENTMONITOR_TEST_DASHBOARD_ORIGIN")
    assert origin is not None, "m4_explicit_dashboard_origin_required"
    parsed = urlsplit(origin)
    assert (
        parsed.scheme == "http"
        and parsed.hostname == "127.0.0.1"
        and parsed.port is not None
        and not parsed.username
        and not parsed.password
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    ), "m4_loopback_dashboard_origin_required"
    account_id = selected.outcomes[0].account_id
    before = datetime.now(UTC)
    history_query = urlencode(
        {
            "subject_id": account_id,
            "metric": "remaining_ratio",
            "series_kind": "poll_snapshot",
            "from": (before - timedelta(days=1)).isoformat(),
            "before": before.isoformat(),
        }
    )
    for path in (
        "/api/v1/accounts?limit=200",
        f"/api/v1/accounts/{account_id}/capacity",
        "/api/v1/sessions?provider_key=claude&limit=200",
        "/api/v1/capacity/history?" + history_query,
    ):
        connection = http.client.HTTPConnection("127.0.0.1", parsed.port, timeout=5)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            assert response.status == 401, "m4_fleet_route_authentication_missing"
        finally:
            connection.close()
