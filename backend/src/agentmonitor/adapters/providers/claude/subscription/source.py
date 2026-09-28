"""One-shot, bounded, read-only Claude `/usage` screen-reader source."""

import errno
import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import termios
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.providers.claude.authentication.classification import (
    classify_auth_failure,
)
from agentmonitor.adapters.providers.claude.subscription.mapper import (
    SanitizedClaudeUsageSnapshot,
    SanitizedClaudeUsageWindow,
)

_MAX_OUTPUT_BYTES = 4 * 1024 * 1024
_ANSI_OSC = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")
_ANSI_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_ANSI_SINGLE = re.compile(r"\x1b[@-_]")
_PERCENT_USED = re.compile(
    r"(?:Esc to cancel)?(?:[0-9]{1,3}% )?"
    r"([0-9]{1,3}(?:\.[0-9]+)?)% used\Z"
)
_SAFE_RESET = re.compile(r"Resets [A-Za-z0-9 (),:+/.-]{1,88}\Z")
_LABELS = {
    "Current session": "current_session",
    "Current week (all models)": "current_week_all_models",
    "Current week (Sonnet only)": "current_week_sonnet_only",
}
_SAFE_PARSE_FAILURE_CODES = frozenset(
    {
        "usage_output_encoding_invalid",
        "usage_terminal_marker_missing",
        "usage_window_set_invalid",
        "usage_window_incomplete",
        "usage_reset_display_invalid",
        "usage_percent_invalid",
        "usage_percent_out_of_range",
        "usage_window_conflicting_duplicate",
    }
)

SourceFailureState = Literal[
    "reauthentication_required",
    "authorization_insufficient",
    "provider_unavailable",
    "invalid_provider_data",
    "deadline_exceeded",
    "blocked_user_action_required",
]


@dataclass(frozen=True, slots=True)
class ClaudeUsageSourceFailure:
    state: SourceFailureState
    code: str


class _IncompleteRender(ValueError):
    pass


def _plain_lines(raw: bytes) -> tuple[str, ...]:
    try:
        rendered = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise _IncompleteRender("usage_output_encoding_invalid") from error
    rendered = _ANSI_OSC.sub("", rendered)
    rendered = _ANSI_CSI.sub("", rendered)
    rendered = _ANSI_SINGLE.sub("", rendered)
    rendered = rendered.replace("\r", "\n")
    lines = tuple(line.strip() for line in rendered.splitlines() if line.strip())
    rendered = ""
    return lines


def _parse_latest_complete_render(raw: bytes) -> SanitizedClaudeUsageSnapshot:
    lines = _plain_lines(raw)
    markers = tuple(
        index for index, line in enumerate(lines) if line == "Usage credits"
    )
    if not markers:
        raise _IncompleteRender("usage_terminal_marker_missing")

    for position in range(len(markers) - 1, -1, -1):
        marker = markers[position]
        start = markers[position - 1] + 1 if position > 0 else 0
        segment = lines[start:marker]
        if any(line in _LABELS for line in segment):
            return _parse_complete_usage_segment(segment)
    raise _IncompleteRender("usage_window_set_invalid")


def _parse_complete_usage_segment(
    final: tuple[str, ...],
) -> SanitizedClaudeUsageSnapshot:
    parsed: list[SanitizedClaudeUsageWindow] = []
    for label, key in _LABELS.items():
        occurrences = tuple(
            index for index, candidate in enumerate(final) if candidate == label
        )
        if not occurrences:
            continue
        # Ink appends terminal refresh history to the PTY byte stream. Earlier
        # occurrences of the same label are superseded screen redraws, not
        # simultaneous values. Only the newest occurrence is authoritative;
        # conflicts inside that current block remain invalid.
        index = occurrences[-1]
        next_label = next(
            (
                position
                for position in range(index + 1, len(final))
                if final[position] in _LABELS
            ),
            len(final),
        )
        following = final[index + 1 : min(index + 7, next_label)]
        percent_matches = tuple(
            match
            for candidate in following
            if (match := _PERCENT_USED.fullmatch(candidate)) is not None
        )
        reset_lines = tuple(
            candidate for candidate in following if candidate.startswith("Resets ")
        )
        if not percent_matches or not reset_lines:
            raise _IncompleteRender("usage_window_incomplete")
        if any(_SAFE_RESET.fullmatch(value) is None for value in reset_lines):
            raise _IncompleteRender("usage_reset_display_invalid")
        try:
            percents = tuple(Decimal(match.group(1)) for match in percent_matches)
        except InvalidOperation as error:
            raise _IncompleteRender("usage_percent_invalid") from error
        if any(not Decimal("0") <= percent <= Decimal("100") for percent in percents):
            raise _IncompleteRender("usage_percent_out_of_range")
        if len(set(percents)) != 1 or len(set(reset_lines)) != 1:
            raise _IncompleteRender("usage_window_conflicting_duplicate")
        percent, reset_display = percents[-1], reset_lines[-1]
        parsed.append(
            SanitizedClaudeUsageWindow(
                window_key=key,  # type: ignore[arg-type]
                percent_used=percent,
                reset_display=reset_display,
            )
        )
    keys = tuple(item.window_key for item in parsed)
    if (
        not 2 <= len(parsed) <= 3
        or len(keys) != len(set(keys))
        or "current_session" not in keys
        or "current_week_all_models" not in keys
    ):
        raise _IncompleteRender("usage_window_set_invalid")
    now = datetime.now(UTC)
    return SanitizedClaudeUsageSnapshot(tuple(parsed), now, now)


