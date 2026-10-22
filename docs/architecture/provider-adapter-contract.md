# Provider adapter contract

- Contract: `ProviderAdapterV1`
- Contract version: `1.0.0-draft.2`
- Status: Draft synchronized; not implementation-authorized

## Purpose

Provider adapters isolate unstable external behavior from the AgentMonitor domain. Claude, Codex, Ollama, and future providers implement the same capability-driven protocol without pretending all providers expose the same data.

## Capability vocabulary

An adapter declares zero or more versioned capabilities:

- `installation.discovery`
- `account.discovery`
- `identity.verification`
- `authentication.health`
- `authentication.reauthenticate`
- `subscription.quota`
- `api.usage`
- `api.cost`
- `api.budget`
- `project.discovery`
- `model.catalog`
- `local.session.discovery`
- `local.session.metrics`
- `local.process.correlation`
- `provider.diagnostics`

Each capability declaration includes schema version, source class, required credential role, verified provider versions, expected freshness, potential side effects, and stability.

## Source classification

1. **Documented API:** public supported API with documented authentication and schema.
2. **Supported CLI:** documented CLI command or structured output.
3. **Approved local metadata:** read-only, allowlisted fields from provider-owned state.
4. **Experimental private/browser:** undocumented endpoint or browser automation; disabled by default and requiring explicit opt-in.

An adapter must not silently move to a lower source class. The active source is returned with every observation.

## Required adapter behavior

Conceptual operations—not final Python signatures—are:

```text
manifest() -> CapabilityManifest
discover_installations(context) -> DiscoveryOutcome
discover_accounts(installation, context) -> DiscoveryOutcome
verify_identity(profile_ref, context) -> IdentityOutcome
inspect_auth(profile_ref, context) -> AuthHealthOutcome
collect(capability, account_ref, profile_ref, window, context) -> CollectionOutcome
discover_local_sessions(installation, context) -> SessionDiscoveryOutcome
start_reauthentication(profile_ref, context) -> ReauthFlowOutcome
verify_reauthentication(flow_ref, expected_identity, context) -> ReauthResult
diagnose(installation/profile_ref, context) -> SanitizedDiagnostics
```

`context` supplies deadline, cancellation, correlation ID, approved paths, safe subprocess executor, HTTP client policy, and secret/profile references. It never exposes unrelated accounts or arbitrary environment values.

## Outcomes

Every completed operation returns exactly one outcome state:

- `success`
- `partial` with explicit missing fields/warnings
- `unsupported`
- `unverified_provider_version`
- `reauthentication_required`
- `authorization_insufficient`
- `provider_unavailable`
- `rate_limited`
- `invalid_provider_data`
- `deadline_exceeded`
- `blocked_user_action_required`
- `internal_adapter_error`

Caller cancellation publishes no completed provider outcome. It travels on
the operation context's cancellation control channel, and M04 records the
cancelled collection-run state without inventing a thirteenth provider outcome.

Exceptions are converted at the adapter/application boundary into sanitized outcomes. Programmer defects may still fail fast in development, but secrets and raw payloads must never cross the boundary.

`ProviderAdapterV1` `1.0.0-draft.2` uses
`reauthentication_required` as both the operation outcome and normalized
provider-auth spelling. The earlier unpublished Draft spelling
`authentication_required` is not a compatible input and has no implemented or
published consumer; provider-native or legacy values are mapped at the adapter
boundary and never enter the normalized contract.

## Observation rules

- Missing is not zero.
- Exhausted is a provider fact or domain conclusion with explicit evidence, not a failed request.
- Reset timestamps include provider timezone/precision when known.
- Derived percentages retain numerator, denominator, units, and input observation IDs.
- Provider-specific safe fields live under a schema-versioned extension object.
- Raw responses are not stored by default. An allowlist mapping extracts only required metadata.
- A source that cannot selectively return safe fields without intentionally
  reading prompts, content, tokens, credentials, or unrelated personal data is
  not opened and is `blocked`, `deferred`, or `unsupported`; post-read discard
  is not a privacy control.

## Identity rules

- Discovery evidence may include safe account ID, workspace/project ID, plan label, and masked display identity.
- Email is treated as personal data and stored/displayed only if required and approved by the account contract.
- An account association needs a stable provider ID or explicit owner confirmation.
- A mismatch during re-authentication stops the flow. A completed verification
  operation returns the outer `success` outcome with a typed identity or
  reauthentication result state of `wrong_account_detected`; that state is not
  an additional operation-outcome variant.
