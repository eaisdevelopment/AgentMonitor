"""Construct the M05-owned financial export codec for operations composition."""

from agentmonitor.contracts.capacity_retention_v1 import BudgetRetentionRecordCodecV1
from agentmonitor.modules.capacity.domain.budget_retention_codec import (
    BudgetRetentionCodecV1,
)


def build_budget_retention_codec() -> BudgetRetentionRecordCodecV1:
    return BudgetRetentionCodecV1()
