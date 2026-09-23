"""Live ST-REG-001 reconciliation handoff point.

Status: NOT RUN. Task 3 must supply a current real ``DiscoveryOutcomeV1`` from
the approved Claude adapter. This module deliberately has no constructed
provider candidate, fixture, replay, seeded account, or passing live assertion.
"""

import pytest


@pytest.mark.skip(
    reason="NOT RUN: ST-CLA-001 must supply the real Claude DiscoveryOutcomeV1"
)
def test_real_claude_candidate_requires_owner_confirmation() -> None:
    """M02-LIVE-005: retained visibly as Not Run until Task 3 integration."""


@pytest.mark.skip(
    reason="NOT RUN: requires a real reconciled Claude candidate from ST-CLA-001"
)
def test_real_candidate_rejects_stale_version_or_changed_evidence() -> None:
    """M02-LIVE-006: no seeded candidate may substitute for real ambiguity."""


@pytest.mark.skip(
    reason="NOT RUN: requires a real confirmed Claude account/profile/resource graph"
)
def test_real_monitoring_graph_enrollment_replays_receipt_and_history() -> None:
    """M02-LIVE-004: no seeded graph may substitute for real enrollment."""
