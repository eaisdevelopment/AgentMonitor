"""Pure security-policy checks for the bounded Codex app-server adapter."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.providers.codex.adapter import (
    CodexAdapterV1,
    classify_codex_app_server_failure_v1,
)
from agentmonitor.adapters.providers.codex.authentication.reauthentication import (
    CodexManagedAuthenticationTargetV1,
    begin_managed_profile_authentication_v1,
)
from agentmonitor.adapters.providers.codex.installation import (
    CodexInstallationUnavailable,
    discover_default_installation,
)
from agentmonitor.adapters.providers.codex.transport import (
    CodexAppServerFailure,
    _decode_codex_response_line_v1,
    _JsonLineFramerV1,
    _request_parameters_v1,
    _validate_initialize_result_v1,
    invoke_codex_app_server_v1,
    validate_codex_managed_profile_root_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def _private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def _adapter(tmp_path: Path) -> CodexAdapterV1:
    profiles = _private_directory(tmp_path / "profiles")
    profile = _private_directory(profiles / "profile-one")
    return CodexAdapterV1(
        discover_default_installation(),
        managed_profiles_root=profiles,
        managed_profile_root=profile,
        expected_identity_fingerprint="a" * 64,
        installation_ref=OpaqueIdV1("installation-one"),
        account_ref=OpaqueIdV1("account-one"),
        profile_ref=OpaqueIdV1("profile-one"),
        resource_ref=OpaqueIdV1("resource-one"),
        access_grant_ref=OpaqueIdV1("grant-one"),
    )


def test_request_target_and_grant_are_bound_before_provider_io(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    request = adapter.subscription_request(
        operation_id="operation-one",
        correlation_id="correlation-one",
        requested_at=datetime.now(UTC),
    )
    mutations = (
        replace(
            request,
            target=replace(
                request.target,
                installation_ref=OpaqueIdV1("installation-two"),
            ),
        ),
        replace(
            request,
            target=replace(request.target, account_ref=OpaqueIdV1("account-two")),
        ),
        replace(
            request,
            target=replace(request.target, profile_ref=OpaqueIdV1("profile-two")),
        ),
        replace(
            request,
            target=replace(request.target, resource_ref=OpaqueIdV1("resource-two")),
        ),
        replace(
            request,
            target=replace(request.target, profile_protection="protected_default"),
        ),
        replace(
            request,
            access_grant_refs=(OpaqueIdV1("grant-two"),),
        ),
        replace(
            request,
            source_policy=replace(
                request.source_policy,
                policy_ref=OpaqueIdV1("other-policy"),
            ),
        ),
    )

    for mutation in mutations:
        outcome = adapter.collect_subscription_quota(mutation)
        assert outcome.state == "invalid_provider_data"
        assert outcome.error is not None
        assert outcome.error.code == "codex_request_binding_mismatch"
        assert outcome.error.retry.disposition == "never"


def test_transport_failure_mapping_has_valid_retry_and_distinct_categories() -> None:
    expected = {
        "codex_app_server_deadline_exceeded": ("deadline_exceeded", "never", None),
        "codex_app_server_protocol_invalid": (
            "invalid_provider_data",
            "after_version_review",
            None,
        ),
        "codex_app_server_notification_rejected": (
            "invalid_provider_data",
            "after_version_review",
            None,
        ),
        "codex_app_server_unavailable": (
            "provider_unavailable",
            "after_delay",
            300,
        ),
        "codex_executable_changed": (
            "unverified_provider_version",
            "after_version_review",
            None,
        ),
        "codex_managed_profile_unsafe": (
            "invalid_provider_data",
            "never",
            None,
        ),
    }

    for code, wanted in expected.items():
        state, retry = classify_codex_app_server_failure_v1(code)
        assert (state, retry.disposition, retry.delay_seconds) == wanted
        if retry.disposition == "after_delay":
            assert retry.delay_precision == "estimated"


def test_expired_absolute_deadline_is_classified_as_deadline_exceeded(
    tmp_path: Path,
) -> None:
    profiles = _private_directory(tmp_path / "profiles")
    profile = _private_directory(profiles / "profile-one")
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_app_server_deadline_exceeded$",
    ):
        invoke_codex_app_server_v1(
            discover_default_installation(),
            managed_profiles_root=profiles,
            managed_profile_root=profile,
            method="account/read",
            deadline_monotonic=time.monotonic() - 1.0,
            parse_result=lambda _payload: None,
        )


def test_non_numeric_deadline_fails_sanitized_before_filesystem_or_process_io(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_app_server_request_invalid$",
    ):
        invoke_codex_app_server_v1(
            discover_default_installation(),
            managed_profiles_root=tmp_path / "missing-profiles",
            managed_profile_root=tmp_path / "missing-profiles" / "profile",
            method="account/read",
            deadline_monotonic="not-a-deadline",  # type: ignore[arg-type]
            parse_result=lambda _payload: None,
        )


def test_hard_linked_auth_store_is_rejected_before_app_server_or_login(
    tmp_path: Path,
) -> None:
    """M5-CDX-SOURCE-010/CONNECT-010: a private hard link is never usable."""
    profiles = _private_directory(tmp_path / "profiles")
    profile = _private_directory(profiles / "profile-one")
    outside = tmp_path / "outside-auth.json"
    outside.write_bytes(b"{}")
    outside.chmod(0o600)
    auth_store = profile / "auth.json"
    auth_store.hardlink_to(outside)
    root_mtime_before = profile.stat().st_mtime_ns

    metadata = auth_store.lstat()
    assert metadata.st_uid == os.getuid()
    assert metadata.st_mode & 0o777 == 0o600
    assert metadata.st_nlink == 2

    installation = discover_default_installation()
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_managed_profile_unsafe$",
    ):
        invoke_codex_app_server_v1(
            installation,
            managed_profiles_root=profiles,
            managed_profile_root=profile,
            method="account/read",
            deadline_monotonic=time.monotonic() + 10.0,
            parse_result=lambda _payload: None,
        )

    with pytest.raises(ValueError, match="^codex_managed_profile_unsafe$"):
        begin_managed_profile_authentication_v1(
            installation,
            CodexManagedAuthenticationTargetV1(
                profile_ref=OpaqueIdV1("profile-one"),
                profile_protection="managed",
                expected_identity_available=True,
                owner_interaction_granted=True,
                existing_verified_identity=False,
            ),
            managed_profiles_root=profiles,
            managed_profile_root=profile,
            expected_email="owner@example.invalid",
        )

    assert tuple(profile.iterdir()) == (auth_store,)
    assert profile.stat().st_mtime_ns == root_mtime_before
    assert outside.lstat().st_nlink == 2
    assert outside.read_bytes() == b"{}"


def test_app_server_postcheck_rejects_auth_store_hard_linked_during_use(
    tmp_path: Path,
) -> None:
    """M5-CDX-SOURCE-010: post-use metadata rejects a concurrent hard link."""
    profiles = _private_directory(tmp_path / "profiles")
    profile = _private_directory(profiles / "profile-one")
    auth_store = profile / "auth.json"
    auth_store.write_bytes(b"{}")
    auth_store.chmod(0o600)
    outside = tmp_path / "outside-auth.json"
    linked = threading.Event()

    def link_after_provider_start() -> None:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if any(path != auth_store for path in profile.rglob("*")):
                outside.hardlink_to(auth_store)
                linked.set()
                return
            time.sleep(0.001)

    linker = threading.Thread(target=link_after_provider_start, daemon=True)
    linker.start()
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_managed_profile_unsafe$",
    ):
        invoke_codex_app_server_v1(
            discover_default_installation(),
            managed_profiles_root=profiles,
            managed_profile_root=profile,
            method="account/read",
            deadline_monotonic=time.monotonic() + 10.0,
            parse_result=lambda _payload: None,
        )
    linker.join(timeout=5.0)

    assert linked.is_set()
    assert outside.samefile(auth_store)
    assert auth_store.lstat().st_nlink == 2


def test_response_decoder_rejects_ids_notifications_and_extra_envelope() -> None:
    invalid = (
        b'{"id":true,"result":{}}',
        b'{"id":"2","result":{}}',
        b'{"method":"thread/started","params":{"content":"forbidden"}}',
        b'{"id":2,"result":{},"method":"content/output"}',
    )

    for raw in invalid:
        with pytest.raises(CodexAppServerFailure):
            _decode_codex_response_line_v1(raw, request_id=2)


def test_method_parameters_are_closed_and_exactly_typed() -> None:
    identity = _request_parameters_v1("account/read")
    quota = _request_parameters_v1("account/rateLimits/read")

    assert identity == {"refreshToken": False}
    assert type(identity["refreshToken"]) is bool
    assert quota == {
        "excludeResetCreditDetails": True,
        "supportsLunaReserve": False,
    }
    assert all(type(value) is bool for value in quota.values())


def test_response_decoder_bounds_json_depth_and_suppresses_parse_context() -> None:
    too_deep = b'{"id":2,"result":' + b"[" * 40 + b"]" * 40 + b"}"
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_app_server_json_depth_exceeded$",
    ):
        _decode_codex_response_line_v1(too_deep, request_id=2)

    with pytest.raises(CodexAppServerFailure) as caught:
        _decode_codex_response_line_v1(b'{"id":2,"result":', request_id=2)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


@pytest.mark.parametrize(
    "raw",
    (
        b'{"id":2,"result":{"value":1,"value":2}}',
        b'{"id":2,"result":{"value":NaN}}',
        b'{"id":2,"result":{"value":Infinity}}',
        b'{"id":2,"result":{"value":1.5}}',
    ),
)
def test_response_decoder_rejects_ambiguous_or_nonstandard_json(raw: bytes) -> None:
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_app_server_protocol_invalid$",
    ):
        _decode_codex_response_line_v1(raw, request_id=2)


def test_line_framer_enforces_line_aggregate_and_message_bounds() -> None:
    line_limit = _JsonLineFramerV1.MAX_LINE_BYTES
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_app_server_output_too_large$",
    ):
        _JsonLineFramerV1().append(b"x" * (line_limit + 1) + b"\n")

    aggregate = _JsonLineFramerV1()
    for _ in range(4):
        aggregate.append(b"x" * (aggregate.MAX_LINE_BYTES - 1) + b"\n")
        assert aggregate.next_line() is not None
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_app_server_output_too_large$",
    ):
        aggregate.append(b"x" * (aggregate.MAX_LINE_BYTES - 1) + b"\n")

    messages = _JsonLineFramerV1()
    messages.append(b"{}\n" * (messages.MAX_MESSAGES + 1))
    for _ in range(messages.MAX_MESSAGES):
        assert messages.next_line() == b"{}"
    with pytest.raises(
        CodexAppServerFailure,
        match="^codex_app_server_message_limit_exceeded$",
    ):
        messages.next_line()


def test_initialize_response_is_bound_to_managed_root_and_exact_platform(
    tmp_path: Path,
) -> None:
    root = _private_directory(tmp_path / "managed")
    valid: dict[str, object] = {
        "userAgent": "agentmonitor/0.160.0 (Linux; x86_64)",
        "codexHome": str(root),
        "platformFamily": "unix",
        "platformOs": "linux",
    }
    _validate_initialize_result_v1(
        valid,
        expected_root=root,
        provider_version="0.160.0",
    )

    for mutation in (
        {**valid, "codexHome": str(tmp_path)},
        {**valid, "platformOs": "windows"},
        {**valid, "unexpected": "content"},
    ):
        with pytest.raises(
            CodexAppServerFailure,
            match="^codex_app_server_initialize_invalid$",
        ):
            _validate_initialize_result_v1(
                mutation,
                expected_root=root,
                provider_version="0.160.0",
            )


def test_managed_profile_must_be_a_private_descendant_without_symlink_components(
    tmp_path: Path,
) -> None:
    profiles = _private_directory(tmp_path / "profiles")
    profile = _private_directory(profiles / "account-one")
    assert (
        validate_codex_managed_profile_root_v1(
            managed_profiles_root=profiles,
            managed_profile_root=profile,
        )
        == profile
    )

    sibling = _private_directory(tmp_path / "sibling")
    with pytest.raises(CodexAppServerFailure, match="codex_managed_profile_unsafe"):
        validate_codex_managed_profile_root_v1(
            managed_profiles_root=profiles,
            managed_profile_root=sibling,
        )

    target = _private_directory(profiles / "target")
    linked_parent = profiles / "linked-parent"
    linked_parent.symlink_to(target, target_is_directory=True)
    linked_child = linked_parent / "child"
    with pytest.raises(CodexAppServerFailure, match="codex_managed_profile_unsafe"):
        validate_codex_managed_profile_root_v1(
            managed_profiles_root=profiles,
            managed_profile_root=linked_child,
        )

    profile.chmod(0o750)
    with pytest.raises(CodexAppServerFailure, match="codex_managed_profile_unsafe"):
        validate_codex_managed_profile_root_v1(
            managed_profiles_root=profiles,
            managed_profile_root=profile,
        )


def test_managed_profile_rejects_resolved_configured_default_alias(
    tmp_path: Path,
) -> None:
    """A configured default symlink cannot alias an AgentMonitor managed root."""

    profiles = _private_directory(tmp_path / "profiles")
    profile = _private_directory(profiles / "profile-one")
    configured_default = tmp_path / "configured-default"
    configured_default.symlink_to(profile, target_is_directory=True)
    previous = os.environ.get("CODEX_HOME")
    os.environ["CODEX_HOME"] = str(configured_default)
    try:
        with pytest.raises(
            CodexAppServerFailure,
            match="^codex_managed_profile_unsafe$",
        ):
            validate_codex_managed_profile_root_v1(
                managed_profiles_root=profiles,
                managed_profile_root=profile,
            )
    finally:
        if previous is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = previous


def test_retained_executable_identity_is_revalidated_at_launch() -> None:
    installation = discover_default_installation()
    assert installation.executable_for_launch() == installation.executable_for_adapter

    changed = replace(installation, _identity=(0, 0, 0, 0, 0, 0, 0, 0))
    with pytest.raises(
        CodexInstallationUnavailable,
        match="^codex_executable_changed$",
    ):
        changed.executable_for_launch()


def test_allowed_result_envelope_remains_method_private() -> None:
    raw = json.dumps({"id": 2, "result": {"requiresOpenaiAuth": True}}).encode()
    assert _decode_codex_response_line_v1(raw, request_id=2) == {
        "requiresOpenaiAuth": True
    }
