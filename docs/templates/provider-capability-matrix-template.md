# Provider capability matrix: provider and surface

- Status: Discovery
- Adapter owner:
- Discovery date:
- Provider product/version/plan context:
- Platform(s):
- Real account references: opaque local aliases only
- Sources: official URLs/document versions

## Safety declaration

Confirm that discovery is read-only, default profiles are unchanged, no secret/content values are captured, and no unsupported/private endpoint is used without explicit architectural approval.

## Capabilities

| Capability | Available | Official/stable | Account scope | Window/unit semantics | Access method | Auth state impact | Confidence | Evidence/scenario | Known gaps |
|---|---|---|---|---|---|---|---|---|---|
| Auth health | Yes/No/Unknown | Rating | Scope | N/A | Method | Impact | High/Medium/Low | ID | Gaps |
| Quota/usage |  |  |  |  |  |  |  |  |  |
| Cost/budget |  |  |  |  |  |  |  |  |  |
| Session/process discovery |  |  |  |  |  |  |  |  |  |
| Token/model metadata |  |  |  |  |  |  |  |  |  |
| Reauthentication guidance |  |  |  |  |  |  |  |  |  |

Use `Unknown`, never an invented value. Keep different provider windows separate.

## Identity and correlation

Explain which non-secret stable fields can distinguish account, organization/group, profile, session, process, and model. State collision/reuse behavior and where owner confirmation is required.

## Provenance and freshness

For every observation type, define source, observed-at/source-at timestamps, freshness expectation, precision, confidence rationale, and raw-reference policy. Full secret-bearing payloads must not be persisted.

## Failure matrix

| Condition | Observable signal | Classification | Retry/backoff | UI/operator result | Live scenario |
|---|---|---|---|---|---|
| Expired auth | Signal | State | Policy | Result | ID |

Include missing CLI/app, version drift, permission denial, malformed/changed output, partial data, rate limit, network loss, credit exhaustion, and provider outage as applicable.

## Live evidence summary

List Passed/Failed/Blocked/Not Run scenarios without account identifiers or payloads. Link sanitized live reports.

## Adapter recommendation

State implementable capabilities, unsupported capabilities, required contract extensions, residual risks, version-detection strategy, and explicit go/no-go decision. Discovery alone does not authorize implementation.

