# M0 G1 approval-integrity correction (in progress)

- Scope: `PLAN-M0-DISCOVERY`, `M0-G1-CONTROLS` `0.3.0-draft`; G1 only.
- Requirements: `NFR-TEST-001`, `NFR-TEST-002`, `NFR-SEC-001`, `NFR-PRIV-001`.
- Acceptance: `AC-TEST-001`, `AC-TEST-002`, `AC-TEST-006`.
- Authority: no provider, account, process, profile, network, or G2 access.

## Defect and correction

The earlier finalizer created security/privacy, test-integrity, provider-system,
and root-integration approvals from one owner confirmation. That was not evidence
of independent decisions. The finalizer now accepts a bounded owner-only local
review file, validates detached non-owner records against the exact current
custody, scanner, and bundle subjects, and creates only the owner's record after
the exact interactive confirmation. It rejects owner references used for
non-owner roles, duplicate roles/IDs, mismatched subjects, cross-role reference
reuse, and unsafe review-file permissions or JSON. It rechecks the custody root
before any write.

The code validates records, not the human or agent identity behind a reviewer
reference. Each role's actual review and exact-subject decision must be captured
as a separate handoff before creating the local review file. A syntactically
valid file alone is **not** proof of independent review.

## Red-to-green evidence

All commands ran in the real checkout on 2026-09-21. The Red failures were
expected behavioral failures before the corresponding code change:

| Behavior | Red command and result | Green command and result |
|---|---|---|
| Owner cannot mint other roles | `python3 -m unittest tools.discovery.test_m0_g1_approval.M0G1ApprovalTests.test_owner_confirmation_does_not_forge_independent_reviewer_decisions` → exit 1, expected missing-review violation absent | `python3 -m unittest tools.discovery.test_m0_g1_approval -v` → exit 0, 6 tests |
| Detached reviewer policy | `python3 -m unittest tools.discovery.test_m0_g1_approval.M0G1ApprovalTests.test_reviewer_decision_policy_rejects_owner_only_or_wrong_subject` → exit 1, validator absent | Same 6-test Green |
| Safe review-file load | `python3 -m unittest tools.discovery.test_m0_g1_approval.M0G1ApprovalTests.test_independent_review_file_is_owner_only_and_duplicate_key_free` → exit 1, loader absent | Same 6-test Green |
| Role-distinct references | Reviewer-policy test → exit 1, shared reference incorrectly accepted | Same 6-test Green |
| Exact owner confirmation | `python3 -m unittest tools.discovery.test_m0_g1_approval.M0G1ApprovalTests.test_finalizer_requires_exact_owner_confirmation_before_writes` → exit 1, unexpected keyword argument | Same 6-test Green |
| Repository-root refusal | `python3 -m unittest tools.discovery.test_m0_g1_approval.M0G1ApprovalTests.test_finalizer_rejects_repository_as_custody_root` → exit 1, only missing-review violation | Same 6-test Green |
| Owner ref cannot attest another role | Reviewer-policy test → exit 1, owner-reference violation absent | Same 6-test Green |
| Review hashes exclude subject content | `python3 -m unittest tools.discovery.test_m0_g1_approval.M0G1ApprovalTests.test_review_subject_rows_expose_ids_and_digests_only` → exit 1, formatter absent | `python3 -m unittest tools.discovery.test_m0_g1_approval -v` → exit 0, 7 tests |
| Pure owner-approval assembly | `python3 -m unittest tools.discovery.test_m0_g1_approval.M0G1ApprovalTests.test_owner_approval_assembly_is_pure_and_policy_valid` → exit 1, assembler absent | `python3 -m unittest tools.discovery.test_m0_g1_approval -v` → exit 0, 9 tests |
| Local-only review selection | `python3 -m unittest tools.discovery.test_m0_g1_approval.M0G1ApprovalTests.test_local_review_selection_validation_is_pure_and_root_agnostic` → exit 1, policy absent | Same 9-test Green; source review confirms no external-root stat before owner confirmation |
| Exact implementation artifact path | `python3 -m unittest tools.discovery.test_m0_g1_exit.M0G1ExitGateTests.test_contract_artifact_path_requires_exact_allowlist_before_read` → exit 1, guard absent | Focused exit and approval suite → exit 0, 16 tests |
| One-read parse/digest | `python3 -m unittest tools.discovery.test_m0_g1_exit.M0G1ExitGateTests.test_control_record_parser_binds_digest_to_same_bounded_bytes` → exit 1, parser absent | Same 16-test Green |
| Symlink parent refusal | `python3 -m unittest tools.discovery.test_m0_g1_exit.M0G1ExitGateTests.test_control_record_reader_rejects_symlink_parent_on_real_filesystem` → exit 1, actual filesystem symlink was accepted | Focused test → exit 0 after fd/parent hardening |
| Explicit sync/backup attestation | `python3 -m unittest tools.discovery.test_m0_g1_exit.M0G1ExitGateTests.test_custody_setup_writes_owner_only_local_selection` → exit 1, unexpected confirmation argument; then focused two-test run → exit 1 with old `1.0` selection version and no attestation | Focused two-test run → exit 0 after `1.1` owner attestation record |
| Old selection cannot pass | Real `AUTO-M0-G1-EXIT` initially Failed on stale bundle while old selection was accepted; after the attestation gate it returned Blocked (3) with old-version/missing-attestation reasons and reported external evidence Not Accessed | Full 97-test tool suite Green; real G1 exit remains Blocked until owner re-attests |
| Complete operation review template | `python3 -m unittest tools.discovery.test_m0_g1_contract.MinimalM0G1ContractTests.test_operation_template_requires_root_review_and_operator_checkpoint` → exit 1, root/integration row absent | Focused test → exit 0; full contract gate 7/7 Green |

