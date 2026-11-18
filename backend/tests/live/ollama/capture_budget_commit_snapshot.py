"""Test-owned worker: copy genuine committed storage before run finalization.

Never reads frame locals or provider bodies. The original live worker finishes
normally; only its untouched private snapshot is later used for recovery.
"""

from __future__ import annotations

import inspect
import os
import resource
import sqlite3
import sys
import threading
import time
from pathlib import Path
from types import FrameType
from typing import Protocol


class TraceFunction(Protocol):
    def __call__(
        self, frame: FrameType, event: str, argument: object, /
    ) -> TraceFunction | None: ...


def main() -> int:
    root, destination, authority = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    watchdog = threading.Timer(120, lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    from agentmonitor.composition import billing_worker
    from agentmonitor.composition.ollama_env_store import read_env_location
    from agentmonitor.modules.collection_control.application.budget_executor import (
        ExecuteBudgetCollectionRunV1,
    )

    operation = ExecuteBudgetCollectionRunV1._collect_and_commit
    lines, start = inspect.getsourcelines(operation)
    matches = [
        start + index
        for index, line in enumerate(lines)
        if line.strip().startswith("final_time = completed_at()")
        and index > 0
        and lines[index - 1].strip() == "receipt = self._sink.commit(outcome)"
    ]
    if len(matches) != 1:
        print("M7 SNAPSHOT: boundary_unavailable", flush=True)
        return 6
    outcome = "not_started"

    def trace(frame: FrameType, event: str, _argument: object) -> TraceFunction | None:
        nonlocal outcome
        if frame.f_code is not operation.__code__:
            return None
        if event == "call":
            outcome = "not_observed"
        if event == "line" and frame.f_lineno == matches[0]:
            sys.settrace(None)
            try:
                deadline = time.monotonic() + 10

                def bounded_copy(_status: int, _remaining: int, _total: int) -> None:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("snapshot_deadline")

                source = sqlite3.connect(
                    f"file:{root / 'agentmonitor.db'}?mode=ro", uri=True, timeout=1
                )
                target = sqlite3.connect(destination, timeout=1)
                try:
                    source.backup(target, pages=128, progress=bounded_copy, sleep=0.01)
                finally:
                    target.close()
                    source.close()
                outcome = "captured"
            except Exception:
                # A verification failure must never prevent live finalization.
                outcome = "capture_failed"
            return None
        return trace

    location = read_env_location(root)
    if location is None:
        return 6
    sys.argv = [
        "billing_worker",
        "--data-root",
        str(root),
        "--credential-env-file",
        str(location),
        "--start-authority",
        authority,
    ]
    try:
        sys.settrace(trace)
        result = billing_worker.main()
    finally:
        sys.settrace(None)
        watchdog.cancel()
    print("M7 SNAPSHOT: " + outcome, flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
