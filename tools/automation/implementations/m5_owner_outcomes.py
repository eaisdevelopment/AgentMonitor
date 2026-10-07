"""Create the private, service-bound V1-M5 owner outcome attestation once."""

# This operator command inserts the checkout's backend source path before imports.
# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

ROOT = Path(__file__).resolve().parents[3]
BACKEND_SOURCE = ROOT / "backend/src"
if str(BACKEND_SOURCE) not in sys.path:
    sys.path.insert(0, str(BACKEND_SOURCE))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.registry_v1 import AccountViewV1
from agentmonitor.modules.registry.application.accounts import ListAccountsV1

from tools.automation.implementations.auto_m3_current_exit import (
    M3CurrentExitErrorV1,
    ServiceLaunchV1,
    _clean_revision,
    _process_start_ticks,
    _read_service_launch,
)

CANONICAL_COMMAND = "python3 tools/automation/run.py AUTO-M5-OWNER-OUTCOMES"
OWNER_OUTCOMES_BASENAME = "m5-owner-outcomes.json"
OWNER_OUTCOMES_SCHEMA = "agentmonitor.m5-owner-outcomes.v2"
OWNER_CONFIRMATION_VALUE = True
OWNER_CONFIRMATION_PHRASE = "CONFIRM M5 OWNER OUTCOMES"
MAX_OWNER_OUTCOME_AGE = timedelta(days=8)
MAX_CLOCK_SKEW = timedelta(minutes=5)
MAX_FILE_BYTES = 16_384
MAX_REGISTRY_PAGE_COUNT = 10_000

_OPAQUE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_SAFE_REASON = re.compile(r"[a-z][a-z0-9_]{0,95}\Z")
_UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z\Z")


class M5OwnerOutcomesErrorV1(ValueError):
    """One sanitized owner-outcome producer or input failure."""


@dataclass(frozen=True, slots=True)
class OwnerAccountSelectionV1:
    """Safe public registry fields which the owner can select in a TTY."""

    account_id: str
    alias: str

    def __post_init__(self) -> None:
        if _OPAQUE.fullmatch(self.account_id) is None:
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_registry_invalid")
        _normalized_alias(self.alias)


@dataclass(frozen=True, slots=True)
class OwnerOutcomeV1:
    """One explicit owner disposition; no provider identity input is accepted."""

    account_id: str
    alias: str
    disposition: Literal["verified", "owner_unavailable"]
    reason: str | None = None

    def __post_init__(self) -> None:
        if _OPAQUE.fullmatch(self.account_id) is None:
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
        _normalized_alias(self.alias)
        if self.disposition == "verified":
            valid = self.reason is None
        elif self.disposition == "owner_unavailable":
            valid = (
                type(self.reason) is str
                and _SAFE_REASON.fullmatch(self.reason) is not None
            )
        else:
            valid = False
        if not valid:
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")

    def as_json(self) -> dict[str, object]:
        row: dict[str, object] = {
            "account_id": self.account_id,
            "alias": self.alias,
            "disposition": self.disposition,
        }
        if self.reason is not None:
            row["reason"] = self.reason
        return row


@dataclass(frozen=True, slots=True)
class ParsedOwnerOutcomesV2:
    """Validated private input, retained only in the local gate process."""

    implementation_revision: str
    service_pid: int
    service_start_time_ticks: int
    owner_confirmed_at: datetime
    outcomes: tuple[OwnerOutcomeV1, ...] = field(repr=False)

    @property
    def verified_account_ids(self) -> frozenset[str]:
        return frozenset(
            item.account_id for item in self.outcomes if item.disposition == "verified"
        )

    @property
    def unavailable_account_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.account_id
                for item in self.outcomes
                if item.disposition == "owner_unavailable"
            )
        )


@dataclass(frozen=True, slots=True)
class SelectedOwnerServiceV1:
    """Exact already-running service tuple to bind before the M5 restart."""

    pid: int
    start_time_ticks: int
    launch: ServiceLaunchV1


def _normalized_alias(value: object) -> str:
    if type(value) is not str or value != value.strip():
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    normalized = unicodedata.normalize("NFKC", value).casefold()
    if not 1 <= len(normalized) <= 128 or not normalized.isprintable():
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    return normalized


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _utc_value(value: object) -> datetime:
    if type(value) is not str or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid") from None
    if parsed.utcoffset() != timedelta(0):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    return parsed


