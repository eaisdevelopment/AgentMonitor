"""Preserve a stale M5 prerequisite set before a new create-once run.

The command never edits or deletes prerequisite evidence.  It validates the
fixed private files, then renames the complete existing set into a private,
revision-and-digest-addressed directory on the same filesystem.  A current
usable set and a completed M5 receipt are both fail-closed conditions.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tools.automation.implementations.auto_m3_current_exit import (
    M3CurrentExitErrorV1,
    ServiceLaunchV1,
    _clean_revision,
)
from tools.automation.implementations.auto_m5_current_exit import (
    ALERT_WITNESS_BASENAME,
    RECEIPT_PATH,
    SelectedServiceV1,
    read_alert_witness_v1,
)
from tools.automation.implementations.m5_codex_quota_witness import (
    QUOTA_WITNESS_BASENAME,
    M5CodexQuotaWitnessErrorV1,
    parse_quota_witness_document_v1,
)
from tools.automation.implementations.m5_completion_lock import (
    M5CompletionLockErrorV1,
    M5CompletionLockV1,
    acquire_m5_completion_lock_v1,
    release_m5_completion_lock_v1,
    validate_m5_completion_lock_v1,
)
from tools.automation.implementations.m5_owner_outcomes import (
    MAX_CLOCK_SKEW,
    MAX_OWNER_OUTCOME_AGE,
    OWNER_OUTCOMES_BASENAME,
    M5OwnerOutcomesErrorV1,
    ParsedOwnerOutcomesV2,
    _selected_service,
    parse_owner_outcomes_document_v2,
)

CANONICAL_COMMAND = "python3 tools/automation/run.py AUTO-M5-ARCHIVE-PREREQUISITES"
ARCHIVE_ROOT_BASENAME = ".m5-prerequisite-archive"
ARCHIVE_MANIFEST_BASENAME = "archive-manifest.json"
ARCHIVE_MANIFEST_SCHEMA = "agentmonitor.m5-prerequisite-archive.v1"
PREREQUISITE_BASENAMES = (
    OWNER_OUTCOMES_BASENAME,
    QUOTA_WITNESS_BASENAME,
    ALERT_WITNESS_BASENAME,
)
MAX_ARTIFACT_BYTES = 16_384
MAX_MANIFEST_BYTES = 16_384

_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")
_RENAME_NOREPLACE = 1
try:
    _LIBC = ctypes.CDLL(None, use_errno=True)
    _RENAMEAT2 = getattr(_LIBC, "renameat2", None)
except OSError:
    _RENAMEAT2 = None
if _RENAMEAT2 is not None:
    _RENAMEAT2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    _RENAMEAT2.restype = ctypes.c_int


class M5PrerequisiteArchiveErrorV1(ValueError):
    """One sanitized archive refusal or filesystem failure."""


def _rename_noreplace_v1(
    source_name: str,
    target_name: str,
    *,
    source_directory_descriptor: int,
    target_directory_descriptor: int,
) -> None:
    """Move one entry with Linux's atomic no-replace guarantee."""

    if (
        _RENAMEAT2 is None
        or not source_name
        or Path(source_name).name != source_name
        or not target_name
        or Path(target_name).name != target_name
    ):
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_atomic_noreplace_unavailable"
        )
    ctypes.set_errno(0)
    result = _RENAMEAT2(
        source_directory_descriptor,
        os.fsencode(source_name),
        target_directory_descriptor,
        os.fsencode(target_name),
        _RENAME_NOREPLACE,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise FileExistsError(error_number, os.strerror(error_number), target_name)
    if error_number in {
        errno.EINVAL,
        errno.ENOSYS,
        errno.ENOTSUP,
        errno.EOPNOTSUPP,
    }:
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_atomic_noreplace_unavailable"
        )
    raise OSError(error_number, os.strerror(error_number), source_name)


@dataclass(frozen=True, slots=True)
class M5PrerequisiteArchiveResultV1:
    """Sanitized result; paths and private prerequisite values stay local."""

    archive_id: str
    implementation_revision: str
    bundle_digest: str
    artifact_count: int
    artifact_digests: tuple[tuple[str, str], ...]


@dataclass(slots=True)
class _OpenedArtifactV1:
    """One held private inode used across validation and rename."""

    basename: str
    descriptor: int
    device: int
    inode: int
    size: int
    digest: str
    document: object = field(repr=False)


