"""ST-OBS-001 executable live-run availability declaration.

M04-LIVE-004/009..011 are Blocked/Not Run: the accepted Claude collector tuple
is unavailable for the current provider version/workspace.  This module
collects one explicit Not Run result and no synthetic substitute.
"""

import pytest

BLOCKED_SCENARIOS = (
    "M04-LIVE-004",
    "M04-LIVE-009",
    "M04-LIVE-010",
    "M04-LIVE-011",
)


@pytest.mark.skip(
    reason=(
        "BLOCKED / NOT RUN: accepted Claude tuple requires an owner-approved "
        "workspace trust interaction before the real collection can execute"
    )
)
def test_real_claude_quota_collection_requires_available_workspace() -> None:
    """M04-LIVE-004/009..011: never substitute constructed provider output."""
