"""Canonical fail-closed technical exit gate for the approved V1-M6 scope.

The command runs the available canonical checks and discovers bounded,
machine-produced real-evidence selector receipts. It does not collect
credentials, prompt for owner decisions, activate a service, or manufacture
unavailable provider/platform observations.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from tools.automation.implementations.m6_exit_policy import (
    ACCEPTANCE_IDS,
    REQUIRED_CHECKS,
    SELECTOR_REQUIREMENTS,
    STORY_IDS,
    M6EvidenceEvaluationV1,
    StatusV1,
    assemble_selector_bundle_v1,
    build_passed_receipt_v1,
    evaluate_evidence_bundle_v1,
    external_scope_status_v1,
    validate_catalog_v1,
    validate_existing_passed_receipt_v1,
)

ROOT = Path(__file__).resolve().parents[3]
CATALOG_NAME = "m6-exit-catalog-v1.json"
MAX_JSON_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
CHECK_TIMEOUT_SECONDS = {
    "AUTO-BUILD": 1800,
    "AUTO-M6-LOCAL-ADMIT": 1200,
    "AUTO-QUALITY": 1800,
    "AUTO-DOCS-CHECK": 1800,
    "AUTO-PLAN-CHECK": 1800,
}
SELECTOR_PRODUCER_TIMEOUT_SECONDS = 1800


class M6ExitErrorV1(ValueError):
    """One sanitized gate-owned artifact or execution error."""


class M6ExitBlockedV1(M6ExitErrorV1):
    """A real prerequisite is absent, stale, busy, or otherwise unavailable."""


@dataclass(slots=True)
class _DirectoryChainV1:
    """Pinned descriptor-relative directory chain rooted at the checkout."""

    root_path: Path
    descriptors: list[int]
    entries: list[tuple[int, str, tuple[int, int, int, int, int]]]
    root_identity: tuple[int, int, int, int, int]

    @property
    def leaf_fd(self) -> int:
        return self.descriptors[-1]

    def revalidate(self) -> None:
        try:
            current_root = self.root_path.lstat()
        except OSError:
            raise M6ExitBlockedV1("m6_directory_chain_changed") from None
        if _directory_identity(current_root) != self.root_identity:
            raise M6ExitBlockedV1("m6_directory_chain_changed")
        for parent_fd, name, expected in self.entries:
            try:
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except OSError:
                raise M6ExitBlockedV1("m6_directory_chain_changed") from None
            if _directory_identity(current) != expected:
                raise M6ExitBlockedV1("m6_directory_chain_changed")

    def close(self) -> None:
        for descriptor in reversed(self.descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise M6ExitErrorV1("m6_json_duplicate_key")
        result[key] = value
    return result


def _load_json_bytes(payload: bytes) -> object:
    if not payload or len(payload) > MAX_JSON_BYTES:
        raise M6ExitErrorV1("m6_json_size_invalid")
    try:
        return json.loads(
            payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise M6ExitErrorV1("m6_json_invalid") from None


def _directory_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
    )


def _file_identity(
    metadata: os.stat_result,
) -> tuple[int, int, int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _safe_component(value: str) -> bool:
    return (
        bool(value)
        and value not in {".", ".."}
        and "/" not in value
        and "\x00" not in value
    )


@contextmanager
def _open_directory_chain(
    parts: tuple[str, ...],
    *,
    private: bool,
    root_path: Path = ROOT,
) -> Iterator[_DirectoryChainV1]:
    """Open every component without following links and retain all ancestors."""

    if any(not _safe_component(part) for part in parts):
        raise M6ExitErrorV1("m6_directory_component_invalid")
    descriptors: list[int] = []
    entries: list[tuple[int, str, tuple[int, int, int, int, int]]] = []
    try:
        before_root = root_path.lstat()
        if not stat.S_ISDIR(before_root.st_mode):
            raise M6ExitErrorV1("m6_checkout_root_invalid")
        root_fd = os.open(
            root_path,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        descriptors.append(root_fd)
        opened_root = os.fstat(root_fd)
        root_identity = _directory_identity(opened_root)
        if root_identity != _directory_identity(before_root):
            raise M6ExitBlockedV1("m6_directory_chain_changed")
        parent_fd = root_fd
        for part in parts:
            try:
                child_fd = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=parent_fd,
                )
            except FileNotFoundError:
                raise
            except OSError as error:
                if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise M6ExitErrorV1("m6_directory_chain_invalid") from None
                raise M6ExitBlockedV1("m6_directory_chain_unavailable") from None
            try:
                child = os.fstat(child_fd)
                child_entry = os.stat(part, dir_fd=parent_fd, follow_symlinks=False)
            except OSError:
                os.close(child_fd)
                raise M6ExitBlockedV1("m6_directory_chain_changed") from None
            identity = _directory_identity(child)
            if identity != _directory_identity(child_entry) or not stat.S_ISDIR(
                child.st_mode
            ):
                os.close(child_fd)
                raise M6ExitBlockedV1("m6_directory_chain_changed")
            if private and (
                child.st_uid != os.getuid() or stat.S_IMODE(child.st_mode) != 0o700
            ):
                os.close(child_fd)
                raise M6ExitErrorV1("m6_private_evidence_root_invalid")
            entries.append((parent_fd, part, identity))
            descriptors.append(child_fd)
            parent_fd = child_fd
        chain = _DirectoryChainV1(
            root_path=root_path,
            descriptors=descriptors,
            entries=entries,
            root_identity=root_identity,
        )
        chain.revalidate()
        yield chain
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _read_regular_at(
    chain: _DirectoryChainV1,
    name: str,
    *,
    private: bool,
    limit: int,
    missing_reason: str,
) -> bytes:
    if not _safe_component(name):
        raise M6ExitErrorV1("m6_evidence_path_invalid")
    try:
        before = os.stat(name, dir_fd=chain.leaf_fd, follow_symlinks=False)
    except FileNotFoundError:
        raise M6ExitErrorV1(missing_reason) from None
    except OSError:
        raise M6ExitBlockedV1("m6_evidence_unavailable") from None
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size < 1
        or before.st_size > limit
        or (
            private
            and (before.st_uid != os.getuid() or stat.S_IMODE(before.st_mode) != 0o600)
        )
    ):
        raise M6ExitErrorV1("m6_evidence_file_invalid")
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=chain.leaf_fd,
        )
        opened = os.fstat(descriptor)
        identity = _file_identity(before)
        if _file_identity(opened) != identity:
            raise M6ExitBlockedV1("m6_evidence_changed")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise M6ExitErrorV1("m6_evidence_file_invalid")
        after_fd = os.fstat(descriptor)
        after_entry = os.stat(name, dir_fd=chain.leaf_fd, follow_symlinks=False)
        if (
            _file_identity(after_fd) != identity
            or _file_identity(after_entry) != identity
        ):
            raise M6ExitBlockedV1("m6_evidence_changed")
        chain.revalidate()
        return b"".join(chunks)
    except M6ExitErrorV1:
        raise
    except OSError:
        raise M6ExitBlockedV1("m6_evidence_unavailable") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _git_revision() -> str:
    try:
        before = subprocess.run(
            ["/usr/bin/git", "rev-parse", "--verify", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        status_result = subprocess.run(
            ["/usr/bin/git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        after = subprocess.run(
            ["/usr/bin/git", "rev-parse", "--verify", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise M6ExitBlockedV1("m6_checkout_unavailable") from None
    value = before.stdout.strip()
    if (
        before.returncode
        or after.returncode
        or after.stdout.strip() != value
        or len(value) != 40
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise M6ExitBlockedV1("m6_checkout_unavailable")
    if status_result.returncode:
        raise M6ExitBlockedV1("m6_checkout_unavailable")
    if status_result.stdout:
        raise M6ExitBlockedV1("m6_checkout_not_clean")
    return value


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_catalog() -> tuple[dict[str, object], bytes, str]:
    try:
        with _open_directory_chain(("tools", "automation"), private=False) as chain:
            payload = _read_regular_at(
                chain,
                CATALOG_NAME,
                private=False,
                limit=MAX_JSON_BYTES,
                missing_reason="m6_catalog_missing",
            )
    except FileNotFoundError:
        raise M6ExitErrorV1("m6_catalog_missing") from None
    except OSError:
        raise M6ExitErrorV1("m6_catalog_path_invalid") from None
    parsed = _load_json_bytes(payload)
    errors = validate_catalog_v1(parsed)
    if errors or not isinstance(parsed, dict):
        raise M6ExitErrorV1(errors[0] if errors else "m6_catalog_invalid")
    return parsed, payload, _sha256(payload)


def _read_routine_states() -> dict[str, str]:
    try:
        with _open_directory_chain(("tools", "automation"), private=False) as chain:
            payload = _read_regular_at(
                chain,
                "routines.toml",
                private=False,
                limit=MAX_JSON_BYTES,
                missing_reason="m6_routine_catalog_missing",
            )
        parsed = tomllib.loads(payload.decode("utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise M6ExitErrorV1("m6_routine_catalog_invalid") from None
    routines = parsed.get("routines")
    if not isinstance(routines, list):
        raise M6ExitErrorV1("m6_routine_catalog_invalid")
    states: dict[str, str] = {}
    for raw in routines:
        if not isinstance(raw, dict):
            raise M6ExitErrorV1("m6_routine_catalog_invalid")
        command_id = raw.get("id")
        status = raw.get("status")
        if not isinstance(command_id, str) or not isinstance(status, str):
            raise M6ExitErrorV1("m6_routine_catalog_invalid")
        if command_id in states:
            raise M6ExitErrorV1("m6_routine_catalog_invalid")
        states[command_id] = status
    return states


def _read_selector_receipts(
    allowed_selector_ids: frozenset[str],
) -> tuple[tuple[object, ...], str]:
    """Discover fixed machine receipts; absence means selectors were Not Run."""

    try:
        chain_context = _open_directory_chain(
            (".agentmonitor-local", "m6-evidence", "selectors"), private=True
        )
        with chain_context as chain:
            names = sorted(os.listdir(chain.leaf_fd))
            if len(names) > 128:
                raise M6ExitErrorV1("m6_selector_receipt_count_invalid")
            receipts: list[object] = []
            digest = hashlib.sha256()
            for name in names:
                if (
                    not _safe_component(name)
                    or name.startswith(".")
                    or not name.endswith(".json")
                ):
                    raise M6ExitErrorV1("m6_selector_receipt_name_invalid")
                try:
                    encoded_name = name.encode("ascii")
                except UnicodeEncodeError:
                    raise M6ExitErrorV1("m6_selector_receipt_name_invalid") from None
                selector_id = name.removesuffix(".json")
                known_selectors = {item[1] for item in SELECTOR_REQUIREMENTS}
                if selector_id not in known_selectors:
                    raise M6ExitErrorV1("m6_selector_receipt_name_invalid")
                if selector_id not in allowed_selector_ids:
                    continue
                payload = _read_regular_at(
                    chain,
                    name,
                    private=True,
                    limit=MAX_JSON_BYTES,
                    missing_reason="m6_selector_receipt_changed",
                )
                parsed = _load_json_bytes(payload)
                if (
                    not isinstance(parsed, dict)
                    or parsed.get("selector_id") != selector_id
                ):
                    raise M6ExitErrorV1("m6_selector_receipt_name_invalid")
                digest.update(encoded_name + b"\0" + payload)
                receipts.append(parsed)
            if sorted(os.listdir(chain.leaf_fd)) != names:
                raise M6ExitBlockedV1("m6_selector_receipts_changed")
            chain.revalidate()
            return tuple(receipts), digest.hexdigest()
    except FileNotFoundError:
        return (), _sha256(b"")
    except M6ExitErrorV1:
        raise
    except OSError:
        raise M6ExitBlockedV1("m6_selector_receipts_unavailable") from None


def _artifact_parts(relative: object) -> tuple[tuple[str, ...], str, bool]:
    if not isinstance(relative, str):
        raise M6ExitErrorV1("m6_evidence_path_invalid")
    parts = tuple(relative.split("/"))
    if any(not _safe_component(part) for part in parts):
        raise M6ExitErrorV1("m6_evidence_path_invalid")
    if parts[:2] == ("docs", "evidence") and len(parts) >= 3:
        return parts[:-1], parts[-1], False
    if parts[:2] == (".agentmonitor-local", "m6-evidence") and len(parts) >= 3:
        return parts[:-1], parts[-1], True
    raise M6ExitErrorV1("m6_evidence_path_invalid")


def _validate_artifact_digests(bundle: dict[str, object]) -> None:
    evidence = bundle.get("evidence")
    if not isinstance(evidence, list):
        raise M6ExitErrorV1("m6_evidence_entries_invalid")
    for item in evidence:
        if not isinstance(item, dict):
            raise M6ExitErrorV1("m6_evidence_entry_shape_invalid")
        directory_parts, name, private = _artifact_parts(item.get("path"))
        try:
            with _open_directory_chain(directory_parts, private=private) as chain:
                payload = _read_regular_at(
                    chain,
                    name,
                    private=private,
                    limit=MAX_ARTIFACT_BYTES,
                    missing_reason="m6_evidence_artifact_missing",
                )
        except FileNotFoundError:
            raise M6ExitErrorV1("m6_evidence_artifact_missing") from None
        except M6ExitErrorV1:
            raise
        except OSError:
            raise M6ExitErrorV1("m6_evidence_artifact_path_invalid") from None
        if _sha256(payload) != item.get("sha256"):
            raise M6ExitErrorV1("m6_evidence_digest_mismatch")


def _empty_statuses() -> tuple[dict[str, StatusV1], dict[str, StatusV1]]:
    return (
        {key: "not_run" for key in ACCEPTANCE_IDS},
        {key: "not_run" for key in STORY_IDS},
    )


def _exit_code(status: StatusV1) -> int:
    return 0 if status == "passed" else 1 if status == "failed" else 3


def _print_result(
    *,
    status: StatusV1,
    revision: str | None,
    catalog_digest: str | None,
    evidence_digest: str | None,
    acceptance: dict[str, StatusV1],
    stories: dict[str, StatusV1],
    checks: dict[str, StatusV1],
    reason_codes: tuple[str, ...],
    evidence_count: int,
    declared_limitations: tuple[str, ...],
    receipt_path: str | None,
) -> None:
    print(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "record_type": "agentmonitor.m6_technical_exit_result.v1",
                "command_id": "AUTO-M6-EXIT",
                "milestone_id": "V1-M6",
                "overall_status": status,
                "exit_code": _exit_code(status),
                "implementation_revision": revision,
                "catalog_sha256": catalog_digest,
                "selector_receipts_sha256": evidence_digest,
                "acceptance": acceptance,
                "stories": stories,
                "checks": checks,
                "reason_codes": list(dict.fromkeys(reason_codes)),
                "evidence_count": evidence_count,
                "declared_limitations": list(declared_limitations),
                "receipt_path": receipt_path,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(f"M6 TECHNICAL EXIT: {status.upper().replace('_', ' ')}")


def _stop(
    status: StatusV1,
    reason: str,
    *,
    revision: str | None = None,
    catalog_digest: str | None = None,
    evidence_digest: str | None = None,
    evaluation: M6EvidenceEvaluationV1 | None = None,
    checks: dict[str, StatusV1] | None = None,
) -> NoReturn:
    acceptance, stories = _empty_statuses()
    reasons: tuple[str, ...] = (reason,)
    evidence_count = 0
    limitations: tuple[str, ...] = ()
    if evaluation is not None:
        acceptance = dict(evaluation.acceptance)
        stories = dict(evaluation.stories)
        reasons = tuple(dict.fromkeys((*evaluation.reason_codes, reason)))
        evidence_count = evaluation.evidence_count
        limitations = evaluation.declared_limitations
    _print_result(
        status=status,
        revision=revision,
        catalog_digest=catalog_digest,
        evidence_digest=evidence_digest,
        acceptance=acceptance,
        stories=stories,
        checks=checks or {key: "not_run" for key in REQUIRED_CHECKS},
        reason_codes=reasons,
        evidence_count=evidence_count,
        declared_limitations=limitations,
        receipt_path=None,
    )
    raise SystemExit(_exit_code(status))


def _process_group_absent(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _terminate_process_group(process: subprocess.Popen[bytes]) -> bool:
    """Bound and confirm cleanup of one check's dedicated process group."""

    group_id = process.pid
    if process.poll() is None:
        try:
            os.killpg(group_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
    if not _process_group_absent(group_id):
        try:
            os.killpg(group_id, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        return False
    deadline = time.monotonic() + 2
    while not _process_group_absent(group_id) and time.monotonic() < deadline:
        time.sleep(0.05)
    return _process_group_absent(group_id)


def _run_command(command_id: str, *, timeout_seconds: int) -> StatusV1:
    try:
        process = subprocess.Popen(
            [sys.executable, "tools/automation/run.py", command_id],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return "blocked"
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return "blocked" if _terminate_process_group(process) else "failed"
    except BaseException:
        _terminate_process_group(process)
        raise
    if not _process_group_absent(process.pid):
        _terminate_process_group(process)
        return "failed"
    if return_code == 0:
        return "passed"
    return "blocked" if return_code == 3 else "failed"


def _run_checks() -> dict[str, StatusV1]:
    return {
        command_id: _run_command(
            command_id, timeout_seconds=CHECK_TIMEOUT_SECONDS[command_id]
        )
        for command_id in REQUIRED_CHECKS
    }


def _run_available_selector_producers(
    *,
    checks_passed: bool,
) -> tuple[dict[str, StatusV1], frozenset[str]]:
    statuses: dict[str, StatusV1] = {
        requirement[1]: "not_run" for requirement in SELECTOR_REQUIREMENTS
    }
    if not checks_passed:
        return statuses, frozenset()
    routine_states = _read_routine_states()
    executed: set[str] = set()
    for requirement in SELECTOR_REQUIREMENTS:
        selector_id = requirement[1]
        command_id = requirement[3]
        routine_state = routine_states.get(command_id)
        if routine_state == "blocked":
            statuses[selector_id] = "blocked"
            continue
        if routine_state not in {"operational", "operational_limited"}:
            continue
        statuses[selector_id] = _run_command(
            command_id, timeout_seconds=SELECTOR_PRODUCER_TIMEOUT_SECONDS
        )
        executed.add(selector_id)
    return statuses, frozenset(executed)


def _checks_status(checks: dict[str, StatusV1]) -> StatusV1:
    values = tuple(checks.values())
    if "failed" in values:
        return "failed"
    if "blocked" in values:
        return "blocked"
    if "not_run" in values:
        return "not_run"
    return "passed"


def _combine_statuses(*statuses: StatusV1) -> StatusV1:
    if "failed" in statuses:
        return "failed"
    if "blocked" in statuses:
        return "blocked"
    if "not_run" in statuses:
        return "not_run"
    return "passed"


@contextmanager
def _open_receipt_directory() -> Iterator[_DirectoryChainV1]:
    try:
        with _open_directory_chain((".agentmonitor-local",), private=True) as local:
            try:
                os.mkdir("m6-exit-receipts", mode=0o700, dir_fd=local.leaf_fd)
                os.fsync(local.leaf_fd)
            except FileExistsError:
                pass
            except OSError:
                raise M6ExitBlockedV1("m6_receipt_root_unavailable") from None
            local.revalidate()
            with _open_directory_chain(
                (".agentmonitor-local", "m6-exit-receipts"), private=True
            ) as receipts:
                if receipts.entries[0][2] != local.entries[0][2]:
                    raise M6ExitBlockedV1("m6_receipt_root_changed")
                yield receipts
    except FileNotFoundError:
        raise M6ExitBlockedV1("m6_receipt_root_unavailable") from None
    except M6ExitErrorV1:
        raise
    except OSError:
        raise M6ExitBlockedV1("m6_receipt_root_unavailable") from None


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise M6ExitBlockedV1("m6_receipt_write_incomplete")
        offset += written


def _unlink_created_receipt(
    parent_fd: int,
    name: str,
    *,
    created_fd: int,
) -> bool:
    try:
        created = os.fstat(created_fd)
    except OSError:
        return False
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    if (current.st_dev, current.st_ino) != (created.st_dev, created.st_ino):
        return False
    try:
        os.unlink(name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except OSError:
        return False
    return True


def _write_or_validate_receipt(
    revision: str,
    receipt: dict[str, object],
    *,
    revalidate_snapshot: Callable[[], None],
) -> str:
    name = f"{revision}.json"
    payload = (
        json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    created = False
    with _open_receipt_directory() as directory:
        revalidate_snapshot()
        descriptor = -1
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=directory.leaf_fd,
            )
        except FileExistsError:
            current = _read_regular_at(
                directory,
                name,
                private=True,
                limit=MAX_JSON_BYTES,
                missing_reason="m6_receipt_changed",
            )
            parsed = _load_json_bytes(current)
            errors = validate_existing_passed_receipt_v1(
                parsed, expected=receipt, now=datetime.now(UTC)
            )
            if errors:
                raise M6ExitErrorV1(errors[0])
            revalidate_snapshot()
            if (
                _read_regular_at(
                    directory,
                    name,
                    private=True,
                    limit=MAX_JSON_BYTES,
                    missing_reason="m6_receipt_changed",
                )
                != current
            ):
                raise M6ExitErrorV1("m6_receipt_changed")
            return str(Path(".agentmonitor-local/m6-exit-receipts") / name)
        except OSError:
            raise M6ExitBlockedV1("m6_receipt_unavailable") from None
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_uid != os.getuid()
                or stat.S_IMODE(opened.st_mode) != 0o600
                or opened.st_nlink != 1
            ):
                raise M6ExitErrorV1("m6_receipt_file_invalid")
            created = True
            _write_all(descriptor, payload)
            os.fsync(descriptor)
            os.fsync(directory.leaf_fd)
            current = _read_regular_at(
                directory,
                name,
                private=True,
                limit=MAX_JSON_BYTES,
                missing_reason="m6_receipt_changed",
            )
            if current != payload:
                raise M6ExitErrorV1("m6_receipt_changed")
            revalidate_snapshot()
            final_current = _read_regular_at(
                directory,
                name,
                private=True,
                limit=MAX_JSON_BYTES,
                missing_reason="m6_receipt_changed",
            )
            if final_current != payload:
                raise M6ExitErrorV1("m6_receipt_changed")
            os.close(descriptor)
            descriptor = -1
        except BaseException:
            cleanup_ok = True
            if created and descriptor >= 0:
                cleanup_ok = _unlink_created_receipt(
                    directory.leaf_fd,
                    name,
                    created_fd=descriptor,
                )
            if descriptor >= 0:
                os.close(descriptor)
            if not cleanup_ok:
                raise M6ExitBlockedV1("m6_receipt_cleanup_identity_changed") from None
            raise
        return str(Path(".agentmonitor-local/m6-exit-receipts") / name)


def _revalidate_completion_snapshot(
    *,
    revision: str,
    catalog: dict[str, object],
    catalog_digest: str,
    selector_receipts: tuple[object, ...],
    selector_digest: str,
    allowed_selector_ids: frozenset[str],
    bundle: dict[str, object],
) -> None:
    if _git_revision() != revision:
        raise M6ExitBlockedV1("m6_checkout_changed")
    _, _, current_catalog_digest = _read_catalog()
    if current_catalog_digest != catalog_digest:
        raise M6ExitBlockedV1("m6_catalog_changed")
    current_receipts, current_selector_digest = _read_selector_receipts(
        allowed_selector_ids
    )
    if (
        current_selector_digest != selector_digest
        or current_receipts != selector_receipts
    ):
        raise M6ExitBlockedV1("m6_evidence_changed")
    _validate_artifact_digests(bundle)
    current_evaluation = evaluate_evidence_bundle_v1(
        bundle,
        catalog=catalog,
        expected_revision=revision,
        expected_catalog_sha256=catalog_digest,
        now=datetime.now(UTC),
    )
    if external_scope_status_v1(current_evaluation) != "passed":
        raise M6ExitBlockedV1("m6_evidence_no_longer_current")
    if _git_revision() != revision:
        raise M6ExitBlockedV1("m6_checkout_changed")


def main() -> int:
    revision: str | None = None
    catalog_digest: str | None = None
    evidence_digest: str | None = None
    evaluation: M6EvidenceEvaluationV1 | None = None
    checks: dict[str, StatusV1] = {key: "not_run" for key in REQUIRED_CHECKS}
    receipt_path: str | None = None
    try:
        catalog, _, catalog_digest = _read_catalog()
        revision = _git_revision()
        checks = _run_checks()
        if _git_revision() != revision:
            raise M6ExitBlockedV1("m6_checkout_changed")
        producer_statuses, executed_selector_ids = _run_available_selector_producers(
            checks_passed=_checks_status(checks) == "passed"
        )
        selector_receipts, evidence_digest = _read_selector_receipts(
            executed_selector_ids
        )
        recorded_at = datetime.now(UTC)
        bundle = assemble_selector_bundle_v1(
            selector_receipts,
            catalog=catalog,
            producer_statuses=producer_statuses,
            expected_revision=revision,
            catalog_sha256=catalog_digest,
            recorded_at=recorded_at,
        )
        evaluation = evaluate_evidence_bundle_v1(
            bundle,
            catalog=catalog,
            expected_revision=revision,
            expected_catalog_sha256=catalog_digest,
            now=recorded_at,
        )
        combined_status = _combine_statuses(
            _checks_status(checks), external_scope_status_v1(evaluation)
        )
        if combined_status != "passed":
            _stop(
                combined_status,
                "m6_required_scope_not_passed",
                revision=revision,
                catalog_digest=catalog_digest,
                evidence_digest=evidence_digest,
                evaluation=evaluation,
                checks=checks,
            )
        _revalidate_completion_snapshot(
            revision=revision,
            catalog=catalog,
            catalog_digest=catalog_digest,
            selector_receipts=selector_receipts,
            selector_digest=evidence_digest,
            allowed_selector_ids=executed_selector_ids,
            bundle=bundle,
        )
        if (
            evaluation.selection_sha256 is None
            or evaluation.source_versions_sha256 is None
        ):
            raise M6ExitErrorV1("m6_selector_digest_missing")
        receipt = build_passed_receipt_v1(
            implementation_revision=revision,
            catalog_sha256=catalog_digest,
            selector_receipts_sha256=evidence_digest,
            selection_sha256=evaluation.selection_sha256,
            source_versions_sha256=evaluation.source_versions_sha256,
            completed_at=datetime.now(UTC),
            evidence_count=evaluation.evidence_count,
            required_checks=REQUIRED_CHECKS,
            declared_limitations=evaluation.declared_limitations,
        )
        receipt_path = _write_or_validate_receipt(
            revision,
            receipt,
            revalidate_snapshot=lambda: _revalidate_completion_snapshot(
                revision=revision,
                catalog=catalog,
                catalog_digest=catalog_digest,
                selector_receipts=selector_receipts,
                selector_digest=evidence_digest,
                allowed_selector_ids=executed_selector_ids,
                bundle=bundle,
            ),
        )
    except M6ExitBlockedV1 as error:
        _stop(
            "blocked",
            str(error),
            revision=revision,
            catalog_digest=catalog_digest,
            evidence_digest=evidence_digest,
            evaluation=evaluation,
            checks=checks,
        )
    except (M6ExitErrorV1, OSError, TypeError, ValueError) as error:
        reason = str(error)
        if not reason.startswith("m6_"):
            reason = "m6_gate_internal_error"
        _stop(
            "failed",
            reason,
            revision=revision,
            catalog_digest=catalog_digest,
            evidence_digest=evidence_digest,
            evaluation=evaluation,
            checks=checks,
        )
    _print_result(
        status="passed",
        revision=revision,
        catalog_digest=catalog_digest,
        evidence_digest=evidence_digest,
        acceptance=dict(evaluation.acceptance),
        stories=dict(evaluation.stories),
        checks=checks,
        reason_codes=(),
        evidence_count=evaluation.evidence_count,
        declared_limitations=evaluation.declared_limitations,
        receipt_path=receipt_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