def _utc_value(value: object) -> datetime:
    if type(value) is not str or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise M5PrerequisiteArchiveErrorV1("m5_prerequisite_archive_artifact_invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_artifact_invalid"
        ) from None
    if parsed.utcoffset() != timedelta(0):
        raise M5PrerequisiteArchiveErrorV1("m5_prerequisite_archive_artifact_invalid")
    return parsed.astimezone(UTC)


def _validate_root(path: Path, descriptor: int) -> tuple[int, int]:
    try:
        metadata = os.fstat(descriptor)
        path_metadata = path.lstat()
        if (
            not path.is_absolute()
            or path.resolve(strict=True) != path
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
        ):
            raise OSError
        return metadata.st_dev, metadata.st_ino
    except OSError:
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_root_invalid"
        ) from None


def _read_exact(descriptor: int, size: int) -> bytes:
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        remaining = size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                raise OSError
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) != size:
            raise OSError
        return payload
    except OSError:
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_artifact_invalid"
        ) from None


def _validate_artifact_metadata(
    metadata: os.stat_result,
    path_metadata: os.stat_result,
    *,
    root_device: int,
) -> None:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or not 2 <= metadata.st_size <= MAX_ARTIFACT_BYTES
        or metadata.st_dev != root_device
        or (metadata.st_dev, metadata.st_ino)
        != (path_metadata.st_dev, path_metadata.st_ino)
    ):
        raise M5PrerequisiteArchiveErrorV1("m5_prerequisite_archive_artifact_invalid")


def _open_artifact(
    root_descriptor: int, basename: str, *, root_device: int
) -> _OpenedArtifactV1 | None:
    descriptor = -1
    try:
        try:
            os.stat(basename, dir_fd=root_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return None
        descriptor = os.open(
            basename,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=root_descriptor,
        )
        metadata = os.fstat(descriptor)
        path_metadata = os.stat(basename, dir_fd=root_descriptor, follow_symlinks=False)
        _validate_artifact_metadata(metadata, path_metadata, root_device=root_device)
        payload = _read_exact(descriptor, metadata.st_size)
        final_metadata = os.fstat(descriptor)
        final_path_metadata = os.stat(
            basename, dir_fd=root_descriptor, follow_symlinks=False
        )
        _validate_artifact_metadata(
            final_metadata, final_path_metadata, root_device=root_device
        )
        if (final_metadata.st_dev, final_metadata.st_ino, final_metadata.st_size) != (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
        ):
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_artifact_invalid"
            )
        try:
            document = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_artifact_invalid"
            ) from None
        result = _OpenedArtifactV1(
            basename,
            descriptor,
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            hashlib.sha256(payload).hexdigest(),
            document,
        )
        descriptor = -1
        return result
    except M5PrerequisiteArchiveErrorV1:
        raise
    except (OSError, RuntimeError, TypeError, ValueError):
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_artifact_invalid"
        ) from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _owner_context(
    artifact: _OpenedArtifactV1,
) -> tuple[ParsedOwnerOutcomesV2, datetime]:
    try:
        if type(artifact.document) is not dict:
            raise ValueError
        confirmed_at = _utc_value(artifact.document.get("owner_confirmed_at"))
        parsed = parse_owner_outcomes_document_v2(artifact.document, now=confirmed_at)
        return parsed, confirmed_at
    except (M5OwnerOutcomesErrorV1, TypeError, ValueError):
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_artifact_invalid"
        ) from None


def _quota_recorded_at(
    artifact: _OpenedArtifactV1,
    *,
    owner: ParsedOwnerOutcomesV2,
    owner_digest: str,
) -> datetime:
    try:
        if type(artifact.document) is not dict:
            raise ValueError
        recorded_at = _utc_value(artifact.document.get("recorded_at"))
        parse_quota_witness_document_v1(
            artifact.document,
            expected_revision=owner.implementation_revision,
            service_pid=owner.service_pid,
            service_start_time_ticks=owner.service_start_time_ticks,
            owner_outcomes_digest=owner_digest,
            verified_account_count=len(owner.verified_account_ids),
            now=recorded_at,
        )
        return recorded_at
    except (M5CodexQuotaWitnessErrorV1, TypeError, ValueError):
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_artifact_invalid"
        ) from None


