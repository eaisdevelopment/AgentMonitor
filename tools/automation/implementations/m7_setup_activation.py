"""Prepare a clean M7 setup or financial candidate without installed changes.

Only a newly created workspace is writable. The existing retained-release,
frontend and SQLite backup helpers perform the work. This is preparation, not
service activation or an installed continuity/recovery acceptance receipt.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from tools.automation.implementations.m6_candidate_release import (
    prepare_candidate_release,
    verify_candidate_release,
)
from tools.automation.implementations.m6_frontend_build import _clean_revision


class SetupPreparationError(RuntimeError):
    """Closed failure without captured subprocess output or owner information."""


@dataclass(frozen=True)
class SetupPreparation:
    status: Literal["prepared", "prepared_activation_blocked"]
    revision: str
    build_digest: str
    release: str
    source_revision: str
    target_revision: str
    catalog_digest: str
    backup_digest: str
    blockers: tuple[str, ...]


# Executed with only the selected retained checkout on PYTHONPATH. These are
# genuine migrations on a NEW empty database, never an alternate live upgrader.
_REHEARSAL = r"""
import json
import sqlite3
import sys
from pathlib import Path
from alembic import command
from alembic.config import Config
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1, open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    MIGRATIONS_PATH, InspectSchemaCompatibilityV1, application_schema_range,
    load_migration_catalog,
)
from tools.automation.implementations.auto_migrate import (
    MigrationRefused, _create_sqlite_backup, _preflight_catalog,
    _verify_sqlite_backup,
)
from tools.automation.implementations.m6_cutover import _retained_migration_source

phase = sys.argv[2] if len(sys.argv) > 2 else "setup"
if phase not in {"setup", "financial"}:
    raise ValueError("m7_setup_phase_invalid")
catalog = load_migration_catalog()
if phase == "financial" and catalog.head != "v1_0734":
    raise ValueError("m7_setup_schema_unavailable")
root = Path(sys.argv[1])
root.mkdir(mode=0o700)
backup = root / "backup"
backup.mkdir(mode=0o700)
ref = DatabaseRefV1(root / "agentmonitor.db", root)
source = "v1_0733" if phase == "financial" else "v1_0720"
revisions = tuple(item.revision for item in catalog.revisions)
if source not in revisions or "v1_0731" not in revisions:
    raise ValueError("m7_setup_schema_unavailable")

def upgrade(target, mode):
    with open_sqlite_database(ref, mode) as handle, handle.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS_PATH))
        config.attributes.update(connection=connection,
            migrations_path=MIGRATIONS_PATH, catalog_digest=catalog.digest)
        command.upgrade(config, target)
        connection.commit()

upgrade(source, "migration_initialize")
with open_sqlite_database(ref, "migration_existing") as handle:
    with handle.connect() as connection:
        driver = connection.connection.driver_connection
        if not isinstance(driver, sqlite3.Connection):
            raise ValueError("m7_setup_driver_invalid")
        backup_digest = _create_sqlite_backup(driver, backup / "agentmonitor.db")
_verify_sqlite_backup(backup, catalog.digest, source)
upgrade(catalog.head, "migration_existing")
view = InspectSchemaCompatibilityV1(
    ref, application_schema_range(), "runtime_read_write"
)
if (view.state != "compatible" or view.current_revision != catalog.head
    or view.integrity_state != "passed" or view.policy_state != "passed"):
    raise ValueError("m7_setup_rehearsal_invalid")
# Reopen the backup AFTER upgrade: prove it still holds the previous schema.
_verify_sqlite_backup(backup, catalog.digest, source)
blockers = []
try:
    _preflight_catalog(source)
except MigrationRefused:
    blockers.append("migration_operator_policy_not_admitted")
if _retained_migration_source(catalog.head) != source:
    blockers.append("cutover_source_policy_not_admitted")
print(json.dumps({"source_revision": source, "target_revision": catalog.head,
    "catalog_digest": catalog.digest, "backup_digest": backup_digest,
    "blockers": blockers}, sort_keys=True))
