"""Pure direct-evidence classification for the canonical M6 exit command.

The I/O-owning gate supplies only sanitized counts and bounded command
outcomes.  This module neither discovers providers nor opens application data.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from tools.automation.implementations.m6_authoritative_evidence import (
    AuthoritativeComparisonV1,
)
from tools.automation.implementations.m6_controlled_recovery_evidence import (
    ControlledRecoveryEvidenceV1,
)
from tools.automation.implementations.m6_recovery_evidence import (
    RecoveryIntervalEvidenceV1,
)

StatusV1 = Literal["passed", "failed", "blocked", "not_run"]
_SAFE_REASON = re.compile(r"[a-z][a-z0-9_]{0,95}\Z")
_SAFE_HOST_ID = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")

DIRECT_EXECUTABLE_SELECTION_V1: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "scope_policy",
        (
            "/usr/bin/env",
            "PYTHONPATH=backend/src",
            "PYTHONDONTWRITEBYTECODE=1",
            "{checkout_python}",
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "tools.automation.pytest_no_skip",
            "tools/automation/test_m6_scope_selection.py",
            "tools/automation/test_m6_cloud_scope_evidence.py",
            "tools/automation/test_m6_direct_evidence.py",
            "tools/automation/test_m6_local_deferral.py",
            "tools/automation/test_m6_controlled_recovery_evidence.py",
        ),
    ),
    (
        "source_security",
        (
            "/usr/bin/env",
            "PYTHONPATH=backend/src",
            "PYTHONDONTWRITEBYTECODE=1",
            "{checkout_python}",
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "tools.automation.pytest_no_skip",
            "tools/automation/test_m6_controlled_recovery_interval.py",
            "backend/tests/adapters/providers/claude/test_usage_failure_cadence.py",
            "backend/tests/collection_control/domain/test_ollama_latest_source_signal.py",
            "backend/tests/registry/domain/test_cloud_owner_assertion.py",
            "backend/tests/adapters/providers/ollama/test_cloud_balance_source_policy.py",
            "backend/tests/adapters/providers/ollama/test_cloud_balance_source_security.py::test_authorization_failure_code_is_runtime_closed",
            "backend/tests/adapters/providers/ollama/test_cloud_balance_source_security.py::test_valid_long_retry_after_is_not_discarded_or_truncated",
            "backend/tests/adapters/providers/ollama/test_cloud_balance_source_security.py::test_unrepresentable_retry_after_fails_closed",
            "backend/tests/adapters/providers/ollama/test_cloud_balance_source_security.py::test_malformed_retry_after_remains_fallback_eligible",
            "backend/tests/adapters/providers/ollama/test_cloud_balance_source_security.py::test_raw_descriptor_cannot_be_used_as_a_credential_lock",
            "backend/tests/adapters/providers/ollama/test_env_capability_policy.py",
            "backend/tests/adapters/providers/ollama/test_env_helper_process_policy.py",
        ),
    ),
    (
        "installed_dashboard",
        (
            "/usr/bin/node",
            "frontend/tests/browser/m6/verify_ollama_dashboard.mjs",
            "{revision}",
        ),
    ),
    (
        "authoritative_policy",
        (
            "/usr/bin/node",
            "--test",
            "frontend/tests/pure/ollama-authoritative-comparison.mjs",
            "frontend/tests/pure/m6-registry-stability.mjs",
        ),
    ),
    (
        "authoritative_comparison",
        (
            "/usr/bin/node",
            "frontend/tests/browser/m6/compare_official_ollama_usage.mjs",
            "{revision}",
        ),
    ),
    (
        "recovery_interval",
        (
            "/usr/bin/env",
            "PYTHONPATH=backend/src",
            "PYTHONDONTWRITEBYTECODE=1",
            "{checkout_python}",
            "-B",
            "-m",
            "tools.automation.implementations.m6_recovery_interval",
            "--revision",
            "{revision}",
        ),
    ),
    (
        "controlled_recovery_interval",
        (
            "/usr/bin/env",
            "PYTHONPATH=backend/src",
            "PYTHONDONTWRITEBYTECODE=1",
            "{checkout_python}",
            "-B",
            "-m",
            "tools.automation.implementations.m6_controlled_recovery_interval",
            "--revision",
            "{revision}",
        ),
    ),
    (
        "database_snapshot",
        (
            "/usr/bin/env",
            "PYTHONPATH=backend/src",
            "PYTHONDONTWRITEBYTECODE=1",
            "{checkout_python}",
            "-B",
            "-m",
            "tools.automation.implementations.m6_real_snapshot",
            "--data-root",
            "/home/dev/.local/share/agentmonitor",
        ),
    ),
)

_BOUNDARY_CHECKS: dict[str, tuple[str, ...]] = {
    "M6-A01": ("browser.ollama_account_admin.v1",),
    "M6-A03": ("m02.cloud_owner_scope.v1", "m02.organization_scope.v1"),
    "M6-A04": (
        "m02.verification.v1",
        "m05.current_capacity.v2",
        "browser.ollama_capacity.v1",
        "provider.authoritative_balance_comparison.v1",
    ),
    "M6-A05": (
        "m05.capacity_history.v1",
        "m07.alert_lineage.v1",
        "m07.alert_event_deduplication.v1",
        "browser.ollama_capacity.v1",
    ),
    "M6-A07": (
        "m04.exact_target_natural_or_witnessed_network_recovery.v1",
        "integration.interval_continuity.v1",
    ),
    "M6-A08": (
        "browser.installed_dashboard_continuity.v1",
        "browser.responsive.v1",
    ),
    "M6-A09": ("m03.source_security.v1", "m02.verification.v1"),
    "ST-OLL-001": ("m03.cloud_source_security.v1", "m02.cloud_registry.v1"),
    "ST-OLL-003": ("m02.cloud_owner_scope.v1", "m02.verification.v1"),
    "ST-OLL-004": (
        "m05.current_capacity.v2",
        "m05.capacity_history.v1",
        "browser.ollama_capacity.v1",
    ),
    "ST-OLL-005": ("m6.external_acceptance.v1",),
}

_SOURCE_VERSIONS: dict[str, tuple[str, ...]] = {
    "M6-A01": ("CTR-REG-002:1.0.0", "CTR-API-001:1.0.0", "CTR-UI-001:1.0.0"),
    "M6-A03": ("CTR-REG-011:1.0.0", "CTR-REG-012:1.1.0", "CTR-REG-013:1.0.0"),
    "M6-A04": (
        "ollama.cloud.balance.v1:1.0.0",
        "CTR-COL-008:1.1.0",
        "CTR-CAP-001:1.0.0",
    ),
    "M6-A05": ("CTR-CAP-006:1.0.0", "CTR-ALERT-002:1.0.0"),
    "M6-A07": (
        "CTR-COL-012:1.0.0",
        "CTR-COL-008:1.1.0",
        "agentmonitor.m6_controlled_recovery_interval.v1:1.0.0",
    ),
    "M6-A08": ("CTR-API-001:1.0.0", "CTR-UI-001:1.0.0"),
    "M6-A09": (
        "ollama.cloud.balance.v1:1.0.0",
        "CTR-PROV-008:1.0.0",
        "CTR-REG-011:1.0.0",
    ),
    "ST-OLL-001": (
        "CTR-PROV-001:1.0.0",
        "CTR-PROV-005:1.0.0",
    ),
    "ST-OLL-003": ("CTR-REG-012:1.1.0", "CTR-REG-013:1.0.0", "CTR-COL-010:2.0.0"),
    "ST-OLL-004": (
        "ollama.cloud.balance.v1:1.0.0",
        "CTR-CAP-001:1.0.0",
        "CTR-CAP-006:1.0.0",
    ),
    "ST-OLL-005": ("M6-CLOUD-SCOPE-2026-11-04:1.0.0", "CTR-UI-001:1"),
}


def _policy_digest(document: dict[str, object]) -> str:
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def direct_policy_hashes_v1(
    scope_id: str,
    selection_policy_id: str,
    source_versions_policy_id: str,
) -> tuple[str, str]:
    """Return reviewed hashes for one fixed direct selector policy."""

    if scope_id not in _BOUNDARY_CHECKS or scope_id not in _SOURCE_VERSIONS:
        raise ValueError("m6_direct_policy_scope_invalid")
    return (
        _policy_digest(
            {
                "policy_id": selection_policy_id,
                "scope_id": scope_id,
                "checks": list(_BOUNDARY_CHECKS[scope_id]),
                "executable_selection": [
                    [name, list(arguments)]
                    for name, arguments in DIRECT_EXECUTABLE_SELECTION_V1
                ],
            }
        ),
        _policy_digest(
            {
                "policy_id": source_versions_policy_id,
                "scope_id": scope_id,
                "source_versions": list(_SOURCE_VERSIONS[scope_id]),
            }
        ),
    )


@dataclass(frozen=True, slots=True)
class BoundaryCheckV1:
    """One actually attempted bounded check and its positive scenario count."""

    status: StatusV1
    test_count: int
    skip_count: int = 0
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"passed", "failed", "blocked", "not_run"}:
            raise ValueError("m6_direct_check_status_invalid")
        if (
            type(self.test_count) is not int
            or self.test_count < 0
            or type(self.skip_count) is not int
            or not 0 <= self.skip_count <= self.test_count
        ):
            raise ValueError("m6_direct_check_count_invalid")
        if self.status in {"passed", "failed"} and self.test_count < 1:
            raise ValueError("m6_direct_check_count_invalid")
        if self.status == "passed" and self.reason_code is not None:
            raise ValueError("m6_direct_check_reason_invalid")
        if (
            self.reason_code is not None
            and _SAFE_REASON.fullmatch(self.reason_code) is None
        ):
            raise ValueError("m6_direct_check_reason_invalid")


@dataclass(frozen=True, slots=True)
class LocalModelHostEvidenceV1:
    """One privacy-minimized real Ollama version/tags/ps observation."""

    host_id: str
    source_id: str
    version: str
    installed_model_count: int
    loaded_model_count: int
    observed_at: str

    def __post_init__(self) -> None:
        try:
            observed = datetime.fromisoformat(self.observed_at)
        except ValueError:
            raise ValueError("m6_direct_model_host_invalid") from None
        if (
            _SAFE_HOST_ID.fullmatch(self.host_id) is None
            or _SAFE_HOST_ID.fullmatch(self.source_id) is None
            or _VERSION.fullmatch(self.version) is None
            or type(self.installed_model_count) is not int
            or self.installed_model_count < 0
            or type(self.loaded_model_count) is not int
            or self.loaded_model_count < 0
            or not self.observed_at.endswith("Z")
            or observed.utcoffset() != timedelta(0)
        ):
            raise ValueError("m6_direct_model_host_invalid")


_CLOUD_DISPOSITIONS = frozenset(
    {"account", "shared", "unavailable", "missing", "invalidated"}
)
_CLOUD_UNAVAILABLE_REASONS = frozenset(
    {
        "account_unavailable",
        "subscription_unavailable",
        "access_unavailable",
        "owner_unavailable",
    }
)
_CLOUD_INVALIDATION_REASONS = frozenset(
    {
        "owner_revoked",
        "account_archived",
        "account_reassigned",
        "organization_archived",
        "source_organization_archived",
        "provider_withdrawn",
    }
)


def cloud_reference_digest_v1(kind: str, value: str) -> str:
    """Domain-separated digest of a non-secret runtime registry reference."""
    if (
        kind not in {"organization", "account", "target"}
        or not isinstance(value, str)
        or not value
    ):
        raise ValueError("m6_cloud_reference_invalid")
    return hashlib.sha256(
        ("m6_cloud_scope:" + kind + "\0" + value).encode()
    ).hexdigest()


def _sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


@dataclass(frozen=True, slots=True)
class CloudOrganizationScopeV1:
    organization_sha256: str
    disposition: str
    account_sha256: str | None
    target_sha256: str | None
    record_version: int
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if (
            not _sha256(self.organization_sha256)
            or not isinstance(self.disposition, str)
            or self.disposition not in _CLOUD_DISPOSITIONS
            or self.reason_code is not None
            and not isinstance(self.reason_code, str)
            or type(self.record_version) is not int
            or self.record_version < 0
            or any(
                value is not None and not _sha256(value)
                for value in (self.account_sha256, self.target_sha256)
            )
        ):
            raise ValueError("m6_cloud_scope_invalid")
        if self.disposition in {"account", "shared"}:
            valid = (
                self.account_sha256 is not None
                and self.record_version > 0
                and self.reason_code is None
            )
        elif self.disposition == "unavailable":
            valid = (
                self.account_sha256 is None
                and self.target_sha256 is None
                and self.record_version > 0
                and self.reason_code in _CLOUD_UNAVAILABLE_REASONS
            )
        elif self.disposition == "invalidated":
            valid = (
                self.target_sha256 is None
                and self.record_version > 0
                and self.reason_code in _CLOUD_INVALIDATION_REASONS
            )
        else:
            valid = (
                self.account_sha256 is None
                and self.target_sha256 is None
                and self.record_version == 0
                and self.reason_code is None
            )
        if not valid:
            raise ValueError("m6_cloud_scope_invalid")


@dataclass(frozen=True, slots=True)
class CloudScopeEvidenceV1:
    """Current intended scope classification, separate from actual target proofs."""

    scopes: tuple[CloudOrganizationScopeV1, ...]
    active_target_sha256s: tuple[str, ...]
    owner_confirmed_target_sha256s: tuple[str, ...]
    verified_target_sha256s: tuple[str, ...]
    registry_revision: int
    as_of: str
    complete: bool

    def __post_init__(self) -> None:
        try:
            instant = datetime.fromisoformat(self.as_of)
        except (ValueError, TypeError):
            raise ValueError("m6_cloud_scope_evidence_invalid") from None
        if (
            not isinstance(self.scopes, tuple)
            or not 1 <= len(self.scopes) <= 200
            or not all(
                isinstance(item, CloudOrganizationScopeV1) for item in self.scopes
            )
            or len({item.organization_sha256 for item in self.scopes})
            != len(self.scopes)
            or type(self.registry_revision) is not int
            or self.registry_revision < 0
            or type(self.complete) is not bool
            or instant.utcoffset() != timedelta(0)
        ):
            raise ValueError("m6_cloud_scope_evidence_invalid")
        sets = (
            self.active_target_sha256s,
            self.owner_confirmed_target_sha256s,
            self.verified_target_sha256s,
        )
        if any(
            not isinstance(values, tuple)
            or len(values) > 200
            or not all(_sha256(value) for value in values)
            or tuple(sorted(set(values))) != values
            for values in sets
        ):
            raise ValueError("m6_cloud_scope_evidence_invalid")
        if (
            not set(self.verified_target_sha256s)
            <= set(self.owner_confirmed_target_sha256s)
            or not set(self.owner_confirmed_target_sha256s)
            <= set(self.active_target_sha256s)
            or any(
                item.target_sha256 is not None
                and item.target_sha256 not in self.active_target_sha256s
                for item in self.scopes
            )
            or not self.complete
            and any(item.disposition != "missing" for item in self.scopes)
        ):
            raise ValueError("m6_cloud_scope_evidence_invalid")
        account_targets: dict[str | None, str | None] = {}
        target_accounts: dict[str, str | None] = {}
        for item in self.scopes:
            if item.disposition in {"account", "shared"}:
                if (
                    item.account_sha256 in account_targets
                    and account_targets[item.account_sha256] != item.target_sha256
                ):
                    raise ValueError("m6_cloud_scope_evidence_invalid")
                account_targets[item.account_sha256] = item.target_sha256
                if item.target_sha256 is not None:
                    if (
                        item.target_sha256 in target_accounts
                        and target_accounts[item.target_sha256] != item.account_sha256
                    ):
                        raise ValueError("m6_cloud_scope_evidence_invalid")
                    target_accounts[item.target_sha256] = item.account_sha256

    @property
    def owner_confirmed_scopes(self) -> int:
        return sum(
            item.disposition in {"account", "shared"}
            and item.target_sha256 in self.owner_confirmed_target_sha256s
            for item in self.scopes
        )

    @property
    def selection_sha256(self) -> str:
        return _policy_digest(
            {
                "provider_key": "ollama",
                "organization_sha256s": [
                    item.organization_sha256 for item in self.scopes
                ],
            }
        )

    def as_json(self) -> dict[str, object]:
        value = asdict(self)
        value["scopes"] = [asdict(item) for item in self.scopes]
        for key in (
            "active_target_sha256s",
            "owner_confirmed_target_sha256s",
            "verified_target_sha256s",
        ):
            value[key] = list(value[key])
        value.update(
            schema_version="1.0.0",
            record_type="agentmonitor.m6_cloud_scope.v1",
            selection_sha256=self.selection_sha256,
        )
        return value


def parse_cloud_scope_evidence_v1(
    value: object, *, expected_organization_ids: tuple[str, ...]
) -> CloudScopeEvidenceV1 | None:
    """Closed parser fenced to the caller's persistent intended organization IDs."""
    if value is None:
        return None
    expected_fields = {
        "scopes",
        "active_target_sha256s",
        "owner_confirmed_target_sha256s",
        "verified_target_sha256s",
        "registry_revision",
        "as_of",
        "complete",
        "schema_version",
        "record_type",
        "selection_sha256",
    }
    if (
        not isinstance(value, dict)
        or set(value) != expected_fields
        or value.get("schema_version") != "1.0.0"
        or value.get("record_type") != "agentmonitor.m6_cloud_scope.v1"
        or not isinstance(value.get("scopes"), list)
        or not 1 <= len(value["scopes"]) <= 200
        or not isinstance(expected_organization_ids, tuple)
        or not 1 <= len(expected_organization_ids) <= 200
        or not all(isinstance(item, str) and item for item in expected_organization_ids)
        or len(set(expected_organization_ids)) != len(expected_organization_ids)
    ):
        raise ValueError("m6_cloud_scope_evidence_invalid")
    rows = []
    for item in value["scopes"]:
        if not isinstance(item, dict) or set(item) != {
            "organization_sha256",
            "disposition",
            "account_sha256",
            "target_sha256",
            "record_version",
            "reason_code",
        }:
            raise ValueError("m6_cloud_scope_evidence_invalid")
        rows.append(CloudOrganizationScopeV1(**item))
    for key in (
        "active_target_sha256s",
        "owner_confirmed_target_sha256s",
        "verified_target_sha256s",
    ):
        if not isinstance(value[key], list) or len(value[key]) > 200:
            raise ValueError("m6_cloud_scope_evidence_invalid")
    result = CloudScopeEvidenceV1(
        tuple(rows),
        tuple(value["active_target_sha256s"]),
        tuple(value["owner_confirmed_target_sha256s"]),
        tuple(value["verified_target_sha256s"]),
        value["registry_revision"],
        value["as_of"],
        value["complete"],
    )
    expected = tuple(
        cloud_reference_digest_v1("organization", item)
        for item in expected_organization_ids
    )
    if (
        tuple(item.organization_sha256 for item in result.scopes) != expected
        or value["selection_sha256"] != result.selection_sha256
    ):
        raise ValueError("m6_cloud_scope_selection_mismatch")
    return result


