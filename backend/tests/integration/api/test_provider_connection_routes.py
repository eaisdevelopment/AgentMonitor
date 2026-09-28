"""Dashboard connection safeguards over real HTTP, SQLite, and native identity."""

import asyncio
import http.cookiejar
import json
import secrets
import time
from pathlib import Path

from agentmonitor.adapters.providers.claude.authentication.identity import (
    read_default_profile_identity_v1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_default_installation,
)

from backend.tests.integration.api.test_iam_http import (
    _installation,
    _request,
    _running,
    _session_cookies,
)


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
