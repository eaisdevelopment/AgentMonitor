# M6 delivery checkpoint — 3 November 2026

This is an implementation checkpoint, not milestone acceptance. The approved
local, process and cloud change plans remain the implementation authority.
The original acceptance scope is unchanged.

## Delivered and observed

- The real Ollama cloud source returned a successful balance and persisted
  included/purchased USD observations at 09:29 UTC. Identity remains
  owner-provided; balance access does not verify an email.
- At `67527dd`, the deployed account page passed the actual browser test for
  native dollar balances, native history, keyboard access and desktop/mobile
  layout. The older observations remained visibly stale.
- `dbcfd26` is deployed through `AUTO-M6-CURRENT-UPDATE` on schema v1_0717.
  Build, static quality, documentation and planning checks passed. HTTP remains
  available; no user agent or default provider profile was changed.
- Local CLI/server 0.24.0 is observed. Its current loopback catalog is empty.
  This does not prove that another desktop application or host has no model.

## Remaining work and ownership

| Work | Current evidence / next action | Owner |
|---|---|---|
| Automatic cloud readings | First success exists; subsequent scheduled dispatch exposed separate registry-revision and lease-counter defects. The former is deployed; the latter is under real private-copy regression. | M04 / integration |
| Repeat connection checks | Receipt-history v1_0718 candidate preserves existing receipts; safe offline rollout/recovery command and subsequent real repeated verification remain to run. | M02 / operations |
| SDK and EAIS scope | One real EAIS account is connected. SDK account or actual shared relationship is still required; owner clarification is pending. | Owner / integration |
| Provider balance comparison | Official Ollama sign-in opened for the existing account. Provider-view reconciliation awaits owner login. | Owner / live operator |
| Model-present local evidence | Loopback daemon reports no installed or loaded models. Real model-present host/source still needs to be established without modifying a provider profile or model. | A03 / live operator |
| Natural failure/recovery and continuity | Current local implementation failures do not count as natural provider failure. Exact read-only evidence producer is being implemented; real conditions remain unobserved. | M04 / integration |
| Full exit and closure | Latest full exit is Failed; owner review and closure follow verified remaining scope. | Integration / owner |

## Latest full check

`AUTO-M6-EXIT` at `dbcfd26` retained the local artifact
`.agentmonitor-local/m6-evidence/direct-dbcfd26c185724bc296601f91d00245c97be2cff-b38bf060d895685a.json`.
Build, quality, docs and planning passed. M6-A01/A08 passed. The local adapter
lane failed two real tests (unadmitted-worker boundary and first runtime tick);
the two focused reruns passed, but this does not turn the full result green.
That failure propagated to A02/A06/A09. A03/A04/A05/A07/A10 remained Not Run.

The direct browser observed actual Ollama processes; the separate native-USD
browser check passed with stale data. Neither replaces fresh cloud collection
or provider-authoritative comparison. No required item is waived, marked done
from code presence alone, or replaced by this checkpoint.

Related evidence: [first cloud response](m6-ollama-body-completion-2026-11-03.md),
[native USD UI](m6-native-usd-account-ui-2026-11-03.md),
[registry revision correction](m6-ollama-registry-revision-admission-2026-11-03.md),
[pre-dispatch recovery](m6-ollama-pre-dispatch-recovery-2026-11-03.md).
