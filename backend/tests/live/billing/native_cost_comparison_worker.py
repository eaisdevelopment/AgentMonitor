"""Alternate real test worker: native monetary comparison, normal fenced commit.

T006/T008/T015. This is not proof of the stock worker entrypoint. No source body
or credential is emitted; only the test-owned source callback adds comparison.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import resource
import sys
import threading
import time
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.composition.billing_collection import BillingCollectionV1
    from agentmonitor.composition.billing_schedule import BillingScheduleIntentV1
    from agentmonitor.contracts.collection_control_v1 import (
        BudgetCollectionRunAdmissionV1,
    )


def failure_context(witness: dict[str, object]) -> str:
    """Return only fixed stages/types, never arbitrary exception text or data."""
    phase, kind = witness.get("phase"), witness.get("error_kind")
    phases = {
        "targets",
        "credential_location",
        "dispatch_prepare",
        "baseline",
        "enqueue",
        "claim",
        "execute",
        "authority",
        "authorization",
        "source",
        "commit",
    }
    kinds = {
        "ValueError",
        "TypeError",
        "AssertionError",
        "TimeoutError",
        "OperationalError",
        "IntegrityError",
        "OSError",
        "RuntimeError",
        "CollectionRepositoryErrorV1",
        "BudgetCollectionError",
    }
    safe_phase = phase if isinstance(phase, str) and phase in phases else "unknown"
    safe_kind = kind if isinstance(kind, str) and kind in kinds else "unknown"
    return f"{safe_phase}:{safe_kind}"


def _has_monetary_baseline(
    reference: DatabaseRefV1, intent: BillingScheduleIntentV1, as_of: datetime
) -> bool:
    """Identify a monetary source across rollover; never supply expected amounts."""
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.contracts.capacity_v1 import BudgetCurrentQueryV1, BudgetPeriodV1

    context, target = intent.report_context, intent.target
    if context.source_category != "cost" or context.grouping:
        return False
    repository = SqliteBudgetReportRepositoryV1(reference)
    # A new UTC period need not have a report before its first comparison.
    # Yesterday's complete same-range evidence can identify the monetary source
    # under the same active binding and scope. The actual request still uses
    # today's unchanged scheduled context and must independently reconcile.
    for offset in (timedelta(0), timedelta(days=1)):
        period = BudgetPeriodV1(
            context.interval_start - offset, context.interval_end - offset
        )
        result = repository.get_current_reports(
            BudgetCurrentQueryV1(
                target.connection.account_id,
                target.connection.resource_id,
                target.connection.scope_generation,
                period,
                as_of,
                active_binding=target.binding,
            )
        )
        if result.availability.state != "available":
            continue
        if any(
            selected.current is not None
            and selected.current.report.subject.provider_key
            == target.connection.provider_key
            and selected.current.report.source_category == "cost"
            and not selected.current.report.grouping
            and selected.current.report.currency is not None
            and selected.current.report.completeness == "complete"
            and selected.current.report.covered_period == period
            and (
                bool(selected.current.report.cost_buckets)
                or selected.current.report.empty_means_zero
            )
            for selected in result.items
        ):
            return True
    return False


def _execute(
    collector: BillingCollectionV1,
    admission: BudgetCollectionRunAdmissionV1,
    witness: dict[str, object],
) -> None:
    """Keep the production credential/service/commit fences around the real source."""
    from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
        SqliteBillingAccessRepositoryV1,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
        SqliteCloudCredentialRegistryV1,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
        account_credential_lock,
    )
    from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
        AnthropicCostRequestV1,
    )
    from agentmonitor.adapters.providers.claude.anthropic_api.source import (
        AnthropicCostResultV1,
    )
    from agentmonitor.adapters.providers.codex.openai_api.policy import (
        OpenAICostRequestV1,
    )
    from agentmonitor.adapters.providers.codex.openai_api.source import (
        OpenAICostResultV1,
    )
    from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
        approve_env_credential_file_v1,
        env_credential_file_lease_v1,
    )
    from agentmonitor.composition.billing_capacity_commit import (
        billing_capacity_repository,
    )
    from agentmonitor.composition.billing_env_authorization import (
        AnthropicEnvAuthorizationV1,
        OpenAIEnvAuthorizationV1,
    )
    from agentmonitor.composition.billing_run import (
        anthropic_billing_outcome,
        anthropic_billing_request,
        normalize_anthropic_billing_outcome,
    )
    from agentmonitor.composition.ollama_env_store import env_location_matches
    from agentmonitor.composition.openai_billing_run import (
        OPENAI_COST_AUTHORITY_ID_V1,
        normalize_openai_billing_outcome,
        openai_billing_outcome,
        openai_billing_request,
    )
    from agentmonitor.contracts.capacity_v1 import BudgetReportInputV1
    from agentmonitor.contracts.collection_control_v1 import (
        BudgetCollectionReceiptV1,
        BudgetCollectionRunAdmissionV2,
        CollectionFailedV1,
    )
    from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1
    from agentmonitor.modules.collection_control.application.budget_executor import (
        ExecuteBudgetCollectionRunV1,
    )

    from backend.tests.live.billing.native_cost_sources import (
        collect_anthropic_cost_with_comparison,
        collect_openai_cost_with_comparison,
    )

    if (
        not isinstance(admission, BudgetCollectionRunAdmissionV2)
        or admission.provider_key not in {"claude", "codex"}
        or admission.capability_id != "api.cost"
        or admission.report_context.source_category != "cost"
        or admission.report_context.grouping
    ):
        raise ValueError("native_cost_context_invalid")
    witness["phase"] = "authority"
    is_openai = admission.provider_key == "codex"
    run = collector._runs.assert_claimed_budget_run(admission, datetime.now(UTC))
    service = SqliteCloudCredentialRegistryV1(
        collector._reference
    ).read_active_access_target(admission.provider_target.target_id)
    if (
        service is None
        or service.provider_key != admission.provider_key
        or service.authority_id
        != (OPENAI_COST_AUTHORITY_ID_V1 if is_openai else "anthropic.analytics")
        or service.manifest_fingerprint != admission.manifest_fingerprint
    ):
        collector._runs.finalize_failed(
            CollectionFailedV1(
                admission.run_id,
                "blocked",
                "billing_service_target_unavailable",
                datetime.now(UTC),
            ),
            fencing_token=run.fencing_token,
            scheduler_instance_id=collector._instance,
        )
        witness["reason"] = "native_cost_service_target_unavailable"
        return
    witness.update(
        service_target_id=service.access_target_id.value,
        service_record_version=service.record_version,
        service_manifest_fingerprint=service.manifest_fingerprint,
    )
    executor = ExecuteBudgetCollectionRunV1(
        collector._runs,
        billing_capacity_repository(
            collector._reference,
            scheduler_instance_id=collector._instance,
            fencing_token=run.fencing_token,
            access_target=service,
        ),
    )
    target = admission.billing_target
    witness["phase"] = "authorization"
    with ExitStack() as stack:
        authorization: AnthropicEnvAuthorizationV1 | OpenAIEnvAuthorizationV1 | None
        authorization = None
        try:
            lock = stack.enter_context(
                account_credential_lock(
                    collector._reference, target.connection.account_id
                )
            )
            SqliteBillingAccessRepositoryV1(collector._reference).ensure_current(target)
            if collector._credential_env_file is None or not env_location_matches(
                collector._data_root, collector._credential_env_file
            ):
                raise ValueError("billing_credential_location_unavailable")
            file = stack.enter_context(
                env_credential_file_lease_v1(
                    approve_env_credential_file_v1(collector._credential_env_file)
                )
            )
            authorize = (
                OpenAIEnvAuthorizationV1 if is_openai else AnthropicEnvAuthorizationV1
            )
            authorization = authorize(
                target.binding.binding_id.value,
                target.connection.account_id,
                lock.inherited_lock(target.connection.account_id),
                file.inherited_file(),
            )
        except (OSError, ValueError):
            authorization = None

        def deadline() -> float:
            remaining = (admission.deadline_at - datetime.now(UTC)).total_seconds() - 5
            return min(collector._deadline - 5, time.monotonic() + remaining)

        def collect_openai() -> CollectionOutcomeV1[BudgetReportInputV1]:
            witness["phase"] = "source"
            assert authorization is None or isinstance(
                authorization, OpenAIEnvAuthorizationV1
            )
            request = openai_billing_request(admission)
            if not isinstance(request, OpenAICostRequestV1):
                raise ValueError("native_cost_context_invalid")
            bound = deadline()
            result = (
                OpenAICostResultV1(
                    "deadline_exceeded", "openai_report_deadline_exceeded", None, 0
                )
                if bound <= time.monotonic()
                else collect_openai_cost_with_comparison(
                    request,
                    authorization=authorization,
                    deadline_monotonic=bound,
                    witness=witness,
                )
            )
            if result.report is not None:
                witness["collected_at"] = result.report.collected_at.isoformat()
            witness["source_state"] = result.state
            witness["phase"] = "commit"
            return openai_billing_outcome(admission, result, datetime.now(UTC))

        def collect_anthropic() -> CollectionOutcomeV1[BudgetReportInputV1]:
            witness["phase"] = "source"
            assert authorization is None or isinstance(
                authorization, AnthropicEnvAuthorizationV1
            )
            request = anthropic_billing_request(admission)
            if not isinstance(request, AnthropicCostRequestV1):
                raise ValueError("native_cost_context_invalid")
            bound = deadline()
            result = (
                AnthropicCostResultV1(
                    "deadline_exceeded",
                    "anthropic_analytics_deadline_exceeded",
                    None,
                    0,
                )
                if bound <= time.monotonic()
                else collect_anthropic_cost_with_comparison(
                    request,
                    authorization=authorization,
                    deadline_monotonic=bound,
                    witness=witness,
                )
            )
            if result.report is not None:
                witness["collected_at"] = result.report.collected_at.isoformat()
            witness["source_state"] = result.state
            witness["phase"] = "commit"
            return anthropic_billing_outcome(admission, result, datetime.now(UTC))

        receipt = executor.execute_claimed(
            admission,
            collect_openai if is_openai else collect_anthropic,
            normalize_openai_billing_outcome
            if is_openai
            else normalize_anthropic_billing_outcome,
            as_of=datetime.now(UTC),
            completed_at=lambda: datetime.now(UTC),
        )
        witness.update(
            run_id=admission.run_id.value,
            account_id=target.connection.account_id.value,
            resource_id=target.connection.resource_id.value,
            source_id=admission.source_id,
            parser_version=admission.adapter_version,
            context={
                "range": admission.report_context.range_key,
                "start": admission.report_context.interval_start.isoformat(),
                "end": admission.report_context.interval_end.isoformat(),
                "source_category": admission.report_context.source_category,
                "grouping": list(admission.report_context.grouping),
            },
        )
        if not isinstance(receipt, BudgetCollectionReceiptV1):
            witness.update(
                state="mismatch"
                if witness.get("comparison_state") == "mismatch"
                else "not_run",
                reason="native_cost_mismatch"
                if witness.get("comparison_state") == "mismatch"
                else "native_cost_authorization_unavailable"
                if witness.get("source_state") == "authorization_unavailable"
                else "native_cost_report_not_committed",
            )
            return
        witness.update(
            report_id=receipt.report_id.value,
            report_digest=receipt.payload_digest,
            fact_count=len(receipt.fact_ids),
            fact_ids_digest=hashlib.sha256(
                "\0".join(item.value for item in receipt.fact_ids).encode("ascii")
            ).hexdigest(),
        )
        matched = witness.get("comparison_state") == "matched" or (
            witness.get("comparison_state") == "empty_complete"
            and witness.get("qualified_zero") is True
        )
        witness.update(
            state="matched" if matched else "not_run",
            reason=None if matched else "native_cost_monetary_comparison_incomplete",
        )


def _run(root: Path, provider: str, witness: dict[str, object]) -> None:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.composition.billing_collection import BillingCollectionV1
    from agentmonitor.composition.billing_schedule import BillingScheduleV1
    from agentmonitor.composition.financial_dispatch import prepare_financial_dispatch
    from agentmonitor.composition.ollama_env_store import read_env_location
    from agentmonitor.composition.ollama_usage_collection import OllamaUsageCollectionV1

    provider_key = {"anthropic": "claude", "openai": "codex"}[provider]
    deadline = time.monotonic() + 110
    reference = DatabaseRefV1(root / "agentmonitor.db", root)
    scheduler = BillingScheduleV1(reference)
    witness["phase"] = "targets"
    targets = scheduler.read_targets(deadline_monotonic=deadline)
    if not any(
        target.connection.provider_key == provider_key
        and target.purpose == "monitoring"
        for target in targets
    ):
        witness["reason"] = "native_cost_monitoring_resource_unavailable"
        return
    witness["phase"] = "credential_location"
    env = read_env_location(root)
    if env is None:
        witness["reason"] = "native_cost_credential_location_unavailable"
        return
    collector = BillingCollectionV1(
        root, credential_env_file=env, deadline_monotonic=deadline
    )
    usage = OllamaUsageCollectionV1(
        root, credential_env_file=env, deadline_monotonic=deadline
    )
    witness["phase"] = "dispatch_prepare"
    work, scheduled, _ = prepare_financial_dispatch(
        collector._runs, scheduler, usage.prepare_runs(), deadline_monotonic=deadline
    )
    for candidate in work:
        if candidate.queued_run_id is not None:
            witness["reason"] = "native_cost_owner_queue_precedes"
            return
        if candidate.key[0] != provider_key or not candidate.scheduled_due:
            continue
        intent = scheduled[candidate.key]
        witness["phase"] = "baseline"
        if (
            intent.report_context.source_category != "cost"
            or intent.report_context.grouping
            or not _has_monetary_baseline(reference, intent, datetime.now(UTC))
        ):
            continue
        witness["phase"] = "enqueue"
        selected = scheduler.enqueue_intent(intent, deadline_monotonic=deadline)
        if selected is None:
            continue
        witness["phase"] = "claim"
        admission = collector._claim_one(
            provider_key=provider_key,
            operation_family=candidate.key[2],
            expected_run_id=selected.run_id,
        )
        if admission is None:
            witness["reason"] = "native_cost_admission_unavailable"
            return
        witness["phase"] = "execute"
        _execute(collector, admission, witness)
        return


def _sealed_runtime(root: Path, revision: str, provider: str) -> bool:
    from agentmonitor.composition import billing_collection

    if provider == "anthropic":
        from agentmonitor.adapters.providers.claude.anthropic_api import (
            source as anthropic_source,
        )

        source_file = anthropic_source.__file__
        relative = "adapters/providers/claude/anthropic_api/source.py"
    else:
        from agentmonitor.adapters.providers.codex.openai_api import (
            source as openai_source,
        )

        source_file = openai_source.__file__
        relative = "adapters/providers/codex/openai_api/source.py"
    if billing_collection.__file__ is None or source_file is None:
        return False
    collection_path = Path(billing_collection.__file__).resolve()
    runtime = collection_path.parents[4]
    return (
        runtime.parent == root / "releases"
        and re.fullmatch("m6-candidate-" + revision + "-[a-f0-9]{64}", runtime.name)
        is not None
        and collection_path
        == runtime / "backend/src/agentmonitor/composition/billing_collection.py"
        and Path(source_file).resolve()
        == runtime / "backend/src/agentmonitor" / relative
    )


def main() -> int:
    from agentmonitor.composition.worker_start_authority import (
        consume_worker_start_authority_v1,
    )

    if len(sys.argv) != 5 or not consume_worker_start_authority_v1(sys.argv[2]):
        return 5
    root = Path(sys.argv[1])
    revision, provider = sys.argv[3:]
    if (
        not root.is_absolute()
        or root in {Path("/"), Path.home()}
        or re.fullmatch("[a-f0-9]{40}", revision) is None
        or provider not in {"anthropic", "openai"}
    ):
        return 2
    if not _sealed_runtime(root, revision, provider):
        return 6
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    watchdog = threading.Timer(120, lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    witness: dict[str, object] = dict(
        schema="m7-native-cost-comparison-v1",
        composition="alternate_real_test_worker",
        revision=revision,
        provider=provider,
        state="not_run",
        reason="native_cost_no_due_context",
        requests=0,
        compared_rows=0,
    )
    try:
        _run(root, provider, witness)
    except Exception as error:
        context = failure_context(
            {"phase": witness.get("phase"), "error_kind": type(error).__name__}
        )
        witness["phase"], witness["error_kind"] = context.split(":")
        witness.update(state="not_run", reason="native_cost_execution_unresolved")
    finally:
        watchdog.cancel()
    print(json.dumps(witness, sort_keys=True), flush=True)
    return 0 if witness["state"] == "matched" and "report_id" in witness else 3


if __name__ == "__main__":
    raise SystemExit(main())
