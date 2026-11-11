"""Real Git admission and rejected CLI calls; never activate an installed service."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WRAPPERS = (
    "auto_m6_cutover",
    "auto_m6_current_update",
    "auto_m6_recover_current_update",
)


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["/usr/bin/git", *arguments],
        cwd=root,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(root), "LANG": "C"},
        stderr=subprocess.DEVNULL,
    ).strip()


@pytest.fixture(params=WRAPPERS)
def controller(tmp_path: Path, request: pytest.FixtureRequest):
    checkout = tmp_path / "controller"
    subprocess.run(
        [
            "/usr/bin/git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            str(ROOT),
            str(checkout),
        ],
        check=True,
        capture_output=True,
    )
    name = request.param
    relative = Path("tools/automation/implementations") / (name + ".py")
    (checkout / relative).write_bytes((ROOT / relative).read_bytes())
    git(checkout, "add", str(relative))
    git(
        checkout,
        "-c",
        "user.name=Controller test",
        "-c",
        "user.email=controller@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--allow-empty",
        "-m",
        "Test current controller source",
    )
    revision = git(checkout, "rev-parse", "HEAD")
    spec = importlib.util.spec_from_file_location(name, checkout / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Importing a controller performs no service/runtime action.
    spec.loader.exec_module(module)
    return checkout, revision, module, checkout / relative


def test_exact_revision_admits_own_real_clean_checkout(controller) -> None:
    checkout, revision, module, _ = controller
    assert module._ROOT == checkout
    assert module._admitted_revision(["--expected-revision=" + revision]) == revision
    assert git(checkout, "status", "--porcelain") == ""


def test_valid_but_different_revision_is_rejected(controller) -> None:
    checkout, _, module, _ = controller
    previous = git(checkout, "rev-parse", "HEAD^")
    with pytest.raises(RuntimeError, match="operator_checkout_revision_mismatch"):
        module._admitted_revision(["--expected-revision=" + previous])


def test_selected_dirty_checkout_is_rejected(controller) -> None:
    checkout, revision, module, _ = controller
    (checkout / "AGENTS.md").write_text("changed during selection\n")
    with pytest.raises(RuntimeError, match="operator_checkout_not_clean"):
        module._admitted_revision(["--expected-revision=" + revision])


def test_unselected_other_checkout_remains_rejected(controller) -> None:
    _, _, module, _ = controller
    with pytest.raises(RuntimeError, match="operator_fixed_checkout_required"):
        module._admitted_revision([])


@pytest.mark.parametrize(
    "arguments",
    [
        ["--expected-revision=bad"],
        ["--unit=another.service"],
        ["--expected-revision=" + "a" * 40, "--data-root=/tmp/elsewhere"],
    ],
)
def test_invalid_cli_selection_exits_without_activation(controller, arguments) -> None:
    checkout, _, _, script = controller
    result = subprocess.run(
        [sys.executable, "-B", str(script), *arguments],
        cwd=checkout,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(checkout),
            "LANG": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 3
    assert "BLOCKED" in result.stdout
    assert "no target arguments are accepted" in result.stdout
    assert result.stderr == ""
