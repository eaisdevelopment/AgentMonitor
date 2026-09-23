"""Side-effect-free M04 cadence and outcome policies."""

from dataclasses import dataclass
from typing import Literal

ActivityClassV1 = Literal["active", "idle", "unknown"]
RetryKindV1 = Literal[
    "normal_cadence",
    "delayed_retry",
    "auth_block",
    "authorization_block",
    "user_action_block",
    "compatibility_block",
    "unsupported",
    "no_retry",
]


class CollectionPolicyErrorV1(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class CollectionCadencePolicyV1:
    active_interval_seconds: int
    idle_interval_seconds: int

    def __post_init__(self) -> None:
        if (
            type(self.active_interval_seconds) is not int
            or type(self.idle_interval_seconds) is not int
            or self.active_interval_seconds < 1
            or self.idle_interval_seconds < self.active_interval_seconds
        ):
            raise CollectionPolicyErrorV1("collection_cadence_policy_invalid")


@dataclass(frozen=True, slots=True)
class RetryDecisionV1:
    kind: RetryKindV1
    delay_seconds: int | None = None


def effective_interval_seconds(
    activity: ActivityClassV1,
    source_minimum_seconds: int | None,
    policy: CollectionCadencePolicyV1,
) -> int:
    if activity not in {"active", "idle", "unknown"}:
        raise CollectionPolicyErrorV1("collection_activity_invalid")
    if source_minimum_seconds is None:
        raise CollectionPolicyErrorV1("collection_constraints_unknown")
    if type(source_minimum_seconds) is not int or source_minimum_seconds < 0:
        raise CollectionPolicyErrorV1("collection_source_minimum_invalid")
    base = (
        policy.active_interval_seconds
        if activity == "active"
        else policy.idle_interval_seconds
    )
    return max(base, source_minimum_seconds)


def decide_retry(outcome: str, delay_seconds: int | None) -> RetryDecisionV1:
    if outcome in {"success", "partial"}:
        decision = RetryDecisionV1("normal_cadence")
    elif outcome == "rate_limited":
        if type(delay_seconds) is not int or delay_seconds < 1:
            raise CollectionPolicyErrorV1("collection_retry_delay_required")
        decision = RetryDecisionV1("delayed_retry", delay_seconds)
    elif outcome in {"provider_unavailable", "deadline_exceeded"}:
        if delay_seconds is None:
            decision = RetryDecisionV1("no_retry")
        elif type(delay_seconds) is int and delay_seconds >= 1:
            decision = RetryDecisionV1("delayed_retry", delay_seconds)
        else:
            raise CollectionPolicyErrorV1("collection_retry_delay_invalid")
    elif outcome == "reauthentication_required":
        decision = RetryDecisionV1("auth_block")
    elif outcome == "authorization_insufficient":
        decision = RetryDecisionV1("authorization_block")
    elif outcome == "blocked_user_action_required":
        decision = RetryDecisionV1("user_action_block")
    elif outcome in {"unverified_provider_version", "invalid_provider_data"}:
        decision = RetryDecisionV1("compatibility_block")
    elif outcome == "unsupported":
        decision = RetryDecisionV1("unsupported")
    elif outcome == "internal_adapter_error":
        decision = RetryDecisionV1("no_retry")
    else:
        raise CollectionPolicyErrorV1("collection_outcome_unknown")
    return decision
