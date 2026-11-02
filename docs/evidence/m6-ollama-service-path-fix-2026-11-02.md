# Ollama service installation discovery path correction

The deployed M6 dashboard reported `ollama_runtime_unavailable` followed by
backoff. Its configured service search path omitted `/usr/local/bin`, while the
real local Ollama 0.24.0 executable is `/usr/local/bin/ollama`; the local API
reported version 0.24.0. The same exact CLI discovery succeeded from a shell
whose search path included that directory. This explains why healthy loopback
HTTP alone did not result in an installation record.

The Ollama adapter now tries the explicit `/usr/local/bin/ollama` location when
normal PATH discovery finds no executable. The existing resolved executable
identity, ownership, mode, bounded isolated version invocation, exact version,
and revalidation checks still apply. The user's PATH and provider profiles are
unchanged. On this workstation the executable and its `/usr`, `/usr/local`, and
`/usr/local/bin` parent directories are root-owned and mode 0755. This is an
additive location under the existing installation discovery contract; no new
dependency, migration, account, credential, or provider write is introduced.

Real Red: the CLI discovery subprocess with `PATH=/usr/bin:/bin` returned
`provider_unavailable None` although the real local executable existed. Green:
that same test returned `success 0.24.0`; five actual CLI, SQLite registry, and
procfs/runtime collection tests passed under the restricted search path. A real
transient user-systemd process with the restricted path also discovered the
real CLI. With the same restricted path and a private SQLite backup of the real
database, the collector observed no current Ollama installation before the
run, completed with `ollama_runtime_partial`, and observed the installation
afterward. The private copy was removed. No live database or service was
modified, no keys were accessed, and no agent process was signalled.

Scope: M6-T013, M6-A06, AC-PROC-001..004; provider adapter installation
source and M02 registry reconciliation use their existing versioned contracts.
The change is isolated and requires review and safe deployment; live dashboard
reconciliation after deployment, natural failure recovery, and full M6
acceptance remain Not Run. Rollback returns to the previous adapter, which will
again fail to locate `/usr/local/bin/ollama` if it is absent from the service
PATH. The earlier test harness import-path error was corrected before the
recorded behavioral Red above.
