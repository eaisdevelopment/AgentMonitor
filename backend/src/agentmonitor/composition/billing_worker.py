"""Fixed supervised billing entrypoint; no provider work in the HTTP process."""

import argparse
import time
from pathlib import Path

from agentmonitor.composition.worker_start_authority import (
    consume_worker_start_authority_v1,
)


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
    try:
        # Import the runtime only after the parent has authorized this worker.
        from agentmonitor.composition.billing_collection import BillingCollectionV1

        collector = BillingCollectionV1(
            args.data_root,
            credential_env_file=args.credential_env_file,
            deadline_monotonic=process_deadline,
        )
        return collector.run(recovery_only=args.recovery_only)
    except Exception:
        # Boundary-only classification: no provider body, secret or exception
        # text enters supervisor output. Unresolved work is recovered from M04.
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
