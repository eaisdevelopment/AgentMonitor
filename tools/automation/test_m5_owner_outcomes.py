"""M5 canonical owner-outcome producer contract and real local boundaries."""

# This test module inserts the checkout's backend source path before imports.
# ruff: noqa: E402

from __future__ import annotations

import json
import os
import stat
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

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

from tools.automation._m5_test_git import (
    attached_real_checkout_v1,
    git_status_v1,
)
from tools.automation.implementations.m5_owner_outcomes import (
    OWNER_CONFIRMATION_VALUE,
    OWNER_OUTCOMES_BASENAME,
    OWNER_OUTCOMES_SCHEMA,
    M5OwnerOutcomesErrorV1,
    OwnerAccountSelectionV1,
    OwnerOutcomeV1,
    _revalidate_runtime_binding_v1,
    _select_four_accounts,
    _select_runtime_binding_v1,
    _unlink_created_inode_v1,
    _validate_private_parent_v1,
    build_owner_outcomes_document_v2,
    read_codex_registry_accounts_v1,
    read_owner_outcomes_file_v2,
    require_owner_confirmation_v1,
    write_owner_outcomes_v2,
)
from tools.automation.implementations.m5_service_activation import (
    candidate_for_checkout_v1,
)

REVISION = "a" * 40
CONFIRMED_AT = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)


def test_owner_selection_rejects_a_real_attached_checkout_before_runtime_io() -> None:
    with attached_real_checkout_v1() as checkout:
        before = git_status_v1(checkout)
        with pytest.raises(
            M5OwnerOutcomesErrorV1,
            match="m5_owner_outcomes_checkout_invalid",
        ):
            _select_runtime_binding_v1({}, checkout_root=checkout)
        assert before == git_status_v1(checkout) == ""


