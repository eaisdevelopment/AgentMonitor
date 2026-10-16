"""Policy and real-filesystem checks for the M5 Codex alert witness."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.automation._m5_test_git import (
    attached_real_checkout_v1,
    git_status_v1,
)
from tools.automation.implementations import m5_codex_alert_witness
from tools.automation.implementations.m5_codex_alert_witness import (
    BROWSER_PROOF_SCHEMA,
    M5CodexAlertWitnessErrorV1,
    _revalidate_runtime_binding_v1,
    _select_runtime_binding_v1,
    _unlink_created_witness_v1,
    _validate_browser_proof,
    _validate_created_witness_v1,
    _write_create_once,
)
from tools.automation.implementations.m5_service_activation import (
    candidate_for_checkout_v1,
)

REVISION = "a" * 40
DIGEST_A = "b" * 64
DIGEST_B = "c" * 64
RECOVERED_AT = datetime(2026, 10, 7, 10, 3, tzinfo=UTC)


def test_alert_selection_rejects_a_real_attached_checkout_before_runtime_io() -> None:
    with attached_real_checkout_v1() as checkout:
        before = git_status_v1(checkout)
        with pytest.raises(
            M5CodexAlertWitnessErrorV1,
            match="m5_alert_witness_checkout_invalid",
        ):
            _select_runtime_binding_v1({}, checkout_root=checkout)
        assert before == git_status_v1(checkout) == ""


def test_alert_prewrite_recheck_rejects_an_attached_checkout_before_io() -> None:
    with attached_real_checkout_v1() as checkout:
        candidate = candidate_for_checkout_v1(
            source_revision=REVISION,
            checkout_root=checkout,
        )
        with pytest.raises(
            M5CodexAlertWitnessErrorV1,
            match="m5_alert_witness_context_changed",
        ):
            _revalidate_runtime_binding_v1(
                candidate,
                expected_revision=REVISION,
                selected_pid=321,
                selected_start_time_ticks=654,
                dashboard_origin="http://127.0.0.1:43110",
                dashboard_cdp_endpoint="http://127.0.0.1:9222",
                checkout_root=checkout,
            )
        assert git_status_v1(checkout) == ""


def test_source_observation_pagination_requires_a_terminal_page() -> None:
    advance = m5_codex_alert_witness._next_source_observation_cursor_v1

    assert advance(has_more=False, next_key=None, after="current") is None
    assert advance(has_more=True, next_key="next", after="current") == "next"
    for next_key, after in ((None, "current"), ("current", "current")):
        with pytest.raises(
            M5CodexAlertWitnessErrorV1,
            match="m5_alert_witness_source_observation_incomplete",
        ):
            advance(has_more=True, next_key=next_key, after=after)


@dataclass(frozen=True, slots=True)
class _OpaqueIdProjection:
    value: str


@dataclass(frozen=True, slots=True)
class _AlertProjection:
    alert_id: _OpaqueIdProjection
    record_version: int


@dataclass(frozen=True, slots=True)
class _RecoveredProjection:
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class _LifecycleProjection:
    account_id: _OpaqueIdProjection
    alert: _AlertProjection
    history_digest: str
    recovered: _RecoveredProjection


def _proof() -> dict[str, object]:
    return {
        "schema": BROWSER_PROOF_SCHEMA,
        "implementation_revision": REVISION,
        "service_source_revision": REVISION,
        "service_pid": 321,
        "service_start_time_ticks": 654,
        "account_id": "account-one",
        "alert_id": "alert-one",
        "presented_at": "2026-10-07T10:04:00Z",
        "browser_presented": True,
        "alert_record_version": 4,
        "history_digest": DIGEST_A,
        "service_checked_at": "2026-10-07T10:03:30Z",
        "service_versions_digest": DIGEST_B,
        "registry_digest_scope": "all-public-registry-fields-v1",
        "registry_digest_before": DIGEST_A,
        "registry_digest_after": DIGEST_A,
        "mutations": 0,
    }


def _lifecycle() -> _LifecycleProjection:
    return _LifecycleProjection(
        account_id=_OpaqueIdProjection("account-one"),
        alert=_AlertProjection(_OpaqueIdProjection("alert-one"), 4),
        history_digest=DIGEST_A,
        recovered=_RecoveredProjection(RECOVERED_AT),
    )


def test_alert_browser_proof_binds_exact_running_service_revision() -> None:
    result = _validate_browser_proof(
        _proof(),
        _lifecycle(),
        revision=REVISION,
        service_pid=321,
        service_start_time_ticks=654,
    )

    assert result[-1] == REVISION

    for unavailable in (None, "9" * 40):
        changed = _proof()
        changed["service_source_revision"] = unavailable
        with pytest.raises(
            M5CodexAlertWitnessErrorV1,
            match="m5_alert_witness_browser_proof_invalid",
        ):
            _validate_browser_proof(
                changed,
                _lifecycle(),
                revision=REVISION,
                service_pid=321,
                service_start_time_ticks=654,
            )

    missing = _proof()
    del missing["service_source_revision"]
    with pytest.raises(
        M5CodexAlertWitnessErrorV1,
        match="m5_alert_witness_browser_proof_invalid",
    ):
        _validate_browser_proof(
            missing,
            _lifecycle(),
            revision=REVISION,
            service_pid=321,
            service_start_time_ticks=654,
        )


@pytest.mark.parametrize(
    "field",
    ("service_pid", "service_start_time_ticks", "alert_record_version", "mutations"),
)
def test_alert_browser_proof_rejects_booleans_for_integer_fields(field: str) -> None:
    proof = _proof()
    lifecycle = _lifecycle()
    service_pid = 321
    service_start_time_ticks = 654
    if field == "service_pid":
        service_pid = 1
    elif field == "service_start_time_ticks":
        service_start_time_ticks = 1
    elif field == "alert_record_version":
        lifecycle = _LifecycleProjection(
            account_id=lifecycle.account_id,
            alert=_AlertProjection(lifecycle.alert.alert_id, 1),
            history_digest=lifecycle.history_digest,
            recovered=lifecycle.recovered,
        )
    proof[field] = field != "mutations"

    with pytest.raises(
        M5CodexAlertWitnessErrorV1,
        match="m5_alert_witness_browser_proof_invalid",
    ):
        _validate_browser_proof(
            proof,
            lifecycle,
            revision=REVISION,
            service_pid=service_pid,
            service_start_time_ticks=service_start_time_ticks,
        )


def test_alert_witness_writer_creates_exact_private_file(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "m5-alert-witness.json"

    digest = _write_create_once(path, {"proof": True})

    metadata = path.lstat()
    assert len(digest) == 64
    assert stat.S_ISREG(metadata.st_mode)
    assert metadata.st_uid == os.getuid()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    assert metadata.st_nlink == 1
    assert path.read_bytes() == b'{\n  "proof": true\n}\n'


def _opened_created_file(path: Path) -> tuple[int, int, os.stat_result]:
    parent_descriptor = os.open(
        path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    descriptor = os.open(path.name, os.O_RDWR | os.O_NOFOLLOW, dir_fd=parent_descriptor)
    return parent_descriptor, descriptor, os.fstat(descriptor)


def test_alert_witness_created_file_validation_rejects_mode_change(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "m5-alert-witness.json"
    path.write_bytes(b"{}\n")
    path.chmod(0o600)
    parent_descriptor, descriptor, created = _opened_created_file(path)
    path.chmod(0o400)

    try:
        with pytest.raises(OSError):
            _validate_created_witness_v1(
                path,
                descriptor,
                parent_descriptor,
                device=created.st_dev,
                inode=created.st_ino,
            )
    finally:
        os.close(descriptor)
        os.close(parent_descriptor)


def test_alert_witness_created_file_validation_rejects_an_added_hardlink(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "m5-alert-witness.json"
    path.write_bytes(b"{}\n")
    path.chmod(0o600)
    parent_descriptor, descriptor, created = _opened_created_file(path)
    os.link(path, tmp_path / "retained-created-inode")

    try:
        with pytest.raises(OSError):
            _validate_created_witness_v1(
                path,
                descriptor,
                parent_descriptor,
                device=created.st_dev,
                inode=created.st_ino,
            )
    finally:
        os.close(descriptor)
        os.close(parent_descriptor)


def test_alert_witness_cleanup_never_unlinks_a_substituted_path(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "m5-alert-witness.json"
    displaced_inode = tmp_path / "displaced-created-inode"
    replacement = b"replacement must remain\n"
    path.write_bytes(b"created inode\n")
    path.chmod(0o600)
    parent_descriptor = os.open(
        tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    created = path.stat()
    path.rename(displaced_inode)
    path.write_bytes(replacement)
    path.chmod(0o600)

    try:
        _unlink_created_witness_v1(
            path,
            parent_descriptor,
            device=created.st_dev,
            inode=created.st_ino,
        )
    finally:
        os.close(parent_descriptor)

    assert path.read_bytes() == replacement
    assert displaced_inode.exists()
