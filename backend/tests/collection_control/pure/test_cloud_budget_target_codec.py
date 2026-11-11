"""Pure M04 cloud authority encoding; constructed DTOs never enter storage."""

import json
from dataclasses import replace
from datetime import timedelta
from typing import Any, Literal, cast

import pytest
from agentmonitor.adapters.persistence.collection_control.sqlite import budget
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetReportContextV1,
)
from agentmonitor.contracts.registry_v1 import (
    CloudMonitoringTargetV1,
    ProviderAccessTargetV1,
)

from backend.tests.contracts.test_cloud_budget_run_contract import _admission

Authority = tuple[
    CloudMonitoringTargetV1, ProviderAccessTargetV1, CloudBudgetReportContextV1
]


def _authority() -> Authority:
    run = _admission()
    return run.cloud_target, run.service_target, run.report_context


def _encode(authority: Authority) -> str:
    encode = getattr(budget, "encode_cloud_budget_target", None)
    assert callable(encode), "M04 cloud budget authority encoder is absent"
    return cast(str, encode(*authority))


def _decode(text: str) -> Authority:
    decode = getattr(budget, "decode_cloud_budget_target", None)
    assert callable(decode), "M04 cloud budget authority decoder is absent"
    return cast(Authority, decode(text))


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


@pytest.mark.parametrize("scope,days", [("self", 7), ("team", 30)])
def test_cloud_authority_round_trip_preserves_graph_service_and_pinned_context(
    scope: Literal["self", "team"],
    days: int,
) -> None:
    graph, service, context = _authority()
    context = replace(
        context,
        scope=scope,
        range_key="7d" if days == 7 else "30d",
        interval_start=context.interval_end - timedelta(days=days),
    )
    authority = graph, service, context
    encoded = _encode(authority)
    assert encoded.isascii() and len(encoded) <= 8192
    assert _decode(encoded) == authority
    assert _encode(_decode(encoded)) == encoded
    payload = json.loads(encoded)
    assert set(payload) == {"tag", "cloud_target", "service_target", "report_context"}
    assert payload["tag"] == "cloud_budget_target.v1"
    assert payload["service_target"]["manifest_fingerprint"] == "b" * 64
    assert payload["cloud_target"]["binding"]["generation"] == 4
    assert payload["cloud_target"]["record_version"] == 7
    assert payload["report_context"]["interval_end"] == "2026-11-11T00:00:00.000000Z"
    assert "billing_target" not in payload


@pytest.mark.parametrize(
    "section", [None, "cloud_target", "service_target", "report_context", "binding"]
)
@pytest.mark.parametrize("change", ["extra", "missing"])
def test_closed_keys_at_every_nested_level(section: str | None, change: str) -> None:
    payload = json.loads(_encode(_authority()))
    selected = (
        payload
        if section is None
        else (
            payload["cloud_target"]["binding"]
            if section == "binding"
            else payload[section]
        )
    )
    if change == "extra":
        selected["unexpected"] = "value"
    else:
        del selected[next(iter(selected))]
    with pytest.raises(
        budget.BudgetCollectionError, match="^budget_target_encoding_invalid$"
    ):
        _decode(_json(payload))


@pytest.mark.parametrize(
    "section,key,value",
    [
        (None, "tag", "cloud_budget_target.v2"),
        ("service_target", "manifest_fingerprint", "b" * 63),
        ("service_target", "manifest_fingerprint", "B" * 64),
        ("service_target", "provider_key", "claude"),
        ("service_target", "authority_id", "another.example"),
        ("service_target", "access_target_id", "amat_" + "d" * 32),
        ("service_target", "lifecycle", "disabled"),
        ("cloud_target", "lifecycle", "archived"),
        ("cloud_target", "identity_state", "inferred"),
        ("cloud_target", "account_id", "other-account"),
        ("cloud_target", "owner_asserted_at", "2026-11-10T00:00:00Z"),
        ("report_context", "range_key", "30d"),
        ("report_context", "range_key", "14d"),
        ("report_context", "scope", "organization"),
        ("report_context", "interval_end", "2026-11-12T00:00:00.000000Z"),
        ("report_context", "interval_start", "2026-11-04T00:00:00.000000+00:00"),
        ("report_context", "interval_start", "2026-11-04T00:00:00.000000"),
        ("binding", "generation", True),
    ],
)
def test_invalid_or_inconsistent_authority_is_rejected(
    section: str | None,
    key: str,
    value: Any,
) -> None:
    payload = json.loads(_encode(_authority()))
    selected = (
        payload
        if section is None
        else (
            payload["cloud_target"]["binding"]
            if section == "binding"
            else payload[section]
        )
    )
    selected[key] = value
    with pytest.raises(
        budget.BudgetCollectionError, match="^budget_target_encoding_invalid$"
    ):
        _decode(_json(payload))


@pytest.mark.parametrize(
    "field", ["tag", "manifest_fingerprint", "generation", "scope"]
)
def test_duplicate_keys_at_any_depth_are_rejected(field: str) -> None:
    text = _encode(_authority())
    key = _json(field) + ":"
    replacement = key + ("4," if field == "generation" else '"duplicate",') + key
    with pytest.raises(budget.BudgetCollectionError):
        _decode(text.replace(key, replacement, 1))


@pytest.mark.parametrize("transform", ["space", "unicode", "oversize", "float", "nan"])
def test_noncanonical_or_unbounded_wire_is_rejected(transform: str) -> None:
    text = _encode(_authority())
    if transform == "space":
        text = " " + text
    elif transform == "unicode":
        text = text.replace("pure-owner", "pure-öwner")
    elif transform == "oversize":
        text = text.replace("pure-owner", "x" * 8193)
    else:
        text = text.replace(
            '"generation":4',
            '"generation":' + ("4.0" if transform == "float" else "NaN"),
        )
    with pytest.raises(budget.BudgetCollectionError):
        _decode(text)


def test_encoder_rejects_cross_service_graph_and_oversized_metadata() -> None:
    graph, service, context = _authority()
    with pytest.raises(budget.BudgetCollectionError):
        _encode((graph, replace(service, provider_key="codex"), context))
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    with pytest.raises(budget.BudgetCollectionError):
        _encode(
            (
                replace(graph, owner_principal_id=OpaqueIdV1("x" * 8193)),
                service,
                context,
            )
        )


def test_cloud_tag_does_not_change_or_cross_decode_legacy_billing_wire() -> None:
    from backend.tests.contracts.test_budget_run_contract import _admission as billing

    target = billing().billing_target
    text = budget.encode_billing_target(target)
    assert "tag" not in json.loads(text)
    assert budget.decode_billing_target(text) == target
    with pytest.raises(budget.BudgetCollectionError):
        _decode(text)
    with pytest.raises(budget.BudgetCollectionError):
        budget.decode_billing_target(_encode(_authority()))
