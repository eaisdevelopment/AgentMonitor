# Claude Code 2.1.289 exact-version admission evidence

- Evidence ID: `A01-M03-CLAUDE-2-1-289-EVIDENCE-001`
- Module/plan/increment: A01 Claude adapter with M03 provider-system
  compatibility and the owner-approved current-M4 change
- Requirements: `FR-DISC-008`, `FR-COL-004`, `FR-COL-006`,
  `FR-COL-007`, `FR-COL-008`, `FR-AUTH-002`, `FR-AUTH-003`,
  `FR-AUTH-006`, `FR-SAFE-001`, `FR-SAFE-002`, `NFR-COMP-001`
- Acceptance contribution: `AC-LIVE-004`, `AC-LIVE-005`, `AC-LIVE-006`,
  `AC-LIVE-007`
- Contracts: `CTR-PROV-001..008` V1; `ClaudeSubscriptionQuotaV1@1.0`,
  `AuthHealthObservationV1@1.0`, `ObservedProfileIdentityV1@1`,
  `ProviderConnectionViewV1@1`; `DiscoveryOutcomeV1@1.0` consumed by the existing M02
  `ReconcileProviderDiscoveryV1` port
- Exact tuple: Claude Code `2.1.289` on Linux x86-64; quota adapter/parser
  `1.0.3`; source `claude.usage.ax-screen-reader.v1`
- Base revision: `c6cf677`. The exact-version increment is bound by the
  containing implementation commit and its clean-revision M4 receipt.
- Recorder/date: integration agent, 2026-10-05 through 2026-10-07
- Evidence status: **Passed for this bounded exact-version admission**. The
  implementation, focused real checks, one owner-completed managed sign-in,
  six-account authenticated preflight, and evidence hash binding below are
  green. At this admission checkpoint, `AUTO-M4-EXIT` and formal M4 acceptance
  were pending because the clean-revision restart and fresh post-restart witness
  had not run. Later M4 receipt and acceptance records supersede only that
  lifecycle status; this exact-version admission remains immutable evidence.

## Admitted boundary

The owner-approved admission record is
[`A01-M03-CLAUDE-2-1-289-001`](../discovery/m0/m0-to-m03-claude-2.1.289-v1.json).
It admits only the exact `2.1.289` executable for:

- read-only subscription quota and authentication health;
- bounded read-only identity verification;
- the official interactive login flow for an AgentMonitor-managed profile,
  with owner browser interaction and exact post-flow identity verification;
- read-only `installation.discovery` through
  `claude.version.banner.v1`, which emits no account candidate.

Protected-default profile writes, credential reads or persistence, running
agent control, compatibility with another Claude version, and Claude OTLP on
`2.1.289` remain outside this admission. The separately admitted OTLP adapter
remains `1.0.0` and exact-pinned to Claude Code `2.1.282`. Because that
executable is not retained on this workstation, the OTLP launch path rejects
the exact `2.1.282` request with `claude_version_unverified` before provider
profile access or process launch.

The workstation's default `claude` command is now Claude Code `2.1.292`, which
is outside this admission. Quota, authentication, identity, and installation
checks covered here select the retained native `2.1.289` executable by its
exact admitted version. The resolver does not treat the default `2.1.292`, the
retained `2.1.289`, and the unretained OTLP `2.1.282` as interchangeable.

Generic read-only process observation through `linux.proc.process.v1` is
A04/M06-owned platform/runtime evidence used alongside Claude monitoring. It
does not depend on an A01 source, is not declared by the Claude adapter, and is
therefore outside this provider-version admission.

The closed `ClaudeSubscriptionQuotaV1@1.0` extension is unchanged. Claude Code
`2.1.289` renders one bounded model-specific weekly card that the V1 extension
cannot name. The parser validates at most one such card, omits it, and returns
`partial` with `claude_model_specific_window_unsupported`; the required current
session and all-model weekly windows remain present. The corresponding
`MissingFieldV1` explicitly reports `availability=unsupported`; it is not
Unknown or temporarily unavailable. Multiple model-specific cards,
duplicate/conflicting values, or an unallowlisted shaped label fail closed. No
provider extension, public API, generated client, event, database schema, or
migration contract changed.

Claude may also report a valid percentage for a recognized window without a
reset line. This is represented inside the same closed contract as
`ClaudeResetDisplayV1(value=None, availability=unknown, precision=unknown)`.
The admission's quota parser policy records
`missing_reset_display: field_unknown`. The reported percentage remains
available. No display text or reset instant is inferred. A present reset line
still has to meet the existing allowlist and conflict checks. Any reset-shaped
line that is present but malformed fails closed as invalid provider data;
absence alone is the only state mapped to Unknown.

