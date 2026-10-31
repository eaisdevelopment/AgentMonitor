"""Exact artifact and scanner subjects for the M0 G1 exit decision."""

from __future__ import annotations

import hashlib
from pathlib import Path


BUNDLE_ARTIFACT_PATHS = tuple(
    sorted(
        (
            "docs/plans/discovery/dependencies/gitleaks-admission.md",
            "docs/plans/discovery/dependencies/python-jsonschema-admission.md",
            "docs/plans/discovery/m0-g1-contract-test-evidence.md",
            "docs/plans/discovery/m0-g1-control-specification.md",
            "docs/plans/discovery/m0-g1-implementation-approval.toml",
            "docs/plans/discovery/m0-g1-record.schema.json",
            "docs/templates/m0-custody-register-template.md",
            "docs/templates/m0-e1-admission-template.md",
            "docs/templates/m0-operation-assertion-packet-template.md",
            "docs/templates/m0-run-result-template.md",
            "docs/templates/m0-scenario-ledger-template.md",
            "docs/templates/m0-stop-incident-template.md",
            "tools/discovery/m0_g1_approve.py",
            "tools/discovery/m0_g1_bundle.py",
            "tools/discovery/m0_g1_custody.py",
            "tools/discovery/m0_g1_exit.py",
            "tools/discovery/m0_g1_records.py",
            "tools/discovery/m0_g1_scanner.py",
            "tools/discovery/requirements-m0-g1.in",
            "tools/discovery/requirements-m0-g1.lock",
            "tools/discovery/test_m0_g1_approval.py",
            "tools/discovery/test_m0_g1_bundle.py",
            "tools/discovery/test_m0_g1_contract.py",
            "tools/discovery/test_m0_g1_exit.py",
            "tools/discovery/test_m0_g1_records.py",
            "tools/automation/run.py",
            "tools/automation/routines.toml",
            "tools/automation/test_run.py",
        )
    )
)


def _artifact(repository_root: Path, relative_path: str) -> dict[str, object]:
    content = (repository_root / relative_path).read_bytes()
    return {
        "path": relative_path,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def bundle_subject(repository_root: Path) -> dict[str, object]:
    """Build the exact review subject from the current real checkout bytes."""

    return {
        "subject_type": "M0G1BundleV1",
        "subject_id": "M0-G1-BUNDLE-001",
        "contract_id": "M0-G1-CONTROLS",
        "contract_version": "0.3.0-draft",
        "artifacts": [
            _artifact(repository_root, path) for path in BUNDLE_ARTIFACT_PATHS
        ],
        "authority": {
            "external_custody_record_access_authorized": True,
            "g1_completion_authorized": True,
            "provider_operations_authorized": False,
            "account_access_authorized": False,
            "g2_authorized": False,
        },
    }


def scanner_subject(repository_root: Path) -> dict[str, object]:
    """Build the exact approved E1 scanner admission subject."""

    binary = repository_root / ".venv-m0-g1/bin/gitleaks"
    wrapper = repository_root / "tools/discovery/m0_g1_scanner.py"
    return {
        "record_type": "E1ScannerAdmissionV1",
        "schema_version": "1.0",
        "admission_id": "E1-GITLEAKS-8300",
        "scanner_name": "gitleaks",
        "scanner_version": "8.30.0",
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "configuration_sha256": hashlib.sha256(wrapper.read_bytes()).hexdigest(),
        "license": "MIT",
        "dependency_review_ref": "REF-DEP-M0-SCANNER-001",
        "telemetry_disabled": True,
        "network_required": False,
        "output_policy": "discard_raw_output",
        "real_verification_status": "Passed",
        "decision": "approved",
        "evidence_ref": "REF-EVID-M0-G1-CONTRACT-002",
        "approvals": [],
    }
