"""Alternate real test composition: one official GET, no provider body retention.

Not the stock worker entrypoint. All admission, credential and commit authorities
are production implementations; only the real source callback adds comparison.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import resource
import secrets
import sys
import threading
import time
import uuid
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from backend.tests.live.ollama.native_usage_comparison import (
    NormalizedCost,
    compare_completed_usd,
    project_native_day,
)

if TYPE_CHECKING:
    from agentmonitor.adapters.providers.ollama.api.policy import OllamaUsageRequestV1
    from agentmonitor.adapters.providers.ollama.api.source import (
        OllamaUsageAuthorizationV1,
        OllamaUsageResultV1,
    )
    from agentmonitor.composition.ollama_usage_collection import OllamaUsageCollectionV1
    from agentmonitor.contracts.collection_control_v1 import (
        CloudBudgetCollectionRunAdmissionV1,
        OllamaCloudRequestLeaseV1,
    )


def _real_source(
    request: OllamaUsageRequestV1,
    authorization: OllamaUsageAuthorizationV1,
    deadline: float,
    witness: dict[str, object],
) -> OllamaUsageResultV1:
    from agentmonitor.adapters.providers.ollama.api import source
    from agentmonitor.adapters.providers.ollama.api.policy import bounded_deadline

    attempted = 0
    payload: dict[str, object] | None = None
    try:
        deadline = bounded_deadline(time.monotonic(), deadline)
        with source.request_deadline(deadline):
            pass
        attempted = 1
        payload = source._fetch(request, authorization, deadline)
        bounded_deadline(time.monotonic(), deadline)
        report, money = source._report(request, payload, datetime.now(UTC))
        bounded_deadline(time.monotonic(), deadline)
        # Known monetary disagreement must not replace a previous good report.
        # Read only the approved day interval/partial/USD fields from RAM.
        failure_stage = "native_extraction"
        try:
            if report.grouping or request.grouping:
                raise ValueError("native_comparison_context_invalid")
            rows = payload["buckets"]
            if not isinstance(rows, list):
                raise ValueError("native_comparison_context_invalid")
            native = []
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError("native_comparison_context_invalid")
                native.append(
                    project_native_day(
                        row["from"],
                        row["until"],
                        row.get("usage_usd"),
                        row.get("partial", False),
                    )
                )
            failure_stage = "exact_comparison"
            normalized = tuple(
                NormalizedCost(
                    cost.period.start,
                    cost.period.end,
                    int(cost.amount.amount.coefficient),
                    cost.amount.amount.scale,
                    cost.amount.currency,
                    bool(cost.dimensions),
                )
                for cost in report.cost_buckets
            )
            count = compare_completed_usd(
                tuple(native), normalized, request.period.start, request.period.end
            )
            if (
                count == (request.period.end - request.period.start).days
                and report.completeness == "complete"
            ):
                witness.update(state="matched", reason=None, matched_days=count)
            else:
                witness.update(
                    state="money_not_reported",
                    reason="native_comparison_money_not_reported",
                    matched_days=count,
                )
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            allowed = {
                "native_comparison_mismatch",
                "native_comparison_context_invalid",
                "native_comparison_money_not_reported",
            }
            reason = (
                str(error)
                if type(error) is ValueError and str(error) in allowed
                else "native_comparison_context_invalid"
            )
            witness.update(
                state="money_not_reported"
                if reason.endswith("money_not_reported")
                else "mismatch",
                reason=reason,
                matched_days=0,
                failure_stage=failure_stage,
            )
        witness.update(requests=attempted, collected_at=report.collected_at.isoformat())
        if witness.get("state") == "mismatch":
            return source.OllamaUsageResultV1(
                "invalid_provider_data",
                "ollama_usage_invalid_provider_data",
                None,
                attempted,
                http_status=200,
            )
        return source.OllamaUsageResultV1(
            "partial" if report.completeness == "partial" else "success",
            "ollama_usage_cost_not_reported"
            if money == "not_reported"
            else "ollama_usage_"
            + ("partial" if report.completeness == "partial" else "success"),
            report,
            attempted,
            money,
            200,
        )
    except source._WorkerRequired:
        state: source.State = "worker_required"
    except TimeoutError:
        state = "deadline_exceeded"
    except source._SourceFailure as error:
        return source.OllamaUsageResultV1(
            error.state,
            "ollama_usage_" + error.state,
            None,
            attempted,
            http_status=error.status,
            retry_after_seconds=error.retry,
        )
    except (ValueError, TypeError, KeyError, RecursionError):
        state = "invalid_provider_data"
    except (OSError, http.client.HTTPException):
        state = "provider_unavailable"
    except Exception:
        state = "internal_error"
    finally:
        if payload is not None:
            payload.clear()
    # Unknown dispatch remains unknown exactly as in the stock source.
    return source.OllamaUsageResultV1(state, "ollama_usage_" + state, None, attempted)


def _execute(
    collector: OllamaUsageCollectionV1,
    run: CloudBudgetCollectionRunAdmissionV1,
    lease: OllamaCloudRequestLeaseV1,
    witness: dict[str, object],
    *,
    claimed: bool,
) -> None:
    from agentmonitor.adapters.persistence.collection_control.sqlite import (
        ollama_cloud_admission as cloud_admission,
    )
    from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
        account_credential_lock,
    )
    from agentmonitor.adapters.providers.ollama.api.policy import SOURCE_ID
    from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
        approve_env_credential_file_v1,
        env_credential_file_lease_v1,
    )
    from agentmonitor.composition import ollama_usage_collection as runtime
    from agentmonitor.composition.billing_env_authorization import (
        OllamaUsageEnvAuthorizationV1,
    )
    from agentmonitor.composition.ollama_usage_dispatch import (
        usage_no_response_terminal,
    )
    from agentmonitor.composition.ollama_usage_fence import (
        cloud_usage_fence,
        usage_capacity_repository,
    )
    from agentmonitor.composition.ollama_usage_result import (
        normalize_usage_report,
        usage_outcome,
    )
    from agentmonitor.composition.ollama_usage_run import usage_request_for_run
    from agentmonitor.contracts.capacity_v1 import BudgetReportInputV1
    from agentmonitor.contracts.collection_control_v1 import (
        BudgetCollectionReceiptV1,
        OllamaCloudRequestCompletionV1,
    )
    from agentmonitor.contracts.provider_system_v1 import CollectionOutcomeV1
    from agentmonitor.modules.collection_control.application.budget_executor import (
        ExecuteBudgetCollectionRunV1,
    )

    from backend.tests.live.ollama.budget_commit_retry_witness import (
        BudgetCommitRetryWitness,
    )

    completion = None
    runs = cloud_admission.SqliteOllamaCloudRunRepositoryV1(
        collector._reference, lease, cloud_admission_fence=cloud_usage_fence
    )
    try:
        request = usage_request_for_run(run, dispatched_at=datetime.now(UTC))
        with ExitStack() as stack:
            lock = stack.enter_context(
                account_credential_lock(
                    collector._reference, run.cloud_target.account_id
                )
            )
            deadline = min(
                collector._deadline - 5,
                time.monotonic()
                + (
                    min(run.deadline_at, lease.lease_expires_at) - datetime.now(UTC)
                ).total_seconds()
                - 5,
            )
            if collector._env_file is None or not runtime._bounded_env_location_matches(
                collector._root, collector._env_file, deadline
            ):
                raise ValueError("native_comparison_credential_location_unavailable")
            credential_file = stack.enter_context(
                env_credential_file_lease_v1(
                    approve_env_credential_file_v1(collector._env_file)
                )
            )
            authorization = OllamaUsageEnvAuthorizationV1(
                run.cloud_target.binding.binding_id.value,
                run.cloud_target.account_id,
                lock.inherited_lock(run.cloud_target.account_id),
                credential_file.inherited_file(),
            )
            admitted = runs.get_run(run.run_id) if claimed else runs.admit_run(run)
            if claimed:
                runs.assert_claimed_budget_run(run, as_of=datetime.now(UTC))
            else:
                runs.mark_running(
                    run.run_id,
                    datetime.now(UTC),
                    fencing_token=admitted.fencing_token,
                    scheduler_instance_id=collector._instance,
                )
            executor = ExecuteBudgetCollectionRunV1(
                runs,
                BudgetCommitRetryWitness(
                    collector._reference,
                    usage_capacity_repository(
                        collector._reference,
                        admission=run,
                        lease=lease,
                        fencing_token=admitted.fencing_token,
                    ),
                    witness,
                ),
            )

            def collect() -> CollectionOutcomeV1[BudgetReportInputV1]:
                nonlocal completion
                collector._gate.mark_dispatched(lease, datetime.now(UTC))
                remaining = (
                    min(run.deadline_at, lease.lease_expires_at) - datetime.now(UTC)
                ).total_seconds() - 5
                result = _real_source(
                    request,
                    authorization,
                    min(collector._deadline - 5, time.monotonic() + remaining),
                    witness,
                )
                completed = datetime.now(UTC)
                terminal = usage_no_response_terminal(
                    result, lease, completed_at=completed
                )
                if terminal is not None:
                    raise runtime._UsageNotStarted(terminal, result)
                if result.http_status is None:
                    raise ValueError("ollama_usage_outcome_unresolved")
                success = result.state in {"success", "partial"}
                completion = OllamaCloudRequestCompletionV1(
                    lease.admission_id,
                    lease.scheduler_instance_id,
                    lease.schedule_id,
                    lease.fencing_token,
                    lease.started_at,
                    completed,
                    "succeeded"
                    if success
                    else "rate_limited"
                    if result.state == "rate_limited"
                    else "failed",
                    result.retry_after_seconds
                    if result.state == "rate_limited"
                    else None,
                    secrets.randbelow(11),
                )
                collector._gate.record_completion(
                    lease, completion, failure_code=None if success else result.state
                )
                return usage_outcome(run, result, completed_at=completed)

            try:
                receipt = executor.execute_claimed(
                    run,
                    collect,
                    normalize_usage_report,
                    as_of=datetime.now(UTC),
                    completed_at=lambda: datetime.now(UTC),
                )
            except runtime._UsageNotStarted as stopped:
                collector._finish_not_started(
                    run, lease, admitted.fencing_token, stopped.terminal, stopped.result
                )
                witness.update(
                    state="not_run", reason="native_comparison_request_not_started"
                )
                return
            if completion is not None:
                collector._gate.complete(completion)
            if not isinstance(receipt, BudgetCollectionReceiptV1):
                if witness.get("state") != "mismatch":
                    witness.update(
                        state="not_run", reason="native_comparison_report_not_committed"
                    )
                return
            witness.update(
                run_id=receipt.run_id.value,
                report_id=receipt.report_id.value,
                report_digest=receipt.payload_digest,
                fact_count=len(receipt.fact_ids),
                fact_ids_digest=hashlib.sha256(
                    "\0".join(item.value for item in receipt.fact_ids).encode("ascii")
                ).hexdigest(),
                account_id=request.subject.account_id.value,
                resource_id=request.subject.resource_id.value,
                context={
                    "scope": request.scope,
                    "range": request.range_key,
                    "start": request.period.start.isoformat(),
                    "end": request.period.end.isoformat(),
                    "grouping": list(request.grouping),
                },
                currency="USD",
                source_id=SOURCE_ID,
            )
    except BaseException:
        try:
            collector._gate.recover_rate_gate(
                datetime.now(UTC), expected=lease, reserved_only=True
            )
        except Exception:
            pass
        raise


def _run(root: Path, witness: dict[str, object]) -> None:
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.adapters.providers.ollama.api.manifest import ADAPTER_VERSION
    from agentmonitor.adapters.providers.ollama.api.policy import SOURCE_ID
    from agentmonitor.composition import ollama_usage_collection as runtime
    from agentmonitor.composition.billing_schedule import BillingScheduleV1
    from agentmonitor.composition.financial_dispatch import prepare_financial_dispatch
    from agentmonitor.composition.ollama_env_store import read_env_location
    from agentmonitor.composition.ollama_usage_run import usage_request_for_run
    from agentmonitor.contracts.capacity_v1 import (
        BudgetPeriodV1,
        BudgetReportHistoryQueryV1,
    )
    from agentmonitor.contracts.collection_control_v1 import OllamaCloudRequestAcquireV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    collector = runtime.OllamaUsageCollectionV1(
        root,
        credential_env_file=read_env_location(root),
        deadline_monotonic=time.monotonic() + 110,
    )
    preparation_started = time.monotonic()
    work, _, scheduled = prepare_financial_dispatch(
        SqliteCollectionRepositoryV1(collector._reference),
        BillingScheduleV1(collector._reference),
        collector.prepare_runs(),
        deadline_monotonic=collector._deadline,
    )
    witness["preparation_ms"] = int((time.monotonic() - preparation_started) * 1000)
    witness["parser_version"] = ADAPTER_VERSION
    for candidate in work:
        if candidate.queued_run_id is not None:
            # Never bypass earlier owner work, including another provider.
            witness["reason"] = "native_comparison_owner_queue_precedes"
            return
        if candidate.key[0] != "ollama":
            continue
        if not candidate.scheduled_due:
            continue
        run = scheduled[candidate.key]
        now = datetime.now(UTC)
        if (
            collector._env_file is None
            or run.deadline_at <= now
            or run.report_context.scope != "self"
            or run.report_context.grouping
        ):
            witness["reason"] = "native_comparison_context_unavailable"
            return
        if (
            SqliteCollectionRepositoryV1(
                collector._reference
            ).get_budget_next_allowed_at(
                run.budget_scope_digest, run.budget_dimension, run.budget_unit, now
            )
            is not None
        ):
            continue
        # Real retained metadata selects a meaningful due test context; no
        # schedule, budget or provider account is rewritten to make it eligible.
        actual_request = usage_request_for_run(run, dispatched_at=now)
        query = BudgetReportHistoryQueryV1(
            run.cloud_target.account_id,
            run.cloud_target.resource_id,
            BudgetPeriodV1(
                run.report_context.interval_start, run.report_context.interval_end
            ),
            limit=50,
            as_of=now,
        )
        page = SqliteBudgetReportRepositoryV1(collector._reference).list_reports(query)
        retained = next(
            (
                item.report
                for item in page.items
                if item.report.source_id == SOURCE_ID
                and item.report.source_category == "self_requests_and_cost"
                and not item.report.grouping
                and item.report.binding_id == run.cloud_target.binding.binding_id
                and item.report.binding_generation
                == run.cloud_target.binding.generation
                and item.report.scope_generation == actual_request.scope_generation
            ),
            None,
        )
        if (
            retained is None
            or retained.currency != "USD"
            or retained.completeness != "complete"
            or len(retained.cost_buckets)
            != (actual_request.period.end - actual_request.period.start).days
        ):
            continue
        decision = collector._gate.acquire_usage(
            OllamaCloudRequestAcquireV1(
                OpaqueIdV1("usage-admission-" + uuid.uuid4().hex),
                collector._instance,
                now,
                run.deadline_at,
                secrets.randbelow(11),
            ),
            admission=run,
        )
        if decision.lease is None:
            witness["admission_state"] = decision.state
            witness["reason"] = "native_comparison_shared_gate_unavailable"
            return
        _execute(collector, run, decision.lease, witness, claimed=False)
        return


def _sealed_runtime(root: Path, revision: str) -> bool:
    """Namespace packages have no file; pin the two actual implementation files."""
    from agentmonitor.adapters.providers.ollama.api import source
    from agentmonitor.composition import ollama_usage_collection

    if ollama_usage_collection.__file__ is None or source.__file__ is None:
        return False
    collection_path = Path(ollama_usage_collection.__file__).resolve()
    runtime = collection_path.parents[4]
    if (
        runtime.parent != root / "releases"
        or re.fullmatch("m6-candidate-" + revision + "-[a-f0-9]{64}", runtime.name)
        is None
    ):
        return False
    source_root = runtime / "backend/src/agentmonitor"
    return (
        collection_path == source_root / "composition/ollama_usage_collection.py"
        and Path(source.__file__).resolve()
        == source_root / "adapters/providers/ollama/api/source.py"
    )


def main() -> int:
    from agentmonitor.composition.worker_start_authority import (
        consume_worker_start_authority_v1,
    )

    if len(sys.argv) != 4 or not consume_worker_start_authority_v1(sys.argv[2]):
        return 5
    root = Path(sys.argv[1])
    revision = sys.argv[3]
    if (
        not root.is_absolute()
        or root in {Path("/"), Path.home()}
        or len(revision) != 40
        or any(c not in "0123456789abcdef" for c in revision)
    ):
        return 2
    if not _sealed_runtime(root, revision):
        return 6
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    watchdog = threading.Timer(120, lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    witness: dict[str, object] = dict(
        schema="m7-native-usage-comparison-v1",
        composition="alternate_real_test_worker",
        revision=revision,
        state="not_run",
        reason="native_comparison_no_due_context",
        requests=0,
        matched_days=0,
    )
    try:
        _run(root, witness)
    except Exception:
        # Never serialize exception text, source payloads or credentials.
        witness.update(state="not_run", reason="native_comparison_execution_unresolved")
    finally:
        watchdog.cancel()
    print(json.dumps(witness, sort_keys=True), flush=True)
    return 0 if witness["state"] == "matched" and "report_id" in witness else 3


if __name__ == "__main__":
    raise SystemExit(main())