"""


def _candidate_process(
    release: Path, python_executable: Path, arguments: list[str], *, timeout: int
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(python_executable), "-B", *arguments],
        cwd=release,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C",
            "PYTHONPATH": str(release / "backend/src") + os.pathsep + str(release),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def prepare_setup_activation(
    *,
    candidate: Path,
    expected_revision: str,
    workspace: Path,
    tool_modules: Path,
    python_executable: Path,
    phase: str = "setup",
) -> SetupPreparation:
    """Retain/build/rehearse one explicit checkout; never activate a service.

    Workspace must not exist. Partial failures are retained for inspection;
    this function never deletes evidence or resumes an ambiguous preparation.
    """
    if phase not in {"setup", "financial"}:
        raise SetupPreparationError("m7_setup_phase_invalid")
    source_revision = "v1_0733" if phase == "financial" else "v1_0720"
    paths = (candidate, workspace, tool_modules)
    if (
        any(not path.is_absolute() or path.resolve() != path for path in paths)
        or not python_executable.is_absolute()
        or not python_executable.is_file()
        or candidate in workspace.parents
        or workspace == candidate
        or workspace in candidate.parents
        or workspace == tool_modules
        or workspace in tool_modules.parents
        or re.fullmatch(r"[a-f0-9]{40}", expected_revision) is None
    ):
        raise SetupPreparationError("m7_setup_selection_invalid")
    if workspace.exists() or workspace.is_symlink():
        raise SetupPreparationError("m7_setup_workspace_exists")
    if _clean_revision(candidate) != expected_revision:
        raise SetupPreparationError("m7_setup_revision_mismatch")
    workspace.mkdir(mode=0o700)
    info = workspace.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or info.st_uid != os.getuid()
    ):
        raise SetupPreparationError("m7_setup_workspace_unsafe")
    release, revision, build = prepare_candidate_release(
        candidate,
        workspace / "releases",
        workspace,
        tool_modules,
        expected_revision=expected_revision,
    )
    if revision != expected_revision:
        raise SetupPreparationError("m7_setup_revision_mismatch")
    help_result = _candidate_process(
        release,
        python_executable,
        ["-m", "agentmonitor.composition.billing_credential_operator", "--help"],
        timeout=30,
    )
    if help_result.returncode or not all(
        flag in help_result.stdout
        for flag in ("--account-id", "--resource-id", "--data-root")
    ):
        raise SetupPreparationError("m7_setup_command_unavailable")
    if phase == "financial":
        worker_help = _candidate_process(
            release,
            python_executable,
            ["-m", "agentmonitor.composition.billing_worker", "--help"],
            timeout=30,
        )
        if worker_help.returncode or not all(
            flag in worker_help.stdout
            for flag in ("--data-root", "--start-authority", "--recovery-only")
        ):
            raise SetupPreparationError("m7_setup_worker_unavailable")
    rehearsal = _candidate_process(
        release,
        python_executable,
        ["-c", _REHEARSAL, str(workspace / "schema-rehearsal"), phase],
        timeout=180,
    )
    if rehearsal.returncode or len(rehearsal.stdout) > 8192:
        raise SetupPreparationError("m7_setup_rehearsal_failed")
    try:
        facts = json.loads(rehearsal.stdout)
        if set(facts) != {
            "source_revision",
            "target_revision",
            "catalog_digest",
            "backup_digest",
            "blockers",
        }:
            raise ValueError
        if (
            facts["source_revision"] != source_revision
            or phase == "financial"
            and facts["target_revision"] != "v1_0734"
            or not isinstance(facts["target_revision"], str)
            or re.fullmatch(r"v1_[0-9]{4}", facts["target_revision"]) is None
            or any(
                not isinstance(facts[key], str)
                or re.fullmatch(r"[a-f0-9]{64}", facts[key]) is None
                for key in ("catalog_digest", "backup_digest")
            )
            or not isinstance(facts["blockers"], list)
            or any(
                item
                not in {
                    "migration_operator_policy_not_admitted",
                    "cutover_source_policy_not_admitted",
                }
                for item in facts["blockers"]
            )
        ):
            raise ValueError
    except (TypeError, ValueError, KeyError):
        raise SetupPreparationError("m7_setup_rehearsal_result_invalid") from None
    verify_candidate_release(release, workspace / "releases", revision, build)
    if _clean_revision(candidate) != revision:
        raise SetupPreparationError("m7_setup_source_changed")
    result = SetupPreparation(
        "prepared_activation_blocked" if facts["blockers"] else "prepared",
        revision,
        build,
        str(release),
        facts["source_revision"],
        facts["target_revision"],
        facts["catalog_digest"],
        facts["backup_digest"],
        tuple(facts["blockers"]),
    )
    descriptor = os.open(
        workspace / "preparation.json",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w") as output:
        json.dump(asdict(result), output, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("setup", "financial"), default="setup")
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--tool-modules", required=True, type=Path)
    parser.add_argument("--python-executable", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare_setup_activation(**vars(args))
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        print("M7 SETUP PREPARATION: blocked; retained workspace requires inspection")
        return 3
    print(json.dumps(asdict(result), sort_keys=True))
    return 3 if result.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
