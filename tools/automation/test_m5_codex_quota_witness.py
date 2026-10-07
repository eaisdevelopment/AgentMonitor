"""Pure policy checks for the owner-observed Codex quota witness."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    CreatePendingAccountCommandV1,
    RegisterAccountV1,
)

from tools.automation.implementations.m5_codex_quota_witness import (
    M5CodexQuotaWitnessErrorV1,
    _agent_records,
    _digest,
    _unlink_created_witness_v1,
    _validate_created_witness_v1,
    _validate_private_parent_v1,
    _validated_browser_records,
    _write_create_once,
    parse_quota_witness_document_v1,
    reconcile_quota_observations_v1,
    registry_graph_digest_v1,
)

REVISION = "a" * 40
DIGEST = "b" * 64
ROOT = Path(__file__).resolve().parents[2]


def test_registry_graph_digest_pages_through_more_than_200_real_accounts(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    repository = SqliteRegistryRepositoryV1(reference)
    register = RegisterAccountV1(repository)
    manifest_reference = get_manifest_fingerprint_v1(build_codex_manifest())
    for index in range(201):
        register.pending(
            CreatePendingAccountCommandV1(
                command_id=OpaqueIdV1(uuid.uuid4().hex),
                principal_id=OpaqueIdV1("m5-quota-registry-test"),
                provider_key="codex",
                manifest_reference=manifest_reference,
                friendly_name=f"Quota Codex {index + 1:03}",
                organization_id=None,
                requested_at=datetime(2026, 10, 7, 10, 0, tzinfo=UTC),
            )
        )

    digest = registry_graph_digest_v1(reference)

    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)

    with pytest.raises(
        M5CodexQuotaWitnessErrorV1,
        match="m5_quota_witness_registry_incomplete",
    ):
        registry_graph_digest_v1(reference, max_page_count=1)


def _agentmonitor_records() -> list[dict[str, object]]:
    return [
        {
            "account_id": "account-one",
            "collection_run_id": "run-one",
            "collected_at": "2026-10-07T12:00:00Z",
            "windows": [
                {
                    "window_key": "codex:primary",
                    "semantic_role": "primary",
                    "remaining_percent": 18,
                    "reset_at": "2026-10-07T14:30:17Z",
                    "reset_precision": "exact",
                },
                {
                    "window_key": "codex:secondary",
                    "semantic_role": "secondary",
                    "remaining_percent": 76,
                    "reset_at": "2026-10-12T00:00:00Z",
                    "reset_precision": "exact",
                },
            ],
        }
    ]


def _owner_records() -> list[dict[str, object]]:
    return [
        {
            "account_id": "account-one",
            "observed_at": "2026-10-07T12:03:00Z",
            "windows": [
                {
                    "window_key": "codex:primary",
                    "semantic_role": "primary",
                    "remaining_percent": 18,
                    "reset_at": "2026-10-07T14:30:00Z",
                    "reset_display_precision": "minute",
                },
                {
                    "window_key": "codex:secondary",
                    "semantic_role": "secondary",
                    "remaining_percent": 76,
                    "reset_at": "2026-10-12T00:00:00Z",
                    "reset_display_precision": "day",
                },
            ],
        }
    ]


def _witness_document() -> dict[str, object]:
    return {
        "schema": "agentmonitor.m5-quota-witness.v1",
        "implementation_revision": REVISION,
        "service_source_revision": REVISION,
        "service_pid": 321,
        "service_start_time_ticks": 654,
        "recorded_at": "2026-10-07T12:04:00Z",
        "owner_confirmation": "interactive_terminal",
        "provider_key": "codex",
        "provider_version": "0.160.0",
        "source_id": "codex.app-server.account-rate-limits-read.v2",
        "account_count": 1,
        "window_count": 2,
        "owner_outcomes_digest": DIGEST,
        "identity_set_digest": "c" * 64,
        "collection_run_set_digest": "d" * 64,
        "quota_value_set_digest": "e" * 64,
        "owner_observation_digest": "f" * 64,
        "rendered_value_set_digest": "e" * 64,
        "history_value_set_digest": "0" * 64,
        "browser_proof_digest": "1" * 64,
        "registry_graph_digest_before": "2" * 64,
        "registry_graph_digest_after": "2" * 64,
        "browser_registry_digest_before": "3" * 64,
        "browser_registry_digest_after": "3" * 64,
    }


def _browser_proof() -> dict[str, object]:
    records = deepcopy(_agentmonitor_records())
    records[0]["alias"] = "Private owner one"
    windows = records[0]["windows"]
    assert isinstance(windows, list)
    for index, window in enumerate(windows, start=1):
        window["current_observation_id"] = f"observation-{index}"
    values, _indexed = _agent_records(_agentmonitor_records())
    value_digest = _digest(values)
    history_material = sorted(
        [
            [
                records[0]["account_id"],
                window["window_key"],
                window["semantic_role"],
                window["remaining_percent"],
                int(datetime.fromisoformat(window["reset_at"]).timestamp())
                if window["reset_at"] is not None
                else None,
                window["reset_precision"],
                window["current_observation_id"],
            ]
            for window in windows
        ],
        key=lambda row: json.dumps(row, ensure_ascii=True, separators=(",", ":")),
    )
    return {
        "schema": "agentmonitor.m5-quota-browser-proof.v1",
        "implementation_revision": REVISION,
        "service_source_revision": REVISION,
        "service_pid": 321,
        "service_start_time_ticks": 654,
        "captured_at": "2026-10-07T12:04:00Z",
        "account_count": 1,
        "window_count": 2,
        "provider_version": "0.160.0",
        "source_id": "codex.app-server.account-rate-limits-read.v2",
        "identity_set_digest": "c" * 64,
        "collection_run_set_digest": "d" * 64,
        "quota_value_set_digest": value_digest,
        "rendered_value_set_digest": value_digest,
        "history_value_set_digest": _digest(history_material),
        "registry_digest_before": "f" * 64,
        "registry_digest_after": "f" * 64,
        "mutations": 0,
        "records": records,
    }


def test_reconciliation_requires_exact_percent_reset_scope_and_five_minute_skew() -> (
    None
):
    result = reconcile_quota_observations_v1(_agentmonitor_records(), _owner_records())

    assert result.account_count == 1
    assert result.window_count == 2
    assert len(result.value_set_digest) == 64
    assert len(result.owner_observation_digest) == 64

    changes: tuple[tuple[str, object], ...] = (
        ("percent", 17),
        ("window_key", "codex:other"),
        ("semantic_role", "other"),
        ("reset_at", "2026-10-07T14:31:00Z"),
        ("skew", "2026-10-07T12:05:01Z"),
    )
    for change, value in changes:
        owner = _owner_records()
        if change == "percent":
            owner[0]["windows"][0]["remaining_percent"] = value  # type: ignore[index]
        elif change == "skew":
            owner[0]["observed_at"] = value
        else:
            owner[0]["windows"][0][change] = value  # type: ignore[index]
        with pytest.raises(
            M5CodexQuotaWitnessErrorV1,
            match="m5_quota_witness_reconciliation_mismatch",
        ):
            reconcile_quota_observations_v1(_agentmonitor_records(), owner)


def test_reconciliation_is_closed_and_rejects_missing_or_duplicate_windows() -> None:
    for mutation in ("extra", "missing", "duplicate", "fractional", "unknown_reset"):
        source = _agentmonitor_records()
        owner = _owner_records()
        if mutation == "extra":
            owner[0]["extra"] = True
        elif mutation == "missing":
            owner[0]["windows"].pop()  # type: ignore[union-attr]
        elif mutation == "duplicate":
            owner[0]["windows"][1] = deepcopy(owner[0]["windows"][0])  # type: ignore[index]
        elif mutation == "fractional":
            owner[0]["windows"][0]["remaining_percent"] = 18.5  # type: ignore[index]
        else:
            source[0]["windows"][0]["reset_at"] = None  # type: ignore[index]
            source[0]["windows"][0]["reset_precision"] = "unknown"  # type: ignore[index]
        with pytest.raises(M5CodexQuotaWitnessErrorV1):
            reconcile_quota_observations_v1(source, owner)


def test_private_witness_policy_binds_revision_service_outcomes_and_freshness() -> None:
    now = datetime(2026, 10, 7, 12, 5, tzinfo=UTC)
    parsed = parse_quota_witness_document_v1(
        _witness_document(),
        expected_revision=REVISION,
        service_pid=321,
        service_start_time_ticks=654,
        owner_outcomes_digest=DIGEST,
        verified_account_count=1,
        now=now,
    )
    assert parsed.account_count == 1
    assert parsed.window_count == 2
    assert parsed.quota_value_set_digest == "e" * 64
    assert parsed.history_value_set_digest == "0" * 64

    for key, value in (
        ("implementation_revision", "9" * 40),
        ("service_source_revision", "9" * 40),
        ("service_pid", 322),
        ("owner_outcomes_digest", "9" * 64),
        ("quota_value_set_digest", "9" * 64),
        ("registry_graph_digest_after", "9" * 64),
        ("recorded_at", "2026-10-07T11:49:59Z"),
    ):
        changed = _witness_document()
        changed[key] = value
        with pytest.raises(
            M5CodexQuotaWitnessErrorV1, match="m5_quota_witness_invalid"
        ):
            parse_quota_witness_document_v1(
                changed,
                expected_revision=REVISION,
                service_pid=321,
                service_start_time_ticks=654,
                owner_outcomes_digest=DIGEST,
                verified_account_count=1,
                now=now,
            )


@pytest.mark.parametrize(
    "field",
    ("service_pid", "service_start_time_ticks", "account_count", "window_count"),
)
def test_private_witness_rejects_booleans_for_integer_fields(field: str) -> None:
    document = _witness_document()
    document[field] = True
    arguments = {
        "expected_revision": REVISION,
        "service_pid": 1 if field == "service_pid" else 321,
        "service_start_time_ticks": (1 if field == "service_start_time_ticks" else 654),
        "owner_outcomes_digest": DIGEST,
        "verified_account_count": 1,
        "now": datetime(2026, 10, 7, 12, 5, tzinfo=UTC),
    }

    with pytest.raises(M5CodexQuotaWitnessErrorV1, match="m5_quota_witness_invalid"):
        parse_quota_witness_document_v1(document, **arguments)  # type: ignore[arg-type]


def test_browser_proof_binds_the_running_service_source_revision() -> None:
    now = datetime(2026, 10, 7, 12, 5, tzinfo=UTC)
    records, sanitized = _validated_browser_records(
        _browser_proof(),
        revision=REVISION,
        service_pid=321,
        service_start_time_ticks=654,
        verified_account_ids=frozenset({"account-one"}),
        now=now,
    )
    assert len(records) == 1
    assert sanitized["window_count"] == 2
    assert (
        sanitized["history_value_set_digest"]
        == _browser_proof()["history_value_set_digest"]
    )

    changed = _browser_proof()
    changed["service_source_revision"] = "9" * 40
    with pytest.raises(
        M5CodexQuotaWitnessErrorV1,
        match="m5_quota_witness_browser_proof_invalid",
    ):
        _validated_browser_records(
            changed,
            revision=REVISION,
            service_pid=321,
            service_start_time_ticks=654,
            verified_account_ids=frozenset({"account-one"}),
            now=now,
        )


@pytest.mark.parametrize("mutation", ("observation_id", "history_digest"))
def test_browser_proof_recomputes_history_digest_from_current_observations(
    mutation: str,
) -> None:
    proof = _browser_proof()
    if mutation == "observation_id":
        proof["records"][0]["windows"][0][  # type: ignore[index]
            "current_observation_id"
        ] = "observation-substituted"
    else:
        proof["history_value_set_digest"] = "9" * 64

    with pytest.raises(
        M5CodexQuotaWitnessErrorV1,
        match="m5_quota_witness_browser_proof_invalid",
    ):
        _validated_browser_records(
            proof,
            revision=REVISION,
            service_pid=321,
            service_start_time_ticks=654,
            verified_account_ids=frozenset({"account-one"}),
            now=datetime(2026, 10, 7, 12, 5, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "field",
    (
        "service_pid",
        "service_start_time_ticks",
        "account_count",
        "window_count",
        "mutations",
    ),
)
def test_browser_proof_rejects_booleans_for_integer_fields(field: str) -> None:
    proof = _browser_proof()
    service_pid = 321
    service_start_time_ticks = 654
    if field == "service_pid":
        service_pid = 1
    elif field == "service_start_time_ticks":
        service_start_time_ticks = 1
    elif field == "window_count":
        record = proof["records"][0]  # type: ignore[index]
        record["windows"] = record["windows"][:1]  # type: ignore[index]
        policy_record = dict(record)
        policy_record.pop("alias")
        policy_record["windows"] = [
            {
                key: value
                for key, value in window.items()
                if key != "current_observation_id"
            }
            for window in policy_record["windows"]  # type: ignore[union-attr]
        ]
        values, _indexed = _agent_records([policy_record])
        proof["quota_value_set_digest"] = _digest(values)
        proof["rendered_value_set_digest"] = _digest(values)
    proof[field] = field != "mutations"

    with pytest.raises(
        M5CodexQuotaWitnessErrorV1,
        match="m5_quota_witness_browser_proof_invalid",
    ):
        _validated_browser_records(
            proof,
            revision=REVISION,
            service_pid=service_pid,
            service_start_time_ticks=service_start_time_ticks,
            verified_account_ids=frozenset({"account-one"}),
            now=datetime(2026, 10, 7, 12, 5, tzinfo=UTC),
        )


def test_quota_browser_entrypoint_loads_the_locked_playwright_installation() -> None:
    completed = subprocess.run(
        ["node", "tools/ui/verify_m5_codex_quota_reconciliation.mjs"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 3
    assert completed.stdout == ""
    assert completed.stderr == (
        "M5 CODEX QUOTA BROWSER: BLOCKED — selection: "
        "m5_quota_browser_selection_invalid\n"
    )


def test_quota_witness_writer_creates_exact_private_file(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "m5-quota-witness.json"

    digest = _write_create_once(path, {"proof": True})

    metadata = path.lstat()
    assert len(digest) == 64
    assert stat.S_ISREG(metadata.st_mode)
    assert metadata.st_uid == os.getuid()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    assert metadata.st_nlink == 1
    assert path.read_bytes() == b'{\n  "proof": true\n}\n'


def test_quota_private_parent_validation_rejects_path_substitution(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    path = parent / "m5-quota-witness.json"
    descriptor = os.open(
        parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    metadata = os.fstat(descriptor)
    parent.rename(tmp_path / "displaced")
    parent.mkdir(mode=0o700)

    try:
        with pytest.raises(OSError):
            _validate_private_parent_v1(
                path,
                descriptor,
                device=metadata.st_dev,
                inode=metadata.st_ino,
            )
    finally:
        os.close(descriptor)


def _opened_created_file(path: Path) -> tuple[int, int, os.stat_result]:
    parent_descriptor = os.open(
        path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    descriptor = os.open(path.name, os.O_RDWR | os.O_NOFOLLOW, dir_fd=parent_descriptor)
    return parent_descriptor, descriptor, os.fstat(descriptor)


def test_quota_witness_created_file_validation_rejects_mode_change(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "m5-quota-witness.json"
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


def test_quota_witness_created_file_validation_rejects_an_added_hardlink(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "m5-quota-witness.json"
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


def test_quota_witness_cleanup_never_unlinks_a_substituted_path(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "m5-quota-witness.json"
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