## Test inventory and status

| Test/scenario | Layer and real dependencies | Status | Evidence |
|---|---|---|---|
| `CLA-PARSER-001`, `FR-COL-006/008` | Pure parser policy; constructed strings, no I/O | Passed | Bounded omission, `unsupported` omission availability, and malformed reset-shaped fail-closed coverage in `test_subscription_source_parser.py` |
| `FR-COL-004/007/008` | Pure parser and mapper policy; constructed structural input, no I/O | Passed | A reported percentage with no reset maps to the existing Unknown reset state; a present malformed reset-shaped line fails closed; no reset is invented |
| `CLA-CLI-003/004`, `CLA-PROV-001` | Manifest, exact mapping, parser provenance, evidence hashes | Passed | Exact scope, versions, evidence SHA-256, admission SHA-256, and manifest binding pass |
| `CLA-LIVE-001/004/005` | Retained native Claude Code `2.1.289` and real provider quota | Passed for the exercised protected and managed profiles | Exact retained-installation selection and genuine quota reads passed; quota may truthfully be `partial` only for the bounded omission |
| `CLA-LIVE-003/011/015` | Real authentication status and protected-default guard | Passed for the exercised profiles | Real auth/managed/connection suite passed; protected-default reauthentication is rejected before provider I/O |
| `CLA-LIVE-012` | Fresh owner-completed managed login on `2.1.289` | Passed for one selected profile | The selected profile completed owner authentication and produced genuine quota; this result does not claim the entire reauth continuity/wrong-account matrix |
| `CLA-LIVE-OTEL-003` | Real default `2.1.292` installation and owner data-root selector | Passed | The unretained exact `2.1.282` OTLP request is rejected before profile access or launch; neither `2.1.292` nor retained `2.1.289` widens the OTLP tuple |
| `FR-DISC-008`, `CTR-REG-004/006` | Retained admitted binary, real file-backed SQLite, stable exclusive service lock, and stopped-service owner registry | Passed | The command acquires owner-only service quiescence before discovery or registry mutation, binds strict replay scope and write metadata, and preserves stable installation and protected records |
| M4 exact partial-lineage and provenance policy | Pure fleet policy | Passed | Only exact source, adapter/parser `1.0.3`, provider `2.1.289`, decision reference, required windows, matching history, and no provider error are eligible; built account pages must render the exact source, adapter/version, and provider version for every window |
| Six-account authenticated preflight | Real scheduler, six owner-selected profiles, SQLite, API, built browser, and process association | Passed | Six accounts in two organizations had six distinct verified identities and six current history rows; one selected account had an owner-confirmed live process link; browser/API mutations were zero |
| `AUTO-M4-EXIT` fresh post-restart witness and formal M4 acceptance | Clean revision, service restart, scheduler, SQLite, API, built browser | Not Run at this admission checkpoint | Preflight reported `fresh_after_restart_count=0`; a later canonical gate and its receipt provide the post-restart result without rewriting this admission record |

## Red evidence

At the start of this increment, the default executable had advanced from the
historical admitted `2.1.282` tuple to `2.1.289`. Before the new admission,
genuine installation discovery failed closed with
`ClaudeInstallationUnavailable: claude_version_unverified`. This was the
expected real compatibility Red; the old parser was not allowed to run against
the new version. The default later advanced again to `2.1.292`; exact selection
continues to use the retained admitted `2.1.289` executable.

The parser and exact-version resolver Red used:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/test_subscription_source_parser.py \
  backend/tests/live/claude/test_installation.py -q --tb=short