def _validate_outcome_set(
    outcomes: tuple[OwnerOutcomeV1, ...],
) -> tuple[OwnerOutcomeV1, ...]:
    if len(outcomes) != 4:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    account_ids = tuple(item.account_id for item in outcomes)
    aliases = tuple(_normalized_alias(item.alias) for item in outcomes)
    if len(set(account_ids)) != 4 or len(set(aliases)) != 4:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    return outcomes


def build_owner_outcomes_document_v2(
    *,
    implementation_revision: str,
    service_pid: int,
    service_start_time_ticks: int,
    owner_confirmed_at: datetime,
    outcomes: tuple[OwnerOutcomeV1, ...],
) -> dict[str, object]:
    """Build the closed v2 attestation after an explicit owner checkpoint."""

    if (
        _REVISION.fullmatch(implementation_revision) is None
        or type(service_pid) is not int
        or not 1 <= service_pid <= 9_999_999_999
        or type(service_start_time_ticks) is not int
        or not 1 <= service_start_time_ticks <= 2**63 - 1
    ):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    checked = _validate_outcome_set(outcomes)
    return {
        "schema": OWNER_OUTCOMES_SCHEMA,
        "implementation_revision": implementation_revision,
        "service_pid": service_pid,
        "service_start_time_ticks": service_start_time_ticks,
        "owner_confirmed_at": _utc_text(owner_confirmed_at),
        "owner_confirmation": OWNER_CONFIRMATION_VALUE,
        "outcomes": [item.as_json() for item in checked],
    }


def parse_owner_outcomes_document_v2(
    document: object, *, now: datetime
) -> ParsedOwnerOutcomesV2:
    """Validate the closed schema and bounded owner-confirmation freshness."""

    expected_keys = {
        "schema",
        "implementation_revision",
        "service_pid",
        "service_start_time_ticks",
        "owner_confirmed_at",
        "owner_confirmation",
        "outcomes",
    }
    if now.utcoffset() != timedelta(0):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    try:
        if (
            type(document) is not dict
            or set(document) != expected_keys
            or document["schema"] != OWNER_OUTCOMES_SCHEMA
            or document["owner_confirmation"] is not OWNER_CONFIRMATION_VALUE
            or type(document["implementation_revision"]) is not str
            or _REVISION.fullmatch(document["implementation_revision"]) is None
            or type(document["service_pid"]) is not int
            or not 1 <= document["service_pid"] <= 9_999_999_999
            or type(document["service_start_time_ticks"]) is not int
            or not 1 <= document["service_start_time_ticks"] <= 2**63 - 1
            or type(document["outcomes"]) is not list
            or len(document["outcomes"]) != 4
        ):
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
        confirmed_at = _utc_value(document["owner_confirmed_at"])
        if (
            confirmed_at > now + MAX_CLOCK_SKEW
            or now - confirmed_at > MAX_OWNER_OUTCOME_AGE
        ):
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
        rows: list[OwnerOutcomeV1] = []
        for raw in document["outcomes"]:
            if type(raw) is not dict:
                raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
            disposition = raw.get("disposition")
            keys = (
                {"account_id", "alias", "disposition"}
                if disposition == "verified"
                else {"account_id", "alias", "disposition", "reason"}
                if disposition == "owner_unavailable"
                else set()
            )
            if set(raw) != keys:
                raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
            rows.append(
                OwnerOutcomeV1(
                    account_id=raw["account_id"],
                    alias=raw["alias"],
                    disposition=cast(
                        Literal["verified", "owner_unavailable"], disposition
                    ),
                    reason=raw.get("reason"),
                )
            )
        outcomes = _validate_outcome_set(tuple(rows))
        return ParsedOwnerOutcomesV2(
            implementation_revision=document["implementation_revision"],
            service_pid=document["service_pid"],
            service_start_time_ticks=document["service_start_time_ticks"],
            owner_confirmed_at=confirmed_at,
            outcomes=outcomes,
        )
    except (KeyError, TypeError):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid") from None


def _validate_private_parent_v1(
    path: Path,
    descriptor: int,
    *,
    device: int,
    inode: int,
) -> None:
    metadata = os.fstat(descriptor)
    path_metadata = path.parent.lstat()
    if (
        not path.is_absolute()
        or path.name != OWNER_OUTCOMES_BASENAME
        or path.parent.resolve(strict=True) != path.parent
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or (metadata.st_dev, metadata.st_ino) != (device, inode)
        or (path_metadata.st_dev, path_metadata.st_ino) != (device, inode)
    ):
        raise OSError