def _alert_recorded_at(
    root: Path,
    artifact: _OpenedArtifactV1,
    *,
    owner: ParsedOwnerOutcomesV2,
) -> datetime:
    try:
        if type(artifact.document) is not dict:
            raise ValueError
        recorded_at = _utc_value(artifact.document.get("recorded_at"))
        selected = SelectedServiceV1(
            owner.service_pid,
            owner.service_start_time_ticks,
            ServiceLaunchV1((), root / "service.env", root, "127.0.0.1", 1),
        )
        read_alert_witness_v1(
            root / ALERT_WITNESS_BASENAME,
            expected_revision=owner.implementation_revision,
            selected_service=selected,
            verified_account_ids=owner.verified_account_ids,
            now=recorded_at,
        )
        return recorded_at
    except (TypeError, ValueError):
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_artifact_invalid"
        ) from None


def _bundle_digest(artifacts: tuple[_OpenedArtifactV1, ...]) -> str:
    material = [[item.basename, item.digest] for item in artifacts]
    return hashlib.sha256(
        json.dumps(material, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def _is_fresh(
    value: datetime, *, now: datetime, maximum_age: timedelta, future: timedelta
) -> bool:
    return value <= now + future and now - value <= maximum_age


def _require_stale_set(
    artifacts: tuple[_OpenedArtifactV1, ...],
    *,
    owner: ParsedOwnerOutcomesV2,
    owner_confirmed_at: datetime,
    quota_recorded_at: datetime | None,
    alert_recorded_at: datetime | None,
    current_revision: str,
    current_service_pid: int,
    current_service_start_time_ticks: int,
    now: datetime,
) -> None:
    context_current = (
        owner.implementation_revision == current_revision
        and owner.service_pid == current_service_pid
        and owner.service_start_time_ticks == current_service_start_time_ticks
    )
    owner_current = _is_fresh(
        owner_confirmed_at,
        now=now,
        maximum_age=MAX_OWNER_OUTCOME_AGE,
        future=MAX_CLOCK_SKEW,
    )
    quota_current = quota_recorded_at is None or _is_fresh(
        quota_recorded_at,
        now=now,
        maximum_age=timedelta(minutes=15),
        future=timedelta(minutes=1),
    )
    alert_current = alert_recorded_at is None or _is_fresh(
        alert_recorded_at,
        now=now,
        maximum_age=timedelta(days=8),
        future=timedelta(minutes=5),
    )
    if context_current and owner_current and quota_current and alert_current:
        raise M5PrerequisiteArchiveErrorV1("m5_prerequisite_archive_current_valid")
    if not artifacts:
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_owner_outcomes_required"
        )


def _open_or_create_private_directory(
    *,
    parent_descriptor: int,
    name: str,
    parent_device: int,
    create: bool,
) -> tuple[int, bool]:
    created = False
    descriptor = -1
    try:
        if create:
            try:
                os.mkdir(name, 0o700, dir_fd=parent_descriptor)
                created = True
            except FileExistsError:
                pass
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
        metadata = os.fstat(descriptor)
        path_metadata = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_dev != parent_device
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
        ):
            raise OSError
        return descriptor, created
    except OSError:
        if descriptor >= 0:
            os.close(descriptor)
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_target_invalid"
        ) from None


def _validate_held_artifact_at(
    artifact: _OpenedArtifactV1,
    *,
    directory_descriptor: int,
) -> None:
    try:
        path_metadata = os.stat(
            artifact.basename,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        metadata = os.fstat(artifact.descriptor)
        _validate_artifact_metadata(
            metadata, path_metadata, root_device=artifact.device
        )
        if (
            metadata.st_ino != artifact.inode
            or metadata.st_size != artifact.size
            or hashlib.sha256(
                _read_exact(artifact.descriptor, artifact.size)
            ).hexdigest()
            != artifact.digest
        ):
            raise OSError
    except (OSError, M5PrerequisiteArchiveErrorV1):
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_artifact_changed"
        ) from None


