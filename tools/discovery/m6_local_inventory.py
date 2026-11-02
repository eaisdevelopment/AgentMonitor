"""Bounded read-only inventory of the owner-local Ollama loopback service.

This is preliminary discovery, not capability admission or an M6 completion
gate. It never invokes inference, opens profiles, or persists response bodies.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

BASE = "http://127.0.0.1:11434"
LIMIT = 256 * 1024
TIMEOUT_SECONDS = 3


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: object,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


def read_json(path: str) -> dict[str, object]:
    if path not in {"/api/version", "/api/tags", "/api/ps"}:
        raise ValueError("source_not_allowed")
    request = urllib.request.Request(BASE + path, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        if (
            response.status != 200
            or response.headers.get_content_type() != "application/json"
        ):
            raise ValueError("response_invalid")
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("response_too_large")
    parsed = json.loads(data)
    if type(parsed) is not dict:
        raise ValueError("object_required")
    return parsed


def main() -> int:
    try:
        version = read_json("/api/version").get("version")
        installed = read_json("/api/tags").get("models")
        loaded = read_json("/api/ps").get("models")
        if type(version) is not str or not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+", version
        ):
            raise ValueError("version_invalid")
        if type(installed) is not list or type(loaded) is not list:
            raise ValueError("model_lists_invalid")
    except (OSError, ValueError, UnicodeError, urllib.error.URLError):
        print("M6 LOCAL INVENTORY: BLOCKED — local source unavailable or invalid")
        return 3
    print(
        f"M6 LOCAL INVENTORY: OBSERVED — daemon {version}; "
        f"installed {len(installed)}; loaded {len(loaded)}"
    )
    print(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "record_type": "agentmonitor.m6_local_inventory.v1",
                "status": "passed",
                "host_id": "local_loopback",
                "source_id": "ollama_loopback_127_0_0_1_11434",
                "version": version,
                "installed_model_count": len(installed),
                "loaded_model_count": len(loaded),
                "observed_at": datetime.now(UTC)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print("Not a capability-admission or milestone-completion result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
