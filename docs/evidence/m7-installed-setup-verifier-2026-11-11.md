# M7 installed setup verifier: bounded read-only evidence

- Scope: T002/T014, M7-A01; P02 installed setup surface, not enrollment or collection acceptance.
- Authority: root-delegated approved M7 verification; no owner configuration mutation.
- Artifact: `frontend/tests/browser/m7/verify_setup.mjs`.
- Contracts: existing API V1 operations/versions and browser setup UI. No contract changes.
- Recorder/date: delegated UI agent, 2026-11-11 UTC.

## Behavior and boundaries

The verifier connects to the existing CDP browser at loopback port 9225 and
creates its own page in the existing dashboard context. It never inspects,
navigates or closes an existing tab, and never reads cookies, credentials,
account names, emails, page bodies or screenshots. It closes only its own page;
process exit disconnects CDP without calling Browser.close or context.close.

The expected installed revision is a mandatory 40-character lowercase SHA
argument. Once authenticated, the verifier reads the actual source revision
from the build manifest through `/api/v1/operations/versions`, checks Overview,
opens Accounts → Add API billing account, verifies the existing provider choices
and disabled empty-form creation action, then returns to Overview without
submitting. It checks promotion/support/company-footer presence and horizontal
overflow at 1366×768. It does not execute a setup command or inspect an account
detail. This deliberately bounded probe does not replace the full browser gate.

All page requests are counted; a non-GET/HEAD/OPTIONS request forces Failed.
No network interception or fake response is used. The only clicked controls
are asserted `type=button` navigation/mode controls. No provider selection,
account-name entry, submit, login, logout or credential action is performed.

Output is one JSON record containing closed status/reason codes, validated
revision values, fixed check names, request counts and observation time. No raw
exceptions, response bodies, account data or session values are printed.
Missing authentication returns Blocked and exit 3; assertion failure returns
Failed and exit 1; all required checks passing returns Passed and exit 0.

## Runnable commands

From the M7 worktree:

```bash
node --check frontend/tests/browser/m7/verify_setup.mjs
node frontend/tests/browser/m7/verify_setup.mjs <installed-40-character-sha>
```

The script first imports normal `@playwright/test`. If that package is absent,
it uses only the already-admitted fallback supplied by root:
`/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs`.
There is no module search, dependency installation or temporary tool link.
No shared helper/build window was taken, so the root's canonical checks could
continue independently.

## Current real result

Syntax validation exited 0. The actual browser invocation was:

```bash
node frontend/tests/browser/m7/verify_setup.mjs c453fe0a91c83e47fe35204fa1b0b92d9c1f780b
```

At `2026-11-11T17:20:01.829Z`, it exited 3 and emitted:

```json
{"record_type":"agentmonitor.m7_installed_setup_probe.v1","status":"blocked","reason_code":"authentication_required","expected_revision":"c453fe0a91c83e47fe35204fa1b0b92d9c1f780b","source_revision":null,"checks":{"authentication":"blocked","revision":"not_run","overview":"not_run","setup_form":"not_run","continuity":"not_run","read_only":"passed"},"requests_observed":6,"unsafe_requests":0,"observed_at":"2026-11-11T17:20:01.829Z"}
```

The existing browser was signed out. No additional sign-in request was made;
the owner's already-pending sign-in remains the prerequisite. No meaningful
behavioral Red or authenticated Green is fabricated from this blocked result.
The account-creation implementation's separate real Red/Green evidence remains
in `m7-api-setup-ui-2026-11-11.md`.

## Remaining verification and declaration

Root must rerun with the actual activated revision after the existing sign-in
request is fulfilled. Revision matching, installed form and header/footer
continuity remain Not Run. Full local credential entry, provider verification,
monitoring, first reading and M7 exit acceptance remain separate work.

Only the verifier and this evidence were added. No production file, dependency,
schema, migration, service or owner configuration changed, and no commit was
made by the delegate.