def _write_manifest(
    archive_descriptor: int,
    *,
    revision: str,
    bundle_digest: str,
    artifacts: tuple[_OpenedArtifactV1, ...],
    archived_at: datetime,
) -> tuple[int, int]:
    document = {
        "schema": ARCHIVE_MANIFEST_SCHEMA,
        "implementation_revision": revision,
        "archived_at": archived_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "artifact_count": len(artifacts),
        "bundle_digest": bundle_digest,
        "artifacts": [
            {"basename": item.basename, "sha256": item.digest} for item in artifacts
        ],
    }
    payload = (json.dumps(document, ensure_ascii=True, indent=2) + "\n").encode("ascii")
    if not 2 <= len(payload) <= MAX_MANIFEST_BYTES:
        raise M5PrerequisiteArchiveErrorV1("m5_prerequisite_archive_manifest_invalid")
    descriptor = -1
    try:
        descriptor = os.open(
            ARCHIVE_MANIFEST_BASENAME,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=archive_descriptor,
        )
        position = 0
        while position < len(payload):
            written = os.write(descriptor, payload[position:])
            if written < 1:
                raise OSError
            position += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        path_metadata = os.stat(
            ARCHIVE_MANIFEST_BASENAME,
            dir_fd=archive_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or metadata.st_size != len(payload)
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
        ):
            raise OSError
        return metadata.st_dev, metadata.st_ino
    except (FileExistsError, OSError):
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_manifest_invalid"
        ) from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _rollback(
    *,
    root_descriptor: int,
    archive_descriptor: int,
    artifacts: tuple[_OpenedArtifactV1, ...],
    moved: list[_OpenedArtifactV1],
    manifest_identity: tuple[int, int] | None,
) -> bool:
    ok = True
    if manifest_identity is not None:
        try:
            metadata = os.stat(
                ARCHIVE_MANIFEST_BASENAME,
                dir_fd=archive_descriptor,
                follow_symlinks=False,
            )
            if (metadata.st_dev, metadata.st_ino) == manifest_identity:
                os.unlink(ARCHIVE_MANIFEST_BASENAME, dir_fd=archive_descriptor)
            else:
                ok = False
        except FileNotFoundError:
            pass
        except OSError:
            ok = False
    for artifact in reversed(moved):
        try:
            archived = os.stat(
                artifact.basename,
                dir_fd=archive_descriptor,
                follow_symlinks=False,
            )
            if (archived.st_dev, archived.st_ino) != (
                artifact.device,
                artifact.inode,
            ):
                ok = False
                continue
            _rename_noreplace_v1(
                artifact.basename,
                artifact.basename,
                source_directory_descriptor=archive_descriptor,
                target_directory_descriptor=root_descriptor,
            )
        except (FileExistsError, M5PrerequisiteArchiveErrorV1, OSError):
            ok = False
    try:
        os.fsync(root_descriptor)
        os.fsync(archive_descriptor)
    except OSError:
        ok = False
    for artifact in artifacts:
        try:
            _validate_held_artifact_at(artifact, directory_descriptor=root_descriptor)
        except M5PrerequisiteArchiveErrorV1:
            ok = False
    return ok


