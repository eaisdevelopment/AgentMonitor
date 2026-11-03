"""Pure recovery decisions over exact, terminal M04 run evidence."""

from agentmonitor.contracts.collection_recovery_v1 import (
    CollectionRecoveryRunV1,
    CollectionRecoveryScopeV1,
)


def _matches(run: CollectionRecoveryRunV1, scope: CollectionRecoveryScopeV1) -> bool:
    return (
        run.provider_key == scope.provider_key
        and run.provider_target_kind == "cloud_service"
        and run.account_id == scope.account_id
        and run.access_target_id == scope.access_target_id
        and run.binding_generation == scope.binding_generation
        and run.capability_id == scope.capability_id
        and run.source_id == scope.source_id
        and run.adapter_version == scope.adapter_version
        and run.source_fingerprint == scope.source_fingerprint
        and run.payload_schema == scope.payload_schema
    )


def latest_natural_failure(
    runs: tuple[CollectionRecoveryRunV1, ...], scope: CollectionRecoveryScopeV1
) -> CollectionRecoveryRunV1 | None:
    """Require a current, received provider failure; local faults do not qualify."""
    matching = [run for run in runs if _matches(run, scope)]
    if not matching:
        return None
    latest = max(matching, key=lambda run: (run.requested_at, run.run_id.value))
    if (
        latest.state == "failed"
        and latest.dispatch_certainty == "response_received"
        and (
            latest.response_outcome == "failed"
            and latest.failure_code in {"unauthorized", "access_denied"}
            or latest.response_outcome == "rate_limited"
            and latest.failure_code == "rate_limited"
        )
    ):
        return latest
    return None


def committed_recovery_after(
    runs: tuple[CollectionRecoveryRunV1, ...],
    failure: CollectionRecoveryRunV1,
    scope: CollectionRecoveryScopeV1,
) -> CollectionRecoveryRunV1 | None:
    """Return a later committed response only for the same failed scope."""
    if latest_natural_failure((failure,), scope) is None:
        return None
    matches = [
        run
        for run in runs
        if (_matches(run, scope) and run.requested_at > failure.completed_at)
    ]
    if not matches:
        return None
    latest = max(matches, key=lambda run: (run.requested_at, run.run_id.value))
    if (
        latest.state in {"succeeded", "partial"}
        and latest.dispatch_certainty == "response_received"
        and latest.response_outcome == "succeeded"
        and latest.failure_code is None
        and latest.payload_digest is not None
        and bool(latest.observation_ids)
    ):
        return latest
    return None
