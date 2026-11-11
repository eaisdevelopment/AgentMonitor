"""Current-selection policy uses constructed reports only inside pure functions."""

from dataclasses import replace
from datetime import timedelta

import pytest
from agentmonitor.adapters.persistence.capacity.sqlite.budget_current_query import (
    bounded_current_report_ids,
    validate_current_report_load,
)
from agentmonitor.contracts.capacity_v1 import (
    BudgetCurrentQueryV1,
    BudgetPeriodV1,
    BudgetReportSelectionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ActiveCredentialBindingRefV1
from agentmonitor.modules.capacity.domain.budget_codec import (
    encode_budget_report,
    utc_text,
)
from agentmonitor.modules.capacity.domain.budget_reports import select_current_report

from backend.tests.capacity.pure.test_budget_report_selection import _report


def test_domain_selection_is_the_published_read_contract() -> None:
    assert isinstance(select_current_report(()), BudgetReportSelectionV1)


@pytest.mark.parametrize("authority", ["missing", "other_binding", "other_generation"])
def test_unresolved_current_load_requires_exact_active_lineage(authority: str) -> None:
    view = _report(1, "8")
    binding = ActiveCredentialBindingRefV1(
        view.report.subject.account_id, OpaqueIdV1("amcb_" + "a" * 32), 2
    )
    view = replace(
        view,
        report=replace(
            view.report,
            scope_id=None,
            scope_evidence="unresolved",
            binding_id=binding.binding_id,
            binding_generation=binding.generation,
        ),
    )
    query = BudgetCurrentQueryV1(
        view.report.subject.account_id,
        view.report.subject.resource_id,
        view.report.scope_generation,
        view.report.requested_period,
        view.stored_at,
        active_binding=binding,
    )
    text = encode_budget_report(view.report)
    validate_current_report_load(
        query,
        view,
        selected_id=view.report_id,
        selected_bytes=len(text.encode("utf-8")),
        canonical_text=text,
        collected_at=utc_text(view.report.collected_at),
    )
    if authority == "missing":
        query = replace(query, active_binding=None)
    elif authority == "other_binding":
        query = replace(
            query,
            active_binding=replace(binding, binding_id=OpaqueIdV1("amcb_" + "b" * 32)),
        )
    else:
        query = replace(query, active_binding=replace(binding, generation=3))
    with pytest.raises(ValueError, match="budget_current_metadata_invalid"):
        validate_current_report_load(
            query,
            view,
            selected_id=view.report_id,
            selected_bytes=len(text.encode("utf-8")),
            canonical_text=text,
            collected_at=utc_text(view.report.collected_at),
        )
    # The immutable report stays available to the separate explicit-history path.
    assert select_current_report((view,)).current == view


@pytest.mark.parametrize("active", [False, True])
def test_resolved_current_scope_does_not_depend_on_the_reading_key(
    active: bool,
) -> None:
    view = _report(1, "8")
    text = encode_budget_report(view.report)
    query = BudgetCurrentQueryV1(
        view.report.subject.account_id,
        view.report.subject.resource_id,
        view.report.scope_generation,
        view.report.requested_period,
        view.stored_at,
        active_binding=(
            ActiveCredentialBindingRefV1(
                view.report.subject.account_id, OpaqueIdV1("amcb_" + "b" * 32), 8
            )
            if active
            else None
        ),
    )
    validate_current_report_load(
        query,
        view,
        selected_id=view.report_id,
        selected_bytes=len(text.encode("utf-8")),
        canonical_text=text,
        collected_at=utc_text(view.report.collected_at),
    )


def test_more_than_fifty_attempts_cannot_resurrect_superseded_charges() -> None:
    old = _report(1, "8")
    replacement = _report(2, None)
    attempts = tuple(
        replace(
            view,
            report=replace(
                view.report,
                completeness="partial",
                omission_codes=("source_partial",),
                empty_means_zero=False,
            ),
        )
        for view in (_report(sequence, "100") for sequence in range(3, 104))
    )
    result = select_current_report((old, replacement, *attempts))
    assert result.current == replacement
    assert result.current.report.cost_buckets == ()
    assert result.latest_attempt == attempts[-1]


def test_current_load_budget_counts_each_report_once() -> None:

    identity = OpaqueIdV1("pure-report")
    assert bounded_current_report_ids(
        ((identity, 16 * 1024 * 1024), (identity, 16 * 1024 * 1024))
    ) == (identity,)
    assert (
        bounded_current_report_ids(
            ((identity, 16 * 1024 * 1024), (OpaqueIdV1("other-report"), 2))
        )
        is None
    )


def test_selected_payload_must_match_metadata_and_requested_scope() -> None:

    view = _report(1, "8")
    text = encode_budget_report(view.report)
    query = BudgetCurrentQueryV1(
        view.report.subject.account_id,
        view.report.subject.resource_id,
        view.report.scope_generation,
        view.report.requested_period,
        view.stored_at,
    )
    check = validate_current_report_load
    check(
        query,
        view,
        selected_id=view.report_id,
        selected_bytes=len(text),
        canonical_text=text,
        collected_at=utc_text(view.report.collected_at),
    )
    for invalid in (
        replace(query, account_id=OpaqueIdV1("other-account")),
        replace(query, resource_id=OpaqueIdV1("other-resource")),
        replace(query, scope_generation=2),
        replace(
            query,
            period=BudgetPeriodV1(
                query.period.start - timedelta(days=1), query.period.end
            ),
        ),
        replace(query, as_of=view.stored_at - timedelta(seconds=1)),
    ):
        with pytest.raises(ValueError, match="budget_current_metadata_invalid"):
            check(
                invalid,
                view,
                selected_id=view.report_id,
                selected_bytes=len(text),
                canonical_text=text,
                collected_at=utc_text(view.report.collected_at),
            )
    with pytest.raises(ValueError, match="budget_current_metadata_invalid"):
        check(
            query,
            view,
            selected_id=view.report_id,
            selected_bytes=len(text) - 1,
            canonical_text=text,
            collected_at=utc_text(view.report.collected_at),
        )
    with pytest.raises(ValueError, match="budget_current_metadata_invalid"):
        check(
            query,
            view,
            selected_id=view.report_id,
            selected_bytes=len(text),
            canonical_text=text,
            collected_at=utc_text(view.report.collected_at - timedelta(seconds=1)),
        )


def test_unknown_currency_and_unresolved_scope_do_not_become_known_money() -> None:

    known = _report(1, None)
    unknown = replace(
        known,
        report=replace(
            known.report,
            currency=None,
            scope_id=None,
            scope_evidence="unresolved",
            empty_means_zero=False,
        ),
    )
    selected = select_current_report((unknown,))
    assert selected.current == unknown
    assert selected.current.report.currency is None
    assert selected.current.report.scope_id is None
    assert not selected.current.report.empty_means_zero
    with pytest.raises(ValueError, match="budget_incompatible_report_context"):
        select_current_report((known, unknown))


def test_collection_time_precedes_storage_time_then_report_id_for_ordering() -> None:

    older = _report(1, "8")
    newer = _report(2, "6")
    late_ingest = replace(older, stored_at=newer.stored_at + timedelta(days=1))
    assert select_current_report((newer, late_ingest)).current == newer
    later_store = replace(
        newer,
        report_id=OpaqueIdV1("pure-later-store"),
        stored_at=newer.stored_at + timedelta(seconds=1),
    )
    assert select_current_report((newer, later_store)).current == later_store
    tie = replace(newer, report_id=OpaqueIdV1("zz-final-tie"))
    assert select_current_report((tie, newer)).current == tie


def test_metadata_reference_bound_and_inconsistent_sizes_fail_closed() -> None:
    references = tuple((OpaqueIdV1(f"report-{index}"), 2) for index in range(401))
    assert len(bounded_current_report_ids(references[:400]) or ()) == 400
    assert bounded_current_report_ids(references) is None
    with pytest.raises(ValueError, match="budget_current_metadata_invalid"):
        bounded_current_report_ids(((OpaqueIdV1("same"), 2), (OpaqueIdV1("same"), 3)))


def test_later_storage_and_wrong_selected_id_cannot_cross_as_of_guard() -> None:
    view = _report(1, "8")
    text = encode_budget_report(view.report)
    query = BudgetCurrentQueryV1(
        view.report.subject.account_id,
        view.report.subject.resource_id,
        1,
        view.report.requested_period,
        view.stored_at,
    )
    with pytest.raises(ValueError, match="budget_current_metadata_invalid"):
        validate_current_report_load(
            query,
            replace(view, stored_at=view.stored_at + timedelta(seconds=1)),
            selected_id=view.report_id,
            selected_bytes=len(text),
            canonical_text=text,
            collected_at=utc_text(view.report.collected_at),
        )
    with pytest.raises(ValueError, match="budget_current_metadata_invalid"):
        validate_current_report_load(
            query,
            view,
            selected_id=OpaqueIdV1("wrong-report"),
            selected_bytes=len(text),
            canonical_text=text,
            collected_at=utc_text(view.report.collected_at),
        )