def _archive_artifacts(
    root: Path,
    root_descriptor: int,
    root_device: int,
    artifacts: tuple[_OpenedArtifactV1, ...],
    *,
    revision: str,
    bundle_digest: str,
    archived_at: datetime,
) -> str:
    archive_parent_descriptor = -1
    archive_descriptor = -1
    archive_parent_created = False
    archive_created = False
    moved: list[_OpenedArtifactV1] = []
    manifest_identity: tuple[int, int] | None = None
    archive_id = f"{revision}-{bundle_digest}"
    try:
        archive_parent_descriptor, archive_parent_created = (
            _open_or_create_private_directory(
                parent_descriptor=root_descriptor,
                name=ARCHIVE_ROOT_BASENAME,
                parent_device=root_device,
                create=True,
            )
        )
        try:
            os.mkdir(archive_id, 0o700, dir_fd=archive_parent_descriptor)
            archive_created = True
        except FileExistsError:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_target_exists"
            ) from None
        archive_descriptor, _created = _open_or_create_private_directory(
            parent_descriptor=archive_parent_descriptor,
            name=archive_id,
            parent_device=root_device,
            create=False,
        )
        for artifact in artifacts:
            _validate_held_artifact_at(artifact, directory_descriptor=root_descriptor)
            try:
                _rename_noreplace_v1(
                    artifact.basename,
                    artifact.basename,
                    source_directory_descriptor=root_descriptor,
                    target_directory_descriptor=archive_descriptor,
                )
            except FileExistsError:
                raise M5PrerequisiteArchiveErrorV1(
                    "m5_prerequisite_archive_target_exists"
                ) from None
            moved.append(artifact)
            _validate_held_artifact_at(
                artifact, directory_descriptor=archive_descriptor
            )
            try:
                os.stat(
                    artifact.basename,
                    dir_fd=root_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                raise M5PrerequisiteArchiveErrorV1(
                    "m5_prerequisite_archive_artifact_changed"
                )
            os.fsync(root_descriptor)
            os.fsync(archive_descriptor)
        manifest_identity = _write_manifest(
            archive_descriptor,
            revision=revision,
            bundle_digest=bundle_digest,
            artifacts=artifacts,
            archived_at=archived_at,
        )
        os.fsync(archive_descriptor)
        os.fsync(archive_parent_descriptor)
        os.fsync(root_descriptor)
        for artifact in artifacts:
            _validate_held_artifact_at(
                artifact, directory_descriptor=archive_descriptor
            )
        return archive_id
    except M5PrerequisiteArchiveErrorV1 as error:
        if archive_descriptor >= 0 and moved:
            restored = _rollback(
                root_descriptor=root_descriptor,
                archive_descriptor=archive_descriptor,
                artifacts=artifacts,
                moved=moved,
                manifest_identity=manifest_identity,
            )
            if not restored:
                raise M5PrerequisiteArchiveErrorV1(
                    "m5_prerequisite_archive_rollback_failed"
                ) from error
        if str(error) in {
            "m5_prerequisite_archive_atomic_noreplace_unavailable",
            "m5_prerequisite_archive_target_exists",
            "m5_prerequisite_archive_target_invalid",
        }:
            raise
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_commit_failed"
        ) from error
    except OSError as error:
        if archive_descriptor >= 0 and moved:
            restored = _rollback(
                root_descriptor=root_descriptor,
                archive_descriptor=archive_descriptor,
                artifacts=artifacts,
                moved=moved,
                manifest_identity=manifest_identity,
            )
            if not restored:
                raise M5PrerequisiteArchiveErrorV1(
                    "m5_prerequisite_archive_rollback_failed"
                ) from error
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_commit_failed"
        ) from None
    finally:
        if archive_descriptor >= 0:
            os.close(archive_descriptor)
        if archive_parent_descriptor >= 0:
            os.close(archive_parent_descriptor)
        if archive_created:
            try:
                archive_directory = root / ARCHIVE_ROOT_BASENAME / archive_id
                if archive_directory.is_dir() and not tuple(
                    archive_directory.iterdir()
                ):
                    archive_directory.rmdir()
            except OSError:
                pass
        if archive_parent_created:
            try:
                archive_parent = root / ARCHIVE_ROOT_BASENAME
                if archive_parent.is_dir() and not tuple(archive_parent.iterdir()):
                    archive_parent.rmdir()
            except OSError:
                pass


