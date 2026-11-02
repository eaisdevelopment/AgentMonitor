"""Exercise a fresh build from an actual disposable checkout and toolchain."""

import subprocess
from pathlib import Path

import pytest

from tools.automation.implementations.auto_m6_local_activate import tree_digest
from tools.automation.implementations.m6_cutover import _check_candidate_schema
from tools.automation.implementations.m6_frontend_build import (
    FrontendBuildError,
    build_clean_frontend,
)


def test_real_clean_checkout_build_and_dirty_refusal(tmp_path: Path) -> None:
    source = Path("/home/dev/.local/share/agentmonitor/worktrees/m6-next")
    modules = Path(
        "/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules"
    )
    checkout = tmp_path / "checkout"
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    subprocess.run(
        [
            "/usr/bin/git",
            "clone",
            "--quiet",
            "--shared",
            "--no-hardlinks",
            str(source),
            str(checkout),
        ],
        check=True,
    )
    _check_candidate_schema(checkout)
    expected = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "HEAD"], cwd=checkout, text=True
    ).strip()
    revision, digest = build_clean_frontend(checkout, data, modules)
    assert revision == expected
    assert digest == tree_digest(checkout / "frontend/dist")
    assert not (checkout / "frontend/node_modules").exists()
    previous = (checkout / "frontend/dist").stat()
    assert build_clean_frontend(checkout, data, modules) == (revision, digest)
    retained = list((data / ".m6-frontend-builds").glob("build-*/dist"))
    assert len(retained) == 1
    old = retained[0].stat()
    assert (old.st_dev, old.st_ino) == (previous.st_dev, previous.st_ino)
    source_file = checkout / "frontend/vite.config.ts"
    source_file.rename(source_file.with_suffix(".moved"))
    with pytest.raises(FrontendBuildError, match="frontend_source_not_clean"):
        build_clean_frontend(checkout, data, modules)


def test_retained_candidate_survives_source_checkout_change(tmp_path: Path) -> None:
    from tools.automation.implementations.m6_candidate_release import (
        prepare_candidate_release,
        verify_candidate_release,
    )

    source = tmp_path / "source"
    releases = tmp_path / "releases"
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    subprocess.run(
        [
            "/usr/bin/git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            "/home/dev/.local/share/agentmonitor/worktrees/m6-cloud-final",
            str(source),
        ],
        check=True,
    )
    modules = Path(
        "/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules"
    )
    release, revision, digest = prepare_candidate_release(
        source, releases, data, modules
    )
    assert prepare_candidate_release(source, releases, data, modules) == (
        release,
        revision,
        digest,
    )
    (source / "frontend/vite.config.ts").rename(
        source / "frontend/vite.config.ts.changed"
    )
    assert verify_candidate_release(release, releases, revision, digest)
    assert not (release / "frontend/node_modules").exists()
    release_file = release / "frontend/vite.config.ts"
    release_file.chmod(0o600)
    with pytest.raises(RuntimeError, match="candidate_release_not_sealed"):
        verify_candidate_release(release, releases, revision, digest)
