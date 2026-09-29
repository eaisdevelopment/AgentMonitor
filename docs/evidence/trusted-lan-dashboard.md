# Trusted LAN dashboard evidence

- Date: 2026-09-29.
- Authority: the owner's explicit private-subnet request and prior system-action
  authorization; [approved plan](../plans/integration/trusted-lan-dashboard-change.md),
  [ADR 0014](../decisions/0014-trusted-lan-dashboard.md).
- Owner: P01 transport; root owns composition, deployment and verification;
  P02 owns the existing generated-client wrapper's HTTP compatibility correction.
- Requirements: `FR-IAM-003/006/007`, `FR-UI-001`, `NFR-SEC-001`,
  `NFR-API-001/002`; selected `AC-UI-001`, `AC-TEST-002` evidence.
- Contracts: optional compatible runner arguments under `CTR-FND-002` and
  explicit LAN admission under `CTR-API-002` V1; REST, IAM/domain, schema and
  generated operation/type shapes unchanged. This is not full remote hosting.

## Actual increment and Red/Green

The runner keeps its exact loopback socket and adds one explicitly selected
private IPv4 socket at the same port. Both share the same application lifespan,
service lock and collectors. Invalid/unpaired/nonprivate targets and foundation
LAN mode fail closed. P01 admits the actual bound listener and kernel peer
subnet, then exact Host, Origin/CSRF, and existing IAM permissions. Forwarded
headers remain untrusted. Default loopback origin proof remains unchanged.

LAN HTTP Chrome does not supply Fetch Metadata. The profile requires exact
Origin or exact-origin Referer for cookie reads before IAM resolution; response
policy `same-origin` supplies proof to this application only. Public static SPA
navigation carries no account response and is exempt from private-read proof.
The authenticated API/docs remain protected. Admin idempotency uses 16 random
bytes from browser `crypto.getRandomValues`; key format/entropy remains a
32-character cryptographic hexadecimal value, usable in LAN HTTP.

| Scenario | Real evidence |
|---|---|
| `LAN-HTTP-001` / `LAN-UI-001` Red | Both real migrated SQLite/HTTP/browser tests Failed before production edits: `TypeError: serve_loopback() got an unexpected keyword argument 'lan_host'`; 2 Failed in 1.40s. |
| Initial dual-listener Green | Real loopback and LAN shells, login and authenticated reads, exact Host/foreign Origin, missing Origin/CSRF, required cookie-read proof and actual disallowed TCP source Passed; real built Chrome login/navigation Passed. |
| LAN admin compatibility Red | A real LAN browser Create organization action Failed at `lan_organization_create`. Safe diagnosis confirmed `lan_http_browser_random_uuid_unavailable`; 1 Failed in 3.08s. No production mutation was replayed or fabricated. |
| LAN admin Green | The same browser created a real organization through production API/SQLite after the wrapper switched to `crypto.getRandomValues`. Overview refresh, account/admin navigation and reload Passed. |
| `LAN-SEC-001` | Actual same-IP/different-port Chrome image requests with ordinary and suppressed Referer both received 403 after 62 real seconds. SQLite session activity and record version remained at their original values. No simulated scope or request interception was used. |
| Final canonical LAN gate | `AUTO-LAN-DASHBOARD` Passed exit 0: 3 real integration/browser cases in 68.94s. Second-computer/firewall reachability is explicitly excluded from this bounded gate. |
| Loopback HTTP regression | 5 real IAM tests Passed in 4.46s: login/cookies, session/CSRF/logout, bearer-advertised login Origin, initialization foreign Origin, raw TCP Host/header bounds. 31 unrelated cases were deselected. |
| Loopback admin browser | Actual `accounts_admin` production browser/API/SQLite scenario Passed. No provider sign-in was started. |

`AUTO-QUALITY` Passed after formatting/type corrections and regenerating the
source-bound provenance pair. The canonical generator reported **compatible**,
44 unchanged operations; only generation provenance/header hashes changed.
The OpenAPI artifact digest is
`3f5647eedb0f654412b33de77356d6671145c74e8d893b2ef3cb89b27a59e77f`.
Strict typechecking/build and zero module-boundary violations Passed. Thirteen
targeted actual catalog/planning tests Passed. Synchronized planning Passed
after rebinding only the two changed automation controls and appending the
scoped binding to both review records; all twenty plan hashes and historical
Draft/approval flags remain unchanged.

The bounded independent source/document review found no concrete blockers
within the approved LAN scope. It performed no browser, provider, process or
test actions and did not treat the HTTP exception as TLS acceptance.

