"""Pure frozen request-correlation grammar, separate from resource IDs."""

from agentmonitor.modules.identity_access.domain.policy import valid_correlation_id


def test_correlation_accepts_exact_frozen_ascii_grammar_and_bounds() -> None:
    assert valid_correlation_id("a.b:c")
    assert valid_correlation_id("A0_-.:z")
    assert valid_correlation_id("x")
    assert valid_correlation_id("x" * 64)
    for invalid in ("", "x" * 65, "é", "x y", "x/y", "x\n", None, True):
        assert not valid_correlation_id(invalid)
