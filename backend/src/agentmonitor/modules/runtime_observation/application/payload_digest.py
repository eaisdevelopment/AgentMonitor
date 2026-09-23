"""Canonical M06 payload digest used by the collection commit seam."""

import hashlib
import json

from agentmonitor.contracts.runtime_observation_v1 import RuntimeObservationBatchV1


def runtime_payload_digest(payload: RuntimeObservationBatchV1) -> str:
    """Digest the complete closed runtime batch without platform/provider I/O."""
    document = {
        "completeness": payload.completeness,
        "omission_codes": list(payload.omission_codes),
        "process_snapshots": [
            {
                "observation_id": item.observation_id,
                "identity": {
                    "platform_source": item.identity.platform_source,
                    "platform_scope_id": item.identity.platform_scope_id,
                    "pid": item.identity.pid,
                    "start_time_ticks": item.identity.start_time_ticks,
                },
                "provider_key": item.provider_key,
                "installation_id": item.installation_id,
                "executable_label": [
                    item.executable_label.state,
                    item.executable_label.value,
                    item.executable_label.reason_code,
                ],
                "parent_pid": [
                    item.parent_pid.state,
                    item.parent_pid.value,
                    item.parent_pid.unit,
                    item.parent_pid.reason_code,
                ],
                "user_cpu_ticks": [
                    item.user_cpu_ticks.state,
                    item.user_cpu_ticks.value,
                    item.user_cpu_ticks.unit,
                    item.user_cpu_ticks.reason_code,
                ],
                "system_cpu_ticks": [
                    item.system_cpu_ticks.state,
                    item.system_cpu_ticks.value,
                    item.system_cpu_ticks.unit,
                    item.system_cpu_ticks.reason_code,
                ],
                "resident_pages": [
                    item.resident_pages.state,
                    item.resident_pages.value,
                    item.resident_pages.unit,
                    item.resident_pages.reason_code,
                ],
                "thread_count": [
                    item.thread_count.state,
                    item.thread_count.value,
                    item.thread_count.unit,
                    item.thread_count.reason_code,
                ],
                "kernel_state": [
                    item.kernel_state.state,
                    item.kernel_state.value,
                    item.kernel_state.reason_code,
                ],
                "observed_at": item.observed_at.isoformat(),
                "source_id": item.source_id,
                "source_version": item.source_version,
                "adapter_version": item.adapter_version,
                "clock_ticks_per_second": item.clock_ticks_per_second,
                "page_size_bytes": item.page_size_bytes,
                "presence": item.presence,
            }
            for item in payload.process_snapshots
        ],
        "session_observations": [
            {
                "observation_id": item.observation_id,
                "identity": [
                    item.session_identity.provider_key,
                    item.session_identity.installation_id,
                    item.session_identity.identity_kind,
                    item.session_identity.identity_value,
                ],
                "observed_at": item.observed_at.isoformat(),
                "source_id": item.source_id,
                "source_version": item.source_version,
                "parser_version": item.parser_version,
                "provider_version": item.provider_version,
                "activity_state": item.activity_state,
                "activity_code": item.activity_code,
                "activity_reason_code": item.activity_reason_code,
            }
            for item in payload.session_observations
        ],
        "metric_observations": [
            {
                "metric_id": item.metric_id,
                "session_identity": [
                    item.session_identity.provider_key,
                    item.session_identity.installation_id,
                    item.session_identity.identity_kind,
                    item.session_identity.identity_value,
                ],
                "process_identity": (
                    [
                        item.process_identity.platform_source,
                        item.process_identity.platform_scope_id,
                        item.process_identity.pid,
                        item.process_identity.start_time_ticks,
                    ]
                    if item.process_identity is not None
                    else None
                ),
                "metric_kind": item.metric_kind,
                "coefficient": item.coefficient,
                "scale": item.scale,
                "unit": item.unit,
                "scope": item.scope,
                "semantics": item.semantics,
                "overlap_class": item.overlap_class,
                "interval_start": item.interval_start.isoformat()
                if item.interval_start is not None
                else None,
                "interval_end": item.interval_end.isoformat()
                if item.interval_end is not None
                else None,
                "observed_at": item.observed_at.isoformat(),
                "source_id": item.source_id,
                "source_version": item.source_version,
                "parser_version": item.parser_version,
                "provider_version": item.provider_version,
            }
            for item in payload.metric_observations
        ],
        "correlation_evidence": [
            {
                "evidence_id": item.evidence_id,
                "identity": [
                    item.session_identity.provider_key,
                    item.session_identity.installation_id,
                    item.session_identity.identity_kind,
                    item.session_identity.identity_value,
                ],
                "evidence_class": item.evidence_class,
                "rule_id": item.rule_id,
                "account_id": item.account_id,
                "observed_at": item.observed_at.isoformat(),
                "source_id": item.source_id,
                "source_version": item.source_version,
                "reason_code": item.reason_code,
            }
            for item in payload.correlation_evidence
        ],
    }
    canonical = json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
