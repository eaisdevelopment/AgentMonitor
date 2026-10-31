"""M01-CRYPTO-004: real production-adapter workload on the target Linux host."""

import json
import resource
import secrets
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter

import pytest


def _peak_rss_kib() -> int:
    if sys.platform == "linux":
        for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
            if line.startswith("VmHWM:"):
                fields = line.split()
                if len(fields) == 3 and fields[2] == "kB" and fields[1].isdigit():
                    return int(fields[1])
                break
        raise RuntimeError("linux_peak_rss_unavailable")
    if sys.platform == "darwin":
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    raise RuntimeError("process_peak_rss_unsupported_platform")


def test_linux_peak_rss_uses_current_process_vmhwm() -> None:
    if sys.platform != "linux":
        pytest.skip("Linux /proc peak-RSS boundary is unavailable on this platform")
    status_before = Path("/proc/self/status").read_text(encoding="ascii")
    before = int(
        next(
            line for line in status_before.splitlines() if line.startswith("VmHWM:")
        ).split()[1]
    )
    observed = _peak_rss_kib()
    status_after = Path("/proc/self/status").read_text(encoding="ascii")
    after = int(
        next(
            line for line in status_after.splitlines() if line.startswith("VmHWM:")
        ).split()[1]
    )
    assert before <= observed <= after


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
    return {
        "all_matched": all(matched for _, matched in measurements),
        "p95_seconds": p95_seconds,
        "peak_kib": _peak_rss_kib(),
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