def archive_m5_prerequisites_v1(
    owner_root: Path,
    *,
    current_revision: str,
    current_service_pid: int,
    current_service_start_time_ticks: int,
    now: datetime,
    final_receipt_path: Path,
) -> M5PrerequisiteArchiveResultV1:
    """Archive one stale, internally consistent prerequisite set."""

    if (
        _REVISION.fullmatch(current_revision) is None
        or type(current_service_pid) is not int
        or not 1 <= current_service_pid <= 9_999_999_999
        or type(current_service_start_time_ticks) is not int
        or not 1 <= current_service_start_time_ticks <= 2**63 - 1
        or now.utcoffset() != timedelta(0)
        or not final_receipt_path.is_absolute()
    ):
        raise M5PrerequisiteArchiveErrorV1("m5_prerequisite_archive_selection_invalid")
    root_descriptor = -1
    completion_lock: M5CompletionLockV1 | None = None
    artifacts: list[_OpenedArtifactV1] = []
    try:
        try:
            root_descriptor = os.open(
                owner_root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
        except OSError:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_root_invalid"
            ) from None
        root_device, root_inode = _validate_root(owner_root, root_descriptor)
        try:
            completion_lock = acquire_m5_completion_lock_v1(final_receipt_path)
        except M5CompletionLockErrorV1:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_lock_unavailable"
            ) from None
        if _validate_root(owner_root, root_descriptor) != (root_device, root_inode):
            raise M5PrerequisiteArchiveErrorV1("m5_prerequisite_archive_root_changed")
        try:
            validate_m5_completion_lock_v1(completion_lock)
        except M5CompletionLockErrorV1:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_lock_unavailable"
            ) from None
        try:
            final_receipt_path.lstat()
        except FileNotFoundError:
            pass
        except OSError:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_receipt_check_failed"
            ) from None
        else:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_final_receipt_exists"
            )
        for basename in PREREQUISITE_BASENAMES:
            artifact = _open_artifact(
                root_descriptor, basename, root_device=root_device
            )
            if artifact is not None:
                artifacts.append(artifact)
        if not artifacts or artifacts[0].basename != OWNER_OUTCOMES_BASENAME:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_owner_outcomes_required"
            )
        opened = tuple(artifacts)
        owner, owner_confirmed_at = _owner_context(opened[0])
        by_name = {item.basename: item for item in opened}
        quota = by_name.get(QUOTA_WITNESS_BASENAME)
        alert = by_name.get(ALERT_WITNESS_BASENAME)
        quota_recorded_at = (
            _quota_recorded_at(
                quota,
                owner=owner,
                owner_digest=opened[0].digest,
            )
            if quota is not None
            else None
        )
        alert_recorded_at = (
            _alert_recorded_at(owner_root, alert, owner=owner)
            if alert is not None
            else None
        )
        _require_stale_set(
            opened,
            owner=owner,
            owner_confirmed_at=owner_confirmed_at,
            quota_recorded_at=quota_recorded_at,
            alert_recorded_at=alert_recorded_at,
            current_revision=current_revision,
            current_service_pid=current_service_pid,
            current_service_start_time_ticks=current_service_start_time_ticks,
            now=now.astimezone(UTC),
        )
        if _validate_root(owner_root, root_descriptor) != (root_device, root_inode):
            raise M5PrerequisiteArchiveErrorV1("m5_prerequisite_archive_root_changed")
        bundle_digest = _bundle_digest(opened)
        try:
            validate_m5_completion_lock_v1(completion_lock)
        except M5CompletionLockErrorV1:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_lock_unavailable"
            ) from None
        archive_id = _archive_artifacts(
            owner_root,
            root_descriptor,
            root_device,
            opened,
            revision=owner.implementation_revision,
            bundle_digest=bundle_digest,
            archived_at=now.astimezone(UTC),
        )
        try:
            validate_m5_completion_lock_v1(completion_lock)
        except M5CompletionLockErrorV1:
            raise M5PrerequisiteArchiveErrorV1(
                "m5_prerequisite_archive_lock_unavailable"
            ) from None
        return M5PrerequisiteArchiveResultV1(
            archive_id,
            owner.implementation_revision,
            bundle_digest,
            len(opened),
            tuple((item.basename, item.digest) for item in opened),
        )
    finally:
        for artifact in artifacts:
            os.close(artifact.descriptor)
        if completion_lock is not None:
            release_m5_completion_lock_v1(completion_lock)
        if root_descriptor >= 0:
            os.close(root_descriptor)


def archive_from_environment_v1(
    environment: Mapping[str, str],
) -> M5PrerequisiteArchiveResultV1:
    """Select the exact live owner root/service and archive stale evidence."""

    try:
        service = _selected_service(environment)
        revision = _clean_revision()
    except (M3CurrentExitErrorV1, M5OwnerOutcomesErrorV1):
        raise M5PrerequisiteArchiveErrorV1(
            "m5_prerequisite_archive_selection_invalid"
        ) from None
    return archive_m5_prerequisites_v1(
        service.launch.data_root,
        current_revision=revision,
        current_service_pid=service.pid,
        current_service_start_time_ticks=service.start_time_ticks,
        now=datetime.now(UTC),
        final_receipt_path=RECEIPT_PATH,
    )


def main() -> int:
    try:
        result = archive_from_environment_v1(os.environ)
    except M5PrerequisiteArchiveErrorV1 as error:
        code = str(error)
        if re.fullmatch(r"[a-z0-9_]+", code) is None:
            code = "m5_prerequisite_archive_unavailable"
        print(f"M5 PREREQUISITE ARCHIVE: BLOCKED — {code}")
        return 3
    except (OSError, RuntimeError, TypeError, ValueError):
        print("M5 PREREQUISITE ARCHIVE: FAILED — execution_unavailable")
        return 1
    print(
        "M5 PREREQUISITE ARCHIVE: PASSED — "
        f"revision={result.implementation_revision} "
        f"artifact_count={result.artifact_count} "
        f"bundle_sha256={result.bundle_digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
