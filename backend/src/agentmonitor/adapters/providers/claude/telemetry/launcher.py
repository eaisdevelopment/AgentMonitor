"""Exec-time Claude telemetry configuration with exact Linux process identity."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from agentmonitor.contracts.runtime_observation_v1 import ProcessIdentityV1

_MAX_STAT_BYTES = 16 * 1024
_MAX_BOOT_BYTES = 128


@dataclass(frozen=True, slots=True)
class ClaudeMonitoredExecV1:
    endpoint: str
    authorization_secret: str = field(repr=False)
    launch_id: str
    installation_id: str


def _read_bounded(path: Path, maximum: int) -> bytes:
    with path.open("rb") as stream:
        value = stream.read(maximum + 1)
    if len(value) > maximum:
        raise ValueError("claude_monitored_launch_metadata_oversize")
    return value


def current_process_identity() -> ProcessIdentityV1:
    """Read only self PID/start/boot namespace metadata before exec."""
    raw = _read_bounded(Path("/proc/self/stat"), _MAX_STAT_BYTES)
    if not raw.endswith(b"\n"):
        raise ValueError("claude_monitored_launch_stat_invalid")
    close_index = raw.rfind(b")")
    try:
        fields = raw[close_index + 2 :].decode("ascii").split()
        start_ticks = int(fields[19])
    except (UnicodeDecodeError, ValueError, IndexError):
        raise ValueError("claude_monitored_launch_stat_invalid") from None
    boot = _read_bounded(Path("/proc/sys/kernel/random/boot_id"), _MAX_BOOT_BYTES)
    if not boot.endswith(b"\n"):
        raise ValueError("claude_monitored_launch_scope_invalid")
    namespace = os.readlink("/proc/self/ns/pid")
    scope = hashlib.sha256(
        f"{boot.strip().decode('ascii')}\x1f{namespace}".encode("ascii")
    ).hexdigest()
    return ProcessIdentityV1(
        platform_source="linux.proc.process.v1",
        platform_scope_id=scope,
        pid=os.getpid(),
        start_time_ticks=start_ticks,
    )


def exec_monitored_claude(
    executable: Path,
    arguments: tuple[str, ...],
    configuration: ClaudeMonitoredExecV1,
) -> None:
    """Set only the reviewed child variables, then replace this helper process."""
    resolved = executable.resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError("claude_monitored_launch_executable_invalid")
    identity = current_process_identity()
    resource_attributes = ",".join(
        (
            f"agentmonitor.launch_id={configuration.launch_id}",
            f"agentmonitor.installation_id={configuration.installation_id}",
            f"agentmonitor.process.pid={identity.pid}",
            f"agentmonitor.process.start_time_ticks={identity.start_time_ticks}",
            "agentmonitor.process.platform_source=linux.proc.process.v1",
            f"agentmonitor.process.platform_scope_id={identity.platform_scope_id}",
        )
    )
    for inherited_name in (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
        "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_LOGS_HEADERS",
        "OTEL_EXPORTER_OTLP_LOGS_PROTOCOL",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
        "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
    ):
        os.unsetenv(inherited_name)
    reviewed_values = {
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        "OTEL_METRICS_EXPORTER": "otlp",
        "OTEL_LOGS_EXPORTER": "none",
        "OTEL_TRACES_EXPORTER": "none",
        "OTEL_EXPORTER_OTLP_METRICS_PROTOCOL": "http/json",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": configuration.endpoint,
        "OTEL_EXPORTER_OTLP_METRICS_HEADERS": (
            f"Authorization=Bearer {configuration.authorization_secret}"
        ),
        "OTEL_EXPORTER_OTLP_METRICS_TIMEOUT": "30000",
        "OTEL_METRIC_EXPORT_INTERVAL": "1000",
        "OTEL_METRICS_INCLUDE_SESSION_ID": "true",
        "OTEL_METRICS_INCLUDE_ACCOUNT_UUID": "true",
        "OTEL_METRICS_INCLUDE_VERSION": "true",
        "OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES": "true",
        "OTEL_METRICS_INCLUDE_REPOSITORY": "false",
        "OTEL_RESOURCE_ATTRIBUTES": resource_attributes,
        "OTEL_LOG_USER_PROMPTS": "0",
        "OTEL_LOG_ASSISTANT_RESPONSES": "0",
        "OTEL_LOG_TOOL_DETAILS": "0",
        "OTEL_LOG_TOOL_CONTENT": "0",
        "OTEL_LOG_RAW_API_BODIES": "0",
    }
    for name, value in reviewed_values.items():
        os.putenv(name, value)
    os.execv(resolved, (str(resolved), *arguments))
