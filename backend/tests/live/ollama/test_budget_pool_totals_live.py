"""Full-filter totals over unchanged genuine reports and isolated owner metadata.

No provider read, credential access or telemetry write. Pool associations are
explicit test-owner assertions, never inferred provider identity.
"""

from __future__ import annotations

import asyncio
import json
import re
import secrets
from collections.abc import Generator
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import pytest
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.financial_pools import (
    SqliteFinancialPoolRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.bootstrap import create_iam_application
from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetCurrentPortV1,
    BudgetOverviewPortV1,
    BudgetOverviewQueryV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.collection_control_v1 import BudgetCollectionRunViewV1
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import AssignFinancialPoolCommandV1
from agentmonitor.foundation.application import LifecycleHooksV1
from agentmonitor.modules.registry.application.accounts import EditAccountCommandV1
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationCommandV1,
)
from fastapi import FastAPI

from backend.tests.integration.api.test_iam_http import _running
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def _require(condition: bool, code: str) -> None:
    if not condition:
        pytest.fail(code, pytrace=False)


def _id() -> OpaqueIdV1:
    return OpaqueIdV1(secrets.token_urlsafe(24))


def _atoms(money: ExactMoneyV1) -> int:
    return int(int(money.amount.coefficient) * 10 ** (18 - money.amount.scale))


def _source_total(view: BudgetReportViewV1) -> int:
    return sum(_atoms(bucket.amount) for bucket in view.report.cost_buckets)


@dataclass
class _Scenario:
    app: FastAPI
    overview: BudgetOverviewPortV1
    reports: tuple[BudgetReportViewV1, BudgetReportViewV1]
    query: BudgetOverviewQueryV1
    primary: OpaqueIdV1
    secondary: OpaqueIdV1
    phase: str
    included: tuple[BudgetReportViewV1, ...]
    excluded: int = 0

    def packet(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "period_start": self.query.period.start.isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z"),
            "period_end": self.query.period.end.isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z"),
            "as_of": self.query.as_of.isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            ),
            "sort_by": self.query.sort_by,
            "sort_direction": self.query.sort_direction,
            "primary": self.primary.value,
            "secondary": self.secondary.value,
            "excluded": self.excluded,
            "monetary_resources": sum(
                bool(view.report.cost_buckets) and view.report.currency is not None
                for view in self.reports
            ),
            "sources": [
                {
                    "account_id": view.report.subject.account_id.value,
                    "resource_id": view.report.subject.resource_id.value,
                    "report_id": view.report_id.value,
                    "included": view in self.included,
                }
                for view in self.reports
            ],
        }


