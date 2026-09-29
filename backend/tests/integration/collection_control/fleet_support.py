"""Explicit owner-selected real M4 fleet; no identities or outcomes are invented."""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1

_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


@dataclass(frozen=True, slots=True)
class OwnerFleetAccountV1:
    account_id: str
    organization_id: str
    disposition: str


@dataclass(frozen=True, slots=True)
class SelectedFleetV1:
    reference: DatabaseRefV1
    outcomes: tuple[OwnerFleetAccountV1, ...]


def selected_owner_fleet() -> SelectedFleetV1:
    root_text = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    manifest_text = os.environ.get("AGENTMONITOR_TEST_M4_OWNER_OUTCOMES")
    if not root_text or not manifest_text:
        raise AssertionError("m4_explicit_owner_selection_required")
    root = Path(root_text)
    manifest = Path(manifest_text)
    if not root.is_absolute() or not manifest.is_absolute():
        raise AssertionError("m4_selection_path_invalid")
    if not (root / "agentmonitor.db").is_file() or not manifest.is_file():
        raise AssertionError("m4_selected_resource_unavailable")
    metadata = manifest.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
        raise AssertionError("m4_outcomes_file_not_private")
    if metadata.st_size < 2 or metadata.st_size > 8192:
        raise AssertionError("m4_outcomes_file_size_invalid")
    try:
        document = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise AssertionError("m4_outcomes_file_invalid") from None
    if (
        not isinstance(document, dict)
        or set(document) != {"schema", "outcomes"}
        or document["schema"] != "agentmonitor.m4-owner-outcomes.v1"
        or not isinstance(document["outcomes"], list)
        or len(document["outcomes"]) != 6
    ):
        raise AssertionError("m4_outcomes_schema_invalid")
    outcomes = []
    for row in document["outcomes"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"account_id", "organization_id", "disposition"}
            or not isinstance(row["account_id"], str)
            or not isinstance(row["organization_id"], str)
            or _ID.fullmatch(row["account_id"]) is None
            or _ID.fullmatch(row["organization_id"]) is None
            or row["disposition"] not in {"verified", "owner_unavailable"}
        ):
            raise AssertionError("m4_outcome_invalid")
        outcomes.append(OwnerFleetAccountV1(**row))
    if len({row.account_id for row in outcomes}) != 6:
        raise AssertionError("m4_duplicate_owner_account")
    if len({row.organization_id for row in outcomes}) != 2:
        raise AssertionError("m4_two_owner_organizations_required")
    return SelectedFleetV1(
        DatabaseRefV1(root / "agentmonitor.db", root), tuple(outcomes)
    )
