"""Pure eligibility for read-only current identity re-attestation."""

from datetime import datetime, timedelta

from agentmonitor.contracts.collection_control_v1 import CollectionRunViewV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def eligible_run_for_readonly_reattest_v1(
    latest: CollectionRunViewV1 | None,
    *,
    account_id: OpaqueIdV1,
    resource_id: OpaqueIdV1,
    provider_key: str,
    capability_id: str,
    source_id: str,
    as_of: datetime,
    is_due: bool,
) -> bool:
    """Require an exact, still-current, observation-bearing successful run.

    Identity matching is a separate registry-owned check. This function does
    not turn a historical run into a new quota observation or reset cadence.
    """
    return bool(
        latest is not None
        and type(is_due) is bool
        and not is_due
        and as_of.utcoffset() == timedelta(0)
        and latest.provider_key == provider_key
        and latest.capability_id == capability_id
        and latest.source_id == source_id
        and latest.account_id == account_id
        and latest.resource_id == resource_id
        and latest.state == "succeeded"
        and latest.completed_at is not None
        and latest.completed_at <= as_of
        and bool(latest.observation_ids)
    )
