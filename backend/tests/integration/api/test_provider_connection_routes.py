"""Dashboard connection safeguards over real HTTP, SQLite, and native identity."""

import asyncio
import hashlib
import http.cookiejar
import json
import secrets
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.claude.authentication.identity import (
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.composition.codex_installation_reconciliation import (
    reconcile_codex_installation_v1,
)
from agentmonitor.composition.codex_managed_connection import (
    _complete_matched_codex_registry_v1,
    managed_codex_root_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import ObservedProfileIdentityV1
from agentmonitor.contracts.registry_v1 import (
    ConfirmProviderIdentityFingerprintCommandV1,
    PrivateProfileLocatorRefV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    ConfirmProviderIdentityFingerprintV1,
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    EditAccountV1,
    EnrollMonitoringGraphCommandV1,
    EnrollMonitoringGraphV1,
    RegisterAccountV1,
)

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


def _disabled_complete_codex_account(tmp_path: Path) -> tuple[str, str]:
    """Create only AgentMonitor registry state; no provider identity is read."""
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    installation = reconcile_codex_installation_v1(reference)
    repository = SqliteRegistryRepositoryV1(reference)
    owner = OpaqueIdV1("codex-disabled-owner")
    pending = RegisterAccountV1(repository).pending(
        CreatePendingAccountCommandV1(
            OpaqueIdV1(uuid.uuid4().hex),
            owner,
            "codex",
            get_manifest_fingerprint_v1(build_codex_manifest()),
            "Disabled connected Codex",
            None,
            datetime.now(UTC),
        )
    )
    fingerprint = hashlib.sha256(b"disabled-connected-codex").hexdigest()
    ConfirmProviderIdentityFingerprintV1(repository)(
        ConfirmProviderIdentityFingerprintCommandV1(
            idempotency_key=OpaqueIdV1(uuid.uuid4().hex),
            principal_id=owner,
            account_id=pending.account_id,
            expected_account_record_version=pending.record_version,
            provider_key="codex",
            identity_scheme="codex.app_server.account.sha256",
            identity_scope="provider_account",
            identity_scheme_version=1,
            subject_fingerprint=fingerprint,
            source_id="codex.app-server.account-read.v2",
            source_version="2",
            parser_version="1.0.0",
            evidence_reference=OpaqueIdV1("disabled-connected-evidence"),
            expected_evidence_digest=fingerprint,
            requested_at=datetime.now(UTC),
            activate_pending_account=True,
        )
    )
    locator = "codex-disabled-complete-profile"
    EnrollMonitoringGraphV1(repository)(
        EnrollMonitoringGraphCommandV1(
            command_id=OpaqueIdV1("codex-disabled-enrollment"),
            principal_id=owner,
            account_id=pending.account_id,
            provider_installation_id=installation.provider_installation_id,
            purpose="subscription",
            profile_locator_ref=PrivateProfileLocatorRefV1(locator),
            locator_fingerprint=hashlib.sha256(locator.encode()).hexdigest(),
            management_state="managed",
            compatibility_state="compatible",
            is_protected_default=False,
            resource_kind="subscription_pool",
            parent_resource_id=None,
            requested_at=datetime.now(UTC),
        )
    )
    active = repository.get_account(pending.account_id)
    assert active is not None
    enabled = EditAccountV1(repository)(
        EditAccountCommandV1(
            account_id=active.account_id,
            expected_version=active.record_version,
            principal_id=owner,
            command_id=OpaqueIdV1("codex-disabled-enable"),
            action="monitoring",
            monitoring_preference="enabled",
            requested_at=datetime.now(UTC),
        )
    )
    disabled = EditAccountV1(repository)(
        EditAccountCommandV1(
            account_id=enabled.account_id,
            expected_version=enabled.record_version,
            principal_id=owner,
            command_id=OpaqueIdV1("codex-disabled-disable"),
            action="monitoring",
            monitoring_preference="disabled",
            requested_at=datetime.now(UTC),
        )
    )
    assert not disabled.is_effective_monitoring_enabled
    return disabled.account_id.value, fingerprint


def test_replayed_complete_codex_enrollment_preserves_monitoring_preference(
    tmp_path: Path,
) -> None:
    """FR-ACC-003: idempotent graph completion cannot undo an owner disable."""
    _installation(tmp_path)
    account_id, fingerprint = _disabled_complete_codex_account(tmp_path)
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    repository = SqliteRegistryRepositoryV1(reference)
    installations = repository.list_provider_installations("codex")
    assert len(installations) == 1

    _complete_matched_codex_registry_v1(
        repository,
        account_id=OpaqueIdV1(account_id),
        provider_installation_id=installations[0].provider_installation_id,
        identity=ObservedProfileIdentityV1(
            "owner@example.invalid",
            None,
            fingerprint,
            datetime.now(UTC),
            "0.160.0",
        ),
        principal_id=OpaqueIdV1("codex-disabled-owner"),
    )

    account = repository.get_account(OpaqueIdV1(account_id))
    assert account is not None
    assert account.monitoring_preference == "disabled"
    assert not account.is_effective_monitoring_enabled


def test_disabled_complete_codex_connection_cannot_restart_or_enable_monitoring(
    tmp_path: Path,
) -> None:
    """FR-ACC-003/M5-CDX-CONNECT-010: connection POST preserves monitoring off."""
    app, credential = _installation(tmp_path)
    account_id, _ = _disabled_complete_codex_account(tmp_path)
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    # If the Red implementation starts background work, this isolated unsafe
    # root stops it before Codex login can begin.
    root = managed_codex_root_v1(tmp_path, OpaqueIdV1(account_id))
    root.parent.mkdir(mode=0o700, parents=True)
    root.parent.parent.chmod(0o700)
    root.parent.chmod(0o700)
    target = tmp_path / "disabled-connection-unsafe-target"
    target.mkdir(mode=0o700)
    root.symlink_to(target, target_is_directory=True)

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            account_path = "/api/v1/accounts/" + account_id
            account_response = await asyncio.to_thread(
                _request, origin, "GET", account_path, cookies=jar
            )
            assert account_response[0] == 200
            connection_path = account_path + "/connection"
            status = await asyncio.to_thread(
                _request, origin, "GET", connection_path, cookies=jar
            )
            assert status[0] == 200
            view = json.loads(status[2])
            assert view["state"] == "connected"
            assert view["can_connect"] is False
            headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                "Idempotency-Key": secrets.token_urlsafe(24),
                "If-Match": account_response[1]["ETag"],
            }
            refused = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                connection_path,
                body={"expected_email": "owner@example.invalid"},
                headers=headers,
                cookies=jar,
            )
            assert refused[0] == 409
            assert json.loads(refused[2])["code"] == "provider_connection_not_eligible"

    asyncio.run(exercise())

    account = SqliteRegistryRepositoryV1(reference).get_account(OpaqueIdV1(account_id))
    assert account is not None and not account.is_effective_monitoring_enabled
    assert tuple(target.iterdir()) == ()
    assert not (tmp_path / "connection-flows").exists()


