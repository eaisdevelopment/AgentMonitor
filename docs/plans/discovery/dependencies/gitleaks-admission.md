# M0 E1 scanner admission

- Admission ID: `DEP-M0-SCANNER-001`
- Status: **Approved for isolated local G1 verification; not for distribution**
- Review date: 2026-09-19
- Scanner: `gitleaks==8.30.0`, Linux x86-64 official binary
- License: MIT

## Decision

Version 8.30.1 is rejected because an upstream report demonstrates a
false-clean regression and its tag is outside the main history. Version 8.30.0
is the preceding signed release on the main history and is pinned for this
local-only gate.

- Official archive SHA-256:
  `79a3ab579b53f71efd634f3aaf7e04a0fa0cf206b7ed434638d1547a2470a66e`
- Installed binary SHA-256:
  `8b6fd684fcd5b4ebe39b68abb072ce59e1063ce7ed4abd556157697845f1f088`
- Scanner wrapper SHA-256:
  `e1e94448457a78b051065ae9318668e3cc144e8d7322e2633635c1fbcba2a375`

Sources: [8.30.0 release](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.0),
[8.30.1 regression](https://github.com/gitleaks/gitleaks/issues/2170), and
[orphaned-tag report](https://github.com/gitleaks/gitleaks/issues/2086).

The binary embeds its exact Go-module build inventory. It remains inside the
ignored local environment and must not be bundled or released until a complete
transitive SBOM/license notice is generated and reviewed.

## Real local verification

The production wrapper scanned exactly the real sanitized
`m0-g1-contract-test-evidence.md` file. It used an empty/minimal environment,
default embedded rules, no ignore/config discovery, zero archive/decode depth,
a size/time bound, complete redaction, and OS-level stdout/stderr discard.
`strace` observed no network syscall. The scan exited cleanly and pre/post file
identity, size, timestamp, and SHA-256 were unchanged.

No synthetic secret was introduced. Positive/failure detection states remain
Not Run until a safe naturally occurring condition exists; they are never
reported Passed. Every future E1 artifact still requires a real clean scan and
human allowlist review.

`detect-secrets==1.5.0` was rejected for this gate because it expands the
runtime/network-client graph and introduces an MPL-2.0 transitive requiring a
separate owner decision.

Copyright © 2026 Pavlo Sidelov. All rights reserved.
