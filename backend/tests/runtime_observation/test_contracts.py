"""M06 pure identity and correlation rules; these tests perform no I/O."""

from dataclasses import fields
from datetime import UTC, datetime

import pytest
from agentmonitor.contracts import runtime_observation_v1 as runtime_contracts
from agentmonitor.modules.runtime_observation.application.payload_digest import (
    runtime_payload_digest,
)


def _process_snapshot(
    *,
    executable_identity: str | None,
    provider_key: str | None = None,
    installation_id: str | None = None,
) -> runtime_contracts.ProcessSnapshotInputV1:
    missing = runtime_contracts.ProcessMetricFieldV1(
        state="not_requested",
        value=None,
        unit=None,
        reason_code="field_not_requested",
    )
    return runtime_contracts.ProcessSnapshotInputV1(
        observation_id="observation-opaque",
        identity=runtime_contracts.ProcessIdentityV1(
            platform_source="linux.proc.process.v1",
            platform_scope_id="boot-scope-opaque",
            pid=412,
            start_time_ticks=9001,
        ),
        provider_key=provider_key,
        installation_id=installation_id,
        executable_label=runtime_contracts.ProcessLabelFieldV1(
            state="present", value="claude", reason_code=None
        ),
        parent_pid=missing,
        user_cpu_ticks=missing,
        system_cpu_ticks=missing,
        resident_pages=missing,
        thread_count=missing,
        kernel_state=runtime_contracts.ProcessCodeFieldV1(
            state="not_requested", value=None, reason_code="field_not_requested"
        ),
        observed_at=datetime(2026, 9, 23, 9, tzinfo=UTC),
        source_id="linux.proc.process.v1",
        source_version="linux-procfs-stat-exe-v1",
        adapter_version="1.1.0",
        clock_ticks_per_second=100,
        page_size_bytes=4096,
        executable_identity=executable_identity,
    )


def test_pid_is_not_a_process_identity_without_start_ticks() -> None:
    """M06-PURE-001/002: PID reuse must produce a distinct typed identity."""
    assert hasattr(runtime_contracts, "ProcessIdentityV1")
    identity_type = runtime_contracts.ProcessIdentityV1

    first = identity_type(
        platform_source="linux.proc.process.v1",
        platform_scope_id="boot-scope-one",
        pid=412,
        start_time_ticks=9001,
    )
    reused = identity_type(
        platform_source="linux.proc.process.v1",
        platform_scope_id="boot-scope-one",
        pid=412,
        start_time_ticks=9002,
    )

    assert first != reused


def test_same_pid_and_start_on_another_boot_is_a_distinct_process() -> None:
    """M06-PURE-001: boot scope prevents cross-reboot PID collisions."""
    first = runtime_contracts.ProcessIdentityV1(
        platform_source="linux.proc.process.v1",
        platform_scope_id="boot-scope-one",
        pid=412,
        start_time_ticks=9001,
    )
    after_reboot = runtime_contracts.ProcessIdentityV1(
        platform_source="linux.proc.process.v1",
        platform_scope_id="boot-scope-two",
        pid=412,
        start_time_ticks=9001,
    )

    assert first != after_reboot


def test_weak_process_evidence_cannot_select_an_account() -> None:
    """M06-PURE-019: process/provider coincidence remains unresolved."""
    assert hasattr(runtime_contracts, "CorrelationEvidenceInputV1")
    assert hasattr(runtime_contracts, "SessionIdentityV1")
    from agentmonitor.modules.runtime_observation.application import correlation

    session = runtime_contracts.SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-opaque",
        identity_kind="process_instance",
        identity_value="session-opaque",
    )
    evidence = runtime_contracts.CorrelationEvidenceInputV1(
        evidence_id="evidence-opaque",
        session_identity=session,
        evidence_class="weak",
        rule_id="claude.process_provider_match.v1",
        account_id=None,
        observed_at=datetime(2026, 9, 22, 12, tzinfo=UTC),
        source_id="linux.proc.process.v1",
        source_version="1.0.0",
        reason_code="process_provider_match_only",
    )

    decision = correlation.decide_session_correlation(session, (evidence,))

    assert decision.state == "unresolved"
    assert decision.account_id is None
    assert decision.reason_code == "strong_evidence_required"


