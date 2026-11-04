# M6 security, privacy and compatibility review

- Review: `M6-T016`, Story `ST-OLL-005`, acceptance `M6-A09`.
- Requirements: `FR-SAFE-001/002`, `FR-COL-007`; `AC-V1-005/007`,
  `AC-PROC-004`.
- Reviewed integration revision: `39f483f221f12c43a3387101feb4d8739285e722`.
- Additional reviewed diffs: `f3b3590` (history period display), `8b9f815`
  (local capability publication), `71f2adf` (real test-account selection).
- Method: bounded source and existing evidence review. No provider, browser,
  database, credential, process-control or service operation was performed.
- Result: no new mandatory security/privacy defect identified in the reviewed
  paths. This is not full M6 acceptance, a penetration test or a fresh live pass.

The authority is the approved [cloud plan](../plans/integration/m6-ollama-cloud-implementation-change.md),
[local plan](../plans/integration/m6-ollama-local-vertical-change.md),
[process plan](../plans/integration/m6-ollama-process-implementation-change.md)
and [coverage amendment](../plans/integration/m6-cloud-scope-outcomes-contract-impact.md).
The owner-approved managed `.env` exception in `AGENTS.md` supersedes the
historical Secret Service proposal; it does not authorize coding agents to
inspect keys or the runtime to alter provider profiles.

## Reviewed controls and findings

| Boundary | Source reviewed and assessment |
|---|---|
| Cloud destination and TLS | `adapters/providers/ollama/cloud_balance/transport_policy.py:36` and `source.py:484,656` fix HTTPS, `ollama.com:443`, GET `/api/balance`, one attempt and no redirect/proxy mechanism. TLS verifies certificates and hostnames; key logging and connection debug output are disabled. No account-supplied URL reaches transport. No SSRF or credential-redirection defect identified in these paths. |
| Timeout and response containment | `source.py:249,577,1022` bounds headers/body and uses a deadline-controlled isolated child. `deadline_helper.py:23,101` disables core dumps/dumpability before credential handling and installs the wall-clock alarm. The parent independently bounds waiting and cleans only its created worker. The direct synchronous transport alone does not promise a strict DNS deadline; the admitted runtime uses the isolated path. |
| Managed credential access | `env_capability.py:73,227,438` checks regular owner-only 0600 single-link files, bounded size, no-follow opens, pinned descriptors and directory/file identities. `env_authorization.py:76` revalidates lock/file authority around the read and sends one binding-specific value to the single-use bearer sink. `env_stream.py:19` skips unrelated lines rather than exposing them to consumers. Secret-bearing exceptions are collapsed to closed codes. |
| Enrollment and storage | `composition/ollama_credential_enrollment.py:95` uses local no-echo entry and existing locked transitions; `ollama_env_store.py` retains guarded file replacement and pending cleanup. The runtime stores the selected managed entry only under the explicit exception. Browser routes and coverage storage do not accept keys. No provider-profile writer was introduced. |
| Worker ownership | `composition/ollama_cloud_worker.py:267,313,547` verifies executable/arguments, data root, transient identity, invocation, limits and cgroup before cleanup. Discovery is scoped to the canonical data-root hash; legacy recovery is limited to the exact own marker. This distinguishes owned collection workers from user agents and foreign installations. |
| Local metadata | `local_catalog/source.py:18,193` restricts requests to version/tags/ps on `127.0.0.1:11434`, bounds transport and model-name parsing, and requires 0.24.0 before and after observation. No inference/load/download/delete route exists. `installation.py:75,96` verifies executable metadata and runs only `--version` with temporary HOME/config/cache and a bounded output/deadline. |
| Process observation | `adapters/platform/linux/processes.py:260` uses the approved executable selector and same-user process metadata. It does not read process argv/environment, prompts or responses. Ollama account/model relationships remain unresolved rather than guessed. |
| Commit fencing | `composition/ollama_capacity_commit.py:65` composes M02/M04 transaction validators with M05 persistence: account, active/current credential generation, target graph, lease/run and source identity are rechecked before commit. No direct provider writes or arbitrary consumer SQL are added by this seam. |
| Registry coverage API | `api/v1/routers/coverage.py:197` requires `write:accounts`, CSRF, If-Match, idempotency and selected-account version. Producer-owned provenance remains `owner_asserted`; coverage changes metadata, not credentials, observations or proven pool identity. Read selection is bounded and preserves absent members. |
| Quota/history presentation | `frontend/src/features/command/quotaPresentation.ts:32` formats exact USD using decimal strings. `CapacityPanel.tsx` retains units, separate windows, freshness, timestamps and lineage; mixed-unit series are not combined. Missing ratios do not become invented percentages. The `f3b3590` history diff renders the supplied `source_period_start` verbatim in the time element and explicitly marks absence. It does not infer a start from reset or require a new current-quota API. |

