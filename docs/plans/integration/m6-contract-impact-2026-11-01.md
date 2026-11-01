# M6 contract-impact assessment

**Status: Draft; decisions and implementation are not approved.** This is a
working assessment against integration baseline `ea37a3f`, not a substitute
for the A03 module plan or live capability admission. It covers M6-A01–A10
and ST-OLL-001–005 in the [ticket catalog](m6-ticket-catalog-v1.json).

| Boundary | Existing evidence | Decision required before implementation |
|---|---|---|
| M02 registry | Provider keys are bounded strings; accounts have installation, resource and organization relationships. | Define how an Ollama cloud identity and a local service are registered independently. Never infer one from the other. Determine how shared team balances are represented without counting them once per member. |
| M03 provider protocol | `ProviderAdapterV1` owns manifests and capability ports; bootstrap currently registers Claude and Codex only. | Specify Ollama capability IDs, exact source/version admission, unsupported lanes, sanitized errors and ownership of new provider-specific schemas. |
| Local catalog and runtime | Real loopback version/tags/ps endpoints responded; current data contains no models. No typed public installed/loaded-model catalog contract was identified. | M03/M06 and P01 must define a versioned catalog view distinguishing installed, loaded and unknown activity, with source, timestamp, safe metadata, partial results and bounds. Do not claim a loaded model is actively working or linked to an account. Verify nonempty response fields before freezing them. |
| M04 collection | Existing collection orchestration and committed outcomes own collection lifecycle and idempotency. | Define rate-limited local/cloud collection, independent failures and recovery, and the existing commit path; no adapter database writes. |
| M05 capacity | `CTR-CAP-001` supports exact decimal quantities, bounded windows and ratios, while `CTR-COMMON-003` also has exact money. Each existing capacity subject has an account and resource. | Decide the source-backed identity of shared pools, separate included and purchased balances, currency and period representation, legacy remaining percentages and native reset semantics. Verify how exact money reaches history/API/UI without silently treating currency as a percentage. Contract/API versioning and migration depend on that decision. |
| M06/A04 runtime | Runtime contract includes provider values and bounded process evidence, but does not prove a model-to-process or process-to-account relationship. | Document permitted Linux metadata and correlation evidence; preserve unknown, permissions and coverage limits. Do not read process environment, process memory, prompts or response content. |
| P01 API and P02 UI | Existing clients use the versioned API; provider filtering is generic. The account page has provider-specific connection views. | Publish any new model/balance fields through a versioned API and regenerated client; render native resource units, freshness, error states, account scope and unknown correlations. Retain promotion and support controls. |
| IAM/security/configuration | Ollama local API is unauthenticated; official direct cloud API requires a key. | Define a trusted local endpoint policy and an AgentMonitor-managed secret reference; no secret goes to browser/source/logs or default profile. Decide owner-driven provisioning and key lifetime before enabling cloud calls. |
| Database/events | Capacity history and alerts have existing owners and idempotency contracts. | Establish whether schema or event changes are necessary from the above decisions. If breaking, supply a versioned migration and ADR; if not, document compatibility and rollback. |

## Source facts versus open questions

Official [local authentication](https://docs.ollama.com/api/authentication),
[balance](https://docs.ollama.com/api/balance) and
[usage](https://docs.ollama.com/api/cloud-usage) documentation describe the
interfaces; they are not evidence of the owner's actual plan, account identity,
role, team relationship, response shape or permissions. Balance has documented
included/purchased and legacy-window variants, team-sharing semantics and a
per-user 10 requests/minute limit across keys and devices. The exact safe
limiter and persistence policy must account for other devices and `Retry-After`.

Local model-present and both cloud account cases remain unverified. The
mandatory M0 preflight is currently blocked as documented in the
[discovery evidence](../../evidence/m6-baseline-discovery-2026-11-01.md).
Resolve that runbook gap and complete appropriately authorized evidence before
claiming source admission. The final A03 plan must map each decision to its
owner, source, tests, paths, rollback and acceptance IDs; this draft does not
authorize production changes.
