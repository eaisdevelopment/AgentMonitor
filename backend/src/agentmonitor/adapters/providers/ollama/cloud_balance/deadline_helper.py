"""Isolated Ollama worker; credentials never cross its process boundary."""

from __future__ import annotations

import json
import math
import os
import signal
import sys
import time
from datetime import UTC, datetime
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


def _fallback_payload(state: str, dispatch_certainty: str) -> bytes:
    # A fallback carries no trusted HTTP status. Preserve only the conservative
    # fact that the request may have started when the precise child result is
    # unavailable.
    if dispatch_certainty == "response_received":
        dispatch_certainty = "may_have_started"
    return json.dumps(
        [
            state,
            datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            None,
            None,
            "not_applicable",
            dispatch_certainty,
            None,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")


def _decimal_argument(value: str, *, minimum: int) -> int:
    if not value or len(value) > 20 or not value.isascii() or not value.isdecimal():
        raise ValueError("probe_argument_invalid") from None
    parsed = int(value)
    if parsed < minimum or str(parsed) != value:
        raise ValueError("probe_argument_invalid") from None
    return parsed


def main() -> int:
    """Run one fixed request; authenticated mode requires an inherited lock."""
    if len(sys.argv) not in {2, 10}:
        return 2
    try:
        deadline = float(sys.argv[1])
    except ValueError:
        return 2
    remaining = deadline - time.monotonic()
    if not math.isfinite(deadline) or not 0 < remaining <= _MAX_OPERATION_SECONDS:
        payload = _fallback_payload("deadline_exceeded", "not_started")
        remaining = 0.0
    else:
        payload = b""
        signal.signal(signal.SIGALRM, _deadline_expired)
        signal.setitimer(signal.ITIMER_REAL, remaining)
    fallback_certainty = "not_started"
    try:
        if remaining > 0:
            _bootstrap_source_root()
            from agentmonitor.adapters.providers.ollama.cloud_balance import (
                worker_protocol,
            )
            from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
                _read_cloud_balance_once_v1,
            )

            authorization = None
            request_allowed = True
            if len(sys.argv) == 10:
                from agentmonitor.adapters.providers.ollama.cloud_balance import (
                    credential_lock,
                    keyring_authorization,
                )
                from agentmonitor.contracts.common_v1 import OpaqueIdV1

                try:
                    account_id = OpaqueIdV1(sys.argv[3])
                    inherited_lock = credential_lock.inherited_credential_lock_v1(
                        account_id=account_id,
                        descriptor=_decimal_argument(sys.argv[4], minimum=3),
                        device=_decimal_argument(sys.argv[5], minimum=0),
                        inode=_decimal_argument(sys.argv[6], minimum=1),
                        directory_descriptor=_decimal_argument(sys.argv[7], minimum=3),
                        root_device=_decimal_argument(sys.argv[8], minimum=0),
                        root_inode=_decimal_argument(sys.argv[9], minimum=1),
                    )
                    authorization = keyring_authorization.SecretToolAuthorizationV1(
                        sys.argv[2], account_id, inherited_lock
                    )
                except (OSError, TypeError, ValueError):
                    payload = _fallback_payload("internal_adapter_error", "not_started")
                    request_allowed = False

            # From this point a failure outside the source cannot prove that the
            # fixed request did not cross the wire. The source returns a more
            # precise closed fact when it completes normally.
            if request_allowed:
                fallback_certainty = "may_have_started"
                result = _read_cloud_balance_once_v1(
                    authorization=authorization,
                    deadline_monotonic=deadline,
                )
                fallback_certainty = result.dispatch_certainty
                payload = worker_protocol.encode_worker_result_v2(
                    state=result.state,
                    observed_at=result.observed_at,
                    http_status=result.http_status,
                    balance=result.balance,
                    retry_after_seconds=result.retry_after_seconds,
                    retry_after_state=result.retry_after_state,
                    dispatch_certainty=result.dispatch_certainty,
                )
    except _DeadlineExpired:
        payload = _fallback_payload("deadline_exceeded", fallback_certainty)
    except BaseException:
        payload = _fallback_payload("internal_adapter_error", fallback_certainty)
    finally:
        if remaining > 0:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
    if not 0 < len(payload) <= 4096:
        payload = _fallback_payload("internal_adapter_error", fallback_certainty)
    try:
        _write_all(payload)
    except OSError:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
