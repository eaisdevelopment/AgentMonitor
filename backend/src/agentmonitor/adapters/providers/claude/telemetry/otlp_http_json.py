"""Private loopback OTLP HTTP/JSON receiver for Claude session metrics only."""

from __future__ import annotations

import hashlib
import hmac
import json
import queue
import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socket import socket
from typing import ClassVar, cast

from agentmonitor.adapters.providers.claude.manifest import CLAUDE_OTEL_SOURCE_ID
from agentmonitor.contracts.runtime_observation_v1 import ProcessIdentityV1
from agentmonitor.modules.provider_system.application.gateway import (
    resolve_one_exact_observation,
)

CLAUDE_OTLP_SOURCE_ID = CLAUDE_OTEL_SOURCE_ID
CLAUDE_OTLP_SOURCE_VERSION = "1.0.0"
CLAUDE_OTLP_PARSER_VERSION = "1.0.0"
_MAX_BODY_BYTES = 1024 * 1024
_MAX_ATTRIBUTE_COUNT = 128
_REQUEST_TIMEOUT_SECONDS = 5
_COMMIT_ACK_TIMEOUT_SECONDS = 30
_LINUX_PROCESS_SOURCE_ID = "linux.proc.process.v1"
_ALLOWED_ATTRIBUTES = frozenset(
    {
        "agentmonitor.installation_id",
        "agentmonitor.launch_id",
        "agentmonitor.process.pid",
        "agentmonitor.process.platform_source",
        "agentmonitor.process.platform_scope_id",
        "agentmonitor.process.start_time_ticks",
        "app.version",
        "session.id",
        "user.account_id",
        "user.account_uuid",
    }
)


class ClaudeOtlpErrorV1(ValueError):
    """Bounded OTLP failure; raw payload values never enter the message."""


@dataclass(frozen=True, slots=True)
class ClaudeOtlpSessionCountV1:
    session_fingerprint: str = field(repr=False)
    process_identity: ProcessIdentityV1
    installation_id: str
    launch_id: str
    observed_account_fingerprint: str = field(repr=False)
    provider_version: str
    observed_at: datetime