def test_owner_prewrite_recheck_rejects_an_attached_checkout_before_io() -> None:
    with attached_real_checkout_v1() as checkout:
        candidate = candidate_for_checkout_v1(
            source_revision=REVISION,
            checkout_root=checkout,
        )
        with pytest.raises(
            M5OwnerOutcomesErrorV1,
            match="m5_owner_outcomes_context_changed",
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


def _outcomes() -> tuple[OwnerOutcomeV1, ...]:
    return (
        OwnerOutcomeV1("account-one", "Private one", "verified", None),
        OwnerOutcomeV1("account-two", "Private two", "verified", None),
        OwnerOutcomeV1(
            "account-three",
            "Private three",
            "owner_unavailable",
            "owner_login_unavailable",
        ),
        OwnerOutcomeV1(
            "account-four",
            "Private four",
            "owner_unavailable",
            "owner_login_unavailable",
        ),
    )


def _document(*, confirmed_at: datetime = CONFIRMED_AT) -> dict[str, object]:
    return build_owner_outcomes_document_v2(
        implementation_revision=REVISION,
        service_pid=321,
        service_start_time_ticks=654,
        owner_confirmed_at=confirmed_at,
        outcomes=_outcomes(),
    )


def _register_codex_account(reference: DatabaseRefV1, *, alias: str) -> str:
    account = RegisterAccountV1(SqliteRegistryRepositoryV1(reference)).pending(
        CreatePendingAccountCommandV1(
            command_id=OpaqueIdV1(uuid.uuid4().hex),
            principal_id=OpaqueIdV1("m5-owner-outcome-test"),
            provider_key="codex",
            manifest_reference=get_manifest_fingerprint_v1(build_codex_manifest()),
            friendly_name=alias,
            organization_id=None,
            requested_at=CONFIRMED_AT,
        )
    )
    return account.account_id.value


def test_document_is_revision_service_bound_and_contains_no_identity_input() -> None:
    document = _document()

    assert document == {
        "schema": OWNER_OUTCOMES_SCHEMA,
        "implementation_revision": REVISION,
        "service_pid": 321,
        "service_start_time_ticks": 654,
        "owner_confirmed_at": "2026-10-07T10:00:00Z",
        "owner_confirmation": OWNER_CONFIRMATION_VALUE,
        "outcomes": [
            {
                "account_id": "account-one",
                "alias": "Private one",
                "disposition": "verified",
            },
            {
                "account_id": "account-two",
                "alias": "Private two",
                "disposition": "verified",
            },
            {
                "account_id": "account-three",
                "alias": "Private three",
                "disposition": "owner_unavailable",
                "reason": "owner_login_unavailable",
            },
            {
                "account_id": "account-four",
                "alias": "Private four",
                "disposition": "owner_unavailable",
                "reason": "owner_login_unavailable",
            },
        ],
    }
    assert "fingerprint" not in json.dumps(document)


def test_owner_confirmation_requires_the_exact_displayed_phrase() -> None:
    require_owner_confirmation_v1("CONFIRM M5 OWNER OUTCOMES")
    for value in (
        "confirm m5 owner outcomes",
        "CONFIRM M5 OWNER OUTCOMES ",
        "yes",
        "",
    ):
        with pytest.raises(
            M5OwnerOutcomesErrorV1,
            match="m5_owner_outcomes_confirmation_required",
        ):
            require_owner_confirmation_v1(value)


def test_owner_outcome_rejects_an_unknown_disposition_even_with_a_safe_reason() -> None:
    with pytest.raises(M5OwnerOutcomesErrorV1, match="m5_owner_outcomes_invalid"):
        OwnerOutcomeV1(  # type: ignore[arg-type]
            "account-one",
            "Private one",
            "unknown",
            "owner_login_unavailable",
        )


def test_account_selection_displays_only_the_four_selected_safe_rows(
    capsys: pytest.CaptureFixture[str],
) -> None:
    accounts = tuple(
        OwnerAccountSelectionV1(f"account-{index}", f"Private {index}")
        for index in range(1, 5)
    )

    assert _select_four_accounts(accounts) == accounts

    output = capsys.readouterr().out
    assert "Available non-archived" not in output
    for account in accounts:
        assert (
            output.count(
                f"{account.alias} [vendor: OpenAI; provider: Codex; "
                f"account ID: {account.account_id}]"
            )
            == 1
        )


def test_real_migrated_registry_is_read_through_public_account_query(
    tmp_path: Path,
) -> None:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    registered = tuple(
        _register_codex_account(
            reference,
            alias=f"Private Codex {index + 1:03}",
        )
        for index in range(201)
    )
    selected = read_codex_registry_accounts_v1(reference, as_of=CONFIRMED_AT)

    assert {item.account_id for item in selected} == set(registered)
    assert tuple(item.alias for item in selected) == tuple(
        f"Private Codex {index + 1:03}" for index in range(201)
    )
    assert all(isinstance(item, OwnerAccountSelectionV1) for item in selected)

    with pytest.raises(
        M5OwnerOutcomesErrorV1,
        match="m5_owner_outcomes_registry_unavailable",
    ):
        read_codex_registry_accounts_v1(
            reference,
            as_of=CONFIRMED_AT,
            max_page_count=1,
        )


def test_create_once_writer_uses_owner_only_regular_single_link_file(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / OWNER_OUTCOMES_BASENAME
    confirmed_at = datetime.now(UTC)

    digest = write_owner_outcomes_v2(path, _document(confirmed_at=confirmed_at))

    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode)
    assert metadata.st_uid == os.getuid()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    assert metadata.st_nlink == 1
    assert len(digest) == 64
    parsed, parsed_digest = read_owner_outcomes_file_v2(
        path, now=confirmed_at + timedelta(minutes=5)
    )
    assert parsed.implementation_revision == REVISION
    assert parsed.verified_account_ids == frozenset({"account-one", "account-two"})
    assert parsed_digest == digest

    with pytest.raises(M5OwnerOutcomesErrorV1, match="m5_owner_outcomes_target_exists"):
        write_owner_outcomes_v2(path, _document(confirmed_at=confirmed_at))


def test_private_parent_validation_rejects_path_substitution(tmp_path: Path) -> None:
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    path = parent / OWNER_OUTCOMES_BASENAME
    descriptor = os.open(
        parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    metadata = os.fstat(descriptor)
    displaced = tmp_path / "displaced"
    parent.rename(displaced)
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


def test_owner_outcome_cleanup_never_unlinks_a_substituted_path(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    path = parent / OWNER_OUTCOMES_BASENAME
    path.write_bytes(b"created inode\n")
    path.chmod(0o600)
    parent_descriptor = os.open(
        parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    created = path.stat()
    displaced = parent / "displaced-created-inode"
    path.rename(displaced)
    replacement = b"replacement must remain\n"
    path.write_bytes(replacement)
    path.chmod(0o600)

    try:
        _unlink_created_inode_v1(
            path,
            parent_descriptor,
            device=created.st_dev,
            inode=created.st_ino,
        )
    finally:
        os.close(parent_descriptor)

    assert path.read_bytes() == replacement
    assert displaced.exists()


@pytest.mark.parametrize("link_kind", ("symlink", "hardlink"))
def test_create_once_writer_refuses_existing_links(
    tmp_path: Path, link_kind: str
) -> None:
    tmp_path.chmod(0o700)
    target = tmp_path / "existing.json"
    target.write_text("{}", encoding="utf-8")
    target.chmod(0o600)
    path = tmp_path / OWNER_OUTCOMES_BASENAME
    if link_kind == "symlink":
        path.symlink_to(target)
    else:
        os.link(target, path)

    with pytest.raises(M5OwnerOutcomesErrorV1, match="m5_owner_outcomes_target_exists"):
        write_owner_outcomes_v2(path, _document(confirmed_at=datetime.now(UTC)))


def test_file_reader_rejects_stale_confirmation_and_private_identity_field(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / OWNER_OUTCOMES_BASENAME
    document = _document()
    outcomes = document["outcomes"]
    assert isinstance(outcomes, list)
    first = outcomes[0]
    assert isinstance(first, dict)
    first["identity_fingerprint"] = "f" * 64
    path.write_text(json.dumps(document), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(M5OwnerOutcomesErrorV1, match="m5_owner_outcomes_invalid"):
        read_owner_outcomes_file_v2(path, now=CONFIRMED_AT + timedelta(minutes=5))

    first.pop("identity_fingerprint")
    path.write_text(json.dumps(document), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(M5OwnerOutcomesErrorV1, match="m5_owner_outcomes_invalid"):
        read_owner_outcomes_file_v2(path, now=CONFIRMED_AT + timedelta(days=9))


def test_file_reader_rejects_a_hard_linked_owner_attestation(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    confirmed_at = datetime.now(UTC)
    path = tmp_path / OWNER_OUTCOMES_BASENAME
    path.write_text(json.dumps(_document(confirmed_at=confirmed_at)), encoding="utf-8")
    path.chmod(0o600)
    os.link(path, tmp_path / "second-name.json")

    with pytest.raises(M5OwnerOutcomesErrorV1, match="m5_owner_outcomes_invalid"):
        read_owner_outcomes_file_v2(path, now=confirmed_at + timedelta(minutes=1))
