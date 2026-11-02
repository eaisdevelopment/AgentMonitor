"""Disposable real systemd processes only; never touch the dashboard unit."""

import subprocess
import uuid

from tools.automation.implementations.m6_quiescent_stop import stop_quiescent_unit


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
    try:
        assert stop_quiescent_unit(unit) == "stopped"
        state = subprocess.run(
            ["systemctl", "--user", "show", unit, "-p", "MainPID", "-p", "NRestarts"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "MainPID=0" in state and "NRestarts=0" in state
    finally:
        subprocess.run(
            ["systemctl", "--user", "stop", unit], capture_output=True, check=False
        )


def test_unit_with_real_child_is_refused_and_main_is_resumed() -> None:
    import time
    from pathlib import Path

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
            stop_quiescent_unit(unit)
        state = next(
            line
            for line in Path(f"/proc/{pid}/status").read_text().splitlines()
            if line.startswith("State:")
        )
        assert state.split()[1] not in {"T", "t"}
    finally:
        subprocess.run(
            ["systemctl", "--user", "stop", unit], capture_output=True, check=False
        )


def test_child_created_by_worker_thread_is_refused() -> None:
    import time
    from pathlib import Path

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
            stop_quiescent_unit(unit)
    finally:
        subprocess.run(
            ["systemctl", "--user", "stop", unit], capture_output=True, check=False
        )
