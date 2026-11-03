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

## Later observed progress

The source/collection lease correction was deployed at `9ac684c`. The service
itself collected a new successful cloud reading at **13:04:31 UTC**, without an
operator-triggered provider request. Both USD windows became fresh and the
actual account UI reported monitoring scheduled. The native-USD browser check
passed again with those fresh readings. This is one automatic success, not
yet proof of uninterrupted subsequent cycles.

The bounded local admission command was rerun once on an isolated clean
`9ac684c` checkout. `AUTO-M6-LOCAL-ADMIT` passed: **111 tests, zero failures,
errors or skips**, plus real authenticated API and built-browser checks.
Its source/test digest was
`0f915a6fd9378d38bc3ade3e3fb46e05319c33cb4cd39a5958b571af14681597`.
Together with the real version/installation observations, this completes
M6-T002's local-installation inventory. It does not complete the separate
model-host task or full M6 gate.

Following that passing local test run, the live cloud supervisor reported
`worker_unavailable`. Its global worker-name discovery crosses data-root
boundaries; an isolated two-supervisor regression and namespace correction
are being prepared. Thus sustained scheduled collection is still under test.

The current-history evidence query also had an off-by-one-microsecond range
error. After the [bounded-range correction](m6-history-snapshot-bound-2026-11-03.md),
the actual read-only snapshot passed and reported one verified, current cloud
target with matching history lineage. No observation was manufactured to
make that check pass.

## Deployed correction and actual re-verification

`22d572c` was deployed using `AUTO-M6-CUTOVER` and
`AUTO-M6-FINALIZE-CANDIDATE`, both successful. The installed database is now
`v1_0718`; the dashboard is active and `Restart=on-failure` is restored. An
automatic cloud success at **13:26:51 UTC** made both monetary windows fresh.
The actual native-USD browser test passed for both windows and history.

The real repeated-verification test subsequently passed in 6.26 seconds,
proving that a later receipt becomes current while the previous one remains
readable with its original lineage. Both private-root overlap and legacy
worker-isolation tests passed after deployment (2 tests, 2.75 seconds); the
live connection still reported `scheduled` with fresh observations afterward.
A later automatic cycle remains required for sustained collection evidence.

That subsequent service-owned cycle committed both windows at **13:36:00 UTC**
after the overlap tests, with a received provider response and two committed
observations. Overview also rendered both real native USD amounts as Current.

The official Ollama Usage page is now signed in. Its visible balance comparison
is being integrated into the canonical command with owner-asserted pairing and
the provider's displayed precision; it is not yet a passing M6-A04 artifact.
The recovery producer has been integrated locally. Review found that the
durable `provider_unavailable` code cannot distinguish a remote outage from
a local body-read error after HTTP 200; that ambiguous code is excluded from
natural recovery evidence. Exact 401/403/429 response outcomes remain eligible.
The final invocation and latest-recovery checks are under correction before
any positive M6-A07 claim.

## Subsequent verification and remaining technical failure

The final-invocation/latest-terminal-state corrections and exact bounded-reader
ownership mappings are integrated. The combined recovery/direct/gate suite
passed **75 tests**. Canonical quality, planning and documentation checks passed
at `8bfcbda`. A signed-in official Usage comparison passed at **13:42:32 UTC**
for the one connected account, with explicit owner-asserted pairing and provider
display precision. Multi-scope aggregation remains under integration.

`AUTO-M6-LOCAL-ADMIT` at `a611cd7` failed its real adapter/HTTP lane. Its failed
test cache identifies the direct Ollama runtime-collection test, which passed
alone in 0.82 seconds. A separate run of the exact suite reproduced a first-tick
collector failure: **114 passed, 1 failed**, zero skips. The failed private
database had no collection runs. Instrumented and focused diagnostic runs
passed, so the cause is unresolved; no timeout increase, assertion weakening,
or passing-suite substitution is accepted. A closed failure-reason diagnostic
is being added to expose the next real occurrence.

