"""Compatibility function for the contract-owned canonical payload digest."""

from agentmonitor.contracts.runtime_observation_v1 import RuntimeObservationBatchV1


def runtime_payload_digest(payload: RuntimeObservationBatchV1) -> str:
    """Return the batch value object's single canonical digest."""
    return payload.canonical_digest()


__all__ = ["runtime_payload_digest"]