```

It produced **3 failures** for the intended behavior: the new model-specific
card was still emitted as an unsupported new enum value, an unallowlisted
weekly label did not fail closed, and the installation resolver did not accept
the capability-specific `verified_provider_version` selector.

The M4 fleet-policy Red used:

```bash
node --test tools/ui/test_m4_fleet_policy.mjs
```

It produced **1 failure and 4 passes** because a truthful exact-tuple `partial`
run with both required current windows was not yet eligible as fresh lineage.

The exact admission test initially rejected the capability list because the
installation-only discovery operation was absent. Adding only
`installation.discovery` / `claude.version.banner.v1` /
`DiscoveryOutcomeV1@1.0` made the scope assertion green. The current structural
run later exposed a separate manifest mismatch: the admitted installation,
authentication-health, identity, and managed-reauthentication rows were absent
from `build_claude_manifest()`. The new `CLA-ARCH-004` admission-to-manifest
test failed with **1 failed** and listed those missing capabilities plus the
overbroad A04/M06-owned process-observation claim. After publishing the five
actual A01 rows and removing generic Linux process observation from this A01
admission, the focused test passed (**1 passed**). The structural manifest run
then returned **4 passed, 1 failed**; its sole failure was the deliberate
`in_progress` evidence status. After the authenticated fleet preflight and the
two-step evidence/admission hash binding, the full manifest suite passed.

The existing authenticated real-HTTP capability projection was rerun after the
manifest correction and passed (**1 passed in 1.56s**). It returned the same
five declaration rows from the production M03 manifest; no provider response
or account value was constructed for this contract check.

Installation reconciliation began with two missing-boundary Reds:
`ModuleNotFoundError` for
`agentmonitor.adapters.providers.claude.installation_discovery` and for
`agentmonitor.modules.registry.domain.discovery`. After the first strict route
was introduced, its real-outcome test failed with a missing
`reconcile_installation_only_discovery` repository entry.

The strict replay guard then used two real file-backed SQLite cases for changed
capability and nested installation-provider scope. Both failed with
`DID NOT RAISE RegistryRepositoryErrorV1`, proving that an existing receipt
could bypass validation:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/registry/test_claude_installation_reconciliation.py::test_strict_replay_rejects_changed_capability_and_preserves_database \
  backend/tests/integration/registry/test_claude_installation_reconciliation.py::test_strict_replay_rejects_changed_installation_provider_and_preserves_database \
  -q --tb=short
```

A second fingerprint Red omitted write metadata. Its focused parametrized test
reported **2 failures**, both
`DID NOT RAISE RegistryCommandConflictV1`:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/registry/test_claude_installation_reconciliation.py::test_strict_replay_binds_write_metadata_and_preserves_database \
  -q --tb=short
```

The correction validates strict scope before replay lookup and includes the
complete write metadata in the receipt fingerprint. The Green command was:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/registry/test_claude_installation_reconciliation.py \
  backend/tests/registry/test_installation_reconciliation_policy.py \
  -q --tb=short
```

It passed **15 tests in 9.56s**.

After the new managed authentication, the same real managed quota test failed
with `usage_deadline_window_incomplete`. A bounded structural diagnostic found
one required window with a reported percentage and no reset line. It inspected
only field presence and retained neither the percentage nor raw provider
output. The parser treated the absent optional field as an incomplete window,
which was the required behavioral Red for the field-availability correction.

A later parser review added five fail-closed cases. The focused Red reported
the expected five failures for a malformed reset beyond the old six-line
slice, a direct segment exceeding the 40-row terminal surface, and bare,
hyphenated, or bracketed unallowlisted `Current week` labels. The correction
validates the complete bounded segment and every weekly-label shape; it does
not widen the accepted values.

The authentication-health version guard began with an isolated audit-hook Red:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/test_authentication_health.py \
  -q --tb=short
```

It failed **1 test** because a supplied retained OTLP `2.1.282` installation
reached the quota source import, where the audit hook raised
`claude_usage_source_import_prohibited`. The correction returns the typed
`unverified_provider_version` / `claude_version_unverified` outcome before the
source module is imported.

## Green and refactor evidence

The minimum parser/installation implementation passed:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/test_subscription_source_parser.py \
  backend/tests/live/claude/test_installation.py \
  backend/tests/adapters/providers/claude/test_capacity_mapper.py \
  -q --tb=short
```

Result on the final focused set: **15 passed in 0.16s**.

The focused sparse-reset parser/mapper regression used:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/test_subscription_source_parser.py \
  backend/tests/adapters/providers/claude/test_capacity_mapper.py \
  -q --tb=short
```

Result on the final focused set: **13 passed in 0.13s**. It proves that the
bounded model-card omission, full-segment fail-closed checks, and reported
percentage behavior remain compatible. In particular, the percentage remains
available while the absent reset becomes `value=None`, `availability=unknown`,
and `precision=unknown`. Present reset displays retain their existing bounded
value and `provider_display` precision. A reset-shaped line that fails the
bounded display allowlist is rejected rather than treated as absent.

The isolated authentication-health version guard then passed with the same
command used for its Red: **1 passed in 0.10s**. A separate genuine read using
the selected retained admitted `2.1.289` executable passed in **4.06s**, proving
that the guard rejects other versions without blocking the admitted source.

The same genuine managed-profile quota scenario was then rerun with the
explicit private owner-data and account selectors used by the managed live
suite:

```bash
AGENTMONITOR_TEST_OWNER_DATA_ROOT=OWNER_DATA_ROOT \
AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID=OWNER_SELECTED_OPAQUE_ID \
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/live/test_managed_quota.py::test_real_managed_quota_uses_its_authenticated_identity \
  -q --tb=short
