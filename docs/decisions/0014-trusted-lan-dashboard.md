# ADR 0014: Explicit trusted LAN dashboard profile

- Status: Accepted for the owner's bounded LAN request.
- Date: 2026-09-29.
- Deciders: P01/root under the owner's explicit LAN instruction and system-action
  authorization.
- Requirements: `FR-IAM-003/006/007`, `NFR-SEC-001`, `FR-UI-001`.
- Supersedes: loopback-only deployment for this explicitly selected profile;
  ADR 0012 remains unchanged for the default loopback profile.

## Context and decision

The owner needs the existing dashboard on other computers in one private
IPv4 subnet. V1's runner and exact loopback Host/Origin admission reject this.
Binding a wildcard alone would expose an unusable or unprotected application.

Add an opt-in interface/subnet pair to the authenticated runner, retain the
loopback socket, and validate actual listener and source peer before IAM.
Require exact IP:port Host and canonical Origin/CSRF for browser mutations.
Trust no forwarded headers or wildcard CORS. Use the same application and
lifespan for both sockets, with one collection service and service lock.
The foundation-only runner cannot use this profile.

Fetch Metadata headers are restricted to potentially trustworthy URLs in
[the W3C Fetch Metadata specification](https://www.w3.org/TR/fetch-metadata/).
For the explicitly selected LAN HTTP profile, admit cookie reads using exact
Origin, existing valid Fetch Metadata, or one exact-origin Referer; require
proof before IAM resolves/touches a session. Set LAN response Referrer-Policy
to `same-origin`, whose behavior is specified in
[the W3C Referrer Policy specification](https://www.w3.org/TR/referrer-policy/).
Public SPA/static navigation is available without proof because it contains
no account data; private API/docs responses still require proof. Foreign and
missing proof remain denied, including hostile image requests with suppressed
referrer. The stricter existing loopback profile is retained.

## Alternatives and consequences

An SSH tunnel preserves the default boundary but does not satisfy the owner's
request for direct LAN browser access. Wildcard binding or trusting forwarded
headers would widen admission beyond the requested subnet and is rejected.
TLS and reverse-proxy hosting need a separate operational profile; this bounded
change retains the explicitly requested existing HTTP service on a trusted LAN.

HTTP does not encrypt administrator credentials, sessions, account data, or
paths on the network. A trusted subnet is an operational restriction, not
protection against an observer or transport attacker inside that subnet.
This profile must not be exposed to the Internet or untrusted networks.
Host-only cookies on the LAN IP are shared across ports; other local web
services on that IP can be a cookie-exposure risk. Host/origin/referrer checks
prevent cross-origin session resolution, but do not eliminate that browser
cookie model. No provider credentials or source/prompts are exposed by the UI.

## Compatibility, verification, and rollback

Existing runner callers and the loopback transport remain unchanged. Optional
non-secret CLI flags are the only configuration addition; REST/schema/client,
IAM/domain contracts, database, and provider behavior are unchanged. Canonical
real socket/SQLite/HTTP and built-browser checks must pass before activation.
The service is restarted with the flags only after that gate. Second-computer
access remains separate owner evidence. Omit both LAN flags and restart the
application to return to loopback-only admission; no data rollback is needed.
