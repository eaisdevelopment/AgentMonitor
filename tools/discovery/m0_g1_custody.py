"""Interactive owner custody selection for the M0 G1 gate."""

from __future__ import annotations

import getpass
import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from m0_g1_exit import is_utc_z_timestamp, verify_custody_root

SYNC_EXCLUSION_CONFIRMATION = "I CONFIRM THIS ROOT IS EXCLUDED FROM SYNC AND BACKUP"
SYNC_ENCRYPTED_CONFIRMATION = (
    "I CONFIRM ENCRYPTED SYNC AND BACKUP FOR THIS ROOT AND ACCEPT THE RISK"
)
SYNC_ACCEPTED_CONFIRMATION = (
    "I CONFIRM THIS ROOT REMAINS SYNCED AND I ACCEPT THE CUSTODY RISK"
)


def disposition_for_confirmation(confirmation: str) -> str | None:
    """Map only exact owner statements to approved custody dispositions."""

    return {
        SYNC_EXCLUSION_CONFIRMATION: "excluded",
        SYNC_ENCRYPTED_CONFIRMATION: "owner_accepted_encrypted",
        SYNC_ACCEPTED_CONFIRMATION: "owner_accepted_synced",
    }.get(confirmation)


def write_selection(
    *,
    selection_path: Path,
    external_root: Path,
    repository_root: Path,
    retention_until_utc: str,
    sync_backup_confirmation: str,
) -> list[str]:
    """Write local custody selection only after explicit owner attestation."""

    disposition = disposition_for_confirmation(sync_backup_confirmation)
    if disposition is None:
        return ["exact sync/backup disposition confirmation is missing"]
    violations = verify_custody_root(external_root, repository_root)
    if not is_utc_z_timestamp(retention_until_utc):
        violations.append("retention deadline must be a UTC-Z timestamp")
    if violations:
        return violations

    parent = selection_path.parent
    try:
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent_metadata = parent.lstat()
    except OSError:
        return ["local custody configuration directory is unavailable"]
    if not stat.S_ISDIR(parent_metadata.st_mode) or parent.is_symlink():
        return ["local custody configuration parent is unsafe"]
    if hasattr(os, "getuid") and parent_metadata.st_uid != os.getuid():
        return ["local custody configuration parent has the wrong owner"]
    if stat.S_IMODE(parent_metadata.st_mode) & 0o077:
        return ["local custody configuration parent is not owner-only"]

    attested_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    content = (
        'schema_version = "1.1"\n'
        'external_root_ref = "REF-M0-CUSTODY-001"\n'
        f"external_root = {json.dumps(str(external_root))}\n"
        "owner_selected = true\n"
        f"sync_backup_disposition = {json.dumps(disposition)}\n"
        "sync_backup_owner_attested = true\n"
        f"sync_backup_attested_at_utc = {json.dumps(attested_at_utc)}\n"
        f"retention_until_utc = {json.dumps(retention_until_utc)}\n"
    )
    temporary_path: Path | None = None
    try:
        descriptor, raw_temporary_path = tempfile.mkstemp(
            prefix=".m0-g1-custody-",
            dir=parent,
            text=True,
        )
        temporary_path = Path(raw_temporary_path)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, selection_path)
        temporary_path = None
    except OSError:
        return ["local custody selection could not be written"]
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return []


def _one_year_from_now_utc() -> str:
    now = datetime.now(timezone.utc)
    try:
        future = now.replace(year=now.year + 1)
    except ValueError:
        future = now.replace(year=now.year + 1, day=28)
    return future.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    raw_root = getpass.getpass("External evidence directory (input hidden): ")
    print("Choose one truthful sync/backup statement:")
    print(f'- excluded: "{SYNC_EXCLUSION_CONFIRMATION}"')
    print(f'- encrypted and owner-accepted: "{SYNC_ENCRYPTED_CONFIRMATION}"')
    print(f'- synced and owner-accepted: "{SYNC_ACCEPTED_CONFIRMATION}"')
    confirmation = input("Type the exact statement: ")
    violations = write_selection(
        selection_path=(repository_root / ".agentmonitor-local/m0-g1-custody.toml"),
        external_root=Path(raw_root),
        repository_root=repository_root,
        retention_until_utc=_one_year_from_now_utc(),
        sync_backup_confirmation=confirmation,
    )
    if violations:
        print("M0 G1 CUSTODY: BLOCKED")
        for violation in violations:
            print(f"- {violation}")
        return 3
    print("M0 G1 CUSTODY: OWNER SELECTION RECORDED")
    print("- path value: NOT DISPLAYED")
    print("- retention: one year")
    print(f"- sync/backup disposition: {disposition_for_confirmation(confirmation)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
