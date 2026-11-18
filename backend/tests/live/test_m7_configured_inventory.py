"""Actual configured resources, with no owner setup or source request."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1

from backend.tests.live.m7_inventory_verification import inspect_configured_inventory


def test_real_configured_financial_inventory_has_current_retained_coverage() -> None:
    root = Path("/home/dev/.local/share/agentmonitor")
    try:
        evidence = inspect_configured_inventory(
            DatabaseRefV1(root / "agentmonitor.db", root), datetime.now(UTC)
        )
    except ValueError as error:
        code = str(error)
        pytest.fail(
            code
            if code.startswith("m7_inventory_")
            else "m7_inventory_read_unavailable",
            pytrace=False,
        )
    print("M7_CONFIGURED_INVENTORY " + json.dumps(asdict(evidence), sort_keys=True))
    if evidence.missing_provider_lanes:
        pytest.fail("m7_inventory_required_provider_coverage_missing", pytrace=False)
    if evidence.reasons:
        pytest.fail("m7_inventory_active_resource_coverage_incomplete", pytrace=False)
