"""Pure and real-filesystem guards for the current-revision M4 exit."""

from __future__ import annotations

import json
import stat
import tempfile
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.automation.implementations.auto_m3_current_exit import (
    ServiceLaunchV1,
    service_identity_matches_v1,
)
from tools.automation.implementations.auto_m4_current_exit import (
    LOCAL_ROUTINES,
    PRE_SERVICE_ROUTINES,
    RECEIPT_BASENAME,
    RECEIPT_DIRECTORY_NAME,
    REQUIRED_LANES,
    M4CurrentExitErrorV1,
    build_passed_receipt_v1,
    validate_fleet_transition_v1,
    write_private_receipt_v1,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION = "a" * 40
DIGEST_A = "b" * 64
DIGEST_B = "c" * 64
DIGEST_C = "d" * 64
STARTED = datetime(2026, 10, 3, 10, 0, tzinfo=UTC)


def _lane_evidence() -> dict[str, str]:
    return {lane: f"{lane}_passed" for lane in REQUIRED_LANES}


def _preflight() -> dict[str, object]:
    return {
        "event": "m4_fleet_preflight",
        "fleet_metadata_digest": DIGEST_A,
        "identity_set_digest": DIGEST_B,
        "collection_run_set_digest": DIGEST_C,
        "account_count": 6,
        "organization_count": 2,
        "distinct_identity_count": 6,
        "current_history_count": 6,
        "mutations": 0,
    }


def _witness() -> dict[str, object]:
    return {
        **_preflight(),
        "event": "m4_fleet_witness",
        "collection_run_set_digest": "e" * 64,
        "fresh_after_restart_count": 6,
    }


def test_catalog_selects_current_m4_exit_and_all_six_stories() -> None:
    catalog = tomllib.loads((ROOT / "tools/automation/routines.toml").read_text())
    routine = next(item for item in catalog["routines"] if item["id"] == "AUTO-M4-EXIT")

    assert routine["implementation_command"] == [
        "backend/.venv/bin/python",
        "-m",
        "tools.automation.implementations.auto_m4_current_exit",
    ]
    assert PRE_SERVICE_ROUTINES == (("build", "AUTO-BUILD"),)
    assert LOCAL_ROUTINES == (
        ("planning", "AUTO-PLAN-CHECK"),
        ("quality", "AUTO-QUALITY"),
        ("mutation", "AUTO-MUTATION"),
        ("documentation", "AUTO-DOCS-CHECK"),
        ("git_preflight", "AUTO-GIT-PREFLIGHT"),
    )


def test_m4_receipt_requires_exact_revision_lanes_and_zero_skips() -> None:
    receipt = build_passed_receipt_v1(
        implementation_revision=REVISION,
        started_at=STARTED,
        completed_at=STARTED + timedelta(minutes=8),
        owner_outcomes_digest=DIGEST_A,
        fleet_metadata_digest=DIGEST_B,
        identity_set_digest=DIGEST_C,
        test_count=257,
        lane_evidence=_lane_evidence(),
    )

    assert receipt["status"] == "passed"
    assert receipt["implementation_revision"] == REVISION
    assert receipt["test_count"] == 257
    assert receipt["skips"] == []
    assert receipt["account_count"] == 6
    assert receipt["organization_count"] == 2
    assert {item["lane_id"] for item in receipt["required_lanes"]} == set(
        REQUIRED_LANES
    )

    missing = _lane_evidence()
    missing.pop("fleet_browser")
    with pytest.raises(M4CurrentExitErrorV1, match="m4_current_lane_set_invalid"):
        build_passed_receipt_v1(
            implementation_revision=REVISION,
            started_at=STARTED,
            completed_at=STARTED,
            owner_outcomes_digest=DIGEST_A,
            fleet_metadata_digest=DIGEST_B,
            identity_set_digest=DIGEST_C,
            test_count=257,
            lane_evidence=missing,
        )


def test_m4_receipt_is_private_and_never_overwrites() -> None:
    receipt = build_passed_receipt_v1(
        implementation_revision=REVISION,
        started_at=STARTED,
        completed_at=STARTED + timedelta(minutes=8),
        owner_outcomes_digest=DIGEST_A,
        fleet_metadata_digest=DIGEST_B,
        identity_set_digest=DIGEST_C,
        test_count=257,
        lane_evidence=_lane_evidence(),
    )
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / RECEIPT_DIRECTORY_NAME
        directory.mkdir(mode=0o700)
        path = directory / RECEIPT_BASENAME
        write_private_receipt_v1(path, receipt)

        assert json.loads(path.read_text(encoding="utf-8")) == receipt
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        with pytest.raises(
            M4CurrentExitErrorV1, match="m4_current_receipt_path_invalid"
        ):
            write_private_receipt_v1(path, receipt)


def test_m4_transition_rejects_duplicate_wrong_or_old_identity_runs() -> None:
    assert validate_fleet_transition_v1(_preflight(), _witness()) == (
        DIGEST_A,
        DIGEST_B,
    )

    for field, value, reason in (
        ("distinct_identity_count", 5, "m4_current_fleet_preflight_invalid"),
        ("fleet_metadata_digest", "f" * 64, "m4_current_fleet_metadata_changed"),
        ("collection_run_set_digest", DIGEST_C, "m4_current_collection_not_fresh"),
        ("current_history_count", 5, "m4_current_fleet_witness_invalid"),
        ("fresh_after_restart_count", 5, "m4_current_fleet_witness_invalid"),
    ):
        witness = _witness()
        if field == "distinct_identity_count":
            preflight = _preflight()
            preflight[field] = value
            with pytest.raises(M4CurrentExitErrorV1, match=reason):
                validate_fleet_transition_v1(preflight, witness)
        else:
            witness[field] = value
            with pytest.raises(M4CurrentExitErrorV1, match=reason):
                validate_fleet_transition_v1(_preflight(), witness)


def test_m4_service_restart_identity_includes_start_time_and_private_root() -> None:
    expected = ServiceLaunchV1(
        ("python", "-m", "agentmonitor.composition.bootstrap"),
        Path("/owner/one/service.env"),
        Path("/owner/one"),
        "127.0.0.1",
        43110,
    )
    changed_root = ServiceLaunchV1(
        expected.command,
        Path("/owner/two/service.env"),
        Path("/owner/two"),
        expected.host,
        expected.port,
    )

    assert service_identity_matches_v1(expected, 100, expected, 100)
    assert not service_identity_matches_v1(expected, 100, expected, 101)
    assert not service_identity_matches_v1(expected, 100, changed_root, 100)
