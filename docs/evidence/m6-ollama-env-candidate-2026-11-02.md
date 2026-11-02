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