class _CommitAcknowledgementV1:
    """Bounded one-shot synchronization from durable commit to HTTP response."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._committed: bool | None = None

    def wait(self, timeout_seconds: float) -> bool:
        if not isinstance(timeout_seconds, (int, float)) or not (
            0 < timeout_seconds <= 60
        ):
            raise ClaudeOtlpErrorV1("claude_otel_ack_timeout_invalid")
        if not self._event.wait(timeout_seconds):
            return False
        with self._lock:
            return self._committed is True

    def committed(self) -> None:
        with self._lock:
            if self._committed is not None:
                raise ClaudeOtlpErrorV1("claude_otel_ack_state_invalid")
            self._committed = True
            self._event.set()

    def failed(self) -> None:
        with self._lock:
            if self._committed is True:
                raise ClaudeOtlpErrorV1("claude_otel_ack_state_invalid")
            if self._committed is None:
                self._committed = False
                self._event.set()


def _attributes(raw: object) -> dict[str, object]:
    if not isinstance(raw, list) or len(raw) > _MAX_ATTRIBUTE_COUNT:
        raise ClaudeOtlpErrorV1("claude_otel_attributes_invalid")
    result: dict[str, object] = {}
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"key", "value"}:
            raise ClaudeOtlpErrorV1("claude_otel_attribute_invalid")
        key = item["key"]
        if not isinstance(key, str):
            raise ClaudeOtlpErrorV1("claude_otel_attribute_invalid")
        if key not in _ALLOWED_ATTRIBUTES:
            continue
        value = item["value"]
        if not isinstance(value, dict) or key in result:
            raise ClaudeOtlpErrorV1("claude_otel_attribute_invalid")
        representations = tuple(
            name
            for name in ("stringValue", "intValue", "doubleValue", "boolValue")
            if name in value
        )
        if len(representations) != 1:
            raise ClaudeOtlpErrorV1("claude_otel_attribute_invalid")
        result[key] = value[representations[0]]
    return result


def _required_string(attributes: dict[str, object], key: str) -> str:
    value = attributes.get(key)
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 256
        or value != value.strip()
        or not value.isprintable()
    ):
        raise ClaudeOtlpErrorV1("claude_otel_required_attribute_missing")
    return value


def _required_positive_int(attributes: dict[str, object], key: str) -> int:
    value = _required_string(attributes, key)
    if not value.isascii() or not value.isdigit():
        raise ClaudeOtlpErrorV1("claude_otel_process_identity_invalid")
    parsed = int(value)
    if parsed <= 0:
        raise ClaudeOtlpErrorV1("claude_otel_process_identity_invalid")
    return parsed


def _required_linux_process_source(attributes: dict[str, object]) -> str:
    value = _required_string(attributes, "agentmonitor.process.platform_source")
    if value != _LINUX_PROCESS_SOURCE_ID:
        raise ClaudeOtlpErrorV1("claude_otel_process_identity_invalid")
    return value


def _time_unix_nano(point: dict[str, object]) -> datetime:
    value = point.get("timeUnixNano")
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ClaudeOtlpErrorV1("claude_otel_timestamp_invalid")
    try:
        return datetime.fromtimestamp(int(value) / 1_000_000_000, tz=UTC)
    except (OverflowError, OSError, ValueError):
        raise ClaudeOtlpErrorV1("claude_otel_timestamp_invalid") from None


def parse_claude_session_count(
    body: bytes, *, expected_launch_id: str
) -> ClaudeOtlpSessionCountV1:
    """Extract one closed session-count point and discard all other attributes."""
    if not body or len(body) > _MAX_BODY_BYTES:
        raise ClaudeOtlpErrorV1("claude_otel_body_size_invalid")
    try:
        document = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ClaudeOtlpErrorV1("claude_otel_json_invalid") from None
    if not isinstance(document, dict) or set(document) != {"resourceMetrics"}:
        raise ClaudeOtlpErrorV1("claude_otel_envelope_invalid")
    resources = document["resourceMetrics"]
    if not isinstance(resources, list) or not 1 <= len(resources) <= 8:
        raise ClaudeOtlpErrorV1("claude_otel_resource_scope_invalid")
    matches: list[ClaudeOtlpSessionCountV1] = []
    for resource_metric in resources:
        if not isinstance(resource_metric, dict):
            raise ClaudeOtlpErrorV1("claude_otel_resource_scope_invalid")
        resource = resource_metric.get("resource")
        scopes = resource_metric.get("scopeMetrics")
        if not isinstance(resource, dict) or not isinstance(scopes, list):
            raise ClaudeOtlpErrorV1("claude_otel_resource_scope_invalid")
        resource_attributes = _attributes(resource.get("attributes", []))
        for scope in scopes:
            if not isinstance(scope, dict) or not isinstance(
                scope.get("metrics"), list
            ):
                raise ClaudeOtlpErrorV1("claude_otel_metric_scope_invalid")
            for metric in scope["metrics"]:
                if (
                    not isinstance(metric, dict)
                    or metric.get("name") != "claude_code.session.count"
                ):
                    continue
                summation = metric.get("sum")
                if not isinstance(summation, dict):
                    raise ClaudeOtlpErrorV1("claude_otel_session_metric_invalid")
                points = summation.get("dataPoints")
                if not isinstance(points, list) or not 1 <= len(points) <= 64:
                    raise ClaudeOtlpErrorV1("claude_otel_session_metric_invalid")
                for point in points:
                    if not isinstance(point, dict):
                        raise ClaudeOtlpErrorV1("claude_otel_session_metric_invalid")
                    point_attributes = _attributes(point.get("attributes", []))
                    combined = dict(resource_attributes)
                    for key, value in point_attributes.items():
                        if key in combined and combined[key] != value:
                            raise ClaudeOtlpErrorV1("claude_otel_attribute_conflict")
                        combined[key] = value
                    launch_id = _required_string(combined, "agentmonitor.launch_id")
                    if launch_id != expected_launch_id:
                        continue
                    session_id = _required_string(combined, "session.id")
                    session_fingerprint = hashlib.sha256(
                        f"claude.otel.session.v1\x1f{session_id}".encode()
                    ).hexdigest()
                    session_id = ""
                    account_uuid = _required_string(combined, "user.account_uuid")
                    account_id = _required_string(combined, "user.account_id")
                    fingerprint = hashlib.sha256(
                        f"claude.otel.account.v1\x1f{account_uuid}\x1f{account_id}".encode()
                    ).hexdigest()
                    matches.append(
                        ClaudeOtlpSessionCountV1(
                            session_fingerprint=session_fingerprint,
                            process_identity=ProcessIdentityV1(
                                platform_source=_required_linux_process_source(
                                    combined
                                ),
                                platform_scope_id=_required_string(
                                    combined, "agentmonitor.process.platform_scope_id"
                                ),
                                pid=_required_positive_int(
                                    combined, "agentmonitor.process.pid"
                                ),
                                start_time_ticks=_required_positive_int(
                                    combined,
                                    "agentmonitor.process.start_time_ticks",
                                ),
                            ),
                            installation_id=_required_string(
                                combined, "agentmonitor.installation_id"
                            ),
                            launch_id=launch_id,
                            observed_account_fingerprint=fingerprint,
                            provider_version=_required_string(combined, "app.version"),
                            observed_at=_time_unix_nano(point),
                        )
                    )
    resolved = resolve_one_exact_observation(tuple(matches))
    if resolved is None:
        raise ClaudeOtlpErrorV1("claude_otel_session_count_ambiguous")
    return resolved


class _PrivateServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = False

    def __init__(self, receiver: ClaudeOtlpHttpJsonReceiverV1) -> None:
        self.receiver = receiver
        super().__init__(("127.0.0.1", 0), _Handler)

    def get_request(self) -> tuple[socket, tuple[str, int]]:
        request, address = super().get_request()
        request.settimeout(_REQUEST_TIMEOUT_SECONDS)
        return request, cast(tuple[str, int], address)

    def handle_error(self, request: object, client_address: object) -> None:
        return


class _Handler(BaseHTTPRequestHandler):
    server: _PrivateServer

    def do_POST(self) -> None:  # noqa: N802
        receiver = self.server.receiver
        if self.client_address[0] != "127.0.0.1" or self.path != "/v1/metrics":
            self.send_error(404)
            return
        expected = f"Bearer {receiver.authorization_secret}"
        supplied = self.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, expected):
            self.send_error(401)
            return
        if self.headers.get("Content-Type", "").lower() != "application/json":
            self.send_error(415)
            return
        raw_length = self.headers.get("Content-Length")
        if raw_length is None or not raw_length.isascii() or not raw_length.isdigit():
            self.send_error(411)
            return
        length = int(raw_length)
        if not 1 <= length <= _MAX_BODY_BYTES:
            self.send_error(413)
            return
        if not receiver.wait_for_observation_acceptance(_REQUEST_TIMEOUT_SECONDS):
            self.send_error(503)
            return
        try:
            body = self.rfile.read(length)
        except OSError:
            self.send_error(408)
            return
        if len(body) != length:
            self.send_error(400)
            return
        try:
            observation = parse_claude_session_count(
                body, expected_launch_id=receiver.launch_id
            )
        except ClaudeOtlpErrorV1:
            self.send_error(400)
            return
        if not receiver.submit_after_process_capture(observation):
            self.send_error(409)
            return
        if not receiver.wait_for_commit_acknowledgement(
            observation, _COMMIT_ACK_TIMEOUT_SECONDS
        ):
            self.send_error(503)
            return
        response = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: object) -> None:
        return


class ClaudeOtlpHttpJsonReceiverV1:
    """One-launch authenticated receiver; it never retains the raw request body."""

    MAX_BODY_BYTES: ClassVar[int] = _MAX_BODY_BYTES

    def __init__(self) -> None:
        self.launch_id = secrets.token_hex(16)
        self.authorization_secret = secrets.token_urlsafe(32)
        self._observations: queue.Queue[ClaudeOtlpSessionCountV1] = queue.Queue(1)
        self._accepted_observation: ClaudeOtlpSessionCountV1 | None = None
        self._accepted_at: datetime | None = None
        self._capture_completed_at: datetime | None = None
        self._accepted_observation_lock = threading.Lock()
        self._observation_acceptance = threading.Event()
        self._acknowledgement = _CommitAcknowledgementV1()
        self._server = _PrivateServer(self)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="agentmonitor-claude-otlp",
            daemon=True,
        )

    @property
    def endpoint(self) -> str:
        host, port = cast(tuple[str, int], self._server.server_address)
        return f"http://{host}:{port}/v1/metrics"

    def __enter__(self) -> ClaudeOtlpHttpJsonReceiverV1:
        self._thread.start()
        return self

    def wait_for_observation_acceptance(self, timeout_seconds: float) -> bool:
        """Block request parsing until the exact launched process is captured."""
        if not isinstance(timeout_seconds, (int, float)) or not (
            0 < timeout_seconds <= 60
        ):
            raise ClaudeOtlpErrorV1("claude_otel_acceptance_timeout_invalid")
        return self._observation_acceptance.wait(timeout_seconds)

    def enable_observation_acceptance(self, captured_at: datetime) -> None:
        """Open the one-shot metric lane after safe process metadata capture."""
        if not isinstance(
            captured_at, datetime
        ) or captured_at.utcoffset() != UTC.utcoffset(captured_at):
            raise ClaudeOtlpErrorV1("claude_otel_capture_timestamp_invalid")
        with self._accepted_observation_lock:
            if self._capture_completed_at is not None:
                raise ClaudeOtlpErrorV1("claude_otel_acceptance_state_invalid")
            self._capture_completed_at = captured_at
            self._observation_acceptance.set()

    def submit_after_process_capture(
        self, observation: ClaudeOtlpSessionCountV1
    ) -> bool:
        """Accept one parsed metric only after the capture gate is open."""
        with self._accepted_observation_lock:
            accepted_at = datetime.now(UTC)
            if (
                self._capture_completed_at is None
                or self._capture_completed_at > accepted_at
            ):
                return False
            if self._accepted_observation is None:
                self._accepted_observation = observation
                self._accepted_at = accepted_at
                self._observations.put_nowait(observation)
                return True
            return self._accepted_observation == observation

    def wait(self, timeout_seconds: float) -> ClaudeOtlpSessionCountV1:
        if not isinstance(timeout_seconds, (int, float)) or not (
            0 < timeout_seconds <= 60
        ):
            raise ClaudeOtlpErrorV1("claude_otel_wait_timeout_invalid")
        try:
            return self._observations.get(timeout=timeout_seconds)
        except queue.Empty:
            raise ClaudeOtlpErrorV1("claude_otel_session_count_deadline") from None

    def wait_for_commit_acknowledgement(
        self, observation: ClaudeOtlpSessionCountV1, timeout_seconds: float
    ) -> bool:
        """Return success only after the accepted observation is durably verified."""
        with self._accepted_observation_lock:
            if self._accepted_observation != observation:
                return False
        return self._acknowledgement.wait(timeout_seconds)

    def acknowledge_committed(self, observation: ClaudeOtlpSessionCountV1) -> None:
        """Release HTTP success only for the exact committed observation."""
        with self._accepted_observation_lock:
            if self._accepted_observation != observation:
                raise ClaudeOtlpErrorV1("claude_otel_ack_state_invalid")
        self._acknowledgement.committed()

    def acknowledge_failed(self) -> None:
        """Release any waiting exporter with a retryable non-success response."""
        self._acknowledgement.failed()

    def __exit__(self, *args: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
