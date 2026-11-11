"""Pure classification of usage failures proven to precede HTTP dispatch."""

from datetime import datetime

from agentmonitor.adapters.providers.ollama.api.source import OllamaUsageResultV1
from agentmonitor.contracts.collection_control_v1 import (
    OllamaCloudNoResponseCompletionV2,
    OllamaCloudRequestLeaseV1,
)


def usage_no_response_terminal(
    result: OllamaUsageResultV1,
    lease: OllamaCloudRequestLeaseV1,
    *,
    completed_at: datetime,
) -> OllamaCloudNoResponseCompletionV2 | None:
    """Never turn an absent response or attempted count into no-request proof.

    A03 authorization failures occur before endheaders. Its worker/deadline
    checks before _fetch have zero attempts; later timeout/transport/parser
    failures may have sent a request and must retain uncertainty.
    """
    if (
        type(result) is not OllamaUsageResultV1
        or result.report is not None
        or result.http_status is not None
        or result.retry_after_seconds is not None
        or result.money_availability is not None
        or type(result.requests_made) is not int
        or result.requests_made not in {0, 1}
        or result.reason_code != "ollama_usage_" + result.state
    ):
        return None
    if result.state == "authorization_unavailable":
        return OllamaCloudNoResponseCompletionV2(
            lease.admission_id,
            lease.scheduler_instance_id,
            lease.schedule_id,
            lease.fencing_token,
            lease.started_at,
            completed_at,
            "store_unavailable",
            "authorization_unavailable",
        )
    if result.requests_made == 0 and result.state in {
        "worker_required",
        "deadline_exceeded",
    }:
        return OllamaCloudNoResponseCompletionV2(
            lease.admission_id,
            lease.scheduler_instance_id,
            lease.schedule_id,
            lease.fencing_token,
            lease.started_at,
            completed_at,
            "source_not_started",
            "internal_adapter_error"
            if result.state == "worker_required"
            else "deadline_exceeded",
        )
    return None
