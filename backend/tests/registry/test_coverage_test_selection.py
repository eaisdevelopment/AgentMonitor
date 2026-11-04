"""Pure test-selection policy; constructed IDs never reach an external port."""

import pytest

from backend.tests.integration.registry.test_coverage_persistence import (
    _select_eligible_coverage_account,
)


def test_multiple_eligible_accounts_select_stably_without_owner_input() -> None:
    candidates = (("account_b", True), ("account_a", True))
    assert _select_eligible_coverage_account(candidates) == "account_a"
    assert _select_eligible_coverage_account(tuple(reversed(candidates))) == "account_a"


def test_different_owner_outcome_is_not_selected() -> None:
    assert (
        _select_eligible_coverage_account((("account_a", False), ("account_b", True)))
        == "account_b"
    )


def test_no_eligible_owner_outcome_fails_closed() -> None:
    with pytest.raises(
        AssertionError, match="actual_eligible_coverage_account_unavailable"
    ):
        _select_eligible_coverage_account((("account_a", False),))


def test_duplicate_candidate_identity_fails_closed() -> None:
    with pytest.raises(
        AssertionError, match="actual_coverage_account_selection_duplicate"
    ):
        _select_eligible_coverage_account((("account_a", True), ("account_a", True)))
