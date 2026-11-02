"""Immutable non-secret transport bounds shared by source admission metadata."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CloudBalancePolicyV1:
    scheme: Literal["https"]
    host: Literal["ollama.com"]
    port: Literal[443]
    method: Literal["GET"]
    path: Literal["/api/balance"]
    request_count: Literal[1]
    automatic_retry_count: Literal[0]
    follow_redirects: Literal[False]
    use_environment_proxy: Literal[False]
    connect_timeout_seconds: float
    read_timeout_seconds: float
    operation_timeout_seconds: float
    maximum_header_count: int
    maximum_header_bytes: int
    maximum_body_bytes: int
    authenticated_collection_admitted: Literal[False]
    operation_deadline_strict: Literal[False]
    dns_deadline_strict: Literal[False]
    wire_header_limit_strict: Literal[True]
    anonymous_probe_process_isolated: Literal[True]
    anonymous_probe_deadline_strict: Literal[True]
    binding_worker_process_isolated: Literal[True]
    binding_worker_deadline_strict: Literal[True]
    binding_worker_authenticated_validated: Literal[False]


CLOUD_BALANCE_POLICY_V1 = CloudBalancePolicyV1(
    scheme="https",
    host="ollama.com",
    port=443,
    method="GET",
    path="/api/balance",
    request_count=1,
    automatic_retry_count=0,
    follow_redirects=False,
    use_environment_proxy=False,
    connect_timeout_seconds=3.0,
    read_timeout_seconds=3.0,
    operation_timeout_seconds=8.0,
    maximum_header_count=64,
    maximum_header_bytes=16 * 1024,
    maximum_body_bytes=64 * 1024,
    authenticated_collection_admitted=False,
    operation_deadline_strict=False,
    dns_deadline_strict=False,
    wire_header_limit_strict=True,
    anonymous_probe_process_isolated=True,
    anonymous_probe_deadline_strict=True,
    binding_worker_process_isolated=True,
    binding_worker_deadline_strict=True,
    binding_worker_authenticated_validated=False,
)
