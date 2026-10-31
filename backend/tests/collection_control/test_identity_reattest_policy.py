"""Pure policy for reusing a persisted current quota run after restart."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.providers.claude.manifest import CLAUDE_USAGE_SOURCE_ID
from agentmonitor.contracts.collection_control_v1 import CollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.domain.identity_attestation import (
    eligible_run_for_readonly_reattest_v1,
)


def _run(now: datetime) -> CollectionRunViewV1:
    requested = now - timedelta(minutes=2)
    return CollectionRunViewV1(
        run_id=OpaqueIdV1("quota-run-1"),
        schedule_id=OpaqueIdV1("quota-schedule-1"),
        provider_key="claude",
        account_id=OpaqueIdV1("account-1"),
        resource_id=OpaqueIdV1("resource-1"),
        capability_id="subscription.quota",
        state="succeeded",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        adapter_version="1.0.0",
        provider_version="2.1.283",
        target_generation=1,
        fencing_token=1,
        requested_at=requested,
        started_at=requested,
        completed_at=requested + timedelta(seconds=2),
        deadline_at=requested + timedelta(seconds=30),
        duration_ms=2000,
        payload_digest="a" * 64,
        outcome_code="succeeded",
        error_code=None,
        observation_ids=(OpaqueIdV1("observation-1"),),
    )


def test_only_current_successful_exact_account_resource_run_can_be_reattested() -> None:
    now = datetime(2026, 9, 29, 13, 0, tzinfo=UTC)
    run = _run(now)
    check = eligible_run_for_readonly_reattest_v1
    assert check(
        run,
        account_id=OpaqueIdV1("account-1"),
        resource_id=OpaqueIdV1("resource-1"),
        provider_key="claude",
        capability_id="subscription.quota",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        as_of=now,
        is_due=False,
    )
    assert run.completed_at is not None
    assert not check(
        run,
        account_id=OpaqueIdV1("another-account"),
        resource_id=OpaqueIdV1("resource-1"),
        provider_key="claude",
        capability_id="subscription.quota",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        as_of=now,
        is_due=False,
    )
    assert not check(
        run,
        account_id=OpaqueIdV1("account-1"),
        resource_id=OpaqueIdV1("another-resource"),
        provider_key="claude",
        capability_id="subscription.quota",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        as_of=now,
        is_due=False,
    )
    assert not check(
        run,
        account_id=OpaqueIdV1("account-1"),
        resource_id=OpaqueIdV1("resource-1"),
        provider_key="claude",
        capability_id="subscription.quota",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        as_of=now,
        is_due=True,
    )
    assert not check(
        replace(run, state="partial", outcome_code="partial"),
        account_id=OpaqueIdV1("account-1"),
        resource_id=OpaqueIdV1("resource-1"),
        provider_key="claude",
        capability_id="subscription.quota",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        as_of=now,
        is_due=False,
    )
    assert not check(
        run,
        account_id=OpaqueIdV1("account-1"),
        resource_id=OpaqueIdV1("resource-1"),
        provider_key="claude",
        capability_id="subscription.quota",
        source_id=CLAUDE_USAGE_SOURCE_ID,
        as_of=run.completed_at - timedelta(seconds=1),
        is_due=False,
    )
