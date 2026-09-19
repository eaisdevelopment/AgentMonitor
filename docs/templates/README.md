# Reusable templates

These templates are mandatory starting points for planning, decision-making, verification, and handoff. Copy a template into the task's approved documentation location, replace every instruction marker, and remove sections only when the completed document explains why they do not apply.

| Template | Use |
|---|---|
| [ADR](adr-template.md) | A durable architectural or cross-module decision |
| [Module plan](module-plan-template.md) | Design and verification plan for one isolated module |
| [Change plan](change-plan-template.md) | Bounded change inside an approved module plan |
| [Provider capability matrix](provider-capability-matrix-template.md) | Evidence-based provider discovery and adapter scope |
| [Live test report](live-test-report-template.md) | Sanitized evidence from real accounts/processes/platforms |
| [Test evidence](test-evidence-template.md) | Red/green/refactor and multi-layer test record |
| [Sub-agent handoff](subagent-handoff-template.md) | Inspectable completion or blocked-work packet |
| [M0 custody register](m0-custody-register-template.md) | External owner-only evidence custody and alias register |
| [M0 operation/assertion packet](m0-operation-assertion-packet-template.md) | Exact reviewed discovery procedure and real-boundary assertions |
| [M0 scenario ledger](m0-scenario-ledger-template.md) | Complete Passed/Failed/Blocked/Not Run accounting |
| [M0 run result](m0-run-result-template.md) | Immutable post-run result and per-assertion evidence manifest |
| [M0 E1 admission](m0-e1-admission-template.md) | Machine scan plus human allowlist gate before repository entry |
| [M0 stop/incident record](m0-stop-incident-template.md) | Sanitized response to unexpected data or side effects |

The approval tables in these aids project detached `ApprovalRecordV1` records.
A Markdown form is an authoring aid; the validated closed JSON record is the
contract artifact.

## Template rules

- Do not put credentials, tokens, account email addresses, prompt/response content, source code, full provider payloads, or process environments in a completed template.
- Use stable requirement, acceptance, contract, module, test, and risk IDs.
- `Blocked`, `Not Run`, `Failed`, and `Passed` are distinct states. Never convert the first three into `Passed`.
- State facts separately from assumptions and unresolved discovery questions.
- Link to durable repository artifacts. External live evidence may remain outside Git when it can expose sensitive metadata; record only its sanitized reference and custodian.
- A copied template does not constitute approval. Record the approver and approval date explicitly.
- General templates such as the provider-capability matrix and live-test report
  are not substitutes for an M0 canonical record. When used for M0 they remain
  subject to opaque-reference, external-custody, owner-timezone, E1-admission,
  and prohibited-data controls; names, URLs, paths, raw timezone names, and
  provider values must not be copied into repository-safe evidence.
