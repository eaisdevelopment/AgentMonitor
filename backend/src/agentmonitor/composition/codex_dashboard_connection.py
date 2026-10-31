"""Owner-clicked Codex initial login, private receipts, and M02 enrollment."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import stat
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar, cast

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.codex.authentication.identity import (
    read_managed_profile_identity_v1,
)
from agentmonitor.adapters.providers.codex.authentication.reauthentication import (
    CodexManagedAuthenticationTargetV1,
    CodexManagedLoginAttemptV1,
    begin_managed_profile_authentication_v1,
)
from agentmonitor.adapters.providers.codex.installation import (
    discover_default_installation,
)
from agentmonitor.composition.codex_installation_reconciliation import (
    reconcile_codex_installation_v1,
)
from agentmonitor.composition.codex_managed_connection import (
    enroll_verified_managed_codex_v1,
    ensure_managed_codex_root_v1,
    managed_codex_graph_state_v1,
    managed_codex_root_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    ProviderConnectionErrorV1,
    ProviderConnectionStateV1,
    ProviderConnectionViewV1,
    StartProviderConnectionCommandV1,
)
from agentmonitor.contracts.registry_v1 import AccountViewV1
from agentmonitor.modules.registry.application.accounts import GetAccountV1

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+\Z")
_ACTIVE = {"requested", "awaiting_sign_in", "verifying"}
_RESUMABLE = _ACTIVE | {"failed", "cancelled", "setup_required"}
_STATES = _ACTIVE | {
    "connected",
    "wrong_account",
    "expired",
    "failed",
    "cancelled",
}
_REASONS = {
    "owner_sign_in_requested",
    "complete_browser_sign_in",
    "checking_account_identity",
    "quota_pending",
    "wrong_account_detected",
    "sign_in_expired",
    "connection_failed",
    "owner_cancelled",
    "service_restarted",
    "account_changed",
    "enrollment_incomplete",
}


@dataclass(slots=True)
class _Flow:
    key: str
    request_fingerprint: str
    account_id: OpaqueIdV1
    flow_id: OpaqueIdV1
    state: ProviderConnectionStateV1
    reason_code: str
    started_at: datetime
    expires_at: datetime
    expected_email: str | None = field(default=None, repr=False)
    attempt: CodexManagedLoginAttemptV1 | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class CodexConnectionStatusV1:
    """Pure connection status derived from registry and optional flow state."""

    state: ProviderConnectionStateV1
    can_connect: bool
    reason_code: str


def resolve_codex_connection_status_v1(
    *,
    provider_key: str,
    lifecycle: str,
    identity_state: str,
    graph_state: str,
    monitoring_enabled: bool,
    flow_state: ProviderConnectionStateV1 | None,
    flow_reason_code: str | None,
) -> CodexConnectionStatusV1:
    """Apply the provider-neutral registry/flow eligibility policy without I/O."""
    identity_bound = identity_state in {"matched", "owner_confirmed"}
    graph_complete = (
        provider_key == "codex"
        and lifecycle == "active"
        and identity_bound
        and graph_state == "complete"
    )
    if type(monitoring_enabled) is not bool:
        raise TypeError("codex_monitoring_state_invalid")
    if graph_complete:
        return CodexConnectionStatusV1("connected", False, "account_not_connectable")
    pending = (
        provider_key == "codex" and lifecycle == "pending" and graph_state == "absent"
    )
    resumable = (
        provider_key == "codex"
        and lifecycle == "active"
        and identity_bound
        and graph_state == "absent"
        and flow_state in _RESUMABLE
    )
    eligible = pending or resumable
    if flow_state is None:
        return CodexConnectionStatusV1(
            "idle",
            eligible,
            "pending_profile" if pending else "account_not_connectable",
        )
    if flow_reason_code is None:
        raise ValueError("codex_connection_flow_reason_required")
    return CodexConnectionStatusV1(
        flow_state,
        eligible and flow_state not in _ACTIVE and flow_state != "wrong_account",
        flow_reason_code,
    )


class CodexDashboardConnectionV1:
    """Initial Codex login starts only from the explicit owner POST command."""

    CONTRACT_ID: ClassVar[str] = "CTR-PROV-007"
    OWNER: ClassVar[str] = "PLAN-INT"

    def __init__(self, reference: DatabaseRefV1, data_root: Path) -> None:
        self._reference = reference
        self._data_root = data_root
        self._registry = SqliteRegistryRepositoryV1(reference)
        self._lock = threading.RLock()
        self._flows: dict[str, _Flow] = {}
        self._latest: dict[OpaqueIdV1, _Flow] = {}
        self._loaded = False
        self._closed = False
        self._thread: threading.Thread | None = None

    def _account(self, account_id: OpaqueIdV1) -> AccountViewV1:
        account = GetAccountV1(self._registry)(account_id)
        if account is None:
            raise ProviderConnectionErrorV1("registry_subject_not_found")
        return account

    @staticmethod
    def _validate_private_directory(directory: Path) -> None:
        try:
            info = directory.lstat()
            resolved = directory.resolve(strict=True)
        except OSError as error:
            raise ProviderConnectionErrorV1(
                "provider_connection_unavailable"
            ) from error
        if (
            directory.is_symlink()
            or resolved != directory
            or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise ProviderConnectionErrorV1("provider_connection_unavailable")

    def _receipt_directory(self, *, create: bool = False) -> Path:
        parent = self._data_root / "connection-flows"
        directory = parent / "codex"
        for candidate in (self._data_root, parent, directory):
            if candidate == self._data_root:
                self._validate_private_directory(candidate)
                continue
            if create:
                try:
                    candidate.mkdir(mode=0o700, exist_ok=True)
                except OSError as error:
                    raise ProviderConnectionErrorV1(
                        "provider_connection_unavailable"
                    ) from error
            if candidate.exists() or candidate.is_symlink():
                self._validate_private_directory(candidate)
            elif candidate == parent and directory.exists():
                raise ProviderConnectionErrorV1("provider_connection_unavailable")
        return directory

    def _load(self) -> None:
        if self._loaded:
            return
        directory = self._receipt_directory()
        if not directory.exists():
            self._loaded = True
            return
        try:
            paths = tuple(directory.glob("*.json"))
        except OSError as error:
            raise ProviderConnectionErrorV1(
                "provider_connection_unavailable"
            ) from error
        if len(paths) > 256:
            raise ProviderConnectionErrorV1("provider_connection_unavailable")
        for path in paths:
            try:
                descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(descriptor, "rb") as stream:
                    info = os.fstat(stream.fileno())
                    if (
                        not stat.S_ISREG(info.st_mode)
                        or info.st_uid != os.getuid()
                        or stat.S_IMODE(info.st_mode) != 0o600
                        or info.st_size > 4096
                    ):
                        raise ProviderConnectionErrorV1(
                            "provider_connection_unavailable"
                        )
                    raw = stream.read(4097)
                if len(raw) > 4096:
                    raise ProviderConnectionErrorV1("provider_connection_unavailable")
                value = json.loads(raw)
            except ProviderConnectionErrorV1:
                raise
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ProviderConnectionErrorV1(
                    "provider_connection_unavailable"
                ) from error
            if (
                type(value) is not dict
                or set(value)
                != {
                    "version",
                    "key",
                    "request_fingerprint",
                    "account_id",
                    "flow_id",
                    "state",
                    "reason_code",
                    "started_at",
                    "expires_at",
                }
                or value["version"] != 1
                or any(
                    type(value[name]) is not str for name in value if name != "version"
                )
            ):
                raise ProviderConnectionErrorV1("provider_connection_unavailable")
            if (
                any(
                    re.fullmatch(r"[a-f0-9]{64}", value[key]) is None
                    for key in ("key", "request_fingerprint")
                )
                or path.name != value["key"] + ".json"
                or value["state"] not in _STATES
                or value["reason_code"] not in _REASONS
            ):
                raise ProviderConnectionErrorV1("provider_connection_unavailable")
            try:
                started_at = datetime.fromisoformat(value["started_at"])
                expires_at = datetime.fromisoformat(value["expires_at"])
                account_id = OpaqueIdV1(value["account_id"])
                flow_id = OpaqueIdV1(value["flow_id"])
            except (TypeError, ValueError) as error:
                raise ProviderConnectionErrorV1(
                    "provider_connection_unavailable"
                ) from error
            if (
                started_at.utcoffset() != timedelta(0)
                or expires_at.utcoffset() != timedelta(0)
                or expires_at <= started_at
                or expires_at - started_at > timedelta(minutes=10)
            ):
                raise ProviderConnectionErrorV1("provider_connection_unavailable")
            state = cast(ProviderConnectionStateV1, value["state"])
            reason = value["reason_code"]
            if state in _ACTIVE:
                state, reason = "cancelled", "service_restarted"
            flow = _Flow(
                value["key"],
                value["request_fingerprint"],
                account_id,
                flow_id,
                state,
                reason,
                started_at,
                expires_at,
            )
            self._flows[flow.key] = flow
            previous = self._latest.get(flow.account_id)
            if previous is None or previous.started_at < flow.started_at:
                self._latest[flow.account_id] = flow
        self._loaded = True

    def _save(self, flow: _Flow) -> None:
        if flow.state not in _STATES or flow.reason_code not in _REASONS:
            raise ValueError("connection_receipt_invalid")
        directory = self._receipt_directory(create=True)
        value = {
            "version": 1,
            "key": flow.key,
            "request_fingerprint": flow.request_fingerprint,
            "account_id": flow.account_id.value,
            "flow_id": flow.flow_id.value,
            "state": flow.state,
            "reason_code": flow.reason_code,
            "started_at": flow.started_at.isoformat(),
            "expires_at": flow.expires_at.isoformat(),
        }
        temporary = directory / ("." + uuid.uuid4().hex)
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(value, stream, separators=(",", ":"), sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(directory / (flow.key + ".json"))
            directory_descriptor = os.open(
                directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            temporary.unlink(missing_ok=True)

    def _view(
        self, account: AccountViewV1, flow: _Flow | None
    ) -> ProviderConnectionViewV1:
        graph_state = managed_codex_graph_state_v1(self._registry, account.account_id)
        status = resolve_codex_connection_status_v1(
            provider_key=account.provider_key,
            lifecycle=account.lifecycle,
            identity_state=account.identity_state,
            graph_state=graph_state,
            monitoring_enabled=account.is_effective_monitoring_enabled,
            flow_state=None if flow is None else flow.state,
            flow_reason_code=None if flow is None else flow.reason_code,
        )
        return ProviderConnectionViewV1(
            account.account_id,
            None if flow is None else flow.flow_id,
            status.state,
            status.can_connect,
            None if flow is None else flow.expected_email,
            None if flow is None else flow.started_at,
            None if flow is None else flow.expires_at,
            status.reason_code,
        )

    def read(self, account_id: OpaqueIdV1) -> ProviderConnectionViewV1:
        with self._lock:
            self._load()
            return self._view(self._account(account_id), self._latest.get(account_id))

    def _flow_remains_eligible(self, account: AccountViewV1, flow: _Flow) -> bool:
        """Validate the saved active flow without authorizing a second start."""
        with self._lock:
            if (
                self._latest.get(account.account_id) is not flow
                or flow.state not in _ACTIVE
            ):
                return False
            graph_state = managed_codex_graph_state_v1(
                self._registry, account.account_id
            )
            return (
                account.provider_key == "codex"
                and graph_state == "absent"
                and (
                    account.lifecycle == "pending"
                    or (
                        account.lifecycle == "active"
                        and account.identity_state in {"matched", "owner_confirmed"}
                    )
                )
            )

    def start(
        self, command: StartProviderConnectionCommandV1
    ) -> ProviderConnectionViewV1:
        with self._lock:
            self._load()
            account = self._account(command.account_id)
            key = hashlib.sha256(
                (
                    command.principal_id.value + "\0" + command.idempotency_key.value
                ).encode("utf-8")
            ).hexdigest()
            fingerprint = hashlib.sha256(
                json.dumps(
                    [
                        command.account_id.value,
                        command.expected_record_version,
                        command.expected_email.casefold(),
                    ],
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            previous = self._flows.get(key)
            if previous is not None:
                if previous.request_fingerprint != fingerprint:
                    raise ProviderConnectionErrorV1("idempotency_key_reused")
                return self._view(account, previous)
            if account.record_version != command.expected_record_version:
                raise ProviderConnectionErrorV1("precondition_failed")
            latest = self._latest.get(account.account_id)
            if latest is not None and latest.state == "wrong_account":
                raise ProviderConnectionErrorV1("provider_connection_not_eligible")
            if not self._view(account, latest).can_connect:
                raise ProviderConnectionErrorV1("provider_connection_not_eligible")
            if (
                type(command.expected_email) is not str
                or len(command.expected_email) > 254
                or _EMAIL.fullmatch(command.expected_email) is None
            ):
                raise ProviderConnectionErrorV1("provider_connection_email_required")
            if self._closed or len(self._flows) >= 256:
                raise ProviderConnectionErrorV1("provider_connection_unavailable")
            if self._thread is not None and self._thread.is_alive():
                raise ProviderConnectionErrorV1("provider_connection_busy")
            now = datetime.now(UTC)
            flow = _Flow(
                key,
                fingerprint,
                account.account_id,
                OpaqueIdV1("codex-connection-" + uuid.uuid4().hex),
                "requested",
                "owner_sign_in_requested",
                now,
                now + timedelta(minutes=10),
                command.expected_email,
            )
            self._save(flow)
            self._flows[key] = flow
            self._latest[account.account_id] = flow
            self._thread = threading.Thread(
                target=self._connect,
                args=(flow, command),
                name="codex-managed-connection",
                daemon=True,
            )
            self._thread.start()
            return self._view(account, flow)

    def _transition(
        self, flow: _Flow, state: ProviderConnectionStateV1, reason: str
    ) -> None:
        with self._lock:
            if flow.state == "cancelled":
                return
            flow.state, flow.reason_code = state, reason
            self._save(flow)

    def _cancelled(self, flow: _Flow) -> bool:
        with self._lock:
            return self._closed or flow.state == "cancelled"

    def _connect(self, flow: _Flow, command: StartProviderConnectionCommandV1) -> None:
        try:
            reconcile_codex_installation_v1(self._reference)
            installation = discover_default_installation()
            root = ensure_managed_codex_root_v1(self._data_root, flow.account_id)
            current = self._account(flow.account_id)
            if (
                current.record_version != command.expected_record_version
                or not self._flow_remains_eligible(current, flow)
            ):
                self._transition(flow, "failed", "account_changed")
                return
            identity = read_managed_profile_identity_v1(
                installation,
                managed_profiles_root=root.parent,
                managed_profile_root=root,
            )
            if identity is None:
                if current.lifecycle != "pending":
                    self._transition(flow, "failed", "connection_failed")
                    return
                with self._lock:
                    if self._cancelled(flow):
                        return
                    attempt = begin_managed_profile_authentication_v1(
                        installation,
                        CodexManagedAuthenticationTargetV1(
                            OpaqueIdV1(
                                "codex-managed-"
                                + hashlib.sha256(
                                    flow.account_id.value.encode("utf-8")
                                ).hexdigest()
                            ),
                            "managed",
                            True,
                            True,
                            False,
                        ),
                        managed_profiles_root=root.parent,
                        managed_profile_root=root,
                        expected_email=command.expected_email,
                    )
                    flow.attempt = attempt
                    self._transition(
                        flow, "awaiting_sign_in", "complete_browser_sign_in"
                    )
                remaining = min(
                    600.0,
                    (flow.expires_at - datetime.now(UTC)).total_seconds(),
                )
                if remaining <= 0:
                    attempt.cancel()
                    self._transition(flow, "expired", "sign_in_expired")
                    return
                if not attempt.wait_for_completion(timeout_seconds=remaining):
                    if not self._cancelled(flow):
                        expired = datetime.now(UTC) >= flow.expires_at
                        self._transition(
                            flow,
                            "expired" if expired else "failed",
                            "sign_in_expired" if expired else "connection_failed",
                        )
                    return
                identity = read_managed_profile_identity_v1(
                    installation,
                    managed_profiles_root=root.parent,
                    managed_profile_root=root,
                )
            if self._cancelled(flow):
                return
            if identity is None:
                self._transition(flow, "failed", "connection_failed")
                return
            self._transition(flow, "verifying", "checking_account_identity")
            if identity.email.casefold() != command.expected_email.casefold():
                self._transition(flow, "wrong_account", "wrong_account_detected")
                return
            verified = read_managed_profile_identity_v1(
                installation,
                managed_profiles_root=root.parent,
                managed_profile_root=root,
            )
            if (
                verified is None
                or verified.fingerprint != identity.fingerprint
                or verified.email.casefold() != command.expected_email.casefold()
            ):
                self._transition(flow, "failed", "connection_failed")
                return
            current = self._account(flow.account_id)
            if (
                current.record_version != command.expected_record_version
                or not self._flow_remains_eligible(current, flow)
            ):
                self._transition(flow, "failed", "account_changed")
                return
            with self._lock:
                if self._cancelled(flow):
                    return
                enroll_verified_managed_codex_v1(
                    self._reference,
                    data_root=self._data_root,
                    account_id=flow.account_id,
                    installation=installation,
                    expected_identity=verified,
                    principal_id=command.principal_id,
                    expected_account_record_version=command.expected_record_version,
                )
                self._transition(flow, "connected", "quota_pending")
        except (OSError, RuntimeError, TypeError, ValueError):
            self._transition(flow, "failed", "connection_failed")
        finally:
            if flow.attempt is not None:
                flow.attempt.cancel()

    def cancel(
        self, account_id: OpaqueIdV1, flow_id: OpaqueIdV1
    ) -> ProviderConnectionViewV1:
        with self._lock:
            self._load()
            account = self._account(account_id)
            flow = self._latest.get(account_id)
            if flow is None or flow.flow_id != flow_id:
                raise ProviderConnectionErrorV1("provider_connection_not_found")
            attempt = flow.attempt
            if flow.state in _ACTIVE:
                flow.state, flow.reason_code = "cancelled", "owner_cancelled"
                self._save(flow)
        if attempt is not None and flow.state == "cancelled":
            attempt.cancel()
        return self._view(account, flow)

    async def run(self) -> None:
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            with self._lock:
                self._closed = True
                active = tuple(
                    flow for flow in self._flows.values() if flow.state in _ACTIVE
                )
                for flow in active:
                    flow.state, flow.reason_code = "cancelled", "service_restarted"
                    self._save(flow)
            for flow in active:
                if flow.attempt is not None:
                    await asyncio.to_thread(flow.attempt.cancel)
            thread = self._thread
            until = time.monotonic() + 12
            while thread is not None and thread.is_alive() and time.monotonic() < until:
                await asyncio.sleep(0.05)
            if thread is not None and thread.is_alive():
                raise RuntimeError("connection_shutdown_incomplete")


__all__ = [
    "CodexConnectionStatusV1",
    "CodexDashboardConnectionV1",
    "managed_codex_root_v1",
    "resolve_codex_connection_status_v1",
]
