"""Pure decision rules for a dashboard update; no service is touched."""

from tools.automation.implementations.m6_local_update_policy import update_preflight


def test_update_requires_distinct_unchanged_baseline_and_candidate():
    baseline = ("/old", "old-digest")
    candidate = ("/new", "new-digest")
    assert update_preflight(baseline, baseline, candidate, candidate, True)
    assert not update_preflight(baseline, ("/old", "changed"), candidate, candidate, True)
    assert not update_preflight(baseline, baseline, candidate, ("/new", "changed"), True)
    assert not update_preflight(baseline, baseline, baseline, baseline, True)
    assert not update_preflight(baseline, baseline, candidate, candidate, False)
    assert not update_preflight(("", ""), ("", ""), candidate, candidate, True)
