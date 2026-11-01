# M6 Ollama cloud credentials and account scope

**Status: Draft.** No key creation, secret-store access, provider sign-in or
cloud API operation is authorized by this document. This design supports
M6-T004/T005/T006/T010/T011 and M6-A03/A04/A09, but does not replace the
approved module plan, live evidence, or the M6 completion gate.

## Current facts

- Ollama documents an API-key bearer credential for its official direct
  [balance API](https://docs.ollama.com/api/balance). The endpoint documents
  shared team balances, 10 requests/minute per user across keys/devices and
  `Retry-After`. The public documentation does not establish a key-to-account
  identity endpoint or a read-only key scope.
- SDK and EAIS account/team relationships, role, plan and endpoint behavior
  are unverified. One authorized human may have memberships in two teams; do
  not assume two personal accounts, duplicate shared pools or derive identity
  from email. The owner may describe each connection, but that assertion is
  not a provider-verified identity.
- Existing registry CRUD does not require hardcoded account names. The current
  app has no Ollama provider manifest, key resolver or provider credential
  enrollment path. An opaque contract reference alone does not apply a key.
- Existing configuration/security policy says provider credentials remain in
  provider-supported stores or explicitly approved managed profiles; copying
  them into `.env` requires a separately approved secret architecture. The
  project instructions also prohibit agents from reading or persisting keys.
  The precise permission for a runtime component to apply an owner-provided
  provider key must be resolved explicitly; the coding agent must never see it.

## Proposed operator experience

1. An administrator creates and assigns each Ollama account using normal
   account/organization CRUD; no account or email is compiled into the app.
2. Each record shows a non-secret connection state such as not configured,
   configured, authorization failed, rate-limited or identity unresolved.
   Where the owner assigns a key to a record, label that association
   `owner_asserted` unless an authoritative provider source proves identity.
3. The owner provisions a key through an approved local-only mechanism after
   authenticating in Ollama's official UI. Do not accept keys through the
   HTTP LAN dashboard, chat, command-line arguments, logs, screenshots,
   database, exports or diagnostic evidence. The UI shows instructions and
   connection state only; it never retrieves or echoes a key.
4. A separately reviewed credential application boundary makes bounded GETs
   only to the official HTTPS host and documented balance route; it rejects
   redirects and arbitrary destinations, limits bytes and time, sanitizes
   failures and applies per-user rate/backoff policy. It passes only safe typed
   observations to the adapter and does not expose secret values in contracts.
5. Distinguish legacy remaining percentages and reset timestamps from included
   and purchased credit amounts; never add shared team balances per account or
   derive percentages without a real denominator. A successful balance read
   proves endpoint access, not account identity or team membership.

## Decision required before implementation

No existing approved key application/storage mechanism has been verified for
Ollama. Options requiring security and ownership review include an
owner-operated OS secret store or an external credential broker that applies
provider credentials without passing them through the application. Neither is
an already approved Ollama-supported store. Review the actual operating-system
service lifetime/unlock behavior, file and process permissions, rotation and
removal, backups, dependency/license impact, and exact rules for in-memory
credential application. Do not silently add a dashboard secret field or
change the provider-credential policy.

As a non-secret workstation inventory on 1 November 2026, `secret-tool` and
`systemd-creds` are installed and the user `gnome-keyring-daemon.service`
reports active. That does not prove that the dashboard service can use either
mechanism, that the store is unlocked after restart, that its access policy is
appropriate, or that the dependencies and key lifecycle are approved. No
secret-store item was queried, created or changed. Treat this as an option to
assess rather than a supported credential implementation.

Once a concrete design is approved, owner-controlled official setup and real
SDK/EAIS provider UI/API comparisons establish source behavior once. Do not
repeat owner attestations for unchanged valid evidence. All unavailable or
unauthorized cases remain explicit. The M6 gate must verify each required
accessible scope and truthful sharing semantics without capturing credentials
or raw provider payloads. Local inventory work can proceed independently.
