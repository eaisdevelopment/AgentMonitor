"""Pure and real-filesystem guards for the safe current M3 exit command."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.automation.implementations.auto_m3_current_exit import (
    LOCAL_ROUTINES,
    PRE_BROWSER_ROUTINES,
    RECEIPT_BASENAME,
    RECEIPT_DIRECTORY_NAME,
    REQUIRED_LANES,
    M3CurrentExitErrorV1,
    ServiceProcessV1,
    _process_start_ticks,
    _stop_spawned_service,
    build_passed_receipt_v1,
    is_exact_service_ready_event_v1,
    parse_service_command_v1,
    start_service_output_drainer_v1,
    validate_browser_transition_v1,
    write_private_receipt_v1,
    write_verified_receipt_v1,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION = "a" * 40
DIGEST = "b" * 64
STARTED = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)


def _lane_evidence() -> dict[str, str]:
    return {lane: f"{lane}_passed" for lane in REQUIRED_LANES}


def test_canonical_m3_exit_selects_read_only_successor() -> None:
    catalog = tomllib.loads((ROOT / "tools/automation/routines.toml").read_text())
    routine = next(item for item in catalog["routines"] if item["id"] == "AUTO-M3-EXIT")

    assert routine["implementation_command"] == [
        "backend/.venv/bin/python",
        "tools/automation/implementations/auto_m3_current_exit.py",
    ]
    assert LOCAL_ROUTINES == (
        ("technical_suite", "AUTO-M3-TEST"),
        ("quality", "AUTO-QUALITY"),
        ("mutation", "AUTO-MUTATION"),
        ("documentation", "AUTO-DOCS-CHECK"),
        ("git_preflight", "AUTO-GIT-PREFLIGHT"),
    )
    assert PRE_BROWSER_ROUTINES == (("build", "AUTO-BUILD"),)


def test_passed_receipt_requires_every_exact_lane() -> None:
    receipt = build_passed_receipt_v1(
        implementation_revision=REVISION,
        started_at=STARTED,
        completed_at=STARTED + timedelta(minutes=2),
        selected_account_digest=DIGEST,
        lane_evidence=_lane_evidence(),
    )

    assert receipt["status"] == "passed"
    assert receipt["exit_code"] == 0
    assert receipt["skips"] == []
    assert {item["lane_id"] for item in receipt["required_lanes"]} == set(
        REQUIRED_LANES
    )

    missing = _lane_evidence()
    missing.pop("current_browser")
    with pytest.raises(M3CurrentExitErrorV1, match="m3_current_lane_set_invalid"):
        build_passed_receipt_v1(
            implementation_revision=REVISION,
            started_at=STARTED,
            completed_at=STARTED + timedelta(minutes=2),
            selected_account_digest=DIGEST,
            lane_evidence=missing,
        )


def test_receipt_is_written_as_private_real_file() -> None:
    receipt = build_passed_receipt_v1(
        implementation_revision=REVISION,
        started_at=STARTED,
        completed_at=STARTED + timedelta(minutes=2),
        selected_account_digest=DIGEST,
        lane_evidence=_lane_evidence(),
    )
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / RECEIPT_DIRECTORY_NAME
        directory.mkdir(mode=0o700)
        path = directory / RECEIPT_BASENAME
        write_private_receipt_v1(path, receipt)

        assert json.loads(path.read_text(encoding="utf-8")) == receipt
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        with pytest.raises(
            M3CurrentExitErrorV1, match="m3_current_receipt_path_invalid"
        ):
            write_private_receipt_v1(path, receipt)
        with pytest.raises(
            M3CurrentExitErrorV1, match="m3_current_receipt_path_invalid"
        ):
            write_private_receipt_v1(Path(raw) / ".env", receipt)


def test_service_restart_command_is_closed_and_bound_to_browser_origin() -> None:
    command = (
        str(ROOT / "backend/.venv/bin/python"),
        "-m",
        "agentmonitor.composition.bootstrap",
        "--config",
        "/owner/agentmonitor/service.env",
        "--data-root",
        "/owner/agentmonitor",
        "--host",
        "127.0.0.1",
        "--port",
        "43110",
        "--authenticated-dashboard",
        "--lan-host",
        "192.168.1.18",
        "--lan-network",
        "192.168.1.0/24",
    )

    launch = parse_service_command_v1(command, "http://127.0.0.1:43110")

    assert launch.host == "127.0.0.1"
    assert launch.port == 43110
    assert launch.data_root == Path("/owner/agentmonitor")
    assert launch.command[0] == str(ROOT / "backend/.venv/bin/python")
    for invalid in (
        (*command, "--unexpected"),
        tuple("43111" if item == "43110" else item for item in command),
    ):
        with pytest.raises(
            M3CurrentExitErrorV1, match="m3_current_service_command_invalid"
        ):
            parse_service_command_v1(invalid, "http://127.0.0.1:43110")


def test_service_readiness_requires_exact_child_event_and_origin() -> None:
    origin = "http://127.0.0.1:43110"
    assert is_exact_service_ready_event_v1({"event": "ready", "origin": origin}, origin)
    assert not is_exact_service_ready_event_v1(
        {"event": "ready", "origin": "http://127.0.0.1:43111"}, origin
    )
    assert not is_exact_service_ready_event_v1(
        {"event": "ready", "origin": origin, "pid": 123}, origin
    )


def test_service_output_is_continuously_drained_without_a_file() -> None:
    read_descriptor, write_descriptor = os.pipe()
    read_stream = os.fdopen(read_descriptor, "rb", buffering=0)
    drainer = start_service_output_drainer_v1(read_stream)
    read_stream.close()
    try:
        os.write(write_descriptor, b"runtime output that must be discarded\n" * 1024)
    finally:
        os.close(write_descriptor)

    assert drainer.wait(timeout=10) == 0


def test_gate_owned_service_cleanup_escalates_and_confirms_exit() -> None:
    process = subprocess.Popen(
        [
            str(ROOT / "backend/.venv/bin/python"),
            "-c",
            (
                "import signal,time\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                "print('ready', flush=True)\n"
                "time.sleep(30)\n"
            ),
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdout is not None
    assert process.stdout.readline() == b"ready\n"
    pidfd = os.pidfd_open(process.pid)
    try:
        assert _stop_spawned_service(
            process,
            pidfd,
            graceful_timeout=0.05,
            kill_timeout=2,
        )
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process.stdout.close()
        os.close(pidfd)


def test_browser_transition_requires_same_private_metadata_digest() -> None:
    preflight = {
        "selected_account_digest": DIGEST,
        "selected_account_metadata_digest": "c" * 64,
        "identity_match": True,
        "registry_unchanged": True,
        "mutations": 0,
    }
    witness = {
        "selected_account_digest": DIGEST,
        "selected_account_metadata_digest": "c" * 64,
        "collection_run_digest": "d" * 64,
        "identity_match": True,
        "registry_unchanged": True,
        "runtime_state": "available",
        "mutations": 0,
    }

    assert validate_browser_transition_v1(preflight, witness, DIGEST) == (
        "d" * 64,
        "available",
    )
    witness["selected_account_metadata_digest"] = "e" * 64
    with pytest.raises(
        M3CurrentExitErrorV1, match="m3_current_browser_metadata_changed"
    ):
        validate_browser_transition_v1(preflight, witness, DIGEST)


def test_receipt_write_is_bound_to_a_live_real_service_process() -> None:
    receipt = build_passed_receipt_v1(
        implementation_revision=REVISION,
        started_at=STARTED,
        completed_at=STARTED + timedelta(minutes=2),
        selected_account_digest=DIGEST,
        lane_evidence=_lane_evidence(),
    )
    process = subprocess.Popen(
        [str(ROOT / "backend/.venv/bin/python"), "-c", "import time; time.sleep(30)"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pidfd = os.pidfd_open(process.pid)
    service = ServiceProcessV1(process.pid, _process_start_ticks(process.pid), pidfd)
    try:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw) / RECEIPT_DIRECTORY_NAME
            directory.mkdir(mode=0o700)
            path = directory / RECEIPT_BASENAME
            write_verified_receipt_v1(service, path, receipt)
            assert path.exists()

        process.terminate()
        process.wait(timeout=10)
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw) / RECEIPT_DIRECTORY_NAME
            directory.mkdir(mode=0o700)
            path = directory / RECEIPT_BASENAME
            with pytest.raises(
                M3CurrentExitErrorV1, match="m3_current_service_changed"
            ):
                write_verified_receipt_v1(service, path, receipt)
            assert not path.exists()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        os.close(pidfd)