def test_explicit_approved_strong_policy_can_select_exactly_one_account() -> None:
    """M06-PURE-018/020: automatic mapping is Strong-only and conflict-safe."""
    assert hasattr(runtime_contracts, "CorrelationEvidenceInputV1")
    assert hasattr(runtime_contracts, "SessionIdentityV1")
    from agentmonitor.modules.runtime_observation.application import correlation

    session = runtime_contracts.SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-opaque",
        identity_kind="provider_session",
        identity_value="session-opaque",
    )
    evidence = runtime_contracts.CorrelationEvidenceInputV1(
        evidence_id="evidence-strong",
        session_identity=session,
        evidence_class="strong",
        rule_id="claude.targeted_profile.v1",
        account_id="account-opaque",
        observed_at=datetime(2026, 9, 22, 12, tzinfo=UTC),
        source_id="claude.targeted_profile.v1",
        source_version="1.0.0",
        reason_code="exact_targeted_profile_join",
    )

    policy = runtime_contracts.ApprovedStrongCorrelationRuleV1(
        rule_id="claude.targeted_profile.v1",
        source_id="claude.targeted_profile.v1",
        source_version="1.0.0",
        decision_reference="owner-reviewed-policy-001",
    )
    decision = correlation.decide_session_correlation(
        session, (evidence,), approved_rules=(policy,)
    )

    assert decision.state == "automatic_matched"
    assert decision.account_id == "account-opaque"


def test_current_claude_targeted_rule_is_unresolved_without_approved_policy() -> None:
    """M0 handoff has no targeted-profile probe evidence or approved rule."""
    from agentmonitor.modules.runtime_observation.application import correlation

    session = runtime_contracts.SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-opaque",
        identity_kind="provider_session",
        identity_value="session-opaque",
    )
    evidence = runtime_contracts.CorrelationEvidenceInputV1(
        evidence_id="evidence-not-yet-approved",
        session_identity=session,
        evidence_class="strong",
        rule_id="claude.targeted_profile.v1",
        account_id="account-opaque",
        observed_at=datetime(2026, 9, 22, 12, tzinfo=UTC),
        source_id="claude.targeted_profile.v1",
        source_version="1.0.0",
        reason_code="not_live_validated",
    )

    decision = correlation.decide_session_correlation(session, (evidence,))

    assert decision.state == "unresolved"
    assert decision.account_id is None


def test_unapproved_strong_rule_cannot_select_an_account() -> None:
    """AC-PROC-003: the strength label alone never authorizes attribution."""
    from agentmonitor.modules.runtime_observation.application import correlation

    session = runtime_contracts.SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-opaque",
        identity_kind="provider_session",
        identity_value="session-opaque",
    )
    evidence = runtime_contracts.CorrelationEvidenceInputV1(
        evidence_id="evidence-unapproved",
        session_identity=session,
        evidence_class="strong",
        rule_id="unapproved.rule.v999",
        account_id="account-opaque",
        observed_at=datetime(2026, 9, 22, 12, tzinfo=UTC),
        source_id="unapproved.source",
        source_version="999.0.0",
        reason_code="caller_claimed_strong",
    )

    decision = correlation.decide_session_correlation(session, (evidence,))

    assert decision.state == "unresolved"
    assert decision.account_id is None
    assert decision.reason_code == "approved_strong_evidence_required"


def test_runtime_contracts_cannot_carry_prohibited_private_fields() -> None:
    """NFR-SEC-001: the closed ingest schemas have no private-data escape hatch."""
    prohibited = {
        "argv",
        "command_line",
        "content",
        "environment",
        "metadata",
        "prompt",
        "raw_path",
        "response",
        "terminal",
        "tool_activity",
    }
    contract_types = (
        runtime_contracts.ProcessSnapshotInputV1,
        runtime_contracts.LocalSessionObservationInputV1,
        runtime_contracts.RuntimeMetricObservationInputV1,
        runtime_contracts.CorrelationEvidenceInputV1,
    )

    for contract_type in contract_types:
        assert {field.name for field in fields(contract_type)}.isdisjoint(prohibited)


