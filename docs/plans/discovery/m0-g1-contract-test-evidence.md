# M0 G1 minimal-contract test evidence

- Evidence ID: `EVID-M0-G1-CONTRACT-002`
- Date: 2026-09-19
- Scope: repository structure only
- Requirements: `NFR-TEST-001`, `NFR-TEST-002`, `NFR-SEC-001`,
  `NFR-PRIV-001`, `NFR-DOC-001`
- Acceptance criteria: `AC-TEST-001`, `AC-TEST-002`, `AC-TEST-006`
- Contract: `M0-G1-CONTROLS` `0.3.0-draft`

This evidence supersedes `EVID-M0-G1-CONTRACT-001`. The earlier evidence bound
the discarded over-scoped G1 design and is not valid for this revision.

## Red

Command:

```bash
python3 -m unittest tools.discovery.test_m0_g1_contract
```

Result: **Failed**, 6/6 tests failed as expected against the obsolete bundle.
The failures identified the 1,606-line specification, 222 schema definitions,
obsolete files/templates, stale indexes, and missing minimal safety fields.

## Green

Command:

```bash
python3 -m unittest tools.discovery.test_m0_g1_contract
```

Result: **Passed**, 6/6 tests. The test reads the real checkout and validates
the bounded specification, seven-record schema, six templates, removals, safety
fields, closed objects, status vocabulary, and documentation indexes.

## Limits

- No provider, account, profile, process, secret, or external evidence root was
  accessed.
- Supply-chain downloads installed only the approved isolated G1 validator and
  scanner. Scanner runtime made no observed network syscall.
- Custody selection, final G1 approval, preflight, postflight, and ledger
  execution remain Blocked or Not Run.

## Implementation increments

The owner approved implementation of the exact `0.3.0-draft` contract plus its
isolated dependency and local-scanner steps. The approval record still
withholds evidence-root, provider, account, G1-completion, and G2 authority.

`python3 -m unittest tools.discovery.test_m0_g1_exit` first failed because the
approval and exit gate did not exist, then passed 2/2 after the fail-closed gate
was implemented. A second Red failed because custody verification did not
exist; Green passed 3/3 after read-only checks were implemented against real
temporary directories, permissions, a real symlink, and the real repository
root. No mock, fake, provider data, scanner, or external evidence root was used.
A third Red failed on the missing UTC-`Z` checker; Green passed 4/4 after a
strict calendar-valid standard-library checker was added. Canonical JSON Schema
execution then failed Red at the absent isolated runtime and passed Green under
the hash-locked `jsonschema==4.26.0` environment. The next Red rejected missing
dependency/scanner authority and absent scanner verification; Green passed 4/4
after exact authority, binary-digest/version checks, output discard, real-file
scan, network-syscall check, and pre/post file-identity checks were implemented.
A final Red rejected the absent custody setup mechanism; Green passed 5/5 after
an interactive, hidden-input, atomic owner-only local selection writer was
implemented. Its real external-root use remains Blocked pending owner action.

The owner then selected a real owner-only external root. This exposed a mutable-
state defect in the canonical test: it expected the earlier unconfigured state.
That test failed Red and passed Green after asserting the verified-selection
state without revealing the path.

Subsequent Red increments failed on the absent detached-approval module, custody
binding, exact bundle manifest, owner finalizer, final-state validator, and
finalizer automation registration. Green added canonical approval projections,
closed role/expiry/digest checks, a fixed owner-only custody record, exact
scanner and bundle binding, and `AUTO-M0-G1-FINALIZE`. The focused suite passed
27/27 against the real checkout and real temporary filesystem. No provider,
account, process, profile, prompt, response, provider source content, credential, or
external custody content was used. Final owner approval and the resulting
canonical exit remain Blocked until the owner executes the named checkpoint.

Copyright © 2026 Pavlo Sidelov. All rights reserved.
