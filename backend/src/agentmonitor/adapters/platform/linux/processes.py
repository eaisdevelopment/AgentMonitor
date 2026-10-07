"""Bounded read-only Linux procfs implementation of CTR-RUN-006."""

from __future__ import annotations

import hashlib
import os
import stat
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.contracts.runtime_observation_v1 import (
    LiveProcessLocationV1,
    PlatformInspectionOutcomeV1,
    PlatformInspectionRequestV1,
    PlatformInspectionStateV1,
    ProcessCodeFieldV1,
    ProcessIdentityV1,
    ProcessLabelFieldV1,
    ProcessMetricFieldV1,
    ProcessSnapshotInputV1,
    RuntimeFieldStateV1,
)

LINUX_PROCESS_ADAPTER_VERSION = "1.1.0"
LINUX_PROCESS_SOURCE_VERSION = "linux-procfs-stat-exe-v1"
_MAX_STAT_BYTES = 16 * 1024
_MAX_BOOT_SCOPE_BYTES = 128
_ADMITTED_SELECTOR_IDENTITIES = {
    "linux.proc.claude-process.v1": "claude",
    "linux.proc.codex-process.v1": "codex",
}


@dataclass(frozen=True, slots=True)
class _ExecutableFileIdentity:
    device: int
    inode: int
    mode: int
    size_bytes: int
    modified_ns: int
    changed_ns: int

    def safe_fingerprint(self) -> str:
        canonical_identity = "\x1f".join(
            (
                "linux.proc.executable-identity.v1",
                str(self.device),
                str(self.inode),
                str(stat.S_IFMT(self.mode)),
                str(self.size_bytes),
                str(self.modified_ns),
                str(self.changed_ns),
            )
        ).encode("ascii")
        return hashlib.sha256(canonical_identity).hexdigest()


def _executable_file_identity(path: Path) -> _ExecutableFileIdentity:
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("linux_executable_identity_invalid")
    return _ExecutableFileIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        size_bytes=metadata.st_size,
        modified_ns=metadata.st_mtime_ns,
        changed_ns=metadata.st_ctime_ns,
    )


@dataclass(frozen=True, slots=True)
class ApprovedLinuxExecutableSelectorV1:
    """Composition-approved executable identity; its path never leaves A04."""

    selector_id: str
    executable_identity: str
    provider_key: str
    installation_id: str
    provider_version: str
    _executable: Path = field(repr=False, compare=False)
    _file_identity: _ExecutableFileIdentity = field(repr=False)

    @classmethod
    def from_executable(
        cls,
        *,
        selector_id: str,
        executable_identity: str,
        provider_key: str,
        installation_id: str,
        provider_version: str,
        executable: Path,
    ) -> ApprovedLinuxExecutableSelectorV1:
        resolved = executable.resolve(strict=True)
        if not os.access(resolved, os.X_OK):
            raise ValueError("linux_executable_identity_invalid")
        return cls(
            selector_id=selector_id,
            executable_identity=executable_identity,
            provider_key=provider_key,
            installation_id=installation_id,
            provider_version=provider_version,
            _executable=resolved,
            _file_identity=_executable_file_identity(resolved),
        )

    def is_current(self) -> bool:
        try:
            return _executable_file_identity(self._executable) == self._file_identity
        except (OSError, ValueError):
            return False


def _read_bounded(path: Path, maximum_bytes: int) -> bytes:
    """Read at most one byte beyond a fixed metadata limit, then fail closed."""
    if type(maximum_bytes) is not int or maximum_bytes <= 0:
        raise ValueError("linux_process_read_limit_invalid")
    with path.open("rb") as stream:
        raw = stream.read(maximum_bytes + 1)
    if len(raw) > maximum_bytes:
        raise ValueError("linux_process_source_oversize")
    return raw


def _missing(state: RuntimeFieldStateV1, reason_code: str) -> ProcessMetricFieldV1:
    return ProcessMetricFieldV1(
        state=state, value=None, unit=None, reason_code=reason_code
    )


def _present(value: int, unit: str) -> ProcessMetricFieldV1:
    return ProcessMetricFieldV1(
        state="present", value=value, unit=unit, reason_code=None
    )