def _terminate_owned_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)


def _safe_deadline_code(raw: bytes) -> str:
    """Return only a closed progress category, never provider terminal text."""
    raw_lower = raw.lower()
    if b"usage credits" in raw_lower:
        try:
            _parse_latest_complete_render(raw)
        except _IncompleteRender as error:
            reason = str(error)
            if reason in _SAFE_PARSE_FAILURE_CODES:
                return "usage_deadline_" + reason.removeprefix("usage_")
        return "usage_deadline_incomplete_render"
    if any(label.encode("ascii").lower() in raw_lower for label in _LABELS):
        return "usage_deadline_partial_render"
    if b"trust" in raw_lower and b"folder" in raw_lower:
        return "usage_blocked_workspace_trust"
    if b"choose a login method" in raw_lower or b"/login" in raw_lower:
        return "usage_blocked_login_required"
    if b"welcome" in raw_lower:
        return "usage_blocked_onboarding"
    if b"/usage" in raw_lower:
        return "usage_deadline_after_command_echo"
    if b"claude code" in raw_lower:
        return "usage_deadline_at_application_shell"
    if raw_lower:
        return "usage_deadline_before_usage_render"
    return "usage_deadline_no_output"


def collect_usage_once(
    executable: Path, *, deadline_ms: int
) -> SanitizedClaudeUsageSnapshot | ClaudeUsageSourceFailure:
    """Invoke Claude exactly once, issue `/usage`, and return allowlisted fields."""
    if not 1 <= deadline_ms <= 30_000:
        return ClaudeUsageSourceFailure(
            "invalid_provider_data", "usage_deadline_invalid"
        )
    master_fd, slave_fd = pty.openpty()
    # Ink does not render reliably on a zero-sized pseudo-terminal.
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 160, 0, 0))
    process: subprocess.Popen[bytes] | None = None
    raw = bytearray()
    started = time.monotonic()
    command_sent = False
    last_output = started
    try:
        process = subprocess.Popen(
            [
                str(executable),
                "--ax-screen-reader",
                "--safe-mode",
                "--restricted",
                "--setting-sources",
                "user",
                "--strict-mcp-config",
                "--no-chrome",
                "--permission-mode",
                "dontAsk",
            ],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            start_new_session=True,
            env={
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "TERM": "xterm-256color",
                "NO_COLOR": "1",
                "CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "1",
                "CLAUDE_CODE_SKIP_PROMPT_HISTORY": "1",
                "DISABLE_AUTOUPDATER": "1",
                "DISABLE_UPDATES": "1",
                "DISABLE_ERROR_REPORTING": "1",
                "DISABLE_TELEMETRY": "1",
            },
        )
        os.close(slave_fd)
        slave_fd = -1
        os.set_blocking(master_fd, False)
        while (time.monotonic() - started) * 1000 < deadline_ms:
            readable, _, _ = select.select([master_fd], [], [], 0.1)
            if readable:
                try:
                    chunk = os.read(master_fd, 65_536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        chunk = b""
                    else:
                        raise
                if chunk:
                    raw.extend(chunk)
                    last_output = time.monotonic()
                    if len(raw) > _MAX_OUTPUT_BYTES:
                        return ClaudeUsageSourceFailure(
                            "invalid_provider_data", "usage_output_limit_exceeded"
                        )
            elapsed = time.monotonic() - started
            application_ready = b"claude code v" in bytes(raw).lower()
            if not command_sent and (
                (application_ready and time.monotonic() - last_output >= 0.35)
                or elapsed >= 8
            ):
                os.write(master_fd, b"/usage\r")
                command_sent = True
            if command_sent and raw:
                try:
                    snapshot = _parse_latest_complete_render(bytes(raw))
                except _IncompleteRender:
                    pass
                else:
                    os.write(master_fd, b"\x1b/exit\r")
                    raw[:] = b""
                    return snapshot
            if process.poll() is not None:
                break
        raw_lower = bytes(raw).lower()
        auth = classify_auth_failure(raw_lower)
        deadline_code = _safe_deadline_code(bytes(raw))
        raw[:] = b""
        if auth == "reauthentication_required":
            return ClaudeUsageSourceFailure(auth, "claude_reauthentication_required")
        if auth == "authorization_insufficient":
            return ClaudeUsageSourceFailure(auth, "claude_authorization_insufficient")
        if process.poll() is None:
            return ClaudeUsageSourceFailure("deadline_exceeded", deadline_code)
        return ClaudeUsageSourceFailure(
            "provider_unavailable", "usage_process_exited_before_complete_render"
        )
    except (OSError, subprocess.SubprocessError):
        raw[:] = b""
        return ClaudeUsageSourceFailure(
            "provider_unavailable", "usage_process_invocation_failed"
        )
    finally:
        raw[:] = b""
        if process is not None:
            _terminate_owned_process(process)
        if slave_fd >= 0:
            os.close(slave_fd)
        os.close(master_fd)