@dataclass(frozen=True, slots=True)
class DirectM6FactsV1:
    """Privacy-minimized facts read from real commands and one SQLite snapshot."""

    local_admission: BoundaryCheckV1
    local_inventory: BoundaryCheckV1
    account_admin_browser: BoundaryCheckV1
    cloud_capacity_browser: BoundaryCheckV1
    capacity_history_browser: BoundaryCheckV1
    process_browser: BoundaryCheckV1
    dashboard_continuity_browser: BoundaryCheckV1
    source_security: BoundaryCheckV1
    database_snapshot: BoundaryCheckV1
    active_ollama_accounts: int
    registered_local_installations: int
    observed_local_installations: int
    observed_model_hosts: int
    model_host_evidence: tuple[LocalModelHostEvidenceV1, ...]
    active_cloud_targets: int
    owner_confirmed_cloud_targets: int
    owner_confirmed_required_scopes: int
    verified_cloud_targets: int
    current_balance_targets: int
    authoritative_balance_reconciled_targets: int
    history_targets: int
    history_lineage_reconciled_targets: int
    configured_alert_targets: int
    alerted_targets: int
    process_observation_count: int
    natural_recovery_targets: int
    cross_provider_continuity_targets: int
    alert_no_transition_targets: int = 0
    cloud_scope_evidence: CloudScopeEvidenceV1 | None = None
    authoritative_observation: AuthoritativeComparisonV1 | None = None
    authoritative_comparison: BoundaryCheckV1 = BoundaryCheckV1(
        "not_run", 0, reason_code="official_usage_not_observed"
    )
    controlled_recovery_targets: int = 0
    controlled_recovery_interval: ControlledRecoveryEvidenceV1 | None = None
    controlled_recovery_observation: BoundaryCheckV1 = BoundaryCheckV1(
        "not_run", 0, reason_code="controlled_recovery_interval_not_observed"
    )
    recovery_interval: RecoveryIntervalEvidenceV1 | None = None
    recovery_observation: BoundaryCheckV1 = BoundaryCheckV1(
        "not_run", 0, reason_code="recovery_interval_not_observed"
    )

    def __post_init__(self) -> None:
        counts = (
            self.active_ollama_accounts,
            self.registered_local_installations,
            self.observed_local_installations,
            self.observed_model_hosts,
            self.active_cloud_targets,
            self.owner_confirmed_cloud_targets,
            self.owner_confirmed_required_scopes,
            self.verified_cloud_targets,
            self.current_balance_targets,
            self.authoritative_balance_reconciled_targets,
            self.history_targets,
            self.history_lineage_reconciled_targets,
            self.configured_alert_targets,
            self.alerted_targets,
            self.alert_no_transition_targets,
            self.process_observation_count,
            self.natural_recovery_targets,
            self.controlled_recovery_targets,
            self.cross_provider_continuity_targets,
        )
        if any(type(value) is not int or value < 0 for value in counts):
            raise ValueError("m6_direct_fact_count_invalid")
        if (
            self.observed_local_installations > self.registered_local_installations
            or self.observed_model_hosts != len(self.model_host_evidence)
            or len({item.host_id for item in self.model_host_evidence})
            != len(self.model_host_evidence)
            or self.owner_confirmed_cloud_targets > self.active_cloud_targets
            or self.verified_cloud_targets > self.active_cloud_targets
            or self.current_balance_targets > self.active_cloud_targets
            or self.authoritative_balance_reconciled_targets > self.active_cloud_targets
            or self.authoritative_balance_reconciled_targets
            > self.current_balance_targets
            or self.history_targets > self.active_cloud_targets
            or self.history_lineage_reconciled_targets > self.active_cloud_targets
            or self.history_lineage_reconciled_targets > self.history_targets
            or self.alerted_targets + self.alert_no_transition_targets
            > self.configured_alert_targets
        ):
            raise ValueError("m6_direct_fact_relationship_invalid")
        scope = self.cloud_scope_evidence
        if scope is not None and (
            len(scope.active_target_sha256s) != self.active_cloud_targets
            or len(scope.owner_confirmed_target_sha256s)
            != self.owner_confirmed_cloud_targets
            or len(scope.verified_target_sha256s) != self.verified_cloud_targets
            or scope.owner_confirmed_scopes != self.owner_confirmed_required_scopes
        ):
            raise ValueError("m6_direct_scope_count_mismatch")