def _validate_private_file_v1(
    name: str,
    descriptor: int,
    parent_descriptor: int,
    *,
    device: int,
    inode: int,
    size: int,
) -> None:
    metadata = os.fstat(descriptor)
    path_metadata = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or metadata.st_size != size
        or (metadata.st_size != 0 and not 2 <= metadata.st_size <= MAX_FILE_BYTES)
        or (metadata.st_dev, metadata.st_ino) != (device, inode)
        or (path_metadata.st_dev, path_metadata.st_ino) != (device, inode)
    ):
        raise OSError


def _read_private_file(path: Path) -> bytes:
    descriptor = -1
    parent_descriptor = -1
    try:
        if not path.is_absolute() or path.name != OWNER_OUTCOMES_BASENAME:
            raise OSError
        parent_descriptor = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        parent_metadata = os.fstat(parent_descriptor)
        parent_identity = (parent_metadata.st_dev, parent_metadata.st_ino)
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
        metadata = os.fstat(descriptor)
        file_identity = (metadata.st_dev, metadata.st_ino)
        _validate_private_file_v1(
            path.name,
            descriptor,
            parent_descriptor,
            device=file_identity[0],
            inode=file_identity[1],
            size=metadata.st_size,
        )
        remaining = metadata.st_size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                raise OSError
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) != metadata.st_size:
            raise OSError
        _validate_private_file_v1(
            path.name,
            descriptor,
            parent_descriptor,
            device=file_identity[0],
            inode=file_identity[1],
            size=metadata.st_size,
        )
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
        return payload
    except (OSError, RuntimeError):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


def read_owner_outcomes_file_v2(
    path: Path, *, now: datetime
) -> tuple[ParsedOwnerOutcomesV2, str]:
    """Open the private file safely and return validated contents plus digest."""

    payload = _read_private_file(path)
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid") from None
    return (
        parse_owner_outcomes_document_v2(document, now=now),
        hashlib.sha256(payload).hexdigest(),
    )


def read_codex_registry_accounts_v1(
    reference: DatabaseRefV1,
    *,
    as_of: datetime,
    max_page_count: int = MAX_REGISTRY_PAGE_COUNT,
) -> tuple[OwnerAccountSelectionV1, ...]:
    """List Codex accounts through M02's public query over the real owner DB."""

    try:
        if type(max_page_count) is not int or not 1 <= max_page_count <= (
            MAX_REGISTRY_PAGE_COUNT
        ):
            raise ValueError
        reference.validate()
        repository = SqliteRegistryRepositoryV1(reference)
        before = repository.get_registry_scope_snapshot("global", None)
        if before.completeness_state != "complete":
            raise ValueError
        query = ListAccountsV1(repository)
        after_key: str | None = None
        seen_cursors: set[str] = set()
        rows: list[AccountViewV1] = []
        for _page_count in range(max_page_count):
            page = query.page("codex", as_of=as_of, limit=200, after_key=after_key)
            if page.availability.state != "available":
                raise ValueError
            rows.extend(page.items)
            if not page.has_more:
                break
            next_key = page.next_key
            if next_key is None or next_key == after_key or next_key in seen_cursors:
                raise ValueError
            seen_cursors.add(next_key)
            after_key = next_key
        else:
            raise ValueError
        if repository.get_registry_scope_snapshot("global", None) != before:
            raise ValueError
        accounts = tuple(
            OwnerAccountSelectionV1(item.account_id.value, item.friendly_name)
            for item in rows
            if item.lifecycle != "archived"
        )
        ordered = tuple(
            sorted(
                accounts,
                key=lambda item: (_normalized_alias(item.alias), item.account_id),
            )
        )
        if len({item.account_id for item in ordered}) != len(ordered) or len(
            {_normalized_alias(item.alias) for item in ordered}
        ) != len(ordered):
            raise ValueError
        return ordered
    except (OSError, RuntimeError, TypeError, ValueError):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_registry_unavailable") from None


def _open_validated_private_parent_v1(path: Path) -> tuple[int, tuple[int, int]]:
    descriptor = -1
    try:
        descriptor = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        metadata = os.fstat(descriptor)
        identity = (metadata.st_dev, metadata.st_ino)
        _validate_private_parent_v1(
            path,
            descriptor,
            device=identity[0],
            inode=identity[1],
        )
        return descriptor, identity
    except (OSError, RuntimeError):
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _require_absent_target_v1(path: Path, parent_descriptor: int) -> None:
    try:
        os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise FileExistsError