For existing Claude continuity, three managed targets are due but stop at the
identity check; three have prior `usage_process_exited_before_complete_render`
outcomes that the existing approved retry policy treats as non-transient. One
bounded official managed-profile status check at **13:39:17 UTC** returned
`loggedIn=false` using the service-pinned Claude 2.1.289 executable. This proves
that one profile needs official sign-in; it does not prove token expiry or the
state of the other profiles. No login, enrollment, profile alteration or agent
restart was performed. The registry/executable version mismatch also prevents
treating blanket reenrollment as a verified remedy.

The local inventory at **13:38:43 UTC** still observed Ollama 0.24.0 with zero
installed and loaded models. The model-present source and SDK cloud relationship
remain owner/environment prerequisites. No unavailable scenario is counted as
passed, and this checkpoint does not close M6.

## Canonical browser lineage correction

At deployed revision `9de11440e73afa05908e2e91a856ec6e15126b58`,
`AUTO-M6-EXIT` passed build, local admission, quality, documentation and planning,
but its installed browser checker reported `ollama_dashboard_lineage_mismatch`.
The focused command reproduced that failure with one confirmed cloud target
and zero reconciled targets:

```bash
node frontend/tests/browser/m6/verify_ollama_dashboard.mjs \
  9de11440e73afa05908e2e91a856ec6e15126b58
```

The checker selected a table labelled `Quota windows table`; the actual P02
markup labels its surrounding region. The technical table and exact source
observations existed. The correction selects that actual region, waits for
positive ready-state markup, opens Technical details and Usage history using
their real controls, and requires both tables to be visible. Exact value,
window/role, source, account, freshness, observation, historical-run and digest
checks remain intact. The technical renderer still includes exact coefficient
and scale beside readable USD, so no comparison precision was relaxed.

The same focused command then passed all five browser results: account admin,
cloud capacity, history, process visibility and dashboard continuity. One real
cloud target reconciled to both current and historical observations with equal
nonempty lineage digests. These are candidate checker results against the
existing deployed product, not a full M6 pass.

Owner: integration verification/P02 boundary. Requirements: FR-QUOTA-001/002/004/006,
M6-A04/A05/A09 and AC-UI-005. Consumed quota/history V2 API contracts are unchanged.
Changed artifact: `frontend/tests/browser/m6/verify_ollama_dashboard.mjs` and this
record. No production, migration, dependency, license or secret-handling change.
The check only navigates its own authenticated tab and reads the actual API/DOM;
it preserves the owner tabs and performs no registry or provider mutation.
Full current-revision acceptance still requires canonical execution and the
previously documented missing environment/provider outcomes.

## Current deployed canonical result — 14:10 UTC

`AUTO-M6-CURRENT-UPDATE` successfully activated
`894f092ebcdb5beaa545eaf185a6fead14b0b234` on schema v1_0718 and restored the
original restart policy. The subsequent `AUTO-M6-EXIT` returned **3**, with no
failed criterion and no completion receipt. Build, local admission, quality,
documentation and planning all passed. Independent review of the browser
correction found no weakened assertion or blocking issue.

- **Passed:** M6-A01, M6-A06, M6-A08 and ST-OLL-001.
- **Not Run / incomplete:** M6-A02 (second local host not observed), M6-A03
  (required owner-confirmed cloud scope missing), M6-A04/A05/A09 (depend on that
  missing scope), M6-A07 (no current qualifying natural failure to observe
  recovery), and M6-A10 (technical completion and owner review still pending).
- Real installed browser results all passed. One cloud target reconciled
  current values, retained history and the official Usage display with the
  same source lineage. The official comparison finished at 14:10:40 UTC and
  used the actual 14:06:59 UTC provider observation. This is one account, not
  evidence of the missing organization or a shared pool.
- One Ollama 0.24.0 loopback host was observed at 14:10:27 UTC: zero installed
  and zero loaded models. Two real process observations were present. Zero
  configured alert targets were observed; no live alert lifecycle is claimed.
- The earlier intermittent runtime admission failure did not recur in this
  run; its underlying cause remains unresolved. The added diagnostics are not
  represented as a behavioral fix. Existing Claude continuity limitations
  above also remain unresolved.