@dataclass(frozen=True, slots=True)
class DirectM6OutcomeV1:
    """One exact acceptance/story result selected by the canonical gate."""

    status: StatusV1
    reason_code: str | None
    test_count: int
    skip_count: int = 0
    declared_limitations: tuple[str, ...] = ()


def _combined(
    *checks: BoundaryCheckV1 | DirectM6OutcomeV1,
    limitation: tuple[str, ...] = (),
) -> DirectM6OutcomeV1:
    statuses = tuple(check.status for check in checks)
    count = sum(check.test_count for check in checks)
    skip_count = sum(check.skip_count for check in checks)
    if "failed" in statuses:
        reason = next(
            (
                check.reason_code
                for check in checks
                if check.status == "failed" and check.reason_code is not None
            ),
            "real_boundary_check_failed",
        )
        return DirectM6OutcomeV1("failed", reason, count, skip_count, limitation)
    if "blocked" in statuses:
        reason = next(
            (
                check.reason_code
                for check in checks
                if check.status == "blocked" and check.reason_code is not None
            ),
            "real_boundary_unavailable",
        )
        return DirectM6OutcomeV1("blocked", reason, count, skip_count, limitation)
    if "not_run" in statuses:
        reason = next(
            (
                check.reason_code
                for check in checks
                if check.status == "not_run" and check.reason_code is not None
            ),
            "real_boundary_not_run",
        )
        return DirectM6OutcomeV1("not_run", reason, count, skip_count, limitation)
    return DirectM6OutcomeV1("passed", None, max(1, count), skip_count, limitation)


