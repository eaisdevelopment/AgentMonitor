"""Isolated anonymous Ollama endpoint probe with sanitized stdout only."""

from __future__ import annotations

import json
import math
import os
import signal
import sys
import time
from pathlib import Path

_MAX_OPERATION_SECONDS = 8.0


class _DeadlineExpired(TimeoutError):
    pass


def _deadline_expired(_signum: int, _frame: object) -> None:
    raise _DeadlineExpired("probe_deadline_exceeded")


def _bootstrap_source_root() -> None:
    source_root = Path(__file__).resolve().parents[5]
    sys.path.insert(0, str(source_root))


def _write_all(payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(1, view)
        if written <= 0:
            raise OSError("probe_result_write_failed")
        view = view[written:]


def main() -> int:
    """Run one fixed request; never accept a destination or credential input."""
    if len(sys.argv) != 2:
        return 2
    try:
        deadline = float(sys.argv[1])
    except ValueError:
        return 2
    remaining = deadline - time.monotonic()
    if not math.isfinite(deadline) or not 0 < remaining <= _MAX_OPERATION_SECONDS:
        fields: list[object] = [
            "deadline_exceeded",
            None,
            None,
            "not_applicable",
            False,
        ]
        remaining = 0.0
    else:
        fields = []
        signal.signal(signal.SIGALRM, _deadline_expired)
        signal.setitimer(signal.ITIMER_REAL, remaining)
    try:
        if remaining > 0:
            _bootstrap_source_root()
            from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
                _read_cloud_balance_once_v1,
            )

            result = _read_cloud_balance_once_v1(
                authorization=None,
                deadline_monotonic=deadline,
            )
            fields = [
                result.state,
                result.http_status,
                result.retry_after_seconds,
                result.retry_after_state,
                result.balance is not None,
            ]
    except _DeadlineExpired:
        fields = ["deadline_exceeded", None, None, "not_applicable", False]
    except BaseException:
        fields = ["internal_adapter_error", None, None, "not_applicable", False]
    finally:
        if remaining > 0:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
    payload = json.dumps(fields, ensure_ascii=True, separators=(",", ":")).encode(
        "ascii"
    )
    if len(payload) > 256:
        payload = b'["internal_adapter_error",null,null,"not_applicable",false]'
    try:
        _write_all(payload)
    except OSError:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
