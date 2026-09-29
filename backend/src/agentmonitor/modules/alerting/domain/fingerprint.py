"""Canonical condition identity; never includes owner identity or metric content."""

import hashlib
import json
from dataclasses import dataclass

from agentmonitor.contracts.alerting_v1 import AlertConditionTypeV1, AlertSubjectV1


@dataclass(frozen=True, slots=True)
class AlertFingerprintV1:
    version: int
    digest: str
    canonical_material: str


def fingerprint_alert_condition(
    condition_type: AlertConditionTypeV1,
    subject: AlertSubjectV1,
    condition_semantic_major: int,
) -> AlertFingerprintV1:
    if type(condition_semantic_major) is not int or condition_semantic_major != 1:
        raise ValueError("alert_condition_semantic_major_unsupported")
    material = json.dumps(
        {
            "version": 1,
            "condition_type": condition_type,
            "subject_kind": subject.subject_kind,
            "subject_id": subject.subject_id.value,
            "dimension_kind": subject.dimension_kind,
            "dimension_id": subject.dimension_id,
            "condition_semantic_major": condition_semantic_major,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return AlertFingerprintV1(
        1, hashlib.sha256(material.encode("ascii")).hexdigest(), material
    )
