"""P01 loopback request envelope; no authentication policy or IAM persistence."""

import asyncio
import re
import secrets

from agentmonitor.api.problem import problem_response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_CORRELATION = re.compile(r"[A-Za-z0-9._:-]{1,64}\Z")
_MAX_HEADERS = 64
_MAX_HEADER_BYTES = 16 * 1024
_MAX_JSON_BYTES = 8 * 1024
_MAX_CONCURRENT = 32
_REQUEST_DEADLINE_SECONDS = 10


def valid_correlation_id(value: str) -> bool:
    """Exact public P01 correlation grammar, independent of HTTP framing."""
    return _CORRELATION.fullmatch(value) is not None


class _OversizedBody(Exception):
    pass


class IamTransportGuard:
    """Admit only one bound IPv4 loopback authority with bounded HTTP work."""

    def __init__(self, app: ASGIApp, binding: object) -> None:
        self.app = app
        self.binding = binding
        self._inflight = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = scope["headers"]
        supplied = [value for key, value in headers if key == b"x-correlation-id"]
        try:
            candidate = supplied[0].decode("ascii") if len(supplied) == 1 else ""
        except UnicodeDecodeError:
            candidate = ""
        correlation_id = (
            candidate if valid_correlation_id(candidate) else secrets.token_urlsafe(18)
        )
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        async def secured_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                output = list(message.get("headers", []))
                output += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (
                        b"permissions-policy",
                        b"camera=(), microphone=(), geolocation=()",
                    ),
                    (b"cross-origin-resource-policy", b"same-origin"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-correlation-id", correlation_id.encode("ascii")),
                    (b"cache-control", b"no-store, private"),
                ]
                problem_content = any(
                    key.lower() == b"content-type"
                    and value.split(b";", 1)[0].strip() == b"application/problem+json"
                    for key, value in output
                )
                if (
                    problem_content
                    or scope["path"].startswith("/api/v1")
                    or scope["path"] == "/openapi.json"
                    or scope["path"].startswith("/problems/")
                ):
                    output.append(
                        (
                            b"content-security-policy",
                            b"default-src 'none'; frame-ancestors 'none'",
                        )
                    )
                elif scope["path"] in {"/docs", "/redoc"} or scope["path"].startswith(
                    "/docs-assets/"
                ):
                    output.append(
                        (
                            b"content-security-policy",
                            b"default-src 'none'; script-src 'self'; "
                            b"style-src 'self' 'unsafe-inline'; "
                            b"img-src 'self' data:; font-src 'self' data:; "
                            b"connect-src 'self'; object-src 'none'; "
                            b"base-uri 'none'; frame-ancestors 'none'",
                        )
                    )
                else:
                    output.append(
                        (
                            b"content-security-policy",
                            b"default-src 'self'; script-src 'self'; style-src 'self'; "
                            b"img-src 'self' data:; connect-src 'self'; "
                            b"object-src 'none'; "
                            b"base-uri 'none'; frame-ancestors 'none'",
                        )
                    )
                message["headers"] = output
            await send(message)

        async def deny(status: int, code: str) -> None:
            await problem_response(status, code, correlation_id)(
                scope, receive, secured_send
            )

        if (
            len(headers) > _MAX_HEADERS
            or sum(len(key) + len(value) for key, value in headers) > _MAX_HEADER_BYTES
        ):
            await deny(413, "request_too_large")
            return
        if len(supplied) > 1 or (supplied and not valid_correlation_id(candidate)):
            await deny(400, "invalid_correlation_id")
            return
        server = scope.get("server")
        client = scope.get("client")
        address = getattr(self.binding, "address", None)
        authority = (
            f"127.0.0.1:{server[1]}".encode("ascii")
            if server is not None and server[0] == "127.0.0.1"
            else b""
        )
        hosts = [value for key, value in headers if key == b"host"]
        if (
            not authority
            or server != address
            or client is None
            or client[0] != "127.0.0.1"
            or scope.get("scheme") != "http"
            or hosts != [authority]
        ):
            await deny(403, "host_not_allowed")
            return

        session_cookie_present = any(
            b"agentmonitor_session=" in value
            for key, value in headers
            if key == b"cookie"
        )
        auth_headers = [value for key, value in headers if key == b"authorization"]
        if len(auth_headers) > 1:
            await deny(400, "invalid_authorization_header")
            return
        bearer_present = bool(auth_headers and auth_headers[0].startswith(b"Bearer "))
        if session_cookie_present and bearer_present:
            await deny(400, "ambiguous_credentials")
            return
        for key, value in headers:
            if key in {b"authorization", b"x-csrf-token"} and len(value) > 512:
                await deny(413, "request_too_large")
                return
            if key == b"cookie" and any(
                len(part.strip()) > 540
                for part in value.split(b";")
                if part.strip().startswith(
                    (b"agentmonitor_session=", b"agentmonitor_csrf=")
                )
            ):
                await deny(413, "request_too_large")
                return

        origin_values = [value for key, value in headers if key == b"origin"]
        expected_origin = b"http://" + authority
        unsafe = scope["method"] not in {"GET", "HEAD"}
        requires_origin = (
            (scope["path"] == "/api/v1/session" and scope["method"] == "POST")
            or (scope["path"] == "/api/v1/iam/initialization")
            or (not bearer_present and (unsafe or session_cookie_present))
        )
        if (
            len(origin_values) > 1
            or (requires_origin and unsafe and origin_values != [expected_origin])
            or (
                requires_origin
                and not unsafe
                and origin_values
                and origin_values != [expected_origin]
            )
        ):
            await deny(403, "origin_not_allowed")
            return

        # An image or navigation from another loopback port can omit Origin
        # while still carrying the host-only session cookie. Reject before
        # M01 resolves (and potentially touches) that session. Fetch Metadata
        # distinguishes same-origin browser traffic from an explicit user
        # navigation; a non-browser cookie client can send canonical Origin.
        if session_cookie_present and not unsafe:
            fetch_site = [value for key, value in headers if key == b"sec-fetch-site"]
            fetch_mode = [value for key, value in headers if key == b"sec-fetch-mode"]
            fetch_dest = [value for key, value in headers if key == b"sec-fetch-dest"]
            direct_navigation = (
                fetch_site == [b"none"]
                and fetch_mode == [b"navigate"]
                and fetch_dest == [b"document"]
            )
            if (
                len(fetch_site) > 1
                or (
                    fetch_site
                    and fetch_site != [b"same-origin"]
                    and not direct_navigation
                )
                or (not fetch_site and origin_values != [expected_origin])
            ):
                await deny(403, "origin_not_allowed")
                return

        json_body_route = (
            scope["path"]
            in {
                "/api/v1/session",
                "/api/v1/session/password",
                "/api/v1/api-tokens",
            }
            and scope["method"] in {"POST", "PATCH"}
        ) or (
            scope["path"].startswith("/api/v1/api-tokens/")
            and scope["path"].endswith("/rotations")
            and scope["method"] == "POST"
        )
        if json_body_route:
            media = [value for key, value in headers if key == b"content-type"]
            if (
                len(media) != 1
                or media[0].split(b";", 1)[0].strip() != b"application/json"
            ):
                await deny(415, "unsupported_media_type")
                return

        length_values = [value for key, value in headers if key == b"content-length"]
        if len(length_values) > 1:
            await deny(400, "invalid_content_length")
            return
        if length_values:
            try:
                length = int(length_values[0])
            except ValueError:
                await deny(400, "invalid_content_length")
                return
            if length < 0 or length > _MAX_JSON_BYTES:
                await deny(413, "request_too_large")
                return
        if self._inflight >= _MAX_CONCURRENT:
            await deny(503, "request_capacity_exceeded")
            return

        received = 0

        async def bounded_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > _MAX_JSON_BYTES:
                    raise _OversizedBody
            return message

        self._inflight += 1
        started = False

        async def tracked_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await secured_send(message)

        try:
            if scope["path"].startswith(
                ("/api/v1", "/problems/", "/docs-assets/")
            ) or scope["path"] in {
                "/docs",
                "/redoc",
                "/openapi.json",
            }:
                await asyncio.wait_for(
                    self.app(scope, bounded_receive, tracked_send),
                    timeout=_REQUEST_DEADLINE_SECONDS,
                )
            else:
                await self.app(scope, bounded_receive, tracked_send)
        except _OversizedBody:
            if not started:
                await deny(413, "request_too_large")
        except TimeoutError:
            if not started:
                await deny(504, "request_timeout")
        except Exception:
            if not started:
                await deny(500, "internal_error")
        finally:
            self._inflight -= 1
