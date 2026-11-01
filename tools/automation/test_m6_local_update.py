"""Pure decision rules for a dashboard update; no service is touched."""

from tools.automation.implementations.m6_local_update_policy import update_preflight


def test_update_requires_distinct_unchanged_baseline_and_candidate():
    baseline = ("/old", "old-digest")
    candidate = ("/new", "new-digest")
    assert update_preflight(baseline, baseline, candidate, candidate, True)
    assert not update_preflight(
        baseline, ("/old", "changed"), candidate, candidate, True
    )
    assert not update_preflight(
        baseline, baseline, candidate, ("/new", "changed"), True
    )
    assert not update_preflight(baseline, baseline, baseline, baseline, True)
    assert not update_preflight(baseline, baseline, candidate, candidate, False)
    assert not update_preflight(("", ""), ("", ""), candidate, candidate, True)


def test_atomic_override_replaces_only_the_expected_real_file(tmp_path):
    from tools.automation.implementations.auto_m6_local_update import replace_override

    target = tmp_path / "dashboard.conf"
    target.write_bytes(b"old configuration\n")
    target.chmod(0o600)
    assert replace_override(target, b"old configuration\n", b"new configuration\n")
    assert target.read_bytes() == b"new configuration\n"
    assert not replace_override(
        target, b"old configuration\n", b"other configuration\n"
    )
    assert target.read_bytes() == b"new configuration\n"


def test_override_can_be_restored_and_never_follows_a_symlink(tmp_path):
    from tools.automation.implementations.auto_m6_local_update import replace_override

    target = tmp_path / "dashboard.conf"
    target.write_bytes(b"original\n")
    target.chmod(0o600)
    assert replace_override(target, b"original\n", b"candidate\n")
    assert replace_override(target, b"candidate\n", b"original\n")
    assert target.read_bytes() == b"original\n"
    link = tmp_path / "link.conf"
    link.symlink_to(target)
    assert not replace_override(link, b"original\n", b"unexpected\n")
    assert target.read_bytes() == b"original\n"
