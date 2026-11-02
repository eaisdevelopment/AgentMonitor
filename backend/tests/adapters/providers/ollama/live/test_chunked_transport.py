"""Exercise HTTP framing against the real, public Ollama documentation server."""

import socket
import ssl
import time


def test_real_ollama_documentation_chunked_response() -> None:
    from agentmonitor.adapters.providers.ollama.local_catalog.source import (
        MAX_BYTES,
        _read_chunked_body,
    )

    deadline = time.monotonic() + 10
    with socket.create_connection(("docs.ollama.com", 443), timeout=3) as raw:
        with ssl.create_default_context().wrap_socket(
            raw, server_hostname="docs.ollama.com"
        ) as sock:
            sock.sendall(
                b"GET /api/tags HTTP/1.1\r\nHost: docs.ollama.com\r\n"
                b"Accept-Encoding: identity\r\nConnection: close\r\n\r\n"
            )
            data = bytearray()
            while b"\r\n\r\n" not in data:
                remaining = deadline - time.monotonic()
                assert remaining > 0, "documentation_deadline_exceeded"
                sock.settimeout(remaining)
                chunk = sock.recv(8192)
                assert chunk, "documentation_headers_incomplete"
                data.extend(chunk)
                assert len(data) <= 16 * 1024 + MAX_BYTES
            headers, body = bytes(data).split(b"\r\n\r\n", 1)
            assert headers.startswith(b"HTTP/1.1 200 ")
            assert b"transfer-encoding: chunked" in headers.lower()
            result = _read_chunked_body(sock, body, deadline)
            assert 0 < len(result) <= MAX_BYTES
