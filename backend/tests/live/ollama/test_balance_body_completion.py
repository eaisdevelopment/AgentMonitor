"""Exercise the balance body reader against the installed real Ollama daemon."""

import http.client
import json
import time

from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    _BoundedHeaderHTTPResponse,
    _headers,
    _read_body,
)


def test_complete_real_ollama_body_does_not_require_a_live_socket_at_eof() -> None:
    """M6-A04/A07: a complete response remains successful after HTTP closes it."""
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=3)
    connection.response_class = _BoundedHeaderHTTPResponse
    try:
        connection.request("GET", "/api/version", headers={"Connection": "close"})
        response = connection.getresponse()
        assert response.status == 200
        headers = _headers(response)
        assert "content-length" in headers
        body = _read_body(
            connection,  # type: ignore[arg-type]  # Actual local HTTP, same stdlib reader.
            response,
            headers,
            time.monotonic() + 8.0,
        )
        assert len(body) == int(headers["content-length"][0])
        version = json.loads(body).get("version")
        assert isinstance(version, str) and version
        assert response.isclosed()
    finally:
        connection.close()