`python3 -m unittest discover -s tools -p 'test_*.py'` passed 98 tests after
the correction. One intervening run failed three tests because an attempted
`routines.toml` blocker-text edit violated its approved snapshot and an exact
test assertion; that edit was reverted and the full suite rerun Green. A later
run failed one exact stdout assertion after the gate's truthful wording changed
from external-root metadata verification to local-only selection verification;
the assertion was updated. Another run failed one dispatcher assertion because
it treated any nonzero exit as Failed rather than preserving real Blocked (3);
that assertion was corrected and the later 98-test suite passed.
`AUTO-M0-G1-CONTRACT` passed 7 structural checks. `AUTO-M0-G1-EXIT` was
historically **Failed** (2) on the stale bundle and is now **Blocked** (3) on
the old, unattested custody selection. No live approval or positive
finalization is claimed. The former
constructed-record positive filesystem test was removed; genuine successful
write, exit validation, and immutable evidence remain required at the real G1
owner checkpoint.

The real `.venv-m0-g1/bin/python tools/discovery/m0_g1_approve.py` invocation
initially exited **Blocked (3)** before an owner prompt because independent
decisions were missing. The first `--review-subjects` implementation emitted
only fixed IDs/digests but unexpectedly statted the external root; this is
documented separately as an open safety finding. The corrected review mode
loads only local selection. After requiring attested local-selection version
`1.1`, the old owner selection is deliberately **Blocked** until renewed.

The owner has since confirmed that the previously selected evidence folder is
**not yet excluded from sync/backup**. The old local `excluded` value is not
factual custody evidence and must not be carried forward, attested, or used for
G1. The folder remains untouched. The approved M0 plan requires an explicit
owner decision, not mandatory exclusion: `CustodyDecisionV1` permits either
`excluded` or `owner_accepted_encrypted`, with `blocked` when neither is
truthful. The tooling now accepts either permitted choice through its own exact
owner statement. This corrects the implementation's unjustified exclusion-only
restriction; it does not assert that the selected folder's sync or backup is
encrypted. No external-root access or provider operation is authorized by this
correction.

The two added pure policy tests first failed (exit 1): the confirmation mapper
was absent, and the validator rejected `owner_accepted_encrypted`. After the
minimal correction, the focused 19-test G1 approval/exit suite passed (exit 0).
The full tool suite passed 100 tests; `AUTO-M0-G1-CONTRACT`,
`AUTO-DOCS-CHECK`, and local `AUTO-QUALITY` also passed. The actual owner
custody choice and `AUTO-M0-G1-EXIT` remain **Blocked (exit 3)**; its output
reported `external custody evidence: NOT ACCESSED`. Local
selection format `1.1` is unchanged; the old unverified `1.0` record still
requires a new truthful owner attestation. No public API or G1 JSON Schema
change was needed.

No dependency, license, provider-state, or public API change. The local custody
selection format changed from `1.0` to `1.1`; migration is an explicit owner
re-attestation, not an automatic conversion. The local reviewer-file interface
is G1 tooling only. Follow-up: independent role handoffs, owner custody
confirmation and incident acknowledgement, exact G1 approval, real exit, and
post-approval full-suite run.

Integration review found two separate post-G1 conditions. The G0-approved M0
plan says G1 executes `M0-COM-001`, while the narrower G1 specification and
runbook place that scenario after G1; no scenario has been executed. An owner
precedence decision or approved plan amendment is required before G2. Also,
`OperationPacketV1` lacks the exact command/HTTPS/path/field review bindings
required by M0 §8–9. The pure packet policy does not authorize a live run;
`AUTO-M0-PREFLIGHT` remains Blocked until a separately reviewed binding and
real runner exist.
