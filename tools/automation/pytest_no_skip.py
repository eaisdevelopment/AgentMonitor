"""Fail a pytest process when any selected case is skipped or xfailed."""

from __future__ import annotations

from typing import Any

_SKIPPED_NODE_IDS: set[str] = set()


def _record_skipped(report: Any) -> None:
    if report.skipped:
        _SKIPPED_NODE_IDS.add(str(report.nodeid))


def pytest_collectreport(report: Any) -> None:
    """Record modules skipped during collection."""
    _record_skipped(report)


def pytest_runtest_logreport(report: Any) -> None:
    """Record tests skipped or xfailed in any runtest phase."""
    _record_skipped(report)


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Turn an otherwise green session with skips into a failed session."""
    if not _SKIPPED_NODE_IDS:
        return
    count = len(_SKIPPED_NODE_IDS)
    noun = "test is" if count == 1 else "tests are"
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(
            f"AUTO-M3-TEST skip policy: {count} skipped {noun} prohibited",
            red=True,
            bold=True,
        )
    if exitstatus == 0:
        session.exitstatus = 1
