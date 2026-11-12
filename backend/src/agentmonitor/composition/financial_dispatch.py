"""Merge current source inventory with persisted queue/schedule ages."""

from datetime import UTC, datetime

from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
    SOURCE_ID as ANTHROPIC_SOURCE,
)
from agentmonitor.adapters.providers.codex.openai_api.policy import (
    SOURCE_ID as OPENAI_SOURCE,
)
from agentmonitor.adapters.providers.ollama.api.policy import SOURCE_ID as OLLAMA_SOURCE
from agentmonitor.composition.billing_context import billing_cost_operation_families
from agentmonitor.composition.billing_run import (
    ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
    anthropic_billing_budget_scope_digest,
    anthropic_cost_manifest_fingerprint,
)
from agentmonitor.composition.billing_schedule import (
    BillingScheduleIntentV1,
    BillingScheduleV1,
)
from agentmonitor.composition.budget_dispatch import BudgetWorkV1, ordered_budget_work
from agentmonitor.composition.ollama_usage_run import (
    POLICY_VERSION,
    usage_manifest_fingerprint,
)
from agentmonitor.composition.openai_billing_run import (
    OPENAI_COST_COLLECTION_POLICY_VERSION_V1,
    openai_billing_budget_scope_digest,
    openai_cost_manifest_fingerprint,
)
from agentmonitor.contracts.collection_control_v1 import (
    CloudBudgetCollectionRunAdmissionV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

Key = tuple[str, str, str]


def prepare_financial_dispatch(
    runs: SqliteCollectionRepositoryV1,
    scheduler: BillingScheduleV1,
    cloud_runs: tuple[CloudBudgetCollectionRunAdmissionV1, ...],
    *,
    deadline_monotonic: float,
) -> tuple[
    tuple[BudgetWorkV1, ...],
    dict[Key, BillingScheduleIntentV1],
    dict[Key, CloudBudgetCollectionRunAdmissionV1],
]:
    """One bounded inventory, then one metadata snapshot per admitted source.

    Queued work wins only within its source budget/operation. Across keys, actual
    prior service age governs both automatic and owner-requested work.
    """
    targets = scheduler.read_targets(deadline_monotonic=deadline_monotonic)
    now = datetime.now(UTC)
    intents = scheduler.due_intents(targets, as_of=now)
    # Canonical budget identity is shared by manual and scheduled paths.
    billing_keys: dict[tuple[OpaqueIdV1, str], Key] = {}
    keys: set[Key] = set()
    key: Key
    for target in targets:
        provider = target.connection.provider_key
        service = scheduler.service_target(target)
        scope = (
            anthropic_billing_budget_scope_digest
            if provider == "claude"
            else openai_billing_budget_scope_digest
        )(target, ProviderTargetRefV1("cloud_service", service.access_target_id))
        for operation in billing_cost_operation_families(provider):
            key = (provider, scope, operation)
            keys.add(key)
            billing_keys[
                target.connection.resource_id, operation.rsplit(".", 1)[-1]
            ] = key
    billing_due: dict[Key, BillingScheduleIntentV1] = {}
    for intent in intents:
        key = billing_keys[
            intent.target.connection.resource_id, intent.report_context.range_key
        ]
        billing_due.setdefault(key, intent)
    usage_due: dict[Key, CloudBudgetCollectionRunAdmissionV1] = {}
    for run in cloud_runs:
        key = ("ollama", run.budget_scope_digest, run.operation_family)
        keys.add(key)
        if run.report_context.scope == "self":
            usage_due.setdefault(key, run)
    selected: list[BudgetWorkV1] = []
    for provider, capability, source, fingerprint, policy in (
        (
            "claude",
            "api.cost",
            ANTHROPIC_SOURCE,
            anthropic_cost_manifest_fingerprint(),
            ANTHROPIC_COST_COLLECTION_POLICY_VERSION_V1,
        ),
        (
            "codex",
            "api.cost",
            OPENAI_SOURCE,
            openai_cost_manifest_fingerprint(),
            OPENAI_COST_COLLECTION_POLICY_VERSION_V1,
        ),
        (
            "ollama",
            "api.usage",
            OLLAMA_SOURCE,
            usage_manifest_fingerprint(),
            POLICY_VERSION,
        ),
    ):
        source_keys = sorted(key for key in keys if key[0] == provider)
        if not source_keys:
            continue
        snapshot = runs.read_budget_dispatch_snapshot(
            provider_key=provider,
            capability_id=capability,
            source_id=source,
            manifest_fingerprint=fingerprint,
            collection_policy_version=policy,
            operation_families=tuple(sorted({key[2] for key in source_keys})),
            budget_scope_digests=tuple(sorted({key[1] for key in source_keys})),
            schedule_ids=tuple(
                sorted(
                    {
                        run.schedule_id
                        for key, run in usage_due.items()
                        if key[0] == provider
                    },
                    key=lambda item: item.value,
                )
            ),
            as_of=datetime.now(UTC),
        )
        states = {
            (item.budget_scope_digest, item.operation_family): item
            for item in snapshot.states
        }
        schedules = {item.schedule_id: item for item in snapshot.schedules}
        for key in source_keys:
            state = states.get((key[1], key[2]))
            queued = None if state is None else state.queued_run_id
            due_at: datetime | None = None
            if key in billing_due:
                due_at = billing_due[key].due_at
            elif key in usage_due:
                timing = schedules.get(usage_due[key].schedule_id)
                if timing is not None and not timing.has_active_lease:
                    ready = max(
                        timing.next_due_at, timing.not_before_at or timing.next_due_at
                    )
                    if ready <= datetime.now(UTC):
                        due_at = ready
            if (
                due_at is not None
                and runs.get_budget_next_allowed_at(
                    key[1], "request", "count", datetime.now(UTC)
                )
                is not None
            ):
                due_at = None
            ready_times = tuple(
                value
                for value in (
                    due_at,
                    None if state is None else state.queued_requested_at,
                )
                if value is not None
            )
            if not ready_times:
                continue
            selected.append(
                BudgetWorkV1(
                    key,
                    None if state is None else state.last_started_at,
                    min(ready_times),
                    queued,
                    due_at is not None,
                )
            )
    return ordered_budget_work(tuple(selected)), billing_due, usage_due
