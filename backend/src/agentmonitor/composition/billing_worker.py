"""Fixed supervised billing entrypoint; no provider work in the HTTP process."""

import argparse
import re
import sys
import syslog
import time
from pathlib import Path

from agentmonitor.composition.worker_start_authority import (
    consume_worker_start_authority_v1,
)

_FAILURE_PHASES = frozenset({"import", "initialize", "collect"})
_FAILURE_TYPES = frozenset(
    {
        "Exception",
        "ImportError",
        "ModuleNotFoundError",
        "ValueError",
        "TypeError",
        "RuntimeError",
        "OSError",
        "BlockingIOError",
        "PermissionError",
        "FileNotFoundError",
        "TimeoutError",
        "SqlitePolicyError",
        "BudgetCollectionError",
        "CollectionRepositoryErrorV1",
        "CredentialBindingRepositoryErrorV1",
        "RegistryRepositoryErrorV1",
        "BudgetRepositoryError",
        "CapacityRepositoryErrorV1",
    }
)
_SOURCE_PATH = re.compile(
    r"(?:composition|adapters|modules|contracts|foundation)/"
    r"(?:[a-z_][a-z0-9_]*/)*[a-z_][a-z0-9_]*\.py"
)


def format_worker_failure(
    phase: str, exception_type: str, source_path: str, line: int
) -> str:
    """Pure closed diagnostic, with no exception object/message/arguments."""
    safe_phase = phase if phase in _FAILURE_PHASES else "unknown"
    safe_type = exception_type if exception_type in _FAILURE_TYPES else "Exception"
    location = "unknown:0"
    if (
        len(source_path) <= 240
        and _SOURCE_PATH.fullmatch(source_path) is not None
        and type(line) is int
        and 1 <= line <= 1000000
    ):
        location = f"backend/src/agentmonitor/{source_path}:{line}"
    return (
        f"BILLING_WORKER_FAILURE phase={safe_phase} type={safe_type} source={location}"
    )


def _report_failure(phase: str, error: Exception) -> None:
    # Read code location only. Never render a traceback, args, locals or messages.
    source_root = Path(__file__).parent.parent
    source_path, line = "", 0
    trace = error.__traceback__
    while trace is not None:
        try:
            candidate = Path(trace.tb_frame.f_code.co_filename).relative_to(source_root)
        except ValueError:
            pass
        else:
            source_path, line = candidate.as_posix(), trace.tb_lineno
        trace = trace.tb_next
    diagnostic = format_worker_failure(phase, type(error).__name__, source_path, line)
    try:
        print(diagnostic, file=sys.stderr, flush=True)
    except OSError:
        pass
    # The existing transient launcher discards piped stderr. The local journal
    # receives the same closed message through syslog, without another file/store.
    try:
        syslog.syslog(syslog.LOG_ERR, diagnostic)
    except OSError:
        pass


def main() -> int:
    """Require the supervisor's live grant before opening AgentMonitor state."""
    process_deadline = time.monotonic() + 115
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--credential-env-file", type=Path)
    parser.add_argument("--recovery-only", action="store_true")
    parser.add_argument("--start-authority", required=True)
    args = parser.parse_args()
    if not args.data_root.is_absolute() or args.data_root in {Path("/"), Path.home()}:
        return 2
    if not consume_worker_start_authority_v1(args.start_authority):
        return 5
    if not (args.data_root / "agentmonitor.db").is_file():
        return 3
    phase = "import"
    try:
        # Import the runtime only after the parent has authorized this worker.
        from agentmonitor.composition.billing_collection import BillingCollectionV1

        phase = "initialize"
        collector = BillingCollectionV1(
            args.data_root,
            credential_env_file=args.credential_env_file,
            deadline_monotonic=process_deadline,
        )
        phase = "collect"
        return collector.run(recovery_only=args.recovery_only)
    except Exception as error:
        # Boundary-only classification: no provider body, secret or exception
        # text enters supervisor output. Unresolved work is recovered from M04.
        _report_failure(phase, error)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
