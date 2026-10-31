"""Owner-clicked native authentication, safe receipts, and M02 enrollment."""

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
from agentmonitor.adapters.providers.claude.authentication.browser import (
    create_managed_browser_opener_v1,
)
from agentmonitor.adapters.providers.claude.authentication.identity import (
    claude_identity_environment_v1,
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.authentication.reauthentication import (
    ClaudeManagedLoginAttemptV1,
    ClaudeReauthenticationTargetV1,
    begin_managed_profile_authentication_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.composition.claude_managed_connection import (
    enroll_verified_managed_claude_v1,
    managed_claude_root_v1,
    managed_identity_matches_account_v1,
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
_STATES = _ACTIVE | {
    "connected",
    "wrong_account",
    "expired",
    "failed",
    "cancelled",
    "setup_required",
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
    "native_setup_required",
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
    attempt: ClaudeManagedLoginAttemptV1 | None = field(default=None, repr=False)


class ClaudeDashboardConnectionV1:
    """One explicit sign-in at a time; GET and service startup never start auth."""

    CONTRACT_ID: ClassVar[str] = "CTR-PROV-007"
    OWNER: ClassVar[str] = "PLAN-M03"

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

    def _receipt_directory(self, *, create: bool = False) -> Path:
        directory = self._data_root / "connection-flows"
        if create:
            directory.mkdir(mode=0o700, exist_ok=True)
        if directory.exists() or directory.is_symlink():
            claude_identity_environment_v1(directory)
        return directory

    def _load(self) -> None:
        if self._loaded:
            return
        directory = self._receipt_directory()
        paths = tuple(directory.glob("*.json")) if directory.exists() else ()
        if len(paths) > 256:
            raise ProviderConnectionErrorV1("provider_connection_unavailable")
        for path in paths:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600
                    or info.st_size > 4096
                ):
                    raise ProviderConnectionErrorV1("provider_connection_unavailable")
                raw = stream.read(4097)
            if len(raw) > 4096:
                raise ProviderConnectionErrorV1("provider_connection_unavailable")
            value = json.loads(raw)
            if (
                not isinstance(value, dict)
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
            ):
                raise ProviderConnectionErrorV1("provider_connection_unavailable")
            if any(
                not isinstance(value[name], str) for name in value if name != "version"
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
            state = cast(ProviderConnectionStateV1, value["state"])
            reason = value["reason_code"]
            if state in _ACTIVE:
                state, reason = "cancelled", "service_restarted"
            flow = _Flow(
                value["key"],
                value["request_fingerprint"],
                OpaqueIdV1(value["account_id"]),
                OpaqueIdV1(value["flow_id"]),
                state,
                reason,
                datetime.fromisoformat(value["started_at"]),
                datetime.fromisoformat(value["expires_at"]),
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
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        try:
            with os.fdopen(descriptor, "w") as stream:
                json.dump(value, stream)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(directory / (flow.key + ".json"))
        finally:
            temporary.unlink(missing_ok=True)

    def _view(
        self, account: AccountViewV1, flow: _Flow | None
    ) -> ProviderConnectionViewV1:
        profiles = self._registry.list_monitoring_profiles(account.account_id)
        prior = self._latest.get(account.account_id)
        recoverable = (
            account.lifecycle == "active"
            and prior is not None
            and prior.state
            in {"failed", "cancelled", "setup_required", "wrong_account"}
            and all(
                item.management_state == "managed" and not item.is_protected_default
                for item in profiles
            )
        )
        eligible = account.provider_key == "claude" and (
            (account.lifecycle == "pending" and not profiles) or recoverable
        )
        if flow is None:
            return ProviderConnectionViewV1(
                account.account_id,
                None,
                "connected"
                if account.lifecycle == "active"
                and account.identity_state in {"matched", "owner_confirmed"}
                and any(item.compatibility_state == "compatible" for item in profiles)
                else "idle",
                eligible,
                None,
                None,
                None,
                "pending_profile" if eligible else "account_not_connectable",
            )
        return ProviderConnectionViewV1(
            account.account_id,
            flow.flow_id,
            flow.state,
            eligible and flow.state not in _ACTIVE,
            flow.expected_email,
            flow.started_at,
            flow.expires_at,
            flow.reason_code,
        )

    def read(self, account_id: OpaqueIdV1) -> ProviderConnectionViewV1:
        with self._lock:
            self._load()
            return self._view(self._account(account_id), self._latest.get(account_id))

    def start(
        self, command: StartProviderConnectionCommandV1
    ) -> ProviderConnectionViewV1:
        with self._lock:
            self._load()
            account = self._account(command.account_id)
            key = hashlib.sha256(
                (
                    command.principal_id.value + "\0" + command.idempotency_key.value
                ).encode()
            ).hexdigest()
            fingerprint = hashlib.sha256(
                json.dumps(
                    [
                        command.account_id.value,
                        command.expected_record_version,
                        command.expected_email.casefold(),
                    ]
                ).encode()
            ).hexdigest()
            previous = self._flows.get(key)
            if previous is not None:
                if previous.request_fingerprint != fingerprint:
                    raise ProviderConnectionErrorV1("idempotency_key_reused")
                return self._view(account, previous)
            if account.record_version != command.expected_record_version:
                raise ProviderConnectionErrorV1("precondition_failed")
            if not self._view(account, None).can_connect:
                raise ProviderConnectionErrorV1("provider_connection_not_eligible")
            if (
                len(command.expected_email) > 320
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
                OpaqueIdV1("connection-" + uuid.uuid4().hex),
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
                target=self._connect, args=(flow, command), daemon=True
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
            installation = discover_default_installation()
            protected = read_default_profile_identity_v1(installation)
            if protected is None:
                raise ValueError("protected_identity_unavailable")
            root = managed_claude_root_v1(self._data_root, flow.account_id)
            for directory in (root.parent.parent, root.parent, root):
                directory.mkdir(mode=0o700, exist_ok=True)
                claude_identity_environment_v1(directory)
            initial = self._account(flow.account_id)
            if initial.record_version != command.expected_record_version:
                self._transition(flow, "failed", "account_changed")
                return
            if initial.lifecycle == "active":
                identity = read_default_profile_identity_v1(
                    installation, managed_profile_root=root
                )
                if identity is None or not managed_identity_matches_account_v1(
                    self._registry, flow.account_id, identity
                ):
                    raise ValueError("managed_recovery_identity_unverified")
            else:
                opener = create_managed_browser_opener_v1(
                    self._receipt_directory() / flow.flow_id.value
                )
                with self._lock:
                    if self._cancelled(flow):
                        return
                    attempt = begin_managed_profile_authentication_v1(
                        installation,
                        ClaudeReauthenticationTargetV1(
                            OpaqueIdV1(
                                "claude-managed-"
                                + hashlib.sha256(
                                    flow.account_id.value.encode()
                                ).hexdigest()
                            ),
                            "managed",
                            True,
                            True,
                        ),
                        managed_profile_root=root,
                        expected_email=command.expected_email,
                        browser_opener=opener,
                    )
                    flow.attempt = attempt
                    self._transition(
                        flow, "awaiting_sign_in", "complete_browser_sign_in"
                    )
                identity = attempt.wait_for_completion(timeout_seconds=600)
            if self._cancelled(flow):
                return
            if identity is None:
                expired = datetime.now(UTC) >= flow.expires_at
                self._transition(
                    flow,
                    "expired" if expired else "failed",
                    "sign_in_expired" if expired else "connection_failed",
                )
                return
            self._transition(flow, "verifying", "checking_account_identity")
            if identity.email.casefold() != command.expected_email.casefold():
                self._transition(flow, "wrong_account", "wrong_account_detected")
                return
            after = read_default_profile_identity_v1(installation)
            current = self._account(flow.account_id)
            if after is None or after.fingerprint != protected.fingerprint:
                raise ValueError("protected_identity_changed")
            if (
                current.record_version != command.expected_record_version
                or current.lifecycle not in {"pending", "active"}
            ):
                self._transition(flow, "failed", "account_changed")
                return
            with self._lock:
                if self._cancelled(flow):
                    return
                enroll_verified_managed_claude_v1(
                    self._reference,
                    data_root=self._data_root,
                    account_id=flow.account_id,
                    installation=installation,
                    expected_identity=identity,
                    principal_id=command.principal_id,
                    expected_account_record_version=command.expected_record_version,
                )
                self._transition(flow, "connected", "quota_pending")
        except (OSError, ValueError, RuntimeError):
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
