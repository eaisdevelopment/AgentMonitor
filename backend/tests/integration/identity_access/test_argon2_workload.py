"""M01-CRYPTO-004: real production-adapter workload on the target Linux host."""

import json
import resource
import secrets
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter


def _measure_in_isolated_process() -> dict[str, float | bool]:
    from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1

    verifier = Argon2PasswordV1()
    candidate = secrets.token_urlsafe(32)
    encoded = verifier.hash(candidate)

    def verify_once(_: int) -> tuple[float, bool]:
        started = perf_counter()
        matched = verifier.verify(encoded, candidate)
        return perf_counter() - started, matched

    with ThreadPoolExecutor(max_workers=2) as executor:
        measurements = list(executor.map(verify_once, range(100)))
    durations = sorted(duration for duration, _ in measurements)
    p95_seconds = durations[94]
    peak_native = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_kib = peak_native / 1024 if sys.platform == "darwin" else peak_native
    return {
        "all_matched": all(matched for _, matched in measurements),
        "p95_seconds": p95_seconds,
        "peak_kib": peak_kib,
    }


def test_two_worker_real_argon2_verification_budget() -> None:
    # The 256 MiB budget applies to the process running the adapter, not the
    # much larger pytest/plugin host. This child runs the actual production
    # adapter on the installed Python and reports only numeric measurements.
    source_root = Path(__file__).resolve().parents[3] / "src"
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--probe"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(source_root)},
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0
    outcome = json.loads(completed.stdout)
    assert outcome["all_matched"] is True
    assert outcome["p95_seconds"] < 0.250
    assert outcome["peak_kib"] < 256 * 1024


if __name__ == "__main__" and sys.argv[1:] == ["--probe"]:
    print(json.dumps(_measure_in_isolated_process(), sort_keys=True))