def _missing_code(state: RuntimeFieldStateV1, reason_code: str) -> ProcessCodeFieldV1:
    return ProcessCodeFieldV1(state=state, value=None, reason_code=reason_code)


def _present_code(value: str) -> ProcessCodeFieldV1:
    return ProcessCodeFieldV1(state="present", value=value, reason_code=None)


def _present_label(value: str) -> ProcessLabelFieldV1:
    return ProcessLabelFieldV1(state="present", value=value, reason_code=None)


def _parse_stat(raw: bytes) -> tuple[str, str, int, int, int, int, int, int]:
    """Return comm, state, ppid, user/system ticks, threads, start ticks, RSS pages."""
    if len(raw) > _MAX_STAT_BYTES or not raw.endswith(b"\n"):
        raise ValueError("linux_process_stat_invalid")
    open_index = raw.find(b"(")
    close_index = raw.rfind(b")")
    if open_index <= 0 or close_index <= open_index:
        raise ValueError("linux_process_stat_invalid")
    try:
        comm = raw[open_index + 1 : close_index].decode("utf-8")
        fields = raw[close_index + 2 :].decode("ascii").split()
        state = fields[0]
        ppid = int(fields[1])
        user_ticks = int(fields[11])
        system_ticks = int(fields[12])
        thread_count = int(fields[17])
        start_ticks = int(fields[19])
        resident_pages = int(fields[21])
    except (UnicodeDecodeError, ValueError, IndexError) as error:
        raise ValueError("linux_process_stat_invalid") from error
    if (
        not comm
        or len(comm) > 255
        or len(state) != 1
        or ppid < 0
        or min(user_ticks, system_ticks, thread_count, start_ticks, resident_pages) < 0
        or start_ticks == 0
    ):
        raise ValueError("linux_process_stat_invalid")
    return (
        comm,
        state,
        ppid,
        user_ticks,
        system_ticks,
        thread_count,
        start_ticks,
        resident_pages,
    )


def _validate_system_units(clock_ticks: int, page_size: int) -> tuple[int, int]:
    if (
        type(clock_ticks) is not int
        or clock_ticks <= 0
        or type(page_size) is not int
        or page_size <= 0
    ):
        raise ValueError("linux_process_units_invalid")
    return clock_ticks, page_size


def _same_owner(expected_uid: int, observed_uid: int) -> bool:
    """Compare stable non-negative owner identities without coercion."""
    return (
        type(expected_uid) is int
        and expected_uid >= 0
        and type(observed_uid) is int
        and observed_uid >= 0
        and expected_uid == observed_uid
    )


def _comm_is_eligible(
    comm: str, executable_identity: str, *, exact_executable_verified: bool
) -> bool:
    """Use kernel comm only for generic discovery, never as verified identity."""
    return exact_executable_verified or comm == executable_identity