def test_pending_connection_status_and_mutation_protections(tmp_path: Path) -> None:
    """Status is inert; malformed/stale/unauthorized starts cannot launch auth."""
    app, credential = _installation(tmp_path)
    identity = read_default_profile_identity_v1(discover_default_installation())
    assert identity is not None, "real owner identity required"

    async def exercise() -> None:
        async with _running(app) as origin:
            jar = http.cookiejar.CookieJar()
            assert (
                await asyncio.to_thread(
                    _request,
                    origin,
                    "POST",
                    "/api/v1/session",
                    body={"password": credential},
                    headers={"Origin": origin},
                    cookies=jar,
                )
            )[0] == 204
            headers = {
                "Origin": origin,
                "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
                "Idempotency-Key": secrets.token_urlsafe(24),
            }
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body={
                    "provider_key": "claude",
                    "friendly_name": "Owner account " + secrets.token_urlsafe(8),
                    "organization_id": None,
                },
                headers=headers,
                cookies=jar,
            )
            assert created[0] == 201
            account = json.loads(created[2])
            path = "/api/v1/accounts/" + account["account_id"] + "/connection"
            status = await asyncio.to_thread(_request, origin, "GET", path, cookies=jar)
            assert status[0] == 200, "pending connection status missing"
            view = json.loads(status[2])
            assert view["state"] == "idle" and view["can_connect"] is True
            assert view["flow_id"] is None
            body: dict[str, object] = {"expected_email": identity.email}
            valid_headers = {**headers, "If-Match": created[1]["ETag"]}
            anonymous = await asyncio.to_thread(
                _request, origin, "POST", path, body=body, headers=valid_headers
            )
            assert anonymous[0] == 401
            no_csrf = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path,
                body=body,
                headers={
                    key: value
                    for key, value in valid_headers.items()
                    if key != "X-CSRF-Token"
                },
                cookies=jar,
            )
            assert no_csrf[0] == 403
            no_version = await asyncio.to_thread(
                _request, origin, "POST", path, body=body, headers=headers, cookies=jar
            )
            assert no_version[0] == 428
            stale = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path,
                body=body,
                headers={**headers, "If-Match": '"' + account["account_id"] + '.2"'},
                cookies=jar,
            )
            assert stale[0] == 412
            no_key = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path,
                body=body,
                headers={
                    key: value
                    for key, value in valid_headers.items()
                    if key != "Idempotency-Key"
                },
                cookies=jar,
            )
            assert no_key[0] == 400
            hostile = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path,
                body=body,
                headers={**valid_headers, "Origin": "http://127.0.0.1:1"},
                cookies=jar,
            )
            assert hostile[0] == 403
            invalid = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path,
                body={"expected_email": ""},
                headers=valid_headers,
                cookies=jar,
            )
            assert invalid[0] == 422
            after = await asyncio.to_thread(_request, origin, "GET", path, cookies=jar)
            assert json.loads(after[2])["flow_id"] is None
            assert not (tmp_path / "profiles").exists()
            unchanged = await asyncio.to_thread(
                _request,
                origin,
                "GET",
                "/api/v1/accounts/" + account["account_id"],
                cookies=jar,
            )
            assert (
                json.loads(unchanged[2])["record_version"] == account["record_version"]
            )
            schema = json.loads(
                (
                    await asyncio.to_thread(
                        _request, origin, "GET", "/openapi.json", cookies=jar
                    )
                )[2]
            )
            for method in ("get", "post", "delete"):
                assert (
                    method
                    in schema["paths"]["/api/v1/accounts/{account_id}/connection"]
                )
            assert (
                schema["paths"]["/api/v1/accounts/{account_id}/connection"]["post"][
                    "x-agentmonitor-required-permission"
                ]
                == "write:reauth"
            )

    asyncio.run(exercise())


