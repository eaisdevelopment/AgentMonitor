# M5 Codex app-server read-side-effect blocker

- Date: 2026-10-07.
- Status: **Safety assumption corrected in production; authenticated live
  verification remains required before M5 acceptance.**
- Requirements: `NFR-SEC-001`, `NFR-PRIV-001/002`, `FR-SAFE-002`, and
  `ST-CDX-001..005`.
- Owning module and contracts: A02 provider adapter,
  `CTR-PROV-001..008`.
- Exact installed provider: `codex-cli 0.160.0` on Linux x86-64.
- Exact upstream source tag and commit: `rust-v0.160.0` at
  `a956835d020762cb2b570053af06f643a11c0ecc`.

## Failed assumption

The M5 discovery and focused plan classified app-server `account/read` and
`account/rateLimits/read` as `read_only`. A real installed-system check showed
that starting the app server for either operation writes provider runtime state
inside the selected `CODEX_HOME` before the requested method completes.

At 2026-10-07T18:20:42+01:00, this behavioral Red ran against a fresh private
temporary root with no credential or default-profile access:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q \
  backend/tests/adapters/providers/codex/live/test_managed_identity.py
```

The test expected the empty managed root to remain unchanged after the real
`account/read` invocation. The first run found 18 descendants and a repeat
found 94, so even the write set is startup-state dependent. No file content,
provider response, identity, credential, or private path was retained.

A second isolated control used every applicable documented/config-schema
redirection or suppression: a separate `CODEX_SQLITE_HOME`, separate
`log_dir`, `history.persistence=none`, disabled analytics and OpenTelemetry,
disabled bundled skills, and disabled plugin-related features. The app server
still created managed-root state. Both `account/read` and
`account/rateLimits/read` started the same mutating runtime; the latter then
reported authentication required because the test root was intentionally
empty. SQLite and logs can be redirected, but the installation identifier and
argument-dispatch runtime cannot.

## Bubblewrap containment experiment

The installed `/usr/bin/bwrap` (`bubblewrap 0.9.0`, Ubuntu package
`0.9.0-1ubuntu0.3`) was tested as a concrete Linux containment option. A real
Codex app-server process ran inside a mount namespace with:

- the fresh selected managed root mounted read-only;
- an in-namespace temporary `CODEX_HOME` containing only a symlink to the
  credential location under that read-only mount;
- SQLite, logs, and other runtime writes directed to a separate private
  temporary root; and
- the same closed `account/read` request with refresh disabled.

Against an empty root, initialization and `account/read` both returned normally,
the selected managed filesystem tree and root metadata remained unchanged with zero
descendants, and the isolated runtime root received the expected provider
runtime files. This proves filesystem containment for the unauthenticated case.

Authenticated verification was **Blocked/Not Run**: the current owner data root
contained zero AgentMonitor-managed Codex profiles, and the default Codex
profile is prohibited. More fundamentally, read-only mounting does not resolve
the exact-source authentication behavior. A proactive refresh can rotate
provider-side tokens before persistence into the read-only credential location
fails. Discarding that refreshed credential could invalidate the selected
profile. This risk must not be manufactured against an owner account.

Bubblewrap therefore does not establish a read-only authenticated operation.
It would also add a new Linux-only executable/runtime dependency, subprocess
allowlist entry, namespace/kernel-policy assumption, and deployment admission.
The installed package is LGPL-2+ and directly depends on libc6, libcap2, and
libselinux1; none of this dependency/plan surface is approved for M5.

## Exact-version source review

The matching official OpenAI source explains the observed behavior:

- app-server startup always resolves an installation identifier by opening its
  file read/write with create enabled, and writes a new value when absent;
- `account/read` with `refreshToken=false` still calls the authentication
  manager's normal `auth()` path;
- `account/rateLimits/read` calls `auth_with_http_client_factory()`, which also
  calls `auth()`;
- `auth()` proactively refreshes near-expiry or old ChatGPT authentication and
  the refresh path persists the returned OAuth token set; and
- the exact committed config schema has SQLite/log/history/telemetry controls
  but no control that disables proactive token refresh for these methods.

Primary source references:

- [app-server account processor at the exact tag](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server/src/request_processors/account_processor.rs#L1026-L1125)
- [authentication refresh and persistence at the exact tag](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/login/src/auth/manager.rs#L2389-L2414)
- [proactive refresh policy at the exact tag](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/login/src/auth/manager.rs#L3004-L3026)
- [installation identifier write at the exact tag](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/src/installation_id.rs#L17-L63)
- [exact-tag config schema](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/config.schema.json)

The reviewed config-schema SHA-256 was
`7ce31bde1ed6ef15c53a96ba460bb1d0fb7b99fd9ab719b567c94c474f62b023`.

## Why redirection is insufficient

Redirecting SQLite, logs, history, skills, plugins, or temporary runtime state
does not suppress installation-identifier writes. More critically, it cannot
turn authentication access into a read-only operation. When the provider
decides that a token needs proactive refresh, it can update both provider-side
authentication state and the selected credential store.

Copying, parsing, exporting, or replaying the OAuth credential into a scratch
profile would violate the credential boundary. A symlink, read-only overlay,
or discarded copy would still permit a server-side refresh-token rotation and
could leave the authoritative managed credential stale. Ephemeral credential
storage would require AgentMonitor to receive or transfer the token, or retain
one provider process indefinitely; neither behavior is in the approved plan or
privacy contract.

## Implemented resolution

The approved M5 plan already bound official browser login and Codex-owned
automatic credential refresh to an AgentMonitor-managed profile. The unsafe
gap was app-server startup against an empty root and the inaccurate
`read_only` declaration.

The production boundary now validates the managed root and safe `auth.json`
metadata without opening the credential file. Missing authentication returns
`codex_managed_authentication_required` before resolving or starting the
app-server executable. The real empty-root Green left the directory metadata
unchanged with zero descendants. Linked, public, nonregular, wrong-owner, and
unbounded stores fail closed.

The exact manifest now declares identity, authentication-health, and quota
queries as `managed_profile_write`. Codex may perform its official automatic
credential refresh and runtime maintenance only inside the explicitly
selected managed profile after owner login. Installation discovery remains
`read_only`; the default profile remains prohibited. Bubblewrap was not added.

Green command:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest -q \
  backend/tests/adapters/providers/codex/test_manifest.py \
  backend/tests/adapters/providers/codex/live/test_managed_identity.py \
  backend/tests/adapters/providers/codex/test_security_policy.py
```

Result: `22 passed`. Owner-authenticated identity/quota behavior and exact
managed-root containment remain live M5 gate requirements; they are not
claimed by this empty-root correction.

## Impact

- Security/privacy: prevented provider startup and mutation on an empty root;
  authenticated provider-controlled auth maintenance is declared and confined
  to the selected managed root. No secrets or provider payloads were inspected
  or retained.
- API/database/migration: none.
- Dependency/license: none.
- Live verification: empty-root non-mutation is **Passed**; authenticated
  managed-profile behavior is **Not Run** until owner enrollment.
- Production implementation: metadata preflight and truthful side-effect
  classification implemented without a dependency or schema migration.
