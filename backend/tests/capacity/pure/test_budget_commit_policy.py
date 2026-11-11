"""Pure envelope validation; no constructed report enters persistence."""

from dataclasses import replace
from typing import Any, cast

import pytest
from agentmonitor.contracts.capacity_v1 import BudgetCollectionInputV1
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.modules.capacity.application.budget_commit import (
    BudgetCommitError,
    budget_history_page_count,
    validate_budget_commit,
)
from agentmonitor.modules.capacity.domain.budget_codec import (
    budget_report_digest,
    decode_budget_provenance,
    encode_budget_provenance,
)

from backend.tests.capacity.pure.test_budget_codec import pure_report


def pure_request() -> BudgetCollectionInputV1:
    report = pure_report()
    unavailable = FieldAvailabilityV1("unknown")
    provenance = ObservationProvenanceV1(
        provider_key=report.subject.provider_key,
        capability_id="api.billing",
        capability_schema_version="2.0.0",
        adapter_id="pure.adapter",
        adapter_version="1.0.0",
        provider_protocol_version="1",
        source_id=report.source_id,
        source_class="documented_api",
        mechanism_version="1",
        parser_version="1",
        provider_version=None,
        provider_version_availability=unavailable,
        observed_at=None,
        observed_at_availability=unavailable,
        collected_at=report.collected_at,
        freshness_deadline=None,
        freshness_availability=unavailable,
        freshness_policy_id="source_defined",
        precision="exact",
        confidence="confirmed",
        confidence_reason_code="provider_reported",
        value_kind="provider_reported",
        is_experimental=False,
        fallback_lineage=(),
        warnings=(),
        operation_id=OpaqueIdV1("pure-operation"),
        correlation_id=OpaqueIdV1("pure-correlation"),
        decision_reference="M7-T005",
        derivation_method=None,
        input_observation_ids=(),
    )
    return BudgetCollectionInputV1(
        OpaqueIdV1("pure-run"),
        1,
        "api.billing",
        "budget.report.v1",
        budget_report_digest(report),
        "succeeded",
        report,
        provenance,
    )


def test_valid_complete_and_partial_envelopes() -> None:
    request = pure_request()
    assert validate_budget_commit(request)
    report = replace(
        request.payload, completeness="partial", omission_codes=("source_partial",)
    )
    assert validate_budget_commit(
        replace(
            request,
            payload=report,  # type: ignore[arg-type]  # Generic dataclass replace typing.
            payload_digest=budget_report_digest(report),
            terminal_state="partial",
        )
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider_key", "codex"),
        ("capability_id", "other"),
        ("source_id", "other"),
        ("capability_schema_version", "99.0.0"),
    ],
)
def test_provenance_must_match_report_and_envelope(field: str, value: str) -> None:
    request = pure_request()
    with pytest.raises(BudgetCommitError, match="budget_provenance_mismatch"):
        validate_budget_commit(
            replace(
                request,
                provenance=replace(
                    request.provenance, **cast(dict[str, Any], {field: value})
                ),
            )
        )


def test_changed_digest_or_terminal_state_cannot_commit() -> None:
    request = pure_request()
    with pytest.raises(BudgetCommitError, match="budget_digest_mismatch"):
        validate_budget_commit(replace(request, payload_digest="0" * 64))
    with pytest.raises(BudgetCommitError, match="budget_terminal_state_mismatch"):
        validate_budget_commit(replace(request, terminal_state="partial"))
    with pytest.raises(BudgetCommitError, match="budget_payload_schema_invalid"):
        validate_budget_commit(replace(request, payload_schema="unknown"))


def test_full_coverage_and_matching_collection_time_required() -> None:
    request = pure_request()
    report = replace(request.payload, covered_period=None)
    with pytest.raises(BudgetCommitError, match="budget_terminal_state_mismatch"):
        validate_budget_commit(
            replace(
                request,
                payload=report,  # type: ignore[arg-type]  # Generic dataclass replace typing.
                payload_digest=budget_report_digest(report),
            )
        )
    with pytest.raises(BudgetCommitError, match="budget_provenance_mismatch"):
        validate_budget_commit(
            replace(
                request,
                provenance=replace(
                    request.provenance,
                    collected_at=request.payload.requested_period.start,
                ),
            )
        )


def test_provenance_codec_preserves_complete_typed_lineage() -> None:
    from agentmonitor.contracts.common_provenance_v1 import FallbackAttemptV1

    provenance = replace(
        pure_request().provenance,
        warnings=("source_delayed",),
        fallback_lineage=(FallbackAttemptV1("prior-source", "source_unavailable"),),
    )
    encoded = encode_budget_provenance(provenance)
    assert decode_budget_provenance(encoded) == provenance
    assert "source_delayed" in encoded


@pytest.mark.parametrize(
    "sizes,limit,expected",
    [
        ((10, 20, 30), 2, 2),
        ((8 * 1024 * 1024, 8 * 1024 * 1024, 2), 200, 2),
        ((16 * 1024 * 1024, 2), 200, 1),
        ((), 50, 0),
    ],
)
def test_history_page_bounds_both_bytes_and_count(
    sizes: tuple[int, ...], limit: int, expected: int
) -> None:
    assert budget_history_page_count(sizes, limit) == expected