Retained private artifact:
`.agentmonitor-local/m6-evidence/direct-894f092ebcdb5beaa545eaf185a6fead14b0b234-b4ec9f387c007935.json`.
SHA-256: `b4ec9f387c007935510c8eaadfad4aed3c82bdab52e002bd0dbbae12d56b9679`.
The documentation index and machine-readable V1 implementation overlay now
reflect this in-progress state instead of claiming M6 has never started.
This documentation-only follow-up does not change the deployed code revision
or convert the incomplete canonical result into a pass.

## Remaining implementation gaps found by scope audit

The incomplete result above must not be described as only missing owner input.
The initial audit at `894f092` found a host-scope contradiction and a cloud contract gap. The host contradiction is resolved by the subsequent owner-direction reconciliation below; it is not a current requirement for another machine:

1. `auto_m6_exit._run_local_inventory` accepts one local inventory record and
   returns one host. Its sole caller runs it once. Consequently A02's two-host
   condition cannot pass through the current canonical producer, even with
   another real machine available. The approved local slice intentionally
   permits only the fixed loopback service. Model-present evidence on the owner-identified local host remains necessary.
   If additional hosts are registered later, their transport/admission and
   evidence collection need implementation; supplying an address alone would
   not finish that additional path.
2. A03 currently requires two credential-bound active targets. Its snapshot
   counts organization scopes only through those targets. The written cloud
   plan also allows actual shared relationships and explicitly unavailable
   outcomes. Registry cloud membership currently represents only unresolved
   relationships, so those alternatives have no adequate contract/evidence
   path. Duplicating a key or inventing an account is not a solution. The
   relationship/outcome contract and its real evidence producer remain work.

A further pure-policy defect allowed two empty hosts to satisfy the required
model-present scenario. The regression
`test_two_empty_hosts_do_not_prove_the_required_model_present_scenario` failed
with `passed` instead of `not_run`. The classifier now requires at least one
actually reported installed or loaded model after checking the existing host
coverage. It does not assume loaded means working, require a model on every
host, or initiate inference. The positive pure input was corrected to contain
an installed model; no constructed value crosses an I/O boundary.

```bash
python -B -m pytest tools/automation/test_m6_direct_evidence.py \
  tools/automation/test_m6_exit.py \
  tools/automation/test_m6_authoritative_evidence.py -q
```

Result: **46 passed**. This integration acceptance-policy correction preserves
upstream failure states and existing contract/API versions; it adds no runtime,
dependency, migration or secret handling. The already recorded deployed result
at `894f092` remains historical and is not claimed to exercise this later
policy correction. Shared/unavailable evidence remains incomplete. Additional-host transport is
not provided by this local slice; the current owner-identified local source
still needs a genuine model-present observation.

### Resolution of the host-count contradiction

The owner had already corrected the model location to **“this local machine”**
and confirmed **“Ollama and model already available”**. The approved local plan
retains that correction. Requiring an additional computer came from the older
execution-plan assumption, not that owner direction. Execution-plan section 11
and M6-A02 now explicitly reconcile this conflict: at least one real registered
host, observation coverage for every registered host, and actual model presence.
The required model-present check remains unproven by the current empty source.
No remote access, download, model start or scope substitution was authorized or
performed by this correction.

The new pure single-host/model-present regression first failed `not_run` versus
`passed`; the corrected classifier and updated bundle-reason assertion pass
**47 tests** in the focused command above. Multiple registered hosts still
require matching coverage, so a single observation cannot satisfy them. This
removes the unreachable invented host count rather than manufacturing a second
host. It does not resolve the cloud shared/unavailable representation gap or
natural-recovery prerequisite.

Independent review additionally reproduced a pure false pass when one empty
registered host was accompanied by an extra unregistered model-present host.
`test_extra_unregistered_host_cannot_supply_model_presence` failed `passed`
versus `not_run`. The count-based coverage fence now requires exact equality
between observed host evidence and registered installations, preventing that
extra host from supplying acceptance. Final focused result: **48 passed**.
This is policy evidence, not a claim of live model presence or remote transport.