def test_session_query_record_requires_closed_observation_provenance() -> None:
    """CTR-RUN-002: session list/tree views cannot discard source provenance."""
    assert "provenance" in {
        field.name for field in fields(runtime_contracts.AgentSessionRecordV1)
    }


def test_metric_interval_and_overlap_semantics_fail_closed() -> None:
    """CTR-RUN-002: gauge and interval metadata cannot contradict each other."""
    session = runtime_contracts.SessionIdentityV1(
        provider_key="claude",
        installation_id="installation-opaque",
        identity_kind="provider_session",
        identity_value="session-opaque",
    )

    with pytest.raises(
        runtime_contracts.InvalidRuntimeObservationV1,
        match="runtime_metric_interval_invalid",
    ):
        runtime_contracts.RuntimeMetricObservationInputV1(
            metric_id="metric-opaque",
            session_identity=session,
            process_identity=None,
            metric_kind="input_tokens",
            coefficient="1",
            scale=0,
            unit="token",
            scope="session",
            semantics="gauge",
            overlap_class="not_applicable",
            interval_start=datetime(2026, 9, 22, 11, tzinfo=UTC),
            interval_end=datetime(2026, 9, 22, 12, tzinfo=UTC),
            observed_at=datetime(2026, 9, 22, 12, tzinfo=UTC),
            source_id="approved.local.source.v1",
            source_version="1.0.0",
            parser_version="1.0.0",
            provider_version="2.1.278",
        )


def test_kernel_state_code_and_executable_label_have_distinct_bounds() -> None:
    """CTR-RUN-006: a multi-character comm label is never a kernel-state code."""
    with pytest.raises(
        runtime_contracts.InvalidRuntimeObservationV1,
        match="runtime_process_code_value_invalid",
    ):
        runtime_contracts.ProcessCodeFieldV1(
            state="present", value="claude", reason_code=None
        )

    label = runtime_contracts.ProcessLabelFieldV1(
        state="present", value="claude", reason_code=None
    )
    assert label.value == "claude"


def test_attributed_process_requires_safe_executable_identity_fingerprint() -> None:
    """CTR-RUN-001/006: attribution cannot rely on a label or raw identity."""
    with pytest.raises(
        runtime_contracts.InvalidRuntimeObservationV1,
        match="runtime_process_attribution_invalid",
    ):
        _process_snapshot(
            executable_identity=None,
            provider_key="claude",
            installation_id="installation-opaque",
        )

    attributed = _process_snapshot(
        executable_identity="a" * 64,
        provider_key="claude",
        installation_id="installation-opaque",
    )
    assert attributed.executable_identity == "a" * 64


@pytest.mark.parametrize("value", ("a" * 63, "A" * 64, "g" * 64, "sha256:a"))
def test_executable_identity_rejects_noncanonical_or_raw_values(value: str) -> None:
    """CTR-RUN-001/006: only lowercase SHA-256 is a safe executable identity."""
    with pytest.raises(
        runtime_contracts.InvalidRuntimeObservationV1,
        match="runtime_executable_identity_invalid",
    ):
        _process_snapshot(executable_identity=value)


def test_generic_process_may_omit_executable_identity() -> None:
    """FR-DISC-001/002: unresolved generic process facts remain representable."""
    generic = _process_snapshot(executable_identity=None)

    assert generic.provider_key is None
    assert generic.installation_id is None
    assert generic.executable_identity is None


def test_executable_identity_participates_in_canonical_payload_digest() -> None:
    """CTR-COL-006: executable evidence changes the idempotency fingerprint."""
    generic = runtime_contracts.RuntimeObservationBatchV1(
        process_snapshots=(_process_snapshot(executable_identity=None),),
        session_observations=(),
        correlation_evidence=(),
        completeness="complete_scope",
    )
    identified = runtime_contracts.RuntimeObservationBatchV1(
        process_snapshots=(_process_snapshot(executable_identity="a" * 64),),
        session_observations=(),
        correlation_evidence=(),
        completeness="complete_scope",
    )

    assert runtime_payload_digest(generic) != runtime_payload_digest(identified)
