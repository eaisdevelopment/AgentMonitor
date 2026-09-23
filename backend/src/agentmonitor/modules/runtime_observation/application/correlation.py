"""Evidence-only M06 session/account correlation policy."""

from agentmonitor.contracts.runtime_observation_v1 import (
    ApprovedStrongCorrelationRuleV1,
    CorrelationEvidenceInputV1,
    SessionCorrelationDecisionV1,
    SessionIdentityV1,
)


def decide_session_correlation(
    session: SessionIdentityV1,
    evidence: tuple[CorrelationEvidenceInputV1, ...],
    approved_rules: tuple[ApprovedStrongCorrelationRuleV1, ...] = (),
) -> SessionCorrelationDecisionV1:
    """Select an account only from one conflict-free Strong evidence set."""
    approved_tuples = {
        (item.rule_id, item.source_id, item.source_version) for item in approved_rules
    }
    applicable = tuple(item for item in evidence if item.session_identity == session)
    evidence_ids = tuple(sorted(item.evidence_id for item in applicable))
    strong_accounts = {
        item.account_id
        for item in applicable
        if item.evidence_class == "strong"
        and item.account_id is not None
        and (item.rule_id, item.source_id, item.source_version) in approved_tuples
    }
    if len(strong_accounts) == 1:
        account_id = next(iter(strong_accounts))
        return SessionCorrelationDecisionV1(
            session_identity=session,
            state="automatic_matched",
            account_id=account_id,
            evidence_ids=evidence_ids,
            reason_code="approved_strong_evidence",
        )
    if len(strong_accounts) > 1:
        return SessionCorrelationDecisionV1(
            session_identity=session,
            state="conflict",
            account_id=None,
            evidence_ids=evidence_ids,
            reason_code="conflicting_strong_evidence",
        )
    has_unapproved_strong = any(
        item.evidence_class == "strong" and item.account_id is not None
        for item in applicable
    )
    return SessionCorrelationDecisionV1(
        session_identity=session,
        state="unresolved",
        account_id=None,
        evidence_ids=evidence_ids,
        reason_code=(
            "approved_strong_evidence_required"
            if has_unapproved_strong
            else "strong_evidence_required"
        ),
    )