```

Result: **1 passed in 4.65s**. The identity remained stable around the read and
the protected default remained unchanged. The private selector is represented
by a non-secret placeholder; provider values and raw output are not repository
evidence.

The genuine current quota read passed:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/live/claude/test_subscription_quota.py -q --tb=short
```

Result: **1 passed in 4.11s**. The result carried source, exact provider,
adapter/parser decision reference, timestamps, precision, confidence, and both
required window keys. The test accepts `partial` only with the single closed
omission/warning code.

Real managed identity, authentication, connection process, and quota checks
used an explicitly selected existing AgentMonitor-managed account and owner
data root:

```bash
AGENTMONITOR_TEST_OWNER_DATA_ROOT=OWNER_DATA_ROOT \
AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID=OWNER_SELECTED_OPAQUE_ID \
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/live/test_managed_identity.py \
  backend/tests/adapters/providers/claude/live/test_authentication.py \
  backend/tests/adapters/providers/claude/live/test_connection_process.py \
  backend/tests/adapters/providers/claude/live/test_managed_quota.py \
  -q --tb=short
```

Result: **12 passed in 24.28s**. The private selector is represented here by a
non-secret placeholder; it is not repository evidence. This result verifies
the current read-only managed boundaries and connection process behavior. It
did not by itself substitute for a fresh owner-completed browser login; the
later selected-profile result above supplies that bounded live evidence without
expanding the claim to the entire reauth matrix.

The exact OTLP separation check used:

```bash
AGENTMONITOR_TEST_OWNER_DATA_ROOT=OWNER_DATA_ROOT \
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/live/claude/test_otel_version_gate.py -q --tb=short
```

Result: **1 passed in 0.42s**. The test generates its authorization value at
runtime and retains no secret.

A current-worktree refactor rerun combined the four managed-profile files and
the OTLP version gate with the same explicit owner selectors. It returned
**13 passed in 25.07s**.

The refactored fleet-policy suite returned **5 passed, 0 failed** with the same
`node --test tools/ui/test_m4_fleet_policy.mjs` command. Negative cases retain
failure for a wrong provider version, a missing required window, any provider
error, an unapproved partial tuple, a returned window without matching partial
history, or stale/mismatched observation history.

The focused registry/install regression used:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/registry \
  backend/tests/integration/registry/test_claude_installation_reconciliation.py \
  backend/tests/integration/registry/test_claude_fleet.py \
  backend/tests/live/claude/test_installation.py \
  backend/tests/foundation/test_contract_boundaries.py \
  -q --tb=short
