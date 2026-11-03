"""Canonical fail-closed technical exit gate for the approved V1-M6 scope.

The command runs the available canonical checks and creates one bounded,
machine-produced real-evidence artifact. It does not collect
credentials, prompt for owner decisions, activate a service, or manufacture
unavailable provider/platform observations.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import select
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NoReturn

from tools.automation.implementations.m6_authoritative_evidence import (
    AuthoritativeComparisonV1,
    parse_authoritative_comparison_v1,
)
from tools.automation.implementations.m6_direct_evidence import (
    DIRECT_EXECUTABLE_SELECTION_V1,
    BoundaryCheckV1,
    DirectM6FactsV1,
    DirectM6OutcomeV1,
    LocalModelHostEvidenceV1,
    classify_direct_m6_evidence_v1,
    direct_bundle_v1,
)
from tools.automation.implementations.m6_exit_policy import (
    ACCEPTANCE_IDS,
    REQUIRED_CHECKS,
    STORY_IDS,
    M6EvidenceEvaluationV1,
    StatusV1,
    build_passed_receipt_v1,
    evaluate_evidence_bundle_v1,
    external_scope_status_v1,
    validate_catalog_v1,
    validate_existing_passed_receipt_v1,
)
from tools.automation.implementations.m6_recovery_evidence import (
    RecoveryIntervalEvidenceV1,
    parse_recovery_interval_v1,
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
DIRECT_CHECK_TIMEOUT_SECONDS = {
    "local_inventory": 120,
    "account_admin_browser": 120,
    "source_security": 300,
    "database_snapshot": 60,
    "recovery_interval": 660,
    "authoritative_comparison": 90,
    "authoritative_policy": 15,
}
DIRECT_SNAPSHOT_KEYS = (
    "active_ollama_accounts",
    "registered_local_installations",
    "observed_local_installations",
    "active_cloud_targets",
    "owner_confirmed_cloud_targets",
    "owner_confirmed_required_scopes",
    "verified_cloud_targets",
    "current_balance_targets",
    "history_targets",
    "configured_alert_targets",
    "alerted_targets",
    "process_observation_count",
    "natural_recovery_targets",
    "cross_provider_continuity_targets",
)
DIRECT_SNAPSHOT_DIGEST_KEYS = (
    "current_balance_lineage_sha256",
    "current_history_lineage_sha256",
)
_EMPTY_LINEAGE_SHA256 = hashlib.sha256(b"").hexdigest()
DIRECT_SNAPSHOT_SCHEMA_STATES = frozenset(
    {
        "missing",
        "empty",
        "upgrade_required",
        "compatible",
        "newer_than_binary",
        "locked",
        "unreadable",
        "corrupt",
        "unknown_revision",
        "multiple_heads",
        "checksum_mismatch",
        "policy_incompatible",
        "migration_failed",
    }
)
PROJECT_BACKEND_VENV = Path("/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv")
PROJECT_NODE_MODULES = Path(
    "/home/dev/Nextcloud/Code/AI/AgentMonitor/frontend/node_modules"
)


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
    root_path: Path | None = None,
) -> Iterator[_DirectoryChainV1]:
    """Open every component without following links and retain all ancestors."""

    if root_path is None:
        root_path = ROOT
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
    artifact_path: str | None = None,
    scope_reason_codes: dict[str, str] | None = None,
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
                "direct_evidence_sha256": evidence_digest,
                "direct_evidence_path": artifact_path,
                "acceptance": acceptance,
                "stories": stories,
                "checks": checks,
                "reason_codes": list(dict.fromkeys(reason_codes)),
                "scope_reason_codes": scope_reason_codes or {},
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
    artifact_path: str | None = None,
    scope_reason_codes: dict[str, str] | None = None,
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
        artifact_path=artifact_path,
        scope_reason_codes=scope_reason_codes,
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
            [sys.executable, "-B", "tools/automation/run.py", command_id],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return "blocked"
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate_process_group(process)
        return "failed"
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


def _tool_target_identity(path: Path) -> tuple[int, int, int, int, int]:
    """Return the stable outer identity of one reviewed installed tool tree."""

    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError:
        raise M6ExitBlockedV1("m6_tool_environment_unavailable") from None
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink < 2
    ):
        raise M6ExitErrorV1("m6_tool_environment_invalid")
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_nlink,
    )


def _create_tool_link(path: Path, target: Path) -> tuple[int, int] | None:
    """Create one exact ignored checkout link, or validate an existing tree."""

    if path.exists() or path.is_symlink():
        if path.is_symlink():
            try:
                if path.resolve(strict=True) != target.resolve(strict=True):
                    raise M6ExitErrorV1("m6_tool_environment_invalid")
            except OSError:
                raise M6ExitBlockedV1("m6_tool_environment_unavailable") from None
        elif not path.is_dir():
            raise M6ExitErrorV1("m6_tool_environment_invalid")
        return None
    try:
        path.symlink_to(target, target_is_directory=True)
        metadata = path.lstat()
    except OSError:
        raise M6ExitBlockedV1("m6_tool_environment_unavailable") from None
    if not stat.S_ISLNK(metadata.st_mode) or path.readlink() != target:
        raise M6ExitBlockedV1("m6_tool_environment_changed")
    return metadata.st_dev, metadata.st_ino


def _remove_tool_link(path: Path, target: Path, identity: tuple[int, int]) -> None:
    """Remove only the exact symlink created by this gate invocation."""

    try:
        metadata = path.lstat()
        if (
            not stat.S_ISLNK(metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino) != identity
            or path.readlink() != target
        ):
            raise M6ExitBlockedV1("m6_tool_environment_cleanup_changed")
        path.unlink()
        parent = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except M6ExitErrorV1:
        raise
    except OSError:
        raise M6ExitBlockedV1("m6_tool_environment_cleanup_unavailable") from None


@contextmanager
def _temporary_tool_environment() -> Iterator[None]:
    """Expose reviewed installed tools while their ordinary checks run.

    AUTO-BUILD and AUTO-QUALITY remain responsible for exact dependency,
    version, lockfile and license admission.  These links only let a clean
    isolated worktree use the independent development Python environment and
    the project's installed Node dependency tree.  It never points build or
    lint commands at a sealed deployed release runtime.
    """

    targets = (
        (ROOT / "backend/.venv", PROJECT_BACKEND_VENV),
        (ROOT / "frontend/node_modules", PROJECT_NODE_MODULES),
    )
    target_identities = {target: _tool_target_identity(target) for _, target in targets}
    created: list[tuple[Path, Path, tuple[int, int]]] = []
    try:
        for path, target in targets:
            identity = _create_tool_link(path, target)
            if identity is not None:
                created.append((path, target, identity))
        yield
        for target, expected in target_identities.items():
            if _tool_target_identity(target) != expected:
                raise M6ExitBlockedV1("m6_tool_environment_changed")
    finally:
        cleanup_error: M6ExitErrorV1 | None = None
        for path, target, identity in reversed(created):
            try:
                _remove_tool_link(path, target, identity)
            except M6ExitErrorV1 as error:
                cleanup_error = error
        if cleanup_error is not None:
            raise cleanup_error


def _boundary(status: StatusV1, reason_code: str | None = None) -> BoundaryCheckV1:
    if status != "passed" and reason_code is None:
        reason_code = {
            "failed": "real_boundary_check_failed",
            "blocked": "real_boundary_unavailable",
            "not_run": "real_boundary_not_run",
        }[status]
    return BoundaryCheckV1(
        status,
        1 if status in {"passed", "failed"} else 0,
        reason_code=reason_code,
    )


def _direct_command(name: str, revision: str) -> list[str]:
    templates = dict(DIRECT_EXECUTABLE_SELECTION_V1)
    try:
        arguments = templates[name]
    except KeyError:
        raise M6ExitErrorV1("m6_direct_command_unknown") from None
    replacements = {
        "{gate_python}": sys.executable,
        "{checkout_python}": str(ROOT / "backend/.venv/bin/python"),
        "{revision}": revision,
    }
    return [replacements.get(value, value) for value in arguments]


@dataclass(frozen=True, slots=True)
class _ProcessResultV1:
    launched: bool
    return_code: int | None
    timed_out: bool
    cleanup_confirmed: bool
    output: bytes


def _run_direct_argv(
    arguments: list[str],
    *,
    timeout_seconds: int,
    capture_output: bool = False,
) -> _ProcessResultV1:
    """Run one fixed bounded check with a hard stdout-ingress limit."""

    try:
        process = subprocess.Popen(
            arguments,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return _ProcessResultV1(False, None, False, True, b"")
    output = bytearray()
    deadline = time.monotonic() + timeout_seconds
    try:
        if capture_output:
            if process.stdout is None:
                _terminate_process_group(process)
                return _ProcessResultV1(True, None, False, False, b"")
            descriptor = process.stdout.fileno()
            os.set_blocking(descriptor, False)
            while True:
                while True:
                    try:
                        chunk = os.read(descriptor, 8192)
                    except BlockingIOError:
                        break
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > 65536:
                        cleanup = _terminate_process_group(process)
                        return _ProcessResultV1(
                            True, process.returncode, False, cleanup, b""
                        )
                if process.poll() is not None:
                    try:
                        tail = os.read(descriptor, 8192)
                    except BlockingIOError:
                        tail = b""
                    if tail:
                        output.extend(tail)
                        if len(output) > 65536:
                            cleanup = _terminate_process_group(process)
                            return _ProcessResultV1(
                                True, process.returncode, False, cleanup, b""
                            )
                        continue
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    cleanup = _terminate_process_group(process)
                    return _ProcessResultV1(True, None, True, cleanup, b"")
                select.select((descriptor,), (), (), min(0.1, remaining))
        else:
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                cleanup = _terminate_process_group(process)
                return _ProcessResultV1(True, None, True, cleanup, b"")
    except BaseException:
        _terminate_process_group(process)
        raise
    if not _process_group_absent(process.pid):
        cleanup = _terminate_process_group(process)
        return _ProcessResultV1(True, process.returncode, False, cleanup, bytes(output))
    return _ProcessResultV1(True, process.returncode, False, True, bytes(output))


def _simple_process_status(result: _ProcessResultV1) -> StatusV1:
    if not result.launched:
        return "blocked"
    if result.timed_out or not result.cleanup_confirmed:
        return "failed"
    return "passed" if result.return_code == 0 else "failed"


def _run_ollama_dashboard_browser(
    revision: str,
) -> tuple[
    BoundaryCheckV1,
    BoundaryCheckV1,
    BoundaryCheckV1,
    BoundaryCheckV1,
    BoundaryCheckV1,
    dict[str, int | str],
]:
    empty_facts: dict[str, int | str] = {
        "confirmed_cloud_targets": 0,
        "current_lineage_targets": 0,
        "current_balance_lineage_sha256": _EMPTY_LINEAGE_SHA256,
        "history_lineage_targets": 0,
        "current_history_lineage_sha256": _EMPTY_LINEAGE_SHA256,
    }
    process_result = _run_direct_argv(
        _direct_command("installed_dashboard", revision),
        timeout_seconds=DIRECT_CHECK_TIMEOUT_SECONDS["account_admin_browser"],
        capture_output=True,
    )
    failed = (
        _boundary("failed"),
        _boundary("failed"),
        _boundary("failed"),
        _boundary("failed"),
        _boundary("failed"),
        empty_facts,
    )
    if not process_result.launched:
        return (
            _boundary("blocked"),
            _boundary("blocked"),
            _boundary("blocked"),
            _boundary("blocked"),
            _boundary("blocked"),
            empty_facts,
        )
    if process_result.timed_out or not process_result.cleanup_confirmed:
        return failed
    try:
        parsed = _load_json_bytes(process_result.output.strip())
    except M6ExitErrorV1:
        return failed
    if (
        not isinstance(parsed, dict)
        or set(parsed) != {"schema_version", "record_type", "results", "facts"}
        or parsed.get("schema_version") != "1.0.0"
        or parsed.get("record_type") != "agentmonitor.m6_ollama_dashboard_check.v1"
        or not isinstance(parsed.get("results"), dict)
        or set(parsed["results"])
        != {
            "account_admin",
            "cloud_capacity",
            "capacity_history",
            "process_visibility",
            "dashboard_continuity",
        }
        or not isinstance(parsed.get("facts"), dict)
        or set(parsed["facts"]) != set(empty_facts)
        or any(
            type(parsed["facts"][name]) is not int or parsed["facts"][name] < 0
            for name in (
                "confirmed_cloud_targets",
                "current_lineage_targets",
                "history_lineage_targets",
            )
        )
        or any(
            not isinstance(parsed["facts"][name], str)
            or len(parsed["facts"][name]) != 64
            or any(
                character not in "0123456789abcdef"
                for character in parsed["facts"][name]
            )
            for name in (
                "current_balance_lineage_sha256",
                "current_history_lineage_sha256",
            )
        )
        or parsed["facts"]["current_lineage_targets"]
        > parsed["facts"]["confirmed_cloud_targets"]
        or parsed["facts"]["history_lineage_targets"]
        > parsed["facts"]["current_lineage_targets"]
    ):
        return failed
    boundaries: list[BoundaryCheckV1] = []
    for name in (
        "account_admin",
        "cloud_capacity",
        "capacity_history",
        "process_visibility",
        "dashboard_continuity",
    ):
        outcome = parsed["results"].get(name)
        if not isinstance(outcome, dict) or set(outcome) != {"status", "reason_code"}:
            return failed
        result_status = outcome.get("status")
        reason = outcome.get("reason_code")
        if (
            result_status not in {"passed", "failed", "blocked", "not_run"}
            or (result_status == "passed" and reason is not None)
            or (
                result_status != "passed"
                and (
                    not isinstance(reason, str) or not reason.replace("_", "").isalnum()
                )
            )
        ):
            return failed
        boundaries.append(_boundary(result_status, reason))
    statuses = [item.status for item in boundaries]
    expected_return_code = (
        1
        if "failed" in statuses
        else 0
        if statuses == ["passed", "passed", "passed", "passed", "passed"]
        else 3
    )
    if process_result.return_code != expected_return_code:
        return failed
    return (
        boundaries[0],
        boundaries[1],
        boundaries[2],
        boundaries[3],
        boundaries[4],
        dict(parsed["facts"]),
    )


def _run_local_inventory() -> tuple[
    BoundaryCheckV1, tuple[LocalModelHostEvidenceV1, ...]
]:
    result = _run_direct_argv(
        _direct_command("local_inventory", "0" * 40),
        timeout_seconds=DIRECT_CHECK_TIMEOUT_SECONDS["local_inventory"],
        capture_output=True,
    )
    if not result.launched:
        return _boundary("blocked", "local_inventory_unavailable"), ()
    if result.timed_out or not result.cleanup_confirmed:
        return _boundary("failed", "local_inventory_execution_failed"), ()
    if result.return_code == 0:
        candidates = [
            line
            for line in result.output.splitlines()
            if line.startswith(b"{") and line.endswith(b"}")
        ]
        if len(candidates) != 1:
            return _boundary("failed", "local_inventory_output_invalid"), ()
        try:
            parsed = _load_json_bytes(candidates[0])
            if (
                not isinstance(parsed, dict)
                or set(parsed)
                != {
                    "schema_version",
                    "record_type",
                    "status",
                    "host_id",
                    "source_id",
                    "version",
                    "installed_model_count",
                    "loaded_model_count",
                    "observed_at",
                }
                or parsed.get("schema_version") != "1.0.0"
                or parsed.get("record_type") != "agentmonitor.m6_local_inventory.v1"
                or parsed.get("status") != "passed"
            ):
                raise ValueError("local_inventory_output_invalid")
            host = LocalModelHostEvidenceV1(
                host_id=parsed["host_id"],
                source_id=parsed["source_id"],
                version=parsed["version"],
                installed_model_count=parsed["installed_model_count"],
                loaded_model_count=parsed["loaded_model_count"],
                observed_at=parsed["observed_at"],
            )
            observed = datetime.fromisoformat(host.observed_at)
            now = datetime.now(UTC)
            if observed > now or now - observed > timedelta(minutes=2):
                raise ValueError("local_inventory_output_stale")
        except (KeyError, TypeError, ValueError):
            return _boundary("failed", "local_inventory_output_invalid"), ()
        return _boundary("passed"), (host,)
    if result.return_code == 3 and b"M6 LOCAL INVENTORY: BLOCKED " in result.output:
        return _boundary("blocked", "local_inventory_source_unavailable"), ()
    return _boundary("failed", "local_inventory_execution_failed"), ()


def _run_real_snapshot() -> tuple[BoundaryCheckV1, dict[str, int], dict[str, str]]:
    empty = {key: 0 for key in DIRECT_SNAPSHOT_KEYS}
    empty_digests = {key: _EMPTY_LINEAGE_SHA256 for key in DIRECT_SNAPSHOT_DIGEST_KEYS}
    result = _run_direct_argv(
        _direct_command("database_snapshot", "0" * 40),
        timeout_seconds=DIRECT_CHECK_TIMEOUT_SECONDS["database_snapshot"],
        capture_output=True,
    )
    if not result.launched:
        return _boundary("blocked"), empty, empty_digests
    if result.timed_out or not result.cleanup_confirmed:
        return _boundary("failed"), empty, empty_digests
    try:
        parsed = _load_json_bytes(result.output.strip())
    except M6ExitErrorV1:
        return _boundary("failed"), empty, empty_digests
    if (
        not isinstance(parsed, dict)
        or set(parsed)
        != {
            "schema_version",
            "record_type",
            "status",
            "reason_code",
            "schema_state",
            "counts",
            "digests",
        }
        or parsed.get("schema_version") != "1.0.0"
        or parsed.get("record_type") != "agentmonitor.m6_real_snapshot.v1"
        or parsed.get("status") not in {"passed", "blocked", "not_run"}
        or parsed.get("schema_state") not in DIRECT_SNAPSHOT_SCHEMA_STATES
        or not isinstance(parsed.get("reason_code"), str)
        or not parsed["reason_code"].startswith("m6_snapshot_")
        or not parsed["reason_code"].replace("_", "").isalnum()
        or not isinstance(parsed.get("counts"), dict)
        or set(parsed["counts"]) != set(DIRECT_SNAPSHOT_KEYS)
        or any(
            type(value) is not int or value < 0 for value in parsed["counts"].values()
        )
        or not isinstance(parsed.get("digests"), dict)
        or set(parsed["digests"]) != set(DIRECT_SNAPSHOT_DIGEST_KEYS)
        or any(
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in parsed["digests"].values()
        )
    ):
        return _boundary("failed"), empty, empty_digests
    parsed_status = parsed["status"]
    expected_return_code = 0 if parsed_status == "passed" else 3
    if result.return_code != expected_return_code:
        return _boundary("failed"), empty, empty_digests
    return (
        _boundary(parsed_status),
        dict(parsed["counts"]),
        dict(parsed["digests"]),
    )


def _run_authoritative_comparison(
    revision: str,
) -> tuple[BoundaryCheckV1, AuthoritativeComparisonV1 | None]:
    policy = _run_direct_argv(
        _direct_command("authoritative_policy", revision),
        timeout_seconds=DIRECT_CHECK_TIMEOUT_SECONDS["authoritative_policy"],
    )
    if _simple_process_status(policy) != "passed":
        return _boundary(
            _simple_process_status(policy), "official_usage_policy_unavailable"
        ), None
    result = _run_direct_argv(
        _direct_command("authoritative_comparison", revision),
        timeout_seconds=DIRECT_CHECK_TIMEOUT_SECONDS["authoritative_comparison"],
        capture_output=True,
    )
    if not result.launched:
        return _boundary("blocked", "official_usage_producer_unavailable"), None
    if result.timed_out or not result.cleanup_confirmed:
        return _boundary("failed", "official_usage_producer_timeout"), None
    try:
        evidence = parse_authoritative_comparison_v1(
            _load_json_bytes(result.output.strip()),
            revision=revision,
            return_code=result.return_code,
            now=datetime.now(UTC),
        )
        return _boundary(
            evidence.status,
            None if evidence.status == "passed" else evidence.reason_code,
        ), evidence
    except (M6ExitErrorV1, ValueError):
        return _boundary("failed", "official_usage_producer_invalid"), None


def _run_recovery_interval(
    revision: str,
) -> tuple[BoundaryCheckV1, RecoveryIntervalEvidenceV1 | None]:
    result = _run_direct_argv(
        _direct_command("recovery_interval", revision),
        timeout_seconds=DIRECT_CHECK_TIMEOUT_SECONDS["recovery_interval"],
        capture_output=True,
    )
    if not result.launched:
        return _boundary("blocked", "m6_recovery_producer_unavailable"), None
    if result.timed_out or not result.cleanup_confirmed:
        return _boundary("failed", "m6_recovery_producer_timeout"), None
    try:
        evidence = parse_recovery_interval_v1(
            _load_json_bytes(result.output.strip()),
            revision=revision,
            return_code=result.return_code,
            now=datetime.now(UTC),
        )
        return _boundary(
            evidence.status,
            None if evidence.status == "passed" else evidence.reason_code,
        ), evidence
    except (M6ExitErrorV1, ValueError):
        return _boundary("failed", "m6_recovery_producer_invalid"), None


def _run_direct_checks(checks: dict[str, StatusV1], revision: str) -> DirectM6FactsV1:
    """Run every available real check once, independent of sibling outcomes."""

    recovery_observation, recovery_interval = _run_recovery_interval(revision)
    local_inventory, model_hosts = _run_local_inventory()
    source_security = _run_direct_argv(
        _direct_command("source_security", revision),
        timeout_seconds=DIRECT_CHECK_TIMEOUT_SECONDS["source_security"],
    )
    (
        account_admin,
        cloud_capacity,
        capacity_history,
        process_browser,
        dashboard_continuity,
        browser_facts,
    ) = _run_ollama_dashboard_browser(revision)
    authoritative_comparison, authoritative_observation = _run_authoritative_comparison(
        revision
    )
    database_snapshot, counts, snapshot_digests = _run_real_snapshot()
    # Historical rows alone cannot attest HTTP continuity. Only this invocation's
    # bounded, revision-bound interval producer supplies recovery counts.
    counts["natural_recovery_targets"] = (
        0 if recovery_interval is None else recovery_interval.natural_recovery_targets
    )
    counts["cross_provider_continuity_targets"] = (
        0
        if recovery_interval is None
        else recovery_interval.cross_provider_continuity_targets
    )
    # A provider DOM comparison is accepted only for the exact current API/DOM/DB
    # observation set. The DB query owns current credential-binding/source proof;
    # no key or invented provider identity is exposed to the browser producer.
    authoritative_balance_reconciled_targets = 0
    if (
        authoritative_comparison.status == "passed"
        and authoritative_observation is not None
    ):
        if (
            authoritative_observation.compared_targets
            == counts["current_balance_targets"]
            == browser_facts["current_lineage_targets"]
            and authoritative_observation.current_balance_lineage_sha256
            == snapshot_digests["current_balance_lineage_sha256"]
            == browser_facts["current_balance_lineage_sha256"]
        ):
            authoritative_balance_reconciled_targets = (
                authoritative_observation.compared_targets
            )
        else:
            authoritative_comparison = _boundary(
                "not_run", "official_usage_current_lineage_not_reconciled"
            )
    history_lineage_reconciled_targets = 0
    if (
        browser_facts["history_lineage_targets"] == counts["history_targets"]
        and browser_facts["current_history_lineage_sha256"]
        == snapshot_digests["current_history_lineage_sha256"]
    ):
        history_lineage_reconciled_targets = counts["history_targets"]
    return DirectM6FactsV1(
        local_admission=_boundary(checks["AUTO-M6-LOCAL-ADMIT"]),
        local_inventory=local_inventory,
        account_admin_browser=account_admin,
        cloud_capacity_browser=cloud_capacity,
        capacity_history_browser=capacity_history,
        process_browser=process_browser,
        dashboard_continuity_browser=dashboard_continuity,
        source_security=_boundary(_simple_process_status(source_security)),
        database_snapshot=database_snapshot,
        authoritative_comparison=authoritative_comparison,
        authoritative_observation=authoritative_observation,
        recovery_interval=recovery_interval,
        recovery_observation=recovery_observation,
        observed_model_hosts=len(model_hosts),
        model_host_evidence=model_hosts,
        authoritative_balance_reconciled_targets=(
            authoritative_balance_reconciled_targets
        ),
        history_lineage_reconciled_targets=history_lineage_reconciled_targets,
        **counts,
    )


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
            # Creating the child legitimately changes the parent's link count.
            # Reopen the complete chain and compare the stable parent identity.
            parent_identity = local.entries[0][2]
        with _open_directory_chain(
            (".agentmonitor-local", "m6-exit-receipts"), private=True
        ) as receipts:
            reopened = receipts.entries[0][2]
            if reopened[:3] != parent_identity[:3] or reopened[4] != parent_identity[4]:
                raise M6ExitBlockedV1("m6_receipt_root_changed")
            yield receipts
    except FileNotFoundError:
        raise M6ExitBlockedV1("m6_receipt_root_unavailable") from None
    except M6ExitErrorV1:
        raise
    except OSError:
        raise M6ExitBlockedV1("m6_receipt_root_unavailable") from None


def _ensure_private_directory(parent_fd: int, name: str) -> None:
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except FileExistsError:
        pass
    except OSError:
        raise M6ExitBlockedV1("m6_evidence_root_unavailable") from None
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        raise M6ExitBlockedV1("m6_evidence_root_unavailable") from None
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise M6ExitErrorV1("m6_private_evidence_root_invalid")


@contextmanager
def _open_direct_evidence_directory() -> Iterator[_DirectoryChainV1]:
    root_fd = -1
    try:
        root_fd = os.open(
            ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        _ensure_private_directory(root_fd, ".agentmonitor-local")
    finally:
        if root_fd >= 0:
            os.close(root_fd)
    with _open_directory_chain((".agentmonitor-local",), private=True) as local:
        _ensure_private_directory(local.leaf_fd, "m6-evidence")
    with _open_directory_chain(
        (".agentmonitor-local", "m6-evidence"), private=True
    ) as evidence:
        yield evidence


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


def _retain_bounded_direct_evidence(
    directory: _DirectoryChainV1, *, keep_name: str
) -> None:
    """Keep bounded unreceipted artifacts and every receipt-bound artifact."""

    pattern = re.compile(r"direct-[0-9a-f]{40}-[0-9a-f]{16}\.json")
    protected = _receipt_bound_evidence_names()
    protected.add(keep_name)
    owned: list[tuple[int, str, tuple[int, int]]] = []
    try:
        for name in os.listdir(directory.leaf_fd):
            if pattern.fullmatch(name) is None or name in protected:
                continue
            metadata = os.stat(name, dir_fd=directory.leaf_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_nlink != 1
            ):
                raise M6ExitErrorV1("m6_evidence_retention_entry_invalid")
            owned.append(
                (
                    metadata.st_mtime_ns,
                    name,
                    (metadata.st_dev, metadata.st_ino),
                )
            )
        owned.sort()
        for _, name, identity in owned[: max(0, len(owned) - 30)]:
            current = os.stat(name, dir_fd=directory.leaf_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != identity:
                raise M6ExitBlockedV1("m6_evidence_retention_changed")
            os.unlink(name, dir_fd=directory.leaf_fd)
        if len(owned) > 30:
            os.fsync(directory.leaf_fd)
        directory.revalidate()
    except M6ExitErrorV1:
        raise
    except OSError:
        raise M6ExitBlockedV1("m6_evidence_retention_unavailable") from None


def _receipt_bound_evidence_names() -> set[str]:
    """Return exact artifact names retained by immutable revision receipts."""

    protected: set[str] = set()
    with _open_receipt_directory() as directory:
        try:
            names = sorted(os.listdir(directory.leaf_fd))
        except OSError:
            raise M6ExitBlockedV1("m6_receipt_unavailable") from None
        if len(names) > 128:
            raise M6ExitErrorV1("m6_receipt_count_invalid")
        for name in names:
            match = re.fullmatch(r"([0-9a-f]{40})\.json", name)
            if match is None:
                raise M6ExitErrorV1("m6_receipt_name_invalid")
            payload = _read_regular_at(
                directory,
                name,
                private=True,
                limit=MAX_JSON_BYTES,
                missing_reason="m6_receipt_changed",
            )
            parsed = _load_json_bytes(payload)
            if (
                not isinstance(parsed, dict)
                or parsed.get("record_type")
                != "agentmonitor.m6_technical_exit_receipt.v1"
                or parsed.get("implementation_revision") != match.group(1)
                or not isinstance(parsed.get("direct_evidence_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", parsed["direct_evidence_sha256"])
                is None
            ):
                raise M6ExitErrorV1("m6_receipt_shape_invalid")
            protected.add(
                f"direct-{match.group(1)}-{parsed['direct_evidence_sha256'][:16]}.json"
            )
        directory.revalidate()
    return protected


def _write_direct_evidence_artifact(
    *,
    revision: str,
    catalog_digest: str,
    recorded_at: datetime,
    checks: dict[str, StatusV1],
    facts: DirectM6FactsV1,
    outcomes: dict[str, DirectM6OutcomeV1],
) -> tuple[str, str]:
    """Create one private sanitized artifact for all direct M6 outcomes."""

    document = {
        "schema_version": "1.0.0",
        "record_type": "agentmonitor.m6_direct_evidence.v1",
        "command_id": "AUTO-M6-EXIT",
        "implementation_revision": revision,
        "catalog_sha256": catalog_digest,
        "observed_at": recorded_at.astimezone(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "required_checks": dict(sorted(checks.items())),
        "direct_facts": asdict(facts),
        "outcomes": {key: asdict(value) for key, value in sorted(outcomes.items())},
    }
    payload = (
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")
    if len(payload) > MAX_JSON_BYTES:
        raise M6ExitErrorV1("m6_direct_evidence_size_invalid")
    payload_digest = _sha256(payload)
    name = f"direct-{revision}-{payload_digest[:16]}.json"
    descriptor = -1
    created = False
    with _open_direct_evidence_directory() as directory:
        _retain_bounded_direct_evidence(directory, keep_name=name)
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=directory.leaf_fd,
            )
            created = True
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_uid != os.getuid()
                or stat.S_IMODE(opened.st_mode) != 0o600
                or opened.st_nlink != 1
            ):
                raise M6ExitErrorV1("m6_evidence_file_invalid")
            _write_all(descriptor, payload)
            os.fsync(descriptor)
            os.fsync(directory.leaf_fd)
            current = _read_regular_at(
                directory,
                name,
                private=True,
                limit=MAX_JSON_BYTES,
                missing_reason="m6_evidence_artifact_missing",
            )
            if current != payload:
                raise M6ExitBlockedV1("m6_evidence_changed")
            directory.revalidate()
            os.close(descriptor)
            descriptor = -1
        except FileExistsError:
            current = _read_regular_at(
                directory,
                name,
                private=True,
                limit=MAX_JSON_BYTES,
                missing_reason="m6_evidence_artifact_missing",
            )
            if current != payload:
                raise M6ExitErrorV1("m6_evidence_artifact_conflict") from None
            directory.revalidate()
        except BaseException:
            cleanup_ok = True
            if created and descriptor >= 0:
                cleanup_ok = _unlink_created_receipt(
                    directory.leaf_fd, name, created_fd=descriptor
                )
            if descriptor >= 0:
                os.close(descriptor)
            if not cleanup_ok:
                raise M6ExitBlockedV1("m6_evidence_cleanup_identity_changed") from None
            raise
    return str(Path(".agentmonitor-local/m6-evidence") / name), payload_digest


def _validate_direct_evidence_artifact(revision: str, digest: str) -> None:
    """Revalidate the immutable direct artifact named by a prior receipt."""

    if (
        re.fullmatch(r"[0-9a-f]{40}", revision) is None
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
    ):
        raise M6ExitErrorV1("m6_receipt_evidence_digest_invalid")
    name = f"direct-{revision}-{digest[:16]}.json"
    with _open_direct_evidence_directory() as directory:
        payload = _read_regular_at(
            directory,
            name,
            private=True,
            limit=MAX_JSON_BYTES,
            missing_reason="m6_evidence_artifact_missing",
        )
        if _sha256(payload) != digest:
            raise M6ExitErrorV1("m6_evidence_digest_mismatch")


def _write_or_validate_receipt(
    revision: str,
    receipt: dict[str, object],
    *,
    revalidate_snapshot: Callable[[], None],
) -> str:
    evidence_digest = receipt.get("direct_evidence_sha256")
    if (
        not isinstance(evidence_digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", evidence_digest) is None
    ):
        raise M6ExitErrorV1("m6_receipt_evidence_digest_invalid")
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
                raise M6ExitErrorV1(errors[0]) from None
            if not isinstance(parsed, dict):
                raise M6ExitErrorV1("m6_receipt_evidence_digest_invalid") from None
            prior_evidence_digest = parsed.get("direct_evidence_sha256")
            if not isinstance(prior_evidence_digest, str):
                raise M6ExitErrorV1("m6_receipt_evidence_digest_invalid") from None
            _validate_direct_evidence_artifact(revision, prior_evidence_digest)
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
                raise M6ExitErrorV1("m6_receipt_changed") from None
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
    bundle: dict[str, object],
) -> None:
    if _git_revision() != revision:
        raise M6ExitBlockedV1("m6_checkout_changed")
    _, _, current_catalog_digest = _read_catalog()
    if current_catalog_digest != catalog_digest:
        raise M6ExitBlockedV1("m6_catalog_changed")
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
    artifact_path: str | None = None
    scope_reason_codes: dict[str, str] = {}
    try:
        catalog, _, catalog_digest = _read_catalog()
        revision = _git_revision()
        with _temporary_tool_environment():
            checks = _run_checks()
            facts = _run_direct_checks(checks, revision)
        if _git_revision() != revision:
            raise M6ExitBlockedV1("m6_checkout_changed")
        outcomes = classify_direct_m6_evidence_v1(facts)
        scope_reason_codes = {
            key: outcome.reason_code
            for key, outcome in outcomes.items()
            if outcome.reason_code is not None
        }
        recorded_at = datetime.now(UTC)
        artifact_path, evidence_digest = _write_direct_evidence_artifact(
            revision=revision,
            catalog_digest=catalog_digest,
            recorded_at=recorded_at,
            checks=checks,
            facts=facts,
            outcomes=outcomes,
        )
        bundle = direct_bundle_v1(
            outcomes,
            catalog=catalog,
            artifact_path=artifact_path,
            artifact_sha256=evidence_digest,
            implementation_revision=revision,
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
                artifact_path=artifact_path,
                scope_reason_codes=scope_reason_codes,
            )
        _revalidate_completion_snapshot(
            revision=revision,
            catalog=catalog,
            catalog_digest=catalog_digest,
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
            direct_evidence_sha256=evidence_digest,
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
            artifact_path=artifact_path,
            scope_reason_codes=scope_reason_codes,
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
            artifact_path=artifact_path,
            scope_reason_codes=scope_reason_codes,
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
        artifact_path=artifact_path,
        scope_reason_codes=scope_reason_codes,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