- The adapter cannot mutate registry ownership directly.

## Credential rules

- `profile_ref` is opaque to the domain.
- Provider credentials remain in provider-managed storage.
- Adapters may invoke the provider CLI with an approved profile root but may not copy credentials into AgentMonitor storage.
- Default profiles are marked protected; mutating operations reject them before invoking external code.
- Authentication commands use argument arrays, sanitized environments, deadlines, and user-visible interaction.
- Passwords, OTPs, MFA, tokens, and browser cookies are never accepted as adapter method parameters.

## Local file parsing

- Paths come from approved installation/profile roots, not provider file contents.
- Reject symlink escapes and non-regular files unless explicitly supported.
- Bound file size and parsing time.
- Read only allowlisted files/fields, and reject a file when the approved parser
  cannot avoid reading co-resident prohibited bytes.
- Parser output records file format/parser version and provider CLI version.
- A format mismatch yields `unverified_provider_version` or `invalid_provider_data`; it does not guess.
- Content-bearing fields are never intentionally read or loaded into memory.

## Subprocess policy

- Use direct executable plus argument vector; no shell interpolation.
- Resolve the executable and record its version before first use.
- Restrict inherited environment to the approved minimum.
- Never place secrets in command arguments.
- Bound stdout/stderr and redact before diagnostic handling.
- Use a process group and a defined cancellation/timeout strategy.
- Read-only collection commands must not modify provider configuration.

### Managed-profile namespace containment

- Successful link creation is rejected unless an approved exact-version
  provider plan defines a closed lifecycle and the containment gate proves it.
- For pinned Codex CLI `0.160.0`, each managed identity and quota app-server
  root may complete the official pre-session Arg0-root setup under ordinary
  confinement: `mkdir(arg0_root, 0777)` may report `EEXIST`, followed by the
  already admitted inode-bound `chmod(arg0_root, 0700)`. Both calls must finish
  before the exact session creation and do not satisfy any lifecycle record.
- Each operation must then create exactly one canonical
  `tmp/arg0/codex-arg0[A-Za-z0-9]{6}` session, open exactly one regular `.lock`
  child with the approved flags and mode, and create exactly one ordered set of
  `apply_patch`, `applypatch`, `codex-linux-sandbox`, and
  `codex-execve-wrapper` symlinks. Double-leading-slash and every other
  noncanonical path spelling are rejected before containment comparison,
  including separately decoded successful-open descriptor annotations. Every
  alias payload must equal the inode-validated pinned executable.
- The lock child and each admitted alias require one matching cleanup in the
  same provider operation before actual operation closure. Their cleanup order
  is filesystem-neutral. The two broad namespace/write guards cover exactly
  session-creation invocation through final fifth-child cleanup completion;
  records invoked in or crossing that interval remain guarded. Namespace
  movement or exchange is rejected throughout it; ordinary removal of the
  empty session directory is permitted only after all five children are clean.
- A cwd-dependent relative path lookup fails closed when its
  invocation/completion interval overlaps a successful unfinished `chdir` in
  the same tracked `CLONE_FS` group. Absolute paths, descriptor-bound relative
  cleanup, and relative lookups invoked after the `chdir` completes remain
  admissible under their other containment rules.
- A successful filesystem write without ownership in the selected provider
  operation fails closed when its syscall interval overlaps the protected Arg0
  operation. Lexical aliases through `/proc/*/root`, directory descriptors, or
  another path spelling cannot bypass namespace or write-through protection.
- Descendant-created, additional, reordered, retained, default-profile,
  outside-profile, hard-link, `symlinkat`, and every other link lifecycle fail
  closed. The exact provider-owned create/cleanup lifecycle is the only
  admitted link lifecycle. This exception grants no access to the protected
  default profile and changes no public adapter outcome or evidence schema.

## Capability matrix

Milestone 0 produces one matrix row per provider/capability/source with:

- provider and installed version;
- account/plan types verified;
- exact real source;
- authentication mechanism;
- fields available and missing;
- refresh behavior and rate limits;
- precision/freshness;
- side effects;
- stability/source class;
- live evidence reference;
- parser/adapter implications;
- decision: supported, experimental, deferred, or unsupported.

No provider implementation plan may be approved without its capability matrix.

## Extension compatibility

Future providers implement the protocol without changing core account, capacity, runtime, or alerting modules. A genuinely new concept begins as a provider extension. It enters the normalized core only after at least two providers need the same semantics and an ADR defines the invariant.
