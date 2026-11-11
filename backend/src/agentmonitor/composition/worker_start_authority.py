"""One-shot parent authority shared by fixed AgentMonitor workers."""

import os
import select
import sys
import time

_START_AUTHORITY_TIMEOUT_SECONDS = 8


def valid_worker_start_token_v1(token: str) -> bool:
    return len(token) == 32 and all(
        character in "0123456789abcdef" for character in token
    )


def consume_worker_start_authority_v1(token: str) -> bool:
    """Consume one parent-issued grant before a worker opens owned state."""
    if not valid_worker_start_token_v1(token):
        return False
    expected = ("START " + token + "\n").encode("ascii")
    received = bytearray()
    deadline = time.monotonic() + _START_AUTHORITY_TIMEOUT_SECONDS
    while len(received) <= len(expected):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            ready, _, _ = select.select([sys.stdin.fileno()], [], [], remaining)
        except (OSError, ValueError):
            return False
        if not ready:
            return False
        try:
            chunk = os.read(sys.stdin.fileno(), len(expected) + 1 - len(received))
        except OSError:
            return False
        if not chunk:
            return False
        received.extend(chunk)
        if b"\n" in received:
            return bytes(received) == expected
    return False