def _validate_target(path: Path) -> None:
    parent_descriptor = -1
    try:
        parent_descriptor, _identity = _open_validated_private_parent_v1(path)
        _require_absent_target_v1(path, parent_descriptor)
    except FileExistsError:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_target_exists") from None
    except (OSError, RuntimeError):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_target_invalid") from None
    finally:
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


def _unlink_created_inode_v1(
    path: Path,
    parent_descriptor: int,
    *,
    device: int,
    inode: int,
) -> None:
    try:
        current = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (device, inode):
            return
        os.unlink(path.name, dir_fd=parent_descriptor)
        os.fsync(parent_descriptor)
    except OSError:
        pass


def write_owner_outcomes_v2(path: Path, document: Mapping[str, object]) -> str:
    """Create one 0600 regular single-link file through a stable parent handle."""

    parse_owner_outcomes_document_v2(document, now=datetime.now(UTC))
    payload = (json.dumps(document, indent=2, sort_keys=False) + "\n").encode("utf-8")
    if not 2 <= len(payload) <= MAX_FILE_BYTES:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
    descriptor = -1
    parent_descriptor = -1
    created_identity: tuple[int, int] | None = None
    parent_identity: tuple[int, int] | None = None
    try:
        try:
            parent_descriptor, parent_identity = _open_validated_private_parent_v1(path)
            _require_absent_target_v1(path, parent_descriptor)
        except FileExistsError:
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_target_exists") from None
        except (OSError, RuntimeError):
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_target_invalid") from None

        descriptor = os.open(
            path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=parent_descriptor,
        )
        metadata = os.fstat(descriptor)
        created_identity = (metadata.st_dev, metadata.st_ino)
        _validate_private_file_v1(
            path.name,
            descriptor,
            parent_descriptor,
            device=created_identity[0],
            inode=created_identity[1],
            size=0,
        )
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                raise OSError
            written += count
        os.fsync(descriptor)
        _validate_private_file_v1(
            path.name,
            descriptor,
            parent_descriptor,
            device=created_identity[0],
            inode=created_identity[1],
            size=len(payload),
        )
        assert parent_identity is not None
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
        os.fsync(parent_descriptor)
        _validate_private_file_v1(
            path.name,
            descriptor,
            parent_descriptor,
            device=created_identity[0],
            inode=created_identity[1],
            size=len(payload),
        )
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
        return hashlib.sha256(payload).hexdigest()
    except FileExistsError:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_target_exists") from None
    except M5OwnerOutcomesErrorV1:
        raise
    except OSError:
        if created_identity is not None and parent_descriptor >= 0:
            _unlink_created_inode_v1(
                path,
                parent_descriptor,
                device=created_identity[0],
                inode=created_identity[1],
            )
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_write_failed") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


def _selected_service(environment: Mapping[str, str]) -> SelectedOwnerServiceV1:
    required = (
        "AGENTMONITOR_TEST_OWNER_DATA_ROOT",
        "AGENTMONITOR_TEST_DATA_ROOT",
        "AGENTMONITOR_TEST_DASHBOARD_ORIGIN",
        "AGENTMONITOR_M5_SERVICE_PID",
    )
    if not all(environment.get(key) for key in required):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_selection_required")
    raw_pid = environment["AGENTMONITOR_M5_SERVICE_PID"]
    if re.fullmatch(r"[1-9][0-9]{0,9}", raw_pid) is None:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_service_invalid")
    try:
        owner_root = Path(environment["AGENTMONITOR_TEST_OWNER_DATA_ROOT"])
        data_root = Path(environment["AGENTMONITOR_TEST_DATA_ROOT"])
        pid = int(raw_pid)
        start_ticks = _process_start_ticks(pid)
        launch = _read_service_launch(
            pid, environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"]
        )
        if (
            owner_root != data_root
            or launch.data_root != owner_root
            or _process_start_ticks(pid) != start_ticks
        ):
            raise OSError
        return SelectedOwnerServiceV1(pid, start_ticks, launch)
    except (M3CurrentExitErrorV1, OSError, RuntimeError, ValueError):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_service_invalid") from None


def _read_tty_line(prompt: str, *, maximum: int = 512) -> str:
    print(prompt, end="", flush=True)
    value = sys.stdin.readline(maximum + 2)
    if not value.endswith("\n") or len(value.encode("utf-8")) > maximum + 1:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_input_invalid")
    value = value[:-1]
    value = value.removesuffix("\r")
    if not value.isprintable():
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_input_invalid")
    return value


