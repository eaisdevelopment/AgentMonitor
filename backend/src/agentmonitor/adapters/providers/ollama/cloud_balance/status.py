"""Sanitized classification of Ollama balance HTTP outcomes; no I/O."""

from typing import Literal

CloudStatus = Literal[
    "success",
    "unauthorized",
    "access_denied",
    "rate_limited",
    "provider_unavailable",
    "unexpected_response",
]


def classify_status(status: int) -> CloudStatus:
    """Map only documented status codes without leaking response data."""
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError("ollama_cloud_http_status_invalid")
    outcomes: dict[int, CloudStatus] = {
        200: "success",
        401: "unauthorized",
        403: "access_denied",
        429: "rate_limited",
        503: "provider_unavailable",
    }
    return outcomes.get(status, "unexpected_response")