def _missing(
    reason_code: str,
    *checks: BoundaryCheckV1 | DirectM6OutcomeV1,
    limitation: tuple[str, ...] = (),
) -> DirectM6OutcomeV1:
    dependency = _combined(*checks, limitation=limitation)
    if dependency.status != "passed":
        return dependency
    return DirectM6OutcomeV1(
        "not_run",
        reason_code,
        dependency.test_count,
        dependency.skip_count,
        limitation,
    )


def classify_direct_m6_evidence_v1(
    facts: DirectM6FactsV1,
) -> dict[str, DirectM6OutcomeV1]:
    """Classify the approved external M6 catalog without inventing evidence."""

    outcomes: dict[str, DirectM6OutcomeV1] = {}
    account_admin = _combined(facts.account_admin_browser, facts.database_snapshot)
    if account_admin.status == "passed" and facts.active_ollama_accounts < 1:
        outcomes["M6-A01"] = _missing("real_ollama_account_not_observed", account_admin)
    else:
        outcomes["M6-A01"] = account_admin

    cloud_base = _combined(facts.database_snapshot)
    scope = facts.cloud_scope_evidence
    if cloud_base.status != "passed":
        outcomes["M6-A03"] = cloud_base
    elif scope is None:
        outcomes["M6-A03"] = _missing("intended_cloud_scope_not_selected", cloud_base)
    elif not scope.complete:
        outcomes["M6-A03"] = _missing("cloud_scope_query_unavailable", cloud_base)
    elif len(scope.scopes) < 2:
        outcomes["M6-A03"] = _missing("intended_cloud_scopes_incomplete", cloud_base)
    elif any(item.disposition == "unavailable" for item in scope.scopes):
        outcomes["M6-A03"] = _missing("required_cloud_scope_unavailable", cloud_base)
    elif (
        scope.owner_confirmed_scopes != len(scope.scopes)
        or facts.owner_confirmed_cloud_targets != facts.active_cloud_targets
        or facts.active_cloud_targets < 1
    ):
        outcomes["M6-A03"] = _missing(
            "owner_confirmed_cloud_scope_not_observed", cloud_base
        )
    else:
        outcomes["M6-A03"] = cloud_base

    cloud_browser = facts.cloud_capacity_browser
    if (
        cloud_browser.status == "not_run"
        and cloud_browser.reason_code != "signed_in_dashboard_unavailable"
        and (facts.current_balance_targets > 0 or facts.history_targets > 0)
    ):
        cloud_browser = BoundaryCheckV1(
            "failed",
            1,
            reason_code="ollama_capacity_ui_missing",
        )
    official = facts.authoritative_comparison
    proof = facts.authoritative_observation
    if official.status == "passed" and (proof is None or proof.status != "passed"):
        official = BoundaryCheckV1(
            "not_run", 0, reason_code="official_usage_not_observed"
        )
    cloud_balance = _combined(outcomes["M6-A03"], cloud_browser, official)
    if cloud_balance.status == "passed" and (
        facts.verified_cloud_targets < facts.active_cloud_targets
        or facts.current_balance_targets < facts.active_cloud_targets
        or facts.authoritative_balance_reconciled_targets < facts.active_cloud_targets
        or proof is None
        or proof.compared_targets != facts.authoritative_balance_reconciled_targets
    ):
        outcomes["M6-A04"] = _missing(
            "authoritative_cloud_balance_not_observed", cloud_balance
        )
    else:
        outcomes["M6-A04"] = cloud_balance

    alerts_complete = (
        facts.configured_alert_targets == 0
        or facts.alerted_targets + facts.alert_no_transition_targets
        == facts.configured_alert_targets
    )
    history_base = _combined(outcomes["M6-A04"], facts.capacity_history_browser)
    if history_base.status == "passed" and (
        facts.history_targets < facts.active_cloud_targets
        or facts.history_lineage_reconciled_targets < facts.active_cloud_targets
        or not alerts_complete
    ):
        outcomes["M6-A05"] = _missing(
            "cloud_history_alert_lineage_not_observed", history_base
        )
    else:
        outcomes["M6-A05"] = history_base

    recovery_limit = ("sampled_dashboard_and_collection_continuity",)
    interval = facts.recovery_interval
    interval_check = facts.recovery_observation
    if interval is not None:
        interval_check = BoundaryCheckV1(
            interval.status,
            1 if interval.status == "passed" else 0,
            reason_code=None if interval.status == "passed" else interval.reason_code,
        )
        if (
            interval.natural_recovery_targets != facts.natural_recovery_targets
            or interval.cross_provider_continuity_targets
            != facts.cross_provider_continuity_targets
        ):
            interval_check = BoundaryCheckV1(
                "failed", 1, reason_code="recovery_interval_count_mismatch"
            )
    elif interval_check.status == "passed":
        interval_check = BoundaryCheckV1(
            "failed", 1, reason_code="recovery_interval_missing"
        )
    recovery_base = _combined(
        cloud_base,
        facts.dashboard_continuity_browser,
        facts.recovery_observation,
        interval_check,
        limitation=recovery_limit,
    )
    if recovery_base.status == "passed" and (
        facts.natural_recovery_targets < 1
        or facts.cross_provider_continuity_targets < 1
    ):
        outcomes["M6-A07"] = _missing(
            "natural_failure_recovery_not_observed",
            recovery_base,
            limitation=recovery_limit,
        )
    else:
        outcomes["M6-A07"] = recovery_base

    controlled = facts.controlled_recovery_interval
    controlled_check = facts.controlled_recovery_observation
    if (
        controlled is not None
        or facts.controlled_recovery_targets
        or controlled_check.status != "not_run"
        or controlled_check.reason_code != "controlled_recovery_interval_not_observed"
    ):
        recovery_limit += ("provider_side_401_403_429_not_observed",)
        natural_absent = (
            facts.recovery_observation.status == "not_run"
            and facts.recovery_observation.reason_code
            == "m6_recovery_current_natural_failure_absent"
            and not facts.natural_recovery_targets
            and (
                interval is None
                or interval.status == "not_run"
                and not interval.natural_recovery_targets
            )
        )
        if (
            not natural_absent
            or controlled is None
            and (
                facts.controlled_recovery_targets or controlled_check.status == "passed"
            )
            or controlled is not None
            and (
                not isinstance(controlled, ControlledRecoveryEvidenceV1)
                or controlled.status != "passed"
                or controlled.controlled_recovery_targets
                != facts.controlled_recovery_targets
                or controlled.cross_provider_continuity_targets
                != facts.cross_provider_continuity_targets
            )
        ):
            controlled_check = BoundaryCheckV1(
                "failed", 1, reason_code="controlled_recovery_interval_mismatch"
            )
        outcomes["M6-A07"] = _combined(
            cloud_base,
            facts.dashboard_continuity_browser,
            controlled_check,
            facts.controlled_recovery_observation,
            limitation=recovery_limit,
        )

    outcomes["M6-A08"] = _combined(facts.dashboard_continuity_browser)
    outcomes["M6-A09"] = _combined(
        facts.source_security,
        outcomes["M6-A03"],
        outcomes["M6-A04"],
    )

    outcomes["ST-OLL-001"] = _combined(facts.database_snapshot, facts.source_security)

    if outcomes["M6-A03"].status == "passed" and (
        facts.verified_cloud_targets < facts.active_cloud_targets
    ):
        outcomes["ST-OLL-003"] = _missing(
            "cloud_authentication_not_verified", outcomes["M6-A03"]
        )
    else:
        outcomes["ST-OLL-003"] = _combined(outcomes["M6-A03"])
    outcomes["ST-OLL-004"] = _combined(outcomes["M6-A04"], outcomes["M6-A05"])
    outcomes["ST-OLL-005"] = _combined(
        *(outcomes[f"M6-A{index:02}"] for index in (1, 3, 4, 5, 7, 8, 9)),
        limitation=recovery_limit,
    )
    return outcomes


