"""Bounded private, create-once recovery exports for financial retention."""

import fcntl
import hashlib
import io
import json
import os
import re
import stat
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

from agentmonitor.contracts.capacity_retention_v1 import (
    BudgetRetentionExportRecordV1,
    BudgetRetentionRecordCodecV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import OperationsParticipantRequestV1

MAX_EXPORT_BYTES = 24 * 1024 * 1024
MAX_ARCHIVE_BYTES = MAX_EXPORT_BYTES + 65536
MAX_STORED_BYTES = 256 * 1024 * 1024
MAX_DIRECTORY_ENTRIES = 4096
RECOVERY_DAYS = 7
_NAME = re.compile(r"budget-checkpoint-[a-f0-9]{64}\.zip")
_DATA_NAME = "budget-reports-v1.ndjson"


def _json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def utc_text(value: datetime) -> str:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError("budget_checkpoint_time_invalid")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _payload(
    request: OperationsParticipantRequestV1,
    records: tuple[BudgetRetentionExportRecordV1, ...],
    codec: BudgetRetentionRecordCodecV1,
) -> tuple[bytes, dict[str, object]]:
    if (
        not isinstance(request, OperationsParticipantRequestV1)
        or request.limit != 1
        or request.cutoff is None
        or request.preview_digest is None
        or request.prepared_database_ref is not None
        or type(records) is not tuple
        or len(records) != 1
        or not isinstance(records[0], BudgetRetentionExportRecordV1)
    ):
        raise ValueError("budget_checkpoint_request_invalid")
    record = records[0]
    receipt = record.receipt
    payload = codec.encode(record)
    if len(payload) > MAX_EXPORT_BYTES - 16384:
        raise ValueError("budget_checkpoint_export_too_large")
    manifest: dict[str, object] = {
        "schema": "agentmonitor-budget-retention-checkpoint-v1",
        "operation_id": request.operation_id.value,
        "correlation_id": request.correlation_id.value,
        "cutoff": utc_text(request.cutoff),
        "deadline": utc_text(request.deadline),
        "contract_major": request.contract_major,
        "limit": request.limit,
        "cursor": request.cursor,
        "preview_digest": request.preview_digest,
        "record_count": 1,
        "fact_count": len(receipt.fact_ids),
        "report_sequence": record.report_sequence,
        "report_id": record.report.report_id.value,
        "receipt_id": record.receipt_id.value,
        "provenance_id": record.provenance_id.value,
        "data_name": _DATA_NAME,
        "data_bytes": len(payload),
        "data_sha256": hashlib.sha256(payload).hexdigest(),
    }
    return payload, manifest


def _private_file(info: os.stat_result) -> bool:
    return (
        stat.S_ISREG(info.st_mode)
        and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_uid == os.getuid()
        and info.st_nlink == 1
    )


class FilesystemBudgetRetentionCheckpointV1:
    """No download path escapes this adapter; an opaque ID selects one archive.

    Cleanup removes only fully validated, expired owned archives. Reaching the
    cap refuses new exports; recent recovery is never pruned to make room.
    """

    CONTRACT_ID: ClassVar[str] = "CTR-OPS-007"
    CONTRACT_VERSION: ClassVar[str] = "1.1.0"
    OWNER: ClassVar[str] = "PLAN-M08"

    def __init__(self, root: Path, *, codec: BudgetRetentionRecordCodecV1) -> None:
        self._root = root
        self._codec = codec
        with self._directory():
            pass

    @contextmanager
    def _directory(self) -> Iterator[int]:
        descriptor = None
        try:
            if not self._root.is_absolute() or self._root.resolve() != self._root:
                raise ValueError("budget_checkpoint_directory_unsafe")
            self._root.mkdir(mode=0o700, exist_ok=True)
            info = self._root.lstat()
            if (
                not stat.S_ISDIR(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o700
                or info.st_uid != os.getuid()
            ):
                raise ValueError("budget_checkpoint_directory_unsafe")
            descriptor = os.open(
                self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise ValueError("budget_checkpoint_directory_unsafe")
            yield descriptor
        except OSError:
            raise ValueError("budget_checkpoint_directory_unsafe") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)

    @contextmanager
    def _locked(self, directory: int) -> Iterator[None]:
        descriptor = os.open(
            ".lock",
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        try:
            if not _private_file(os.fstat(descriptor)):
                raise ValueError("budget_checkpoint_file_unsafe")
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(descriptor)

    @staticmethod
    def _names(directory: int) -> tuple[str, ...]:
        names: list[str] = []
        with os.scandir(directory) as entries:
            for entry in entries:
                if len(names) == MAX_DIRECTORY_ENTRIES:
                    raise ValueError("budget_checkpoint_directory_limit")
                names.append(entry.name)
        return tuple(names)

    def _stored_bytes(self, directory: int) -> int:
        total = 0
        for name in self._names(directory):
            if name != ".lock" and _NAME.fullmatch(name) is None:
                raise ValueError("budget_checkpoint_directory_contents_unsafe")
            info = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if not _private_file(info):
                raise ValueError("budget_checkpoint_file_unsafe")
            total += info.st_size
            if total > MAX_STORED_BYTES:
                raise ValueError("budget_checkpoint_storage_limit")
        return total

    def _read_archive(
        self, directory: int, name: str
    ) -> tuple[bytes, dict[str, Any], os.stat_result]:
        descriptor = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory
        )
        with os.fdopen(descriptor, "rb") as source:
            info = os.fstat(source.fileno())
            if not _private_file(info) or not 1 <= info.st_size <= MAX_ARCHIVE_BYTES:
                raise ValueError("budget_checkpoint_file_unsafe")
            data = source.read(MAX_ARCHIVE_BYTES + 1)
            if len(data) != info.st_size:
                raise ValueError("budget_checkpoint_file_unsafe")
        with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
            entries = archive.infolist()
            if (
                len(entries) != 2
                or {entry.filename for entry in entries}
                != {"manifest.json", _DATA_NAME}
                or any(
                    entry.compress_type != zipfile.ZIP_STORED
                    or entry.file_size != entry.compress_size
                    or entry.file_size > MAX_EXPORT_BYTES
                    for entry in entries
                )
                or sum(entry.file_size for entry in entries) > MAX_EXPORT_BYTES
                or archive.getinfo("manifest.json").file_size > 16384
            ):
                raise ValueError("budget_checkpoint_archive_invalid")
            manifest_bytes = archive.read("manifest.json")
            manifest = json.loads(manifest_bytes)
            if type(manifest) is not dict or manifest_bytes != _json(manifest):
                raise ValueError("budget_checkpoint_manifest_invalid")
            payload = archive.read(_DATA_NAME)
            record = self._codec.decode(payload)
            request = OperationsParticipantRequestV1(
                OpaqueIdV1(manifest["operation_id"]),
                OpaqueIdV1(manifest["correlation_id"]),
                datetime.fromisoformat(manifest["deadline"]),
                manifest["contract_major"],
                datetime.fromisoformat(manifest["cutoff"]),
                manifest["limit"],
                manifest["cursor"],
                manifest["preview_digest"],
                None,
                None,
            )
            canonical, expected = _payload(request, (record,), self._codec)
            created = datetime.fromisoformat(manifest["created_at"])
            expires = datetime.fromisoformat(manifest["expires_at"])
            if (
                set(manifest) != set(expected) | {"created_at", "expires_at"}
                or utc_text(created) != manifest["created_at"]
                or utc_text(expires) != manifest["expires_at"]
                or expires != created + timedelta(days=RECOVERY_DAYS)
                or any(manifest[key] != value for key, value in expected.items())
                or canonical != payload
                or name
                != "budget-checkpoint-"
                + hashlib.sha256(_json(expected)).hexdigest()
                + ".zip"
            ):
                raise ValueError("budget_checkpoint_manifest_invalid")
            return payload, manifest, info

    def _verify(
        self, directory: int, name: str, payload: bytes, expected: dict[str, object]
    ) -> bool:
        stored, manifest, _ = self._read_archive(directory, name)
        return (
            stored == payload
            and all(manifest[key] == value for key, value in expected.items())
            and datetime.fromisoformat(manifest["created_at"])
            <= datetime.now(UTC)
            < datetime.fromisoformat(manifest["expires_at"])
        )

    def find_prepared(
        self, request: OperationsParticipantRequestV1
    ) -> OperationsParticipantRequestV1 | None:
        """Recover one exact original intent, without changing its deadline."""
        if (
            request.limit != 1
            or request.cutoff is None
            or request.preview_digest is not None
            or request.checkpoint_id is not None
            or request.prepared_database_ref is not None
            or request.deadline <= datetime.now(UTC)
        ):
            raise ValueError("budget_checkpoint_request_invalid")
        expected = {
            "operation_id": request.operation_id.value,
            "correlation_id": request.correlation_id.value,
            "cutoff": utc_text(request.cutoff),
            "deadline": utc_text(request.deadline),
            "contract_major": request.contract_major,
            "limit": request.limit,
            "cursor": request.cursor,
        }
        result = None
        try:
            with self._directory() as directory, self._locked(directory):
                self._stored_bytes(directory)
                for name in self._names(directory):
                    if name == ".lock":
                        continue
                    _, manifest, _ = self._read_archive(directory, name)
                    if any(manifest[key] != value for key, value in expected.items()):
                        continue
                    now = datetime.now(UTC)
                    if (
                        not datetime.fromisoformat(manifest["created_at"])
                        <= now
                        < datetime.fromisoformat(manifest["expires_at"])
                    ):
                        raise ValueError("budget_checkpoint_recovery_expired")
                    recovered = replace(
                        request,
                        preview_digest=manifest["preview_digest"],
                        checkpoint_id=OpaqueIdV1(name[:-4]),
                    )
                    if result is not None and result != recovered:
                        raise ValueError("budget_checkpoint_recovery_ambiguous")
                    result = recovered
        except (
            OSError,
            zipfile.BadZipFile,
            RuntimeError,
            EOFError,
            KeyError,
            TypeError,
        ):
            raise ValueError("budget_checkpoint_recovery_unavailable") from None
        return result

    def cleanup_expired(self, *, as_of: datetime, limit: int = 32) -> int:
        """Explicit bounded cleanup; invalid or foreign files are never deleted."""
        utc_text(as_of)
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("budget_checkpoint_cleanup_invalid")
        removed = 0
        try:
            with self._directory() as directory, self._locked(directory):
                for name in self._names(directory):
                    if removed == limit:
                        break
                    if _NAME.fullmatch(name) is None:
                        continue
                    try:
                        _, manifest, info = self._read_archive(directory, name)
                    except (
                        OSError,
                        ValueError,
                        TypeError,
                        KeyError,
                        zipfile.BadZipFile,
                        RuntimeError,
                        EOFError,
                    ):
                        continue
                    if datetime.fromisoformat(manifest["expires_at"]) > as_of:
                        continue
                    current = os.stat(name, dir_fd=directory, follow_symlinks=False)
                    if not _private_file(current) or (
                        current.st_dev,
                        current.st_ino,
                        current.st_size,
                        current.st_mtime_ns,
                    ) != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns):
                        continue
                    os.unlink(name, dir_fd=directory)
                    removed += 1
                if removed:
                    os.fsync(directory)
        except OSError:
            raise ValueError("budget_checkpoint_cleanup_unavailable") from None
        return removed

    def store(
        self,
        request: OperationsParticipantRequestV1,
        records: tuple[BudgetRetentionExportRecordV1, ...],
    ) -> OpaqueIdV1:
        payload, base = _payload(request, records, self._codec)
        identity = OpaqueIdV1(
            "budget-checkpoint-" + hashlib.sha256(_json(base)).hexdigest()
        )
        if request.checkpoint_id not in {None, identity}:
            raise ValueError("budget_checkpoint_identity_invalid")
        name = identity.value + ".zip"
        created = datetime.now(UTC)
        manifest = base | {
            "created_at": utc_text(created),
            "expires_at": utc_text(created + timedelta(days=RECOVERY_DAYS)),
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("manifest.json", _json(manifest))
            archive.writestr(_DATA_NAME, payload)
        content = buffer.getvalue()
        if len(content) > MAX_ARCHIVE_BYTES:
            raise ValueError("budget_checkpoint_export_too_large")
        try:
            with self._directory() as directory, self._locked(directory):
                stored = self._stored_bytes(directory)
                if name in self._names(directory):
                    if not self._verify(directory, name, payload, base):
                        raise ValueError("budget_checkpoint_verification_failed")
                    return identity
                if stored + len(content) > MAX_STORED_BYTES:
                    raise ValueError("budget_checkpoint_storage_limit")
                descriptor = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=directory,
                )
                with os.fdopen(descriptor, "wb") as target:
                    target.write(content)
                    target.flush()
                    os.fsync(target.fileno())
                os.fsync(directory)
                if not self._verify(directory, name, payload, base):
                    raise ValueError("budget_checkpoint_verification_failed")
        except (OSError, zipfile.BadZipFile, RuntimeError, EOFError):
            raise ValueError("budget_checkpoint_storage_unavailable") from None
        return identity

    def verify(
        self,
        request: OperationsParticipantRequestV1,
        records: tuple[BudgetRetentionExportRecordV1, ...],
    ) -> bool:
        try:
            payload, base = _payload(request, records, self._codec)
            identity = "budget-checkpoint-" + hashlib.sha256(_json(base)).hexdigest()
            if request.checkpoint_id != OpaqueIdV1(identity):
                return False
            with self._directory() as directory, self._locked(directory):
                self._stored_bytes(directory)
                return self._verify(directory, identity + ".zip", payload, base)
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            zipfile.BadZipFile,
            RuntimeError,
            EOFError,
        ):
            return False