```

Result on the final focused set: **250 passed in 19.99s**. Ruff, Ruff format,
strict Mypy, the module boundary checker (**0 violations**), and
`git diff --check` also passed for the
reconciliation increment. The strict M02 repository entry uses one transaction
for the version update, stable installation ID, provider-scoped protected-row
comparison, and replay-receipt creation and verification. It performs no
failure-producing read after commit.

The canonical reconciliation command now acquires the same stable exclusive,
owner-only service lock used by service operations before it reads the
installation or opens a registry write path. The occupied-lock scenario
returns **Blocked** with `service quiescence required`, preserves the database
bytes, and creates no installation row. The operator cannot race a running
AgentMonitor service into a version update.

## Canonical current-revision M4 technical lane

The `AUTO-M4-EXIT` implementation runs `AUTO-M3-TEST` after the
clean-revision service restart and before the M4 Pytest suite. That suite
includes exact-admission authentication, quota mapper, manifest, parser,
installation, OTLP version-gate, subscription-quota, installation policy, and
real reconciliation paths:

```text
backend/tests/adapters/providers/claude/live/test_authentication.py
backend/tests/adapters/providers/claude/test_authentication_health.py
backend/tests/adapters/providers/claude/test_capacity_mapper.py
backend/tests/adapters/providers/claude/test_manifest.py
backend/tests/adapters/providers/claude/test_subscription_source_parser.py
backend/tests/live/claude/test_installation.py
backend/tests/live/claude/test_otel_version_gate.py
backend/tests/live/claude/test_subscription_quota.py
backend/tests/registry/test_installation_reconciliation_policy.py
backend/tests/integration/registry/test_claude_installation_reconciliation.py
```

Its fleet witness rejects any current window or matching history point whose
source, adapter ID/version, parser version, provider version, or decision
reference differs from the admitted tuple. The built account page must also
render the exact source, `agentmonitor.claude · 1.0.3`, and provider version
`2.1.289` for every returned quota window. This describes the executable gate
scope. At this admission checkpoint, the authenticated preflight had passed with
six current account/history lineages and the owner-confirmed runtime link, while
the clean-revision gate had not run and its post-restart freshness count was
zero. A later M4 receipt records the gate outcome separately.

## Real-system evidence

All external-boundary checks above used the exactly selected retained native
Claude `2.1.289` binary, provider-owned real account state, real processes, and,
where selected, the
owner's real AgentMonitor SQLite data root. No provider response or dynamic
quota value was copied into this record. The default `claude` command is
`2.1.292` on Linux x86-64 and is outside this admission. The historical
`2.1.282` mapping and evidence remain unchanged; that executable is not
retained, so the OTLP lane fails closed.

With the AgentMonitor service stopped, the canonical installation command
acquired exclusive service quiescence and returned exit `0` against the owner
registry. The one existing opaque
installation ID remained stable while its reported version advanced from
`2.1.282` to `2.1.289`. Privacy-minimized public-view digests and counts were
identical before and after for six accounts, one discovery candidate, six
monitoring profiles, and six resource links. The private ID and record values
are not repository evidence.

One new owner-completed managed authentication and its genuine quota read are
proven for the exact admitted tuple. The later authenticated M4 preflight
proved six selected accounts in two organizations, six distinct verified
identities, six current matching history rows, one owner-confirmed live
process/account association, and zero browser/API mutations. This is a
pre-restart result. It does not claim the six fresh post-restart readings or
formal acceptance that only `AUTO-M4-EXIT` can produce.

## Integrity and data review

No mock, fake, stub, emulator, recorded/replayed provider response, demo
account, seeded telemetry, placeholder quota, hardcoded pass, disabled
assertion, or test-only production branch was used. Constructed values appear
only in the pure parser, mapper, and fleet-policy tests.

This record contains no account address, credential, token, password, one-time
code, raw provider output, prompt, response, source content, arbitrary process
environment, private profile path, or dynamic quota value. The provider owns
all authentication material. The official login flow accepts owner interaction
only for an AgentMonitor-managed profile and rechecks the protected default.

## Compatibility, migration, license, and operations impact

- The quota adapter/parser provenance advances to `1.0.3`; exact quota and
  managed-auth compatibility advances to Claude Code `2.1.289`.
- `ClaudeSubscriptionQuotaV1@1.0` and all public HTTP/generated-client schemas
  remain unchanged. The model-specific card is a bounded `unsupported`
  omission, and a missing reset uses the contract's existing Unknown field
  state. A malformed reset-shaped line fails closed. None is an unversioned
  schema extension.
- The separate OTLP adapter remains `1.0.0` and exact-pinned to Claude Code
  `2.1.282`; no `2.1.289` or `2.1.292` OTLP support is claimed.
- Installation reconciliation uses the real A01 discovery outcome and the
  existing M02 public port under a stable exclusive service lock. It blocks
  before mutation while AgentMonitor is running. Its internal strict
  transaction preserves the stable installation ID and provider-scoped
  account, profile, profile-resource-link, and candidate records.
- There is no database migration, dependency, license, provider-profile,
  credential, default-profile, or running-agent-control change.
- Rollback restores the prior adapter/manifest code. It does not rewrite the
  Claude installation, provider profiles, registry history, or quota history.

## Conclusion and residual gates

Focused evidence supports the exact `2.1.289` parser, read-only quota/auth
boundaries, closed partial result, truthful Unknown reset fields,
protected-default safety, atomic owner installation reconciliation, and
fail-closed version and OTLP separation. The six-account authenticated preflight
and two-step evidence/admission hash binding close this bounded exact-version
admission. The default `2.1.292` command remains unadmitted. At this admission
checkpoint, `AUTO-M4-EXIT`, its clean-revision restart, six fresh post-restart
readings, receipt, and formal M4 owner acceptance were pending and were not
implied by this Passed record. Later lifecycle evidence records those outcomes.