def direct_bundle_v1(
    outcomes: dict[str, DirectM6OutcomeV1],
    *,
    catalog: dict[str, object],
    artifact_path: str,
    artifact_sha256: str,
    implementation_revision: str,
    catalog_sha256: str,
    recorded_at: datetime,
) -> dict[str, object]:
    """Build one gate-owned bundle from direct results and one shared artifact.

    No external producer receipt is required. Every catalog scope names its own
    result while all scopes bind the same privacy-minimized machine artifact.
    """

    from tools.automation.implementations.m6_exit_policy import (
        ACCEPTANCE_IDS,
        SELECTOR_REQUIREMENTS,
        STORY_IDS,
        validate_catalog_v1,
    )

    expected_scopes = {item[0] for item in SELECTOR_REQUIREMENTS}
    catalog_rows = catalog.get("selectors") if isinstance(catalog, dict) else None
    if (
        set(outcomes) != expected_scopes
        or validate_catalog_v1(catalog)
        or not isinstance(catalog_rows, list)
    ):
        raise ValueError("m6_direct_outcomes_invalid")
    by_selector = {
        row.get("selector_id"): row for row in catalog_rows if isinstance(row, dict)
    }
    if (
        not artifact_path.startswith(".agentmonitor-local/m6-evidence/")
        or len(artifact_sha256) != 64
        or any(character not in "0123456789abcdef" for character in artifact_sha256)
        or len(implementation_revision) != 40
        or any(
            character not in "0123456789abcdef" for character in implementation_revision
        )
        or len(catalog_sha256) != 64
        or any(character not in "0123456789abcdef" for character in catalog_sha256)
        or recorded_at.utcoffset() != timedelta(0)
    ):
        raise ValueError("m6_direct_bundle_identity_invalid")

    evidence: list[dict[str, object]] = []
    by_scope: dict[str, str] = {}
    selection_digest = hashlib.sha256()
    source_versions_digest = hashlib.sha256()
    limitations: set[str] = set()
    valid_until = recorded_at + timedelta(minutes=20)
    observed = (
        recorded_at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    valid = (
        valid_until.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    for (
        scope_id,
        selector_id,
        _boundary,
        producer_id,
        _required_limitations,
        selection_policy_id,
        source_versions_policy_id,
    ) in SELECTOR_REQUIREMENTS:
        outcome = outcomes[scope_id]
        selection, source_versions = direct_policy_hashes_v1(
            scope_id, selection_policy_id, source_versions_policy_id
        )
        catalog_row = by_selector.get(selector_id)
        if (
            not isinstance(catalog_row, dict)
            or catalog_row.get("selection_sha256") != selection
            or catalog_row.get("source_versions_sha256") != source_versions
        ):
            raise ValueError("m6_direct_catalog_policy_mismatch")
        evidence_id = "E-" + selector_id
        by_scope[scope_id] = evidence_id
        limitations.update(outcome.declared_limitations)
        selection_digest.update(
            selector_id.encode("ascii")
            + b"\0"
            + selection_policy_id.encode("ascii")
            + b"\0"
            + selection.encode("ascii")
        )
        source_versions_digest.update(
            selector_id.encode("ascii")
            + b"\0"
            + source_versions_policy_id.encode("ascii")
            + b"\0"
            + source_versions.encode("ascii")
        )
        evidence.append(
            {
                "evidence_id": evidence_id,
                "path": artifact_path,
                "sha256": artifact_sha256,
                "scope_ids": [scope_id],
                "result": outcome.status,
                "producer_id": producer_id,
                "producer_version": "1.0.0",
                "exit_code": 0
                if outcome.status == "passed"
                else 1
                if outcome.status == "failed"
                else 3,
                "test_count": outcome.test_count,
                "skip_count": outcome.skip_count,
                "implementation_revision": implementation_revision,
                "observed_at": observed,
                "valid_until": valid,
            }
        )

    def rows(scope_ids: tuple[str, ...]) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for scope_id in scope_ids:
            if scope_id == "M6-A10":
                result.append(
                    {
                        "id": scope_id,
                        "status": "not_run",
                        "reason_code": "self_completion_pending",
                        "evidence_ids": [],
                    }
                )
                continue
            outcome = outcomes[scope_id]
            result.append(
                {
                    "id": scope_id,
                    "status": outcome.status,
                    "reason_code": outcome.reason_code,
                    "evidence_ids": [by_scope[scope_id]],
                }
            )
        return result

    return {
        "schema_version": "1.0.0",
        "record_type": "agentmonitor.m6_completion_evidence.v1",
        "milestone_id": "V1-M6",
        "implementation_revision": implementation_revision,
        "catalog_sha256": catalog_sha256,
        "selection_sha256": selection_digest.hexdigest(),
        "source_versions_sha256": source_versions_digest.hexdigest(),
        "recorded_at": observed,
        "acceptance": rows(ACCEPTANCE_IDS),
        "stories": rows(STORY_IDS),
        "evidence": evidence,
        "declared_limitations": sorted(limitations),
    }