An exploratory full automation/planning unit run was **Failed**: generated
provenance drift made two subchecks fail (subsequently corrected), the
clean-clone test saw the uncommitted new routine, and the pre-existing runtime
mutation-equivalence contract fingerprint was stale. The runtime contract was
byte-for-byte unchanged from the pre-LAN commit. The broader mutation gate
has not been reaccepted by this LAN increment. These results are not claimed
Passed or hidden by the targeted verification.

After the LAN implementation commit, the exact previously failing clean-clone
test Passed against a genuine fresh Git checkout. The generation checks had
already Passed after the canonical provenance update. The unrelated runtime
mutation-equivalence fingerprint remains the outstanding broader test finding.

## Deployment and remaining real boundary

After the gate and independent review, only AgentMonitor was gracefully
restarted with the explicit interface/subnet flags. The actual service announced
both origins and retained the real database/config/profile roots. Kernel socket
inspection confirmed exactly two selected listeners. Real HTTP checks returned
shell 200 and protected accounts 401 on each; an actual non-subnet source
received 403 on the LAN socket. The existing owner browser session persists.
In-memory identity receipts refresh through normal genuine scheduled reads.

UFW is configured enabled. `sudo -n ufw status` returned
`sudo: a password is required`; this session has no usable passwordless OS
administrator elevation. The owner was given the exact subnet/interface/port
allow command to execute locally, with the password kept in their terminal.
Firewall change and a browser on a second computer remain **Pending owner
execution/Not Run** until their actual result is received. Local LAN HTTP success
is not represented as proof that the firewall admits another computer.

## Security, privacy, migration, license and rollback

This is a trusted-LAN HTTP exception. It does not encrypt credentials, sessions,
account data or paths against network observers/attackers. TLS, Internet,
multi-user/proxy deployment and remote collectors remain outside scope.
No new dependency/license, database migration, provider/default-profile edit,
agent control, owner password read, arbitrary environment/process-content
read, provider page/cookie inspection, screenshot or trace was involved.
Tests use OS-random isolated credentials through private stdin, real sockets,
real migrated SQLite, production HTTP and actual built Chrome.

Rollback omits both LAN flags and restarts only AgentMonitor; remove the exact
firewall rule if it was added. Data and provider profiles remain intact.
The operational command and canonical prerequisites are in the
[runbook](../operations/runbook.md#owner-approved-trusted-lan-dashboard).

Changed files include P01 application/transport, root bootstrap, P02 shared API
wrapper, the two regenerated provenance artifacts, the new real LAN tests and
browser checker, shared hostile-resource browser target selection, the canonical
LAN gate/catalog/validators, and this plan/ADR/runbook/evidence/index plus scoped
automation snapshot bindings. Full M4 acceptance and account-to-running-agent
correlation retain their existing incomplete state.

## Final local checks and exact files

The deployed owner Overview verifier Passed for six real accounts, retained
manual/periodic organization selection, ascending lowest quota, one low red
and eleven normal bars, responsive layout, keyboard access and read-only
navigation. `AUTO-DOCS-CHECK` Passed 261 Markdown files, local
`AUTO-GIT-PREFLIGHT` Passed, and `git diff --check` Passed. The LAN application
listener is active; the OS firewall/second-computer boundary remains pending
as stated above. No push or release was performed.

```text
backend/src/agentmonitor/api/app.py
backend/src/agentmonitor/api/transport.py
backend/src/agentmonitor/composition/bootstrap.py
backend/tests/integration/api/test_lan_http.py
contracts/openapi/agentmonitor-v1.json
docs/README.md
docs/architecture/deployment.md
docs/architecture/security.md
docs/decisions/0014-trusted-lan-dashboard.md
docs/decisions/README.md
docs/engineering/completion-and-automation-gates.md
docs/evidence/trusted-lan-dashboard.md
docs/operations/runbook.md
docs/plans/integration/cs1-final-readiness-audit.md
docs/plans/integration/cs1-full-plan-synchronization.md
docs/plans/integration/trusted-lan-dashboard-change.md
docs/plans/plan-baseline.toml
frontend/src/generated/api/index.ts
frontend/src/shared/api/client.ts
frontend/tests/browser/p02/hostile_resource.mjs
tools/automation/implementations/auto_lan_dashboard.py
tools/automation/routines.toml
tools/automation/run.py
tools/automation/test_run.py
tools/planning/validate_plans.py
tools/ui/verify_lan_dashboard.mjs
```
