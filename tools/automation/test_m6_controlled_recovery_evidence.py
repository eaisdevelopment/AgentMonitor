"""Pure receipt rules; constructed values never replace provider observations."""

import hashlib
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta

import pytest
from agentmonitor.contracts.collection_recovery_v1 import (
    CollectionRecoveryRunV1,
    CollectionRecoveryScopeV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1

from tools.automation.implementations.m6_controlled_recovery_evidence import (
    ControlledNetworkWitnessV1,
    build_controlled_recovery_evidence_v1,
    parse_controlled_recovery_interval_v1,
)

NOW = datetime(2026, 11, 4, 15, tzinfo=UTC)
REVISION = "a" * 40
INVOCATION = "b" * 32
ATTEMPT = "c" * 32


def at(seconds):
    return NOW + timedelta(seconds=seconds)


def scope():
    return CollectionRecoveryScopeV1(
        account_id=OpaqueIdV1("account"),
        access_target_id=OpaqueIdV1("target"),
        binding_generation=2,
        capability_id="cloud.balance",
        source_id="cloud-source",
        adapter_version="1.0.0",
        source_fingerprint="d" * 64,
        payload_schema="balance.v1",
        provider_key="ollama",
    )


def run(identifier="failure", **changes):
    fields = {
        name: getattr(scope(), name)
        for name in (
            "account_id",
            "access_target_id",
            "binding_generation",
            "capability_id",
            "source_id",
            "adapter_version",
            "source_fingerprint",
            "payload_schema",
            "provider_key",
        )
    }
    fields.update(
        run_id=OpaqueIdV1(identifier),
        provider_target_kind="cloud_service",
        requested_at=at(-90),
        completed_at=at(-85),
        state="failed",
        dispatch_certainty="not_started",
        response_outcome=None,
        failure_code="provider_unavailable",
        payload_digest=None,
        observation_ids=(),
    )
    fields.update(changes)
    return CollectionRecoveryRunV1(**fields)


def successful(identifier, **changes):
    return run(
        identifier,
        **dict(
            requested_at=at(-30),
            completed_at=at(-25),
            state="succeeded",
            dispatch_certainty="response_received",
            response_outcome="succeeded",
            failure_code=None,
            payload_digest="e" * 64,
            observation_ids=(OpaqueIdV1("observation-" + identifier),),
            **changes,
        ),
    )


def arguments():
    return dict(
        revision=REVISION,
        service_invocation_id=INVOCATION,
        attempt_id=ATTEMPT,
        scope=scope(),
        witness=ControlledNetworkWitnessV1(
            attempt_id=ATTEMPT,
            source_revision=REVISION,
            service_invocation_id=INVOCATION,
            worker_pid=321,
            worker_start_ticks=456,
            parent_namespace_inode=101,
            worker_namespace_inode=102,
            failure_run_id="failure",
            started_at=at(-100),
            completed_at=at(-80),
            cleanup_confirmed=True,
        ),
        failure=run(),
        recovery=successful("recovery"),
        dashboard_observed_at=(at(-95), at(-70), at(-20)),
        continuity_runs=(
            successful(
                "claude-run", provider_key="claude", capability_id="subscription.quota"
            ),
            successful(
                "codex-run", provider_key="codex", capability_id="subscription.quota"
            ),
        ),
        now=NOW,
    )


def parse(value, **changes):
    return parse_controlled_recovery_interval_v1(
        value,
        **dict(
            revision=REVISION,
            service_invocation_id=INVOCATION,
            attempt_id=ATTEMPT,
            return_code=0,
            now=NOW,
            **changes,
        ),
    )


def document():
    return json.loads(
        json.dumps(asdict(build_controlled_recovery_evidence_v1(**arguments())))
    )


def test_controlled_evidence_is_separate_and_round_trips():
    result = parse(document())
    assert result.controlled_recovery_targets == 1
    assert result.natural_recovery_targets == 0
    assert result.recovery_run_pairs == (("failure", "recovery"),)
    assert result.continuity_run_ids == (
        ("claude", "claude-run"),
        ("codex", "codex-run"),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("attempt_id", "f" * 32),
        ("source_revision", "f" * 40),
        ("service_invocation_id", "f" * 32),
        ("worker_namespace_inode", 101),
        ("worker_pid", 0),
        ("worker_start_ticks", False),
        ("failure_run_id", "another-run"),
        ("cleanup_confirmed", False),
        ("started_at", at(-88)),
        ("completed_at", at(-86)),
    ],
)
def test_foreign_missing_or_unowned_witness_rejected(field, value):
    args = arguments()
    args["witness"] = replace(args["witness"], **{field: value})
    with pytest.raises(ValueError, match="m6_controlled_recovery_evidence_invalid"):
        build_controlled_recovery_evidence_v1(**args)


