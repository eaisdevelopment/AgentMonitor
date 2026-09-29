# M4 Claude identity re-attestation after service restart

- Status: **Read-only implementation, pure-policy evidence, and root-operated live restart evidence**.
- Scope: `ST-FLEET-001/002`, `AC-LIVE-004/005/007`, `FR-COL-004/006/008`, `FR-QUOTA-004/006`; supporting `NFR-SEC-001`, `NFR-PRIV-001/002`, `NFR-RES-001`.
- Contracts: existing `CTR-COL-002`, `CTR-REG-006`, `CTR-PROV-005` V1. No public shape, database schema or provider adapter change.

## Behavior

The service collector keeps successful same-run identity receipts in memory. A restart clears that cache although successful quota runs and observations remain durable. Once per polling tick, before due collection, the collector may read Claude's official `auth status` for one monitored target whose latest persisted source run is `succeeded`, observation-bearing, exact account/resource/source and not due. It requires the current identity fingerprint to resolve through the existing owner-confirmed M02 `claude.cli.auth.status.sha256` claim to the same account. It also checks provider/adapter version, the unchanged registry target, and the unchanged latest run after the read. Only then does it recreate an in-memory `VerifiedQuotaIdentityV1` tied to that actual run. It creates no quota value, source run, registry claim, new schedule or provider-state write. A read failure leaves the identity unresolved and does not defer another account's due collection.

The legacy protected-default enrollment has only an `m03_candidate_ref_sha256` claim. It cannot pass this restart check until an explicit owner-confirmed auth-status claim exists, or a fresh due quota collection obtains a same-run in-memory receipt. The published `ConfirmProviderIdentityFingerprintCommandV1` is an **owner command** whose repository records `owner_confirmed` and an owner principal. Calling it autonomously from a poller would falsely attribute an owner decision, so this increment does not do so. A future automatic persisted provider-verified claim requires a separate M02 contract and policy. Editable account names/emails are never identity proof.

## Test evidence

`backend/.venv/bin/python -m pytest backend/tests/collection_control/test_identity_reattest_policy.py -q` was Red after the function skeleton: `NotImplementedError: identity_reattest_policy_pending` on the exact successful-run assertion. After implementation, the same pure test passed. It checks the successful exact run, wrong account/resource, due run, partial run, and future completion. Inputs are constructed immutable domain values with no I/O. Ruff and strict mypy on the changed source/tests passed. This role did not open or modify the real owner database, service or profiles; root supplied the live evidence below.

## Root-operated live restart

Root restarted the installed service against the existing `v1_0707` owner database. Within about 30 seconds, five managed Claude accounts had verified identity receipts through read-only re-attestation against their exact stored M02 claims and latest successful quota runs. The protected-default account stayed unresolved because it lacked a durable `claude.cli.auth.status.sha256` claim. After its next genuine due quota collection produced a same-run identity receipt, all six accounts were verified and `verify_m4_fleet.mjs` passed. Re-attestation itself made no provider or registry writes and created no quota reading; the later scheduled collection persisted its genuine run and observation through the normal collector. Root performed this live operation; this role did not operate the owner service, database or profiles.

## Impact and follow-up

Changed only the M04 pure policy, service collector and its pure test. No migration, dependency/license, API/client, configuration or secret impact. The collector invokes only the existing read-only Claude auth-status adapter; it never reads prompts/responses, provider profile contents or arbitrary environment values. The protected default's durable claim gap remains: after another restart, its endpoint stays unresolved until a fresh due collection or explicit owner confirmation. Automatic durable provider-verified claims need a separately approved M02 contract and policy. Root owns the full M4 gate.
