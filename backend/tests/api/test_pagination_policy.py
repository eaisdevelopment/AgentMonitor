"""Side-effect-free P01 policy checks paired with live IAM list HTTP tests."""

import secrets

import pytest
from agentmonitor.api.problem import ProblemError, SafeProblemV1
from agentmonitor.api.v1.pagination import CursorCodecV1, parse_list_query_values
from agentmonitor.api.v1.schemas.iam import PageMetaV1


def test_iam_sort_parser_appends_the_approved_id_tie_breaker() -> None:
    for primary, keyset_id in (
        ("-issued_at", "session_id"),
        ("-issued_at", "api_token_id"),
        ("-occurred_at", "event_id"),
    ):
        omitted = parse_list_query_values((), sort=primary, id_field=keyset_id)
        explicit = parse_list_query_values(
            (("sort", primary),), sort=primary, id_field=keyset_id
        )
        assert omitted.order == (primary, "-" + keyset_id)
        assert explicit.order == omitted.order
        with pytest.raises(ProblemError) as rejected:
            parse_list_query_values(
                (("sort", "name"),), sort=primary, id_field=keyset_id
            )
        assert rejected.value.status == 400
        assert rejected.value.code == "invalid_sort"


def test_iam_query_parser_rejects_unknown_and_repeated_keys() -> None:
    for pairs in (
        (("state", "active"),),
        (("limit", "1"), ("limit", "2")),
        (("sort", "-issued_at"), ("sort", "-issued_at")),
    ):
        with pytest.raises(ProblemError) as rejected:
            parse_list_query_values(pairs, sort="-issued_at", id_field="session_id")
        assert rejected.value.status == 400
        assert rejected.value.code == "invalid_filter"


def test_cursor_codec_rejects_tamper_and_different_query_binding() -> None:
    codec = CursorCodecV1(secrets.token_bytes(32))
    issued = codec.encode("opaque_id", b"query-and-credential-a")
    assert codec.decode(issued, b"query-and-credential-a") == "opaque_id"
    with pytest.raises(ProblemError) as mismatch:
        codec.decode(issued, b"query-and-credential-b")
    assert mismatch.value.code == "cursor_query_mismatch"
    position = len(issued) // 2
    altered = (
        issued[:position]
        + ("A" if issued[position] != "A" else "B")
        + issued[position + 1 :]
    )
    with pytest.raises(ProblemError) as invalid:
        codec.decode(altered, b"query-and-credential-a")
    assert invalid.value.code == "invalid_cursor"


def test_problem_and_page_schema_distinguish_optional_from_nullable() -> None:
    problem = SafeProblemV1.model_json_schema()
    page = PageMetaV1.model_json_schema()
    assert "detail" in problem["properties"]
    assert "detail" not in problem["required"]
    assert problem["properties"]["detail"]["type"] == "string"
    assert "errors" not in problem["required"]
    assert "next_cursor" in page["required"]
    assert {part["type"] for part in page["properties"]["next_cursor"]["anyOf"]} == {
        "string",
        "null",
    }