def test_witness_required():
    args = arguments()
    args["witness"] = None
    with pytest.raises(ValueError):
        build_controlled_recovery_evidence_v1(**args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("account_id", OpaqueIdV1("other-account")),
        ("access_target_id", OpaqueIdV1("other-target")),
        ("binding_generation", 3),
        ("source_id", "other-source"),
        ("adapter_version", "2.0.0"),
        ("source_fingerprint", "f" * 64),
        ("payload_schema", "other.v1"),
        ("capability_id", "other-capability"),
        ("provider_key", "codex"),
        ("provider_target_kind", "local"),
    ],
)
@pytest.mark.parametrize("which", ["failure", "recovery"])
def test_both_runs_bound_to_exact_scope(which, field, value):
    args = arguments()
    args[which] = replace(args[which], **{field: value})
    with pytest.raises(ValueError):
        build_controlled_recovery_evidence_v1(**args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("state", "blocked"),
        ("dispatch_certainty", "response_received"),
        ("response_outcome", "failed"),
        ("failure_code", "unauthorized"),
        ("payload_digest", "f" * 64),
        ("observation_ids", (OpaqueIdV1("unexpected"),)),
    ],
)
def test_only_real_no_response_failure_qualifies(field, value):
    args = arguments()
    args["failure"] = replace(args["failure"], **{field: value})
    with pytest.raises(ValueError):
        build_controlled_recovery_evidence_v1(**args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("state", "failed"),
        ("dispatch_certainty", "not_started"),
        ("response_outcome", None),
        ("failure_code", "provider_unavailable"),
        ("payload_digest", None),
        ("observation_ids", ()),
        ("requested_at", at(-95)),
        ("run_id", OpaqueIdV1("failure")),
    ],
)
def test_recovery_must_be_later_and_committed(field, value):
    args = arguments()
    args["recovery"] = replace(args["recovery"], **{field: value})
    with pytest.raises(ValueError):
        build_controlled_recovery_evidence_v1(**args)


@pytest.mark.parametrize(
    "value",
    [(), (at(-95),), (at(-95), at(-20)), (at(-70), at(-60)), (at(-20), at(-70))],
)
def test_dashboard_requires_failure_and_recovered_samples(value):
    args = arguments()
    args["dashboard_observed_at"] = value
    with pytest.raises(ValueError):
        build_controlled_recovery_evidence_v1(**args)


@pytest.mark.parametrize(
    "mutation", ["missing", "foreign", "early", "uncommitted", "duplicate"]
)
def test_real_cross_provider_interval_references_required(mutation):
    args = arguments()
    first, second = args["continuity_runs"]
    args["continuity_runs"] = {
        "missing": (first,),
        "foreign": (first, replace(second, provider_key="ollama")),
        "early": (first, replace(second, requested_at=at(-120))),
        "uncommitted": (first, replace(second, observation_ids=())),
        "duplicate": (first, replace(second, run_id=first.run_id)),
    }[mutation]
    with pytest.raises(ValueError):
        build_controlled_recovery_evidence_v1(**args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("attempt_id", "f" * 32),
        ("source_revision", "f" * 40),
        ("service_invocation_id", "f" * 32),
        ("cleanup_confirmed", False),
        ("worker_namespace_inode", 101),
        ("scope_sha256", "invalid"),
        ("lineage_sha256", "f" * 64),
        ("controlled_recovery_targets", 0),
        ("cross_provider_continuity_targets", 0),
        ("dashboard_sample_count", 1),
        ("started_at", at(-661).isoformat()),
        ("completed_at", at(-31).isoformat()),
        ("status", "passed-but-incomplete"),
        ("natural_recovery_targets", 1),
    ],
)
def test_serialized_reused_stale_or_altered_receipts_rejected(field, value):
    data = document()
    data[field] = value
    if field != "lineage_sha256":
        data["lineage_sha256"] = hashlib.sha256(
            json.dumps(
                {key: item for key, item in data.items() if key != "lineage_sha256"},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    with pytest.raises(ValueError):
        parse(data)


def test_nonzero_process_status_cannot_pass():
    with pytest.raises(ValueError):
        parse_controlled_recovery_interval_v1(
            document(),
            revision=REVISION,
            service_invocation_id=INVOCATION,
            attempt_id=ATTEMPT,
            return_code=3,
            now=NOW,
        )


@pytest.mark.parametrize("dispatch", ["not_started", "may_have_started"])
@pytest.mark.parametrize("state", ["succeeded", "partial"])
def test_actual_no_response_dispatch_variants_with_committed_recovery(dispatch, state):
    args = arguments()
    args["failure"] = replace(args["failure"], dispatch_certainty=dispatch)
    args["recovery"] = replace(args["recovery"], state=state)
    assert (
        build_controlled_recovery_evidence_v1(**args).controlled_recovery_targets == 1
    )


def test_duration_limit_and_freshness_boundary():
    args = arguments()
    args["witness"] = replace(args["witness"], started_at=at(-660))
    data = json.loads(json.dumps(asdict(build_controlled_recovery_evidence_v1(**args))))
    assert (
        parse_controlled_recovery_interval_v1(
            data,
            revision=REVISION,
            service_invocation_id=INVOCATION,
            attempt_id=ATTEMPT,
            return_code=0,
            now=at(30),
        ).controlled_recovery_targets
        == 1
    )
    with pytest.raises(ValueError):
        parse_controlled_recovery_interval_v1(
            data,
            revision=REVISION,
            service_invocation_id=INVOCATION,
            attempt_id=ATTEMPT,
            return_code=0,
            now=at(31),
        )
    args["witness"] = replace(args["witness"], started_at=at(-661))
    with pytest.raises(ValueError):
        build_controlled_recovery_evidence_v1(**args)


def test_claude_codex_continuity_uses_provider_neutral_committed_run_metadata():
    args = arguments()
    args["continuity_runs"] = tuple(
        replace(run, dispatch_certainty=None, response_outcome=None)
        for run in args["continuity_runs"]
    )
    result = build_controlled_recovery_evidence_v1(**args)
    assert result.cross_provider_continuity_targets == 1


def test_other_provider_capability_is_not_quota_continuity():
    args = arguments()
    first, second = args["continuity_runs"]
    args["continuity_runs"] = (
        first,
        replace(second, capability_id="installation.discovery"),
    )
    with pytest.raises(ValueError):
        build_controlled_recovery_evidence_v1(**args)
