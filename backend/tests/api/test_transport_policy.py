"""Direct P01 pure policy checks, paired with live IAM HTTP regressions."""

import json

import pytest
from agentmonitor.api import problem, transport
from agentmonitor.api.problem import problem_response
from agentmonitor.api.v1.routers import iam
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def test_correlation_validator_accepts_exact_grammar_and_ends() -> None:
    for value in ("a", "a.b:c-d_e", "A" * 64):
        assert transport.valid_correlation_id(value)
    for value in (
        "",
        "A" * 65,
        "a b",
        " a",
        "a\t",
        "a\n",
        "a\x00",
        "é",
    ):
        assert not transport.valid_correlation_id(value)


def test_etag_codec_round_trips_strong_versions_and_rejects_weak_values() -> None:
    subject = OpaqueIdV1("opaque_subject")
    for version in (1, 19, 2**31):
        assert iam.decode_strong_etag(iam.encode_strong_etag(subject, version)) == (
            subject,
            version,
        )
    for malformed in (
        'W/"opaque_subject.1"',
        '"opaque_subject.0"',
        '"opaque_subject.-1"',
        '"opaque_subject.1", "opaque_subject.2"',
        '"opaque_subject.1',
        "opaque_subject.1",
        '"opaque_subject.01"',
    ):
        assert iam.decode_strong_etag(malformed) is None
    with pytest.raises(ValueError):
        iam.encode_strong_etag(subject, 0)


def test_unexpected_problem_mapper_never_serializes_exception_content() -> None:
    constructed = RuntimeError("token=" + "x" * 48)
    status, code = problem.map_unexpected_error(constructed)
    assert (status, code) == (500, "internal_error")
    payload = json.loads(bytes(problem_response(status, code, "a.b:c").body))
    assert payload == {
        "type": "/problems/internal_error",
        "title": "Internal service error",
        "status": 500,
        "detail": "Internal service error.",
        "code": "internal_error",
        "correlation_id": "a.b:c",
    }
