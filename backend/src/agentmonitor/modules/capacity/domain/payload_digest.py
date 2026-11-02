"""Canonical M05 quota-payload digest with no provider or I/O dependency."""

import hashlib
import json

from agentmonitor.contracts.capacity_v1 import (
    CapacitySubjectV2,
    ExactMetricFieldV1,
    ProviderQuotaInputV1,
    ProviderQuotaInputV2,
)


def _field(field: ExactMetricFieldV1) -> dict[str, object]:
    value = field.value
    return {
        "availability": field.availability.state,
        "coefficient": value.amount.coefficient if value is not None else None,
        "scale": value.amount.scale if value is not None else None,
        "unit": value.unit if value is not None else None,
        "precision": field.precision,
        "confidence": field.confidence,
        "value_kind": field.value_kind,
        "reason_code": field.reason_code,
    }


def capacity_payload_digest(
    payload: ProviderQuotaInputV1 | ProviderQuotaInputV2,
) -> str:
    """Hash the complete closed payload; caller-supplied digests are never trusted."""
    subject_target = (
        {
            "target_kind": payload.subject.provider_target.target_kind,
            "target_id": payload.subject.provider_target.target_id.value,
        }
        if isinstance(payload.subject, CapacitySubjectV2)
        else {"installation_id": payload.subject.installation_id.value}
    )
    document = {
        "subject": {
            "provider_key": payload.subject.provider_key,
            **subject_target,
            "account_id": payload.subject.account_id.value,
            "resource_id": payload.subject.resource_id.value,
        },
        "registry_revision": payload.registry_revision,
        "capability_schema_version": payload.capability_schema_version,
        "completeness": payload.completeness,
        "omission_codes": list(payload.omission_codes),
        "windows": [
            {
                "window_key": window.window_key,
                "safe_label": window.safe_label,
                "semantic_role": window.semantic_role,
                "is_constraining": window.is_constraining,
                "used": _field(window.used),
                "remaining": _field(window.remaining),
                "limit": _field(window.limit),
                "remaining_ratio": _field(window.remaining_ratio),
                "reset_at": (
                    window.reset_at.isoformat(timespec="microseconds")
                    if window.reset_at is not None
                    else None
                ),
                "reset_precision": window.reset_precision,
                **(
                    {
                        "source_period_start": window.source_period_start.isoformat(
                            timespec="microseconds"
                        )
                    }
                    if window.source_period_start is not None
                    else {}
                ),
            }
            for window in sorted(payload.windows, key=lambda item: item.window_key)
        ],
    }
    encoded = json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
