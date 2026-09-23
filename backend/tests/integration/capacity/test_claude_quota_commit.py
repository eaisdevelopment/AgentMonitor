"""ST-OBS-001 executable live capacity-commit availability declaration.

M05-DB-002..010/016..021 and M05-LIVE-001..006 require a fresh real provider
observation.  They are Blocked/Not Run for the current Claude tuple.  No
provider observation is fabricated, copied, replayed, or inserted here; the
module collects one explicit Not Run result.
"""

import pytest

BLOCKED_SCENARIOS = (
    "M05-DB-002..010",
    "M05-DB-016..021",
    "M05-LIVE-001..006",
)


@pytest.mark.skip(
    reason=(
        "BLOCKED / NOT RUN: no fresh real Claude quota observation is available "
        "until owner-approved workspace trust permits the live collector"
    )
)
def test_real_claude_quota_commit_requires_fresh_provider_observation() -> None:
    """M05-DB-002..010/016..021 and M05-LIVE-001..006 remain Not Run."""
