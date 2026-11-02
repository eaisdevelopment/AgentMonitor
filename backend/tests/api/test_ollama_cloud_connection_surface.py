"""Inspect the real generated application route without starting providers."""

from agentmonitor.composition.bootstrap import create_iam_schema_application


def test_signed_in_ollama_cloud_connection_surface_is_declared() -> None:
    paths = create_iam_schema_application().openapi()["paths"]
    path = paths["/api/v1/accounts/{account_id}/ollama-cloud-connection"]
    assert {"get", "post"} <= set(path)
    post = path["post"]
    assert post["x-agentmonitor-auth-profile"] == "browser_cookie_only"
    assert post["x-agentmonitor-required-permission"] == "write:reauth"
    assert "requestBody" not in post
    assert {item["name"] for item in post["parameters"]} >= {
        "account_id",
        "If-Match",
        "Idempotency-Key",
    }
