"""Pure policy checks for the fixed Ollama cloud balance source."""

from inspect import signature

from agentmonitor.adapters.providers.ollama.cloud_balance.source import (
    CLOUD_BALANCE_POLICY_V1,
    CloudBalanceAuthorizationSinkV1,
    CloudBalanceAuthorizationV1,
    probe_cloud_balance_for_binding_v1,
    read_cloud_balance_for_binding_v1,
    read_cloud_balance_once_v1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1


class _MustNotApplyAuthorization:
    def apply_authorization_v1(self, sink: CloudBalanceAuthorizationSinkV1) -> None:
        raise AssertionError("unadmitted_authorization_was_applied")


def test_cloud_balance_source_is_one_fixed_bounded_request() -> None:
    """M6-A09/OLL-SEC-012: callers cannot choose the network destination."""
    policy = CLOUD_BALANCE_POLICY_V1

    assert policy.scheme == "https"
    assert policy.host == "ollama.com"
    assert policy.port == 443
    assert policy.method == "GET"
    assert policy.path == "/api/balance"
    assert policy.request_count == 1
    assert policy.automatic_retry_count == 0
    assert not policy.follow_redirects
    assert not policy.use_environment_proxy
    assert policy.connect_timeout_seconds < policy.operation_timeout_seconds
    assert policy.read_timeout_seconds < policy.operation_timeout_seconds
    assert 0 < policy.maximum_header_count <= 100
    assert 0 < policy.maximum_header_bytes <= 64 * 1024
    assert 0 < policy.maximum_body_bytes <= 256 * 1024
    assert not policy.authenticated_collection_admitted
    assert not policy.operation_deadline_strict
    assert not policy.dns_deadline_strict
    assert not policy.wire_header_limit_strict
    assert policy.anonymous_probe_process_isolated
    assert policy.anonymous_probe_deadline_strict
    assert policy.binding_worker_process_isolated
    assert policy.binding_worker_deadline_strict
    assert not policy.binding_worker_authenticated_validated
    assert tuple(signature(read_cloud_balance_once_v1).parameters) == (
        "authorization",
        "deadline_monotonic",
    )
    assert tuple(
        signature(CloudBalanceAuthorizationV1.apply_authorization_v1).parameters
    ) == ("self", "sink")
    assert tuple(signature(read_cloud_balance_for_binding_v1).parameters) == (
        "binding",
        "deadline_monotonic",
    )
    assert tuple(signature(probe_cloud_balance_for_binding_v1).parameters) == (
        "binding",
        "deadline_monotonic",
    )
    assert {
        name
        for name in CloudBalanceAuthorizationSinkV1.__dict__
        if not name.startswith("_")
    } == {"put_bearer_token_v1"}


def test_authenticated_source_fails_closed_before_authorization_or_network() -> None:
    result = read_cloud_balance_once_v1(
        authorization=_MustNotApplyAuthorization(),
        deadline_monotonic=0.0,
    )

    assert result.state == "source_not_admitted"
    assert result.reason_code == "ollama_cloud_authenticated_source_not_admitted"
    assert result.http_status is None
    assert result.balance is None


def test_binding_source_fails_closed_before_admission_probe_or_network() -> None:
    result = read_cloud_balance_for_binding_v1(
        binding=ActiveCredentialBindingRefV1(
            account_id=OpaqueIdV1("account-policy-check"),
            binding_id=OpaqueIdV1("amcb_" + "a" * 32),
            generation=1,
        ),
        deadline_monotonic=0.0,
    )

    assert result.state == "source_not_admitted"
    assert result.reason_code == "ollama_cloud_authenticated_source_not_admitted"
    assert result.http_status is None
    assert result.balance is None