def _select_four_accounts(
    accounts: tuple[OwnerAccountSelectionV1, ...],
) -> tuple[OwnerAccountSelectionV1, ...]:
    if len(accounts) < 4:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_four_accounts_required")
    selected: tuple[OwnerAccountSelectionV1, ...]
    if len(accounts) == 4:
        selected = accounts
    else:
        raw = _read_tty_line(
            "Enter exactly four Codex registry account IDs separated by spaces: ",
            maximum=300,
        )
        identifiers = tuple(raw.split())
        by_id = {item.account_id: item for item in accounts}
        if (
            len(identifiers) != 4
            or len(set(identifiers)) != 4
            or any(item not in by_id for item in identifiers)
        ):
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_selection_invalid")
        selected = tuple(by_id[item] for item in identifiers)
    print("Selected M5 accounts:", flush=True)
    for account in selected:
        print(f"- {account.alias} [{account.account_id}]", flush=True)
    return selected


def _collect_outcomes(
    selected: tuple[OwnerAccountSelectionV1, ...],
) -> tuple[OwnerOutcomeV1, ...]:
    outcomes: list[OwnerOutcomeV1] = []
    for account in selected:
        disposition = _read_tty_line(
            f"Disposition for {account.alias} [{account.account_id}] "
            "(verified/owner_unavailable): ",
            maximum=64,
        )
        if disposition == "verified":
            outcomes.append(
                OwnerOutcomeV1(account.account_id, account.alias, "verified", None)
            )
        elif disposition == "owner_unavailable":
            reason = _read_tty_line(
                "Owner-unavailable reason code (lowercase letters/digits/_): ",
                maximum=96,
            )
            outcomes.append(
                OwnerOutcomeV1(
                    account.account_id,
                    account.alias,
                    "owner_unavailable",
                    reason,
                )
            )
        else:
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_disposition_invalid")
    if not any(item.disposition == "verified" for item in outcomes):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_verified_account_required")
    return tuple(outcomes)


def require_owner_confirmation_v1(value: str) -> None:
    """Accept only the exact phrase displayed at the final owner checkpoint."""

    if value != OWNER_CONFIRMATION_PHRASE:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_confirmation_required")


def create_owner_outcomes_v2(environment: Mapping[str, str]) -> str:
    """Read the real registry, obtain owner attestations, and create the file."""

    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_controlling_tty_required")
    service = _selected_service(environment)
    revision = _clean_revision()
    path = service.launch.data_root / OWNER_OUTCOMES_BASENAME
    _validate_target(path)
    reference = DatabaseRefV1(
        service.launch.data_root / "agentmonitor.db", service.launch.data_root
    )
    accounts = read_codex_registry_accounts_v1(reference, as_of=datetime.now(UTC))
    selected = _select_four_accounts(accounts)
    outcomes = _collect_outcomes(selected)
    print("Owner outcomes to record:", flush=True)
    for item in outcomes:
        suffix = f" ({item.reason})" if item.reason is not None else ""
        print(
            f"- {item.alias} [{item.account_id}]: {item.disposition}{suffix}",
            flush=True,
        )
    confirmation = _read_tty_line(
        f"Type {OWNER_CONFIRMATION_PHRASE!r} to create the private file: ",
        maximum=len(OWNER_CONFIRMATION_PHRASE),
    )
    require_owner_confirmation_v1(confirmation)
    confirmed_at = datetime.now(UTC)
    try:
        if (
            _clean_revision() != revision
            or _process_start_ticks(service.pid) != service.start_time_ticks
            or _read_service_launch(
                service.pid, environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"]
            )
            != service.launch
        ):
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_context_changed")
    except M3CurrentExitErrorV1:
        raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_context_changed") from None
    document = build_owner_outcomes_document_v2(
        implementation_revision=revision,
        service_pid=service.pid,
        service_start_time_ticks=service.start_time_ticks,
        owner_confirmed_at=confirmed_at,
        outcomes=outcomes,
    )
    return write_owner_outcomes_v2(path, document)


def main() -> int:
    try:
        create_owner_outcomes_v2(os.environ)
    except (M5OwnerOutcomesErrorV1, M3CurrentExitErrorV1) as error:
        print(f"M5 OWNER OUTCOMES: BLOCKED — {error}")
        return 3
    except (OSError, RuntimeError, TypeError, ValueError):
        print("M5 OWNER OUTCOMES: FAILED — execution_unavailable")
        return 1
    print(
        "M5 OWNER OUTCOMES: PASSED — four explicit service-bound outcomes "
        "recorded in one private create-once file"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
