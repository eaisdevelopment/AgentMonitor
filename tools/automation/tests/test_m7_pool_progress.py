"""Closed browser progress identifies the failed step without exposing page data."""

import pytest

from frontend.tests.browser.m7.run_financial_pools import pool_progress_stage


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (None, "browser_boundary"),
        (b"M7 POOL STAGE: login\nM7 POOL STAGE: pagination\n", "pagination"),
        ("M7 POOL STAGE: owner_metadata\n", "owner_metadata"),
        ("M7 POOL STAGE: unknown_content\n", "browser_output_invalid"),
        ("unexpected output\n", "browser_output_invalid"),
        ("M7 POOL STAGE: login\nM7 FINANCIAL POOLS BROWSER: PASSED\n", "login"),
    ],
)
def test_pool_progress_is_closed(output: str | bytes | None, expected: str) -> None:
    assert pool_progress_stage(output) == expected