class InspectLinuxProcessesV1:
    """Inspect selected same-user processes without argv/environment/content."""

    def __init__(
        self,
        proc_root: Path = Path("/proc"),
        *,
        approved_executable_selectors: tuple[
            ApprovedLinuxExecutableSelectorV1, ...
        ] = (),
    ) -> None:
        self._proc_root = proc_root
        selector_keys = tuple(
            (
                item.selector_id,
                item.executable_identity,
                item.provider_key,
                item.installation_id,
                item.provider_version,
            )
            for item in approved_executable_selectors
        )
        if len(selector_keys) != len(set(selector_keys)):
            raise ValueError("linux_executable_selector_duplicate")
        self._approved_executable_selectors = approved_executable_selectors

    def __call__(
        self, request: PlatformInspectionRequestV1
    ) -> PlatformInspectionOutcomeV1:
        observed_at = datetime.now(UTC)
        if request.deadline_at <= observed_at:
            return self._failure(
                request, observed_at, "deadline_exceeded", "linux_deadline_exceeded"
            )
        approved_selector = self._approved_selector(request)
        if request.provider_key is not None and approved_selector is None:
            return self._failure(
                request,
                observed_at,
                "unverified_platform_version",
                "linux_provider_attribution_unverified",
            )
        if approved_selector is not None and not approved_selector.is_current():
            return self._failure(
                request,
                observed_at,
                "unverified_platform_version",
                "linux_executable_identity_unverified",
            )
        if request.source_id != "linux.proc.process.v1":
            return self._failure(
                request, observed_at, "unsupported", "linux_source_unverified"
            )
        expected_executable_identity = _ADMITTED_SELECTOR_IDENTITIES.get(
            request.selector_id
        )
        if expected_executable_identity is None:
            return self._failure(
                request, observed_at, "unsupported", "linux_selector_unverified"
            )
        if request.executable_identity != expected_executable_identity:
            return self._failure(
                request, observed_at, "invalid_request", "linux_selector_mismatch"
            )

        try:
            boot_id = _read_bounded(
                self._proc_root / "sys/kernel/random/boot_id",
                _MAX_BOOT_SCOPE_BYTES,
            )
            if not boot_id.endswith(b"\n"):
                raise ValueError("linux_boot_scope_invalid")
            boot_scope = boot_id.strip().decode("ascii")
            if not boot_scope or any(
                character not in "0123456789abcdef-" for character in boot_scope
            ):
                raise ValueError("linux_boot_scope_invalid")
            namespace_scope = os.readlink(self._proc_root / "self/ns/pid")
            if (
                not 1 <= len(namespace_scope) <= 128
                or not namespace_scope.isprintable()
                or not namespace_scope.startswith("pid:[")
                or not namespace_scope.endswith("]")
            ):
                raise ValueError("linux_pid_namespace_scope_invalid")
            platform_scope_id = hashlib.sha256(
                f"{boot_scope}\x1f{namespace_scope}".encode("ascii")
            ).hexdigest()
        except (OSError, UnicodeDecodeError, ValueError):
            return self._failure(
                request,
                observed_at,
                "source_unavailable",
                "linux_boot_scope_unavailable",
            )

        try:
            entries = sorted(
                (
                    entry
                    for entry in self._proc_root.iterdir()
                    if entry.name.isascii() and entry.name.isdigit()
                ),
                key=lambda item: int(item.name),
            )
        except OSError:
            return self._failure(
                request, observed_at, "source_unavailable", "linux_procfs_unavailable"
            )

        processes: list[ProcessSnapshotInputV1] = []
        omissions: set[str] = set()
        owner_uid = os.getuid()
        try:
            clock_ticks, page_size = _validate_system_units(
                os.sysconf("SC_CLK_TCK"), os.sysconf("SC_PAGE_SIZE")
            )
        except (OSError, ValueError):
            return self._failure(
                request,
                observed_at,
                "invalid_platform_data",
                "linux_process_units_invalid",
            )
        deadline_monotonic = time.monotonic() + max(
            0.0, (request.deadline_at - observed_at).total_seconds()
        )
        matched_candidates = 0
        for entry in entries[: request.maximum_candidates]:
            if time.monotonic() >= deadline_monotonic:
                omissions.add("deadline_exceeded")
                break
            try:
                if not _same_owner(owner_uid, entry.stat(follow_symlinks=False).st_uid):
                    continue
                before = _read_bounded(entry / "stat", _MAX_STAT_BYTES)
                parsed = _parse_stat(before)
            except (FileNotFoundError, ProcessLookupError):
                omissions.add("candidate_exited_before_classification")
                continue
            except PermissionError:
                omissions.add("candidate_permission_denied")
                continue
            except OSError:
                omissions.add("candidate_source_unavailable")
                continue
            except ValueError:
                omissions.add("candidate_layout_invalid")
                continue
            if not _comm_is_eligible(
                parsed[0],
                request.executable_identity,
                exact_executable_verified=approved_selector is not None,
            ):
                continue
            executable_file_identity: _ExecutableFileIdentity | None = None
            if approved_selector is not None:
                try:
                    executable_file_identity = _executable_file_identity(entry / "exe")
                except (FileNotFoundError, ProcessLookupError):
                    omissions.add("candidate_exited_before_executable_identity")
                    continue
                except PermissionError:
                    omissions.add("candidate_executable_identity_permission_denied")
                    continue
                except OSError:
                    omissions.add("candidate_executable_identity_unavailable")
                    continue
                except ValueError:
                    omissions.add("candidate_executable_identity_invalid")
                    continue
                if executable_file_identity != approved_selector._file_identity:
                    continue
            matched_candidates += 1
            try:
                after = _read_bounded(entry / "stat", _MAX_STAT_BYTES)
                after_parsed = _parse_stat(after)
                final_owner_uid = entry.stat(follow_symlinks=False).st_uid
            except (FileNotFoundError, ProcessLookupError):
                omissions.add("matched_process_exited")
                continue
            except PermissionError:
                omissions.add("matched_process_permission_denied")
                continue
            except OSError:
                omissions.add("matched_process_source_unavailable")
                continue
            except ValueError:
                omissions.add("matched_process_layout_invalid")
                continue
            if not _same_owner(owner_uid, final_owner_uid):
                omissions.add("matched_process_owner_changed")
                continue
            if (parsed[0], parsed[6]) != (after_parsed[0], after_parsed[6]):
                omissions.add("process_changed_during_inspection")
                continue
            if approved_selector is not None:
                try:
                    final_executable_identity = _executable_file_identity(entry / "exe")
                except (FileNotFoundError, ProcessLookupError):
                    omissions.add("matched_process_exited")
                    continue
                except PermissionError:
                    omissions.add("matched_process_executable_permission_denied")
                    continue
                except OSError:
                    omissions.add("matched_process_executable_unavailable")
                    continue
                except ValueError:
                    omissions.add("matched_process_executable_invalid")
                    continue
                if (
                    executable_file_identity != final_executable_identity
                    or final_executable_identity != approved_selector._file_identity
                ):
                    omissions.add("process_executable_changed_during_inspection")
                    continue
            (
                comm,
                state,
                ppid,
                user_ticks,
                system_ticks,
                threads,
                start_ticks,
                rss_pages,
            ) = parsed
            if len(processes) >= request.maximum_results:
                omissions.add("result_limit_reached")
                break
            pid = int(entry.name)
            identity = ProcessIdentityV1(
                platform_source=request.source_id,
                platform_scope_id=platform_scope_id,
                pid=pid,
                start_time_ticks=start_ticks,
            )
            observation_id = hashlib.sha256(
                f"{request.source_id}\x1f{pid}\x1f{start_ticks}\x1f{observed_at.isoformat()}".encode()
            ).hexdigest()
            requested = set(request.requested_fields)
            processes.append(
                ProcessSnapshotInputV1(
                    observation_id=observation_id,
                    identity=identity,
                    provider_key=(
                        approved_selector.provider_key
                        if approved_selector is not None
                        else None
                    ),
                    installation_id=(
                        approved_selector.installation_id
                        if approved_selector is not None
                        else None
                    ),
                    executable_label=_present_label(comm),
                    parent_pid=_present(ppid, "pid")
                    if "parent_pid" in requested
                    else _missing("not_requested", "field_not_requested"),
                    user_cpu_ticks=_present(user_ticks, "clock_tick")
                    if "user_cpu_ticks" in requested
                    else _missing("not_requested", "field_not_requested"),
                    system_cpu_ticks=_present(system_ticks, "clock_tick")
                    if "system_cpu_ticks" in requested
                    else _missing("not_requested", "field_not_requested"),
                    resident_pages=_present(rss_pages, "page")
                    if "resident_pages" in requested
                    else _missing("not_requested", "field_not_requested"),
                    thread_count=_present(threads, "thread")
                    if "thread_count" in requested
                    else _missing("not_requested", "field_not_requested"),
                    kernel_state=_present_code(state)
                    if "kernel_state" in requested
                    else _missing_code("not_requested", "field_not_requested"),
                    observed_at=observed_at,
                    source_id=request.source_id,
                    source_version=LINUX_PROCESS_SOURCE_VERSION,
                    adapter_version=LINUX_PROCESS_ADAPTER_VERSION,
                    clock_ticks_per_second=clock_ticks,
                    page_size_bytes=page_size,
                    executable_identity=(
                        executable_file_identity.safe_fingerprint()
                        if executable_file_identity is not None
                        else None
                    ),
                )
            )
        truncated = (
            len(entries) > request.maximum_candidates
            or "result_limit_reached" in omissions
        )
        if len(entries) > request.maximum_candidates:
            omissions.add("candidate_limit_reached")
        if approved_selector is not None and not approved_selector.is_current():
            return self._failure(
                request,
                observed_at,
                "unverified_platform_version",
                "linux_executable_identity_changed",
            )
        return PlatformInspectionOutcomeV1(
            state="partial" if omissions or truncated else "success",
            processes=tuple(processes),
            observed_at=observed_at,
            source_id=request.source_id,
            source_version=LINUX_PROCESS_SOURCE_VERSION,
            candidate_count=matched_candidates,
            truncated=truncated,
            omission_codes=tuple(sorted(omissions)),
            error_code=None,
        )

    def _approved_selector(
        self, request: PlatformInspectionRequestV1
    ) -> ApprovedLinuxExecutableSelectorV1 | None:
        if request.provider_key is None:
            return None
        expected = (
            request.selector_id,
            request.executable_identity,
            request.provider_key,
            request.installation_id,
            request.provider_version,
        )
        return next(
            (
                item
                for item in self._approved_executable_selectors
                if (
                    item.selector_id,
                    item.executable_identity,
                    item.provider_key,
                    item.installation_id,
                    item.provider_version,
                )
                == expected
            ),
            None,
        )

    def locations(
        self, request: PlatformInspectionRequestV1
    ) -> tuple[PlatformInspectionOutcomeV1, tuple[LiveProcessLocationV1, ...]]:
        """Read cwd only after exact executable discovery, with PID reuse guards."""
        outcome = self(request)
        selector = self._approved_selector(request)
        if selector is None or outcome.state not in {"success", "partial"}:
            return outcome, ()
        locations = []
        for snapshot in outcome.processes:
            if datetime.now(UTC) >= request.deadline_at:
                break
            entry = self._proc_root / str(snapshot.identity.pid)
            try:
                before = _parse_stat(_read_bounded(entry / "stat", _MAX_STAT_BYTES))
                if (
                    before[6] != snapshot.identity.start_time_ticks
                    or before[1] in {"Z", "X", "x"}
                    or not _same_owner(os.getuid(), entry.stat().st_uid)
                    or _executable_file_identity(entry / "exe")
                    != selector._file_identity
                ):
                    continue
                cwd: str | None
                try:
                    cwd = os.readlink(entry / "cwd")
                    if (
                        not cwd.startswith("/")
                        or not 1 <= len(cwd) <= 4096
                        or not cwd.isprintable()
                        or cwd.endswith(" (deleted)")
                    ):
                        cwd = None
                except OSError:
                    cwd = None
                after = _parse_stat(_read_bounded(entry / "stat", _MAX_STAT_BYTES))
                if (
                    (before[0], before[6]) != (after[0], after[6])
                    or not _same_owner(os.getuid(), entry.stat().st_uid)
                    or _executable_file_identity(entry / "exe")
                    != selector._file_identity
                    or not selector.is_current()
                ):
                    continue
                locations.append(
                    LiveProcessLocationV1(
                        snapshot.identity,
                        selector.provider_key,
                        cwd,
                        datetime.now(UTC),
                        snapshot=snapshot,
                        provider_version=selector.provider_version,
                    )
                )
            except (OSError, ValueError):
                continue
        return outcome, tuple(locations)

    @staticmethod
    def _failure(
        request: PlatformInspectionRequestV1,
        observed_at: datetime,
        state: PlatformInspectionStateV1,
        code: str,
    ) -> PlatformInspectionOutcomeV1:
        return PlatformInspectionOutcomeV1(
            state=state,
            processes=(),
            observed_at=observed_at,
            source_id=request.source_id,
            source_version=LINUX_PROCESS_SOURCE_VERSION,
            candidate_count=0,
            truncated=False,
            error_code=code,
        )
