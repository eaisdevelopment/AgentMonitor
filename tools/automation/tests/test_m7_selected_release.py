"""Retain the requested real checkout/revision without touching a service."""

import subprocess
from pathlib import Path

import pytest

from tools.automation.implementations.m6_candidate_release import (
    CandidateReleaseError,
    prepare_candidate_release,
    verify_candidate_release,
)
from tools.automation.implementations.m6_cutover import (
    CutoverError,
    _selected_cutover_source,
    cutover,
    update_current_schema,
)

ROOT = Path(__file__).resolve().parents[3]
MODULES = Path(
    "/home/dev/.local/share/agentmonitor/worktrees/"
    "dashboard-product-promotion/frontend/node_modules"
)


@pytest.fixture
def checkout(tmp_path: Path) -> tuple[Path, str, str]:
    source = tmp_path / "selected"
    subprocess.run(
        ["/usr/bin/git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(source)],
        check=True,
        capture_output=True,
    )
    revisions = subprocess.check_output(
        ["/usr/bin/git", "rev-list", "--max-count=2", "HEAD"], cwd=source, text=True
    ).splitlines()
    return source, revisions[0], revisions[1]


def test_wrong_real_revision_refused_before_release_files(
    tmp_path: Path, checkout: tuple[Path, str, str]
) -> None:
    source, _, parent = checkout
    releases = tmp_path / "releases"
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    with pytest.raises(
        CandidateReleaseError, match="candidate_release_revision_mismatch"
    ):
        prepare_candidate_release(
            source, releases, data, MODULES, expected_revision=parent
        )
    assert not releases.exists()
    assert list(data.iterdir()) == []


def test_selected_real_revision_build_is_retained_and_reused(
    tmp_path: Path, checkout: tuple[Path, str, str]
) -> None:
    source, expected, parent = checkout
    releases = tmp_path / "releases"
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    release, revision, digest = prepare_candidate_release(
        source, releases, data, MODULES, expected_revision=expected
    )
    assert revision == expected
    assert verify_candidate_release(release, releases, expected, digest)
    assert prepare_candidate_release(
        source, releases, data, MODULES, expected_revision=expected
    ) == (release, expected, digest)
    with pytest.raises(
        CandidateReleaseError, match="candidate_release_revision_mismatch"
    ):
        prepare_candidate_release(
            source, releases, data, MODULES, expected_revision=parent
        )
    assert list(releases.iterdir()) == [release]
    assert not (source / "frontend/node_modules").exists()


def test_selected_checkout_alias_is_refused(
    tmp_path: Path, checkout: tuple[Path, str, str]
) -> None:
    source, revision, _ = checkout
    alias = tmp_path / "alias"
    alias.symlink_to(source, target_is_directory=True)
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    with pytest.raises(
        CandidateReleaseError, match="candidate_release_selection_invalid"
    ):
        prepare_candidate_release(
            alias, tmp_path / "releases", data, MODULES, expected_revision=revision
        )
    assert not (tmp_path / "releases").exists()


@pytest.mark.parametrize("activate", [cutover, update_current_schema])
def test_activation_rejects_wrong_revision_before_installed_transition(
    checkout: tuple[Path, str, str], activate: object
) -> None:
    source, _, parent = checkout
    assert callable(activate)
    with pytest.raises(CutoverError, match="candidate_revision_mismatch"):
        activate(candidate=source, expected_revision=parent)


def test_source_selection_uses_actual_checkout_and_requires_both_fields(
    checkout: tuple[Path, str, str],
) -> None:
    source, revision, _ = checkout
    assert _selected_cutover_source(source, revision) == source
    with pytest.raises(CutoverError, match="cutover_selection_invalid"):
        _selected_cutover_source(source, None)
    with pytest.raises(CutoverError, match="cutover_selection_invalid"):
        _selected_cutover_source(None, revision)
    (source / "AGENTS.md").rename(source / "AGENTS.changed")
    with pytest.raises(CutoverError, match="candidate_checkout_not_clean"):
        _selected_cutover_source(source, revision)
