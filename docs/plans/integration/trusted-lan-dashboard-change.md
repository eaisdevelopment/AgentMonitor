# Trusted LAN dashboard change

- Status: Approved for the bounded owner-directed implementation.
- Date: 2026-09-29.
- Authority: the owner's explicit request, “Open this app for local network
  192.168.1.*”, following authorization for needed system actions.
- Primary owner: P01 transport. Root owns composition, automation, deployment,
  and documentation integration; P02's existing same-origin client is consumed.
- Requirements: `FR-IAM-003/006/007`, `FR-UI-001`, `NFR-SEC-001`,
  `NFR-API-001/002`; selected `AC-UI-001`, `AC-TEST-002` evidence.
- Contract impact: compatible optional runner arguments under `CTR-FND-002`,
  explicit transport profile under `CTR-API-002` V1. REST shapes, generated
  clients, IAM/domain/database contracts remain unchanged. This is an explicit
  owner exception to loopback-only deployment, not full `FR-REMOTE-001` hosting.

## Behavior and security review

Keep the existing IPv4 loopback listener, and add exactly one explicitly
selected private IPv4 interface at the same port. Two opt-in non-secret CLI
arguments, `--lan-host` and `--lan-network`, must be supplied together and are
valid only for the authenticated dashboard. The address must be a usable host
inside the canonical RFC1918 IPv4 subnet. No wildcard, forwarded proxy trust,
DNS host admission, automatic subnet discovery, or foundation schema exposure
is added. Startup fails closed if either socket cannot bind. Disable the profile
by omitting both flags and restarting the application service.

P01 checks the actual kernel listener/peer against the selected subnet before
authentication, then exact Host and same-origin mutation Origin/CSRF. Existing
loopback origin proof stays unchanged. LAN HTTP browsers may omit Fetch
Metadata; the LAN profile admits cookie reads only with canonical Origin,
existing valid Fetch Metadata, or a canonical same-origin Referer. Its response
policy is `same-origin` so the browser sends that proof to this application
without sending it elsewhere. Public static SPA navigation carries no private
response and remains available without that proof. Protected API/docs reads
without proof, foreign/duplicate origins/referrers, spoofed hosts/proxy headers,
and peers outside the subnet are denied. Password/session authentication,
SameSite/HttpOnly cookies, CSRF, limits, CSP, and permissions remain active.

The owner-requested existing HTTP deployment is limited to a trusted LAN.
It does not provide encryption against LAN observers or transport attackers;
TLS/proxy/multi-user/Internet hosting remains separate scope. The threat review
and exact exception are recorded in [ADR 0014](../../decisions/0014-trusted-lan-dashboard.md).

## Implementation and real verification

Owned production write set: `backend/src/agentmonitor/api/app.py`,
`backend/src/agentmonitor/api/transport.py`, and
`backend/src/agentmonitor/composition/bootstrap.py`. Tests and the canonical
`AUTO-LAN-DASHBOARD` implementation are root-owned integration artifacts.
P02 also owns any necessary correction to
`frontend/src/shared/api/client.ts` for browser idempotency on the admitted
LAN HTTP context. It must retain cryptographic randomness and the existing
header contract and be preceded by a real failing admin-browser check.
No dependencies, provider/profile changes, agent controls, migrations, or
secrets in commands/logs/evidence are needed.

First run real socket/SQLite/HTTP tests against the existing missing LAN runner
and retain the expected Red. Green must cover both real listeners, allowed LAN
HTTP login/reads, same-origin Referer browser compatibility, authentication,
CSRF, hostile host/origin/headerless reads, and an actual disallowed socket
source. A built Chrome scenario uses a genuine isolated admin/database on the
LAN listener and checks sign-in, API reads, refresh, navigation, and zero
provider sign-in. Loopback HTTP/browser regression and static/doc/planning
checks must pass. The canonical gate fails if a real LAN interface or built
frontend is absent; it never substitutes synthetic ASGI scope for TCP evidence.

After tests, restart only the AgentMonitor service with the explicit LAN flags;
verify real LAN and loopback shell/auth boundaries. Existing collection cadence,
profiles, data, and owner sessions persist; in-memory identity receipts refresh
at the next genuine collection. Browser access from a second physical computer
must be reported separately until the owner confirms it.