Source paths in the table are relative to `backend/src/agentmonitor` unless
prefixed with `frontend`. References identify the reviewed revision, not future
line locations. The source payload parsers admit closed balance variants and
exact decimal quantities; raw provider bodies do not leave the adapter.

## Additional diff assessment

`8b9f815` publishes only installation discovery and local model catalog for the
existing exact 0.24.0/Linux tuple, with read-only sources and the existing
3-second/12-second budgets. It neither enables cloud authentication generally
nor grants model mutation. Publication of a supported metadata capability does
not establish a model-present acceptance result.

`71f2adf` changes private-copy test selection to an eligible existing active,
owner-confirmed account without assuming exactly one account exists. It retains
complete-page checks, matching existing declarations and deterministic ordering.
The browser harness still refuses the installed dashboard port before writes;
it does not create a fictional account or synthesize a shared/unavailable
owner outcome. This review did not run that mutating private-copy harness.

## Compatibility, dependencies and residual limits

The reviewed boundaries use `OLLAMA-CLOUD-BALANCE-V1` 1.0.0,
`CTR-PROV-OLLAMA-LOCAL-CATALOG-001` 1.0.0, `CTR-REG-011` 1.0.0,
`CTR-COL-008` 1.0.0, `CTR-REG-013` 1.0.0 and the existing generated
`AccountCapacityViewV2`, `QuotaWindowViewV2`, `CapacityHistoryPointV2` and
`ExactMetricFieldWireV1`. Coverage is the reviewed additive schema0719 change;
the three additional diffs add no contract or database version. This review
adds only this evidence document.

The dependency manifests/lockfile (`backend/pyproject.toml`, root
`pyproject.toml`, `frontend/package.json` and `frontend/package-lock.json`)
have no diff between accepted M5 `ab1408b` and reviewed `39f483f`; the three
additional diffs also change no dependency. No new package/license admission
is required by these changes. This is not a fresh vulnerability-database scan.

Existing limitations remain explicit:

- Same-user privileged software is outside the credential isolation guarantee;
  bytearray clearing does not prove elimination of all immutable TLS/Python
  copies. Base64 storage is encoding, not encryption.
- The approved parent-directory policy permits group-writable 0770/0775
  directories while pinning/validating identities. That recorded residual is
  not a claim of protection against a malicious same-user/group writer.
- Loopback HTTP identifies the configured local endpoint, not a cryptographically
  authenticated desktop application or a different model host.
- Historical evidence includes blocked/not-run checks and corrections. In
  particular, the worker-isolation full-file run disclosed an anonymous
  provider probe outside that task's restriction; it must not be relabelled
  provider-free. No such request was repeated for this review.
- The reviewer contributed earlier migration, worker and UI changes. This
  bounded review is not represented as an independent audit of all M6 code.

## Evidence used and verification status

Reviewed component records include [managed environment](m6-ollama-env-candidate-2026-11-02.md),
[worker isolation](m6-worker-root-isolation-2026-11-03.md),
[registry coverage](m6-coverage-registry-2026-11-03.md),
[coverage API/UI](m6-coverage-api-ui-2026-11-03.md),
[migration recovery](m6-coverage-migration-2026-11-03.md),
[native USD display](m6-native-usd-account-ui-2026-11-03.md),
[process display](m6-ollama-process-ui-2026-11-02.md), and the
[delivery checkpoint](m6-delivery-checkpoint-2026-11-03.md).
Their reported outcomes retain their original revision and boundary; none is
claimed as a new test result from this review.

Runtime tests, authenticated browser checks, provider checks, secret-store
operations, migration/restore and `AUTO-QUALITY` were **Not Run by this review**.
Root owns the integrated canonical checks and installed verification, including
the history-period browser Green. Outstanding model-present, organization,
natural-recovery or acceptance evidence is not waived by finding no new
security defect. No new approval or completion gate is introduced here.
