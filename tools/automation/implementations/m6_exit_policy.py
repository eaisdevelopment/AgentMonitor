"""Pure, closed technical-evidence policy for the V1-M6 exit gate."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast

StatusV1 = Literal["passed", "failed", "blocked", "not_run"]

ACCEPTANCE_IDS = tuple(f"M6-A{index:02}" for index in range(1, 11))
STORY_IDS = tuple(f"ST-OLL-{index:03}" for index in range(1, 6))
ALL_SCOPE_IDS = (*ACCEPTANCE_IDS, *STORY_IDS)
SELF_COMPLETION_SCOPE_ID = "M6-A10"
REQUIRED_CHECKS = (
    "AUTO-BUILD",
    "AUTO-M6-LOCAL-ADMIT",
    "AUTO-QUALITY",
    "AUTO-DOCS-CHECK",
    "AUTO-PLAN-CHECK",
)
SELECTOR_REQUIREMENTS = (
    (
        "M6-A01",
        "M6-SEL-A01",
        "registry_account_admin",
        "AUTO-M6-EVIDENCE-A01",
        (),
        "M6-SELECTION-A01-V1",
        "M6-SOURCE-VERSIONS-A01-V1",
    ),
    (
        "M6-A02",
        "M6-SEL-A02",
        "local_service_model_hosts",
        "AUTO-M6-EVIDENCE-A02",
        (),
        "M6-SELECTION-A02-V1",
        "M6-SOURCE-VERSIONS-A02-V1",
    ),
    (
        "M6-A03",
        "M6-SEL-A03",
        "cloud_identity_scope",
        "AUTO-M6-EVIDENCE-A03",
        (),
        "M6-SELECTION-A03-V1",
        "M6-SOURCE-VERSIONS-A03-V1",
    ),
    (
        "M6-A04",
        "M6-SEL-A04",
        "cloud_balance_reconciliation",
        "AUTO-M6-EVIDENCE-A04",
        (),
        "M6-SELECTION-A04-V1",
        "M6-SOURCE-VERSIONS-A04-V1",
    ),
    (
        "M6-A05",
        "M6-SEL-A05",
        "capacity_history_alert_lineage",
        "AUTO-M6-EVIDENCE-A05",
        (),
        "M6-SELECTION-A05-V1",
        "M6-SOURCE-VERSIONS-A05-V1",
    ),
    (
        "M6-A06",
        "M6-SEL-A06",
        "process_model_relationships",
        "AUTO-M6-EVIDENCE-A06",
        ("sampled_process_coverage",),
        "M6-SELECTION-A06-V1",
        "M6-SOURCE-VERSIONS-A06-V1",
    ),
    (
        "M6-A07",
        "M6-SEL-A07",
        "natural_failure_recovery",
        "AUTO-M6-EVIDENCE-A07",
        (),
        "M6-SELECTION-A07-V1",
        "M6-SOURCE-VERSIONS-A07-V1",
    ),
    (
        "M6-A08",
        "M6-SEL-A08",
        "built_browser_accessibility",
        "AUTO-M6-EVIDENCE-A08",
        (),
        "M6-SELECTION-A08-V1",
        "M6-SOURCE-VERSIONS-A08-V1",
    ),
    (
        "M6-A09",
        "M6-SEL-A09",
        "security_privacy_source_limits",
        "AUTO-M6-EVIDENCE-A09",
        (),
        "M6-SELECTION-A09-V1",
        "M6-SOURCE-VERSIONS-A09-V1",
    ),
    (
        "ST-OLL-001",
        "M6-SEL-ST-OLL-001",
        "provider_admission_installation",
        "AUTO-M6-EVIDENCE-ST-OLL-001",
        (),
        "M6-SELECTION-ST-OLL-001-V1",
        "M6-SOURCE-VERSIONS-ST-OLL-001-V1",
    ),
    (
        "ST-OLL-002",
        "M6-SEL-ST-OLL-002",
        "local_model_runtime",
        "AUTO-M6-EVIDENCE-ST-OLL-002",
        (),
        "M6-SELECTION-ST-OLL-002-V1",
        "M6-SOURCE-VERSIONS-ST-OLL-002-V1",
    ),
    (
        "ST-OLL-003",
        "M6-SEL-ST-OLL-003",
        "cloud_identity_authentication",
        "AUTO-M6-EVIDENCE-ST-OLL-003",
        (),
        "M6-SELECTION-ST-OLL-003-V1",
        "M6-SOURCE-VERSIONS-ST-OLL-003-V1",
    ),
    (
        "ST-OLL-004",
        "M6-SEL-ST-OLL-004",
        "cloud_subscription_capacity",
        "AUTO-M6-EVIDENCE-ST-OLL-004",
        (),
        "M6-SELECTION-ST-OLL-004-V1",
        "M6-SOURCE-VERSIONS-ST-OLL-004-V1",
    ),
    (
        "ST-OLL-005",
        "M6-SEL-ST-OLL-005",
        "integrated_runtime_dashboard_closure",
        "AUTO-M6-EVIDENCE-ST-OLL-005",
        ("sampled_process_coverage",),
        "M6-SELECTION-ST-OLL-005-V1",
        "M6-SOURCE-VERSIONS-ST-OLL-005-V1",
    ),
)
EXTERNAL_SELECTOR_SCOPE_IDS = tuple(item[0] for item in SELECTOR_REQUIREMENTS)

_STATUS_VALUES = frozenset(("passed", "failed", "blocked", "not_run"))
_CATALOG_KEYS = frozenset(
    (
        "schema_version",
        "record_type",
        "milestone_id",
        "acceptance_ids",
        "story_ids",
        "required_checks",
        "selectors",
    )
)
_BUNDLE_KEYS = frozenset(
    (
        "schema_version",
        "record_type",
        "milestone_id",
        "implementation_revision",
        "catalog_sha256",
        "selection_sha256",
        "source_versions_sha256",
        "recorded_at",
        "acceptance",
        "stories",
        "evidence",
        "declared_limitations",
    )
)
_OUTCOME_KEYS = frozenset(("id", "status", "reason_code", "evidence_ids"))
_EVIDENCE_KEYS = frozenset(
    (
        "evidence_id",
        "path",
        "sha256",
        "scope_ids",
        "result",
        "producer_id",
        "producer_version",
        "exit_code",
        "test_count",
        "skip_count",
        "implementation_revision",
        "observed_at",
        "valid_until",
    )
)
_SELECTOR_KEYS = frozenset(
    (
        "schema_version",
        "record_type",
        "selector_id",
        "boundary",
        "selection_policy_id",
        "source_versions_policy_id",
        "selection_sha256",
        "source_versions_sha256",
        "evidence",
        "reason_code",
        "declared_limitations",
    )
)
_SELECTOR_CATALOG_KEYS = frozenset(
    (
        "scope_id",
        "selector_id",
        "boundary",
        "producer_command_id",
        "producer_version",
        "selection_policy_id",
        "source_versions_policy_id",
        "selection_sha256",
        "source_versions_sha256",
        "required_limitations",
    )
)
_RECEIPT_KEYS = frozenset(
    (
        "schema_version",
        "record_type",
        "milestone_id",
        "command_id",
        "command",
        "implementation_revision",
        "completed_at",
        "status",
        "exit_code",
        "technical_acceptance_count",
        "pending_acceptance_ids",
        "story_count",
        "evidence_count",
        "catalog_sha256",
        "selector_receipts_sha256",
        "selection_sha256",
        "source_versions_sha256",
        "required_checks",
        "declared_limitations",
    )
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,95}\Z")
_SAFE_ID = re.compile(r"[A-Z][A-Z0-9_.:-]{0,127}\Z")
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
_SAFE_PATH = re.compile(r"[A-Za-z0-9_./-]{1,240}\Z")


@dataclass(frozen=True, slots=True)
class M6EvidenceEvaluationV1:
    """Sanitized result of evaluating one closed completion-evidence bundle."""

    overall_status: StatusV1
    acceptance: Mapping[str, StatusV1]
    stories: Mapping[str, StatusV1]
    reason_codes: tuple[str, ...]
    evidence_count: int
    declared_limitations: tuple[str, ...]
    selection_sha256: str | None
    source_versions_sha256: str | None


def _is_utc(value: datetime) -> bool:
    offset = value.utcoffset()
    return offset is not None and offset.total_seconds() == 0


def _utc_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if not _is_utc(parsed):
        return None
    return parsed.astimezone(UTC)


def _safe_codes(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or len(value) > 64:
        return None
    if any(
        not isinstance(item, str) or _SAFE_CODE.fullmatch(item) is None
        for item in value
    ):
        return None
    if len(set(value)) != len(value):
        return None
    return tuple(value)


def _status_summary(values: tuple[StatusV1, ...]) -> StatusV1:
    if "failed" in values:
        return "failed"
    if "blocked" in values:
        return "blocked"
    if "not_run" in values or not values:
        return "not_run"
    return "passed"


def validate_catalog_v1(catalog: object) -> tuple[str, ...]:
    """Validate the exact versioned M6 requirement/check catalog."""

    errors: list[str] = []
    if not isinstance(catalog, dict) or set(catalog) != _CATALOG_KEYS:
        return ("m6_catalog_shape_invalid",)
    if (
        catalog.get("schema_version") != "1.0.0"
        or catalog.get("record_type") != "agentmonitor.m6_exit_catalog.v1"
        or catalog.get("milestone_id") != "V1-M6"
    ):
        errors.append("m6_catalog_header_invalid")
    if catalog.get("acceptance_ids") != list(ACCEPTANCE_IDS):
        errors.append("m6_catalog_acceptance_invalid")
    if catalog.get("story_ids") != list(STORY_IDS):
        errors.append("m6_catalog_stories_invalid")
    if catalog.get("required_checks") != list(REQUIRED_CHECKS):
        errors.append("m6_catalog_checks_invalid")
    selectors = catalog.get("selectors")
    if not isinstance(selectors, list) or len(selectors) != len(SELECTOR_REQUIREMENTS):
        errors.append("m6_catalog_selectors_invalid")
        return tuple(errors)
    for raw, requirement in zip(selectors, SELECTOR_REQUIREMENTS, strict=True):
        (
            scope_id,
            selector_id,
            boundary,
            producer_command_id,
            required_limitations,
            selection_policy_id,
            source_versions_policy_id,
        ) = requirement
        if not isinstance(raw, dict) or set(raw) != _SELECTOR_CATALOG_KEYS:
            errors.append("m6_catalog_selectors_invalid")
            continue
        fixed = {
            "scope_id": scope_id,
            "selector_id": selector_id,
            "boundary": boundary,
            "producer_command_id": producer_command_id,
            "producer_version": "1.0.0",
            "selection_policy_id": selection_policy_id,
            "source_versions_policy_id": source_versions_policy_id,
            "required_limitations": list(required_limitations),
        }
        if any(raw.get(key) != value for key, value in fixed.items()):
            errors.append("m6_catalog_selectors_invalid")
        for field in ("selection_sha256", "source_versions_sha256"):
            value = raw.get(field)
            if value is not None and (
                not isinstance(value, str) or _SHA256.fullmatch(value) is None
            ):
                errors.append("m6_catalog_selector_digest_invalid")
    return tuple(errors)


def assemble_selector_bundle_v1(
    selector_receipts: tuple[object, ...],
    *,
    catalog: object,
    producer_statuses: Mapping[str, StatusV1],
    expected_revision: str,
    catalog_sha256: str,
    recorded_at: datetime,
) -> dict[str, object]:
    """Assemble fixed machine receipts; missing scopes remain explicitly Not Run."""

    if (
        _REVISION.fullmatch(expected_revision) is None
        or _SHA256.fullmatch(catalog_sha256) is None
        or not _is_utc(recorded_at)
        or len(selector_receipts) > 128
        or validate_catalog_v1(catalog)
    ):
        raise ValueError("m6_selector_assembly_identity_invalid")
    if not isinstance(catalog, dict):
        raise TypeError("m6_selector_assembly_identity_invalid")
    catalog_rows = catalog.get("selectors")
    if not isinstance(catalog_rows, list):
        raise TypeError("m6_selector_assembly_identity_invalid")
    by_scope: dict[str, tuple[StatusV1, str | None, str]] = {}
    evidence: list[dict[str, object]] = []
    limitation_codes: set[str] = set()
    selection_digest = hashlib.sha256()
    source_versions_digest = hashlib.sha256()
    requirements = {
        requirement[1]: requirement for requirement in SELECTOR_REQUIREMENTS
    }
    catalog_by_selector = {
        cast(str, row["selector_id"]): row
        for row in catalog_rows
        if isinstance(row, dict) and isinstance(row.get("selector_id"), str)
    }
    if set(producer_statuses) != set(requirements) or any(
        status not in _STATUS_VALUES for status in producer_statuses.values()
    ):
        raise ValueError("m6_selector_producer_statuses_invalid")
    for raw in selector_receipts:
        if not isinstance(raw, dict) or set(raw) != _SELECTOR_KEYS:
            raise ValueError("m6_selector_receipt_shape_invalid")
        if (
            raw.get("schema_version") != "1.0.0"
            or raw.get("record_type") != "agentmonitor.m6_selector_receipt.v1"
        ):
            raise ValueError("m6_selector_receipt_header_invalid")
        item = raw.get("evidence")
        if not isinstance(item, dict):
            raise TypeError("m6_selector_receipt_evidence_invalid")
        evidence_id = item.get("evidence_id")
        scopes = item.get("scope_ids")
        result = item.get("result")
        reason = raw.get("reason_code")
        selector_id = raw.get("selector_id")
        boundary = raw.get("boundary")
        selection_policy_id = raw.get("selection_policy_id")
        source_versions_policy_id = raw.get("source_versions_policy_id")
        selection = raw.get("selection_sha256")
        source_versions = raw.get("source_versions_sha256")
        requirement = (
            requirements.get(selector_id) if isinstance(selector_id, str) else None
        )
        catalog_row = (
            catalog_by_selector.get(selector_id)
            if isinstance(selector_id, str)
            else None
        )
        if (
            not isinstance(evidence_id, str)
            or requirement is None
            or catalog_row is None
            or scopes != [requirement[0]]
            or boundary != requirement[2]
            or item.get("producer_id") != requirement[3]
            or item.get("producer_version") != catalog_row.get("producer_version")
            or selection_policy_id != requirement[5]
            or source_versions_policy_id != requirement[6]
            or not isinstance(selection, str)
            or _SHA256.fullmatch(selection) is None
            or not isinstance(source_versions, str)
            or _SHA256.fullmatch(source_versions) is None
            or result not in _STATUS_VALUES
            or producer_statuses.get(cast(str, selector_id)) == "not_run"
            or result != producer_statuses.get(cast(str, selector_id))
            or (result == "passed" and reason is not None)
            or (
                result != "passed"
                and (
                    not isinstance(reason, str) or _SAFE_CODE.fullmatch(reason) is None
                )
            )
        ):
            raise ValueError("m6_selector_receipt_outcome_invalid")
        limitations = _safe_codes(raw.get("declared_limitations"))
        if limitations is None:
            raise ValueError("m6_selector_receipt_limitations_invalid")
        if result == "passed" and not set(requirement[4]).issubset(limitations):
            raise ValueError("m6_selector_receipt_limitations_missing")
        frozen_selection = catalog_row.get("selection_sha256")
        frozen_source_versions = catalog_row.get("source_versions_sha256")
        if result == "passed" and (
            not isinstance(frozen_selection, str)
            or not isinstance(frozen_source_versions, str)
        ):
            raise ValueError("m6_selector_selection_not_frozen")
        if (isinstance(frozen_selection, str) and selection != frozen_selection) or (
            isinstance(frozen_source_versions, str)
            and source_versions != frozen_source_versions
        ):
            raise ValueError("m6_selector_selection_mismatch")
        selector_id = cast(str, selector_id)
        limitation_codes.update(limitations)
        scope = requirement[0]
        if scope in by_scope:
            raise ValueError("m6_selector_scope_duplicate_or_invalid")
        by_scope[scope] = (result, reason, evidence_id)
        selection_digest.update(
            selector_id.encode("ascii")
            + b"\0"
            + cast(str, selection_policy_id).encode("ascii")
            + b"\0"
            + selection.encode("ascii")
        )
        source_versions_digest.update(
            selector_id.encode("ascii")
            + b"\0"
            + cast(str, source_versions_policy_id).encode("ascii")
            + b"\0"
            + source_versions.encode("ascii")
        )
        evidence.append(item)

    def outcomes(scope_ids: tuple[str, ...]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for scope_id in scope_ids:
            if scope_id == SELF_COMPLETION_SCOPE_ID:
                rows.append(
                    {
                        "id": scope_id,
                        "status": "not_run",
                        "reason_code": "self_completion_pending",
                        "evidence_ids": [],
                    }
                )
                continue
            selected = by_scope.get(scope_id)
            if selected is None:
                requirement = next(
                    item for item in SELECTOR_REQUIREMENTS if item[0] == scope_id
                )
                producer_status = producer_statuses[requirement[1]]
                if producer_status == "passed":
                    missing_status: StatusV1 = "failed"
                    reason_code = "selector_receipt_missing"
                elif producer_status == "failed":
                    missing_status = "failed"
                    reason_code = "selector_producer_failed"
                elif producer_status == "blocked":
                    missing_status = "blocked"
                    reason_code = "selector_producer_blocked"
                else:
                    missing_status = "not_run"
                    reason_code = "selector_producer_not_run"
                rows.append(
                    {
                        "id": scope_id,
                        "status": missing_status,
                        "reason_code": reason_code,
                        "evidence_ids": [],
                    }
                )
                continue
            status, reason, evidence_id = selected
            rows.append(
                {
                    "id": scope_id,
                    "status": status,
                    "reason_code": reason,
                    "evidence_ids": [evidence_id],
                }
            )
        return rows

    return {
        "schema_version": "1.0.0",
        "record_type": "agentmonitor.m6_completion_evidence.v1",
        "milestone_id": "V1-M6",
        "implementation_revision": expected_revision,
        "catalog_sha256": catalog_sha256,
        "selection_sha256": selection_digest.hexdigest(),
        "source_versions_sha256": source_versions_digest.hexdigest(),
        "recorded_at": recorded_at.astimezone(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "acceptance": outcomes(ACCEPTANCE_IDS),
        "stories": outcomes(STORY_IDS),
        "evidence": evidence,
        "declared_limitations": sorted(limitation_codes),
    }


def _validate_evidence_entry(
    raw: object,
    *,
    expected_revision: str,
    now: datetime,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    reasons: list[str] = []
    if not isinstance(raw, dict) or set(raw) != _EVIDENCE_KEYS:
        return None, ("m6_evidence_entry_shape_invalid",)
    evidence_id = raw.get("evidence_id")
    path = raw.get("path")
    digest = raw.get("sha256")
    scopes = raw.get("scope_ids")
    result = raw.get("result")
    producer = raw.get("producer_id")
    producer_version = raw.get("producer_version")
    exit_code = raw.get("exit_code")
    test_count = raw.get("test_count")
    skip_count = raw.get("skip_count")
    revision = raw.get("implementation_revision")
    observed_at = _utc_datetime(raw.get("observed_at"))
    valid_until = _utc_datetime(raw.get("valid_until"))
    if not isinstance(evidence_id, str) or _SAFE_ID.fullmatch(evidence_id) is None:
        reasons.append("m6_evidence_id_invalid")
    if (
        not isinstance(path, str)
        or _SAFE_PATH.fullmatch(path) is None
        or path.startswith("/")
        or ".." in path.split("/")
        or not path.startswith(("docs/evidence/", ".agentmonitor-local/m6-evidence/"))
    ):
        reasons.append("m6_evidence_path_invalid")
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        reasons.append("m6_evidence_digest_invalid")
    if (
        not isinstance(scopes, list)
        or not scopes
        or len(set(scopes)) != len(scopes)
        or any(scope not in ALL_SCOPE_IDS for scope in scopes)
    ):
        reasons.append("m6_evidence_scope_invalid")
    if result not in _STATUS_VALUES:
        reasons.append("m6_evidence_result_invalid")
    if not isinstance(producer, str) or _SAFE_ID.fullmatch(producer) is None:
        reasons.append("m6_evidence_producer_invalid")
    if (
        not isinstance(producer_version, str)
        or _SEMVER.fullmatch(producer_version) is None
    ):
        reasons.append("m6_evidence_producer_version_invalid")
    if (
        type(exit_code) is not int
        or exit_code < 0
        or exit_code > 255
        or (result == "passed" and exit_code != 0)
        or (result in {"blocked", "not_run"} and exit_code != 3)
        or (result == "failed" and exit_code in {0, 3})
    ):
        reasons.append("m6_evidence_exit_code_invalid")
    if type(test_count) is not int or test_count < 0:
        reasons.append("m6_evidence_test_count_invalid")
    elif result in {"passed", "failed"} and test_count == 0:
        reasons.append("m6_required_scenario_missing")
    if (
        type(skip_count) is not int
        or skip_count < 0
        or (type(test_count) is int and skip_count > test_count)
    ):
        reasons.append("m6_evidence_skip_count_invalid")
    elif skip_count:
        reasons.append("m6_required_scenario_skipped")
    if revision != expected_revision:
        reasons.append("m6_evidence_revision_mismatch")
    if (
        observed_at is None
        or valid_until is None
        or observed_at > now
        or valid_until < observed_at
    ):
        reasons.append("m6_evidence_time_invalid")
    elif valid_until < now:
        reasons.append("m6_evidence_stale")
    return raw, tuple(reasons)


def evaluate_evidence_bundle_v1(
    bundle: object,
    *,
    catalog: object,
    expected_revision: str,
    expected_catalog_sha256: str,
    now: datetime,
) -> M6EvidenceEvaluationV1:
    """Evaluate closed real-evidence results without performing I/O."""

    acceptance: dict[str, StatusV1] = {key: "not_run" for key in ACCEPTANCE_IDS}
    stories: dict[str, StatusV1] = {key: "not_run" for key in STORY_IDS}
    reasons: list[str] = list(validate_catalog_v1(catalog))
    evidence_count = 0
    limitations: tuple[str, ...] = ()
    selection_digest: str | None = None
    source_versions_digest: str | None = None
    structural_failure = bool(reasons)
    if (
        not isinstance(expected_revision, str)
        or _REVISION.fullmatch(expected_revision) is None
        or not isinstance(expected_catalog_sha256, str)
        or _SHA256.fullmatch(expected_catalog_sha256) is None
        or not _is_utc(now)
    ):
        reasons.append("m6_evaluation_identity_invalid")
        structural_failure = True
    if not isinstance(bundle, dict) or set(bundle) != _BUNDLE_KEYS:
        reasons.append("m6_evidence_bundle_shape_invalid")
        structural_failure = True
        return M6EvidenceEvaluationV1(
            "failed",
            acceptance,
            stories,
            tuple(dict.fromkeys(reasons)),
            evidence_count,
            limitations,
            selection_digest,
            source_versions_digest,
        )
    if (
        bundle.get("schema_version") != "1.0.0"
        or bundle.get("record_type") != "agentmonitor.m6_completion_evidence.v1"
        or bundle.get("milestone_id") != "V1-M6"
    ):
        reasons.append("m6_evidence_bundle_header_invalid")
        structural_failure = True
    if bundle.get("catalog_sha256") != expected_catalog_sha256:
        reasons.append("m6_evidence_catalog_mismatch")
    if bundle.get("implementation_revision") != expected_revision:
        reasons.append("m6_evidence_revision_mismatch")
    if _utc_datetime(bundle.get("recorded_at")) is None:
        reasons.append("m6_evidence_recorded_at_invalid")
        structural_failure = True
    for field, code in (
        ("selection_sha256", "m6_selection_digest_invalid"),
        ("source_versions_sha256", "m6_source_versions_digest_invalid"),
    ):
        value = bundle.get(field)
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            reasons.append(code)
            structural_failure = True
        elif field == "selection_sha256":
            selection_digest = value
        else:
            source_versions_digest = value
    parsed_limitations = _safe_codes(bundle.get("declared_limitations"))
    if parsed_limitations is None:
        reasons.append("m6_declared_limitations_invalid")
        structural_failure = True
    else:
        limitations = parsed_limitations

    evidence_by_id: dict[str, dict[str, object]] = {}
    evidence_reasons: dict[str, tuple[str, ...]] = {}
    raw_evidence = bundle.get("evidence")
    if not isinstance(raw_evidence, list) or len(raw_evidence) > 128:
        reasons.append("m6_evidence_entries_invalid")
        structural_failure = True
    else:
        for raw in raw_evidence:
            parsed, entry_reasons = _validate_evidence_entry(
                raw, expected_revision=expected_revision, now=now
            )
            reasons.extend(entry_reasons)
            if parsed is None:
                structural_failure = True
                continue
            evidence_id = parsed.get("evidence_id")
            if not isinstance(evidence_id, str) or evidence_id in evidence_by_id:
                reasons.append("m6_evidence_id_duplicate")
                structural_failure = True
                continue
            evidence_by_id[evidence_id] = parsed
            evidence_reasons[evidence_id] = entry_reasons
        evidence_count = len(evidence_by_id)

    def consume_outcomes(
        field: str,
        expected: tuple[str, ...],
        target: dict[str, StatusV1],
        missing_code: str,
    ) -> None:
        nonlocal structural_failure
        raw_rows = bundle.get(field)
        if not isinstance(raw_rows, list):
            reasons.append(f"m6_{field}_shape_invalid")
            structural_failure = True
            return
        seen: set[str] = set()
        for raw in raw_rows:
            if not isinstance(raw, dict) or set(raw) != _OUTCOME_KEYS:
                reasons.append(f"m6_{field}_entry_invalid")
                structural_failure = True
                continue
            scope_id = raw.get("id")
            status = raw.get("status")
            reason_code = raw.get("reason_code")
            evidence_ids = raw.get("evidence_ids")
            if (
                not isinstance(scope_id, str)
                or scope_id not in expected
                or scope_id in seen
            ):
                reasons.append(f"m6_{field}_identity_invalid")
                structural_failure = True
                continue
            seen.add(scope_id)
            if status not in _STATUS_VALUES:
                reasons.append(f"m6_{field}_status_invalid")
                target[scope_id] = "failed"
                structural_failure = True
                continue
            if (
                not isinstance(evidence_ids, list)
                or len(set(evidence_ids)) != len(evidence_ids)
                or any(not isinstance(item, str) for item in evidence_ids)
            ):
                reasons.append(f"m6_{field}_references_invalid")
                target[scope_id] = "failed"
                structural_failure = True
                continue
            if status == "passed":
                if reason_code is not None or not evidence_ids:
                    reasons.append(f"m6_{field}_pass_invalid")
                    target[scope_id] = "failed"
                    structural_failure = True
                    continue
            elif (
                not isinstance(reason_code, str)
                or _SAFE_CODE.fullmatch(reason_code) is None
            ):
                reasons.append(f"m6_{field}_reason_invalid")
                target[scope_id] = "failed"
                structural_failure = True
                continue
            row_status: StatusV1 = status
            for evidence_id in evidence_ids:
                entry = evidence_by_id.get(evidence_id)
                if entry is None:
                    reasons.append("m6_evidence_reference_missing")
                    row_status = "failed"
                    structural_failure = True
                    continue
                scopes = entry.get("scope_ids")
                if not isinstance(scopes, list) or scope_id not in scopes:
                    reasons.append("m6_evidence_scope_narrower")
                    row_status = "failed"
                    structural_failure = True
                    continue
                if entry.get("result") != status:
                    reasons.append("m6_evidence_result_mismatch")
                    row_status = "failed"
                    structural_failure = True
                entry_codes = evidence_reasons.get(evidence_id, ())
                if "m6_required_scenario_skipped" in entry_codes:
                    row_status = "blocked"
                if any(
                    code in entry_codes
                    for code in (
                        "m6_evidence_revision_mismatch",
                        "m6_evidence_stale",
                        "m6_evidence_catalog_mismatch",
                    )
                ):
                    row_status = "blocked"
                if any(
                    code
                    not in {
                        "m6_required_scenario_skipped",
                        "m6_evidence_revision_mismatch",
                        "m6_evidence_stale",
                    }
                    for code in entry_codes
                ):
                    row_status = "failed"
                    structural_failure = True
            target[scope_id] = row_status
        if seen != set(expected):
            reasons.append(missing_code)

    consume_outcomes(
        "acceptance", ACCEPTANCE_IDS, acceptance, "m6_acceptance_evidence_missing"
    )
    consume_outcomes("stories", STORY_IDS, stories, "m6_story_evidence_missing")

    for scope_id, _, _, _, required_limitations, _, _ in SELECTOR_REQUIREMENTS:
        target = acceptance if scope_id in acceptance else stories
        if target[scope_id] == "passed" and not set(required_limitations).issubset(
            limitations
        ):
            reasons.append("m6_sampled_process_limitation_missing")
            target[scope_id] = "failed"
            structural_failure = True

    if (
        "m6_evidence_revision_mismatch" in reasons
        or "m6_evidence_catalog_mismatch" in reasons
    ):
        for target in (acceptance, stories):
            for key, status in target.items():
                if status == "passed":
                    target[key] = "blocked"
    statuses = tuple(acceptance.values()) + tuple(stories.values())
    overall = _status_summary(statuses)
    if structural_failure:
        overall = "failed"
    return M6EvidenceEvaluationV1(
        overall,
        acceptance,
        stories,
        tuple(dict.fromkeys(reasons)),
        evidence_count,
        limitations,
        selection_digest,
        source_versions_digest,
    )


def external_scope_status_v1(evaluation: M6EvidenceEvaluationV1) -> StatusV1:
    """Summarize all externally evidenced scopes while A10 is still pending."""

    if evaluation.overall_status == "failed":
        return "failed"
    statuses = tuple(
        status
        for scope_id, status in evaluation.acceptance.items()
        if scope_id != SELF_COMPLETION_SCOPE_ID
    ) + tuple(evaluation.stories.values())
    return _status_summary(statuses)


def build_passed_receipt_v1(
    *,
    implementation_revision: str,
    catalog_sha256: str,
    selector_receipts_sha256: str,
    selection_sha256: str,
    source_versions_sha256: str,
    completed_at: datetime,
    evidence_count: int,
    required_checks: tuple[str, ...],
    declared_limitations: tuple[str, ...],
) -> dict[str, object]:
    """Build a privacy-minimized receipt after every exact lane has passed."""

    if (
        _REVISION.fullmatch(implementation_revision) is None
        or any(
            _SHA256.fullmatch(value) is None
            for value in (
                catalog_sha256,
                selector_receipts_sha256,
                selection_sha256,
                source_versions_sha256,
            )
        )
        or not _is_utc(completed_at)
        or type(evidence_count) is not int
        or evidence_count != len(SELECTOR_REQUIREMENTS)
        or required_checks != REQUIRED_CHECKS
        or _safe_codes(list(declared_limitations)) != declared_limitations
    ):
        raise ValueError("m6_receipt_input_invalid")
    return {
        "schema_version": "1.0.0",
        "record_type": "agentmonitor.m6_technical_exit_receipt.v1",
        "milestone_id": "V1-M6",
        "command_id": "AUTO-M6-EXIT",
        "command": "python3 tools/automation/run.py AUTO-M6-EXIT",
        "implementation_revision": implementation_revision,
        "completed_at": completed_at.astimezone(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "status": "passed",
        "exit_code": 0,
        "technical_acceptance_count": len(ACCEPTANCE_IDS) - 1,
        "pending_acceptance_ids": [SELF_COMPLETION_SCOPE_ID],
        "story_count": len(STORY_IDS),
        "evidence_count": evidence_count,
        "catalog_sha256": catalog_sha256,
        "selector_receipts_sha256": selector_receipts_sha256,
        "selection_sha256": selection_sha256,
        "source_versions_sha256": source_versions_sha256,
        "required_checks": [
            {"command_id": command_id, "status": "passed", "exit_code": 0}
            for command_id in required_checks
        ],
        "declared_limitations": list(declared_limitations),
    }


def validate_existing_passed_receipt_v1(
    receipt: object,
    *,
    expected: Mapping[str, object],
    now: datetime,
) -> tuple[str, ...]:
    """Validate one immutable prior receipt against the current exact snapshot."""

    if not isinstance(receipt, dict) or set(receipt) != _RECEIPT_KEYS:
        return ("m6_receipt_shape_invalid",)
    if not isinstance(expected, Mapping) or set(expected) != _RECEIPT_KEYS:
        return ("m6_receipt_expected_shape_invalid",)
    completed_at = _utc_datetime(receipt.get("completed_at"))
    if not _is_utc(now) or completed_at is None or completed_at > now:
        return ("m6_receipt_completed_at_invalid",)
    mismatched = tuple(
        key
        for key in sorted(_RECEIPT_KEYS - {"completed_at"})
        if receipt.get(key) != expected.get(key)
    )
    if mismatched:
        return ("m6_receipt_conflict",)
    return ()
