"""Pure schema compatibility: optional queries cannot weaken existing contracts."""

from copy import deepcopy

import pytest

from tooling.foundation.openapi_client import classify_compatibility


def _document(parameters: list[dict[str, object]]) -> dict[str, object]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "AgentMonitor", "version": "0.0.0"},
        "paths": {
            "/api/v1/items": {
                "get": {
                    "operationId": "items",
                    "parameters": parameters,
                    "responses": {"200": {"description": "Success"}},
                }
            }
        },
    }


def test_optional_query_addition_preserves_old_requests() -> None:
    old = {
        "in": "query",
        "name": "limit",
        "schema": {"type": "integer"},
        "required": False,
    }
    addition = {
        "in": "query",
        "name": "sort",
        "schema": {"type": "string", "default": "state"},
        "required": False,
    }
    assert (
        classify_compatibility(_document([old]), _document([addition, old]))
        == "compatible"
    )


@pytest.mark.parametrize(
    "change", ("required", "header", "removed", "changed", "duplicate")
)
def test_optional_query_policy_rejects_incompatible_changes(change: str) -> None:
    old = {
        "in": "query",
        "name": "limit",
        "schema": {"type": "integer"},
        "required": False,
    }
    addition = {
        "in": "query",
        "name": "sort",
        "schema": {"type": "string"},
        "required": False,
    }
    values = [deepcopy(old), addition]
    if change == "required":
        addition["required"] = True
    elif change == "header":
        addition["in"] = "header"
    elif change == "removed":
        values = [addition]
    elif change == "changed":
        values[0]["schema"] = {"type": "string"}
    else:
        values.append(old)
    assert classify_compatibility(_document([old]), _document(values)) == "breaking"
