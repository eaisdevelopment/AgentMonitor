"""Disposable real systemd processes only; never touch the dashboard unit."""

import subprocess
import uuid
from pathlib import Path

from tools.automation.implementations.m6_quiescent_stop import (
    _process_identity,
    _properties,
    stop_quiescent_unit,
)


def _bound(unit: str) -> dict:
    props = _properties(unit)
    pid = int(props["MainPID"])
    identity = _process_identity(pid, props["ControlGroup"])
    return {
        "expected_pid": pid,
        "expected_cgroup": props["ControlGroup"],
        "expected_start_ticks": identity[0],
        "expected_executable_identity": identity[1:],
        "expected_invocation_id": props["InvocationID"],
        "expected_start_monotonic": props["ExecMainStartTimestampMonotonic"],
    }


def _arm(unit: str) -> Path:
    directory = Path.home() / ".config/systemd/user" / (unit + ".d")
    directory.mkdir(mode=0o700)
    guard = directory / "90-test.conf"
    guard.write_text("[Unit]\nRefuseManualStart=yes\n[Service]\nRestart=no\n")
    guard.chmod(0o600)
    subprocess.run(
        ["systemctl", "--user", "daemon-reload"], check=True, capture_output=True
    )
    return directory


def _cleanup(unit: str, directory: Path) -> None:
    subprocess.run(
        ["systemctl", "--user", "stop", unit], capture_output=True, check=False
    )
    (directory / "90-test.conf").unlink(missing_ok=True)
    directory.rmdir()
    subprocess.run(
        ["systemctl", "--user", "daemon-reload"], capture_output=True, check=False
    )


def test_stopped_unit_is_killed_without_automatic_restart() -> None:
    unit = f"agentmonitor-cutover-test-{uuid.uuid4().hex}.service"
    result = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--unit",
            unit,
            "--property=Restart=no",
            "/bin/sleep",
            "60",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    directory = _arm(unit)
    try:
        assert stop_quiescent_unit(unit, **_bound(unit)).unit == unit
        state = subprocess.run(
            ["systemctl", "--user", "show", unit, "-p", "MainPID", "-p", "NRestarts"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "MainPID=0" in state and "NRestarts=0" in state
    finally:
        _cleanup(unit, directory)


def test_unit_with_real_child_is_refused_and_main_is_resumed() -> None:
    import time

    import pytest

    from tools.automation.implementations.m6_quiescent_stop import QuiescentStopError

    unit = f"agentmonitor-cutover-test-{uuid.uuid4().hex}.service"
    result = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--unit",
            unit,
            "--property=Restart=no",
            "/bin/bash",
            "-c",
            "sleep 60 & wait",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    directory = _arm(unit)
    try:
        info = subprocess.run(
            ["systemctl", "--user", "show", unit, "-p", "MainPID", "--value"],
            capture_output=True,
            text=True,
            check=True,
        )
        pid = int(info.stdout.strip())
        children = Path(f"/proc/{pid}/task/{pid}/children")
        deadline = time.monotonic() + 3
        while not children.read_text().strip() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert children.read_text().strip()
        with pytest.raises(
            QuiescentStopError, match="unit_has_children_or_not_stopped"
        ):
            stop_quiescent_unit(unit, **_bound(unit))
        state = next(
            line
            for line in Path(f"/proc/{pid}/status").read_text().splitlines()
            if line.startswith("State:")
        )
        assert state.split()[1] not in {"T", "t"}
    finally:
        _cleanup(unit, directory)


def test_child_created_by_worker_thread_is_refused() -> None:
    import time

    import pytest

    from tools.automation.implementations.m6_quiescent_stop import QuiescentStopError

    unit = f"agentmonitor-cutover-test-{uuid.uuid4().hex}.service"
    code = (
        "import subprocess,threading,time; "
        "threading.Thread(target=lambda:(subprocess.Popen(['/bin/sleep','60']),time.sleep(60))).start(); "
        "time.sleep(60)"
    )
    result = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--unit",
            unit,
            "--property=Restart=no",
            "/usr/bin/python3",
            "-c",
            code,
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    directory = _arm(unit)
    try:
        pid = int(
            subprocess.run(
                ["systemctl", "--user", "show", unit, "-p", "MainPID", "--value"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        root = Path(f"/proc/{pid}/task")
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            tasks = list(root.iterdir())
            if any(
                task.name != str(pid) and (task / "children").read_text().strip()
                for task in tasks
            ):
                break
            time.sleep(0.02)
        else:
            raise AssertionError("worker child not observed")
        assert not (root / str(pid) / "children").read_text().strip()
        with pytest.raises(
            QuiescentStopError, match="unit_has_children_or_not_stopped"
        ):
            stop_quiescent_unit(unit, **_bound(unit))
    finally:
        _cleanup(unit, directory)


def test_manual_start_block_is_required_before_freezing() -> None:
    import pytest

    from tools.automation.implementations.m6_quiescent_stop import QuiescentStopError

    unit = f"agentmonitor-cutover-test-{uuid.uuid4().hex}.service"
    result = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--unit",
            unit,
            "--property=Restart=no",
            "/bin/sleep",
            "60",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    try:
        with pytest.raises(QuiescentStopError, match="unit_not_quiescent_ready"):
            stop_quiescent_unit(unit, **_bound(unit))
        result = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "active"
    finally:
        subprocess.run(
            ["systemctl", "--user", "stop", unit], capture_output=True, check=False
        )


def test_mismatched_real_invocation_identity_never_stops_target() -> None:
    import time

    import pytest

    from tools.automation.implementations.m6_quiescent_stop import QuiescentStopError

    first = f"agentmonitor-cutover-test-{uuid.uuid4().hex}.service"
    second = f"agentmonitor-cutover-test-{uuid.uuid4().hex}.service"
    directories = []
    try:
        for unit, executable in ((first, "/bin/sleep"), (second, "/usr/bin/tail")):
            result = subprocess.run(
                [
                    "systemd-run",
                    "--user",
                    "--unit",
                    unit,
                    "--property=Restart=no",
                    executable,
                    "60" if executable.endswith("sleep") else "-f",
                    *([] if executable.endswith("sleep") else ["/dev/null"]),
                ],
                capture_output=True,
                check=False,
            )
            assert result.returncode == 0
            directories.append(_arm(unit))
            time.sleep(0.05)
        expected = _bound(first)
        other = _bound(second)
        for name in (
            "expected_pid",
            "expected_cgroup",
            "expected_start_ticks",
            "expected_executable_identity",
            "expected_invocation_id",
            "expected_start_monotonic",
        ):
            assert expected[name] != other[name]
            mismatched = {**expected, name: other[name]}
            with pytest.raises(QuiescentStopError):
                stop_quiescent_unit(first, **mismatched)
            pid = expected["expected_pid"]
            state = next(
                line
                for line in Path(f"/proc/{pid}/status").read_text().splitlines()
                if line.startswith("State:")
            )
            assert state.split()[1] not in {"T", "t"}
            assert _properties(first)["ActiveState"] == "active"
    finally:
        for unit, directory in zip((first, second), directories, strict=False):
            _cleanup(unit, directory)
