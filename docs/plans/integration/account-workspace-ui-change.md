# Change plan: account workspace view

- Status: Approved for implementation by the owner's explicit 2026-09-28 account-page redesign request.
- Owner: P02 React dashboard.
- Requirements: `FR-ACC-002/005/006`, `FR-ORG-001`, `FR-DISC-001/002/004/007`, `FR-UI-001/002/004/005/006`, `FR-COL-008`; bounded acceptance `AC-UI-002/003/005/006`, `AC-PROC-001/003/004`, `AC-HIST-001` (presentation only).
- Contracts: generated V1 registry, capacity, session, UI, and additive profile-identity read contract. No database migration, dependency, or provider-state change.

## Owner correction: automatic account attribution

The owner clarified that they cannot label the profile because identifying
mixed running accounts is the dashboard's job. A01 therefore reads the official
`claude auth status` JSON command, whose metadata-only identity fields were
observed on the installed admitted version. It exposes only email and provider
organization plus a private identity fingerprint; never credentials, raw JSON,
transcripts, arbitrary environment values, or configuration contents.
The service reads identity before and after quota collection and associates
the verified label only with that exact successful collection run when both
observations match. M03 owns the typed observation/query seam, Foundation
owns the in-memory receipt cache, and P01 publishes an authenticated read-only
V1 identity endpoint. No old quota or other running agent is relabeled from
the current default profile. A cache miss after restart remains unresolved
until a new real collection. Registry names and organization assignments stay
admin-owned and are displayed separately from observed identity.

This additive contract changes no existing operation's semantics. Its new
consumer adoption is declared; OpenAPI/client are regenerated normally.
The endpoint's pre-implementation 404 and the built browser's missing-table
failure are behavioral Reds. A real new collection must make the label and
its run lineage Green. Other accounts remain visibly unresolved when no
session-specific identity evidence exists; never assign all agents to the
default account. Full mixed-account attribution remains a data-source gap and
must be reported separately from the delivered redesign.

## Live process location increment

The owner's requested Path column also authorizes read-only working-directory
metadata. A04 Linux supplies a bounded live view of same-user Claude processes
whose executable matches the admitted installation. It reads only procfs stat,
exe, owner, and cwd metadata, verifies start ticks/executable/owner before and
after cwd inspection, and never reads argv, environment, or session contents.
M06 owns the typed query, Foundation wires its port, and P01 publishes an
additive authenticated V1 operation. Paths are memory-only, shown exactly as
working directories (not inferred project roots). Process presence means
Running; it cannot prove Working or any account/quota ownership. The UI shows
these processes separately with unresolved accounts. Unsupported platforms or
unverified executable versions are visibly unavailable, never an empty success.
The canonical owner browser must fail on the missing operation before this
increment and verify real paths/process identities afterwards.

## M05 percentage presentation increment

The real Claude source reports percent used but leaves remaining-ratio fields
unknown. M05 adds a pure display calculation: remaining percentage is 100 minus
a reported used percentage, or 100 times an available reported remaining ratio.
It accepts only applicable units and values in range, preserves rounded
precision/confidence and stale input state, and exposes its method and source
observation ID. P01 adds a nullable allowance field to each existing quota-window
view, leaving original source values, health decisions, stored observations,
and history intact. P02 formats that M05 value and displays its calculation;
it does not derive or aggregate account capacity. The real browser's missing
remaining-percentage assertion is the behavioral Red. Pure tests cover exact
zero/full, fractional, stale, unavailable, and incompatible/out-of-range inputs.

## User outcome

Make the observed provider email and administrator-assigned organization the
primary identity; keep the editable registry name separate. Show an Account / State / Left / Path table before settings
or diagnostics. Left is the percentage from the M05-selected constraining
window, or labeled individual windows when no single selected window is
published; do not invent a frontend account aggregation. Clearly distinguish
quota freshness and monitoring preference from agent activity. The existing
session API publishes no working-state or project-path field; those cells must
state that they are not reported, without manufacturing activity or paths.
The owner's example email, percentage, state, and path are not production data.

Provide compact readable quota cards with percentage bars and update times.
Move administration, identity/provenance, exact metrics, history, and session
inspection behind native expandable sections. Keep all prior admin actions,
exact values, chart/table lineage, pagination, and authentication/CSRF behavior.
Refresh the summary using the generated API every 30 seconds. No new package,
backend import, direct fetch, database read, profile read, or running-agent
control is permitted in the UI.

## Verification and delivery

First run a failing real built-browser assertion for the four-column table and
organization/name attribution against the current production service. Assert
the selected percentage against its real capacity API response. Redesign and
rerun against the real owner DB/browser without request interception, recorded
responses, or invented telemetry. Verify laptop, desktop, and 390px layouts;
inspect actual screenshots. Keep credentials memory-only in the existing
private stdin pattern and screenshots free of login fields. Run admin browser,
typing/build, boundaries, documentation, and local Git checks, then commit the
reviewable UI and leave the existing dashboard running. The canonical owner
browser command is `tools/ui/verify_account_workspace.py --origin` with an
explicit running loopback origin; absent real prerequisites cannot pass.
