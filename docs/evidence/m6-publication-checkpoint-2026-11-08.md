# M6 publication checkpoint — 8 November 2026

Status: current source publication; M6 remains in progress and is not accepted.
Authority: owner instruction to commit, push and update the project.
Implementation: `a60b6b9035f5955a91fa03f55de1d92097ad4d02`, including
`fde1adca36372479ad7c2b23efb1202c5e572774` and `8da0eb4`.

## Delivered and observed

The deployed cloud collector recovers an abandoned scheduled Ollama request,
preserves known rate-limit deadlines and resumes reads after its cooldown.
M03 now accepts the corresponding recovered uncertainty without fabricating a
provider response. Schema is `v1_0720`; contracts are CTR-COL-008 1.2.0 and
CTR-PROV-003 1.2.0. See the [implementation and Red/Green evidence](m6-unknown-outcome-recovery-2026-11-07.md)
and [migration/cutover evidence](m6-v0720-retained-cutover-2026-11-07.md).

On 7 November, real scheduled collection restored fresh cloud balances for both
owner-configured organizations. The unchanged installed-browser verifier then
passed account administration, current balances, history and dashboard
availability for both accounts. The official Ollama usage comparison passed for
one account. Source/security selection passed 157 tests with zero skips;
canonical build, quality, documentation and planning checks passed.

The full `AUTO-M6-EXIT` run on this implementation **failed**. At that point the
history test had only one new reading for one account; its unchanged recheck
passed after a second genuine reading. The initial official comparison reported
connection unavailable; its later unchanged recheck passed for one account.
These later component passes do not turn the full gate into a pass.

The approved isolated-network test recorded a real failure followed by normal
Ollama recovery while the dashboard and Codex collection continued. Complete
cross-provider evidence was not obtained because no successful Claude reading
occurred in the interval. The managed Claude sign-in attempt timed out.

## Remaining acceptance work

- Compare the second organization's balances with its official Ollama usage page.
- Complete one existing managed Claude sign-in and verify normal collection.
- Rerun the bounded canonical M6 check with all required evidence present.
- Present the complete result for owner acceptance.

Unknown interrupted verification requests remain explicitly unresolved; this
change recovers scheduled requests only. No real provider-side 401/403/429
scenario is claimed. All local Ollama work remains deferred by the owner.
No account configuration, default provider profile or running agent was changed.

The public update preserves the blurred dashboard image, funding configuration
and personal-use/EAIS licensing terms. It publishes current work in progress;
it is not a packaged V1 release.
