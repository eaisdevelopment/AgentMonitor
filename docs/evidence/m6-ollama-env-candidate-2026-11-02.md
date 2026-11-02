# M6 managed Ollama credential candidate

The owner selected the protected AgentMonitor-managed `.env` for Ollama cloud
credentials on 2 November 2026. This replaces the earlier Secret Service
design; provider profiles are not used or changed. The M03 helper and M02
binding lifecycle must be reviewed together before activation.

The candidate local operator selects an existing account by name, reads the
key at a non-echoing terminal prompt, and stores its binding-specific entry
in the explicitly selected existing owner-only `.env`. On this installation
its parent is group-writable, so identity checks cannot eliminate malicious
same-group replacement. Rotation prepares a new binding,
writes its entry, then activates it and cleans up prior entries. Disconnect
disables the binding before deleting its entries. Interrupted cleanup remains
recorded. File replacement is serialized by a shared local writer lock and
preserves unrelated content; per-account locking protects binding changes.
The standard requires excluding `.env` from all backups and diagnostics; the
SQLite migration backup copies only the database, while other routines still
require review. These implementation claims require independent review; base64 is not encryption
and Python cannot guarantee complete in-memory zeroization.

Red/green evidence: pure format tests failed because the format module did not
exist, then passed. Only ordinary non-secret bytes were used as pure input; no
account, key, provider data, or file content was fabricated at an external
boundary. No actual `.env` was opened, copied or modified. Real owner setup,
rotation, deletion, concurrent file access, crash recovery, runtime reload,
browser and provider verification are Not Run. The change affects M6-A01,
M6-A03, M6-A04, M6-A09; the M02 binding and M03 source contracts/fingerprint
require reconciliation. No database migration or new dependency is introduced
by the file writer. The full M6 completion gate has not passed.

Restore recovery retains the location while managed entry names remain, even
if an older database contains no binding. Candidate untracked-entry cleanup
and binding preparation now use a shared data-root guard; a real empty-directory
guard-exclusion test failed before implementation and passed afterward. The
cleanup uses short M02 reads and does not hold SQLite during file I/O. Real
restore, file update, binding race and crash recovery remain Not Run.

A real isolated systemd worker completed with the configured project `.env`
path and an empty migrated database. A separate isolated dashboard started on
loopback; headless Playwright received HTTP 200 on `/`, `/login` and `/accounts`
and showed the expected administrator-setup screen for that empty database.
No administrator, account, credential or telemetry was fabricated. The
isolated processes and temporary databases were removed afterward. This does
not validate authenticated onboarding, provider access or any `.env` update.

The account form labels its free-form identifier as “Provider” and explains
that it is not an API key; suggestions do not restrict other provider names.
The frontend typecheck and build passed; an authenticated browser check of
this form remains Not Run.

After the unshipped credential-contention schema amendment, canonical
`AUTO-MIGRATE` passed from a private read-only backup of the installed real
v1_0707 database to v1_0717, with its verified private pre-migration backup.
Temporary copies were deleted; installed database and service were unchanged.
This proves that migration path only, not activation or credential behavior.

The candidate provider now receives a sealed file authority for the same
explicit path, acquires the shared writer lock, streams the selected binding
entry, and reloads per attempt. Forty-eight focused pure and provider-free
checks passed after integration; the populated credential boundary and exact
concurrent replay path remain Not Run and require independent review.

The candidate local operator is invoked with the installed Python environment:

```text
python -m agentmonitor.composition.ollama_credential_operator --data-root DATA_ROOT
```

It presents account names and accepts the key only through the no-echo prompt.
The operator reads the path selected by the active dashboard service. For this
installation it is the owner's existing project `.env`; the service must receive
that path via its explicit
`--credential-env-file` setting. This is a candidate instruction, not evidence
that the operator, runtime capability or service deployment has been verified.

At candidate commit `576046f`, the frontend typecheck and build passed using
the existing installed dependencies, and the planning synchronization and
`AUTO-DOCS-CHECK` gates passed. A fresh private empty database and 0600 empty
configuration were used to start an isolated candidate dashboard with the
explicit project `.env` path. Real headless Chrome received HTTP 200 for `/`,
`/login`, and `/accounts`; after waiting for asynchronous rendering, the
administrator-setup heading appeared. An immediate visibility assertion had
failed before that wait. No account, credential, or telemetry was created;
the isolated process and database were removed. This does not verify a
signed-in account, credential operations, provider collection, or the M6 exit
gate. No installed service, live database, or `.env` contents were changed.
