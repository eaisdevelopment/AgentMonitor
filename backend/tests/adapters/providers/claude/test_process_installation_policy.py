"""Bounded Claude process-installation policy without provider profile access."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.claude import installation


def test_real_oversized_version_banner_is_stopped_at_the_output_limit() -> None:
    """A real subprocess cannot make the version probe buffer unbounded output."""
    executable = shutil.which("bash")
    assert executable is not None

    with pytest.raises(
        installation.ClaudeInstallationUnavailable,
        match="^claude_version_output_too_large$",
    ):
        installation._read_version(Path(executable))


def test_native_version_candidate_selection_is_bounded_and_name_safe() -> None:
    """Only a bounded prefix and bounded semantic-version names are considered."""
    consumed = 0

    def entries() -> Iterator[Path]:
        nonlocal consumed
        for patch in range(400):
            consumed += 1
            yield Path(f"2.1.{patch}")

    select = getattr(installation, "_bounded_native_version_candidates", None)
    assert callable(select)
    candidates, truncated = select(entries(), default_executable=None)

    assert truncated is True
    assert len(candidates) == 32
    assert consumed <= 257
    assert all(len(item.name) <= 20 for item in candidates)

    long_component = Path("9" * 10_000 + ".1.1")
    candidates, truncated = select(
        (long_component, Path("2.1.296")), default_executable=None
    )
    assert candidates == (Path("2.1.296"),)
    assert truncated is True
