# M7 official billing-interface discovery

- Status: documentation discovery; live billing checks **Not Run**.
- Date: 2026-11-11.
- Requirements: FR-BUDGET-001..006; AC-LIVE-004/005/007; AC-OPS-006.
- Baseline: `f7a1799b04be762e1eb81c79d83d50d9bbcfcceb`.
- Method: official documentation and OpenAI's published OpenAPI endpoint schemas.
  No keys, provider profiles, billing payloads, or account configuration inspected.

## Anthropic

The [recommended analytics interface](https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api)
provides separate GET usage and cost reports at
`/v1/organizations/analytics/usage` and `/v1/organizations/analytics/cost`.
The documented beta header is `analytics-usage-cost-2026-08-24`.
Console access requires an administrative credential, distinct from Claude
subscription authentication. Costs are decimal strings in USD cents; distinguish
discounted amount, list amount, and credits. Reports expose refresh time and may
be delayed or revised. Dimensions, bucket size, and query length are constrained.
M7 will label this source experimental while the provider requires beta admission.

The [older Console interface](https://platform.claude.com/docs/en/manage-claude/usage-cost-api)
remains documented, but recommends the new interface for new integrations.
Decision: implement the recommended interface, with explicit version admission;
do not silently switch to the old source when authentication or parsing fails.

The [spend-limit API](https://platform.claude.com/docs/en/manage-claude/spend-limits-api)
describes Enterprise member controls. It does not establish that a Console API
billing account exposes prepaid balance or organization hard limits. Those
fields remain unavailable until an applicable official source is verified.

## OpenAI

The [official usage/cost reference](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage)
and endpoint-specific OpenAPI schemas expose GET `/v1/organization/costs` and
`/v1/organization/usage/*`. They require administrative API authentication.
Cost buckets are daily; queries have bounded pagination and optional dimensions.
Costs and activity counts are different measures. Usage endpoints cover separate
categories; token categories and dimensions vary by endpoint. The completions
report alone must not be labeled all API usage. Cost grouping includes project,
key identifier, line item, user, and API source; some combinations depend on the
organization and period. Unsupported query combinations must remain explicit.

The [official cookbook](https://developers.openai.com/cookbook/examples/completions_usage_api)
also demonstrates administrative credentials and paged usage/cost queries.
Decision: decode numeric JSON directly to exact decimal values, never through
binary floating point. Do not calculate authoritative spend from a price list.
No applicable prepaid balance or hard/soft budget endpoint was established in
this discovery; do not substitute ChatGPT/Codex subscription percentages.

OpenAPI currently lists usage categories: completions, embeddings, moderations,
images, audio speeches/transcriptions, code-interpreter sessions, vector stores,
file-search calls, web-search calls, and decisions. Freeze each category's
allowlisted fields before enabling it; absent dimensions are not zero values.

## Ollama

[Cloud usage](https://docs.ollama.com/api/cloud-usage) provides GET
`https://ollama.com/api/usage`, authenticated by an API key, with fixed 24h/7d/30d
ranges. It exposes totals and buckets, partial current buckets, optional monetary
and token values, and model grouping with a remainder. Legacy plans may provide
request counts only. Team scope requires administrative access. Key/member
breakdowns and custom ranges are not currently offered. The documented limit is
10 requests/minute/user, shared across keys/devices; respect `Retry-After`.

[Balance](https://docs.ollama.com/api/balance) is already collected by M6.
Decision: reuse the existing pool identity and balance observations; do not
duplicate purchased credits or attribute shared cloud usage exclusively to an
API key unless the provider establishes that attribution. New usage collection
requires extending the balance-only runtime credential permission.

## Live prerequisite ledger

| Boundary | What exists | What must still be established |
|---|---|---|
| Anthropic Console | Official documented administrative interface | Owner-selected billing account, locally configured credential, successful permitted read, same-period authoritative comparison |
| OpenAI Platform | Official administrative schemas | Owner-selected billing account, locally configured credential, successful permitted read, same-period authoritative comparison |
| Ollama cloud | Accepted M6 balance collection for two organizations | Owner-enabled usage purpose and real `/api/usage` reconciliation; legacy/paid field availability per actual account |

An unanswered or ambiguous access question is not proof of absent access.
Missing credentials affect that provider's live lane, not independent design,
pure tests, empty real-stack tests, or other providers. Documentation examples
must never become test fixtures or dashboard evidence. Natural 401/403/429,
exhaustion, and delayed/revised-data cases remain Not Run or Blocked unless
observed; deliberately generating spend is outside this plan.