def _scenarios(
    tmp_path: Path, *, require_two_money: bool = False
) -> Generator[_Scenario, None, None]:
    reference = _private_real_copy(tmp_path)
    config = tmp_path / "isolated.env"
    config.write_text("")
    config.chmod(0o600)
    app = create_iam_application(config, tmp_path, lifecycle=LifecycleHooksV1())
    app.state.lifecycle.hooks = replace(app.state.lifecycle.hooks, tasks=())
    current = cast(
        AccountBudgetCurrentPortV1,
        app.state.observation_ports.get_account_budget_current,
    )
    overview = cast(
        BudgetOverviewPortV1, app.state.observation_ports.list_budget_overview
    )
    repository = SqliteBudgetReportRepositoryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    now = datetime.now(UTC)
    now = now.replace(microsecond=now.microsecond // 1000 * 1000)
    stored: dict[OpaqueIdV1, BudgetReportViewV1] = {}
    after = None
    seen = set()
    for _ in range(100):
        batch = runs.list_runs("ollama", None, now, 500, after)
        for run in batch:
            if (
                isinstance(run, BudgetCollectionRunViewV1)
                and run.report_id is not None
                and run.account_id is not None
            ):
                view = repository.get_report(run.account_id, run.report_id)
                if view is not None:
                    stored[view.report_id] = view
        if len(batch) < 500:
            break
        after = batch[-1].run_id.value
        _require(after not in seen, "genuine_run_cursor_repeated")
        seen.add(after)
    else:
        pytest.fail("genuine_run_inventory_exceeds_bound", pytrace=False)
    # Discover periods from real records, then ask the current public port for
    # eligible lineage. A retained old report alone is not current pool authority.
    candidates: dict[OpaqueIdV1, BudgetReportViewV1] = {}
    contexts = {
        (view.report.subject.account_id, view.report.requested_period)
        for view in stored.values()
    }
    for account_id, period in contexts:
        reading = current(account_id, period=period, as_of=now)
        if reading is None or reading.availability.state != "available":
            continue
        for resource in reading.cloud_resources:
            for selection in resource.reports:
                view = selection.current
                if view is None:
                    continue
                report = view.report
                if (
                    report.completeness == "complete"
                    and report.covered_period == report.requested_period
                    and (report.cost_buckets or report.usage_buckets)
                    and not report.grouping
                    and report.source_category == "self_requests_and_cost"
                    and report.subject.provider_key == "ollama"
                ):
                    candidates[view.report_id] = view
    ordered = sorted(
        candidates.values(),
        key=lambda v: (bool(v.report.cost_buckets), v.stored_at, v.report_id.value),
        reverse=True,
    )
    pair = next(
        (
            (left, right)
            for left in ordered
            for right in ordered
            if left.report.subject.account_id != right.report.subject.account_id
            and left.report.currency is not None
            and _source_total(left) != 0
            and (
                not require_two_money
                or right.report.currency is not None
                and bool(right.report.cost_buckets)
            )
            and (
                right.report.currency is None
                or right.report.currency == left.report.currency
            )
            and (
                left.report.requested_period,
                left.report.cost_basis,
                left.report.source_category,
                left.report.source_id,
                left.report.subject.provider_target,
            )
            == (
                right.report.requested_period,
                right.report.cost_basis,
                right.report.source_category,
                right.report.source_id,
                right.report.subject.provider_target,
            )
            and (_source_total(left) != 0 or _source_total(right) != 0)
        ),
        None,
    )
    eligible = {
        view.report.subject.resource_id
        for view in ordered
        if view.report.cost_buckets and view.report.currency is not None
    }
    nonzero = {
        view.report.subject.resource_id for view in ordered if _source_total(view) != 0
    }
    current_resource_count = len({view.report.subject.resource_id for view in ordered})
    _require(
        pair is not None,
        (
            "genuine_two_current_compatible_money_resources_required"
            if require_two_money
            else "genuine_money_and_second_current_resource_required"
        )
        + f"_eligible_resources_{len(eligible)}_nonzero_resources_{len(nonzero)}"
        + f"_current_report_resources_{current_resource_count}",
    )
    assert pair is not None
    registry = SqliteRegistryRepositoryV1(reference)
    pools = SqliteFinancialPoolRepositoryV1(reference)
    owner = _id()
    organizations = tuple(
        registry.create_organization(
            CreateOrganizationCommandV1(
                _id(), owner, name + secrets.token_hex(4), None, datetime.now(UTC)
            )
        ).organization_id
        for name in ("Pool total primary ", "Pool total secondary ")
    )
    primary, secondary = organizations
    pool_ids = []

    def assign(
        view: BudgetReportViewV1,
        action: Literal["create", "join", "unlink"],
        pool: OpaqueIdV1 | None = None,
    ) -> OpaqueIdV1 | None:
        subject = view.report.subject
        configuration = pools.get_configuration(
            subject.account_id, subject.resource_id, "self"
        )
        _require(
            configuration is not None and configuration.scope is not None,
            "genuine_current_pool_authority_required",
        )
        assert configuration is not None and configuration.scope is not None
        result = pools.assign(
            AssignFinancialPoolCommandV1(
                configuration.scope,
                configuration.registry_revision,
                action,
                pool,
                primary if action == "create" else None,
                owner,
                _id(),
                datetime.now(UTC),
            )
        )
        return result.pool.pool_id if result.pool is not None else None

    for view in pair:
        account = registry.get_account(view.report.subject.account_id)
        _require(account is not None, "genuine_account_missing")
        assert account is not None
        registry.edit_account(
            EditAccountCommandV1(
                account.account_id,
                account.record_version,
                owner,
                _id(),
                "assign",
                datetime.now(UTC),
                organization_id=secondary,
            )
        )
        configuration = pools.get_configuration(
            account.account_id, view.report.subject.resource_id, "self"
        )
        if configuration is not None and configuration.pool is not None:
            assign(view, "unlink")
        pool_ids.append(assign(view, "create"))
    query = BudgetOverviewQueryV1(
        pair[0].report.requested_period,
        now,
        provider_key="ollama",
        organization_ids=(primary,),
        include_ungrouped=False,
        limit=1,
        sort_by="account",
    )
    scenario = _Scenario(
        app,
        overview,
        pair,
        query,
        primary,
        secondary,
        "distinct",
        tuple(
            view
            for view in pair
            if view.report.currency is not None and view.report.cost_buckets
        ),
    )
    if len(scenario.included) == 1 and any(
        context.spend is not None and _atoms(context.spend) != 0
        for row in overview(query).page.items
        for context in row.contexts
    ):
        scenario.query = replace(query, sort_direction="descending")
    yield scenario
    assign(pair[1], "unlink")
    assign(pair[1], "join", pool_ids[0])
    winner = max(
        scenario.included,
        key=lambda view: (
            view.report.collected_at,
            view.stored_at,
            view.report_id.value,
            view.report.subject.resource_id.value,
        ),
    )
    scenario.phase, scenario.included = "shared", (winner,)
    yield scenario
    # Both source accounts stay secondary. Primary-only must still resolve money
    # from them; the secondary filter must not count that pool or call it missing.
    assign(pair[1], "unlink")
    scenario.phase, scenario.included, scenario.excluded = "unlinked", (pair[0],), 1
    yield scenario
    for view in pair:
        _require(
            repository.get_report(view.report.subject.account_id, view.report_id)
            == view,
            "genuine_report_changed_by_metadata_scenario",
        )


def _check(scenario: _Scenario) -> None:
    for groups, counts in (
        ((scenario.primary,), True),
        ((scenario.secondary,), False),
        ((scenario.primary, scenario.secondary), True),
    ):
        query = replace(scenario.query, organization_ids=groups)
        first = scenario.overview(query)
        _require(
            first.page.availability.state == "available",
            "pool_total_overview_unavailable",
        )
        rows = list(first.page.items)
        page = first
        cursors = set()
        while page.page.has_more:
            cursor = page.page.next_key
            _require(
                cursor is not None and cursor not in cursors,
                "pool_total_cursor_invalid",
            )
            cursors.add(cursor)
            page = scenario.overview(replace(query, after_key=cursor))
            _require(
                page.page.availability.state == "available",
                "pool_total_continuation_unavailable",
            )
            _require(
                page.summaries == first.summaries
                and page.exclusions == first.exclusions
                and page.registry_revision == first.registry_revision,
                "pool_total_depends_on_loaded_page",
            )
            rows.extend(page.page.items)
        canonical = [row for row in rows if row.pool_id is not None]
        _require(
            len(canonical) == (2 if scenario.phase == "distinct" else 1),
            "pool_total_canonical_row_count",
        )
        _require(
            all(row.counted_in_selection is counts for row in canonical),
            "pool_total_primary_attribution",
        )
        if scenario.phase == "distinct":
            _require(first.page.has_more, "pool_total_later_page_required")
            if len(scenario.included) == 1:
                _require(
                    not any(
                        context.spend is not None and _atoms(context.spend) != 0
                        for row in first.page.items
                        for context in row.contexts
                    ),
                    "genuine_money_on_later_page_required",
                )
        if scenario.phase == "shared":
            _require(
                len(canonical[0].access_paths) == 2,
                "pool_total_shared_access_paths_missing",
            )
        expected = sum(_source_total(view) for view in scenario.included)
        relevant_exclusions = (
            (scenario.excluded if scenario.secondary in groups else 0)
            if scenario.phase == "unlinked"
            else (
                sum(
                    not view.report.cost_buckets or view.report.currency is None
                    for view in scenario.reports
                )
                if counts
                else 0
            )
        )
        if counts:
            _require(
                len(first.summaries) == 2, "pool_total_global_and_primary_required"
            )
            _require(
                {s.scope_kind for s in first.summaries} == {"global", "organization"},
                "pool_total_scopes_missing",
            )
            for summary in first.summaries:
                _require(
                    _atoms(summary.total) == expected
                    and summary.total.currency == scenario.included[0].report.currency,
                    "pool_total_not_independent_source_sum",
                )
                _require(
                    summary.included_pool_count == len(scenario.included)
                    and summary.excluded_resource_count
                    == (
                        0
                        if scenario.phase == "unlinked"
                        and summary.scope_kind == "organization"
                        else relevant_exclusions
                    ),
                    f"pool_total_coverage_incorrect_{scenario.phase}_{summary.scope_kind}"
                    + f"_included_{summary.included_pool_count}"
                    + f"_excluded_{summary.excluded_resource_count}"
                    + f"_expected_included_{len(scenario.included)}"
                    + f"_excluded_{relevant_exclusions}",
                )
                _require(
                    summary.cost_basis == scenario.included[0].report.cost_basis
                    and summary.source_category
                    == scenario.included[0].report.source_category,
                    "pool_total_context_incorrect",
                )
                _require(
                    summary.scope_kind == "global"
                    or summary.organization_id == scenario.primary,
                    "pool_total_wrong_organization",
                )
        else:
            _require(first.summaries == (), "secondary_pool_counted_twice")
        _require(
            sum(item.count for item in first.exclusions) == relevant_exclusions,
            "pool_total_false_missing_coverage",
        )
        if relevant_exclusions:
            _require(
                {e.reason_code for e in first.exclusions}
                == (
                    {"unresolved_overlap"}
                    if scenario.phase == "unlinked"
                    else {"currency_unavailable"}
                ),
                "pool_total_unavailable_reason",
            )
        for row in canonical:
            for context in row.contexts:
                if context.spend is None:
                    _require(
                        context.currency is None
                        and context.spend_reason == "cost_not_reported",
                        "counts_only_became_money",
                    )
                    continue
                matching = [
                    view
                    for view in scenario.included
                    if view.report_id == context.report_id
                ]
                _require(
                    len(matching) == 1 and context.spend is not None,
                    "pool_total_contributing_report_missing",
                )
                view = matching[0]
                _require(
                    context.report_account_id == view.report.subject.account_id
                    and context.report_resource_id == view.report.subject.resource_id,
                    "pool_total_contributing_destination_incorrect",
                )
                assert context.spend is not None
                _require(
                    _atoms(context.spend) == _source_total(view),
                    "pool_total_context_source_sum",
                )


def test_genuine_available_filtered_pool_totals(tmp_path: Path) -> None:
    for scenario in _scenarios(tmp_path):
        _check(scenario)


def test_genuine_two_monetary_pool_totals(tmp_path: Path) -> None:
    for scenario in _scenarios(tmp_path, require_two_money=True):
        _check(scenario)


@pytest.mark.parametrize("phases", (1, 3), ids=("first_phase", "all_phases"))
def test_genuine_pool_totals_built_browser(tmp_path: Path, phases: int) -> None:
    async def exercise() -> None:
        scenarios = _scenarios(tmp_path)
        first = next(scenarios)
        async with _running(first.app) as origin:

            async def probe(scenario: _Scenario) -> None:
                _check(scenario)
                process = await asyncio.create_subprocess_exec(
                    "node",
                    "frontend/tests/browser/m7/pool_totals.mjs",
                    origin,
                    cwd=Path(__file__).resolve().parents[4],
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                try:
                    output, _ = await asyncio.wait_for(
                        process.communicate(json.dumps(scenario.packet()).encode()),
                        timeout=180,
                    )
                finally:
                    if process.returncode is None:
                        process.terminate()
                        await asyncio.wait_for(process.wait(), timeout=10)
                failed_stage = re.fullmatch(
                    rb"M7 POOL TOTALS BROWSER: FAILED \xe2\x80\x94 ([a-z_]+)\n",
                    output,
                )
                _require(
                    process.returncode == 0
                    and re.fullmatch(
                        rb"M7 POOL TOTALS BROWSER: PASSED monetary_resources=[12] "
                        rb"filters=3 continuations=[0-9]+ links=[1-9][0-9]*\n",
                        output,
                    )
                    is not None,
                    "pool_totals_browser_failed_"
                    + scenario.phase
                    + "_"
                    + (
                        failed_stage.group(1).decode("ascii")
                        if failed_stage
                        else "protocol_or_exit"
                    ),
                )

            await probe(first)
            if phases == 1:
                scenarios.close()
                return
            for scenario in scenarios:
                await probe(scenario)

    asyncio.run(exercise())