def test_unsafe_managed_root_receipt_survives_restart_without_auth(
    tmp_path: Path,
) -> None:
    """Real failed request remains replayable without starting a provider login."""
    from agentmonitor.composition.bootstrap import create_iam_application
    from agentmonitor.composition.claude_managed_connection import (
        managed_claude_root_v1,
    )
    from agentmonitor.contracts.common_v1 import OpaqueIdV1
    from agentmonitor.foundation.application import LifecycleHooksV1

    app, credential = _installation(tmp_path)
    installation = discover_default_installation()
    before = read_default_profile_identity_v1(installation)
    assert before is not None
    remembered: dict[str, object] = {}

    async def sign_in(origin: str) -> tuple[http.cookiejar.CookieJar, dict[str, str]]:
        jar = http.cookiejar.CookieJar()
        assert (
            await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/session",
                body={"password": credential},
                headers={"Origin": origin},
                cookies=jar,
            )
        )[0] == 204
        return jar, {
            "Origin": origin,
            "X-CSRF-Token": _session_cookies(jar)["agentmonitor_csrf"],
            "Idempotency-Key": secrets.token_urlsafe(24),
        }

    async def exercise() -> None:
        async with _running(app) as origin:
            jar, headers = await sign_in(origin)
            created = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                "/api/v1/accounts",
                body={
                    "provider_key": "claude",
                    "friendly_name": "Connection " + secrets.token_urlsafe(8),
                    "organization_id": None,
                },
                headers=headers,
                cookies=jar,
            )
            assert created[0] == 201
            account = json.loads(created[2])
            root = managed_claude_root_v1(tmp_path, OpaqueIdV1(account["account_id"]))
            root.parent.mkdir(mode=0o700, parents=True)
            root.parent.parent.chmod(0o700)
            target = tmp_path / "unsafe-owned-directory"
            target.mkdir(mode=0o700)
            root.symlink_to(target, target_is_directory=True)
            path = "/api/v1/accounts/" + account["account_id"] + "/connection"
            start_headers = {
                **headers,
                "Idempotency-Key": secrets.token_urlsafe(24),
                "If-Match": created[1]["ETag"],
            }
            body: dict[str, object] = {"expected_email": before.email}
            started = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path,
                body=body,
                headers=start_headers,
                cookies=jar,
            )
            assert started[0] == 202
            assert started[1]["Location"] == path
            flow_id = json.loads(started[2])["flow_id"]
            until = time.monotonic() + 8
            while True:
                status = await asyncio.to_thread(
                    _request, origin, "GET", path, cookies=jar
                )
                view = json.loads(status[2])
                if view["state"] == "failed":
                    break
                assert time.monotonic() < until, "unsafe root did not fail closed"
                await asyncio.sleep(0.05)
            assert view["reason_code"] == "connection_failed"
            replay = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                path,
                body=body,
                headers=start_headers,
                cookies=jar,
            )
            assert replay[0] == 202 and json.loads(replay[2])["flow_id"] == flow_id
            assert not tuple(target.iterdir()), "unsafe provider root was written"
            receipts = tuple((tmp_path / "connection-flows").glob("*.json"))
            assert len(receipts) == 1
            assert receipts[0].stat().st_mode & 0o777 == 0o600
            receipt = json.loads(receipts[0].read_text())
            assert receipt["state"] == "failed"
            assert before.email not in receipts[0].read_text()
            assert set(receipt) == {
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
            remembered.update(
                path=path,
                body=body,
                key=start_headers["Idempotency-Key"],
                etag=created[1]["ETag"],
                flow_id=flow_id,
            )
        config = next(tmp_path.glob("*.env"))
        restarted = create_iam_application(
            config, tmp_path, lifecycle=LifecycleHooksV1()
        )
        async with _running(restarted) as origin:
            jar, headers = await sign_in(origin)
            assert isinstance(remembered["path"], str)
            assert isinstance(remembered["body"], dict)
            headers.update(
                {
                    "Idempotency-Key": str(remembered["key"]),
                    "If-Match": str(remembered["etag"]),
                }
            )
            result = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                remembered["path"],
                body=remembered["body"],
                headers=headers,
                cookies=jar,
            )
            assert result[0] == 202
            assert json.loads(result[2])["flow_id"] == remembered["flow_id"]
            assert json.loads(result[2])["state"] == "failed"
            changed = await asyncio.to_thread(
                _request,
                origin,
                "POST",
                remembered["path"],
                body=remembered["body"],
                headers={
                    **headers,
                    "If-Match": '"' + json.loads(result[2])["account_id"] + '.2"',
                },
                cookies=jar,
            )
            assert (
                changed[0] == 409
                and json.loads(changed[2])["code"] == "idempotency_key_reused"
            )
            assert not tuple(target.iterdir())

    asyncio.run(exercise())
    after = read_default_profile_identity_v1(installation)
    assert after is not None and after.fingerprint == before.fingerprint
